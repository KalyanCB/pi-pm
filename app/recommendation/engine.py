"""Recommendation Engine v1 — deterministic action assignment.

Business rules from PRD §6 (01_RECOMMENDATION_ENGINE_PRD.md):
  R-ENTRY-01..06  entry gate logic
  R-HOLD-01       hold for active positions
  R-EXIT-01..04   exit trigger logic

ADR-032:
  R-ENTRY-02-RCE  regime-conditional edge gate (replaces R-ENTRY-02 when regime_fit available)
  R-EXIT-05       edge degraded exit advisory

Why-not evaluation order (16_WHY_NOT_RECOMMENDED_FRAMEWORK.md §4):
  1. RANK_OUTSIDE_POOL
  2. REGIME_NO_EDGE / VALIDATION_PENDING (R-ENTRY-02-RCE or legacy R-ENTRY-02)
  3. REGIME_BLOCK
  4. Conviction scoring
  5. CONVICTION_LOW → WATCH; otherwise → BUY

The engine emits the PURE entry signal (eligibility + conviction + regime). It does
NOT apply portfolio capacity / daily-buy throttles — those are admission decisions that
depend on live portfolio state and are enforced downstream (portfolio_service /
replay buy loop). A BUY here means "we'd want to own this", not "we have a free slot".
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.core.constants import (
    CONVICTION_TOP_POOL_SIZE,
    REC_REASON_CONVICTION_LOW,
    REC_REASON_EXIT_RISK,
    REC_REASON_LOW_EXPECTANCY,
    REC_REASON_RANK_OUTSIDE_POOL,
    REC_REASON_RANK_POOL_TOP20,
    REC_REASON_REGIME_BLOCK,
    REC_REASON_PROVISIONAL_EDGE,
    REC_REASON_REGIME_NO_EDGE,
    REC_REASON_VALIDATION_PENDING,
    ConvictionBand,
    RecommendationAction,
    RecommendationConfidence,
    RecommendationLifecycleState,
)
from app.recommendation.conviction_scorer import ConvictionInputs, ConvictionResult, score
from app.recommendation.regime_edge_engine import EdgeState, RegimeFit


@dataclass
class RankingResultRow:
    stock_id: UUID
    rank: int
    composite_score: float
    score_components: dict[str, Any] | None = None


@dataclass
class ValidationSummary:
    status: str
    ic_20d: float | None = None
    top_decile_spread: float | None = None


@dataclass
class ExitSignal:
    """Per-stock exit signal derived from exit research data."""

    rank_deteriorated: bool = False  # R-EXIT-01: rank fell below threshold
    alpha_decayed: bool = False  # R-EXIT-02: alpha decay curve breached
    holding_days: int = 0  # R-EXIT-04: time stop
    regime_turned_defensive: bool = False  # R-EXIT-03: regime transition
    edge_degraded: bool = False  # R-EXIT-05 (ADR-032): regime edge deteriorated since entry


@dataclass
class EngineConfig:
    config_version: str = "rec_v1.0.0"
    conviction_config_version: str = "conv_v1.1.0"
    top_pool_size: int = CONVICTION_TOP_POOL_SIZE
    regime_posture: str = "neutral"
    factor_ic_median: float | None = None
    rank_v2_promoted: bool = False
    exceptional_daily_cap: int = 3
    rank_deterioration_threshold: int = 40  # rank > this → exit signal
    max_holding_days: int = 30  # R-EXIT-04 time stop
    # ADR-032: RCEE regime fit (None → fallback to legacy R-ENTRY-02)
    regime_fit: RegimeFit | None = None


@dataclass
class FreshnessCheck:
    """Result of approval-time freshness validation (Phase 5)."""

    is_fresh: bool
    stale_reasons: list[str] = field(default_factory=list)


@dataclass
class RecommendationRow:
    stock_id: UUID
    rank: int | None
    composite_score: float | None
    action: str
    lifecycle_state: str | None
    conviction_score: int
    conviction_band: str
    conviction_components: dict[str, Any]
    reason_codes: list[str]
    recommendation_confidence: str | None = None  # ADR-032


def _compute_input_hash(
    ranking_run_id: UUID,
    config_version: str,
    regime_posture: str,
    validation_status: str,
    edge_state: str | None = None,
) -> str:
    canonical = json.dumps(
        {
            "ranking_run_id": str(ranking_run_id),
            "config_version": config_version,
            "regime_posture": regime_posture,
            "validation_status": validation_status,
            "edge_state": edge_state,
        },
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def run(
    *,
    ranking_run_id: UUID,
    ranking_results: list[RankingResultRow],
    validation: ValidationSummary,
    config: EngineConfig,
    active_position_stock_ids: set[UUID] | None = None,
    exit_signals: dict[UUID, ExitSignal] | None = None,
    cooldown_stock_ids: set[UUID] | None = None,
) -> tuple[list[RecommendationRow], str]:
    """Return (results, input_hash).

    exit_signals: per stock_id exit signal derived from exit research data.
                  Only relevant for stocks already in active_position_stock_ids.
    cooldown_stock_ids: stock_ids stopped out recently — suppress BUY for 5 trading days.
    """
    active_positions = active_position_stock_ids or set()
    exit_signals = exit_signals or {}
    cooldown_stocks = cooldown_stock_ids or set()

    edge_state = config.regime_fit.edge_state.value if config.regime_fit else None
    input_hash = _compute_input_hash(
        ranking_run_id,
        config.config_version,
        config.regime_posture,
        validation.status,
        edge_state,
    )

    top20_scores = [r.composite_score for r in ranking_results if r.rank <= config.top_pool_size]

    results: list[RecommendationRow] = []
    exceptional_count = 0

    # Sort by rank so the (per-run) exceptional-conviction cap is applied in rank order,
    # keeping output deterministic and rank-priority.
    sorted_results = sorted(ranking_results, key=lambda r: r.rank)

    for rr in sorted_results:
        is_active = rr.stock_id in active_positions
        in_cooldown = rr.stock_id in cooldown_stocks and not is_active
        exit_signal = exit_signals.get(rr.stock_id, ExitSignal()) if is_active else ExitSignal()

        action, lifecycle, reason_codes, conviction, confidence = _evaluate(
            rr=rr,
            validation=validation,
            config=config,
            top20_scores=top20_scores,
            is_active_position=is_active,
            exit_signal=exit_signal,
            exceptional_count=exceptional_count,
        )

        # Re-entry cooldown: downgrade BUY → WATCH for 5 trading days after stop-loss exit
        if action == RecommendationAction.BUY and in_cooldown:
            action = RecommendationAction.WATCH
            reason_codes = list(reason_codes) + ["RECENT_STOP_EXIT"]

        if action == RecommendationAction.BUY:
            if conviction.band == ConvictionBand.EXCEPTIONAL:
                exceptional_count += 1

        results.append(
            RecommendationRow(
                stock_id=rr.stock_id,
                rank=rr.rank,
                composite_score=rr.composite_score,
                action=action,
                lifecycle_state=lifecycle,
                conviction_score=conviction.score,
                conviction_band=conviction.band.value,
                conviction_components=conviction.components,
                reason_codes=reason_codes,
                recommendation_confidence=confidence.value if confidence else None,
            )
        )

    return results, input_hash


def _evaluate(
    *,
    rr: RankingResultRow,
    validation: ValidationSummary,
    config: EngineConfig,
    top20_scores: list[float],
    is_active_position: bool,
    exit_signal: ExitSignal,
    exceptional_count: int,
) -> tuple[str, str | None, list[str], ConvictionResult, RecommendationConfidence | None]:
    reason_codes: list[str] = []

    # ── Active position path (R-HOLD-01, R-EXIT-01..05) ──────────────────────
    if is_active_position:
        position_state, exit_reasons = _resolve_position_state(rr, exit_signal, config)
        conviction = _conviction_for(rr, validation, config, top20_scores, position_state)

        if exit_reasons:
            # Any exit trigger → EXIT_APPROVED (human must confirm)
            return (
                RecommendationAction.EXIT_APPROVED,
                RecommendationLifecycleState.EXIT_APPROVED,
                exit_reasons,
                conviction,
                None,
            )

        # R-HOLD-01: no trigger → HOLD
        return (
            RecommendationAction.HOLD,
            RecommendationLifecycleState.ACTIVE,
            [],
            conviction,
            None,
        )

    # ── Entry path ────────────────────────────────────────────────────────────

    # R-ENTRY-01: pool gate
    if rr.rank > config.top_pool_size:
        conviction = _conviction_for(rr, validation, config, top20_scores, "none")
        return RecommendationAction.REJECT, None, [REC_REASON_RANK_OUTSIDE_POOL], conviction, None

    reason_codes.append(REC_REASON_RANK_POOL_TOP20)

    # R-ENTRY-02-RCE: regime-conditional edge gate (ADR-032)
    if config.regime_fit is not None:
        if config.regime_fit.edge_state == EdgeState.NO_EDGE:
            conviction = _conviction_for(rr, validation, config, top20_scores, "none")
            reason_codes.append(REC_REASON_REGIME_NO_EDGE)
            return (
                RecommendationAction.WATCH,
                None,
                reason_codes,
                conviction,
                RecommendationConfidence.UNKNOWN,
            )
        if config.regime_fit.edge_state == EdgeState.EDGE_WEAK:
            conviction = _conviction_for(rr, validation, config, top20_scores, "none")
            reason_codes.append(REC_REASON_LOW_EXPECTANCY)
            return (
                RecommendationAction.WATCH,
                None,
                reason_codes,
                conviction,
                RecommendationConfidence.EARLY,
            )
        if config.regime_fit.edge_state == EdgeState.EDGE_PROVISIONAL:
            # P-04: tentative early-sample edge — allowed to trade (falls through to
            # the BUY path) but tagged so it is auditable and downstream sizing/limits
            # can treat it more cautiously than confirmed EDGE_PRESENT.
            reason_codes.append(REC_REASON_PROVISIONAL_EDGE)
    else:
        # Fallback: legacy R-ENTRY-02 when RCEE not available (regime_fit=None)
        # validation.status=="insufficient_data" is always true in backtest/replay — fall
        # through to conviction scoring so RCEE works from day 1.
        pass

    conviction = _conviction_for(rr, validation, config, top20_scores, "none")

    # R-ENTRY-03: BLOCKED conviction → REJECT
    if conviction.band == ConvictionBand.BLOCKED:
        reason_codes.append(REC_REASON_CONVICTION_LOW)
        return RecommendationAction.REJECT, None, reason_codes, conviction, None

    # R-ENTRY-05a: LOW conviction → WATCH
    if conviction.band == ConvictionBand.LOW:
        reason_codes.append(REC_REASON_CONVICTION_LOW)
        return RecommendationAction.WATCH, None, reason_codes, conviction, None

    # Regime gate (R-ENTRY-04)
    # Skip when RCEE has confirmed EDGE_PRESENT for this strategy in this regime.
    # EDGE_PRESENT already encodes that the strategy has statistically proven edge
    # here — e.g. reversal_v1 in BEAR_LOW_VOL. The posture gate is redundant and
    # would incorrectly block strategies deliberately designed for "defensive" regimes.
    _rcee_confirmed = (
        config.regime_fit is not None
        and config.regime_fit.edge_state == EdgeState.EDGE_PRESENT
    )
    if config.regime_posture == "defensive" and not _rcee_confirmed:
        reason_codes.append(REC_REASON_REGIME_BLOCK)
        return RecommendationAction.WATCH, None, reason_codes, conviction, None

    # NOTE: portfolio capacity / daily-buy throttle (the former R-ENTRY-05b
    # "PORTFOLIO_FULL" gate) is intentionally NOT applied here. It is an admission
    # decision that requires live portfolio state (free slots, buys-already-today) and
    # is enforced downstream (portfolio_service.RegimeLimits / the replay buy loop).
    # Keeping it out of the engine makes recommendation_results the pure, reusable
    # signal and removes path-dependence on the run-time portfolio trajectory.

    # Exceptional daily cap
    if (
        conviction.band == ConvictionBand.EXCEPTIONAL
        and exceptional_count >= config.exceptional_daily_cap
    ):
        return RecommendationAction.WATCH, None, reason_codes, conviction, None

    # Derive confidence for BUY path
    confidence = _derive_buy_confidence(config)

    # R-ENTRY-04: MEDIUM+ conviction, regime allows, slots available → BUY
    return (
        RecommendationAction.BUY,
        RecommendationLifecycleState.CANDIDATE,
        reason_codes,
        conviction,
        confidence,
    )


def _derive_buy_confidence(config: EngineConfig) -> RecommendationConfidence:
    """Derive recommendation confidence for BUY path based on RCEE evidence."""
    if config.regime_fit and config.regime_fit.edge_state == EdgeState.EDGE_PRESENT:
        if config.regime_fit.sample_days >= 200:
            return RecommendationConfidence.HIGH_CONFIDENCE
        elif config.regime_fit.sample_days >= 60:
            return RecommendationConfidence.VALIDATED
        else:
            return RecommendationConfidence.EARLY
    return RecommendationConfidence.UNKNOWN


def _resolve_position_state(
    rr: RankingResultRow,
    exit_signal: ExitSignal,
    config: EngineConfig,
) -> tuple[str, list[str]]:
    """Return (position_state_for_conviction, exit_reason_codes).

    Evaluates R-EXIT-01..05 in priority order.
    Multiple triggers can fire simultaneously — all reason codes are returned.
    """
    exit_reasons: list[str] = []

    # R-EXIT-01: rank deterioration
    if exit_signal.rank_deteriorated or rr.rank > config.rank_deterioration_threshold:
        exit_reasons.append(REC_REASON_EXIT_RISK)

    # R-EXIT-02: alpha decay
    if exit_signal.alpha_decayed:
        exit_reasons.append("ALPHA_DECAY")

    # R-EXIT-03: regime turned defensive
    if exit_signal.regime_turned_defensive:
        exit_reasons.append(REC_REASON_REGIME_BLOCK)

    # R-EXIT-04: time stop
    if exit_signal.holding_days >= config.max_holding_days:
        exit_reasons.append("TIME_STOP")

    # R-EXIT-05: edge degraded (ADR-032) — advisory, surfaces as EXIT_APPROVED for HITL review
    if exit_signal.edge_degraded:
        exit_reasons.append("EDGE_DEGRADED")

    if exit_reasons:
        position_state = "active_deteriorating" if exit_signal.rank_deteriorated else "active_decay"
    else:
        position_state = "active_clean"

    return position_state, exit_reasons


def _conviction_for(
    rr: RankingResultRow,
    validation: ValidationSummary,
    config: EngineConfig,
    top20_scores: list[float],
    position_state: str,
) -> ConvictionResult:
    edge_state = config.regime_fit.edge_state.value if config.regime_fit else None
    # Strategy-level IC from RCEE — used instead of per-factor median for strategies
    # whose factors are not in factor_daily_metrics (e.g. reversal_v1, low_vol_v1).
    strategy_regime_ic = (
        float(config.regime_fit.avg_ic)
        if config.regime_fit and config.regime_fit.avg_ic is not None
        else None
    )
    return score(
        ConvictionInputs(
            rank=rr.rank,
            composite_score=rr.composite_score,
            top20_composite_scores=top20_scores,
            validation_status=validation.status,
            validation_ic_20d=validation.ic_20d,
            validation_top_decile_spread=validation.top_decile_spread,
            factor_ic_median=config.factor_ic_median,
            regime_posture=config.regime_posture,
            position_state=position_state,
            rank_v2_promoted=config.rank_v2_promoted,
            config_version=config.conviction_config_version,
            regime_fit_edge_state=edge_state,
            strategy_regime_ic=strategy_regime_ic,
        )
    )


def check_recommendation_freshness(
    *,
    result: RecommendationRow,
    current_ranking_rows: list[RankingResultRow],
    regime_fit: RegimeFit | None,
    recommendation_age_days: int,
    max_age_days: int = 3,
) -> FreshnessCheck:
    """Approval-time freshness validation. Returns STALE_BREACH reasons if stale."""
    from app.core.constants import (
        REC_REASON_RANK_EXITED_POOL,
        REC_REASON_REGIME_EDGE_LOST,
        REC_REASON_STALE_AGE,
    )

    stale_reasons: list[str] = []

    # Check 1: age
    if recommendation_age_days > max_age_days:
        stale_reasons.append(REC_REASON_STALE_AGE)

    # Check 2: still in top pool
    current_ranks = {r.stock_id: r.rank for r in current_ranking_rows}
    current_rank = current_ranks.get(result.stock_id)
    if current_rank is None or current_rank > CONVICTION_TOP_POOL_SIZE:
        stale_reasons.append(REC_REASON_RANK_EXITED_POOL)

    # Check 3: edge still valid (regime may have changed)
    if regime_fit and regime_fit.edge_state == EdgeState.NO_EDGE:
        stale_reasons.append(REC_REASON_REGIME_EDGE_LOST)

    return FreshnessCheck(is_fresh=len(stale_reasons) == 0, stale_reasons=stale_reasons)
