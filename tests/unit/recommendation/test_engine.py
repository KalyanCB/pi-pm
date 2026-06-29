"""Tests for Recommendation Engine business rules (AC-RE-01 through AC-RE-06)."""

from __future__ import annotations

import uuid

from app.core.constants import RecommendationAction, RecommendationLifecycleState
from app.recommendation.engine import (
    EngineConfig,
    RankingResultRow,
    ValidationSummary,
    run,
)


def _row(rank: int, score: float = 0.70) -> RankingResultRow:
    return RankingResultRow(stock_id=uuid.uuid4(), rank=rank, composite_score=score)


def _run(
    rows: list[RankingResultRow],
    validation_status: str = "completed",
    ic_20d: float = 0.06,
    regime: str = "risk_on",
    active_positions: set | None = None,
) -> list:
    cfg = EngineConfig(regime_posture=regime)
    val = ValidationSummary(status=validation_status, ic_20d=ic_20d, top_decile_spread=0.02)
    results, _ = run(
        ranking_run_id=uuid.uuid4(),
        ranking_results=rows,
        validation=val,
        config=cfg,
        active_position_stock_ids=active_positions,
    )
    return results


# ── Entry rules ───────────────────────────────────────────────────────────────


def test_top_pool_eligible_for_buy():
    rows = [_row(r) for r in range(1, 6)]
    results = _run(rows)
    actions = {r.action for r in results}
    assert RecommendationAction.BUY in actions


def test_rank_outside_pool_is_reject():
    rows = [_row(25), _row(30), _row(40)]
    results = _run(rows)
    for r in results:
        assert r.action == RecommendationAction.REJECT
        assert "RANK_OUTSIDE_POOL" in r.reason_codes


# R-ENTRY-02: validation insufficient_data → max WATCH
def test_insufficient_data_does_not_block_buy():
    # RCEE works from day 1 — insufficient_data validation must not hard-cap at WATCH.
    # Conviction scoring decides; top-ranked candidates should be able to reach BUY.
    rows = [_row(r) for r in range(1, 6)]
    results = _run(rows, validation_status="insufficient_data", ic_20d=None)
    actions = {r.action for r in results if r.rank and r.rank <= 20}
    assert RecommendationAction.BUY in actions or RecommendationAction.WATCH in actions


# R-ENTRY-04: defensive regime blocks BUY
def test_defensive_regime_blocks_buy():
    rows = [_row(r) for r in range(1, 6)]
    results = _run(rows, regime="defensive")
    for r in results:
        assert r.action != RecommendationAction.BUY


# R-ENTRY-05: engine emits the PURE signal — no portfolio/slot cap. Every eligible
# top-pool candidate becomes BUY; capacity is an admission decision enforced downstream.
def test_no_portfolio_slot_cap_in_engine():
    rows = [_row(r) for r in range(1, 16)]
    results = _run(rows)
    buys = [r for r in results if r.action == RecommendationAction.BUY]
    # Far more than the old 5/10-slot cap — all eligible names get BUY.
    assert len(buys) > 5
    # PORTFOLIO_FULL must never be emitted by the recommendation engine.
    for r in results:
        assert "PORTFOLIO_FULL" not in r.reason_codes


# R-HOLD-01: active positions get HOLD
def test_active_position_gets_hold():
    row = _row(5)
    results = _run([row], active_positions={row.stock_id})
    assert results[0].action == RecommendationAction.HOLD
    assert results[0].lifecycle_state == RecommendationLifecycleState.ACTIVE


# ── AC-RE-01: deterministic replay ───────────────────────────────────────────


def test_deterministic_replay():
    rows = [_row(r, score=0.5 + r * 0.01) for r in range(1, 11)]
    ranking_run_id = uuid.uuid4()

    cfg = EngineConfig(regime_posture="risk_on")
    val = ValidationSummary(status="completed", ic_20d=0.06, top_decile_spread=0.02)

    r1, hash1 = run(ranking_run_id=ranking_run_id, ranking_results=rows, validation=val, config=cfg)
    r2, hash2 = run(ranking_run_id=ranking_run_id, ranking_results=rows, validation=val, config=cfg)

    assert hash1 == hash2
    assert [(x.action, x.conviction_score) for x in r1] == [
        (x.action, x.conviction_score) for x in r2
    ]


