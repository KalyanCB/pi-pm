"""Recommendation Engine v1 — deterministic action assignment.

Business rules from PRD §6 (01_RECOMMENDATION_ENGINE_PRD.md):
  R-ENTRY-01..06  entry gate logic
  R-HOLD-01       hold for active positions
  R-EXIT-01..04   exit trigger logic

Why-not evaluation order (16_WHY_NOT_RECOMMENDED_FRAMEWORK.md §4):
  1. RANK_OUTSIDE_POOL
  2. VALIDATION_PENDING / VALIDATION_WEAK
  3. REGIME_BLOCK
  4. Conviction scoring
  5. CONVICTION_LOW / PORTFOLIO_FULL → WATCH or BUY
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.core.constants import (
    CONVICTION_ENGINE_VERSION,
    CONVICTION_TOP_POOL_SIZE,
    ConvictionBand,
    RecommendationAction,
    RecommendationLifecycleState,
    REC_REASON_CONVICTION_LOW,
    REC_REASON_EXIT_RISK,
    REC_REASON_RANK_OUTSIDE_POOL,
    REC_REASON_RANK_POOL_TOP20,
    REC_REASON_REGIME_BLOCK,
    REC_REASON_VALIDATION_PENDING,
    REC_REASON_PORTFOLIO_FULL,
)
from app.recommendation.conviction_scorer import ConvictionInputs, ConvictionResult, score


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
    rank_deteriorated: bool = False      # R-EXIT-01: rank fell below threshold
    alpha_decayed: bool = False          # R-EXIT-02: alpha decay curve breached
    holding_days: int = 0               # R-EXIT-04: time stop
    regime_turned_defensive: bool = False  # R-EXIT-03: regime transition


@dataclass
class EngineConfig:
    config_version: str = "rec_v1.0.0"
    conviction_config_version: str = "conv_v1.1.0"
    top_pool_size: int = CONVICTION_TOP_POOL_SIZE
    max_buy_slots: int = 5
    regime_posture: str = "neutral"
    factor_ic_median: float | None = None
    rank_v2_promoted: bool = False
    exceptional_daily_cap: int = 3
    rank_deterioration_threshold: int = 40   # rank > this → exit signal
    max_holding_days: int = 30               # R-EXIT-04 time stop


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


def _compute_input_hash(
    ranking_run_id: UUID,
    config_version: str,
    regime_posture: str,
    validation_status: str,
) -> str:
    canonical = json.dumps(
        {
            "ranking_run_id": str(ranking_run_id),
            "config_version": config_version,
            "regime_posture": regime_posture,
            "validation_status": validation_status,
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
) -> tuple[list[RecommendationRow], str]:
    """Return (results, input_hash).

    exit_signals: per stock_id exit signal derived from exit research data.
                  Only relevant for stocks already in active_position_stock_ids.
    """
    active_positions = active_position_stock_ids or set()
    exit_signals = exit_signals or {}
    input_hash = _compute_input_hash(
        ranking_run_id, config.config_version, config.regime_posture, validation.status
    )

    top20_scores = [
        r.composite_score for r in ranking_results if r.rank <= config.top_pool_size
    ]

    results: list[RecommendationRow] = []
    buy_count = 0
    exceptional_count = 0

    # Sort by rank so slot limits apply in rank order
    sorted_results = sorted(ranking_results, key=lambda r: r.rank)

    for rr in sorted_results:
        is_active = rr.stock_id in active_positions
        exit_signal = exit_signals.get(rr.stock_id, ExitSignal()) if is_active else ExitSignal()

        action, lifecycle, reason_codes, conviction = _evaluate(
            rr=rr,
            validation=validation,
            config=config,
            top20_scores=top20_scores,
            is_active_position=is_active,
            exit_signal=exit_signal,
            buy_count=buy_count,
            exceptional_count=exceptional_count,
        )

        if action == RecommendationAction.BUY:
            buy_count += 1
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
    buy_count: int,
    exceptional_count: int,
) -> tuple[str, str | None, list[str], ConvictionResult]:
    reason_codes: list[str] = []

    # ── Active position path (R-HOLD-01, R-EXIT-01..04) ──────────────────────
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
            )

        # R-HOLD-01: no trigger → HOLD
        return (
            RecommendationAction.HOLD,
            RecommendationLifecycleState.ACTIVE,
            [],
            conviction,
        )

    # ── Entry path ────────────────────────────────────────────────────────────

    # R-ENTRY-01: pool gate
    if rr.rank > config.top_pool_size:
        conviction = _conviction_for(rr, validation, config, top20_scores, "none")
        return RecommendationAction.REJECT, None, [REC_REASON_RANK_OUTSIDE_POOL], conviction

    reason_codes.append(REC_REASON_RANK_POOL_TOP20)

    # R-ENTRY-02: validation gate
    if validation.status == "insufficient_data":
        conviction = _conviction_for(rr, validation, config, top20_scores, "none")
        reason_codes.append(REC_REASON_VALIDATION_PENDING)
        return RecommendationAction.WATCH, None, reason_codes, conviction

    conviction = _conviction_for(rr, validation, config, top20_scores, "none")

    # R-ENTRY-03: BLOCKED conviction → REJECT
    if conviction.band == ConvictionBand.BLOCKED:
        reason_codes.append(REC_REASON_CONVICTION_LOW)
        return RecommendationAction.REJECT, None, reason_codes, conviction

    # R-ENTRY-05a: LOW conviction → WATCH
    if conviction.band == ConvictionBand.LOW:
        reason_codes.append(REC_REASON_CONVICTION_LOW)
        return RecommendationAction.WATCH, None, reason_codes, conviction

    # Regime gate (R-ENTRY-04)
    if config.regime_posture == "defensive":
        reason_codes.append(REC_REASON_REGIME_BLOCK)
        return RecommendationAction.WATCH, None, reason_codes, conviction

    # Slot limit (R-ENTRY-05b)
    if buy_count >= config.max_buy_slots:
        reason_codes.append(REC_REASON_PORTFOLIO_FULL)
        return RecommendationAction.WATCH, None, reason_codes, conviction

    # Exceptional daily cap
    if (
        conviction.band == ConvictionBand.EXCEPTIONAL
        and exceptional_count >= config.exceptional_daily_cap
    ):
        return RecommendationAction.WATCH, None, reason_codes, conviction

    # R-ENTRY-04: MEDIUM+ conviction, regime allows, slots available → BUY
    return (
        RecommendationAction.BUY,
        RecommendationLifecycleState.CANDIDATE,
        reason_codes,
        conviction,
    )


def _resolve_position_state(
    rr: RankingResultRow,
    exit_signal: ExitSignal,
    config: EngineConfig,
) -> tuple[str, list[str]]:
    """Return (position_state_for_conviction, exit_reason_codes).

    Evaluates R-EXIT-01..04 in priority order.
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
        )
    )
