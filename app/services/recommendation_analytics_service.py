"""Recommendation Analytics Service — orchestrates analytics queries and metric computation.

All analytics are observation-only. No output feeds back into the
recommendation engine, conviction formula, or ARGS committees (AC-RP-09).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.db.repositories.recommendation_outcome_repository import RecommendationOutcomeRepository
from app.db.repositories.recommendation_repository import RecommendationRepository
from app.models.recommendation import RecommendationRun
from app.models.stock import Stock
from app.recommendation_analytics.calculator import (
    OutcomeRow,
    check_conviction_calibration,
    compute_committee_breakdown,
    compute_conviction_breakdown,
    compute_quality_metrics,
    compute_regime_breakdown,
)
from app.recommendation_analytics.dtos import (
    CommitteePerformanceDTO,
    ConvictionPerformanceDTO,
    OutcomeWindowDTO,
    RecommendationSummaryDTO,
    RegimePerformanceDTO,
    SymbolAnalyticsDTO,
    TrustMetricsDTO,
)
from app.recommendation_analytics.trust_metrics import (
    _ActionHistory,
    compute_trust_metrics,
)


class RecommendationAnalyticsService:
    def __init__(
        self,
        db: Session,
        *,
        outcome_repo: RecommendationOutcomeRepository | None = None,
        recommendation_repo: RecommendationRepository | None = None,
    ) -> None:
        self.db = db
        self.outcome_repo = outcome_repo or RecommendationOutcomeRepository(db)
        self.recommendation_repo = recommendation_repo or RecommendationRepository(db)

    # ── Summary ───────────────────────────────────────────────────────────────

    def get_summary(
        self,
        *,
        strategy_name: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> RecommendationSummaryDTO:
        rows = self._load_outcome_rows(
            strategy_name=strategy_name, from_date=from_date, to_date=to_date
        )
        window = self._make_window(rows, strategy_name, from_date, to_date)
        quality = compute_quality_metrics(rows)

        # Top conviction BUYs (open, sorted by conviction_score proxy via alpha)
        open_rows = self.outcome_repo.list_for_analytics(
            strategy_name=strategy_name,
            from_date=from_date,
            to_date=to_date,
            outcome_statuses=["OPEN"],
        )
        top_buys = sorted(
            [
                {
                    "symbol": r.symbol,
                    "outcome_status": r.outcome_status,
                    "conviction_band": r.conviction_band,
                }
                for r in open_rows
                if r.symbol
            ],
            key=lambda x: (
                ["EXCEPTIONAL", "HIGH", "MEDIUM", "LOW", "BLOCKED"].index(x["conviction_band"])
                if x["conviction_band"] in ["EXCEPTIONAL", "HIGH", "MEDIUM", "LOW", "BLOCKED"]
                else 99
            ),
        )[:10]

        # Exit candidates from latest recommendation run
        exit_candidates = self._get_exit_candidates(strategy_name)

        return RecommendationSummaryDTO(
            as_of_date=to_date,
            window=window,
            quality=quality,
            top_conviction_buys=top_buys,
            exit_candidates=exit_candidates,
        )

    # ── Conviction ────────────────────────────────────────────────────────────

    def get_conviction_performance(
        self,
        *,
        strategy_name: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> ConvictionPerformanceDTO:
        rows = self._load_outcome_rows(
            strategy_name=strategy_name, from_date=from_date, to_date=to_date
        )
        window = self._make_window(rows, strategy_name, from_date, to_date)
        bands = compute_conviction_breakdown(rows)
        is_cal, rho = check_conviction_calibration(bands)

        if is_cal is None:
            note = "Insufficient closed outcomes to assess calibration."
        elif is_cal:
            note = f"Conviction bands are calibrated (ρ={rho}). EXCEPTIONAL outperforms HIGH outperforms MEDIUM."
        else:
            note = f"Conviction bands are NOT calibrated (ρ={rho}). PO review recommended."

        return ConvictionPerformanceDTO(
            window=window, bands=bands, calibration_rank_correct=is_cal, calibration_note=note
        )

    # ── Regime ────────────────────────────────────────────────────────────────

    def get_regime_performance(
        self,
        *,
        strategy_name: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> RegimePerformanceDTO:
        rows = self._load_outcome_rows(
            strategy_name=strategy_name, from_date=from_date, to_date=to_date
        )
        window = self._make_window(rows, strategy_name, from_date, to_date)
        regimes = compute_regime_breakdown(rows)
        return RegimePerformanceDTO(window=window, regimes=regimes)

    # ── Committee ─────────────────────────────────────────────────────────────

    def get_committee_performance(
        self,
        *,
        strategy_name: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> CommitteePerformanceDTO:
        rows = self._load_outcome_rows(
            strategy_name=strategy_name, from_date=from_date, to_date=to_date
        )
        window = self._make_window(rows, strategy_name, from_date, to_date)
        advisories = compute_committee_breakdown(rows)
        return CommitteePerformanceDTO(
            window=window,
            advisories=advisories,
            note="Committee outputs are advisory only. These metrics measure usefulness post-hoc and must not influence future recommendation generation.",
        )

    # ── Trust ─────────────────────────────────────────────────────────────────

    def get_trust_metrics(
        self,
        *,
        strategy_name: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> TrustMetricsDTO:
        # Bound the window. Unbounded, every trust query scans all history; under
        # NIFTY_1000 that hangs >20s and exhausts the connection pool (which took the
        # whole app down). Trust metrics are recent-window measures anyway — default
        # to the last 90 days when the caller (the UI) doesn't pass dates.
        if from_date is None:
            from_date = (to_date or date.today()) - timedelta(days=90)
        rows = self._load_outcome_rows(
            strategy_name=strategy_name, from_date=from_date, to_date=to_date
        )
        window = self._make_window(rows, strategy_name, from_date, to_date)

        # Stability: query directly from recommendation_results — no closed outcomes needed.
        # Falls back to outcome-linked history if direct query returns nothing (shouldn't happen).
        raw_history = self.outcome_repo.list_action_history_from_results(
            strategy_name=strategy_name,
            from_date=from_date,
            to_date=to_date,
        )
        if not raw_history:
            raw_history = self.outcome_repo.list_action_history(
                strategy_name=strategy_name,
                from_date=from_date,
                to_date=to_date,
            )
        # Group by symbol
        by_symbol: dict[str, list] = defaultdict(list)
        for row in raw_history:
            by_symbol[row["symbol"]].append((row["date"], row["action"]))
        action_history = [
            _ActionHistory(symbol=sym, dates_actions=sorted(seq)) for sym, seq in by_symbol.items()
        ]

        # Reliability: query directly from recommendation_results — no closed outcomes needed.
        val_counts = self.outcome_repo.count_by_validation_status_from_results(
            strategy_name=strategy_name,
            from_date=from_date,
            to_date=to_date,
        )
        if val_counts["completed"] == 0 and val_counts["insufficient_data"] == 0:
            # Fallback to outcome-linked counts if direct query has no data
            val_counts = self.outcome_repo.count_by_validation_status(
                strategy_name=strategy_name,
                from_date=from_date,
                to_date=to_date,
            )
        total = val_counts["completed"] + val_counts["insufficient_data"]

        return compute_trust_metrics(
            window=window,
            outcome_rows=rows,
            action_history=action_history,
            total_recommendations=total,
            completed_validation_count=val_counts["completed"],
            insufficient_data_count=val_counts["insufficient_data"],
        )

    # ── Symbol analytics ──────────────────────────────────────────────────────

    def get_symbol_analytics(
        self, symbol: str, strategy_name: str | None = None
    ) -> SymbolAnalyticsDTO:
        outcomes = self.outcome_repo.list_by_symbol(symbol)
        results = self.outcome_repo.list_results_for_symbol(symbol, strategy_name)

        closed = [o for o in outcomes if o.outcome_status in ("WIN", "LOSS", "BREAKEVEN")]
        wins = [o for o in closed if o.outcome_status == "WIN"]
        alphas = [float(o.alpha_pct) for o in closed if o.alpha_pct is not None]
        days = [o.days_held for o in closed if o.days_held is not None]

        # Latest recommendation result
        latest_result = results[0] if results else None
        last_action = latest_result.action if latest_result else None
        last_date = None
        if latest_result:
            rec_run = self.db.get(RecommendationRun, latest_result.recommendation_run_id)
            last_date = rec_run.as_of_date if rec_run else None

        # Why not recommended: reason codes from latest result that is not BUY
        why_not: list[str] = []
        if latest_result and latest_result.action != "BUY":
            why_not = latest_result.reason_codes or []

        action_counts: dict[str, int] = defaultdict(int)
        for r in results:
            action_counts[r.action] += 1

        conv_scores = [r.conviction_score for r in results if r.conviction_score is not None]

        return SymbolAnalyticsDTO(
            symbol=symbol.upper(),
            total_recommendations=len(results),
            buy_count=action_counts.get("BUY", 0),
            watch_count=action_counts.get("WATCH", 0),
            reject_count=action_counts.get("REJECT", 0),
            closed_outcomes=len(closed),
            win_rate=len(wins) / len(closed) if closed else None,
            avg_alpha_pct=sum(alphas) / len(alphas) if alphas else None,
            avg_conviction_score=sum(conv_scores) / len(conv_scores) if conv_scores else None,
            avg_days_held=sum(days) / len(days) if days else None,
            last_action=last_action,
            last_recommendation_date=last_date,
            why_not_recommended=why_not,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _load_outcome_rows(
        self,
        *,
        strategy_name: str | None,
        from_date: date | None,
        to_date: date | None,
    ) -> list[OutcomeRow]:
        db_rows = self.outcome_repo.list_for_analytics(
            strategy_name=strategy_name,
            from_date=from_date,
            to_date=to_date,
        )
        return [
            OutcomeRow(
                outcome_status=r.outcome_status,
                alpha_pct=float(r.alpha_pct) if r.alpha_pct is not None else None,
                pnl_pct=float(r.pnl_pct) if r.pnl_pct is not None else None,
                benchmark_return_pct=float(r.benchmark_return_pct)
                if r.benchmark_return_pct is not None
                else None,
                target_hit=r.target_hit,
                stop_hit=r.stop_hit,
                days_held=r.days_held,
                conviction_band=r.conviction_band,
                regime_label=r.regime_label,
                strategy_name=r.strategy_name,
                committee_advisory=r.committee_advisory,
                symbol=r.symbol,
            )
            for r in db_rows
        ]

    def _make_window(
        self,
        rows: list[OutcomeRow],
        strategy_name: str | None,
        from_date: date | None,
        to_date: date | None,
    ) -> OutcomeWindowDTO:
        closed = [r for r in rows if r.outcome_status in ("WIN", "LOSS", "BREAKEVEN")]
        return OutcomeWindowDTO(
            from_date=from_date,
            to_date=to_date,
            strategy_name=strategy_name,
            window_sessions=len(closed),
        )

    def _get_exit_candidates(self, strategy_name: str | None) -> list[dict]:
        rec_run = None
        if strategy_name:
            rec_run = self.recommendation_repo.get_latest_run_by_strategy(strategy_name)
        if rec_run is None:
            return []
        results = self.recommendation_repo.get_results(rec_run.id, action_filter=["EXIT_APPROVED"])
        out = []
        for r in results[:10]:
            stock = self.db.get(Stock, r.stock_id)
            out.append(
                {
                    "symbol": stock.symbol if stock else str(r.stock_id),
                    "conviction_band": r.conviction_band,
                    "reason_codes": r.reason_codes,
                }
            )
        return out
