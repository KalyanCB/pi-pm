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
        fill_price, last_close = self._fill_price(result.stock_id, fill_date, side="BUY")

        # Compute quantity from portfolio allocation
        try:
            alloc = self.portfolio_service.compute_allocation(
                conviction_band=result.conviction_band or "MEDIUM",
                last_price=last_close,
            )
            quantity = max(1.0, alloc.quantity_estimate)
        except Exception:
            quantity = 1.0

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
        fee = self._fee()
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
        fee = self._fee()
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
        fill_price, last_close = self._fill_price(stock_id, fill_date, side="SELL")
        quantity = float(pos.quantity)

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
            },
        )
        self.db.add(trade)
        self.db.flush()

        self.portfolio_service.close_position(stock_id, exit_price=fill_price, exit_date=fill_date)

        proceeds = quantity * fill_price
        fee = self._fee()
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

    def _fill_price(self, stock_id: UUID, fill_date: date, side: str) -> tuple[float, float]:
        """Return (fill_price_with_slippage, last_close) on or before fill_date."""
        bars = self.market_data_repo.get_by_stock_and_date_range(
            stock_id, end_date=fill_date, limit=1
        )
        if not bars:
            raise ValueError(f"No market data for stock {stock_id} on or before {fill_date}")
        last_close = float(bars[0].close)
        slippage_factor = 1.0005 if side == "BUY" else 0.9995  # 5 bps
        return round(last_close * slippage_factor, 4), last_close

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
