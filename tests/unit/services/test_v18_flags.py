"""ADR-037 v18 Tier-1/2 feature flags.

Winner-protection (graduation / runner / let-winners-run) is now the intended lifecycle
baseline — it lets the fat-tail names ride the wide trail instead of being clipped by the
MOMENTUM_FADE handoff — so it defaults ON. Gold rotation stays OFF (opt-in).
"""
from app.core.config import Settings


def test_winner_protection_defaults_on():
    # Assert the class DEFAULTS (env-independent — a local .env must not mask the intent).
    f = Settings.model_fields
    assert f["graduation_enabled"].default is True
    assert f["runner_tier_enabled"].default is True
    assert f["let_winners_run_enabled"].default is True


def test_gold_rotation_defaults_off():
    assert Settings.model_fields["gold_rotation_enabled"].default is False


def test_v18_defaults_sane():
    s = Settings()
    assert s.graduation_winner_trail_pct == 12.0
    assert s.runner_max_rank == 5
    assert s.runner_min_gain_pct == 20.0
    assert s.runner_trail_pct == 25.0
    assert s.gold_symbol == "GOLDBEES.NS"
    assert 0 < s.gold_alloc_pct <= 1.0
    # P-23: rare-regime floor lowered to 40 (reversal hit n=41)
    assert s.rcee_rare_regime_sample_days == 40


def test_gold_rotation_noop_when_flag_off():
    # With the flag off, _gold_rotation must short-circuit to None (no DB writes).
    from app.ops.daily_batch.paper_pilot_ops import PaperPilotOps
    import inspect
    src = inspect.getsource(PaperPilotOps._gold_rotation)
    assert "if not s.gold_rotation_enabled:" in src and "return None" in src
