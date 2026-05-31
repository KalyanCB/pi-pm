from app.regime_policy.metrics import (
    bootstrap_metric_ci,
    build_research_findings,
    compare_spread_significance,
    compute_max_drawdown,
)
from app.regime_policy.models import MetricWithSignificance


def test_compute_max_drawdown():
    result = compute_max_drawdown([0.01, -0.02, 0.005, -0.03])
    assert result.max_drawdown is not None
    assert result.max_drawdown > 0


def test_bootstrap_metric_ci():
    values = [0.01, 0.015, 0.012, 0.008, 0.011]
    ci = bootstrap_metric_ci(values, n_bootstrap=500, seed=42)
    assert ci.value is not None
    assert ci.ci_lower is not None
    assert ci.ci_upper is not None
    assert ci.ci_lower <= ci.value <= ci.ci_upper


def test_compare_spread_significance_detects_improvement():
    baseline = [0.001, 0.002, 0.001, 0.002, 0.001]
    policy = [0.02, 0.025, 0.018, 0.022, 0.021]
    sig = compare_spread_significance(policy, baseline, n_bootstrap=500, seed=42)
    assert sig.value is not None
    assert sig.value > 0
    assert sig.p_value is not None
    assert sig.is_statistically_significant is True


def test_build_research_findings_promotes_on_significant_improvement():
    sig = MetricWithSignificance(
        value=0.014,
        ci_lower=0.005,
        ci_upper=0.023,
        p_value=0.01,
        is_statistically_significant=True,
    )
    findings = build_research_findings(
        policy_type="HARD_GATE_E2",
        baseline_spread=0.002,
        policy_spread=0.016,
        sample_count=237,
        ranked_days=50,
        spread_significance=sig,
    )
    assert findings["improvement"] == 0.014
    assert findings["recommendation"] == "promote_to_next_research_stage"
    assert findings["confidence"] in {"medium", "high"}
