from datetime import UTC, date, datetime
from decimal import Decimal

from app.core.constants import (
    RANKING_STRATEGY_BREAKOUT_V1,
    RANKING_STRATEGY_BREAKOUT_V1_VERSION,
    RankingRunStatus,
)
from app.db.repositories.ranking_validation_repository import RankingValidationRepository
from app.db.repositories.regime_policy_config_repository import RegimePolicyConfigRepository
from app.models.platform_traceability import ValidationHorizonMetric
from app.models.ranking_performance_snapshot import RankingPerformanceSnapshot
from app.models.ranking_result import RankingResult
from app.models.ranking_run import RankingRun
from app.models.ranking_validation_report import RankingValidationReport
from app.models.stock import Stock
from app.regime_policy.engine import breakout_v1_preset_specs
from app.regime_policy.replay import RegimePolicyReplayService, build_single_holdout_window
from app.validation.constants import VALIDATION_STATUS_COMPLETED


def _seed_validated_run(
    db_session,
    *,
    as_of: date,
    regime_label: str,
    symbol: str = "TST.NS",
):
    stock = Stock(
        symbol=symbol,
        name=symbol,
        exchange="NSE",
        is_active=True,
        data_status="ACTIVE",
    )
    db_session.add(stock)
    db_session.flush()

    run = RankingRun(
        strategy_name=RANKING_STRATEGY_BREAKOUT_V1,
        strategy_version=RANKING_STRATEGY_BREAKOUT_V1_VERSION,
        universe_code="PI_PM_CORE",
        as_of_date=as_of,
        benchmark_symbol="^NSEI",
        filter_config_hash="test-filter",
        normalization_method="percentile",
        status=RankingRunStatus.COMPLETED.value,
        regime_label=regime_label,
        inputs_hash=f"hash-{as_of.isoformat()}",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    db_session.add(run)
    db_session.flush()

    db_session.add(
        RankingResult(
            ranking_run_id=run.id,
            stock_id=stock.id,
            rank=1,
            score=Decimal("10"),
            created_at=datetime.now(UTC),
        )
    )
    db_session.add(
        RankingPerformanceSnapshot(
            ranking_run_id=run.id,
            stock_id=stock.id,
            return_20d=0.02,
            captured_at=datetime.now(UTC),
        )
    )

    report = RankingValidationReport(
        ranking_run_id=run.id,
        status=VALIDATION_STATUS_COMPLETED,
        regime_label=regime_label,
        computed_at=datetime.now(UTC),
    )
    db_session.add(report)
    db_session.commit()
    return run, report


def test_replay_e2_excludes_non_bull_days(db_session):
    bull_date = date(2024, 6, 3)
    bear_date = date(2024, 6, 10)
    _seed_validated_run(db_session, as_of=bull_date, regime_label="BULL_LOW_VOL", symbol="AAA.NS")
    _seed_validated_run(db_session, as_of=bear_date, regime_label="BEAR_LOW_VOL", symbol="BBB.NS")

    config_repo = RegimePolicyConfigRepository(db_session)
    spec = breakout_v1_preset_specs()[1]
    config = config_repo.create(
        policy_name=spec.policy_name,
        policy_type=spec.policy_type,
        strategy_name=spec.strategy_name,
        strategy_version=spec.strategy_version,
        policy_version=1,
        allowed_regimes=spec.allowed_regimes,
        size_multipliers=spec.size_multipliers,
        min_decile=spec.min_decile,
        max_decile=spec.max_decile,
        default_action=spec.default_action,
    )
    db_session.commit()

    replay_service = RegimePolicyReplayService(
        db_session,
        RankingValidationRepository(db_session),
    )
    window = build_single_holdout_window(date(2024, 1, 1), date(2024, 12, 31), date(2025, 1, 1))
    result = replay_service.replay(
        policy_config_id=config.id,
        config=spec,
        window_spec=window,
        horizon=20,
        strategy_name=spec.strategy_name,
        strategy_version=spec.strategy_version,
        universe_code="PI_PM_CORE",
    )
    assert result.days_included == 1
    assert result.days_excluded == 1


def _seed_e2_config(db_session):
    config_repo = RegimePolicyConfigRepository(db_session)
    spec = breakout_v1_preset_specs()[1]
    config = config_repo.create(
        policy_name=spec.policy_name,
        policy_type=spec.policy_type,
        strategy_name=spec.strategy_name,
        strategy_version=spec.strategy_version,
        policy_version=1,
        allowed_regimes=spec.allowed_regimes,
        size_multipliers=spec.size_multipliers,
        min_decile=spec.min_decile,
        max_decile=spec.max_decile,
        default_action=spec.default_action,
    )
    db_session.commit()
    return config, spec


def _seed_validated_run_with_stocks(
    db_session,
    *,
    as_of: date,
    regime_label: str,
    symbols: list[str],
):
    stocks: list[Stock] = []
    for symbol in symbols:
        stock = Stock(
            symbol=symbol,
            name=symbol,
            exchange="NSE",
            is_active=True,
            data_status="ACTIVE",
        )
        db_session.add(stock)
        stocks.append(stock)
    db_session.flush()

    run = RankingRun(
        strategy_name=RANKING_STRATEGY_BREAKOUT_V1,
        strategy_version=RANKING_STRATEGY_BREAKOUT_V1_VERSION,
        universe_code="PI_PM_CORE",
        as_of_date=as_of,
        benchmark_symbol="^NSEI",
        filter_config_hash="test-filter",
        normalization_method="percentile",
        status=RankingRunStatus.COMPLETED.value,
        regime_label=regime_label,
        inputs_hash=f"hash-{as_of.isoformat()}-{len(symbols)}",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    db_session.add(run)
    db_session.flush()

    for rank, stock in enumerate(stocks, start=1):
        db_session.add(
            RankingResult(
                ranking_run_id=run.id,
                stock_id=stock.id,
                rank=rank,
                score=Decimal(str(100 - rank)),
                created_at=datetime.now(UTC),
            )
        )
        db_session.add(
            RankingPerformanceSnapshot(
                ranking_run_id=run.id,
                stock_id=stock.id,
                return_20d=0.01 + (rank * 0.001),
                captured_at=datetime.now(UTC),
            )
        )

    report = RankingValidationReport(
        ranking_run_id=run.id,
        status=VALIDATION_STATUS_COMPLETED,
        regime_label=regime_label,
        computed_at=datetime.now(UTC),
    )
    db_session.add(report)
    db_session.commit()
    return run, report


def test_replay_e2_two_bull_low_vol_days_have_positive_metrics(db_session):
    """Regression: E2 ALLOW days must contribute ranked_days and sample_count."""
    bull_dates = (date(2024, 6, 3), date(2024, 6, 10))
    for idx, as_of in enumerate(bull_dates):
        _seed_validated_run_with_stocks(
            db_session,
            as_of=as_of,
            regime_label="BULL_LOW_VOL",
            symbols=[f"BULL{idx}_{stock_idx}.NS" for stock_idx in range(6)],
        )

    config, spec = _seed_e2_config(db_session)
    replay_service = RegimePolicyReplayService(
        db_session,
        RankingValidationRepository(db_session),
    )
    window = build_single_holdout_window(date(2024, 1, 1), date(2024, 12, 31), date(2025, 1, 1))
    result = replay_service.replay(
        policy_config_id=config.id,
        config=spec,
        window_spec=window,
        horizon=20,
        strategy_name=spec.strategy_name,
        strategy_version=spec.strategy_version,
        universe_code="PI_PM_CORE",
    )

    assert result.days_included == 2
    assert result.train_metrics.ranked_days == 2
    assert result.train_metrics.sample_count > 0
    assert result.holdout_metrics.ranked_days == 0


def test_replay_e2_uses_precomputed_horizon_metrics_when_snapshot_returns_missing(db_session):
    """Regression: ALLOW + missing return_20d must not drop included days when horizon metrics exist."""
    as_of = date(2024, 6, 3)
    stock = Stock(
        symbol="NULLRET.NS",
        name="NULLRET",
        exchange="NSE",
        is_active=True,
        data_status="ACTIVE",
    )
    db_session.add(stock)
    db_session.flush()

    run = RankingRun(
        strategy_name=RANKING_STRATEGY_BREAKOUT_V1,
        strategy_version=RANKING_STRATEGY_BREAKOUT_V1_VERSION,
        universe_code="PI_PM_CORE",
        as_of_date=as_of,
        benchmark_symbol="^NSEI",
        filter_config_hash="test-filter",
        normalization_method="percentile",
        status=RankingRunStatus.COMPLETED.value,
        regime_label="BULL_LOW_VOL",
        inputs_hash="hash-null-ret",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    db_session.add(run)
    db_session.flush()

    db_session.add(
        RankingResult(
            ranking_run_id=run.id,
            stock_id=stock.id,
            rank=1,
            score=Decimal("10"),
            created_at=datetime.now(UTC),
        )
    )
    db_session.add(
        RankingPerformanceSnapshot(
            ranking_run_id=run.id,
            stock_id=stock.id,
            return_20d=None,
            captured_at=datetime.now(UTC),
        )
    )
    report = RankingValidationReport(
        ranking_run_id=run.id,
        status=VALIDATION_STATUS_COMPLETED,
        regime_label="BULL_LOW_VOL",
        computed_at=datetime.now(UTC),
    )
    db_session.add(report)
    db_session.flush()
    db_session.add(
        ValidationHorizonMetric(
            validation_report_id=report.id,
            ranking_run_id=run.id,
            strategy_name=RANKING_STRATEGY_BREAKOUT_V1,
            strategy_version=RANKING_STRATEGY_BREAKOUT_V1_VERSION,
            regime_label="BULL_LOW_VOL",
            horizon=20,
            spread=0.0162,
            sample_size=120,
            computed_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    config, spec = _seed_e2_config(db_session)
    replay_service = RegimePolicyReplayService(
        db_session,
        RankingValidationRepository(db_session),
    )
    window = build_single_holdout_window(date(2024, 1, 1), date(2024, 12, 31), date(2025, 1, 1))
    result = replay_service.replay(
        policy_config_id=config.id,
        config=spec,
        window_spec=window,
        horizon=20,
        strategy_name=spec.strategy_name,
        strategy_version=spec.strategy_version,
        universe_code="PI_PM_CORE",
        horizon_spreads_by_report={report.id: 0.0162},
        horizon_sample_sizes_by_report={report.id: 120},
    )

    assert result.days_included == 1
    assert result.train_metrics.ranked_days == 1
    assert result.train_metrics.sample_count == 120
    assert result.day_results[0].decision.action == "ALLOW"
    assert result.day_results[0].included is True


def test_replay_window_spec_supports_future_walk_forward():
    window = build_single_holdout_window(date(2024, 1, 1), date(2025, 12, 31), date(2025, 1, 1))
    payload = window.to_dict()
    assert payload["mode"] == "single_holdout"
    assert payload["rolling_window_days"] is None
    assert payload["walk_forward_step_days"] is None
    assert window.split_dates(date(2024, 6, 1)) == "train"
    assert window.split_dates(date(2025, 6, 1)) == "holdout"
