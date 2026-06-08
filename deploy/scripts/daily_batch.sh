#!/usr/bin/env bash
# Daily NIFTY 500 batch — PAPER AUTO-PILOT. Runs inside the api container.
# Cron (deploy user), weekdays ~post-close IST:
#   30 16 * * 1-5  /opt/pi-pm/current/deploy/scripts/daily_batch.sh >> /var/log/pipm-daily-batch.log 2>&1
#
# --pilot-auto-execute is PAPER only; ENABLE_LIVE_TRADING stays false.
set -euo pipefail

BASE="/opt/pi-pm"
REL="$(readlink ${BASE}/current)"
COMPOSE=(docker compose -p pipm --project-directory "${REL}/docker" \
  -f "${REL}/docker/docker-compose.yml" -f "${REL}/docker/docker-compose.prod.yml")

echo "$(date -Is) starting daily batch"
"${COMPOSE[@]}" exec -T api python scripts/run_daily_nifty500_batch.py \
  --portfolio --pilot-auto-approve --pilot-auto-execute
echo "$(date -Is) daily batch finished"
