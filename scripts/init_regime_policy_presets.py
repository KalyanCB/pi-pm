#!/usr/bin/env python3
"""Load Sprint 8.1 E1-E4 regime policy preset configurations."""

from __future__ import annotations

import argparse
import sys

from app.core.config import get_settings
from app.db.repositories.regime_policy_config_repository import RegimePolicyConfigRepository
from app.db.session import get_session_factory
from app.services.regime_policy_service import RegimePolicyPresetService


def main() -> int:
    parser = argparse.ArgumentParser(description="Load breakout_v1 regime policy presets (E1-E4)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating configs")
    args = parser.parse_args()

    get_settings()
    session_factory = get_session_factory()
    db = session_factory()
    try:
        repo = RegimePolicyConfigRepository(db)
        service = RegimePolicyPresetService(repo)
        configs = service.load_breakout_v1_presets(dry_run=args.dry_run)
        if not args.dry_run:
            db.commit()
        print(f"{'Would load' if args.dry_run else 'Loaded'} {len(configs)} preset config(s):")
        for config in configs:
            print(f"  - {config.policy_name} ({config.policy_type}) [{config.status}]")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
