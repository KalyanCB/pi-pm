"""Tests for Recommendation Engine RCEE integration (ADR-032 Phase 3 & 4)."""

from __future__ import annotations

import uuid

import pytest

from app.core.constants import RecommendationAction, RecommendationConfidence
from app.recommendation.engine import (
    EngineConfig,
    ExitSignal,
    RankingResultRow,
    ValidationSummary,
    run,
)
from app.recommendation.regime_edge_engine import (
    EdgeState,
    RCEEConfig,
    RegimeFit,
)


def _make_regime_fit(
    edge_state: EdgeState,
    sample_days: int = 100,
    ic_lower_95: float | None = 0.019,
    hit_rate: float | None = 0.60,
    strategy_name: str = "breakout_v1",
    regime_label: str = "BULL_LOW_VOL",
) -> RegimeFit:
    cfg = RCEEConfig()
    return RegimeFit(
        strategy_name=strategy_name,
        regime_label=regime_label,
        avg_ic=0.028 if edge_state == EdgeState.EDGE_PRESENT else -0.05,
        ic_lower_95=ic_lower_95,
        hit_rate=hit_rate,
        expectancy=0.015,
        expectancy_after_costs=0.014,
        sample_days=sample_days,
        edge_state=edge_state,
        threshold_config={k: float(v) for k, v in cfg.__dict__.items()},
        gate_results={},
    )


def _row(rank: int, score: float = 0.70) -> RankingResultRow:
    return RankingResultRow(stock_id=uuid.uuid4(), rank=rank, composite_score=score)


def _run_with_fit(
    rows: list[RankingResultRow],
    regime_fit: RegimeFit | None,
    regime: str = "risk_on",
    validation_status: str = "insufficient_data",
    ic_20d: float | None = None,
) -> list:
    cfg = EngineConfig(
        regime_posture=regime,
        max_buy_slots=5,
        regime_fit=regime_fit,
    )
    val = ValidationSummary(status=validation_status, ic_20d=ic_20d, top_decile_spread=0.02)
    results, _ = run(
        ranking_run_id=uuid.uuid4(),
        ranking_results=rows,
        validation=val,
        config=cfg,
    )
    return results


# ── Core RCEE gate tests ──────────────────────────────────────────────────────


def test_no_edge_produces_watch_with_regime_no_edge_reason():
    """NO_EDGE regime_fit → WATCH + REGIME_NO_EDGE reason code for top-pool stocks."""
    rows = [_row(r) for r in range(1, 6)]
    fit = _make_regime_fit(EdgeState.NO_EDGE)
    results = _run_with_fit(rows, fit, regime="risk_on")
    for r in results:
        if r.rank and r.rank <= 20:
            assert r.action == RecommendationAction.WATCH
            assert "REGIME_NO_EDGE" in r.reason_codes


def test_edge_weak_produces_watch_with_low_expectancy_reason():
    """EDGE_WEAK → WATCH + LOW_EXPECTANCY reason code."""
    rows = [_row(r) for r in range(1, 6)]
    fit = _make_regime_fit(EdgeState.EDGE_WEAK)
    results = _run_with_fit(rows, fit, regime="risk_on")
    for r in results:
        if r.rank and r.rank <= 20:
            assert r.action == RecommendationAction.WATCH
            assert "LOW_EXPECTANCY" in r.reason_codes


def test_edge_present_allows_buy_path():
    """EDGE_PRESENT + risk_on regime → BUY eligible for top pool."""
    rows = [_row(r, score=0.5 + r * 0.01) for r in range(1, 6)]
    fit = _make_regime_fit(EdgeState.EDGE_PRESENT)
    results = _run_with_fit(
        rows, fit, regime="risk_on", validation_status="completed", ic_20d=0.06
    )
    buys = [r for r in results if r.action == RecommendationAction.BUY]
    assert len(buys) > 0


def test_fallback_to_legacy_when_no_regime_fit():
    """regime_fit=None → falls back to legacy R-ENTRY-02 validation gate behavior.

    With validation_status='insufficient_data', top-pool stocks should get WATCH.
    """
    rows = [_row(r) for r in range(1, 6)]
    results = _run_with_fit(rows, regime_fit=None, validation_status="insufficient_data")
    for r in results:
        if r.rank and r.rank <= 20:
            assert r.action in (RecommendationAction.WATCH, RecommendationAction.REJECT)
            assert r.action != RecommendationAction.BUY


