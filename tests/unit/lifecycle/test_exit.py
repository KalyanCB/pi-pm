from __future__ import annotations

import pytest

from app.lifecycle.exit import (
    EXIT_B1_FADE,
    EXIT_RV1_RECOVERED,
    b1_has_peaked,
    exit_rank_strategy,
    pct_from_rank,
    should_exit_on_handoff,
)

BV2, BV1 = "breakout_v2", "breakout_v1"
RV3, RV1 = "reversion_v3", "reversal_v1"


# ── handoff routing (enter on new, exit on OLD active rank) ───────────────────
@pytest.mark.parametrize("entry,exit_rank", [
    (BV2, BV1),     # breakout enters on v2, exits on v1
    (RV3, RV1),     # reversion enters on v3, exits on reversal_v1
    ("momentum_v3", None),
    (None, None),
])
def test_exit_rank_strategy(entry, exit_rank):
    assert exit_rank_strategy(entry) == exit_rank


def test_pct_from_rank():
    assert pct_from_rank(1, 100) == pytest.approx(1.0)     # best
    assert pct_from_rank(100, 100) == pytest.approx(0.0)    # worst
    assert pct_from_rank(50, 100) == pytest.approx(50 / 99, abs=1e-3)
    assert pct_from_rank(None, 100) is None
    assert pct_from_rank(1, 1) is None


def test_b1_has_peaked():
    assert b1_has_peaked(0.70) is True
    assert b1_has_peaked(0.65) is True
    assert b1_has_peaked(0.50) is False
    assert b1_has_peaked(None) is False


# ── breakout handoff: exit on B1 FADE, only after a spike ─────────────────────
def test_breakout_exits_on_b1_fade_after_spike():
    fired, reason = should_exit_on_handoff(entry_strategy=BV2, handoff_pct=0.30, has_peaked=True)
    assert fired and reason == EXIT_B1_FADE


def test_breakout_holds_while_b1_strong():
    fired, _ = should_exit_on_handoff(entry_strategy=BV2, handoff_pct=0.60, has_peaked=True)
    assert fired is False


def test_breakout_not_cut_if_never_spiked():
    # B1 low but it never fired -> leave it to the stop/cap, don't handoff-exit
    fired, _ = should_exit_on_handoff(entry_strategy=BV2, handoff_pct=0.20, has_peaked=False)
    assert fired is False


# ── reversion handoff: exit on RV1 RECOVERY, after grace ──────────────────────
def test_reversion_exits_when_recovered_after_grace():
    fired, reason = should_exit_on_handoff(entry_strategy=RV3, handoff_pct=0.30, days_held=10)
    assert fired and reason == EXIT_RV1_RECOVERED


def test_reversion_holds_within_grace():
    fired, _ = should_exit_on_handoff(entry_strategy=RV3, handoff_pct=0.30, days_held=2)
    assert fired is False


def test_reversion_holds_while_still_oversold():
    # RV1 still high (>= recover threshold) = still oversold -> hold for the bounce
    fired, _ = should_exit_on_handoff(entry_strategy=RV3, handoff_pct=0.70, days_held=10)
    assert fired is False


def test_non_lifecycle_strategy_no_handoff_exit():
    assert should_exit_on_handoff(entry_strategy="momentum_v3", handoff_pct=0.1, has_peaked=True) == (False, None)
