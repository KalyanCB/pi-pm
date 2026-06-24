"""Tests for the Trade Decision Layer (ADR-037 P-21).

Edge cases are drawn directly from the replay backtest findings:
cold-start thin samples, outlier-inflated buckets, cross-strategy dedup,
all-negative-EV regimes, the rank-vs-expectancy inversion, and determinism.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from app.recommendation.trade_prioritizer import (
    TradeCandidate,
    evaluate_eligibility,
    prioritize,
    rank_bucket,
)


def _cand(rank=1, conviction=70.0, strategy="breakout_v1", regime="BULL_LOW_VOL",
          stock_id=None, last_price=100.0, sma50=90.0, segment_state="UP",
          volume_today=1000.0, volume_avg90=1000.0, rs=1.0, symbol="X",
          adv_value=5.0e7):
    return TradeCandidate(
        stock_id=stock_id or uuid4(),
        symbol=symbol,
        strategy_name=strategy,
        rank=rank,
        conviction_score=conviction,
        market_regime=regime,
        recommendation_id=uuid4(),
        last_price=last_price,
        sma50=sma50,
        segment_state=segment_state,
        volume_today=volume_today,
        volume_avg90=volume_avg90,
        rs_vs_universe=rs,
        adv_value=adv_value,
    )


class _Provider:
    """Static expectancy map: (strategy, regime, bucket) -> (return, n)."""

    def __init__(self, table):
        self.table = table

    def expected_return(self, strategy, regime, bucket, segment_state):
        return self.table.get((strategy, regime, bucket), (None, 0))


# ── Rank bucketing ──────────────────────────────────────────────────────────

def test_rank_bucketing():
    assert rank_bucket(1) == "1-5"
    assert rank_bucket(5) == "1-5"
    assert rank_bucket(6) == "6-10"
    assert rank_bucket(20) == "11-20"
    assert rank_bucket(21) == ">20"


# ── Eligibility veto (altitude 2) ───────────────────────────────────────────

def test_eligibility_passes_healthy():
    r = evaluate_eligibility(_cand(), breadth_pct=0.60)
    assert r.eligible is True


def test_eligibility_vetoes_below_sma50():
    r = evaluate_eligibility(_cand(last_price=80.0, sma50=90.0))
    assert r.eligible is False
    assert "BELOW_SMA50" in r.reasons


def test_eligibility_vetoes_low_breadth_marketwide():
    r = evaluate_eligibility(_cand(), breadth_pct=0.30)
    assert r.eligible is False
    assert any("LOW_BREADTH" in x for x in r.reasons)


def test_eligibility_vetoes_segment_downtrend_and_negative_rs():
    r = evaluate_eligibility(_cand(segment_state="DOWN", rs=-2.0))
    assert r.eligible is False
    assert "SEGMENT_DOWNTREND" in r.reasons
    assert "NEGATIVE_RS" in r.reasons


def test_eligibility_vetoes_nano_cap_below_adv_floor():
    # ₹1cr/day < ₹2cr floor → vetoed (the 22%-win noise tier)
    r = evaluate_eligibility(_cand(adv_value=1.0e7))
    assert r.eligible is False
    assert any("BELOW_ADV_FLOOR" in x for x in r.reasons)


def test_eligibility_passes_above_adv_floor():
    r = evaluate_eligibility(_cand(adv_value=3.0e7), breadth_pct=0.6)
    assert r.eligible is True


def test_adv_floor_applies_to_all_strategies():
    # even a mean-reversion candidate is vetoed if it's an illiquid nano-cap
    r = evaluate_eligibility(
        _cand(strategy="reversal_v1", adv_value=0.5e7, segment_state="UNKNOWN", rs=None),
        require_uptrend=False,
    )
    assert r.eligible is False
    assert any("BELOW_ADV_FLOOR" in x for x in r.reasons)


def test_eligibility_fails_open_on_missing_data():
    # No price/sma/volume/breadth → cannot veto → eligible (degrade gracefully)
    c = _cand(last_price=None, sma50=None, volume_today=None, volume_avg90=None,
              segment_state="UNKNOWN", rs=None)
    assert evaluate_eligibility(c, breadth_pct=None).eligible is True


# ── Prioritization: the rank-vs-expectancy inversion (the user's example) ────

def test_lower_rank_higher_expectancy_wins():
    """Rank #2 historically returns 5-6%; rank #8 returns 8-10%. The #8 must
    sort ABOVE the #2 because expected value, not rank, is the sort key."""
    s1 = uuid4(); s2 = uuid4()
    high_rank = _cand(rank=2, conviction=80.0, stock_id=s1, symbol="HIGHRANK")
    low_rank = _cand(rank=8, conviction=70.0, stock_id=s2, symbol="LOWRANK")
    provider = _Provider({
        ("breakout_v1", "BULL_LOW_VOL", "1-5"): (0.055, 100),
        ("breakout_v1", "BULL_LOW_VOL", "6-10"): (0.090, 100),
    })
    q = prioritize([high_rank, low_rank], provider)
    assert [pc.candidate.symbol for pc in q] == ["LOWRANK", "HIGHRANK"]
    assert q[0].expected_return == 0.090