def test_defensive_regime_allows_buy_when_edge_present():
    """EDGE_PRESENT + posture=defensive → R-ENTRY-04 skipped → BUY allowed.

    Rationale: reversal_v1 has EDGE_PRESENT in BEAR_LOW_VOL (defensive posture).
    The RCEE already confirmed this regime is suitable — R-ENTRY-04 would
    incorrectly block strategies designed for bear regimes.
    """
    rows = [_row(r, score=0.5 + r * 0.01) for r in range(1, 6)]
    fit = _make_regime_fit(EdgeState.EDGE_PRESENT)
    results = _run_with_fit(
        rows, fit, regime="defensive", validation_status="completed", ic_20d=0.06
    )
    buys = [r for r in results if r.action == RecommendationAction.BUY]
    assert len(buys) > 0, "EDGE_PRESENT should override defensive posture gate"


def test_defensive_regime_blocks_without_edge_present():
    """NO_EDGE + posture=defensive → R-ENTRY-04 still fires → WATCH (legacy behavior)."""
    rows = [_row(r, score=0.5 + r * 0.01) for r in range(1, 6)]
    fit = _make_regime_fit(EdgeState.NO_EDGE)
    results = _run_with_fit(
        rows, fit, regime="defensive", validation_status="completed", ic_20d=0.06
    )
    for r in results:
        assert r.action != RecommendationAction.BUY


def test_defensive_regime_blocks_without_regime_fit():
    """regime_fit=None + posture=defensive → R-ENTRY-04 fires → no BUY."""
    rows = [_row(r, score=0.5 + r * 0.01) for r in range(1, 6)]
    results = _run_with_fit(
        rows, None, regime="defensive", validation_status="completed", ic_20d=0.06
    )
    for r in results:
        assert r.action != RecommendationAction.BUY


def test_confidence_high_on_large_sample():
    """sample_days=250, EDGE_PRESENT → HIGH_CONFIDENCE on BUY."""
    rows = [_row(r, score=0.5 + r * 0.01) for r in range(1, 4)]
    fit = _make_regime_fit(EdgeState.EDGE_PRESENT, sample_days=250)
    results = _run_with_fit(
        rows, fit, regime="risk_on", validation_status="completed", ic_20d=0.06
    )
    buys = [r for r in results if r.action == RecommendationAction.BUY]
    assert len(buys) > 0
    for b in buys:
        assert b.recommendation_confidence == RecommendationConfidence.HIGH_CONFIDENCE.value


def test_confidence_validated_on_medium_sample():
    """sample_days=80, EDGE_PRESENT → VALIDATED."""
    rows = [_row(r, score=0.5 + r * 0.01) for r in range(1, 4)]
    fit = _make_regime_fit(EdgeState.EDGE_PRESENT, sample_days=80)
    results = _run_with_fit(
        rows, fit, regime="risk_on", validation_status="completed", ic_20d=0.06
    )
    buys = [r for r in results if r.action == RecommendationAction.BUY]
    assert len(buys) > 0
    for b in buys:
        assert b.recommendation_confidence == RecommendationConfidence.VALIDATED.value


def test_confidence_unknown_without_regime_fit():
    """No regime_fit → confidence=UNKNOWN on BUY path."""
    rows = [_row(r, score=0.5 + r * 0.01) for r in range(1, 4)]
    results = _run_with_fit(
        rows,
        regime_fit=None,
        regime="risk_on",
        validation_status="completed",
        ic_20d=0.06,
    )
    buys = [r for r in results if r.action == RecommendationAction.BUY]
    assert len(buys) > 0
    for b in buys:
        assert b.recommendation_confidence == RecommendationConfidence.UNKNOWN.value


# ── Conviction model integration ─────────────────────────────────────────────


