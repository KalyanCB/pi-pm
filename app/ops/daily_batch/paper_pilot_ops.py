"""Paper-trading pilot orchestration for daily batch.

Orchestrates portfolio ops only — does not modify ranking, validation,
recommendation generation, conviction, or committee logic.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import RecommendationAction
from app.models.portfolio_analytics import ExitRecommendation, PortfolioNavHistory
from app.models.portfolio_position import PortfolioPosition
from app.models.recommendation import RecommendationResult, RecommendationRun
from app.recommendation.rank_bucket_expectancy import RankBucketExpectancyProvider
from app.recommendation.trade_prioritizer import TradeCandidate, prioritize
from app.portfolio.exit_monitor.service import ExitMonitorService
from app.portfolio.reconciliation.service import ReconciliationService
from app.execution.services.execution_service import ExecutionService
from app.models.recommendation import RecommendationApproval
from app.services.paper_trade_service import PaperTradeService
from app.services.portfolio_nav_service import PortfolioNavService
from app.services.portfolio_service import PortfolioService
from app.services.recommendation_service import RecommendationService

DEFAULT_PORTFOLIO_ID = UUID("00000000-0000-4000-8000-000000000010")


class PaperPilotOps:
    def __init__(
        self,
        db: Session,
        *,
        portfolio_service: PortfolioService | None = None,
        nav_service: PortfolioNavService | None = None,
        reconciliation_service: ReconciliationService | None = None,
        exit_monitor: ExitMonitorService | None = None,
        paper_trade_service: PaperTradeService | None = None,
        recommendation_service: RecommendationService | None = None,
        execution_service: ExecutionService | None = None,
    ) -> None:
        self.db = db
        self.portfolio_service = portfolio_service or PortfolioService(
            db, portfolio_id=DEFAULT_PORTFOLIO_ID
        )
        self.nav_service = nav_service or PortfolioNavService(db)
        self.reconciliation_service = reconciliation_service or ReconciliationService(db)
        self.exit_monitor = exit_monitor or ExitMonitorService(db)
        self.paper_trade_service = paper_trade_service or PaperTradeService(
            db, portfolio_service=self.portfolio_service
        )
        self.recommendation_service = recommendation_service or RecommendationService(db)
        self.execution_service = execution_service or ExecutionService(
            db, portfolio_id=DEFAULT_PORTFOLIO_ID
        )
        self._pilot_actor_id = UUID("00000000-0000-4000-8000-000000000001")

    def run(
        self,
        as_of_date: date,
        *,
        recompute: bool = True,
        exit_monitor: bool = True,
        paper_trading: bool = True,
        nav_snapshot: bool = True,
        reconcile: bool = True,
        pilot_auto_approve: bool = False,
        pilot_auto_execute: bool = False,
    ) -> dict:
        results: dict = {}

        if recompute:
            results["recompute"] = self.portfolio_service.recompute(as_of_date)

        if exit_monitor:
            exit_recs = self.exit_monitor.run(as_of_date)
            results["exit_monitor"] = {
                "candidates": len(exit_recs),
                "ids": [str(r.id) for r in exit_recs],
            }

        if paper_trading and pilot_auto_execute:
            results["paper_trading"] = self._execute_pilot_trades(
                as_of_date,
                pilot_auto_approve=pilot_auto_approve,
            )

        if nav_snapshot:
            nav = self.nav_service.snapshot(as_of_date)
            results["nav_snapshot"] = {
                "nav_id": str(nav.id),
                "total_equity": float(nav.total_equity),
                "cash_pct": float(nav.cash_pct),
                "open_positions": nav.open_positions,
            }

        if reconcile:
            try:
                report = self.reconciliation_service.run(as_of_date)
                results["reconcile"] = {
                    "report_id": str(report.id),
                    "status": report.status,
                    "discrepancy_pct": float(report.discrepancy_pct),
                }
            except Exception as exc:
                self.db.rollback()
                results["reconcile"] = {"status": "ERROR", "error": str(exc)}

        return results

    # ── ADR-037 v18 P-22: defensive gold rotation (flag-gated) ───────────────

    def _gold_rotation(self, as_of_date: date, regime_label: str) -> dict | None:
        """In BEAR regimes deploy the defensive sleeve to GOLDBEES instead of cash;
        sell it when the regime is no longer bear. Gold is a non-universe instrument
        (strategy_name='gold_rotation') so it never interacts with the equity ranking.
        """
        from app.core.config import get_settings
        from sqlalchemy import text as _text
        s = get_settings()
        if not s.gold_rotation_enabled:
            return None
        gold = self.db.execute(_text("SELECT id FROM stocks WHERE symbol=:sym"),
                               {"sym": s.gold_symbol}).fetchone()
        if not gold:
            return {"status": "no_gold_data"}
        gold_id = gold[0]
        px = self.db.execute(_text(
            "SELECT close FROM market_data WHERE stock_id=:s AND date<=:d ORDER BY date DESC LIMIT 1"
        ), {"s": gold_id, "d": as_of_date}).scalar()
        if not px:
            return {"status": "no_gold_price"}
        px = float(px)

        held = self.db.scalar(select(PortfolioPosition).where(
            PortfolioPosition.stock_id == gold_id,
            PortfolioPosition.is_current.is_(True),
            PortfolioPosition.position_status == "OPEN",
        ))
        is_bear = regime_label.upper().startswith("BEAR")
        cash = self.nav_service.cash_balance()

        # fast_deploy: demand-driven dynamic-band sleeve (rides winners, yields to
        # buys, 25-50% band, buy-cooldown to curb gold churn).
        if s.fast_deploy_enabled:
            return self._gold_rotation_dynamic(as_of_date, gold_id, px, held, cash, regime_label, s)

        def _sell(reason: str) -> dict:
            fill = round(px * 0.9995, 4)
            qty = float(held.quantity)
            self.portfolio_service.close_position(
                gold_id, exit_price=fill, exit_date=as_of_date, exit_reason=reason)
            self.nav_service.record_cash_entry(
                entry_type="TRADE_SELL", amount=qty * fill, as_of_date=as_of_date,
                reference_type="gold_rotation", description=f"{reason} {qty} @ {fill}")
            return {"action": reason, "qty": qty, "price": fill}

        # NON-BEAR: ride if winning, cut only if losing (underwater vs avg cost).
        if not is_bear:
            if held is None:
                return {"action": "none", "is_bear": False}
            if px < float(held.entry_price):          # underwater → cut the loser
                return _sell("GOLD_LOSS_EXIT")
            return {"action": "GOLD_HOLD_RIDE",       # in profit → let it ride into bull
                    "unreal_pct": round((px / float(held.entry_price) - 1) * 100, 1)}

        # BEAR: slots take ABSOLUTE priority. Reserve cash for any open stock slots
        # (slots_available × single-name cap × equity); gold may only use the surplus.
        cfg = self.portfolio_service.get_config()
        total_equity = float(cfg.total_equity) if cfg else 0.0
        cap = float(cfg.single_name_cap_pct) if cfg and cfg.single_name_cap_pct else 0.18
        limits = self.portfolio_service.get_limits(as_of_date)
        reserve = limits.slots_available * cap * total_equity

        # Open stock slots need cash that's parked in gold → yield: sell gold to fund them.
        if held is not None and cash < reserve:
            return _sell("GOLD_YIELD_SLOTS")

        # Deploy gold_alloc_pct (80%) of the surplus cash beyond the slot reserve.
        if held is None:
            deployable = max(0.0, cash - reserve)
            budget = deployable * s.gold_alloc_pct
            qty = int(budget / px)
            if qty <= 0:
                return {"action": "hold", "cash": round(cash), "reserve": round(reserve)}
            fill = round(px * 1.0005, 4)  # 5bps slippage
            self.portfolio_service.open_position(
                stock_id=gold_id, quantity=qty, fill_price=fill,
                entry_date=as_of_date, strategy_name="gold_rotation", sector="ETF",
            )
            self.nav_service.record_cash_entry(
                entry_type="TRADE_BUY", amount=-(qty * fill), as_of_date=as_of_date,
                reference_type="gold_rotation", description=f"GOLD BUY {qty} @ {fill}")
            return {"action": "GOLD_BUY", "qty": qty, "price": fill}

        return {"action": "GOLD_HOLD_BEAR", "cash": round(cash), "reserve": round(reserve)}

    def _gold_rotation_dynamic(
        self, as_of_date, gold_id, px, held, cash, regime_label, s
    ) -> dict:
        """fast_deploy gold sleeve: demand-driven dynamic band (% of total portfolio).
        Stock slots have absolute priority. Gold rides winners (no auto-sell on a
        regime flip), yields cash to stock BUYS (bull: fully; bear: down to the 25%
        floor), soaks idle cash up to the 50% ceiling, cuts losers, and a buy-cooldown
        stops the buy-yield-rebuy thrash.
        """
        from sqlalchemy import text as _text

        cfg = self.portfolio_service.get_config()
        total_equity = float(cfg.total_equity) if cfg else 0.0
        is_bear = regime_label.upper().startswith("BEAR")
        gold_val = float(held.quantity) * px if held else 0.0
        # Cash the stock slots still want = regime DEPLOY CEILING (fast_deploy-aware)
        # minus what stocks already hold. NOT slots_available × single-name-cap — that
        # over-reserved (e.g. BEAR_HIGH_VOL: 4 slots × 18% = 72% phantom-reserved for
        # stocks that won't be bought at a 0% ceiling, starving gold of idle cash).
        summary = self.portfolio_service.get_summary(as_of_date)
        stock_value = max(0.0, float(summary.market_value) - gold_val)
        slot_reserve = max(0.0, float(summary.deployable_capital) - stock_value)
        floor = s.gold_min_pct * total_equity
        ceil = s.gold_max_pct * total_equity

        def _sell(qty: float, reason: str) -> dict:
            qty = min(qty, float(held.quantity))
            fill = round(px * 0.9995, 4)
            if qty >= float(held.quantity) - 1e-9:
                self.portfolio_service.close_position(
                    gold_id, exit_price=fill, exit_date=as_of_date, exit_reason=reason)
            else:
                held.quantity = float(held.quantity) - qty   # partial yield
                self.db.flush()
            self.nav_service.record_cash_entry(
                entry_type="TRADE_SELL", amount=qty * fill, as_of_date=as_of_date,
                reference_type="gold_rotation", description=f"{reason} {qty:.0f} @ {fill}")
            return {"action": reason, "qty": qty, "price": fill}

        # cut losers (bull only — in bear the band holds through MTM dips)
        if held is not None and not is_bear and px < float(held.entry_price):
            return _sell(float(held.quantity), "GOLD_LOSS_EXIT")

        # YIELD to stock buys: slots need cash → release gold (bull: all; bear: to floor)
        if held is not None and cash < slot_reserve:
            need = slot_reserve - cash
            sellable = gold_val if not is_bear else max(0.0, gold_val - floor)
            qty = int(min(need, sellable) / px)
            if qty > 0:
                return _sell(qty, "GOLD_YIELD_SLOTS")

        if not is_bear:
            if held is None:
                return {"action": "none", "is_bear": False}
            return {"action": "GOLD_HOLD_RIDE",
                    "unreal_pct": round((px / float(held.entry_price) - 1) * 100, 1)}

        # BEAR: size gold to the band from idle cash, once, cooldown-gated.
        if held is not None:
            return {"action": "GOLD_HOLD_BEAR", "gold_val": round(gold_val)}
        idle = max(0.0, cash - slot_reserve)
        if idle < floor:                       # not enough idle to meet the 25% floor
            return {"action": "hold", "idle": round(idle)}
        last = self.db.execute(_text(
            "SELECT max(as_of_date) FROM portfolio_cash_ledger WHERE reference_type='gold_rotation'"
        )).scalar()
        if last is not None and (as_of_date - last).days < s.gold_buy_cooldown_days:
            return {"action": "GOLD_COOLDOWN", "last": str(last)}
        budget = min(ceil, idle)               # soak idle cash up to the 50% ceiling
        qty = int(budget / px)
        if qty <= 0:
            return {"action": "hold"}
        fill = round(px * 1.0005, 4)
        self.portfolio_service.open_position(
            stock_id=gold_id, quantity=qty, fill_price=fill,
            entry_date=as_of_date, strategy_name="gold_rotation", sector="ETF")
        self.nav_service.record_cash_entry(
            entry_type="TRADE_BUY", amount=-(qty * fill), as_of_date=as_of_date,
            reference_type="gold_rotation", description=f"GOLD BUY {qty} @ {fill}")
        return {"action": "GOLD_BUY", "qty": qty, "price": fill, "budget": round(budget)}

    def _raise_cash_from_gold(self, need: float, as_of_date: date, regime_label: str) -> float:
        """Sell GOLD to fund a stock buy when cash is short. Returns cash raised.

        Funding waterfall (per-trade): bull → gold is fully sellable; bear → only the
        amount ABOVE the 25% gold floor (gold_min_pct*equity) may be sold, keeping the
        bear hedge intact. No-op if gold is disabled / not held / already at the floor.
        """
        from app.core.config import get_settings
        from sqlalchemy import text as _text
        s = get_settings()
        if need <= 0 or not s.gold_rotation_enabled:
            return 0.0
        gold = self.db.execute(_text("SELECT id FROM stocks WHERE symbol=:sym"),
                               {"sym": s.gold_symbol}).fetchone()
        if not gold:
            return 0.0
        gold_id = gold[0]
        held = self.db.scalar(select(PortfolioPosition).where(
            PortfolioPosition.stock_id == gold_id,
            PortfolioPosition.is_current.is_(True),
            PortfolioPosition.position_status == "OPEN"))
        if held is None:
            return 0.0
        px = self.db.execute(_text(
            "SELECT close FROM market_data WHERE stock_id=:s AND date<=:d ORDER BY date DESC LIMIT 1"),
            {"s": gold_id, "d": as_of_date}).scalar()
        if not px:
            return 0.0
        fill = round(float(px) * 0.9995, 4)        # 5bps sell slippage (matches sleeve)
        is_bear = regime_label.upper().startswith("BEAR")
        cfg = self.portfolio_service.get_config()
        equity = float(cfg.total_equity) if cfg else 0.0
        floor = (s.gold_min_pct * equity) if is_bear else 0.0
        gold_val = float(held.quantity) * fill
        sellable_val = max(0.0, gold_val - floor)
        if sellable_val <= 0:
            return 0.0
        # Sell just enough to cover `need` (+1 unit for rounding), capped at the floor.
        qty = min(int(need / fill) + 1, int(sellable_val / fill))
        if qty <= 0:
            return 0.0
        proceeds = qty * fill
        if qty >= float(held.quantity) - 1e-9:
            self.portfolio_service.close_position(
                gold_id, exit_price=fill, exit_date=as_of_date, exit_reason="GOLD_YIELD_BUY")
        else:
            held.quantity = float(held.quantity) - qty
            self.db.flush()
        self.nav_service.record_cash_entry(
            entry_type="TRADE_SELL", amount=proceeds, as_of_date=as_of_date,
            reference_type="gold_rotation", description=f"GOLD_YIELD_BUY {qty} @ {fill}")
        return proceeds

    # ── P-21 Trade Decision Layer ────────────────────────────────────────────

    def _get_expectancy_provider(self, as_of_date: date) -> RankBucketExpectancyProvider:
        """Cached rank-bucketed expectancy. Rebuilt quarterly (expectancy is slow-
        moving and the build is a heavy historical aggregation — avoid per-day cost)."""
        built_for = getattr(self, "_expectancy_built_for", None)
        if built_for is None or (as_of_date - built_for).days >= 63:
            self._expectancy_provider = RankBucketExpectancyProvider.build(
                self.db, as_of_date=as_of_date
            )
            self._expectancy_built_for = as_of_date
        return self._expectancy_provider

    def _market_context(self, as_of_date: date) -> tuple[float | None, float | None]:
        """(P-14 breadth, P-13 synthetic-universe 20-day mean return) in one query
        over the traded universe. Both are absolute market signals the NIFTY-50
        regime cannot see. Returns (None, None) at cold start (<50 stocks)."""
        from sqlalchemy import text as _text
        row = self.db.execute(_text("""
            WITH recent AS (
                SELECT stock_id, close,
                       ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
                FROM market_data WHERE source = 'kite' AND date <= :d
            ),
            per_stock AS (
                SELECT stock_id,
                       MAX(close) FILTER (WHERE rn = 1)  AS last_close,
                       AVG(close) FILTER (WHERE rn <= 50) AS sma50,
                       MAX(close) FILTER (WHERE rn = 20) AS close_20d,
                       COUNT(*) AS bars
                FROM recent WHERE rn <= 50 GROUP BY stock_id
            )
            SELECT
                COUNT(*) FILTER (WHERE bars >= 50) AS n,
                AVG(CASE WHEN last_close > sma50 THEN 1.0 ELSE 0.0 END)
                    FILTER (WHERE bars >= 50) AS breadth,
                AVG((last_close - close_20d) / close_20d)
                    FILTER (WHERE bars >= 50 AND close_20d > 0) AS universe_ret20
            FROM per_stock
        """), {"d": as_of_date}).fetchone()
        if row is None or row.n is None or row.n < 50:
            return None, None
        breadth = float(row.breadth) if row.breadth is not None else None
        uret = float(row.universe_ret20) if row.universe_ret20 is not None else None
        return breadth, uret

    def _prioritize_entries(
        self,
        fresh_recs: list,
        active_strategy: str,
        regime_label: str,
        as_of_date: date,
    ) -> list:
        """Order BUY candidates by expected value (P-21), with per-stock trend
        eligibility. Returns RecommendationResult objects in execution order.
        Falls back to conviction ordering when expectancy is thin (cold start)."""
        if not fresh_recs:
            return []

        # Batch trend/volume context for all candidate stocks in one query.
        # close_20d (rn=20) supports the P-13 synthetic relative-strength check.
        from sqlalchemy import text as _text
        sids = [r.stock_id for r in fresh_recs]
        ctx_rows = self.db.execute(_text("""
            WITH recent AS (
                SELECT stock_id, close, volume,
                       ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY date DESC) AS rn
                FROM market_data
                WHERE stock_id = ANY(:sids) AND source = 'kite' AND date <= :d
            )
            SELECT stock_id,
                   MAX(close)  FILTER (WHERE rn = 1)  AS last_price,
                   AVG(close)  FILTER (WHERE rn <= 50) AS sma50,
                   MAX(close)  FILTER (WHERE rn = 20) AS close_20d,
                   MAX(volume) FILTER (WHERE rn = 1)  AS vol_today,
                   AVG(volume) FILTER (WHERE rn <= 90) AS vol_avg90,
                   AVG(close * volume) FILTER (WHERE rn <= 90) AS adv_value
            FROM recent WHERE rn <= 90 GROUP BY stock_id
        """), {"sids": sids, "d": as_of_date}).fetchall()
        ctx = {r.stock_id: r for r in ctx_rows}

        # P-14 breadth + P-13 synthetic universe benchmark (equal-weight 20-day mean
        # return) — one universe-wide query, the absolute market/segment context the
        # NIFTY-50 regime cannot see (the 2024-H1 failure mode).
        breadth_pct, universe_ret20 = self._market_context(as_of_date)

        provider = self._get_expectancy_provider(as_of_date)

        # Trend-following strategies require uptrend + volume + positive RS.
        # Mean-reversion strategies (reversal_v1, low_vol_v1) intentionally buy
        # oversold/quiet names *below* their 50-SMA and underperforming peers — those
        # gates must NOT apply to them, or they would veto every legitimate entry.
        _trend_following = active_strategy in ("breakout_v1", "momentum_v1")

        candidates: list[TradeCandidate] = []
        rec_by_id = {}
        for rec in fresh_recs:
            row = ctx.get(rec.stock_id)
            rec_by_id[rec.id] = rec
            # P-13 synthetic RS: stock 20-day return minus universe 20-day return.
            rs = None
            if (_trend_following and row and row.last_price is not None
                    and row.close_20d is not None and float(row.close_20d) > 0
                    and universe_ret20 is not None):
                stock_ret20 = (float(row.last_price) - float(row.close_20d)) / float(row.close_20d)
                rs = stock_ret20 - universe_ret20
            candidates.append(TradeCandidate(
                stock_id=rec.stock_id,
                symbol=str(rec.stock_id),
                strategy_name=active_strategy,
                rank=int(rec.rank) if rec.rank is not None else 999,
                conviction_score=float(rec.conviction_score or 0.0),
                market_regime=regime_label,
                recommendation_id=rec.id,
                last_price=float(row.last_price) if row and row.last_price is not None else None,
                sma50=float(row.sma50) if row and row.sma50 is not None else None,
                segment_state="UNKNOWN",  # true segment-index state needs P-13 index ingest
                volume_today=(float(row.vol_today)
                              if _trend_following and row and row.vol_today is not None else None),
                volume_avg90=(float(row.vol_avg90)
                              if _trend_following and row and row.vol_avg90 is not None else None),
                rs_vs_universe=rs,
                adv_value=(float(row.adv_value)
                           if row and row.adv_value is not None else None),
            ))

        # Breadth gate applies market-wide only to trend-following entries (mean-
        # reversion is designed to buy weak tape); pass None for reversal/low_vol.
        _breadth = breadth_pct if _trend_following else None
        ordered = prioritize(
            candidates, provider,
            breadth_pct=_breadth,
            require_uptrend=_trend_following,
        )
        # Map prioritized queue back to RecommendationResult objects, preserving order.
        return [rec_by_id[pc.candidate.recommendation_id] for pc in ordered]

    def _execute_pilot_trades(
        self,
        as_of_date: date,
        *,
        pilot_auto_approve: bool,
    ) -> dict:
        entries: list[str] = []
        exits: list[str] = []
        skipped: list[dict] = []

        limits = self.portfolio_service.get_limits(as_of_date)

        # Exits first — only when pilot_auto_execute; otherwise exit_monitor.run() leaves PENDING for UI.
        monitor_exits = self.db.scalars(
            select(ExitRecommendation).where(
                ExitRecommendation.as_of_date == as_of_date,
                ExitRecommendation.status == "PENDING",
            )
        ).all()
        for exit_rec in monitor_exits:
            pos = self.db.get(PortfolioPosition, exit_rec.portfolio_position_id)
            if pos is None or pos.position_status != "OPEN" or not pos.is_current:
                continue
            try:
                trade = self.paper_trade_service.execute_position_exit(
                    stock_id=exit_rec.stock_id,
                    as_of_date=as_of_date,
                    exit_triggers=list(exit_rec.triggers or []),
                    portfolio_exit_recommendation_id=exit_rec.id,
                    idempotency_key=f"pilot-exit-monitor:{exit_rec.id}",
                )
                self.exit_monitor.confirm(exit_rec.id)
                exits.append(str(trade.id))
            except Exception as exc:
                skipped.append({
                    "exit_recommendation_id": str(exit_rec.id),
                    "action": "exit_monitor",
                    "error": str(exc),
                })

        # EXIT_APPROVED recommendation rows (engine path, when present)
        exit_candidates = self.db.scalars(
            select(RecommendationResult).where(
                RecommendationResult.action == RecommendationAction.EXIT_APPROVED.value,
            )
        ).all()
        for rec in exit_candidates:
            pos = self.db.scalar(
                select(PortfolioPosition).where(
                    PortfolioPosition.stock_id == rec.stock_id,
                    PortfolioPosition.is_current.is_(True),
                    PortfolioPosition.position_status == "OPEN",
                )
            )
            if pos is None:
                continue
            try:
                approval_id = self._latest_approval_id(rec.id)
                if approval_id is None:
                    self.recommendation_service.approve(
                        rec.id,
                        approval_type="EXIT",
                        decision="APPROVED",
                        actor_id="paper_pilot",
                        note="Auto-approved exit for paper pilot",
                        idempotency_key=f"pilot-approve-exit:{rec.id}",
                    )
                    approval_id = self._latest_approval_id(rec.id)
                order = self.execution_service.submit_from_recommendation(
                    recommendation_id=rec.id,
                    approval_id=approval_id,
                    requested_by=self._pilot_actor_id,
                    as_of_date=as_of_date,
                    idempotency_key=f"pilot-exit:{rec.id}",
                )
                exits.append(str(order.id))
            except Exception as exc:
                skipped.append({"recommendation_id": str(rec.id), "action": "exit", "error": str(exc)})

        # Entries — BUY recommendations
        # Regime-gated strategy selection: only trade the strategy whose design
        # regime matches the current market regime. The other two still rank for
        # Factor IC evidence but do not generate live trades.
        # regime_label (4-way) gives finer routing than trend_regime (3-way).
        # BEAR_LOW_VOL: reversal has RCEE edge (ic_lo95=+0.010, hr=58.5%).
        # BEAR_HIGH_VOL: reversal is lethal (ic_lo95=-0.114); use low_vol instead.
        # BULL_HIGH_VOL: breakout underperforms in high-vol; momentum is safer.
        _REGIME_STRATEGY: dict[str, str] = {
            "BULL_LOW_VOL":    "breakout_v1",
            "BULL_HIGH_VOL":   "momentum_v1",
            "BEAR_LOW_VOL":    "reversal_v1",
            "BEAR_HIGH_VOL":   "low_vol_v1",
            "NEUTRAL_LOW_VOL": "momentum_v1",
            "NEUTRAL_HIGH_VOL":"momentum_v1",
        }
        from app.db.repositories.regime_analytics_repository import RegimeAnalyticsRepository
        from app.core.constants import DEFAULT_BENCHMARK_SYMBOL
        _regime_repo = RegimeAnalyticsRepository(self.db)
        _regime_row = _regime_repo.get_current(
            benchmark_symbol=DEFAULT_BENCHMARK_SYMBOL,
            as_of_date=as_of_date,
        )
        _regime_label = (_regime_row.regime_label if _regime_row else None) or "NEUTRAL_LOW_VOL"
        _active_strategy = _REGIME_STRATEGY.get(_regime_label, "momentum_v1")

        # P-22 (v18, flag-gated): rotate the defensive sleeve to gold in BEAR regimes.
        _gold = self._gold_rotation(as_of_date, _regime_label)
        if _gold and _gold.get("action", "").startswith("GOLD_"):
            entries.append(f"gold:{_gold['action']}")

        rec_runs = self.db.scalars(
            select(RecommendationRun).where(
                RecommendationRun.as_of_date == as_of_date,
                RecommendationRun.status == "completed",
                RecommendationRun.strategy_name == _active_strategy,
            )
        ).all()

        # Collect all buy candidates upfront
        all_buy_results: list = []
        for run in rec_runs:
            rows = self.db.scalars(
                select(RecommendationResult).where(
                    RecommendationResult.recommendation_run_id == run.id,
                    RecommendationResult.action == RecommendationAction.BUY.value,
                )
            ).all()
            all_buy_results.extend(rows)

        # Batch: fetch all open position stock_ids in one query
        _open_stock_ids: set = set(self.db.scalars(
            select(PortfolioPosition.stock_id).where(
                PortfolioPosition.is_current.is_(True),
                PortfolioPosition.position_status == "OPEN",
            )
        ).all())

        # ── P-21 Trade Decision Layer: order by expected value, not conviction ────
        # Eligibility (absolute per-stock trend) + prioritization (rank-bucketed
        # expectancy, horizon-matched). Cold-start / thin buckets fall back to
        # conviction so behaviour degrades gracefully. The ordered queue is the
        # same artifact a HITL reviewer would approve top-down.
        _fresh = [r for r in all_buy_results
                  if not r.portfolio_position_id and r.stock_id not in _open_stock_ids]
        _ordered_recs = self._prioritize_entries(
            _fresh, _active_strategy, _regime_label, as_of_date
        )

        buys_today = 0
        # Seed the ₹10L starting capital BEFORE any cash check. The funding waterfall
        # (cash floor + gold-yield) reads cash_balance() to size/gate each buy; without
        # this, day-1 cash reads 0 (initial capital was only seeded lazily inside the
        # entry path that the funding gate blocks) → every buy is skipped → zero trades.
        self.nav_service.ensure_initial_capital(as_of_date)
        # Live slot cap (fixes over-allocation): count open NON-gold positions now and
        # cap at max_positions, incremented per entry below. `limits.can_add_position`
        # was a stale day-start snapshot — when eligibility was loose (e.g. shorter RCEE
        # warm-up) it let many candidates through, opening far more than max_positions.
        # Gold is excluded — it is not a stock slot.
        _open_slots = self.db.scalar(
            select(func.count(PortfolioPosition.id)).where(
                PortfolioPosition.is_current.is_(True),
                PortfolioPosition.position_status == "OPEN",
                PortfolioPosition.strategy_name != "gold_rotation",
            )
        ) or 0
        for rec in _ordered_recs:
                if rec.portfolio_position_id:
                    continue
                if rec.stock_id in _open_stock_ids:
                    continue

                if pilot_auto_approve and rec.lifecycle_state != "APPROVED":
                    try:
                        self.recommendation_service.approve(
                            rec.id,
                            approval_type="PILOT_AUTO",
                            decision="APPROVED",
                            actor_id="paper_pilot",
                            note="Auto-approved for 90-day paper pilot",
                            idempotency_key=f"pilot-approve:{rec.id}",
                        )
                    except Exception as exc:
                        skipped.append({
                            "recommendation_id": str(rec.id),
                            "action": "approve",
                            "error": str(exc),
                        })
                        continue

                if rec.lifecycle_state not in ("APPROVED", "ACTIVE"):
                    skipped.append({
                        "recommendation_id": str(rec.id),
                        "action": "entry",
                        "reason": f"lifecycle={rec.lifecycle_state}",
                    })
                    continue

                if _open_slots >= limits.max_positions or buys_today >= limits.max_buy_per_day:
                    skipped.append({
                        "recommendation_id": str(rec.id),
                        "action": "entry",
                        "reason": limits.block_reason
                        or f"slot_limit: {_open_slots}/{limits.max_positions} open, "
                        f"{buys_today}/{limits.max_buy_per_day} buys today",
                    })
                    continue

                # P-05: volume confirmation — skip entry if today's volume < 70% of 90d avg.
                # Runs per-stock after slot check so it only fires on actual buy candidates.
                # reversal_v1 and low_vol_v1 intentionally buy quiet names — exempt.
                if _active_strategy in ("breakout_v1", "momentum_v1"):
                    from sqlalchemy import text as _text
                    _vol_row = self.db.execute(_text("""
                        WITH recent AS (
                            SELECT volume FROM market_data
                            WHERE stock_id = :sid AND source = 'kite'
                              AND date <= :d
                            ORDER BY date DESC LIMIT 90
                        ),
                        today_vol AS (
                            SELECT volume FROM market_data
                            WHERE stock_id = :sid AND source = 'kite' AND date = :d
                        )
                        SELECT
                            (SELECT volume FROM today_vol) as today_volume,
                            AVG(volume) as avg_90d
                        FROM recent
                    """), {"sid": rec.stock_id, "d": as_of_date}).fetchone()
                    if _vol_row and _vol_row[0] is not None and _vol_row[1] is not None:
                        if float(_vol_row[0]) < float(_vol_row[1]) * 0.70:
                            skipped.append({
                                "recommendation_id": str(rec.id),
                                "action": "entry",
                                "reason": f"LOW_VOLUME_ENTRY: {float(_vol_row[0]):.0f} < 70% of {float(_vol_row[1]):.0f}",
                            })
                            continue

                # ── Funding waterfall (cash floor + gold yields to buys) ──────────
                # Size to the concentration target (same compute_allocation the
                # execution uses), then verify it can be PAID FOR: cash first, then
                # sell gold down to its 25% bear floor. If still short → SKIP. Never
                # buy on margin: this floors cash at 0 and removes the negative-cash
                # leverage. Per-position, in priority order, so 4-5 eligible buys each
                # get funded until the money runs out.
                from sqlalchemy import text as _ctext
                _latest = self.db.execute(_ctext(
                    "SELECT close FROM market_data WHERE stock_id=:s AND date<=:d "
                    "ORDER BY date DESC LIMIT 1"), {"s": rec.stock_id, "d": as_of_date}).scalar()
                if _latest:
                    _alloc = self.portfolio_service.compute_allocation(
                        conviction_band=rec.conviction_band or "MEDIUM",
                        last_price=float(_latest), as_of_date=as_of_date)
                    _need = float(_alloc.position_notional) * 1.005  # + fee/slippage buffer
                    _cash = self.nav_service.cash_balance()
                    if _cash < _need:
                        _cash += self._raise_cash_from_gold(_need - _cash, as_of_date, _regime_label)
                    if _cash < _need:
                        skipped.append({
                            "recommendation_id": str(rec.id), "action": "entry",
                            "reason": f"INSUFFICIENT_CASH: need {_need:.0f} > cash {_cash:.0f} (gold at floor)"})
                        continue

                try:
                    approval_id = self._latest_approval_id(rec.id)
                    order = self.execution_service.submit_from_recommendation(
                        recommendation_id=rec.id,
                        approval_id=approval_id,
                        requested_by=self._pilot_actor_id,
                        as_of_date=as_of_date,
                        idempotency_key=f"pilot-entry:{rec.id}",
                    )
                    entries.append(str(order.id))
                    buys_today += 1
                    _open_slots += 1  # live slot cap — count this new position
                except Exception as exc:
                    skipped.append({
                        "recommendation_id": str(rec.id),
                        "action": "entry",
                        "error": str(exc),
                    })

        return {
            "entries": entries,
            "exits": exits,
            "skipped": skipped,
            "entries_count": len(entries),
            "exits_count": len(exits),
            "regime_label": _regime_label,
            "active_strategy": _active_strategy,
        }

    def _latest_approval_id(self, recommendation_id: UUID) -> UUID | None:
        approval = self.db.scalar(
            select(RecommendationApproval)
            .where(
                RecommendationApproval.recommendation_result_id == recommendation_id,
                RecommendationApproval.decision == "APPROVED",
            )
            .order_by(RecommendationApproval.decided_at.desc())
        )
        return approval.id if approval else None

    def health_snapshot(self, as_of_date: date | None = None) -> dict:
        """Portfolio health for pilot dashboard — read-only."""
        as_of = as_of_date or date.today()
        limits = self.portfolio_service.get_limits(as_of)
        summary = self.portfolio_service.get_summary()
        nav = self.db.scalar(
            select(PortfolioNavHistory)
            .where(PortfolioNavHistory.as_of_date <= as_of)
            .order_by(PortfolioNavHistory.as_of_date.desc())
            .limit(1)
        )
        recon = self.reconciliation_service.get_latest()
        pending_exits = int(
            self.db.scalar(
                select(func.count(ExitRecommendation.id)).where(
                    ExitRecommendation.status == "PENDING"
                )
            )
            or 0
        )
        return {
            "as_of_date": as_of.isoformat(),
            "summary": summary,
            "limits": {
                "can_add_position": limits.can_add_position,
                "slots_available": limits.slots_available,
                "block_reason": limits.block_reason,
            },
            "nav": {
                "total_equity": float(nav.total_equity) if nav else None,
                "day_return_pct": float(nav.day_return_pct) if nav and nav.day_return_pct else None,
                "alpha_pct": float(nav.alpha_pct) if nav and nav.alpha_pct else None,
            },
            "reconciliation_status": recon.status if recon else None,
            "pending_exit_recommendations": pending_exits,
        }
