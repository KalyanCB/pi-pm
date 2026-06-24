#!/usr/bin/env bash
# ============================================================================
# Pi-PM Clean Slate Backtest — 2021 to today
#
# Steps:
#   1. Wipe market_data + all derived analytics (keeps stocks/universe)
#   2. Ingest Kite OHLCV from 2021-01-01 via run_full_rebuild_from_date
#      (ingest + ranking + validation + recommendations in one pass)
#   3. Paper trade replay v4 (₹10L, ₹50K SIP, 5 slots)
#
# Required env (in .env):
#   MARKET_DATA_PROVIDER=kite
#   REGIME_DYNAMIC_STOPS_ENABLED=true
#   TIME_STOP_ENABLED=false
#   KITE_API_KEY, KITE_API_SECRET (kite_access_token loaded from DB)
#
# Estimated runtime: 3-5 hours (1000 stocks × 4+ years via Kite)
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  Pi-PM Clean Slate Backtest 2021–$(date +%Y)                              ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# ── Step 0: Validate env flags ────────────────────────────────────────────────
echo "[0/3] Checking required env flags..."
python_check=$(uv run python -c "
from app.core.config import get_settings
s = get_settings()
errors = []
if s.market_data_provider != 'kite':
    errors.append(f'MARKET_DATA_PROVIDER={s.market_data_provider} (need kite)')
if not s.regime_dynamic_stops_enabled:
    errors.append('REGIME_DYNAMIC_STOPS_ENABLED must be true')
if s.time_stop_enabled:
    errors.append('TIME_STOP_ENABLED must be false')
if not s.kite_api_key:
    errors.append('KITE_API_KEY not set')
if errors:
    print('FATAL:', ' | '.join(errors))
    exit(1)
print('OK: kite provider, regime stops, no time stop')
" 2>&1)
echo "    $python_check"
if echo "$python_check" | grep -q "FATAL"; then
    exit 1
fi

# ── Step 1: Clean slate — wipe market data + analytics ───────────────────────
echo ""
echo "[1/3] Wiping market_data + analytics (keeps stocks/universe/recommendations)..."
uv run python - <<'PYEOF'
from sqlalchemy import create_engine, text
import os

url = os.getenv("DATABASE_URL", "postgresql+psycopg://pipm:pipm@localhost:5432/pipm")
engine = create_engine(url)

# TRUNCATE CASCADE is instant — bypasses row-by-row FK checks
# Order doesn't matter with CASCADE; list root tables and let Postgres handle dependents
tables = [
    "market_data",
    "market_data_ingestion_runs",
    "ingestion_batch_runs",
    "ranking_runs",
    "recommendation_runs",
    "exit_research_runs",
    "factor_performance_runs",
    "regime_history",
    "regime_backtest_runs",
    "research_intelligence_runs",
    "daily_batch_runs",
    "paper_trades",
    "portfolio_positions",
    "portfolio_nav_history",
    "portfolio_cash_ledger",
    "portfolio_reconciliation_reports",
    "portfolio_exit_recommendations",
    "run_lineage_records",
    "full_universe_validation_runs",
    "full_universe_validation_campaigns",
]
for t in tables:
    try:
        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE {t} CASCADE"))
            print(f"  truncated {t}")
    except Exception as e:
        print(f"  skip {t}: {e}")
print("  ✓ market data + analytics wiped")
PYEOF

# ── Step 2: Ingest + Rank + Validate + Recommend from 2021 ──────────────────
echo ""
echo "[2/3] Ingest from 2021-01-01 + ranking + validation + recommendations..."
echo "      (this takes 3-5 hours for 1000 stocks via Kite)"
echo ""
uv run python scripts/run_full_rebuild_from_date.py \
    --from-date 2021-01-01 \
    --output docs/rebuild-2021-clean-slate.json

echo ""
echo "      ✓ Ingest + rebuild complete"

# ── Step 3: Paper trade replay v4 ────────────────────────────────────────────
echo ""
echo "[3/3] Paper trade replay v4 (₹10L + ₹50K SIP, 5 slots, 2021–today)..."
echo ""
uv run python scripts/replay_paper_trade_v4.py

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  Clean slate backtest complete. View results in the UI:             ║"
echo "║  Portfolio → NAV History, Performance, Positions                    ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
