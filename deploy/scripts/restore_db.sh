#!/usr/bin/env bash
# Restore a pg_dump (custom format) into the VPS Pi-PM database.
# Run on the VPS BEFORE first reliance on the app (api may be up; this
# brings db up and restores into it). Safe to run with only db started.
#
#   bash deploy/scripts/restore_db.sh /opt/pi-pm/shared/backups/pipm-<stamp>.dump
#
# Uses --clean --if-exists so it is idempotent against an already-migrated
# or partially-populated schema. Expected alembic head after restore:
# 20260611_0027 (must match the deployed release's migration head).
set -euo pipefail

BASE="/opt/pi-pm"
DUMP="${1:?usage: restore_db.sh <dump-file>}"
REL="$(readlink ${BASE}/current)"
COMPOSE=(docker compose -p pipm --project-directory "${REL}/docker" --env-file "${REL}/.env" \
  -f "${REL}/docker/docker-compose.yml" -f "${REL}/docker/docker-compose.prod.yml")

if [ -f "${DUMP}.sha256" ]; then
  echo "==> Verify checksum"
  (cd "$(dirname "${DUMP}")" && sha256sum -c "$(basename "${DUMP}").sha256")
fi

echo "==> Ensure db is up"
"${COMPOSE[@]}" up -d db
sleep 5
DB_CID="$("${COMPOSE[@]}" ps -q db)"
[ -n "${DB_CID}" ] || { echo "FATAL: db container not found"; exit 1; }

echo "==> Copy dump into db container"
docker cp "${DUMP}" "${DB_CID}:/tmp/restore.dump"

echo "==> pg_restore (cleaning existing objects first)"
docker exec "${DB_CID}" pg_restore -U pipm -d pipm \
  --clean --if-exists --no-owner --no-privileges --jobs=4 /tmp/restore.dump \
  || echo "NOTE: pg_restore returned non-zero (often benign DROP-of-missing on first run). Review output."
docker exec "${DB_CID}" rm -f /tmp/restore.dump

echo "==> Verify"
docker exec "${DB_CID}" psql -U pipm -d pipm -c "SELECT version_num AS alembic_head FROM alembic_version;"
docker exec "${DB_CID}" psql -U pipm -d pipm -c \
  "SELECT 'market_data' AS tbl, count(*) FROM market_data
   UNION ALL SELECT 'ranking_runs', count(*) FROM ranking_runs
   UNION ALL SELECT 'recommendation_runs', count(*) FROM recommendation_runs;"

echo "==> Expected alembic_head = 20260611_0027."
echo "    Now (re)start the full stack:  ${COMPOSE[*]} up -d"
