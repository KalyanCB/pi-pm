"""Phase 1 — targeted intraday backfill for realistic next-session VWAP fills.

Pulls intraday (default 60-minute) OHLCV from Kite ONLY for symbols that were actually
traded, and ONLY for the sessions around each entry/exit decision date (the next-session
fill window). This is the lean path: a few thousand chunked calls instead of millions for
the whole universe × full history.

Idempotent: upserts on (stock_id, ts, interval, source) DO NOTHING, so it is safe to
re-run / resume.

Usage:
  uv run python scripts/backfill_intraday_fills.py            # all traded symbols, 60min
  uv run python scripts/backfill_intraday_fills.py --interval minute --buffer-days 3
  uv run python scripts/backfill_intraday_fills.py --limit-symbols 5 --dry-run

Requires a valid Kite token (token_store / KITE_ACCESS_TOKEN) and the Kite historical-data
subscription add-on for intraday history.
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import UTC, date, datetime, timedelta

sys.path.insert(0, ".")

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.models.market_data_intraday import MarketDataIntraday
from app.models.portfolio_position import PortfolioPosition
from app.models.stock import Stock
from app.providers.kite import token_store
from app.providers.kite.client import KiteConnectProvider

SOURCE = "kite"


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _merge_windows(dates: set[date], buffer_days: int) -> list[tuple[date, date]]:
    """Expand each decision date to [d, d+buffer] and merge overlapping ranges."""
    if not dates:
        return []
    spans = sorted((d, d + timedelta(days=buffer_days)) for d in dates)
    merged: list[tuple[date, date]] = [spans[0]]
    for start, end in spans[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + timedelta(days=1):
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def main() -> int:
    ap = argparse.ArgumentParser(description="Targeted intraday backfill for realistic fills")
    settings = get_settings()
    ap.add_argument("--interval", default=settings.intraday_interval)
    ap.add_argument("--buffer-days", type=int, default=5)
    ap.add_argument("--limit-symbols", type=int, default=None, help="Cap symbols (testing)")
    ap.add_argument("--dry-run", action="store_true", help="Plan only — no fetch/write")
    args = ap.parse_args()

    db = get_session_factory()()

    # Decision dates per traded stock (entry + exit) → the next-session fill windows.
    rows = db.execute(
        select(Stock.id, Stock.symbol, PortfolioPosition.entry_date, PortfolioPosition.exit_date)
        .join(PortfolioPosition, PortfolioPosition.stock_id == Stock.id)
    ).all()

    needs: dict[tuple, set[date]] = {}
    for stock_id, symbol, entry_d, exit_d in rows:
        if not symbol or symbol.startswith("^"):
            continue
        bucket = needs.setdefault((stock_id, symbol), set())
        for d in (entry_d, exit_d):
            if d is not None:
                bucket.add(d)

    symbols = list(needs.items())
    if args.limit_symbols:
        symbols = symbols[: args.limit_symbols]

    total_windows = sum(len(_merge_windows(dts, args.buffer_days)) for _, dts in symbols)
    _log(
        f"interval={args.interval}  traded_symbols={len(symbols)}  "
        f"merged_windows={total_windows}  buffer={args.buffer_days}d  dry_run={args.dry_run}"
    )
    if args.dry_run:
        for (sid, sym), dts in symbols[:10]:
            _log(f"  {sym}: {len(dts)} dates → {_merge_windows(dts, args.buffer_days)}")
        db.close()
        return 0

    token = token_store.get_token(db) or settings.kite_access_token
    provider = KiteConnectProvider(api_key=settings.kite_api_key, access_token=token)

    inserted = 0
    failed = 0
    for i, ((stock_id, symbol), dts) in enumerate(symbols, 1):
        windows = _merge_windows(dts, args.buffer_days)
        for start, end in windows:
            try:
                bars = provider.fetch_intraday_since(symbol, start, end, interval=args.interval)
            except Exception as exc:  # noqa: BLE001 — keep going on a per-symbol failure
                failed += 1
                _log(f"  ! {symbol} {start}..{end} fetch failed: {exc}")
                continue
            if not bars:
                continue
            now = datetime.now(UTC)
            payload = [
                {
                    "stock_id": stock_id,
                    "ts": b["ts"],
                    "interval": args.interval,
                    "open": b["open"],
                    "high": b["high"],
                    "low": b["low"],
                    "close": b["close"],
                    "volume": b["volume"],
                    "source": SOURCE,
                    "ingested_at": now,
                }
                for b in bars
            ]
            stmt = pg_insert(MarketDataIntraday).on_conflict_do_nothing(
                constraint="uq_md_intraday_stock_ts_interval_source"
            )
            db.execute(stmt, payload)
            db.commit()
            inserted += len(payload)
        if i % 25 == 0:
            _log(f"  {i}/{len(symbols)} symbols  rows≈{inserted}  failed_windows={failed}")

    _log(f"DONE  symbols={len(symbols)}  rows≈{inserted}  failed_windows={failed}")
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
