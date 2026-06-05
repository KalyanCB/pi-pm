from datetime import UTC, datetime
from uuid import uuid4

from app.models.ranking_validation_report import RankingValidationReport
from app.validation.constants import (
    VALIDATION_STATUS_COMPLETED,
    VALIDATION_STATUS_FAILED,
    VALIDATION_STATUS_INSUFFICIENT_DATA,
)
from app.validation.summary_aggregator import aggregate_cross_run_summary


def _report(
    *,
    status: str = VALIDATION_STATUS_COMPLETED,
    regime_label: str | None = "BULL_LOW_VOL",
    trend_regime: str | None = "BULL",
    vol_regime: str | None = "LOW_VOL",
    ic: str = "0.10",
    include_metrics: bool = True,
) -> RankingValidationReport:
    horizon_metrics = None
    if include_metrics and status == VALIDATION_STATUS_COMPLETED:
        horizon_metrics = {
            "20": {
                "status": "ok",
                "ic_spearman": ic,
                "top_minus_bottom_spread": "0.05",
                "deciles": [
                    {"decile": 1, "mean_return": "0.08"},
                    {"decile": 10, "mean_return": "0.01"},
                ],
                "hit_rates": {
                    "top_vs_bottom_hit_rate": "0.70",
                    "rank_directional_hit_rate": "0.60",
                },
            }
        }
    return RankingValidationReport(
        id=uuid4(),
        ranking_run_id=uuid4(),
        status=status,
        regime_label=regime_label,
        trend_regime=trend_regime,
        vol_regime=vol_regime,
        horizon_metrics=horizon_metrics,
        computed_at=datetime.now(UTC),
    )


def test_aggregate_empty_dataset():
    summary = aggregate_cross_run_summary([], horizon=20, all_reports=[])
    assert summary.reports_count == 0
    assert summary.validated_runs == 0
    assert summary.average_ic is None
    assert summary.best_regime is None


def test_aggregate_average_median_and_hit_rates():
    reports = [
        _report(ic="0.20", regime_label="BULL_LOW_VOL"),
        _report(ic="0.10", regime_label="BULL_HIGH_VOL"),
        _report(ic="0.00", regime_label="BEAR_LOW_VOL"),
    ]
    summary = aggregate_cross_run_summary(reports, horizon=20, all_reports=reports)
    assert summary.reports_count == 3
    assert summary.validated_runs == 3
    assert summary.average_ic == "0.10000000"
    assert summary.median_ic == "0.10000000"
    assert summary.hit_rate == "0.70000000"
    assert summary.directional_hit_rate == "0.60000000"
    assert summary.spread == "0.05000000"
    assert summary.top_decile_return == "0.08000000"
    assert summary.bottom_decile_return == "0.01000000"


def test_aggregate_mixed_validation_statuses():
    reports = [
        _report(status=VALIDATION_STATUS_COMPLETED),
        _report(status=VALIDATION_STATUS_INSUFFICIENT_DATA, include_metrics=False),
        _report(status=VALIDATION_STATUS_FAILED, include_metrics=False),
    ]
    summary = aggregate_cross_run_summary(
        [reports[0]],
        horizon=20,
        all_reports=reports,
    )
    assert summary.reports_count == 1
    assert summary.validated_runs == 1
    assert summary.insufficient_data_runs == 1
    assert summary.failed_runs == 1


def test_aggregate_regime_grouping_and_best_worst():
    reports = [
        _report(
            ic="0.30",
            regime_label="BULL_LOW_VOL",
            trend_regime="BULL",
            vol_regime="LOW_VOL",
        ),
        _report(
            ic="0.10",
            regime_label="BULL_HIGH_VOL",
            trend_regime="BULL",
            vol_regime="HIGH_VOL",
        ),
        _report(
            ic="-0.10",
            regime_label="BEAR_LOW_VOL",
            trend_regime="BEAR",
            vol_regime="LOW_VOL",
        ),
        _report(
            ic="0.05",
            regime_label="BEAR_HIGH_VOL",
            trend_regime="BEAR",
            vol_regime="HIGH_VOL",
        ),
    ]
    summary = aggregate_cross_run_summary(reports, horizon=20, all_reports=reports)
    assert summary.regime_ic["BULL_LOW_VOL"] == "0.30000000"
    assert summary.regime_ic["BEAR_LOW_VOL"] == "-0.10000000"
    assert summary.bull_market_ic == "0.20000000"
    assert summary.bear_market_ic == "-0.02500000"
    assert summary.high_vol_ic == "0.07500000"
    assert summary.low_vol_ic == "0.10000000"
    assert summary.best_regime == "BULL_LOW_VOL"
    assert summary.worst_regime == "BEAR_LOW_VOL"


def test_aggregate_skips_non_ok_horizon_metrics():
    report = _report()
    report.horizon_metrics = {"20": {"status": "insufficient_data"}}
    summary = aggregate_cross_run_summary([report], horizon=20, all_reports=[report])
    assert summary.reports_count == 1
    assert summary.average_ic is None