def test_conviction_uses_regime_fit_score():
    """With EDGE_PRESENT, conviction components should show S_regime_fit=85."""
    rows = [_row(5, score=0.70)]
    fit = _make_regime_fit(EdgeState.EDGE_PRESENT, sample_days=100)
    results = _run_with_fit(rows, fit, regime="risk_on", validation_status="completed", ic_20d=0.06)
    r = results[0]
    assert r.conviction_components["validation"] == 85.0
    assert r.conviction_components["validation_scorer_used"] == "regime_fit"
    assert r.conviction_components["regime_fit_edge_state"] == "EDGE_PRESENT"


def test_no_edge_conviction_uses_s15():
    """NO_EDGE → S_regime_fit=15 in conviction components."""
    rows = [_row(5, score=0.70)]
    fit = _make_regime_fit(EdgeState.NO_EDGE)
    results = _run_with_fit(rows, fit, regime="risk_on")
    r = results[0]
    assert r.conviction_components["validation"] == 15.0
    assert r.conviction_components["validation_scorer_used"] == "regime_fit"


def test_legacy_conviction_uses_validation_scorer():
    """With regime_fit=None, conviction components show legacy validation scorer."""
    rows = [_row(5, score=0.70)]
    results = _run_with_fit(
        rows, regime_fit=None, regime="risk_on", validation_status="completed", ic_20d=0.06
    )
    r = results[0]
    assert r.conviction_components["validation_scorer_used"] == "legacy_validation"
    assert r.conviction_components["regime_fit_edge_state"] is None


# ── Determinism ───────────────────────────────────────────────────────────────


def test_deterministic_replay_with_regime_fit():
    """Same inputs with regime_fit → same hash and results."""
    rows = [_row(r, score=0.5 + r * 0.01) for r in range(1, 11)]
    ranking_run_id = uuid.uuid4()
    fit = _make_regime_fit(EdgeState.EDGE_PRESENT, sample_days=100)
    cfg = EngineConfig(regime_posture="risk_on", regime_fit=fit)
    val = ValidationSummary(status="completed", ic_20d=0.06, top_decile_spread=0.02)

    r1, hash1 = run(ranking_run_id=ranking_run_id, ranking_results=rows, validation=val, config=cfg)
    r2, hash2 = run(ranking_run_id=ranking_run_id, ranking_results=rows, validation=val, config=cfg)

    assert hash1 == hash2
    assert [(x.action, x.conviction_score) for x in r1] == [
        (x.action, x.conviction_score) for x in r2
    ]


def test_edge_state_in_input_hash():
    """Different edge states produce different input hashes."""
    rows = [_row(r) for r in range(1, 4)]
    ranking_run_id = uuid.uuid4()
    val = ValidationSummary(status="completed", ic_20d=0.06, top_decile_spread=0.02)

    cfg_edge = EngineConfig(
        regime_posture="risk_on",
        regime_fit=_make_regime_fit(EdgeState.EDGE_PRESENT),
    )
    cfg_no_edge = EngineConfig(
        regime_posture="risk_on",
        regime_fit=_make_regime_fit(EdgeState.NO_EDGE),
    )
    cfg_none = EngineConfig(regime_posture="risk_on", regime_fit=None)

    _, h1 = run(ranking_run_id=ranking_run_id, ranking_results=rows, validation=val, config=cfg_edge)
    _, h2 = run(ranking_run_id=ranking_run_id, ranking_results=rows, validation=val, config=cfg_no_edge)
    _, h3 = run(ranking_run_id=ranking_run_id, ranking_results=rows, validation=val, config=cfg_none)

    assert h1 != h2
    assert h1 != h3
    assert h2 != h3


# ── Exit symmetry (Phase 6) ──────────────────────────────────────────────────


def test_edge_degraded_exit_signal_triggers_exit_approved():
    """R-EXIT-05: edge_degraded=True on active position → EXIT_APPROVED."""
    from app.recommendation.engine import ExitSignal

    row = _row(5)
    sig = ExitSignal(edge_degraded=True)
    cfg = EngineConfig(
        regime_posture="risk_on",
        regime_fit=_make_regime_fit(EdgeState.NO_EDGE),
    )
    val = ValidationSummary(status="completed", ic_20d=0.06)
    results, _ = run(
        ranking_run_id=uuid.uuid4(),
        ranking_results=[row],
        validation=val,
        config=cfg,
        active_position_stock_ids={row.stock_id},
        exit_signals={row.stock_id: sig},
    )
    assert results[0].action == RecommendationAction.EXIT_APPROVED
    assert "EDGE_DEGRADED" in results[0].reason_codes


