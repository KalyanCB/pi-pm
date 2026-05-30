from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class BacktestGenerationResult:
    universe_code: str
    strategy_name: str
    strategy_version: str
    benchmark_symbol: str
    start_date: date
    end_date: date
    trading_days_total: int
    runs_created: int
    runs_reused: int
    runs_failed: int
    failed_dates: tuple[date, ...]