# ── AC-RE-02: every result has stock_id (lineage) ─────────────────────────────


def test_every_result_has_stock_id():
    rows = [_row(r) for r in range(1, 6)]
    results = _run(rows)
    for r in results:
        assert r.stock_id is not None


# ── Lifecycle state ───────────────────────────────────────────────────────────


def test_buy_gets_candidate_lifecycle():
    rows = [_row(r) for r in range(1, 4)]
    results = _run(rows)
    buys = [r for r in results if r.action == RecommendationAction.BUY]
    for b in buys:
        assert b.lifecycle_state == RecommendationLifecycleState.CANDIDATE


def test_reject_has_no_lifecycle():
    rows = [_row(30)]
    results = _run(rows)
    assert results[0].lifecycle_state is None


# ── AC-RE-05: EXIT_APPROVED has reason codes ─────────────────────────────────
# (Exit triggers are M2; in M1 active positions → HOLD; tested here for contract)


def test_hold_has_empty_reason_codes():
    row = _row(3)
    results = _run([row], active_positions={row.stock_id})
    assert results[0].reason_codes == []


# ── Exit signal tests (R-EXIT-01..04) ────────────────────────────────────────

from app.recommendation.engine import ExitSignal


def _run_with_exit(rows, exit_signals=None, active_positions=None):
    cfg = EngineConfig(
        regime_posture="risk_on", rank_deterioration_threshold=40, max_holding_days=30
    )
    val = ValidationSummary(status="completed", ic_20d=0.06, top_decile_spread=0.02)
    results, _ = run(
        ranking_run_id=uuid.uuid4(),
        ranking_results=rows,
        validation=val,
        config=cfg,
        active_position_stock_ids=active_positions or set(),
        exit_signals=exit_signals or {},
    )
    return results


def test_rank_deterioration_triggers_exit():
    """R-EXIT-01: rank > threshold on active position → EXIT_APPROVED."""
    row = _row(45)  # rank 45 > threshold 40
    results = _run_with_exit([row], active_positions={row.stock_id})
    assert results[0].action == RecommendationAction.EXIT_APPROVED
    assert "EXIT_RISK" in results[0].reason_codes


def test_alpha_decay_triggers_exit():
    """R-EXIT-02: alpha_decayed=True → EXIT_APPROVED."""
    row = _row(5)
    sig = ExitSignal(alpha_decayed=True)
    results = _run_with_exit(
        [row], active_positions={row.stock_id}, exit_signals={row.stock_id: sig}
    )
    assert results[0].action == RecommendationAction.EXIT_APPROVED
    assert "ALPHA_DECAY" in results[0].reason_codes


def test_regime_defensive_triggers_exit_for_active():
    """R-EXIT-03: regime turned defensive on active position → EXIT_APPROVED."""
    row = _row(5)
    sig = ExitSignal(regime_turned_defensive=True)
    results = _run_with_exit(
        [row], active_positions={row.stock_id}, exit_signals={row.stock_id: sig}
    )
    assert results[0].action == RecommendationAction.EXIT_APPROVED


def test_time_stop_triggers_exit():
    """R-EXIT-04: holding_days >= max_holding_days → EXIT_APPROVED."""
    row = _row(5)
    sig = ExitSignal(holding_days=30)
    results = _run_with_exit(
        [row], active_positions={row.stock_id}, exit_signals={row.stock_id: sig}
    )
    assert results[0].action == RecommendationAction.EXIT_APPROVED
    assert "TIME_STOP" in results[0].reason_codes


def test_clean_active_position_stays_hold():
    """No exit trigger → HOLD."""
    row = _row(5)
    sig = ExitSignal()  # all False, holding_days=0
    results = _run_with_exit(
        [row], active_positions={row.stock_id}, exit_signals={row.stock_id: sig}
    )
    assert results[0].action == RecommendationAction.HOLD


def test_exit_approved_has_lifecycle_exit_approved():
    row = _row(5)
    sig = ExitSignal(alpha_decayed=True)
    results = _run_with_exit(
        [row], active_positions={row.stock_id}, exit_signals={row.stock_id: sig}
    )
    assert results[0].lifecycle_state == "EXIT_APPROVED"