# ── Freshness check ───────────────────────────────────────────────────────────


def test_freshness_check_stale_age():
    """recommendation_age_days > max_age_days → STALE_AGE."""
    from app.recommendation.engine import RecommendationRow, check_recommendation_freshness

    result = RecommendationRow(
        stock_id=uuid.uuid4(),
        rank=3,
        composite_score=0.7,
        action="BUY",
        lifecycle_state="CANDIDATE",
        conviction_score=72,
        conviction_band="HIGH",
        conviction_components={},
        reason_codes=[],
    )
    current_rows = [_row(3)]
    current_rows[0].stock_id = result.stock_id
    fit = _make_regime_fit(EdgeState.EDGE_PRESENT)
    check = check_recommendation_freshness(
        result=result,
        current_ranking_rows=current_rows,
        regime_fit=fit,
        recommendation_age_days=5,
        max_age_days=3,
    )
    assert not check.is_fresh
    assert "STALE_AGE" in check.stale_reasons


def test_freshness_check_rank_exited_pool():
    """Stock no longer in top 20 → RANK_EXITED_POOL."""
    from app.recommendation.engine import RecommendationRow, check_recommendation_freshness

    sid = uuid.uuid4()
    result = RecommendationRow(
        stock_id=sid,
        rank=3,
        composite_score=0.7,
        action="BUY",
        lifecycle_state="CANDIDATE",
        conviction_score=72,
        conviction_band="HIGH",
        conviction_components={},
        reason_codes=[],
    )
    # Current ranking has this stock at rank 25 (outside pool)
    current_rows = [RankingResultRow(stock_id=sid, rank=25, composite_score=0.4)]
    fit = _make_regime_fit(EdgeState.EDGE_PRESENT)
    check = check_recommendation_freshness(
        result=result,
        current_ranking_rows=current_rows,
        regime_fit=fit,
        recommendation_age_days=1,
        max_age_days=3,
    )
    assert not check.is_fresh
    assert "RANK_EXITED_POOL" in check.stale_reasons


def test_freshness_check_regime_edge_lost():
    """NO_EDGE regime_fit → REGIME_EDGE_LOST."""
    from app.recommendation.engine import RecommendationRow, check_recommendation_freshness

    sid = uuid.uuid4()
    result = RecommendationRow(
        stock_id=sid,
        rank=3,
        composite_score=0.7,
        action="BUY",
        lifecycle_state="CANDIDATE",
        conviction_score=72,
        conviction_band="HIGH",
        conviction_components={},
        reason_codes=[],
    )
    current_rows = [RankingResultRow(stock_id=sid, rank=3, composite_score=0.7)]
    fit = _make_regime_fit(EdgeState.NO_EDGE)
    check = check_recommendation_freshness(
        result=result,
        current_ranking_rows=current_rows,
        regime_fit=fit,
        recommendation_age_days=1,
        max_age_days=3,
    )
    assert not check.is_fresh
    assert "REGIME_EDGE_LOST" in check.stale_reasons


def test_freshness_check_all_pass():
    """Fresh stock → is_fresh=True, no stale reasons."""
    from app.recommendation.engine import RecommendationRow, check_recommendation_freshness

    sid = uuid.uuid4()
    result = RecommendationRow(
        stock_id=sid,
        rank=3,
        composite_score=0.7,
        action="BUY",
        lifecycle_state="CANDIDATE",
        conviction_score=72,
        conviction_band="HIGH",
        conviction_components={},
        reason_codes=[],
    )
    current_rows = [RankingResultRow(stock_id=sid, rank=3, composite_score=0.7)]
    fit = _make_regime_fit(EdgeState.EDGE_PRESENT)
    check = check_recommendation_freshness(
        result=result,
        current_ranking_rows=current_rows,
        regime_fit=fit,
        recommendation_age_days=1,
        max_age_days=3,
    )
    assert check.is_fresh
    assert check.stale_reasons == []
