#!/usr/bin/env bash
# Daily NIFTY 500 batch — PAPER AUTO-PILOT, deploy-lane (N-1) execution.
# Cron (root), weekdays ~post-close IST:
#   30 16 * * 1-5  /opt/pi-pm/current/deploy/scripts/daily_batch.sh >> /var/log/pipm-daily-batch.log 2>&1
#
# Two phases, matching local behaviour ("buy from N-1 trading day BUYs"):
#   1) Advance the pipeline for the current session — ingest/rank/recommend/
#      validate (NO portfolio phase). This pulls the latest EOD data in so it
#      can mature over the coming sessions.
#   2) Execute the paper-pilot portfolio phase against the *previous* completed
#      trading day (N-1), whose recommendations are matured. Paper auto-approve/
#      execute are server-side when HITL off + paper on; ENABLE_LIVE_TRADING
#      stays false.
set -euo pipefail

BASE="/opt/pi-pm"
REL="$(readlink ${BASE}/current)"
COMPOSE=(docker compose -p pipm --project-directory "${REL}/docker" --env-file "${REL}/.env" \
  -f "${REL}/docker/docker-compose.yml" -f "${REL}/docker/docker-compose.prod.yml")

echo "$(date -Is) [1/2] advance pipeline for current session (ingest/rank/recommend; no paper)"
"${COMPOSE[@]}" exec -T api python scripts/run_daily_nifty500_batch.py

echo "$(date -Is) [2/2] resolve N-1 (last completed trading day before today)"
TARGET="$(
  "${COMPOSE[@]}" exec -T db psql -U pipm -d pipm -tAc \
    "SELECT max(as_of_date) FROM recommendation_runs WHERE status='completed' AND as_of_date < CURRENT_DATE;" \
  | tr -d '[:space:]'
)"
if [ -z "${TARGET}" ] || [ "${TARGET}" = "None" ]; then
  echo "$(date -Is) no prior completed recommendation day found — skipping paper execution"
  exit 0
fi
echo "$(date -Is) deploy-lane target (N-1) = ${TARGET}; executing paper BUYs"
"${COMPOSE[@]}" exec -T api python scripts/run_daily_nifty500_batch.py --portfolio --target-date "${TARGET}"
echo "$(date -Is) daily batch finished"
