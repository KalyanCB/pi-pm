from app.args.analytics.committee_effectiveness import (
    CommitteeReviewSnapshot,
    compute_committee_uniqueness_score,
    compute_packet_metrics,
    evidence_refs,
    jaccard_similarity,
    summarize_run_metrics,
    tokenize_text,
)


def _review(
    code: str,
    *,
    findings: str = "",
    strengths: list[str] | None = None,
    risks: list[str] | None = None,
    evidence: list[dict] | None = None,
    confidence: float = 0.5,
) -> CommitteeReviewSnapshot:
    return CommitteeReviewSnapshot(
        committee_code=code,
        symbol="TEST.NS",
        packet_id="pkt-1",
        findings=findings,
        strengths=strengths or [],
        risks=risks or [],
        supporting_evidence=evidence or [],
        confidence=confidence,
    )


def test_tokenize_strips_stopwords():
    tokens = tokenize_text("The ranking and momentum surge")
    assert "ranking" in tokens
    assert "momentum" in tokens
    assert "the" not in tokens


def test_jaccard_identical_sets():
    a = tokenize_text("volume surge breakout")
    assert jaccard_similarity(a, a) == 1.0


def test_uniqueness_high_when_peers_differ():
    review = _review(
        "TARC",
        findings="breakout volume expansion technical rank",
        strengths=["volume surge", "relative strength"],
        risks=["weak atr expansion"],
        evidence=[{"ref": "ranking:volume_surge"}],
        confidence=0.8,
    )
    peer = _review(
        "FRC",
        findings="profitability balance sheet valuation earnings",
        strengths=["roe improvement", "margin expansion"],
        risks=["high debt load"],
        evidence=[{"ref": "fundamentals:roe"}],
        confidence=0.6,
    )
    score = compute_committee_uniqueness_score(review, [peer])
    assert score["unique_evidence_count"] == 1
    assert score["composite_uniqueness"] > 0.5
    assert score["overlap_with_other_committees"] < 0.5


def test_uniqueness_low_when_peers_echo():
    shared = "ranking composite score regime bear low vol validation"
    review = _review(
        "TARC",
        findings=shared,
        strengths=["ranking composite score"],
        risks=["regime bear low vol"],
        evidence=[{"ref": "ranking:rank"}, {"ref": "regime:regime_label"}],
    )
    peer = _review(
        "QRC",
        findings=shared,
        strengths=["ranking composite score"],
        risks=["regime bear low vol"],
        evidence=[{"ref": "ranking:rank"}, {"ref": "regime:regime_label"}],
    )
    score = compute_committee_uniqueness_score(review, [peer])
    assert score["unique_evidence_count"] == 0
    assert score["overlap_with_other_committees"] > 0.7
    assert score["composite_uniqueness"] < 0.4


def test_packet_metrics_disagreement_lower_when_evidence_echoes():
    echo_a = _review(
        "TARC",
        findings="ranking composite regime validation",
        evidence=[{"ref": "ranking:rank"}, {"ref": "regime:regime_label"}],
    )
    echo_b = _review(
        "QRC",
        findings="ranking composite regime validation",
        evidence=[{"ref": "ranking:rank"}, {"ref": "regime:regime_label"}],
    )
    low = compute_packet_metrics([echo_a, echo_b])["disagreement_score"]

    distinct_a = _review(
        "TARC",
        findings="technical momentum volume breakout",
        evidence=[{"ref": "technical:volume_surge"}],
    )
    distinct_b = _review(
        "RC",
        findings="drawdown liquidity concentration veto",
        evidence=[{"ref": "risk:max_drawdown"}],
    )
    high = compute_packet_metrics([distinct_a, distinct_b])["disagreement_score"]
    assert high > low


def test_summarize_run_headline_disagreement_rate():
    pkt_a = [
        _review("TARC", findings="echo one", confidence=0.7),
        _review("QRC", findings="echo one", confidence=0.71),
    ]
    pkt_b = [
        _review("TARC", findings="technical breakout volume", confidence=0.9),
        _review("RC", findings="liquidity drawdown veto risk", confidence=0.2),
    ]
    summary = summarize_run_metrics({"p1": pkt_a, "p2": pkt_b}, disagreement_threshold=0.25)
    assert summary["packet_count"] == 2
    assert 0.0 <= summary["headline_disagreement_rate"] <= 1.0


def test_evidence_refs_from_dict():
    refs = evidence_refs([{"ref": "ranking:rank"}, {"evidence_ref": "regime:label"}])
    assert refs == {"ranking:rank", "regime:label"}


def test_uniqueness_accepts_dict_payload():
    review = {
        "committee_code": "NRCC",
        "findings": "macro sector headline catalyst",
        "strengths": ["sector tailwind"],
        "risks": ["macro headwind"],
        "supporting_evidence": [{"ref": "news:headline"}],
        "confidence": 0.55,
    }
    peer = {
        "committee_code": "TARC",
        "findings": "ranking momentum technical",
        "strengths": ["momentum"],
        "risks": ["volatility"],
        "supporting_evidence": [{"ref": "ranking:rank"}],
        "confidence": 0.8,
    }
    score = compute_committee_uniqueness_score(review, [peer])
    assert score["committee_code"] == "NRCC"
    assert score["unique_evidence_count"] >= 1