# ── Cold start / thin samples ───────────────────────────────────────────────

def test_thin_bucket_falls_back_to_conviction():
    """Below the sample floor, EV is untrusted → order by conviction so cold-start
    days still trade rather than freezing."""
    a = _cand(rank=3, conviction=60.0, symbol="A")
    b = _cand(rank=4, conviction=85.0, symbol="B")
    provider = _Provider({})  # no data → all thin
    q = prioritize([a, b], provider, expectancy_sample_floor=25)
    assert [pc.candidate.symbol for pc in q] == ["B", "A"]
    assert all(pc.sort_basis == "conviction_fallback" for pc in q)


def test_ev_known_outranks_ev_unknown():
    known = _cand(rank=10, conviction=50.0, symbol="KNOWN")
    unknown = _cand(rank=1, conviction=95.0, symbol="UNKNOWN")
    provider = _Provider({("breakout_v1", "BULL_LOW_VOL", "6-10"): (0.04, 100)})
    q = prioritize([known, unknown], provider)
    # EV-known (even at +4% / low conviction) sorts ahead of a high-conviction unknown
    assert q[0].candidate.symbol == "KNOWN"


# ── All-negative-EV regime: take nothing ────────────────────────────────────

def test_negative_ev_dropped_take_nothing():
    a = _cand(rank=2, symbol="A")
    provider = _Provider({("breakout_v1", "BULL_LOW_VOL", "1-5"): (-0.03, 100)})
    q = prioritize([a], provider, drop_negative_ev=True)
    assert q == []  # known-negative expectancy → sit in cash


def test_negative_ev_kept_when_flag_off():
    a = _cand(rank=2, symbol="A")
    provider = _Provider({("breakout_v1", "BULL_LOW_VOL", "1-5"): (-0.03, 100)})
    q = prioritize([a], provider, drop_negative_ev=False)
    assert len(q) == 1


# ── Cross-strategy dedup + consensus ────────────────────────────────────────

def test_dedup_same_stock_keeps_best_and_tags_consensus():
    sid = uuid4()
    via_breakout = _cand(rank=5, conviction=70.0, strategy="breakout_v1",
                         stock_id=sid, symbol="DUP")
    via_momentum = _cand(rank=2, conviction=90.0, strategy="momentum_v1",
                         stock_id=sid, symbol="DUP")
    provider = _Provider({})  # thin → conviction fallback picks the 90 one
    q = prioritize([via_breakout, via_momentum], provider)
    assert len(q) == 1
    assert q[0].consensus_count == 2
    assert "CROSS_STRATEGY_CONSENSUS" in q[0].reasons
    assert q[0].candidate.conviction_score == 90.0


# ── Determinism ─────────────────────────────────────────────────────────────

def test_deterministic_ordering_on_ties():
    # Two identical-conviction, identical-rank candidates with fixed ids → stable order
    s1 = UUID("00000000-0000-0000-0000-000000000001")
    s2 = UUID("00000000-0000-0000-0000-000000000002")
    a = _cand(rank=3, conviction=70.0, stock_id=s1, symbol="A")
    b = _cand(rank=3, conviction=70.0, stock_id=s2, symbol="B")
    q1 = prioritize([a, b], _Provider({}))
    q2 = prioritize([b, a], _Provider({}))
    assert [pc.candidate.symbol for pc in q1] == [pc.candidate.symbol for pc in q2]


def test_outlier_protection_is_providers_job():
    """The prioritizer trusts the provider's expectancy; the provider is responsible
    for median/trimmed-mean so one ASAL-type +330% trade can't inflate a bucket.
    Here we assert the prioritizer uses the value as given (contract test)."""
    a = _cand(rank=2, symbol="A")
    provider = _Provider({("breakout_v1", "BULL_LOW_VOL", "1-5"): (0.02, 100)})
    q = prioritize([a], provider)
    assert q[0].expected_return == 0.02
