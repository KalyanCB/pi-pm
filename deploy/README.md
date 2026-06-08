# Pi-PM Deployment — Hostinger KVM4 (paper auto-pilot)

Target: `srv1733992` / `187.127.177.217` · Ubuntu · 4 vCPU / 16 GB / 200 GB
Mode: **paper auto-pilot** — `HITL_ENABLED=false`, `PAPER_TRADING_ENABLED=true`,
`ENABLE_LIVE_TRADING=false`. Auth **off** (`AUTH_ENABLED=false`, web `AUTH_BYPASS=true`).
Access: single public origin `http://187.127.177.217` via Caddy. No domain/TLS.

> ⚠️ HTTP + no auth on a public IP = anyone who finds the IP has full API access.
> Bounded because it is paper-only and live is gated off. Recommended hardening
> later: restrict UFW `:80` to your IP, or put the box behind Tailscale/WireGuard.

## Architecture

```
internet :80 ──> Caddy ──/api/*──> api:8000 (FastAPI)         [not published to host]
                      └──/*──────> /srv  (Expo web static dist)
                                   api ── db:5432 (Postgres 16) [not published to host]
                                          volume: pipm_pgdata (shared across releases)
```

Immutable release model: each deploy unpacks the tagged tarball into
`/opt/pi-pm/releases/pi-pm-<tag>/`, builds a pinned image `pipm-api:<tag>`,
then flips `/opt/pi-pm/current` to it. Rollback = flip the symlink back.

```
/opt/pi-pm/
  releases/pi-pm-release-<date>-<sha>/   # unpacked snapshot (immutable)
  current -> releases/pi-pm-release-...   # what the stack runs
  shared/
    .env            # API secrets/flags (from deploy/.env.api.example), chmod 600
    .env.web        # frontend build env  (from deploy/.env.web.example)
    backups/        # DB dumps (manual + nightly)
```

## Artifacts in this directory

| File | Runs on | Purpose |
|------|---------|---------|
| `../docker/docker-compose.prod.yml` | VPS | Prod overlay: no public db/api ports, Caddy, pinned image, healthcheck |
| `Caddyfile` | VPS | Reverse proxy `/api/*` → api, `/*` → static SPA |
| `.env.api.example` | VPS | Template → `shared/.env` |
| `.env.web.example` | VPS | Template → `shared/.env.web` |
| `scripts/provision.sh` | VPS (root) | Baseline harden + Docker + UFW + layout |
| `scripts/deploy.sh` | VPS (deploy user) | Unpack snapshot, build FE, up stack, flip symlink |
| `scripts/rollback.sh` | VPS | Switch `current` to a prior release |
| `scripts/dump_local_db.sh` | **local** | `pg_dump -Fc` of local DB + checksum |
| `scripts/restore_db.sh` | VPS | `pg_restore` the dump into the VPS DB |
| `scripts/pg_backup.sh` | VPS (cron) | Nightly logical DB backup, 14-day retention |
| `scripts/daily_batch.sh` | VPS (cron) | Daily NIFTY 500 paper auto-pilot batch |

## End-to-end sequence

1. **Local — dump the DB** (4.5 GB → ~1–1.5 GB):
   ```bash
   bash deploy/scripts/dump_local_db.sh
   ```
2. **VPS — provision** (as root):
   ```bash
   DEPLOY_USER=pipm bash provision.sh
   ```
3. **VPS — secrets**: copy templates and fill them:
   ```bash
   cp deploy/.env.api.example /opt/pi-pm/shared/.env   && chmod 600 /opt/pi-pm/shared/.env
   cp deploy/.env.web.example /opt/pi-pm/shared/.env.web
   # edit: POSTGRES_PASSWORD, JWT_SECRET_KEY, RELEASE_TAG (= the tag you deploy)
   ```
4. **Ship artifacts** to `/opt/pi-pm/shared/`:
   release tarball + `.sha256`, and the DB dump + `.sha256` (use `rsync -avP --partial`).
5. **VPS — deploy** (builds frontend + brings stack up, runs migrations):
   ```bash
   bash <release>/deploy/scripts/deploy.sh /opt/pi-pm/shared/pi-pm-release-<tag>.tar.gz
   ```
6. **VPS — import data** (do this before relying on the app):
   ```bash
   bash /opt/pi-pm/current/deploy/scripts/restore_db.sh \
     /opt/pi-pm/shared/backups/pipm-<stamp>.dump
   # verify alembic_head = 20260611_0027, then: docker compose ... up -d
   ```
7. **Verify**: `http://187.127.177.217/api/v1/health` and the UI loads.
8. **Cron** (deploy user `crontab -e`):
   ```cron
   30 16 * * 1-5  /opt/pi-pm/current/deploy/scripts/daily_batch.sh >> /var/log/pipm-daily-batch.log 2>&1
   0  1  * * *    /opt/pi-pm/current/deploy/scripts/pg_backup.sh   >> /var/log/pipm-backup.log     2>&1
   ```
   Plus enable Hostinger daily backups + take a snapshot after first good deploy.

## Migration-vs-data invariant

The deployed release's alembic head **must equal** the dump's head
(`20260611_0027`). The release tag was cut from merged `main` (PR #14,
`552c645`) which carries `20260611_0027`, so this holds. If you re-cut the
release, re-confirm before restoring.

## Rollback

```bash
bash /opt/pi-pm/current/deploy/scripts/rollback.sh                  # list
bash /opt/pi-pm/current/deploy/scripts/rollback.sh pi-pm-release-<older-tag>
```
Code-only. The DB volume is shared; if the newer release migrated the schema,
restore a pre-deploy dump or downgrade migrations separately.

## Notes / TODO to confirm at execution

- `daily_batch.sh` runs the batch client **inside** the api container; confirm
  the script's default API base URL resolves to `http://localhost:8000`
  (pass `--base-url` if it needs it).
- Frontend is built with a **dockerized** Node 20 + pnpm 9.15 (no host Node
  required). First build pulls `node:20-bookworm-slim`.
- `pg_dump`/`pg_restore`/`psql` always run inside the **db** container
  (postgres:16-alpine), reached via `docker exec` — no host Postgres client.
