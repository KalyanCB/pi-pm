from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class TradingDayResolution:
    target_trading_day: date
    calendar_today: date
    session_complete: bool
    latest_benchmark_date: date | None
    resolution_reason: str


@dataclass
class DailyBatchPlan:
    target_trading_day: date
    from_date: date
    needs_ingest: bool
    ranking_gaps: dict[str, list[date]] = field(default_factory=dict)
    validation_gap_count: int = 0
    factor_ic_needed: bool = False
    regime_history_needed: bool = False
    regime_performance_needed: bool = False
    exit_research_needed: bool = False
    research_intelligence_needed: bool = False
    factor_ic_window_start: date | None = None
    factor_ic_window_end: date | None = None
    already_current: bool = False

    def to_dict(self) -> dict:
        return {
            "target_trading_day": self.target_trading_day.isoformat(),
            "from_date": self.from_date.isoformat(),
            "needs_ingest": self.needs_ingest,
            "ranking_gaps": {
                k: [d.isoformat() for d in v] for k, v in self.ranking_gaps.items()
            },
            "validation_gap_count": self.validation_gap_count,
            "factor_ic_needed": self.factor_ic_needed,
            "regime_history_needed": self.regime_history_needed,
            "regime_performance_needed": self.regime_performance_needed,
            "exit_research_needed": self.exit_research_needed,
            "research_intelligence_needed": self.research_intelligence_needed,
            "factor_ic_window_start": (
                self.factor_ic_window_start.isoformat() if self.factor_ic_window_start else None
            ),
            "factor_ic_window_end": (
                self.factor_ic_window_end.isoformat() if self.factor_ic_window_end else None
            ),
            "already_current": self.already_current,
        }
