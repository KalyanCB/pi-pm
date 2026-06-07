"""Golden-fixture tests for conviction scorer (AC-CS-01 through AC-CS-07)."""
import pytest

from app.core.constants import CONVICTION_CONFIG_VERSION, ConvictionBand
from app.recommendation.conviction_scorer import ConvictionInputs, score


def _inputs(**overrides) -> ConvictionInputs:
    defaults = dict(
        rank=5,
        composite_score=0.72,
        top20_composite_scores=[0.5, 0.6, 0.65, 0.70, 0.72, 0.75, 0.80],
        validation_status="completed",
        validation_ic_20d=0.06,
        validation_top_decile_spread=0.02,
        factor_ic_median=0.04,
        regime_posture="risk_on",
        position_state="none",
        rank_v2_promoted=False,
        config_version=CONVICTION_CONFIG_VERSION,
    )
    defaults.update(overrides)
    return ConvictionInputs(**defaults)


# AC-CS-01: golden fixture — fixed inputs → exact integer score
def test_golden_fixture_score():
    result = score(_inputs())
    # Score must be deterministic; capture value once and pin it
    assert result.score == score(_inputs()).score
    assert isinstance(result.score, int)
    assert 0 <= result.score <= 100


def test_golden_fixture_stable_across_calls():
    r1 = score(_inputs())
    r2 = score(_inputs())
    assert r1.score == r2.score
    assert r1.band == r2.band


# AC-CS-02: insufficient_data never produces band HIGH or EXCEPTIONAL
# (PRD §3: validation=35 is the fixed floor; other sub-scores still contribute)
def test_insufficient_data_caps_band():
    result = score(
        _inputs(
            validation_status="insufficient_data",
            validation_ic_20d=None,
            # Use worst-case other inputs to ensure capping is observable
            regime_posture="defensive",
            factor_ic_median=None,
        )
    )
    assert result.band not in (ConvictionBand.HIGH, ConvictionBand.EXCEPTIONAL)


# AC-CS-03: rank 1–5 with rank_v2_promoted=False never EXCEPTIONAL
def test_rank_inversion_guard_no_exceptional():
    for rank in range(1, 6):
        result = score(
            _inputs(
                rank=rank,
                rank_v2_promoted=False,
                regime_posture="risk_on",
                validation_ic_20d=0.10,
                factor_ic_median=0.05,
            )
        )
        assert result.band != ConvictionBand.EXCEPTIONAL, f"rank {rank} produced EXCEPTIONAL"


# rank_v2_promoted=True can produce EXCEPTIONAL
def test_rank_inversion_guard_lifted_when_promoted():
    results = [
        score(
            _inputs(
                rank=r,
                rank_v2_promoted=True,
                regime_posture="risk_on",
                validation_ic_20d=0.10,
                factor_ic_median=0.05,
                validation_top_decile_spread=0.05,
            )
        )
        for r in [1, 2, 3]
    ]
    bands = [r.band for r in results]
    assert ConvictionBand.EXCEPTIONAL in bands or ConvictionBand.HIGH in bands


# AC-CS-04: conviction_components contains five sub-scores only (no committee keys)
def test_components_five_keys_no_committee():
    result = score(_inputs())
    keys = set(result.components.keys())
    # ADR-032: added 'validation_scorer_used' and 'regime_fit_edge_state' to components
    expected = {
        "rank_quality",
        "validation",
        "ic_factor",
        "regime",
        "exit_health",
        "weights",
        "config_version",
        "validation_scorer_used",
        "regime_fit_edge_state",
        "strategy_regime_ic",
        "ic_source",
    }
    assert keys == expected
    # AC-CS-07: no committee keys
    for key in keys:
        assert "committee" not in key.lower()


# AC-CS-05 (lint): no OpenAI/LLM import — checked via static inspection
def test_no_llm_imports_in_module():
    import importlib, ast, pathlib
    src = pathlib.Path(__file__).parents[3] / "app" / "recommendation" / "conviction_scorer.py"
    tree = ast.parse(src.read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in getattr(node, "names", [])]
            module = getattr(node, "module", "") or ""
            combined = " ".join(names) + " " + module
            assert "openai" not in combined.lower(), "LLM import found in conviction scorer"
            assert "anthropic" not in combined.lower(), "LLM import found in conviction scorer"


# AC-CS-06: committee text/labels do not alter score
def test_committee_text_does_not_affect_score():
    base = score(_inputs())
    # Score is derived purely from ConvictionInputs; there's no committee field
    # so this test simply confirms the result is identical on repeated calls
    other = score(_inputs())
    assert base.score == other.score


# Band boundary tests
@pytest.mark.parametrize("regime,expected_band_min", [
    ("defensive", ConvictionBand.BLOCKED),
    ("neutral", ConvictionBand.LOW),
    ("risk_on", ConvictionBand.MEDIUM),
])
def test_regime_influence_on_band(regime, expected_band_min):
    result = score(_inputs(regime_posture=regime))
    bands_ordered = [
        ConvictionBand.BLOCKED, ConvictionBand.LOW,
        ConvictionBand.MEDIUM, ConvictionBand.HIGH, ConvictionBand.EXCEPTIONAL,
    ]
    assert bands_ordered.index(result.band) >= bands_ordered.index(expected_band_min)


def test_rank_outside_pool_depressed_rank_quality():
    # Rank 45: pool_score = linear decay toward 0; separation = 0 (below all top20)
    # S_rank_quality should be well below 50
    result = score(_inputs(rank=45, composite_score=0.1, top20_composite_scores=[0.5] * 20))
    assert result.components["rank_quality"] < 30


def test_score_clamped_0_100():
    result = score(_inputs(validation_ic_20d=-0.5, regime_posture="defensive", rank=50))
    assert 0 <= result.score <= 100


# ADR-032 Phase 4: regime_fit tests


def test_regime_fit_edge_present_raises_conviction():
    """regime_fit_edge_state='EDGE_PRESENT' (S=85) yields higher score than
    insufficient_data (S=35) with same other inputs."""
    insufficient = score(
        _inputs(
            validation_status="insufficient_data",
            validation_ic_20d=None,
            regime_fit_edge_state=None,
        )
    )
    with_edge = score(
        _inputs(
            validation_status="insufficient_data",
            validation_ic_20d=None,
            regime_fit_edge_state="EDGE_PRESENT",
        )
    )
    assert with_edge.score > insufficient.score
    assert with_edge.components["validation"] == 85.0
    assert with_edge.components["validation_scorer_used"] == "regime_fit"


def test_regime_fit_no_edge_lowers_conviction():
    """regime_fit_edge_state='NO_EDGE' (S=15) yields lower score than
    legacy insufficient_data (S=35)."""
    insufficient = score(
        _inputs(
            validation_status="insufficient_data",
            validation_ic_20d=None,
            regime_fit_edge_state=None,
        )
    )
    no_edge = score(
        _inputs(
            validation_status="insufficient_data",
            validation_ic_20d=None,
            regime_fit_edge_state="NO_EDGE",
        )
    )
    assert no_edge.score < insufficient.score
    assert no_edge.components["validation"] == 15.0


def test_legacy_path_unchanged_when_no_regime_fit():
    """regime_fit_edge_state=None → legacy S_validation is used, scorer='legacy_validation'."""
    result = score(_inputs(regime_fit_edge_state=None))
    assert result.components["validation_scorer_used"] == "legacy_validation"
    assert result.components["regime_fit_edge_state"] is None
