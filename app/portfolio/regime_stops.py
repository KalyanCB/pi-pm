"""ADR-035: regime-dynamic stop-loss resolution.

Single source of truth for the advisory/critical stop percentages. When
``regime_dynamic_stops_enabled`` is off (default) this returns the static
ADR-033 values, so all callers are behaviour-neutral until the flag flips.

When on, the advisory stop comes from ``regime_stop_map`` keyed by the latest
``regime_history`` label (benchmark ^NSEI) resolved at evaluation time — i.e.
re-evaluated daily, deliberately WITHOUT debounce (tested and rejected in the
ADR-035 evidence base). Critical = advisory + ``regime_critical_offset_pct``.
"""

from __future__ import annotations

import json
from datetime import date

from app.core.config import Settings, get_settings
from app.core.constants import DEFAULT_BENCHMARK_SYMBOL
from app.db.repositories.regime_analytics_repository import RegimeAnalyticsRepository


def parse_stop_map(settings: Settings) -> dict[str, float]:
    """Parse regime_stop_map JSON; empty dict on malformed input (safe fallback)."""
    try:
        raw = json.loads(settings.regime_stop_map)
        return {str(k).upper(): float(v) for k, v in raw.items()}
    except (ValueError, TypeError, AttributeError):
        return {}


def resolve_stop_pcts(
    regime_repo: RegimeAnalyticsRepository,
    *,
    as_of: date | None = None,
    settings: Settings | None = None,
) -> tuple[float, float]:
    """Return (advisory_stop_pct, critical_stop_pct) for ``as_of``.

    Flag off → static (settings.advisory_stop_pct, settings.critical_stop_pct).
    Flag on  → regime-mapped advisory (fallback when label unknown/missing),
               critical = advisory + regime_critical_offset_pct.
    """
    s = settings or get_settings()
    if not s.regime_dynamic_stops_enabled:
        return s.advisory_stop_pct, s.critical_stop_pct

    label = None
    try:
        regime = regime_repo.get_current(
            benchmark_symbol=DEFAULT_BENCHMARK_SYMBOL, as_of_date=as_of
        )
        label = (regime.regime_label or "").upper() if regime else None
    except Exception:
        label = None

    stop_map = parse_stop_map(s)
    advisory = stop_map.get(label or "", s.regime_stop_fallback_pct)
    if not stop_map:
        # Malformed map: fail safe to the static ADR-033 stops.
        return s.advisory_stop_pct, s.critical_stop_pct
    return advisory, advisory + s.regime_critical_offset_pct
