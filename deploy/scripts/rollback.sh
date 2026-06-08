#!/usr/bin/env bash
# Pi-PM rollback — point `current` at a previous release and restart.
#   bash deploy/scripts/rollback.sh                      # list releases
#   bash deploy/scripts/rollback.sh pi-pm-release-<tag>  # roll back to it
#
# NOTE: the DB (volume pipm_pgdata) is shared across releases. This rolls
# back CODE only. If the newer release applied migrations, roll those back
# (or restore a pre-deploy DB dump) separately.
set -euo pipefail
BASE="/opt/pi-pm"

if [ $# -eq 0 ]; then
  echo "Releases under ${BASE}/releases:"; ls -1 "${BASE}/releases" 2>/dev/null || echo "  (none)"
  echo "current -> $(readlink ${BASE}/current 2>/dev/null || echo none)"
  exit 0
fi

NAME="$(basename "$1")"
TARGET_DIR="${BASE}/releases/${NAME}"
[ -d "${TARGET_DIR}" ] || { echo "No such release: ${TARGET_DIR}"; exit 1; }
TAG="$(echo "${NAME}" | sed 's/^pi-pm-//')"

CUR="$(readlink ${BASE}/current 2>/dev/null || true)"
if [ -n "${CUR}" ] && [ -d "${CUR}" ] && [ "${CUR}" != "${TARGET_DIR}" ]; then
  echo "==> Stopping current stack (${CUR})"
  docker compose -p pipm --project-directory "${CUR}/docker" --env-file "${CUR}/.env" \
    -f "${CUR}/docker/docker-compose.yml" -f "${CUR}/docker/docker-compose.prod.yml" down || true
fi

echo "==> Bring up ${TARGET_DIR} (image pipm-api:${TAG})"
export RELEASE_TAG="${TAG}"
docker compose -p pipm --project-directory "${TARGET_DIR}/docker" --env-file "${TARGET_DIR}/.env" \
  -f "${TARGET_DIR}/docker/docker-compose.yml" \
  -f "${TARGET_DIR}/docker/docker-compose.prod.yml" up -d

ln -sfn "${TARGET_DIR}" "${BASE}/current"
echo "==> current -> $(readlink ${BASE}/current)"
