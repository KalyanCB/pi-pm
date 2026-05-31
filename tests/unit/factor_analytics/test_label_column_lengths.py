from app.factor_analytics.metrics_engine import coverage_label, stability_label


def test_coverage_label_fits_varchar32():
    for pct in (0.03, 0.10, 0.20):
        label = coverage_label(pct)
        assert label is not None
        assert len(label) <= 32


def test_stability_label_fits_varchar32():
    for score in (0.75, 0.60, 0.40):
        label = stability_label(score)
        assert label is not None
        assert len(label) <= 32


def test_adequate_coverage_exceeds_legacy_varchar16():
    label = coverage_label(0.20)
    assert label == "adequate_coverage"
    assert len(label) > 16
