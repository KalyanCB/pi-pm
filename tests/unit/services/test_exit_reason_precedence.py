"""ADR-037: exit-reason precedence — gap-down stops must not be mislabelled RANK_DROP.

When multiple exit triggers fire on the same day (a gap-down trips both the stop-loss
and rank-drop), the recorded exit_reason must be the most *severe* one. Picking the
first-appended trigger mislabelled gap-down stops as RANK_DROP, which bypassed the
P-16 stop-loss re-entry cooldown.
"""

from app.services.paper_trade_service import _primary_exit_reason


def test_stop_loss_wins_over_rank_drop_on_gap_down():
    # rank-drop is appended first by _evaluate_triggers; stop-loss must still win
    assert _primary_exit_reason(["EXIT_RANK_DROP", "EXIT_STOP_LOSS"]) == "EXIT_STOP_LOSS"


def test_regime_wins_over_rank_drop():
    assert _primary_exit_reason(["EXIT_RANK_DROP", "EXIT_REGIME"]) == "EXIT_REGIME"


def test_stop_loss_top_priority_among_many():
    assert _primary_exit_reason(
        ["EXIT_ALPHA_DECAY", "EXIT_RANK_DROP", "EXIT_STOP_LOSS"]
    ) == "EXIT_STOP_LOSS"


def test_single_trigger_passthrough():
    assert _primary_exit_reason(["EXIT_RANK_DROP"]) == "EXIT_RANK_DROP"


def test_trailing_over_rank_drop():
    assert _primary_exit_reason(["EXIT_RANK_DROP", "EXIT_TRAILING_STOP"]) == "EXIT_TRAILING_STOP"


def test_empty_and_unknown():
    assert _primary_exit_reason([]) is None
    assert _primary_exit_reason(None) is None
    assert _primary_exit_reason(["WEIRD_NEW_TRIGGER"]) == "WEIRD_NEW_TRIGGER"
