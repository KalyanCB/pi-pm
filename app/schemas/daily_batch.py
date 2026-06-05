from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.constants import (
    RANKING_STRATEGY_BREAKOUT_V1,
    RANKING_STRATEGY_BREAKOUT_V1_VERSION,
    RANKING_STRATEGY_MOMENTUM_V1,
    RANKING_STRATEGY_MOMENTUM_V1_VERSION,
    UNIVERSE_NIFTY_500,
)
from app.factor_analytics.constants import DEFAULT_HOLDOUT_START_DATE


class DailyBatchStrategySpec(BaseModel):
    strategy_name: str
    strategy_version: str


class DailyBatchPortfolioPhaseFlags(BaseModel):
    """Paper-trading pilot ops — orchestration only; no engine logic changes."""

    recompute: bool = True
    exit_monitor: bool = True
    paper_trading: bool = True
    nav_snapshot: bool = True
    reconcile: bool = True


class DailyBatchPhaseFlags(BaseModel):
    ingest: bool = True
    rankings: bool = True
    validation: bool = True
    recommendations: bool = True
    regime_history: bool = True
    regime_performance: bool = True
    factor_ic: bool = True
    research_intelligence: bool = True
    exit_research: bool = True
    portfolio: bool = False


class DailyBatchRunCreateRequest(BaseModel):
    universe_code: str = UNIVERSE_NIFTY_500
    benchmark_symbol: str = "^NSEI"
    strategies: list[DailyBatchStrategySpec] = Field(
        default_factory=lambda: [
            DailyBatchStrategySpec(
                strategy_name=RANKING_STRATEGY_BREAKOUT_V1,
                strategy_version=RANKING_STRATEGY_BREAKOUT_V1_VERSION,
            ),
            DailyBatchStrategySpec(
                strategy_name=RANKING_STRATEGY_MOMENTUM_V1,
                strategy_version=RANKING_STRATEGY_MOMENTUM_V1_VERSION,
            ),
        ]
    )
    target_date: date | None = None
    from_date: date | None = None
    force_from_date: bool = False
    assume_session_done: bool = True
    force: bool = False
    force_recompute: bool = False
    force_regenerate_rankings: bool = False
    force_ingest: bool = False
    dry_run: bool = False
    phases: DailyBatchPhaseFlags = Field(default_factory=DailyBatchPhaseFlags)
    portfolio_phases: DailyBatchPortfolioPhaseFlags = Field(
        default_factory=DailyBatchPortfolioPhaseFlags
    )
    """When phases.portfolio=true, run mark-to-market → exit monitor → paper fills → NAV → recon."""
    pilot_auto_approve: bool = False
    """Paper pilot: auto-approve BUY recommendations before simulated fill (HITL bypass)."""
    pilot_auto_execute: bool = False
    """Paper pilot: simulate paper entries/exits for approved/exit-approved recommendations."""
    ingest_portfolio_benchmarks: bool = True
    """Also ingest ^CRSLDX (NIFTY 500 TR) when portfolio phases enabled."""
    holdout_start_date: date = DEFAULT_HOLDOUT_START_DATE
    ingest_batch_size: int = Field(default=25, ge=1, le=100)
    allow_partial_ingest: bool = False
    idempotency_key: str | None = None


class DailyBatchPlanSnapshot(BaseModel):
    needs_ingest: bool
    ranking_gaps: dict[str, list[str]]
    validation_gap_count: int
    factor_ic_needed: bool
    regime_history_needed: bool = False
    regime_performance_needed: bool = False
    exit_research_needed: bool
    research_intelligence_needed: bool = False
    factor_ic_window_start: date | None = None
    factor_ic_window_end: date | None = None
    already_current: bool


class DailyBatchRunCreateResponse(BaseModel):
    run_id: str
    status: str
    target_trading_day: date | None
    from_date: date | None
    resolution_reason: str | None = None
    already_current: bool = False
    plan: DailyBatchPlanSnapshot | None = None
    phases: dict[str, Any] | None = None
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    error_message: str | None = None
    idempotent_replay: bool = False


class DailyBatchRunStatusResponse(BaseModel):
    run_id: str
    status: str
    current_phase: str | None = None
    target_trading_day: date | None = None
    from_date: date | None = None
    percent_complete: float | None = None
    phase_progress: dict[str, Any] | None = None
    plan_snapshot: dict[str, Any] | None = None
    phase_results: dict[str, Any] | None = None
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float | None = None


class DailyBatchRunSummary(BaseModel):
    run_id: str
    status: str
    universe_code: str
    target_trading_day: date | None
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float | None = None


class DailyBatchTraceResponse(BaseModel):
    run_id: str
    status: str
    current_phase: str | None = None
    target_trading_day: date | None = None
    from_date: date | None = None
    lineage: dict[str, list[str]]
    current_load: dict[str, Any] | None = None
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
