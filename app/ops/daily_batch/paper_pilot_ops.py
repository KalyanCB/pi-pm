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

        if is_bear and held is None:
            cash = self.nav_service.cash_balance()
            budget = cash * s.gold_alloc_pct
            qty = int(budget / px)
            if qty <= 0:
                return {"status": "insufficient_cash"}
            fill = round(px * 1.0005, 4)  # 5bps slippage
            self.portfolio_service.open_position(
                stock_id=gold_id, quantity=qty, fill_price=fill,
                entry_date=as_of_date, strategy_name="gold_rotation", sector="ETF",
            )
            self.nav_service.record_cash_entry(
                entry_type="TRADE_BUY", amount=-(qty * fill), as_of_date=as_of_date,
                reference_type="gold_rotation", description=f"GOLD BUY {qty} @ {fill}")
            return {"action": "GOLD_BUY", "qty": qty, "price": fill}

        if not is_bear and held is not None:
            fill = round(px * 0.9995, 4)
            qty = float(held.quantity)
            self.portfolio_service.close_position(
                gold_id, exit_price=fill, exit_date=as_of_date, exit_reason="GOLD_REGIME_EXIT")
            self.nav_service.record_cash_entry(
                entry_type="TRADE_SELL", amount=qty * fill, as_of_date=as_of_date,
                reference_type="gold_rotation", description=f"GOLD SELL {qty} @ {fill}")
            return {"action": "GOLD_SELL", "qty": qty, "price": fill}
        return {"action": "hold", "is_bear": is_bear, "holding": held is not None}

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

                if not limits.can_add_position or buys_today >= limits.max_buy_per_day:
                    skipped.append({
                        "recommendation_id": str(rec.id),
                        "action": "entry",
                        "reason": limits.block_reason or "slot_limit",
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
