from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import RankingRunStatus
from app.db.repositories.factor_performance_metric_repository import FactorPerformanceMetricRepository
from app.models.ranking_result import RankingResult
from app.models.ranking_run import RankingRun
from app.models.ranking_validation_report import RankingValidationReport
from app.models.stock import Stock
from app.services.signal_validation_service import SignalValidationService
from app.validation.constants import VALIDATION_STATUS_COMPLETED


class ResearchIntelligenceBuilder:
    def __init__(
        self,
        db: Session,
        validation_service: SignalValidationService,
        factor_metric_repo: FactorPerformanceMetricRepository,
    ) -> None:
        self.db = db
        self.validation_service = validation_service
        self.factor_metric_repo = factor_metric_repo

    def build_coverage_statistics(
        self,
        *,
        universe_code: str,
        start_date,
        end_date,
    ) -> dict:
        ranking_counts = dict(
            self.db.execute(
                select(RankingRun.strategy_name, func.count())
                .where(RankingRun.universe_code == universe_code)
                .where(RankingRun.status == RankingRunStatus.COMPLETED.value)
                .where(RankingRun.as_of_date >= start_date)
                .where(RankingRun.as_of_date <= end_date)
                .group_by(RankingRun.strategy_name)
            ).all()
        )
        validation_counts = dict(
            self.db.execute(
                select(RankingValidationReport.status, func.count())
                .join(RankingRun, RankingRun.id == RankingValidationReport.ranking_run_id)
                .where(RankingRun.universe_code == universe_code)
                .where(RankingRun.as_of_date >= start_date)
                .where(RankingRun.as_of_date <= end_date)
                .group_by(RankingValidationReport.status)
            ).all()
        )
        return {
            "report": "coverage_statistics",
            "universe_code": universe_code,
            "ranking_runs_by_strategy": ranking_counts,
            "validation_reports_by_status": validation_counts,
        }

    def build_ranking_statistics(self, *, universe_code: str, start_date, end_date) -> dict:
        rows = self.db.execute(
            select(
                RankingRun.strategy_name,
                func.avg(RankingRun.ranked_stock_count),
                func.count(),
            )
            .where(RankingRun.universe_code == universe_code)
            .where(RankingRun.status == RankingRunStatus.COMPLETED.value)
            .where(RankingRun.as_of_date >= start_date)
            .where(RankingRun.as_of_date <= end_date)
            .group_by(RankingRun.strategy_name)
        ).all()
        return {
            "report": "ranking_statistics",
            "entries": [
                {
                    "strategy_name": row[0],
                    "avg_ranked_stocks": float(row[1]) if row[1] is not None else None,
                    "run_count": row[2],
                }
                for row in rows
            ],
        }

    def build_ic_spread_by_strategy(
        self,
        *,
        universe_code: str,
        start_date,
        end_date,
        horizon: int = 20,
    ) -> dict:
        strategies = ["breakout_v1", "momentum_v1"]
        ic_entries = []
        spread_entries = []
        for strategy in strategies:
            summary = self.validation_service.get_summary(
                universe_code=universe_code,
                strategy_name=strategy,
                strategy_version="1.0.0",
                start_date=start_date,
                end_date=end_date,
                horizon=horizon,
            )
            horizon_key = str(horizon)
            ic_entries.append(
                {
                    "strategy_name": strategy,
                    "ic_spearman": summary.get(f"average_ic_{horizon}d"),
                    "sample_size": summary.get("validated_runs"),
                }
            )
            spread_entries.append(
                {
                    "strategy_name": strategy,
                    "spread": summary.get(f"spread_{horizon}d"),
                    "sample_size": summary.get("validated_runs"),
                }
            )
        return {
            "ic_by_strategy": {"report": "ic_by_strategy", "entries": ic_entries},
            "spread_by_strategy": {"report": "spread_by_strategy", "entries": spread_entries},
        }

    def build_ic_spread_by_regime(
        self,
        *,
        universe_code: str,
        strategy_name: str,
        start_date,
        end_date,
        horizon: int = 20,
    ) -> dict:
        reports = self.db.scalars(
            select(RankingValidationReport)
            .join(RankingRun, RankingRun.id == RankingValidationReport.ranking_run_id)
            .where(RankingRun.universe_code == universe_code)
            .where(RankingRun.strategy_name == strategy_name)
            .where(RankingValidationReport.status == VALIDATION_STATUS_COMPLETED)
            .where(RankingRun.as_of_date >= start_date)
            .where(RankingRun.as_of_date <= end_date)
        ).all()
        by_regime: dict[str, list[float]] = {}
        spread_by_regime: dict[str, list[float]] = {}
        for report in reports:
            if not report.regime_label:
                continue
            metrics = (report.horizon_metrics or {}).get(str(horizon), {})
            ic = metrics.get("ic_spearman")
            spread = metrics.get("top_minus_bottom_spread")
            if ic is not None:
                by_regime.setdefault(report.regime_label, []).append(float(ic))
            if spread is not None:
                spread_by_regime.setdefault(report.regime_label, []).append(float(spread))
        return {
            "ic_by_regime": {
                "report": "ic_by_regime",
                "entries": [
                    {
                        "regime_label": regime,
                        "mean_ic": sum(vals) / len(vals),
                        "sample_size": len(vals),
                    }
                    for regime, vals in sorted(by_regime.items())
                ],
            },
            "spread_by_regime": {
                "report": "spread_by_regime",
                "entries": [
                    {
                        "regime_label": regime,
                        "mean_spread": sum(vals) / len(vals),
                        "sample_size": len(vals),
                    }
                    for regime, vals in sorted(spread_by_regime.items())
                ],
            },
        }

    def build_factor_contribution_analysis(
        self,
        *,
        universe_code: str,
        regime_label: str = "BULL_LOW_VOL",
        dataset_split: str = "HOLDOUT",
    ) -> dict:
        metrics = self.factor_metric_repo.list_metrics(
            universe_code=universe_code,
            regime_label=regime_label,
            dataset_split=dataset_split,
            horizon=20,
            limit=20,
        )
        return {
            "report": "factor_contribution_analysis",
            "entries": [
                {
                    "factor_name": m.factor_name,
                    "ic_spearman": float(m.ic_spearman) if m.ic_spearman is not None else None,
                    "stability_score": float(m.stability_score) if m.stability_score is not None else None,
                    "sample_size": m.sample_size,
                }
                for m in sorted(
                    metrics,
                    key=lambda row: float(row.ic_spearman) if row.ic_spearman is not None else -999,
                    reverse=True,
                )
            ],
        }

    def build_top_20_candidates(
        self,
        *,
        universe_code: str,
        strategy_name: str = "breakout_v1",
        strategy_version: str = "1.0.0",
    ) -> dict:
        latest_run = self.db.scalar(
            select(RankingRun)
            .where(RankingRun.universe_code == universe_code)
            .where(RankingRun.strategy_name == strategy_name)
            .where(RankingRun.strategy_version == strategy_version)
            .where(RankingRun.status == RankingRunStatus.COMPLETED.value)
            .order_by(RankingRun.as_of_date.desc())
            .limit(1)
        )
        if latest_run is None:
            return {"report": "current_top_20_candidates", "entries": []}
        rows = self.db.execute(
            select(RankingResult.rank, Stock.symbol, Stock.name, RankingResult.score)
            .join(Stock, Stock.id == RankingResult.stock_id)
            .where(RankingResult.ranking_run_id == latest_run.id)
            .order_by(RankingResult.rank)
            .limit(20)
        ).all()
        return {
            "report": "current_top_20_candidates",
            "as_of_date": latest_run.as_of_date.isoformat(),
            "run_id": str(latest_run.id),
            "entries": [
                {
                    "rank": row.rank,
                    "symbol": row.symbol,
                    "name": row.name,
                    "score": float(row.score),
                }
                for row in rows
            ],
        }

    def build_executive_summary(
        self,
        *,
        universe_code: str,
        start_date,
        end_date,
        holdout_start_date,
    ) -> dict:
        coverage = self.build_coverage_statistics(
            universe_code=universe_code, start_date=start_date, end_date=end_date
        )
        ranking_stats = self.build_ranking_statistics(
            universe_code=universe_code, start_date=start_date, end_date=end_date
        )
        strategy_metrics = self.build_ic_spread_by_strategy(
            universe_code=universe_code, start_date=start_date, end_date=end_date
        )
        regime_metrics = self.build_ic_spread_by_regime(
            universe_code=universe_code,
            strategy_name="breakout_v1",
            start_date=start_date,
            end_date=end_date,
        )
        factors = self.build_factor_contribution_analysis(universe_code=universe_code)
        top20 = self.build_top_20_candidates(universe_code=universe_code)

        breakout_ic = next(
            (
                e["ic_spearman"]
                for e in strategy_metrics["ic_by_strategy"]["entries"]
                if e["strategy_name"] == "breakout_v1"
            ),
            None,
        )
        momentum_ic = next(
            (
                e["ic_spearman"]
                for e in strategy_metrics["ic_by_strategy"]["entries"]
                if e["strategy_name"] == "momentum_v1"
            ),
            None,
        )
        bull_spread = next(
            (
                e["mean_spread"]
                for e in regime_metrics["spread_by_regime"]["entries"]
                if e["regime_label"] == "BULL_LOW_VOL"
            ),
            None,
        )
        conclusions = []
        if breakout_ic is not None and momentum_ic is not None:
            if float(breakout_ic) > float(momentum_ic):
                conclusions.append("breakout_v1 outperforms momentum_v1 on pooled IC.")
            else:
                conclusions.append("momentum_v1 matches or exceeds breakout_v1 on pooled IC.")
        if bull_spread is not None and float(bull_spread) > 0:
            conclusions.append("Strongest edge is concentrated in BULL_LOW_VOL.")
        conclusions.append("Regime-aware deployment is recommended pending exit research confirmation.")

        return {
            "report": "executive_committee_summary",
            "generated_at": datetime.now(UTC).isoformat(),
            "universe_code": universe_code,
            "window": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "holdout_start_date": holdout_start_date.isoformat(),
            },
            "coverage_statistics": coverage,
            "ranking_statistics": ranking_stats,
            "ic_by_strategy": strategy_metrics["ic_by_strategy"],
            "spread_by_strategy": strategy_metrics["spread_by_strategy"],
            "ic_by_regime": regime_metrics["ic_by_regime"],
            "spread_by_regime": regime_metrics["spread_by_regime"],
            "top_contributing_factors": factors,
            "current_top_20": top20,
            "key_conclusions": conclusions,
        }
