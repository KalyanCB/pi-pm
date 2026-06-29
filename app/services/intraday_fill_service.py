"""Realistic execution fills: next-session VWAP anchor + size-vs-ADV market impact.

This replaces the flat ``cost_slippage_bps`` with a *measured* fill:

  fill_price = next_session_vwap * (1 ± impact)
  impact_bps = impact_spread_bps/2 + impact_coeff_bps * sqrt(order_value / ADV)

A small order in a liquid name pays ~half-spread; a large order in a thin small-cap
pays a participation-scaled square-root impact — the real driver of true-net cost.

The math (``market_impact_bps``, ``vwap_from_bars``) is kept as pure functions so it is
unit-testable without a database; the service methods only fetch rows and delegate.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.market_data import MarketData
from app.models.market_data_intraday import MarketDataIntraday


@dataclass(frozen=True)
class FillQuote:
    fill_price: float
    ref_price: float       # the VWAP anchor before impact
    impact_bps: float      # directional market-impact applied
    participation: float   # order_value / ADV (0 when ADV unknown)
    fill_ts: datetime


def market_impact_bps(
    order_value: float | None,
    adv: float | None,
    spread_bps: float,
    coeff_bps: float,
) -> float:
    """Square-root market-impact in bps.

    half-spread is always paid; the impact term scales with sqrt(participation),
    where participation = order_value / ADV. When ADV is unknown/zero we assume a
    fully illiquid worst case (participation = 1).
    """
    half_spread = spread_bps / 2.0
    if not order_value or order_value <= 0:
        return half_spread
    if not adv or adv <= 0:
        participation = 1.0
    else:
        participation = order_value / adv
    return half_spread + coeff_bps * math.sqrt(participation)


def vwap_from_bars(
    bars: list[tuple[datetime, float, int | None]],
    window_minutes: int,
) -> tuple[float, datetime] | None:
    """Volume-weighted average price over the first ``window_minutes`` of a session.

    ``bars`` is ``(ts, close, volume)`` ordered by ts for a single session. Falls back
    to a simple price average when volume is missing/zero. Returns (vwap, first_ts).
    """
    if not bars:
        return None
    bars = sorted(bars, key=lambda b: b[0])
    first_ts = bars[0][0]
    cutoff = first_ts + timedelta(minutes=window_minutes)
    window = [b for b in bars if b[0] < cutoff] or [bars[0]]
    num = sum(c * (v or 0) for _, c, v in window)
    den = sum((v or 0) for _, _, v in window)
    if den > 0:
        return num / den, first_ts
    # no volume → simple average of closes
    return sum(c for _, c, _ in window) / len(window), first_ts


class IntradayFillService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings

    def resolve_fill(
        self,
        stock_id: UUID,
        decision_date: date,
        side: str,
        order_value: float | None = None,
    ) -> FillQuote | None:
        """Compute a realistic fill for a decision made on ``decision_date`` close.

        Returns None when intraday data for the next session is unavailable — the
        caller then falls back to the legacy next-open/close fill.
        """
        anchor = self._next_session_vwap(stock_id, decision_date)
        if anchor is None:
            return None
        vwap, fill_ts = anchor

        adv = self._adv(stock_id, decision_date)
        impact = market_impact_bps(
            order_value, adv, self.settings.impact_spread_bps, self.settings.impact_coeff_bps
        )
        direction = 1.0 if side == "BUY" else -1.0
        fill_price = vwap * (1.0 + direction * impact / 10_000.0)
        participation = (order_value / adv) if (order_value and adv and adv > 0) else 0.0
        return FillQuote(
            fill_price=round(fill_price, 4),
            ref_price=round(vwap, 4),
            impact_bps=round(impact, 4),
            participation=round(participation, 6),
            fill_ts=fill_ts,
        )

    # ── DB access (thin — pure math lives above) ────────────────────────────

    def _next_session_vwap(
        self, stock_id: UUID, after_date: date
    ) -> tuple[float, datetime] | None:
        after_dt = datetime.combine(after_date, time(23, 59, 59))
        first_ts = self.db.scalar(
            select(MarketDataIntraday.ts)
            .where(
                MarketDataIntraday.stock_id == stock_id,
                MarketDataIntraday.interval == self.settings.intraday_interval,
                MarketDataIntraday.ts > after_dt,
            )
            .order_by(MarketDataIntraday.ts)
            .limit(1)
        )
        if first_ts is None:
            return None
        session_day = first_ts.date()
        day_start = datetime.combine(session_day, time(0, 0, 0), tzinfo=first_ts.tzinfo)
        day_end = datetime.combine(session_day, time(23, 59, 59), tzinfo=first_ts.tzinfo)
        rows = self.db.execute(
            select(MarketDataIntraday.ts, MarketDataIntraday.close, MarketDataIntraday.volume)
            .where(
                MarketDataIntraday.stock_id == stock_id,
                MarketDataIntraday.interval == self.settings.intraday_interval,
                MarketDataIntraday.ts >= day_start,
                MarketDataIntraday.ts <= day_end,
            )
            .order_by(MarketDataIntraday.ts)
        ).all()
        bars = [(ts, float(close), int(vol) if vol is not None else None) for ts, close, vol in rows]
        return vwap_from_bars(bars, self.settings.vwap_window_minutes)

    def _adv(self, stock_id: UUID, as_of: date) -> float | None:
        """Trailing average daily traded value (close × volume) over the lookback."""
        rows = self.db.execute(
            select(MarketData.close, MarketData.volume)
            .where(MarketData.stock_id == stock_id, MarketData.date < as_of)
            .order_by(MarketData.date.desc())
            .limit(self.settings.adv_lookback_days)
        ).all()
        vals = [float(c) * float(v) for c, v in rows if c is not None and v]
        if not vals:
            return None
        return sum(vals) / len(vals)
