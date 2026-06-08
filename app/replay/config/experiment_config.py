"""Replay Experiment Configuration — parsed from YAML, validated with Pydantic."""

from __future__ import annotations

from datetime import date
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, field_validator, model_validator


class ExperimentMode(str, Enum):
    AUTONOMOUS_RCEE = "AUTONOMOUS_RCEE"               # RCEE gates, auto approve
    AUTONOMOUS_NO_RCEE = "AUTONOMOUS_NO_RCEE"         # legacy validation gate, auto approve
    AUTONOMOUS_FORCE_EDGE = "AUTONOMOUS_FORCE_EDGE"   # force EDGE_PRESENT always (for comparison)
    HITL_SIMULATION = "HITL_SIMULATION"               # auto-approve with 1-day delay
    COMMITTEE_BYPASS = "COMMITTEE_BYPASS"             # skip committee review
    CUSTOM = "CUSTOM"                                  # full config control


class CapitalConfig(BaseModel):
    initial_cash: float                            # e.g. 1000000 (INR)
    monthly_contribution: float = 0.0             # SIP amount
    contribution_day: str = "FIRST_TRADING_DAY"   # or "LAST_TRADING_DAY"


class ExecutionConfig(BaseModel):
    auto_approve_buys: bool = True
    auto_approve_exits: bool = True
    slippage_bps: float = 5.0
    fee_per_leg: float = 20.0


class RecommendationConfig(BaseModel):
    use_rcee: bool = True
    use_committee: bool = False       # skip committee for speed
    use_validation_gate: bool = False  # legacy gate — off by default


class PortfolioConfig(BaseModel):
    max_positions: int = 10
    max_buy_slots: int = 5             # per day
    deploy_pct: float = 0.85
    cash_floor_pct: float = 0.15
    single_name_cap_pct: float = 0.18
    sizing_policy: str = "conviction"  # "conviction" | "equal" | "risk_parity"


class OutputConfig(BaseModel):
    generate_nav_curve: bool = True
    generate_trade_report: bool = True
    generate_regime_report: bool = True
    generate_strategy_report: bool = True
    output_dir: str = "docs/experiments/results"


class ReplayExperimentConfig(BaseModel):
    experiment_id: str
    name: str
    description: str = ""
    mode: str = "AUTONOMOUS_RCEE"  # see ExperimentMode enum
    start_date: date
    end_date: date
    strategies: list[str] = ["breakout_v1", "momentum_v1"]
    capital: CapitalConfig
    execution: ExecutionConfig = ExecutionConfig()
    recommendations: RecommendationConfig = RecommendationConfig()
    portfolio: PortfolioConfig = PortfolioConfig()
    outputs: OutputConfig = OutputConfig()

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        valid = {m.value for m in ExperimentMode}
        if v not in valid:
            raise ValueError(f"mode must be one of {valid}, got {v!r}")
        return v

    @model_validator(mode="after")
    def validate_dates(self) -> "ReplayExperimentConfig":
        if self.start_date >= self.end_date:
            raise ValueError(f"start_date {self.start_date} must be before end_date {self.end_date}")
        return self

    @property
    def experiment_mode(self) -> ExperimentMode:
        return ExperimentMode(self.mode)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ReplayExperimentConfig":
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError(
                "PyYAML is required to load YAML experiment configs. "
                "Install it with: uv add pyyaml"
            ) from e

        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
