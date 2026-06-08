#!/usr/bin/env bash
# Pi-PM deploy — materialize a release snapshot and bring up the stack.
# Run on the VPS as the deploy user.
#
#   bash deploy/scripts/deploy.sh /opt/pi-pm/shared/pi-pm-release-<tag>.tar.gz
#
# Steps: verify checksum -> unpack into releases/ -> link shared .env ->
# build frontend (dockerized node, no host toolchain) -> build+up the
# pinned stack -> flip the `current` symlink -> health check.
# The Postgres data volume (pipm_pgdata) is shared across releases.
set -euo pipefail

BASE="/opt/pi-pm"
SHARED="${BASE}/shared"
TARBALL="${1:?usage: deploy.sh <release-tarball.tar.gz>}"

[ -f "${SHARED}/.env" ] || { echo "FATAL: ${SHARED}/.env missing (from deploy/.env.api.example)"; exit 1; }

TAG="$(basename "${TARBALL}" .tar.gz | sed 's/^pi-pm-//')"   # release-<date>-<sha>
RELEASE_DIR="${BASE}/releases/pi-pm-${TAG}"

if [ -f "${TARBALL}.sha256" ]; then
  echo "==> Verify checksum"
  (cd "$(dirname "${TARBALL}")" && sha256sum -c "$(basename "${TARBALL}").sha256")
fi

echo "==> Unpack -> ${RELEASE_DIR}"
mkdir -p "${BASE}/releases"
rm -rf "${RELEASE_DIR}"
tar xzf "${TARBALL}" -C "${BASE}/releases"   # creates pi-pm-<tag>/

echo "==> Link shared secrets (.env at release root)"
ln -sfn "${SHARED}/.env" "${RELEASE_DIR}/.env"

echo "==> Frontend web .env (build-time inlined)"
if [ -f "${SHARED}/.env.web" ]; then
  cp "${SHARED}/.env.web" "${RELEASE_DIR}/frontend/apps/web/.env"
else
  cp "${RELEASE_DIR}/deploy/.env.web.example" "${RELEASE_DIR}/frontend/apps/web/.env"
fi

echo "==> Build frontend (Expo web export) via dockerized node 20"
docker run --rm \
  -v "${RELEASE_DIR}/frontend:/work" -w /work \
  -e CI=1 node:20-bookworm-slim bash -lc '
    corepack enable &&
    corepack prepare pnpm@9.15.0 --activate &&
    pnpm install --frozen-lockfile &&
    pnpm --filter @pipm/web build'
[ -d "${RELEASE_DIR}/frontend/apps/web/dist" ] || { echo "FATAL: no frontend dist/ produced"; exit 1; }

echo "==> Build + start stack"
export RELEASE_TAG="${TAG}"
COMPOSE=(docker compose -p pipm --project-directory "${RELEASE_DIR}/docker" --env-file "${RELEASE_DIR}/.env" \
  -f "${RELEASE_DIR}/docker/docker-compose.yml" \
  -f "${RELEASE_DIR}/docker/docker-compose.prod.yml")
"${COMPOSE[@]}" build
"${COMPOSE[@]}" up -d

echo "==> Flip current -> ${RELEASE_DIR}"
ln -sfn "${RELEASE_DIR}" "${BASE}/current"

echo "==> Wait for API health (entrypoint runs 'alembic upgrade head')"
ok=0
for _ in $(seq 1 36); do
  if "${COMPOSE[@]}" exec -T api python -c \
      "import urllib.request;urllib.request.urlopen('http://localhost:8000/api/v1/health',timeout=5)" 2>/dev/null; then
    ok=1; break
  fi
  sleep 5
done
# (COMPOSE pins -p pipm + --project-directory so relative paths resolve to the release root)
[ "${ok}" = 1 ] && echo "API healthy." || { echo "WARN: API not healthy yet — check: ${COMPOSE[*]} logs api"; }

PUBLIC_HOST="$(grep -E '^PUBLIC_HOST=' "${SHARED}/.env" | cut -d= -f2 || true)"
echo "==> Done. current -> $(readlink ${BASE}/current)"
echo "    UI:  http://${PUBLIC_HOST:-<host>}/"
echo "    API: http://${PUBLIC_HOST:-<host>}/api/v1/health"
echo "If this is the FIRST deploy with imported data, run restore_db.sh BEFORE"
echo "relying on the app (see deploy/README.md)."
