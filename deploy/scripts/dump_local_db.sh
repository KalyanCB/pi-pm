#!/usr/bin/env bash
# Dump the LOCAL Pi-PM Postgres (docker) to a portable custom-format file.
# Run on your LOCAL/dev machine. Read-only against the database.
#
#   bash deploy/scripts/dump_local_db.sh
#   DB_CONTAINER=docker-db-1 OUT_DIR=./backups bash deploy/scripts/dump_local_db.sh
set -euo pipefail

CONTAINER="${DB_CONTAINER:-docker-db-1}"
OUT_DIR="${OUT_DIR:-./backups}"
STAMP="$(date +%Y%m%d-%H%M)"
OUT="${OUT_DIR}/pipm-${STAMP}.dump"

mkdir -p "${OUT_DIR}"
echo "==> Dumping 'pipm' from ${CONTAINER} (custom format, level-6 compression)"
docker exec "${CONTAINER}" pg_dump -U pipm -d pipm -Fc -Z6 -f /tmp/pipm.dump
docker cp "${CONTAINER}:/tmp/pipm.dump" "${OUT}"
docker exec "${CONTAINER}" rm -f /tmp/pipm.dump

shasum -a 256 "${OUT}" | tee "${OUT}.sha256"
ls -lh "${OUT}"

cat <<EOF

==> Dump ready: ${OUT}
Ship it to the VPS:
  rsync -avP --partial "${OUT}" "${OUT}.sha256" \\
    <user>@187.127.177.217:/opt/pi-pm/shared/backups/
Then on the VPS:
  bash /opt/pi-pm/current/deploy/scripts/restore_db.sh \\
    /opt/pi-pm/shared/backups/$(basename "${OUT}")
EOF
