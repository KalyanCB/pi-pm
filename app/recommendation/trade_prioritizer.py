"""Trade Decision Layer (ADR-037 P-21).

Three altitudes, kept deliberately separate:

  1. RANK         — relative, per strategy (upstream; not here).
  2. ELIGIBILITY  — absolute, binary veto: is this name healthy enough to own?
  3. PRIORITIZE   — cross-strategy ordering by *expected value*, not raw rank.

The output is a single priority-ordered, explainable queue — the artifact a HITL
reviewer approves from the top, and the same artifact the auto-pilot takes top-N
from when HITL is off.

This module is pure (no DB/IO): callers supply candidate context and an
``ExpectancyProvider``. That keeps the trade-selection logic unit-testable and
deterministic for replay reproducibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

# ── Rank bucketing ──────────────────────────────────────────────────────────
# Buckets are coarse on purpose: per-rank expectancy is too thin to be reliable,
# and the trade decision only needs "roughly how good is this rank in this regime".

RANK_BUCKETS: tuple[tuple[int, str], ...] = (
    (5, "1-5"),
    (10, "6-10"),
    (20, "11-20"),
)


def rank_bucket(rank: int) -> str:
    """Map a strategy rank to its expectancy bucket label."""
    for hi, label in RANK_BUCKETS:
        if rank <= hi:
            return label
    return ">20"


# ── Candidate + result types ────────────────────────────────────────────────


@dataclass(frozen=True)
class TradeCandidate:
    """A single BUY candidate handed to the trade-decision layer.

    Carries everything eligibility and prioritization need so the layer stays
    pure (no lookups). ``segment_state`` is the stock's own trend state
    ("UP"/"DOWN"/"UNKNOWN"), distinct from the market regime.
    """

    stock_id: UUID
    symbol: str
    strategy_name: str
    rank: int
    conviction_score: float
    market_regime: str
    recommendation_id: UUID
    # Eligibility context (absolute health)
    last_price: float | None = None
    sma50: float | None = None
    segment_state: str = "UNKNOWN"
    volume_today: float | None = None
    volume_avg90: float | None = None
    rs_vs_universe: float | None = None  # stock return minus equal-weight universe return
    adv_value: float | None = None       # avg daily traded value in ₹ (close × volume, 90d)


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PrioritizedCandidate:
    """One row of the HITL review queue — fully explainable."""

    candidate: TradeCandidate
    expected_return: float | None      # None when bucket sample is too thin
    expectancy_n: int
    consensus_count: int               # how many strategies surfaced this stock
    reasons: list[str]                 # eligibility/prioritization annotations
    # The sort key actually used (for audit). Larger = earlier in queue.
    sort_basis: str                    # "expected_value" | "conviction_fallback"


# ── Expectancy provider ─────────────────────────────────────────────────────


class ExpectancyProvider(Protocol):
    """Supplies rank-bucketed expected forward return for a (strategy, regime).

    Returns (expected_return, sample_count). ``expected_return`` is net of costs
    and horizon-matched to the strategy's native hold. Return (None, n) when no
    estimate is available.
    """

    def expected_return(
        self,
        strategy_name: str,
        market_regime: str,
        rank_bucket_label: str,
        segment_state: str,
    ) -> tuple[float | None, int]:
        ...


# ── Eligibility (altitude 2) ────────────────────────────────────────────────


def evaluate_eligibility(
    c: TradeCandidate,
    *,
    breadth_pct: float | None = None,
    min_breadth: float = 0.45,
    vol_floor_ratio: float = 0.70,
    require_uptrend: bool = True,
    min_adv_value: float = 2.0e7,  # ₹2cr/day — eliminate the nano-cap "noise" tier
) -> EligibilityResult:
    """Absolute, binary health veto. Missing inputs never veto (fail-open) so a
    data gap degrades to current behaviour rather than silently blocking trading.
    """
    reasons: list[str] = []

    # Liquidity floor: drop the bottom nano-cap "noise" names (ADV < ₹2cr/day).
    # Backtest showed this tier has a 22% win rate and the worst gap risk. Applies to
    # ALL strategies — an illiquid nano-cap is untradeable regardless of signal.
    if c.adv_value is not None and c.adv_value < min_adv_value:
        reasons.append(f"BELOW_ADV_FLOOR:{c.adv_value/1e7:.1f}cr<{min_adv_value/1e7:.1f}cr")

    # Market-wide: breadth gate (P-14). A single market signal can veto all names.
    if breadth_pct is not None and breadth_pct < min_breadth:
        reasons.append(f"LOW_BREADTH:{breadth_pct:.2f}<{min_breadth:.2f}")

    # Per-stock: individual uptrend (must be above own 50-SMA).
    if require_uptrend and c.last_price is not None and c.sma50 is not None:
        if c.last_price < c.sma50:
            reasons.append("BELOW_SMA50")

    # Per-stock: own segment/trend state rolling over.
    if c.segment_state == "DOWN":
        reasons.append("SEGMENT_DOWNTREND")

    # Per-stock: relative strength vs the traded universe (P-13 intent).
    if c.rs_vs_universe is not None and c.rs_vs_universe < 0:
        reasons.append("NEGATIVE_RS")

    # Per-stock: volume confirmation (P-05).
    if c.volume_today is not None and c.volume_avg90 is not None and c.volume_avg90 > 0:
        if c.volume_today < c.volume_avg90 * vol_floor_ratio:
            reasons.append("LOW_VOLUME")

    return EligibilityResult(eligible=len(reasons) == 0, reasons=reasons)


# ── Prioritization (altitude 3) ─────────────────────────────────────────────


def prioritize(
    candidates: list[TradeCandidate],
    provider: ExpectancyProvider | None,
    *,
    breadth_pct: float | None = None,
    min_breadth: float = 0.45,
    vol_floor_ratio: float = 0.70,
    require_uptrend: bool = True,
    expectancy_sample_floor: int = 25,
    drop_negative_ev: bool = True,
) -> list[PrioritizedCandidate]:
    """Produce the priority-ordered HITL queue.

    Steps:
      1. Eligibility veto (absolute health).
      2. Dedup by stock across strategies — keep the best instance, count consensus.
      3. Expected value per candidate (None when bucket sample < floor).
      4. Order: EV-known (desc) ahead of EV-unknown; EV-unknown fall back to
         conviction so cold-start / thin-bucket days still trade rather than
         freezing. Deterministic tiebreak: conviction, then better (lower) rank,
         then stock_id — for replay reproducibility.
      5. Optionally drop EV-*known* negatives (willing to sit in cash); EV-unknown
         are never dropped here (no evidence to condemn them).
    """
    # 1. Eligibility
    eligible: list[tuple[TradeCandidate, list[str]]] = []
    for c in candidates:
        res = evaluate_eligibility(
            c,
            breadth_pct=breadth_pct,
            min_breadth=min_breadth,
            vol_floor_ratio=vol_floor_ratio,
            require_uptrend=require_uptrend,
        )
        if res.eligible:
            eligible.append((c, []))

    # 2. Dedup by stock; track how many strategies surfaced each name (consensus).
    consensus: dict[UUID, int] = {}
    for c, _ in eligible:
        consensus[c.stock_id] = consensus.get(c.stock_id, 0) + 1

    # 3. Compute EV and pick the best instance per stock.
    best_by_stock: dict[UUID, PrioritizedCandidate] = {}
    for c, _ in eligible:
        ev: float | None = None
        n = 0
        if provider is not None:
            ev_raw, n = provider.expected_return(
                c.strategy_name, c.market_regime, rank_bucket(c.rank), c.segment_state
            )
            if n >= expectancy_sample_floor:
                ev = ev_raw  # trustworthy
            else:
                ev = None    # thin → fall back to conviction

        reasons: list[str] = []
        if consensus.get(c.stock_id, 1) >= 2:
            reasons.append("CROSS_STRATEGY_CONSENSUS")
        if ev is None:
            reasons.append(f"EV_UNKNOWN_THIN_SAMPLE:n={n}")

        pc = PrioritizedCandidate(
            candidate=c,
            expected_return=ev,
            expectancy_n=n,
            consensus_count=consensus.get(c.stock_id, 1),
            reasons=reasons,
            sort_basis="expected_value" if ev is not None else "conviction_fallback",
        )
        prev = best_by_stock.get(c.stock_id)
        if prev is None or _is_better(pc, prev):
            best_by_stock[c.stock_id] = pc

    queue = list(best_by_stock.values())

    # 5. Drop EV-known negatives (sit in cash rather than take a known loser).
    if drop_negative_ev:
        queue = [
            pc for pc in queue
            if not (pc.expected_return is not None and pc.expected_return <= 0)
        ]

    # 4. Order. EV-known first (by EV desc), then EV-unknown (by conviction desc).
    queue.sort(key=_sort_key, reverse=True)
    return queue


def _is_better(a: PrioritizedCandidate, b: PrioritizedCandidate) -> bool:
    """Is candidate ``a`` a better instance of the same stock than ``b``?"""
    return _sort_key(a) > _sort_key(b)


def _sort_key(pc: PrioritizedCandidate) -> tuple:
    """Deterministic ordering key (larger = earlier).

    Tier 1: EV-known beats EV-unknown.
    Tier 2: expected return (EV-known) — the headline sort.
    Tier 3: conviction — primary key for EV-unknown, tiebreak for EV-known.
    Tier 4: better (lower) rank.
    Tier 5: stock_id as a stable final tiebreak for reproducibility.
    """
    ev_known = pc.expected_return is not None
    ev = pc.expected_return if pc.expected_return is not None else 0.0
    return (
        1 if ev_known else 0,
        ev,
        pc.candidate.conviction_score,
        -pc.candidate.rank,
        # stable, comparable tail: hash of stock_id is deterministic within a run
        str(pc.candidate.stock_id),
    )
