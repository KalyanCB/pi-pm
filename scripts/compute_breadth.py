"""Precompute the market-breadth regime into `market_breadth` (point-in-time).

The breakout_v3 suite selects its sleeve by this table:
  breadth     = fraction of the LIQUID universe (50d median ₹-vol >= floor) trading
                ABOVE its own 200-day SMA on each day  (classic participation breadth).
  breadth20   = 20d SMA of breadth (de-noised).
  thr         = trailing-252d MEDIAN of breadth, LAGGED one day (no look-ahead).
  broad_flag  = breadth20 > thr   (BROAD market). At cold start (thr NULL) -> BROAD.

BROAD  -> breakout_v3_broad (proximity+momentum+efficiency)
NARROW -> breakout_v3_def   (proximity+low_vol)

Deterministic, single pass over market_data (source=kite). Re-runnable (TRUNCATE+insert).

Usage:  uv run python scripts/compute_breadth.py [START_DATE=2019-01-01] [END_DATE=2026-06-30]
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from sqlalchemy import text

from app.db.session import get_session_factory

LIQ_FLOOR = float(os.getenv("BREADTH_LIQ_FLOOR", "1e7"))   # ₹1cr median 50d traded value
START = os.getenv("REPLAY_START_DATE", os.getenv("START_DATE", "2019-01-01"))
END = os.getenv("REPLAY_END_DATE", os.getenv("END_DATE", "2026-12-31"))

DDL = """
CREATE TABLE IF NOT EXISTS market_breadth (
    date        date PRIMARY KEY,
    breadth     double precision,
    breadth20   double precision,
    thr         double precision,
    broad_flag  boolean NOT NULL
);
"""


def main() -> int:
    sf = get_session_factory()
    db = sf()
    try:
        eng = db.get_bind()
        print(f"reading market_data {START}..{END} (source=kite) ...", flush=True)
        df = pd.read_sql(
            text(
                "SELECT stock_id, date, close, volume FROM market_data "
                "WHERE source='kite' AND date >= :s AND date <= :e AND close > 0 "
                "ORDER BY stock_id, date"
            ),
            eng, params={"s": START, "e": END}, parse_dates=["date"],
        )
        print(f"  {len(df):,} rows / {df.stock_id.nunique()} stocks", flush=True)

        g = df.groupby("stock_id", group_keys=False)
        df["sma200"] = g["close"].apply(lambda s: s.rolling(200, min_periods=120).mean())
        df["rupee"] = df["close"] * df["volume"].fillna(0)
        df["liq50"] = g["rupee"].apply(lambda s: s.rolling(50, min_periods=30).median())
        df["above200"] = (df["close"] > df["sma200"]).astype(float)

        liq = df[(df["liq50"] >= LIQ_FLOOR) & df["sma200"].notna()]
        breadth = liq.groupby("date")["above200"].mean().rename("breadth").sort_index()
        b = breadth.to_frame()
        b["breadth20"] = b["breadth"].rolling(20, min_periods=10).mean()
        b["thr"] = b["breadth"].rolling(252, min_periods=120).median().shift(1)
        # BROAD when de-noised breadth is above its own trailing median; cold start -> BROAD
        b["broad_flag"] = (b["breadth20"] > b["thr"]) | b["thr"].isna()

        db.execute(text(DDL))
        db.execute(text("TRUNCATE market_breadth"))
        rows = [
            {
                "date": idx.date(),
                "breadth": float(r.breadth) if pd.notna(r.breadth) else None,
                "breadth20": float(r.breadth20) if pd.notna(r.breadth20) else None,
                "thr": float(r.thr) if pd.notna(r.thr) else None,
                "broad_flag": bool(r.broad_flag),
            }
            for idx, r in b.iterrows()
        ]
        db.execute(
            text(
                "INSERT INTO market_breadth (date, breadth, breadth20, thr, broad_flag) "
                "VALUES (:date, :breadth, :breadth20, :thr, :broad_flag)"
            ),
            rows,
        )
        db.commit()

        # summary by year
        b["yr"] = b.index.year
        print(f"\nwrote {len(rows)} breadth rows. Regime by year (% BROAD days):", flush=True)
        for y, grp in b.groupby("yr"):
            if y < 2021:
                continue
            print(f"  {y}: mean breadth {grp['breadth'].mean():.0%}  BROAD {grp['broad_flag'].mean():.0%}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
