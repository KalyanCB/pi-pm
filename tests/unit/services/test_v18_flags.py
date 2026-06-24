"""ADR-037 v18 Tier-1/2 features are flag-gated and default OFF (v17 baseline safe)."""
from app.core.config import Settings


def test_v18_flags_default_off():
    s = Settings()
    assert s.graduation_enabled is False
    assert s.runner_tier_enabled is False
    assert s.gold_rotation_enabled is False


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
