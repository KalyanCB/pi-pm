#!/bin/sh
# Sequential v21 pipeline: bulk_rank -> bulk_rec -> paper trade.
# Run inside the pipm-api image with app/ + scripts/ mounted and --env-file the prod .env
# (DB, kite, mega/gold). Per-stage env is set inline because the date windows differ
# (rank/rec span 2018-2026; the paper trade runs 2021+). Stops on first failure.
set -e

echo "================= STAGE 1/3: bulk_rank (drop-index, all 5 strategies) ================="
REPLAY_START_DATE=2018-01-01 REPLAY_END_DATE=2026-06-25 \
  STRATEGY_SUITE=lifecycle BULK_WORKERS=3 BULK_DROP_INDEXES=1 \
  RANKING_FACTOR_CONTRIBUTIONS_ENABLED=false \
  python scripts/bulk_rank.py

echo "================= STAGE 2/3: bulk_rec ================="
REPLAY_START_DATE=2018-01-01 REPLAY_END_DATE=2026-06-25 \
  STRATEGY_SUITE=lifecycle BULK_WORKERS=3 BULK_DROP_INDEXES=1 \
  python scripts/bulk_rec.py

echo "================= STAGE 3/3: paper trade (2021+, all exit fixes ON) ================="
STRATEGY_SUITE=lifecycle \
  REPLAY_START_DATE=2021-01-01 REPLAY_END_DATE=2026-06-25 REPLAY_PAPER_FROM=2021-01-01 \
  REPLAY_PHASED=1 REPLAY_SKIP_RANK=1 REPLAY_SKIP_REC=1 REPLAY_NO_RESUME=1 \
  LIFECYCLE_ENTRY_ENABLED=true LIFECYCLE_HANDOFF_EXITS_ENABLED=true LIFECYCLE_ENTRY_TOP_RANK=5 \
  LIFECYCLE_MAX_POSITIONS=18 LIFECYCLE_MAX_BUY_PER_DAY=5 \
  ENTRY_EXECUTE_NEXT_SESSION=true NEXT_OPEN_FILLS_ENABLED=true EXIT_FILLS_AT_CLOSE_ENABLED=true \
  GOLD_ROTATION_ENABLED=false MEGA_DIVERSIFIER_ENABLED=false FAST_DEPLOY_ENABLED=false \
  HITL_ENABLED=false PAPER_TRADING_ENABLED=true \
  python scripts/replay_fast.py

echo "================= PIPELINE COMPLETE ================="
