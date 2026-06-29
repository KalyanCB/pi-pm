"""Public, server-rendered backtest/replay progress page (auto-refresh, mobile-friendly).

Exposed without auth so it can be opened from a phone at /api/v1/backtest/replay-status.
Reads live replay state straight from the DB — no dependency on the running job.
"""
from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db

router = APIRouter()

_INITIAL_CAPITAL = 1_000_000.0  # ₹10L


@router.get("/replay-status", response_class=HTMLResponse)
def replay_status(db: Session = Depends(get_db)) -> HTMLResponse:
    # ranking_runs has a row per (strategy, day) and runs every day incl. the
    # warm-up phase, so distinct as_of_date tracks progress across both phases.
    prog = db.execute(
        text(
            "SELECT COUNT(DISTINCT as_of_date) AS n, MAX(as_of_date) AS d, "
            "MIN(as_of_date) AS s FROM ranking_runs"
        )
    ).fetchone()
    processed = prog.n or 0
    cur_date = prog.d
    # Derive the denominator's start from the numerator's own range so the two can
    # never drift (the warm-up start moved 2020→2018 and a hardcoded 2020-01-01
    # here under-counted the total, inflating % and showing a wrong day count).
    start_date = prog.s or date(2018, 1, 1)

    total = (
        db.execute(
            text(
                "SELECT COUNT(*) FROM (SELECT DISTINCT m.date FROM market_data m "
                "JOIN stocks s ON s.id = m.stock_id "
                "WHERE s.symbol = '^NSEI' AND m.source = 'kite' "
                "AND m.date >= :start) x"
            ),
            {"start": start_date},
        ).scalar()
        or 0
    )
    pct = round(processed / total * 100, 1) if total else 0.0

    nav = db.execute(
        text(
            "SELECT as_of_date, total_equity, open_positions, regime_label "
            "FROM portfolio_nav_history ORDER BY as_of_date DESC LIMIT 1"
        )
    ).fetchone()
    trades = db.execute(text("SELECT COUNT(*) FROM paper_trades")).scalar() or 0
    rankings = db.execute(text("SELECT COUNT(*) FROM ranking_results")).scalar() or 0

    # Starting capital — read the ACTUAL seeded amount, not a hardcoded constant.
    # (The config can be ₹10L or ₹1cr; a fixed divisor showed bogus 900%+ returns.)
    initial_capital = float(
        db.execute(text(
            "SELECT amount FROM portfolio_cash_ledger WHERE entry_type='INITIAL_CAPITAL' "
            "ORDER BY as_of_date LIMIT 1"
        )).scalar()
        or db.execute(text(
            "SELECT total_equity FROM portfolio_configs WHERE is_active LIMIT 1"
        )).scalar()
        or _INITIAL_CAPITAL
    )

    # PHASED replay: PHASE 1 ranks ALL days in parallel (no trades), then PHASE 2 trades
    # sequentially. So track two progress axes: RANKING (above) and TRADING (paper days,
    # below). The paper window starts 2021-01-01; a paper day is "done" once it has a NAV
    # snapshot. Strategies-per-day is detected from the data.
    n_strat = db.execute(text(
        "SELECT COALESCE(MAX(c), 1) FROM (SELECT COUNT(DISTINCT strategy_name) c "
        "FROM ranking_runs GROUP BY as_of_date) x"
    )).scalar() or 1
    paper_start = date(2021, 1, 1)
    paper_total = db.execute(text(
        "SELECT COUNT(*) FROM (SELECT DISTINCT m.date FROM market_data m "
        "JOIN stocks s ON s.id = m.stock_id WHERE s.symbol = '^NSEI' "
        "AND m.source = 'kite' AND m.date >= :ps) x"
    ), {"ps": paper_start}).scalar() or 0
    _pp = db.execute(text(
        "SELECT COUNT(DISTINCT as_of_date) AS n, MAX(as_of_date) AS d "
        "FROM portfolio_nav_history"
    )).fetchone()
    paper_done = (_pp.n if _pp else 0) or 0
    paper_cur = _pp.d if _pp else None
    paper_pct = round(paper_done / paper_total * 100, 1) if paper_total else 0.0
    active_strategy = db.execute(text(
        "SELECT strategy_name FROM recommendation_runs "
        "ORDER BY as_of_date DESC, created_at DESC LIMIT 1"
    )).scalar() or "—"

    # Run timing — started / elapsed (wall-clock of processing) / avg per trade-day.
    _tm = db.execute(text(
        "SELECT min(started_at) AS s, max(completed_at) AS e FROM daily_batch_runs"
    )).fetchone()
    if _tm and _tm.s and _tm.e:
        _el = (_tm.e - _tm.s).total_seconds()
        started_str = _tm.s.strftime("%Y-%m-%d %H:%M UTC")
        elapsed_str = (f"{int(_el // 3600)}h {int((_el % 3600) // 60)}m"
                       if _el >= 3600 else f"{_el / 60:.1f} min")
        per_day_str = f"{_el / max(processed, 1):.1f}s"
    else:
        started_str = elapsed_str = per_day_str = "—"

    if nav is not None:
        equity = float(nav.total_equity)
        ret = (equity / initial_capital - 1) * 100
        nav_date = nav.as_of_date
        positions = nav.open_positions
        regime = nav.regime_label or "—"
    else:
        equity, ret, nav_date, positions, regime = initial_capital, 0.0, None, 0, "—"

    # Phase detection from state: PHASE 1 ranks all days before any trade exists.
    ranking_done = processed >= total and total > 0
    if processed == 0:
        phase, headline_pct = "Not started", 0.0
    elif paper_done == 0 and not ranking_done:
        phase, headline_pct = "PHASE 1 &mdash; Ranking all days (parallel)", pct
    elif paper_done == 0:
        phase, headline_pct = "PHASE 1 done &middot; PHASE 2 (trading) starting", pct
    elif paper_done < paper_total:
        phase, headline_pct = "PHASE 2 &mdash; Trading (sequential)", paper_pct
    else:
        phase, headline_pct = "Complete", 100.0

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    ret_cls = "pos" if ret >= 0 else "neg"

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="30">
<title>Pi-PM Replay &middot; {active_strategy}</title>
<style>
 body{{font-family:-apple-system,system-ui,Segoe UI,Roboto,sans-serif;margin:0;padding:16px;
   background:#0b1020;color:#e6e9f0;-webkit-text-size-adjust:100%}}
 .card{{background:#161c2e;border-radius:14px;padding:18px;margin:0 0 14px;box-shadow:0 1px 4px rgba(0,0,0,.4)}}
 h1{{font-size:19px;margin:0 0 2px}} .sub{{color:#8a93a6;font-size:12.5px;line-height:1.5}}
 .big{{font-size:40px;font-weight:700;margin:8px 0 4px;letter-spacing:-1px}}
 .bar{{height:16px;background:#23304d;border-radius:9px;overflow:hidden;margin:10px 0 6px}}
 .fill{{height:100%;background:linear-gradient(90deg,#3b82f6,#22c55e);transition:width .4s}}
 .grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px 10px}}
 .k{{color:#8a93a6;font-size:11.5px;text-transform:uppercase;letter-spacing:.4px}}
 .v{{font-size:20px;font-weight:650;margin-top:2px}}
 .pos{{color:#22c55e}} .neg{{color:#ef4444}}
</style></head><body>
<div class="card">
 <h1>Pi-PM &mdash; Replay (fast)</h1>
 <div class="sub">{phase}<br>updated {now} &middot; auto-refresh 30s</div>
 <div class="big">{headline_pct}%</div>
 <div class="bar"><div class="fill" style="width:{pct}%"></div></div>
 <div class="sub">PHASE 1 &middot; RANKING ({n_strat} strat): {processed:,} / {total:,} days
   &middot; ranked to <b>{cur_date or '—'}</b></div>
 <div class="bar" style="background:#2a2433"><div class="fill" style="width:{paper_pct}%;background:linear-gradient(90deg,#a855f7,#f59e0b)"></div></div>
 <div class="sub">PHASE 2 &middot; TRADING: {paper_done:,} / {paper_total:,} paper days
   &middot; traded to <b>{paper_cur or '—'}</b> &middot; active: <b>{active_strategy}</b></div>
 <div class="sub" style="margin-top:8px">started <b>{started_str}</b> &middot; elapsed <b>{elapsed_str}</b>
   &middot; ~<b>{per_day_str}</b>/day</div>
</div>
<div class="card"><div class="grid">
 <div><div class="k">NAV ({nav_date or '—'})</div><div class="v">&#8377;{equity:,.0f}</div></div>
 <div><div class="k">Return</div><div class="v {ret_cls}">{ret:+.1f}%</div></div>
 <div><div class="k">Open positions</div><div class="v">{positions}</div></div>
 <div><div class="k">Regime</div><div class="v">{regime}</div></div>
 <div><div class="k">Paper trades</div><div class="v">{trades:,}</div></div>
 <div><div class="k">Ranking rows</div><div class="v">{rankings:,}</div></div>
</div></div>
<div class="sub" style="text-align:center">&#8377;{initial_capital:,.0f} start &middot; foreground=active-only (identical trades) &middot; background=research async</div>
</body></html>"""
    return HTMLResponse(content=html)
