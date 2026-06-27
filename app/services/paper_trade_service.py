"""Paper Trade Service — fill simulation at last close ± slippage.

Fill rules (PRD §4):
- Price: last NSE close from market_data
- Slippage: +5 bps on BUY, -5 bps on SELL (config)
- Full quantity only (no partials v1)
- Fees: flat ₹20 per leg (config)
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import DEFAULT_BENCHMARK_SYMBOL, TradeSide, TradeStatus
from app.db.repositories.market_data_repository import MarketDataRepository
from app.models.paper_trade import PaperTrade
from app.models.recommendation import RecommendationOutcome, RecommendationResult, RecommendationRun
from app.services.portfolio_nav_service import PortfolioNavService
from app.services.portfolio_service import PortfolioService

# When several exit triggers fire on the same day (e.g. a gap-down trips both the
# stop-loss AND rank-drop), the recorded exit_reason must be the most *severe* one,
# not whichever was appended first. Picking triggers[0] mislabelled gap-down stops
# as RANK_DROP, which (a) distorted exit analytics and (b) bypassed the P-16
# stop-loss re-entry cooldown — letting the pilot immediately re-buy a crashed name.
# Lower index = higher precedence.
_EXIT_REASON_PRECEDENCE: list[str] = [
    "EXIT_STOP_LOSS",      # capital protection — always wins the label
    "EXIT_TRAILING_STOP",  # profit protection
    "EXIT_REGIME",         # de-risk on regime flip
    "EXIT_LIQUIDITY",
    "EXIT_TIME",
    "EXIT_ALPHA_DECAY",
    "EXIT_RANK_DROP",      # analytical — least severe
]


def _primary_exit_reason(exit_triggers: list[str] | None) -> str | None:
    """Pick the most severe fired trigger as the recorded exit reason."""
    if not exit_triggers:
        return None
    for reason in _EXIT_REASON_PRECEDENCE:
        if reason in exit_triggers:
            return reason
    return exit_triggers[0]  # unknown trigger — fall back to first


class PaperTradeService:
    def __init__(
        self,
        db: Session,
        *,
        portfolio_service: PortfolioService | None = None,
        market_data_repo: MarketDataRepository | None = None,
        nav_service: PortfolioNavService | None = None,
    ) -> None:
        self.db = db
        self.portfolio_service = portfolio_service or PortfolioService(db)
        self.market_data_repo = market_data_repo or MarketDataRepository(db)
        self.nav_service = nav_service or PortfolioNavService(db)
        from app.core.config import get_settings
        self.settings = get_settings()

    def execute_entry(
        self,
        *,
        recommendation_result_id: UUID,
        as_of_date: date | None = None,
        idempotency_key: str | None = None,
    ) -> PaperTrade:
        """Simulate a BUY fill for an approved recommendation."""
        result = self.db.get(RecommendationResult, recommendation_result_id)
        if result is None:
            raise ValueError(f"RecommendationResult {recommendation_result_id} not found")
        if result.action != "BUY":
            raise ValueError(f"Cannot execute entry — action is {result.action}, expected BUY")

        idem_key = idempotency_key or self._make_idem_key("entry", recommendation_result_id)
        existing = self.db.scalar(select(PaperTrade).where(PaperTrade.idempotency_key == idem_key))
        if existing:
            return existing

        fill_date = as_of_date or date.today()
        fill_price, last_close = self._fill_price(
            result.stock_id, fill_date, side="BUY",
            entry_low=float(result.entry_low) if result.entry_low is not None else None,
            entry_high=float(result.entry_high) if result.entry_high is not None else None,
        )

        # Compute quantity from portfolio allocation
        try:
            alloc = self.portfolio_service.compute_allocation(
                conviction_band=result.conviction_band or "MEDIUM",
                last_price=last_close,
                as_of_date=fill_date,
            )
            quantity = max(1.0, alloc.quantity_estimate)
        except Exception:
            quantity = 1.0

        # Cash guard: skip fill if insufficient cash (avoids negative cash balance)
        summary = self.portfolio_service.get_summary(fill_date)
        required = quantity * fill_price
        if summary.cash_available < required:
            raise ValueError(
                f"Insufficient cash: have ₹{summary.cash_available:,.0f}, need ₹{required:,.0f}"
            )

        rec_run = self.db.get(RecommendationRun, result.recommendation_run_id)
        ranking_run_id = rec_run.ranking_run_id if rec_run else None
        strategy_name = rec_run.strategy_name if rec_run else None
        regime_label = None
        if rec_run and rec_run.regime_snapshot:
            regime_label = rec_run.regime_snapshot.get("regime_label")

        trade = PaperTrade(
            stock_id=result.stock_id,
            side=TradeSide.BUY.value,
            quantity=quantity,
            limit_price=None,
            fill_price=fill_price,
            fill_quantity=quantity,
            status=TradeStatus.FILLED.value,
            ranking_run_id=ranking_run_id,
            idempotency_key=idem_key,
            requested_at=datetime(fill_date.year, fill_date.month, fill_date.day, 15, 0, tzinfo=UTC),
            filled_at=datetime(fill_date.year, fill_date.month, fill_date.day, 15, 0, tzinfo=UTC),
            metadata_={
                "recommendation_result_id": str(recommendation_result_id),
                "recommendation_run_id": str(result.recommendation_run_id),
                "conviction_band": result.conviction_band,
                "conviction_score": result.conviction_score,
                "reason_codes": result.reason_codes,
                "last_close": last_close,
                "slippage_bps": 5.0,
                **self._fill_meta(),
            },
        )
        self.db.add(trade)
        self.db.flush()

        # Open portfolio position
        from app.models.stock import Stock

        stock = self.db.get(Stock, result.stock_id)
        sector = stock.industry if stock else None

        pos = self.portfolio_service.open_position(
            stock_id=result.stock_id,
            quantity=quantity,
            fill_price=fill_price,
            entry_date=fill_date,
            recommendation_result_id=recommendation_result_id,
            conviction_band=result.conviction_band,
            strategy_name=strategy_name,
            sector=sector,
        )

        # Cash ledger: capital out (trade value) + fee
        self.nav_service.ensure_initial_capital(fill_date)
        trade_value = quantity * fill_price
        fee = self._leg_cost(trade_value, "BUY")  # P-24: full cost stack when enabled
        self.nav_service.record_cash_entry(
            entry_type="TRADE_BUY",
            amount=-trade_value,
            as_of_date=fill_date,
            reference_id=trade.id,
            reference_type="paper_trade",
            description=f"BUY {quantity} {stock.symbol if stock else ''} @ {fill_price}",
        )
        if fee:
            self.nav_service.record_cash_entry(
                entry_type="FEE",
                amount=-fee,
                as_of_date=fill_date,
                reference_id=trade.id,
                reference_type="paper_trade",
                description="Entry fee",
            )

        # Create RecommendationOutcome (OPEN)
        outcome = self.db.scalar(
            select(RecommendationOutcome).where(
                RecommendationOutcome.recommendation_result_id == recommendation_result_id
            )
        )
        if outcome is None:
            outcome = RecommendationOutcome(
                recommendation_result_id=recommendation_result_id,
                outcome_status="OPEN",
                entry_date=fill_date,
                entry_price=fill_price,
                conviction_band=result.conviction_band,
                symbol=stock.symbol if stock else None,
                strategy_name=strategy_name,
                regime_label=regime_label,
            )
            self.db.add(outcome)

        # Advance lifecycle
        result.lifecycle_state = "ACTIVE"
        result.portfolio_position_id = pos.id
        self.db.flush()
        return trade

    def _fee(self) -> float:
        cfg = (
            self.portfolio_service.get_config()
            if hasattr(self.portfolio_service, "get_config")
            else None
        )
        try:
            return float(cfg.fee_per_leg) if cfg else 20.0
        except Exception:
            return 20.0

    def _fill_meta(self) -> dict:
        """Realistic-fill diagnostics for the most recent ``_fill_price`` call, to be
        merged into the trade metadata. Empty (→ no metadata change) when realistic
        fills are off or intraday data was unavailable, so the legacy path is identical.
        """
        q = getattr(self, "_last_fill_quote", None)
        if q is None:
            return {}
        return {
            "fill_model": {
                "vwap": q.ref_price,
                "impact_bps": q.impact_bps,
                "participation_pct": round(q.participation * 100.0, 4),
                "fill_ts": q.fill_ts.isoformat(),
            }
        }

    def _leg_cost(self, trade_value: float, side: str) -> float:
        """P-24: per-leg transaction cost (₹). When ``transaction_costs_enabled``,
        models the NSE delivery-equity stack (STT + stamp + exchange txn + SEBI +
        GST + flat brokerage) so NAV is net of costs; otherwise returns the legacy
        flat per-leg fee. STT applies on both legs (delivery); stamp duty buy-only.
        """
        s = self.settings
        brokerage = self._fee()
        if not getattr(s, "transaction_costs_enabled", False):
            return brokerage
        is_buy = side == "BUY"
        stt = (s.cost_stt_buy_pct if is_buy else s.cost_stt_sell_pct) / 100.0 * trade_value
        stamp = (s.cost_stamp_buy_pct / 100.0 * trade_value) if is_buy else 0.0
        exch = s.cost_exchange_txn_pct / 100.0 * trade_value
        sebi = s.cost_sebi_pct / 100.0 * trade_value
        gst = s.cost_gst_rate * (brokerage + exch + sebi)
        return round(stt + stamp + exch + sebi + brokerage + gst, 2)

    def execute_exit(
        self,
        *,
        recommendation_result_id: UUID,
        as_of_date: date | None = None,
        idempotency_key: str | None = None,
    ) -> PaperTrade:
        """Simulate a SELL fill for a confirmed EXIT_APPROVED."""
        result = self.db.get(RecommendationResult, recommendation_result_id)
        if result is None:
            raise ValueError(f"RecommendationResult {recommendation_result_id} not found")
        if result.action not in ("EXIT_APPROVED", "HOLD"):
            raise ValueError(f"Cannot execute exit — action is {result.action}")

        idem_key = idempotency_key or self._make_idem_key("exit", recommendation_result_id)
        existing = self.db.scalar(select(PaperTrade).where(PaperTrade.idempotency_key == idem_key))
        if existing:
            return existing

        fill_date = as_of_date or date.today()
        fill_price, last_close = self._fill_price(result.stock_id, fill_date, side="SELL")

        # Get position for quantity
        from app.models.portfolio_position import PortfolioPosition

        pos = self.db.scalar(
            select(PortfolioPosition).where(
                PortfolioPosition.stock_id == result.stock_id,
                PortfolioPosition.is_current.is_(True),
            )
        )
        quantity = float(pos.quantity) if pos else 1.0

        rec_run = self.db.get(RecommendationRun, result.recommendation_run_id)
        ranking_run_id = rec_run.ranking_run_id if rec_run else None

        trade = PaperTrade(
            stock_id=result.stock_id,
            side=TradeSide.SELL.value,
            quantity=quantity,
            limit_price=None,
            fill_price=fill_price,
            fill_quantity=quantity,
            status=TradeStatus.FILLED.value,
            ranking_run_id=ranking_run_id,
            idempotency_key=idem_key,
            requested_at=datetime(fill_date.year, fill_date.month, fill_date.day, 15, 0, tzinfo=UTC),
            filled_at=datetime(fill_date.year, fill_date.month, fill_date.day, 15, 0, tzinfo=UTC),
            metadata_={
                "recommendation_result_id": str(recommendation_result_id),
                "recommendation_run_id": str(result.recommendation_run_id),
                "exit_reason_codes": result.reason_codes,
                "last_close": last_close,
                "slippage_bps": 5.0,
                **self._fill_meta(),
            },
        )
        self.db.add(trade)
        self.db.flush()

        # Close portfolio position
        if pos:
            self.portfolio_service.close_position(
                result.stock_id, exit_price=fill_price, exit_date=fill_date
            )

        # Cash ledger: capital in (sale proceeds) - fee
        proceeds = quantity * fill_price
        fee = self._leg_cost(proceeds, "SELL")  # P-24: full cost stack when enabled
        self.nav_service.record_cash_entry(
            entry_type="TRADE_SELL",
            amount=proceeds,
            as_of_date=fill_date,
            reference_id=trade.id,
            reference_type="paper_trade",
            description=f"SELL {quantity} @ {fill_price}",
        )
        if fee:
            self.nav_service.record_cash_entry(
                entry_type="FEE",
                amount=-fee,
                as_of_date=fill_date,
                reference_id=trade.id,
                reference_type="paper_trade",
                description="Exit fee",
            )

        # Update RecommendationOutcome
        outcome = self.db.scalar(
            select(RecommendationOutcome).where(
                RecommendationOutcome.recommendation_result_id == recommendation_result_id
            )
        )
        if outcome:
            entry = (
                float(outcome.entry_price)
                if outcome.entry_price
                else float(pos.avg_cost if pos else 0)
            )
            benchmark_return = self._holding_benchmark_return(
                outcome.entry_date, fill_date
            )
            pnl_pct = ((fill_price - entry) / entry * 100) if entry else 0
            days = (fill_date - outcome.entry_date).days if outcome.entry_date else 0

            outcome.exit_date = fill_date
            outcome.exit_price = fill_price
            outcome.days_held = days
            outcome.pnl_pct = round(pnl_pct, 4)
            outcome.benchmark_return_pct = round(benchmark_return, 4) if benchmark_return else None
            outcome.alpha_pct = (
                round(pnl_pct - benchmark_return, 4) if benchmark_return is not None else None
            )
            outcome.exit_reason_codes = result.reason_codes
            outcome.outcome_status = (
                "WIN" if pnl_pct > 0 else ("LOSS" if pnl_pct < 0 else "BREAKEVEN")
            )

        result.lifecycle_state = "CLOSED"
        self.db.flush()
        return trade

    def execute_position_exit(
        self,
        *,
        stock_id: UUID,
        as_of_date: date,
        exit_triggers: list[str] | None = None,
        portfolio_exit_recommendation_id: UUID | None = None,
        idempotency_key: str | None = None,
    ) -> PaperTrade:
        """Simulate SELL fill for backtest/paper pilot from exit-monitor (no EXIT_APPROVED rec)."""
        from app.models.portfolio_position import PortfolioPosition

        idem_key = idempotency_key or (
            f"exit-monitor:{portfolio_exit_recommendation_id}"
            if portfolio_exit_recommendation_id
            else self._make_idem_key("exit-pos", stock_id)
        )
        existing = self.db.scalar(select(PaperTrade).where(PaperTrade.idempotency_key == idem_key))
        if existing:
            return existing

        pos = self.db.scalar(
            select(PortfolioPosition).where(
                PortfolioPosition.stock_id == stock_id,
                PortfolioPosition.is_current.is_(True),
                PortfolioPosition.position_status == "OPEN",
            )
        )
        if pos is None:
            raise ValueError(f"No open position for stock {stock_id}")

        fill_date = as_of_date
        # Position is known here → pass notional so the realistic-fill impact model
        # scales by participation (order size vs ADV). No-op when realistic fills off.
        _ov = float(pos.quantity) * float(pos.avg_cost) if pos and pos.avg_cost else None
        fill_price, last_close = self._fill_price(stock_id, fill_date, side="SELL", order_value=_ov)
        quantity = float(pos.quantity)

        primary_trigger = _primary_exit_reason(exit_triggers)

        # ADR-033 restoration: cap a stop-loss exit at the regime advisory stop level.
        # A daily backtest has no ticks, so model the hard stop the standard way — if
        # the day's LOW breached the advisory stop, the realised fill is the stop level
        # (intraday slide), or the day's open if the stock gapped below it. Without this,
        # an intraday slide to -13% by the close was booked at the close instead of the
        # -6%/-8% stop the system was designed to honour.
        if primary_trigger == "EXIT_STOP_LOSS" and pos.avg_cost:
            capped = self._stop_capped_fill(stock_id, fill_date, float(pos.avg_cost))
            if capped is not None:
                fill_price = capped

        trade = PaperTrade(
            stock_id=stock_id,
            side=TradeSide.SELL.value,
            quantity=quantity,
            limit_price=None,
            fill_price=fill_price,
            fill_quantity=quantity,
            status=TradeStatus.FILLED.value,
            ranking_run_id=None,
            idempotency_key=idem_key,
            requested_at=datetime(fill_date.year, fill_date.month, fill_date.day, 15, 0, tzinfo=UTC),
            filled_at=datetime(fill_date.year, fill_date.month, fill_date.day, 15, 0, tzinfo=UTC),
            metadata_={
                "portfolio_exit_recommendation_id": (
                    str(portfolio_exit_recommendation_id) if portfolio_exit_recommendation_id else None
                ),
                "exit_triggers": exit_triggers or [],
                "recommendation_result_id": (
                    str(pos.recommendation_result_id) if pos.recommendation_result_id else None
                ),
                "last_close": last_close,
                "slippage_bps": 5.0,
                **self._fill_meta(),
            },
        )
        self.db.add(trade)
        self.db.flush()

        self.portfolio_service.close_position(
            stock_id, exit_price=fill_price, exit_date=fill_date, exit_reason=primary_trigger
        )

        proceeds = quantity * fill_price
        fee = self._leg_cost(proceeds, "SELL")  # P-24: full cost stack when enabled
        self.nav_service.record_cash_entry(
            entry_type="TRADE_SELL",
            amount=proceeds,
            as_of_date=fill_date,
            reference_id=trade.id,
            reference_type="paper_trade",
            description=f"SELL {quantity} @ {fill_price}",
        )
        if fee:
            self.nav_service.record_cash_entry(
                entry_type="FEE",
                amount=-fee,
                as_of_date=fill_date,
                reference_id=trade.id,
                reference_type="paper_trade",
                description="Exit fee",
            )

        if pos.recommendation_result_id:
            result = self.db.get(RecommendationResult, pos.recommendation_result_id)
            outcome = self.db.scalar(
                select(RecommendationOutcome).where(
                    RecommendationOutcome.recommendation_result_id == pos.recommendation_result_id
                )
            )
            if outcome:
                entry = (
                    float(outcome.entry_price)
                    if outcome.entry_price
                    else float(pos.avg_cost)
                )
                benchmark_return = self._holding_benchmark_return(outcome.entry_date, fill_date)
                pnl_pct = ((fill_price - entry) / entry * 100) if entry else 0
                days = (fill_date - outcome.entry_date).days if outcome.entry_date else 0
                outcome.exit_date = fill_date
                outcome.exit_price = fill_price
                outcome.days_held = days
                outcome.pnl_pct = round(pnl_pct, 4)
                outcome.benchmark_return_pct = (
                    round(benchmark_return, 4) if benchmark_return is not None else None
                )
                outcome.alpha_pct = (
                    round(pnl_pct - benchmark_return, 4)
                    if benchmark_return is not None
                    else None
                )
                outcome.exit_reason_codes = exit_triggers or []
                outcome.outcome_status = (
                    "WIN" if pnl_pct > 0 else ("LOSS" if pnl_pct < 0 else "BREAKEVEN")
                )
            if result:
                result.lifecycle_state = "CLOSED"

        self.db.flush()
        return trade

    def _fill_price(
        self,
        stock_id: UUID,
        fill_date: date,
        side: str,
        order_value: float | None = None,
        entry_low: float | None = None,
        entry_high: float | None = None,
    ) -> tuple[float, float]:
        """Return (fill_price_with_slippage, ref_price).

        Default: fills at ``fill_date``'s close (same-bar).
        Execution-realism (``next_open_fills_enabled``): the decision is made on the
        fill_date close, but the order can only execute on the NEXT trading day's OPEN —
        removing the same-bar look-ahead (you can't observe the close and trade at it).
        Realistic fills (``realistic_fills_enabled``): fill at the next session's
        intraday VWAP with a size-vs-ADV market-impact cost (``order_value`` drives the
        participation). Falls back to next-open/close when intraday data is missing.
        Falls back to the close fill when there is no next bar (e.g. the final day).
        """
        self._last_fill_quote = None

        # Entry-band LIMIT fill (price-tag): a BUY is a limit on the rec's band. Fill at
        # the lowest of D+1's O/H/L/C that lands IN the band; else (gap-down/straddle —
        # gap-up is gated upstream in the pilot) at min(open, entry_high). No extra
        # slippage — the band dispersion IS the cost model.
        if (side == "BUY" and self.settings.entry_band_fills_enabled
                and entry_low is not None and entry_high is not None):
            nxt = self.market_data_repo.get_first_bar_after(stock_id, fill_date)
            if nxt is not None and nxt.open is not None:
                o = float(nxt.open)
                prices = [o,
                          float(nxt.high) if nxt.high is not None else o,
                          float(nxt.low) if nxt.low is not None else o,
                          float(nxt.close) if nxt.close is not None else o]
                in_band = [p for p in prices if entry_low <= p <= entry_high]
                ref = min(in_band) if in_band else min(o, float(entry_high))
                return round(ref, 4), ref

        if self.settings.ohlc_fills_enabled:
            # Smarter daily-OHLC fill: execute on the NEXT session (no same-bar look-
            # ahead) at a gap-robust typical price — median(open, (high+low)/2,
            # (open+close)/2). The OHLC dispersion stands in for slippage; none is added.
            # (Stop/trailing exits fill at their trigger via _stop_capped_fill.)
            import statistics
            nxt = self.market_data_repo.get_first_bar_after(stock_id, fill_date)
            if nxt is None or nxt.open is None:   # final day → last close on/before fill_date
                _b = self.market_data_repo.get_by_stock_and_date_range(
                    stock_id, end_date=fill_date, limit=1)
                if not _b:
                    raise ValueError(f"No market data for stock {stock_id} on or before {fill_date}")
                _c = float(_b[0].close)
                return round(_c, 4), _c
            o = float(nxt.open)
            h = float(nxt.high) if nxt.high is not None else o
            l = float(nxt.low) if nxt.low is not None else o
            c = float(nxt.close) if nxt.close is not None else o
            fill = statistics.median([o, (h + l) / 2.0, (o + c) / 2.0])
            return round(fill, 4), o

        if self.settings.realistic_fills_enabled:
            from app.services.intraday_fill_service import IntradayFillService

            quote = IntradayFillService(self.db, self.settings).resolve_fill(
                stock_id, fill_date, side, order_value=order_value
            )
            if quote is not None:
                self._last_fill_quote = quote
                return quote.fill_price, quote.ref_price

        slip = self.settings.cost_slippage_bps / 10_000.0  # configurable (default 5 bps)
        slippage_factor = (1.0 + slip) if side == "BUY" else (1.0 - slip)

        if self.settings.next_open_fills_enabled:
            nxt = self.market_data_repo.get_first_bar_after(stock_id, fill_date)
            if nxt is not None and nxt.open is not None:
                ref = float(nxt.open)
                return round(ref * slippage_factor, 4), ref

        bars = self.market_data_repo.get_by_stock_and_date_range(
            stock_id, end_date=fill_date, limit=1
        )
        if not bars:
            raise ValueError(f"No market data for stock {stock_id} on or before {fill_date}")
        last_close = float(bars[0].close)
        return round(last_close * slippage_factor, 4), last_close

    def _stop_capped_fill(
        self, stock_id: UUID, fill_date: date, avg_cost: float
    ) -> float | None:
        """Stop-loss fill capped at the regime advisory stop level (ADR-033).

        If the day's LOW breached the advisory stop, the realised fill is the stop
        level (intraday slide) or the day's open if it gapped below (a gap can't fill
        better than the open). Returns None if the stop wasn't breached this day or
        data is missing — caller then keeps the normal close-based fill.
        """
        from app.db.repositories.regime_analytics_repository import RegimeAnalyticsRepository
        from app.portfolio.regime_stops import resolve_stop_pcts

        advisory_pct, _ = resolve_stop_pcts(
            RegimeAnalyticsRepository(self.db), as_of=fill_date, settings=self.settings
        )
        stop_level = avg_cost * (1 + advisory_pct / 100.0)
        bars = self.market_data_repo.get_by_stock_and_date_range(
            stock_id, end_date=fill_date, limit=1
        )
        if not bars or bars[0].low is None or bars[0].open is None:
            return None
        day_low = float(bars[0].low)
        day_open = float(bars[0].open)
        if day_low > stop_level:
            return None  # stop not breached intraday — keep normal fill
        fill = min(day_open, stop_level)  # slide → stop level; gap → open
        # OHLC fills: the stop level IS the fill (no slippage add-on).
        slip = 0.0 if self.settings.ohlc_fills_enabled else self.settings.cost_slippage_bps / 10_000.0
        return round(fill * (1.0 - slip), 4)    # sell slippage

    def _make_idem_key(self, action: str, result_id: UUID) -> str:
        raw = f"{action}:{result_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def _holding_benchmark_return(self, entry_date: date, exit_date: date) -> float | None:
        """Cumulative ^NSEI return over holding period (read-only market data)."""
        try:
            from app.models.stock import Stock

            stock = self.db.scalar(
                select(Stock).where(Stock.symbol == DEFAULT_BENCHMARK_SYMBOL)
            )
            if stock is None:
                return None
            bars = self.market_data_repo.get_by_stock_and_date_range(
                stock.id, end_date=exit_date, limit=400
            )
            if not bars:
                return None
            by_date = {b.trading_date: float(b.close) for b in bars}
            entry_close = by_date.get(entry_date)
            exit_close = by_date.get(exit_date)
            if entry_close is None or exit_close is None or entry_close <= 0:
                return None
            return (exit_close - entry_close) / entry_close * 100
        except Exception:
            return None
