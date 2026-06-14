"""ADR-035: regime-dynamic stop resolution + time-stop gating (flag-off safe)."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.portfolio.regime_stops import parse_stop_map, resolve_stop_pcts


def _repo(label: str | None):
    repo = MagicMock()
    if label is None:
        repo.get_current.return_value = None
    else:
        regime = MagicMock()
        regime.regime_label = label
        repo.get_current.return_value = regime
    return repo


def _settings(**kw) -> Settings:
    return Settings(**kw)


# ── Resolver ──────────────────────────────────────────────────────────────────


def test_flag_off_returns_static_adr033_stops():
    s = _settings(regime_dynamic_stops_enabled=False)
    adv, crit = resolve_stop_pcts(_repo("BULL_LOW_VOL"), settings=s)
    assert adv == pytest.approx(s.advisory_stop_pct)   # -8 default
    assert crit == pytest.approx(s.critical_stop_pct)  # -10 default


@pytest.mark.parametrize(
    ("label", "expected_advisory"),
    [
        ("BULL_LOW_VOL", -6.0),
        ("BULL_HIGH_VOL", -8.0),
        ("BEAR_LOW_VOL", -2.0),
        ("BEAR_HIGH_VOL", -3.0),
    ],
)
def test_flag_on_maps_regime_to_advisory(label, expected_advisory):
    s = _settings(regime_dynamic_stops_enabled=True)
    adv, crit = resolve_stop_pcts(_repo(label), as_of=date(2026, 6, 10), settings=s)
    assert adv == pytest.approx(expected_advisory)
    # critical = advisory + offset (-2 default)
    assert crit == pytest.approx(expected_advisory + s.regime_critical_offset_pct)


def test_unknown_label_uses_fallback():
    s = _settings(regime_dynamic_stops_enabled=True)
    adv, _ = resolve_stop_pcts(_repo("SIDEWAYS_WEIRD"), settings=s)
    assert adv == pytest.approx(s.regime_stop_fallback_pct)  # -4 default


def test_missing_regime_row_uses_fallback():
    s = _settings(regime_dynamic_stops_enabled=True)
    adv, _ = resolve_stop_pcts(_repo(None), settings=s)
    assert adv == pytest.approx(s.regime_stop_fallback_pct)


def test_repo_error_uses_fallback():
    s = _settings(regime_dynamic_stops_enabled=True)
    repo = MagicMock()
    repo.get_current.side_effect = RuntimeError("db down")
    adv, _ = resolve_stop_pcts(repo, settings=s)
    assert adv == pytest.approx(s.regime_stop_fallback_pct)


def test_malformed_map_fails_safe_to_static():
    s = _settings(regime_dynamic_stops_enabled=True, regime_stop_map="{not json")
    adv, crit = resolve_stop_pcts(_repo("BULL_LOW_VOL"), settings=s)
    assert adv == pytest.approx(s.advisory_stop_pct)
    assert crit == pytest.approx(s.critical_stop_pct)


def test_parse_stop_map_uppercases_keys():
    s = _settings(regime_stop_map='{"bull_low_vol": -5.5}')
    assert parse_stop_map(s) == {"BULL_LOW_VOL": -5.5}


# ── Time-stop gating (T2 monitor) ─────────────────────────────────────────────


def _t2_service():
    from app.portfolio.exit_monitor.service import ExitMonitorService

    svc = ExitMonitorService.__new__(ExitMonitorService)
    svc.regime_repo = _repo("BULL_LOW_VOL")
    return svc


def _ctx(days_held: int) -> dict:
    return {"days_held": days_held, "unrealized_pnl_pct": 0.0, "current_rank": 1}


def _pos():
    pos = MagicMock()
    pos.weight_pct = None
    pos.market_value = None
    return pos


def test_t2_time_stop_fires_when_enabled(monkeypatch):
    svc = _t2_service()
    monkeypatch.setattr(
        "app.portfolio.exit_monitor.service.get_settings",
        lambda: _settings(time_stop_enabled=True),
    )
    fired = svc._evaluate_triggers(_pos(), _ctx(days_held=45), None, "neutral")
    assert any(t.trigger_code == "EXIT_TIME" for t in fired)


def test_t2_time_stop_gated_off(monkeypatch):
    svc = _t2_service()
    monkeypatch.setattr(
        "app.portfolio.exit_monitor.service.get_settings",
        lambda: _settings(time_stop_enabled=False),
    )
    fired = svc._evaluate_triggers(_pos(), _ctx(days_held=500), None, "neutral")
    assert not any(t.trigger_code == "EXIT_TIME" for t in fired)


def test_t2_stop_loss_uses_regime_map_when_enabled(monkeypatch):
    svc = _t2_service()
    svc.regime_repo = _repo("BEAR_LOW_VOL")  # advisory -2
    monkeypatch.setattr(
        "app.portfolio.exit_monitor.service.get_settings",
        lambda: _settings(regime_dynamic_stops_enabled=True),
    )
    ctx = _ctx(days_held=1)
    ctx["unrealized_pnl_pct"] = -3.0  # breaches -2 (regime) but not -8 (static)
    fired = svc._evaluate_triggers(_pos(), ctx, None, "neutral")
    assert any(t.trigger_code == "EXIT_STOP_LOSS" for t in fired)


# ── Engine R-EXIT-04 gate ─────────────────────────────────────────────────────


def test_engine_config_unbounded_hold_when_time_stop_off():
    from app.services.recommendation_service import RecommendationService

    svc = RecommendationService.__new__(RecommendationService)
    svc.settings = _settings(time_stop_enabled=False)
    svc.db = MagicMock()
    svc._resolve_regime_posture = MagicMock(return_value="neutral")
    svc._resolve_factor_ic = MagicMock(return_value=None)
    svc._load_regime_fit = MagicMock(return_value=None)
    run = MagicMock()
    run.strategy_name = "breakout_v1"
    cfg = svc._build_engine_config(run)
    assert cfg.max_holding_days >= 10**9

    svc.settings = _settings(time_stop_enabled=True)
    assert svc._build_engine_config(run).max_holding_days == 30
