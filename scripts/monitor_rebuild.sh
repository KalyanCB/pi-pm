#!/usr/bin/env bash
# Poll rebuild progress every 5 minutes until batch completes or process exits.
set -euo pipefail
cd "$(dirname "$0")/.."
LOG=docs/rebuild-monitor.log
BATCH_ID=95506d13-b50a-4288-986a-41f780441c20

snapshot() {
  .venv/bin/python <<PY
from datetime import date, datetime, timezone, timedelta
from app.db.session import get_session_factory
from sqlalchemy import text

FROM_D, TO_D = date(2024, 6, 1), date(2026, 6, 2)
BATCH_ID = "$BATCH_ID"
BATCH_START = datetime(2026, 6, 2, 15, 50, 52, tzinfo=timezone.utc)

Session = get_session_factory()
with Session() as db:
    batch = db.execute(text("""
        SELECT status, current_phase, percent_complete, error_message
        FROM daily_batch_runs WHERE id = :id
    """), {"id": BATCH_ID}).mappings().first()
    expected = db.execute(text("""
        SELECT COUNT(DISTINCT date) FROM market_data md
        JOIN stocks s ON s.id = md.stock_id
        WHERE s.symbol = '^NSEI' AND md.date >= :f AND md.date <= :t
    """), {"f": FROM_D, "t": TO_D}).scalar() or 493
    new_rank = db.execute(text("SELECT COUNT(*) FROM ranking_runs WHERE started_at > :t"), {"t": BATCH_START}).scalar()
    latest = db.execute(text("""
        SELECT strategy_name, as_of_date FROM ranking_runs ORDER BY started_at DESC LIMIT 1
    """)).first()
    since5 = datetime.now(timezone.utc) - timedelta(minutes=5)
    recent = db.execute(text("SELECT COUNT(*) FROM ranking_runs WHERE started_at > :s"), {"s": since5}).scalar()
    import subprocess
    running = bool(subprocess.run(["pgrep", "-f", "run_full_rebuild_from_date"], capture_output=True, text=True).stdout.strip())
    rank_units = expected * 2
    rank_pct = 100 * new_rank / rank_units if rank_units else 0
    db_pct = float(batch["percent_complete"] or 0)
    phase = batch["current_phase"]
    est = 12 + (rank_pct / 100) * 20 if phase == "rankings" else db_pct
    if batch["status"] == "completed":
        est = 100
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(
        f"{ts} | status={batch['status']} phase={phase} db={db_pct:.0f}% est={est:.0f}% "
        f"rank={new_rank}/{rank_units} ({rank_pct:.0f}%) latest={latest[0]}@{latest[1]} "
        f"rate5m={recent} proc={running} err={batch['error_message'] or 'none'}"
    )
    if batch["status"] in ("completed", "failed"):
        raise SystemExit(0 if batch["status"] == "completed" else 1)
    if not running and batch["status"] != "completed":
        raise SystemExit(2)
PY
}

echo "=== rebuild monitor started $(date -u) ===" >> "$LOG"
while true; do
  line=$(snapshot) || rc=$?
  echo "$line" | tee -a "$LOG"
  if [[ "${rc:-0}" -eq 0 ]] || [[ "${rc:-0}" -eq 1 ]]; then
    echo "=== monitor stopped: exit ${rc:-0} ===" >> "$LOG"
    exit "${rc:-0}"
  fi
  if [[ "${rc:-0}" -eq 2 ]]; then
    echo "=== WARNING: process gone but batch not completed ===" >> "$LOG"
    exit 2
  fi
  sleep 300
done
