from __future__ import annotations

import logging
import time

from app.core.structured_logging import log_event
from app.workspace_exit_research.constants import (
    PERSISTENCE_PERCENT_FLOOR,
    SIMULATION_PERCENT_CAP,
)

logger = logging.getLogger(__name__)

PROGRESS_LOG_INTERVAL = 100
PERSIST_LOG_INTERVAL = 10


def log_backfill_startup(
    *,
    strategy_name: str,
    strategy_version: str,
    universe_code: str,
    start_date,
    end_date,
    total_entries: int,
) -> float:
    log_event(
        logger,
        "exit_research_startup",
        strategy=strategy_name,
        strategy_version=strategy_version,
        universe=universe_code,
        start_date=start_date,
        end_date=end_date,
        total_entries=total_entries,
    )
    return time.monotonic()


def log_phase_changed(*, strategy_name: str, phase: str) -> None:
    log_event(
        logger,
        "exit_research_phase_changed",
        strategy=strategy_name,
        phase=phase,
    )


def log_entry_progress(
    *,
    strategy_name: str,
    processed: int,
    total: int,
    started_monotonic: float,
) -> None:
    elapsed = time.monotonic() - started_monotonic
    pct = simulation_percent_complete(processed, total)
    rate = processed / elapsed if elapsed > 0 and processed else 0.0
    remaining = total - processed
    eta = remaining / rate if rate > 0 else None
    log_event(
        logger,
        "exit_research_progress",
        strategy=strategy_name,
        processed=processed,
        total=total,
        pct=round(pct, 2),
        elapsed_sec=round(elapsed, 1),
        eta_sec=round(eta, 1) if eta is not None else None,
        rate=f"{rate:.1f}_entries_per_sec",
    )


def log_persist_progress(
    *,
    strategy_name: str,
    phase: str,
    processed: int,
    total: int,
    started_monotonic: float,
) -> None:
    elapsed = time.monotonic() - started_monotonic
    pct = persistence_percent_complete(processed, total)
    log_event(
        logger,
        "exit_research_persist_progress",
        strategy=strategy_name,
        phase=phase,
        processed=processed,
        total=total,
        percent_complete=round(pct, 2),
        elapsed_sec=round(elapsed, 1),
    )


def log_policy_batch_completed(policy_family: str, *, entries: int) -> None:
    log_event(
        logger,
        "exit_research_policy_batch",
        family=policy_family,
        status="completed",
        entries=entries,
    )


def log_alpha_decay_progress(
    *,
    entries_processed: int,
    alpha_points_generated: int,
    alpha_rows_written: int,
) -> None:
    log_event(
        logger,
        "exit_research_alpha_decay",
        entries_processed=entries_processed,
        alpha_points_generated=alpha_points_generated,
        alpha_rows_written=alpha_rows_written,
    )


def log_backfill_complete(
    *,
    strategy_name: str,
    runtime_sec: float,
    simulations_generated: int,
    alpha_points_generated: int,
    database_rows_written: int,
    signals_processed: int,
) -> None:
    log_event(
        logger,
        "exit_research_complete",
        strategy=strategy_name,
        runtime_sec=round(runtime_sec, 1),
        simulations_generated=simulations_generated,
        alpha_points_generated=alpha_points_generated,
        database_rows_written=database_rows_written,
        signals_processed=signals_processed,
    )


def should_log_progress(processed: int, total: int) -> bool:
    return processed % PROGRESS_LOG_INTERVAL == 0 or processed == total


def should_log_persist_progress(processed: int, total: int) -> bool:
    if total <= 0:
        return False
    return processed % PERSIST_LOG_INTERVAL == 0 or processed == total


def simulation_percent_complete(processed: int, total: int) -> float:
    if not total:
        return 0.0
    raw = processed / total * SIMULATION_PERCENT_CAP
    if processed >= total:
        return SIMULATION_PERCENT_CAP
    return min(SIMULATION_PERCENT_CAP - 0.0001, raw)


def persistence_percent_complete(processed: int, total: int) -> float:
    if not total:
        return PERSISTENCE_PERCENT_FLOOR
    span = 100.0 - PERSISTENCE_PERCENT_FLOOR
    return PERSISTENCE_PERCENT_FLOOR + (processed / total) * span


def simulation_progress_fields(
    processed: int,
    total: int,
    started_monotonic: float,
) -> dict[str, float | int]:
    elapsed = time.monotonic() - started_monotonic
    return {
        "processed_entries": processed,
        "total_entries": total,
        "percent_complete": round(simulation_percent_complete(processed, total), 4),
        "elapsed_seconds": round(elapsed, 2),
    }


def persistence_progress_fields(
    processed: int,
    total: int,
    started_monotonic: float,
) -> dict[str, float | int]:
    elapsed = time.monotonic() - started_monotonic
    return {
        "persistence_items_processed": processed,
        "persistence_items_total": total,
        "percent_complete": round(persistence_percent_complete(processed, total), 4),
        "elapsed_seconds": round(elapsed, 2),
    }
