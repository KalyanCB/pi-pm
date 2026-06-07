#!/usr/bin/env python3
"""Replay Simulation Framework CLI.

Usage:
    uv run python scripts/run_replay.py configs/EXP01_SMOKE_2W.yaml
    uv run python scripts/run_replay.py configs/EXP03_REGIME_TRANSITION_6M.yaml --verbose
    uv run python scripts/run_replay.py configs/EXP05_FULL_REPLAY.yaml --output-dir /tmp/results
    uv run python scripts/run_replay.py configs/EXP01_SMOKE_2W.yaml --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path when run directly
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )


def _dry_run(config_path: Path) -> None:
    from app.replay.config.experiment_config import ReplayExperimentConfig
    from app.db.session import get_session_factory
    from sqlalchemy import text

    config = ReplayExperimentConfig.from_yaml(config_path)
    print(f"\nDry run: {config.experiment_id}")
    print(f"  Name:        {config.name}")
    print(f"  Period:      {config.start_date} → {config.end_date}")
    print(f"  Mode:        {config.mode}")
    print(f"  Strategies:  {', '.join(config.strategies)}")
    print(f"  Initial cash: {config.capital.initial_cash:,.0f}")
    print(f"  Max positions: {config.portfolio.max_positions}")

    try:
        SessionFactory = get_session_factory()
        with SessionFactory() as db:
            rows = db.execute(
                text(
                    """
                    SELECT COUNT(DISTINCT as_of_date) AS cnt
                    FROM ranking_runs
                    WHERE as_of_date >= :start
                      AND as_of_date <= :end
                      AND strategy_name = ANY(:strategies)
                      AND status = 'completed'
                    """
                ),
                {
                    "start": config.start_date,
                    "end": config.end_date,
                    "strategies": config.strategies,
                },
            ).fetchone()
            trading_days = rows.cnt if rows else 0
        print(f"  Trading days with data: {trading_days}")
    except Exception as e:
        print(f"  [WARNING] Could not query DB: {e}")

    print("\nConfig is valid. Use without --dry-run to execute.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pi-PM Replay Simulation Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("config_path", type=Path, help="Path to experiment YAML config")
    parser.add_argument("--verbose", action="store_true", help="Print day-by-day progress")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Override output directory for reports",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config and count trading days, don't run",
    )
    args = parser.parse_args()

    _setup_logging(args.verbose)

    config_path = args.config_path.resolve()
    if not config_path.exists():
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        return 1

    if args.dry_run:
        _dry_run(config_path)
        return 0

    from app.replay.config.experiment_config import ReplayExperimentConfig
    from app.replay.engine import ReplayEngine

    config = ReplayExperimentConfig.from_yaml(config_path)

    if args.output_dir:
        config.outputs.output_dir = args.output_dir

    engine = ReplayEngine(verbose=args.verbose)
    result = engine.run(config)

    m = result.metrics
    print(f"\n{'='*60}")
    print(f"Replay complete: {config.experiment_id}")
    print(f"{'='*60}")
    print(f"  Days processed : {result.days_processed} ({result.days_skipped} skipped)")
    print(f"  Initial NAV    : {m.initial_nav:>12,.0f}")
    print(f"  Final NAV      : {m.final_nav:>12,.0f}")
    print(f"  Total Return   : {m.total_return_pct:>+10.2f}%")
    print(f"  CAGR           : {m.cagr_pct:>+10.2f}%")
    if m.sharpe_ratio:
        print(f"  Sharpe         : {m.sharpe_ratio:>12.2f}")
    print(f"  Max Drawdown   : {m.max_drawdown_pct:>+10.2f}%")
    print(f"  Win Rate       : {m.win_rate_pct:>10.1f}%")
    print(f"  Total Buys     : {m.total_buys:>12}")
    print(f"  Total Exits    : {m.total_exits:>12}")
    if result.output_dir:
        print(f"\n  Reports        : {result.output_dir}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
