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
    exit_research_needed: bool = False
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
            "exit_research_needed": self.exit_research_needed,
            "already_current": self.already_current,
        }
