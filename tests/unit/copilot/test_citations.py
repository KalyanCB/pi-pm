"""Tests for citation validator."""

from app.copilot.citations import citations_to_dicts, validate


def test_extracts_inline_citations():
    answer = "The rank is 5 [source: ranking_results.rank = 5] for this stock."
    result = validate(answer)
    assert len(result.citations) == 1
    assert result.citations[0].table == "ranking_results"
    assert result.citations[0].field == "rank"
    assert result.citations[0].value == "5"


def test_multiple_citations():
    answer = (
        "Conviction is 74 [source: recommendation_results.conviction_score = 74] "
        "and band is HIGH [source: recommendation_results.conviction_band = HIGH]."
    )
    result = validate(answer)
    assert len(result.citations) == 2


def test_answer_hash_stable():
    answer = "The conviction is 81 [source: recommendation_results.conviction_score = 81]."
    r1 = validate(answer)
    r2 = validate(answer)
    assert r1.answer_hash == r2.answer_hash


def test_answer_hash_different_for_different_answers():
    r1 = validate("Answer one [source: t.f = 1].")
    r2 = validate("Answer two [source: t.f = 2].")
    assert r1.answer_hash != r2.answer_hash


def test_citations_to_dicts():
    answer = "Rank is 3 [source: ranking_results.rank = 3]."
    result = validate(answer)
    dicts = citations_to_dicts(result.citations)
    assert dicts[0]["source_table"] == "ranking_results"
    assert dicts[0]["source_field"] == "rank"


def test_no_citations_empty_list():
    answer = "No numeric claims here."
    result = validate(answer)
    assert result.citations == []


def test_safe_years_not_flagged():
    answer = "As of 2026-06-05, the validation was completed."
    result = validate(answer)
    # Years should not be flagged as uncited claims
    year_claims = [c for c in result.uncited_claims if c in {"2026", "2025", "2024"}]
    assert year_claims == []
