"""Public, server-rendered backtest/replay progress page (auto-refresh, mobile-friendly).

Exposed without auth so it can be opened from a phone at /api/v1/backtest/replay-status.
Reads live state straight from the DB — no dependency on the running job.

3-STAGE pipeline view: (1) RANKING (bulk_rank) → (2) RECOMMENDATIONS (bulk_rec) →
(3) PAPER TRADE (replay_fast). Each stage gets its own progress bar; the headline tracks
the active stage. NAV/return shown once the paper stage starts.
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
_PAPER_START = date(2021, 1, 1)


@router.get("/replay-status", response_class=HTMLResponse)
def replay_status(db: Session = Depends(get_db)) -> HTMLResponse:
    def _scalar(sql: str, **p):
        return db.execute(text(sql), p).scalar()

    # ── Targets (dynamic, from the benchmark's own trading calendar) ──────────
    rank_start = _scalar("SELECT min(as_of_date) FROM ranking_runs") or date(2018, 1, 1)
    n_strat = _scalar(
        "SELECT COALESCE(MAX(c),5) FROM (SELECT COUNT(DISTINCT strategy_name) c "
        "FROM ranking_runs GROUP BY as_of_date) x"
    ) or 5
    total_days = _scalar(
        "SELECT COUNT(*) FROM (SELECT DISTINCT m.date FROM market_data m "
        "JOIN stocks s ON s.id=m.stock_id WHERE s.symbol='^NSEI' AND m.source='kite' "
        "AND m.date >= :s) x", s=rank_start
    ) or 0
    rank_target = total_days * n_strat
    paper_total = _scalar(
        "SELECT COUNT(*) FROM (SELECT DISTINCT m.date FROM market_data m "
        "JOIN stocks s ON s.id=m.stock_id WHERE s.symbol='^NSEI' AND m.source='kite' "
        "AND m.date >= :ps) x", ps=_PAPER_START
    ) or 0

    # ── Stage progress ───────────────────────────────────────────────────────
    rank_done = _scalar("SELECT count(*) FROM ranking_runs") or 0
    rank_max = _scalar("SELECT max(as_of_date) FROM ranking_runs")
    rec_done = _scalar("SELECT count(*) FROM recommendation_runs") or 0
    rec_max = _scalar("SELECT max(as_of_date) FROM recommendation_runs")
    paper_done = _scalar("SELECT count(DISTINCT as_of_date) FROM portfolio_nav_history") or 0
    paper_max = _scalar("SELECT max(as_of_date) FROM portfolio_nav_history")
    rank_results = _scalar("SELECT count(*) FROM ranking_results") or 0
    rec_results = _scalar("SELECT count(*) FROM recommendation_results") or 0
    trades = _scalar("SELECT count(*) FROM paper_trades") or 0

    def _pct(done, target):
        return round(min(done / target * 100, 100.0), 1) if target else 0.0

    rank_pct = _pct(rank_done, rank_target)
    rec_pct = _pct(rec_done, rank_target)
    paper_pct = _pct(paper_done, paper_total)

    # ── Active stage detection ───────────────────────────────────────────────
    rank_full = rank_done >= rank_target and rank_target > 0
    rec_full = rec_done >= rank_target and rank_target > 0
    paper_full = paper_done >= paper_total and paper_total > 0
    if rank_done == 0:
        stage, headline = "Idle &mdash; not started", 0.0
    elif not rank_full:
        stage, headline = "STAGE 1/3 &middot; Ranking (bulk_rank)", rank_pct
    elif not rec_full:
        stage, headline = "STAGE 2/3 &middot; Recommendations (bulk_rec)", rec_pct
    elif not paper_full:
        stage, headline = "STAGE 3/3 &middot; Paper trade (replay)", paper_pct
    else:
        stage, headline = "Complete", 100.0

    # ── NAV / return ─────────────────────────────────────────────────────────
    initial_capital = float(
        _scalar("SELECT amount FROM portfolio_cash_ledger WHERE entry_type='INITIAL_CAPITAL' "
                "ORDER BY as_of_date LIMIT 1")
        or _INITIAL_CAPITAL
    )
    nav = db.execute(text(
        "SELECT as_of_date, total_equity, open_positions, regime_label "
        "FROM portfolio_nav_history ORDER BY as_of_date DESC LIMIT 1"
    )).fetchone()
    if nav is not None:
        equity = float(nav.total_equity)
        ret = (equity / initial_capital - 1) * 100
        nav_date, positions, regime = nav.as_of_date, nav.open_positions, (nav.regime_label or "—")
    else:
        equity, ret, nav_date, positions, regime = initial_capital, 0.0, None, 0, "—"
    ret_cls = "pos" if ret >= 0 else "neg"
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    def _bar(pct, c1, c2, bg="#23304d"):
        return (f'<div class="bar" style="background:{bg}"><div class="fill" '
                f'style="width:{pct}%;background:linear-gradient(90deg,{c1},{c2})"></div></div>')

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="20">
<title>Pi-PM Pipeline &middot; {stage}</title>
<style>
 body{{font-family:-apple-system,system-ui,Segoe UI,Roboto,sans-serif;margin:0;padding:16px;
   background:#0b1020;color:#e6e9f0;-webkit-text-size-adjust:100%}}
 .card{{background:#161c2e;border-radius:14px;padding:18px;margin:0 0 14px;box-shadow:0 1px 4px rgba(0,0,0,.4)}}
 h1{{font-size:19px;margin:0 0 2px}} .sub{{color:#8a93a6;font-size:12.5px;line-height:1.5}}
 .big{{font-size:40px;font-weight:700;margin:8px 0 2px;letter-spacing:-1px}}
 .bar{{height:15px;border-radius:9px;overflow:hidden;margin:6px 0 3px}}
 .fill{{height:100%;transition:width .4s}}
 .stg{{font-size:12px;color:#aab3c5;margin:10px 0 2px;font-weight:600}}
 .grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px 10px}}
 .k{{color:#8a93a6;font-size:11.5px;text-transform:uppercase;letter-spacing:.4px}}
 .v{{font-size:20px;font-weight:650;margin-top:2px}}
 .pos{{color:#22c55e}} .neg{{color:#ef4444}}
</style></head><body>
<div class="card">
 <h1>Pi-PM &mdash; Replay pipeline</h1>
 <div class="sub">{stage}<br>updated {now} &middot; auto-refresh 20s</div>
 <div class="big">{headline}%</div>

 <div class="stg">&#9312; RANKING &middot; {rank_done:,} / {rank_target:,} runs &middot; to <b>{rank_max or '—'}</b></div>
 {_bar(rank_pct, '#3b82f6', '#22c55e')}
 <div class="stg">&#9313; RECOMMENDATIONS &middot; {rec_done:,} / {rank_target:,} runs &middot; to <b>{rec_max or '—'}</b></div>
 {_bar(rec_pct, '#8b5cf6', '#22c55e', '#241f3a')}
 <div class="stg">&#9314; PAPER TRADE &middot; {paper_done:,} / {paper_total:,} days &middot; to <b>{paper_max or '—'}</b></div>
 {_bar(paper_pct, '#a855f7', '#f59e0b', '#2a2433')}
</div>
<div class="card"><div class="grid">
 <div><div class="k">NAV ({nav_date or '—'})</div><div class="v">&#8377;{equity:,.0f}</div></div>
 <div><div class="k">Return</div><div class="v {ret_cls}">{ret:+.1f}%</div></div>
 <div><div class="k">Open positions</div><div class="v">{positions}</div></div>
 <div><div class="k">Regime</div><div class="v">{regime}</div></div>
 <div><div class="k">Ranking rows</div><div class="v">{rank_results:,}</div></div>
 <div><div class="k">Rec rows</div><div class="v">{rec_results:,}</div></div>
 <div><div class="k">Paper trades</div><div class="v">{trades:,}</div></div>
 <div><div class="k">Strategies/day</div><div class="v">{n_strat}</div></div>
</div></div>
<div class="sub" style="text-align:center">&#8377;{initial_capital:,.0f} start &middot; bulk_rank &rarr; bulk_rec &rarr; paper (sequential) &middot; all exit fixes ON</div>
</body></html>"""
    return HTMLResponse(content=html)
