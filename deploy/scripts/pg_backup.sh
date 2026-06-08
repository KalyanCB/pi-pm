#!/usr/bin/env bash
# Nightly logical backup of the VPS Pi-PM DB (logical dump != Hostinger
# disk snapshot — keep both). Add to the deploy user's crontab:
#   0 1 * * *  /opt/pi-pm/current/deploy/scripts/pg_backup.sh >> /var/log/pipm-backup.log 2>&1
set -euo pipefail

BASE="/opt/pi-pm"
OUT_DIR="${BASE}/shared/backups"
RETAIN_DAYS="${RETAIN_DAYS:-14}"
REL="$(readlink ${BASE}/current)"
COMPOSE=(docker compose -p pipm --project-directory "${REL}/docker" --env-file "${REL}/.env" \
  -f "${REL}/docker/docker-compose.yml" -f "${REL}/docker/docker-compose.prod.yml")
DB_CID="$("${COMPOSE[@]}" ps -q db)"
[ -n "${DB_CID}" ] || { echo "$(date -Is) FATAL: db container not found"; exit 1; }

STAMP="$(date +%Y%m%d-%H%M)"
OUT="${OUT_DIR}/pipm-auto-${STAMP}.dump"
mkdir -p "${OUT_DIR}"

docker exec "${DB_CID}" pg_dump -U pipm -d pipm -Fc -Z6 -f /tmp/auto.dump
docker cp "${DB_CID}:/tmp/auto.dump" "${OUT}"
docker exec "${DB_CID}" rm -f /tmp/auto.dump
sha256sum "${OUT}" > "${OUT}.sha256"

find "${OUT_DIR}" -name 'pipm-auto-*.dump*' -mtime +"${RETAIN_DAYS}" -delete
echo "$(date -Is) backup ok: ${OUT}"
