from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

RECOVERY_TABLES = (
    "regime_history",
    "strategy_regime_performance",
    "factor_performance_metrics",
    "factor_daily_metrics",
    "factor_performance_runs",
    "research_intelligence_runs",
    "research_intelligence_reports",
    "validation_horizon_metrics",
)


def snapshot_table_counts(db: Session) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in RECOVERY_TABLES:
        counts[table] = int(db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one())
    return counts
