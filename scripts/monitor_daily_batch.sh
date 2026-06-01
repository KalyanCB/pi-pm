#!/usr/bin/env bash
set -euo pipefail
RUN_ID="${1:?run id required}"
BASE="${2:-http://127.0.0.1:8000}"
INTERVAL="${3:-30}"

echo "Monitoring run $RUN_ID every ${INTERVAL}s..."
while true; do
  TS=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
  STATUS_JSON=$(curl -s "$BASE/api/v1/ops/daily-batch/runs/$RUN_ID")
  TRACE_JSON=$(curl -s "$BASE/api/v1/ops/daily-batch/runs/$RUN_ID/trace")
  export TS STATUS_JSON TRACE_JSON
  python3 <<'PY'
import json, os, sys
status = json.loads(os.environ["STATUS_JSON"])
trace = json.loads(os.environ["TRACE_JSON"])
lin = trace.get("lineage", {})
load = status.get("phase_progress") or trace.get("current_load") or {}
err = status.get("error_message") or ""
print(
    f"BATCH_PROGRESS [{os.environ['TS']}] run={status['run_id'][:8]} "
    f"status={status['status']} phase={status.get('current_phase')} "
    f"pct={status.get('percent_complete')} "
    f"ingest_batches={len(lin.get('ingestion_batch_ids', []))} "
    f"rankings={len(lin.get('ranking_run_ids', []))} "
    f"validations={len(lin.get('validation_report_ids', []))} "
    f"factor_runs={len(lin.get('factor_performance_run_ids', []))} "
    f"exit_runs={len(lin.get('exit_research_run_ids', []))} "
    f"load={load} err={(err[:80] + '...') if len(err) > 80 else (err or '-')}"
)
sys.exit(0 if status["status"] in ("completed", "failed") else 1)
PY
  if [ $? -eq 0 ]; then
    ST=$(echo "$STATUS_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
    echo "BATCH_PROGRESS [$TS] MONITOR_STOP status=$ST"
    break
  fi
  sleep "$INTERVAL"
done
