"""Unit tests for ReplayExperimentConfig."""

from __future__ import annotations

import textwrap
from datetime import date
from pathlib import Path

import pytest

from app.replay.config.experiment_config import (
    CapitalConfig,
    ExperimentMode,
    ReplayExperimentConfig,
)


def _minimal_config(**overrides) -> dict:
    base = {
        "experiment_id": "TEST_001",
        "name": "Test Experiment",
        "start_date": "2025-01-01",
        "end_date": "2025-06-30",
        "capital": {"initial_cash": 1_000_000},
    }
    base.update(overrides)
    return base


def test_load_from_yaml(tmp_path: Path):
    yaml_content = textwrap.dedent("""\
        experiment_id: EXP_YAML_TEST
        name: "YAML Load Test"
        start_date: "2025-01-01"
        end_date: "2025-12-31"
        strategies: [breakout_v1]
        capital:
          initial_cash: 500000
          monthly_contribution: 50000
    """)
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(yaml_content)

    try:
        config = ReplayExperimentConfig.from_yaml(yaml_file)
    except ImportError:
        pytest.skip("pyyaml not installed")

    assert config.experiment_id == "EXP_YAML_TEST"
    assert config.capital.initial_cash == 500_000
    assert config.capital.monthly_contribution == 50_000
    assert config.strategies == ["breakout_v1"]


def test_defaults_applied():
    config = ReplayExperimentConfig(**_minimal_config())

    # ExecutionConfig defaults
    assert config.execution.slippage_bps == 5.0
    assert config.execution.fee_per_leg == 20.0
    assert config.execution.auto_approve_buys is True

    # PortfolioConfig defaults
    assert config.portfolio.max_positions == 10
    assert config.portfolio.single_name_cap_pct == 0.18
    assert config.portfolio.cash_floor_pct == 0.15

    # RecommendationConfig defaults
    assert config.recommendations.use_rcee is True
    assert config.recommendations.use_committee is False

    # Mode default
    assert config.mode == "AUTONOMOUS_RCEE"

    # Strategies default
    assert "breakout_v1" in config.strategies


def test_invalid_dates_rejected():
    with pytest.raises(Exception):
        ReplayExperimentConfig(
            **_minimal_config(start_date="2025-06-30", end_date="2025-01-01")
        )


def test_same_start_end_rejected():
    with pytest.raises(Exception):
        ReplayExperimentConfig(
            **_minimal_config(start_date="2025-01-01", end_date="2025-01-01")
        )


def test_mode_enum_validated():
    config = ReplayExperimentConfig(**_minimal_config(mode="AUTONOMOUS_FORCE_EDGE"))
    assert config.experiment_mode == ExperimentMode.AUTONOMOUS_FORCE_EDGE


def test_invalid_mode_rejected():
    with pytest.raises(Exception):
        ReplayExperimentConfig(**_minimal_config(mode="INVALID_MODE"))


def test_capital_config_parsed():
    config = ReplayExperimentConfig(
        **_minimal_config(
            capital={
                "initial_cash": 2_000_000,
                "monthly_contribution": 100_000,
                "contribution_day": "LAST_TRADING_DAY",
            }
        )
    )
    assert config.capital.initial_cash == 2_000_000
    assert config.capital.monthly_contribution == 100_000
    assert config.capital.contribution_day == "LAST_TRADING_DAY"


def test_experiment_mode_property():
    config = ReplayExperimentConfig(**_minimal_config(mode="HITL_SIMULATION"))
    assert config.experiment_mode == ExperimentMode.HITL_SIMULATION
    assert isinstance(config.experiment_mode, ExperimentMode)
