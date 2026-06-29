"""Public, server-rendered backtest/replay progress page (auto-refresh, mobile-friendly).

Exposed without auth so it can be opened from a phone at /api/v1/backtest/replay-status.
Reads live state straight from the DB — no dependency on the running job.

Shows the 3-STAGE pipeline (① RANKING → ② RECOMMENDATIONS → ③ PAPER), the live NAV/return
+ portfolio metrics, an EXIT-QUALITY table (post-exit 90d "ran after" = is the trail
clipping runners?), and recent fills.
"""
from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db

router = APIRouter()

_INITIAL_CAPITAL = 1_000_000.0
_PAPER_START = date(2021, 1, 1)


def _scalar(db: Session, sql: str, **p):
    return db.execute(text(sql), p).scalar()


def _fmt_dur(seconds: float | None) -> str:
    if not seconds or seconds <= 0:
        return "—"
    if seconds >= 3600:
        return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"
    return f"{seconds / 60:.1f} min"


@router.get("/replay-status", response_class=HTMLResponse)
def replay_status(db: Session = Depends(get_db)) -> HTMLResponse:
    # ── Paper (stage 3) progress ──────────────────────────────────────────────────
    paper_total = _scalar(db,
        "SELECT COUNT(*) FROM (SELECT DISTINCT m.date FROM market_data m "
        "JOIN stocks s ON s.id = m.stock_id WHERE s.symbol = '^NSEI' "
        "AND m.source = 'kite' AND m.date >= :ps) x", ps=_PAPER_START) or 0
    _pp = db.execute(text(
        "SELECT COUNT(DISTINCT as_of_date) n, MIN(as_of_date) s, MAX(as_of_date) d "
        "FROM portfolio_nav_history")).fetchone()
    paper_done = (_pp.n if _pp else 0) or 0
    paper_first = _pp.s if _pp else None
    paper_cur = _pp.d if _pp else None
    paper_pct = round(paper_done / paper_total * 100, 1) if paper_total else 0.0

    # ── Ranking (stage 1) + recommendations (stage 2) ─────────────────────────────
    rank = db.execute(text(
        "SELECT COUNT(*) n, MAX(as_of_date) d FROM ranking_runs")).fetchone()
    rank_done = (rank.n if rank else 0) or 0
    ranked_to = rank.d if rank else None
    rec = db.execute(text(
        "SELECT COUNT(*) n, MAX(as_of_date) d FROM recommendation_runs")).fetchone()
    rec_done = (rec.n if rec else 0) or 0
    rec_to = rec.d if rec else None
    n_strat = _scalar(db,
        "SELECT COALESCE(MAX(c),5) FROM (SELECT COUNT(DISTINCT strategy_name) c "
        "FROM ranking_runs GROUP BY as_of_date) x") or 5
    rank_start = _scalar(db, "SELECT MIN(as_of_date) FROM ranking_runs") or _PAPER_START
    rank_total_days = _scalar(db,
        "SELECT COUNT(*) FROM (SELECT DISTINCT m.date FROM market_data m "
        "JOIN stocks s ON s.id = m.stock_id WHERE s.symbol = '^NSEI' AND m.source = 'kite' "
        "AND m.date >= :s) x", s=rank_start) or 0
    rank_target = rank_total_days * n_strat

    def _p(d, t):
        return round(min(d / t * 100, 100.0), 1) if t else 0.0
    rank_pct = _p(rank_done, rank_target)
    rec_pct = _p(rec_done, rank_target)

    # Active stage (sequential fill: rank→rec→paper).
    paper_full = paper_total > 0 and paper_done >= paper_total
    if rank_done == 0:
        stage, headline = "Idle &mdash; not started", 0.0
    elif paper_full:
        stage, headline = "Complete", 100.0
    elif paper_done > 0:
        stage, headline = "STAGE 3/3 &middot; Paper trade", paper_pct
    elif rec_done > 0:
        stage, headline = "STAGE 2/3 &middot; Recommendations", rec_pct
    else:
        stage, headline = "STAGE 1/3 &middot; Ranking", rank_pct

    # ── Capital ───────────────────────────────────────────────────────────────────
    initial_capital = float(
        _scalar(db, "SELECT amount FROM portfolio_cash_ledger "
                "WHERE entry_type='INITIAL_CAPITAL' ORDER BY as_of_date LIMIT 1")
        or _scalar(db, "SELECT total_equity FROM portfolio_configs WHERE is_active LIMIT 1")
        or _INITIAL_CAPITAL)

    # ── Latest NAV + metrics ──────────────────────────────────────────────────────
    nav = db.execute(text(
        "SELECT as_of_date, total_equity, cash_balance, market_value, open_positions, "
        "regime_label, benchmark_return_pct FROM portfolio_nav_history "
        "ORDER BY as_of_date DESC LIMIT 1")).fetchone()
    if nav is not None:
        equity = float(nav.total_equity)
        ret = (equity / initial_capital - 1) * 100
        nav_date = nav.as_of_date
        positions = nav.open_positions
        regime = nav.regime_label or "—"
        cash_pct = (float(nav.cash_balance) / equity * 100) if nav.cash_balance and equity else 0.0
    else:
        equity, ret, nav_date, positions, regime, cash_pct = initial_capital, 0.0, None, 0, "—", 100.0

    cagr = None
    if paper_first and nav_date and nav_date > paper_first and equity > 0:
        yrs = (nav_date - paper_first).days / 365.25
        if yrs > 0.05:
            cagr = ((equity / initial_capital) ** (1 / yrs) - 1) * 100
    max_dd = _scalar(db,
        "SELECT round(MIN((total_equity/peak - 1)*100)::numeric,1) FROM "
        "(SELECT total_equity, MAX(total_equity) OVER (ORDER BY as_of_date) peak "
        "FROM portfolio_nav_history) z")
    bench_cum = _scalar(db,
        "SELECT round((exp(sum(ln(1+benchmark_return_pct/100.0)))-1)*100,1) "
        "FROM portfolio_nav_history WHERE benchmark_return_pct IS NOT NULL "
        "AND benchmark_return_pct > -100")
    alpha = round(ret - float(bench_cum), 1) if bench_cum is not None else None

    _ps = db.execute(text(
        "SELECT COUNT(*) FILTER (WHERE exit_date IS NOT NULL) closed, "
        "COUNT(*) FILTER (WHERE exit_date IS NOT NULL AND exit_price > entry_price) wins "
        "FROM portfolio_positions")).fetchone()
    closed = (_ps.closed if _ps else 0) or 0
    wins = (_ps.wins if _ps else 0) or 0
    win_rate = round(wins / closed * 100, 0) if closed else None
    trades = _scalar(db, "SELECT COUNT(*) FROM paper_trades") or 0

    recent = db.execute(text(
        "SELECT pt.side, s.symbol, pt.fill_price, pt.filled_at "
        "FROM paper_trades pt JOIN stocks s ON s.id = pt.stock_id "
        "WHERE pt.filled_at IS NOT NULL ORDER BY pt.filled_at DESC LIMIT 6")).fetchall()

    # ── Exit quality by reason — is the trail clipping runners? ────────────────────
    exitq = db.execute(text("""
        WITH closed AS (
          SELECT p.stock_id, p.entry_price, p.exit_price, p.exit_date,
                 replace(p.exit_reason,'EXIT_','') reason,
                 (p.exit_price/NULLIF(p.entry_price,0)-1)*100 pnl,
                 (p.exit_date - p.entry_date) held
          FROM portfolio_positions p
          WHERE p.exit_date IS NOT NULL AND p.exit_reason IS NOT NULL),
        enr AS (
          SELECT c.*, (SELECT MAX(md.high) FROM market_data md
                       WHERE md.stock_id=c.stock_id AND md.source='kite'
                         AND md.date > c.exit_date AND md.date <= c.exit_date + 90) mh
          FROM closed c)
        SELECT reason, COUNT(*) n,
               round(AVG(pnl)::numeric,1) avg_pnl,
               round(AVG(held)::numeric,0) avg_held,
               round(AVG((mh/NULLIF(exit_price,0)-1)*100)::numeric,1) ran_after,
               round(100.0*COUNT(*) FILTER (WHERE mh/NULLIF(exit_price,0)-1 > 0.10)
                     /NULLIF(COUNT(*),0),0) pct_ran
        FROM enr GROUP BY reason ORDER BY n DESC
    """)).fetchall()

    _tm = db.execute(text(
        "SELECT MIN(started_at) s, MAX(completed_at) e FROM daily_batch_runs")).fetchone()
    elapsed = (_tm.e - _tm.s).total_seconds() if _tm and _tm.s and _tm.e else None
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    ret_cls = "pos" if ret >= 0 else "neg"

    def metric(k, v, cls=""):
        return f'<div><div class="k">{k}</div><div class="v {cls}">{v}</div></div>'

    cagr_s = f"{cagr:+.1f}%" if cagr is not None else "—"
    metrics = "".join([
        metric(f"NAV ({nav_date or '—'})", f"&#8377;{equity:,.0f}"),
        metric("Return", f"{ret:+.1f}%", ret_cls),
        metric("CAGR", cagr_s, "pos" if (cagr or 0) >= 0 else "neg"),
        metric("Max drawdown", f"{max_dd}%" if max_dd is not None else "—", "neg"),
        metric("Benchmark", f"{bench_cum:+.1f}%" if bench_cum is not None else "—"),
        metric("Alpha", f"{alpha:+.1f}%" if alpha is not None else "—",
               "pos" if (alpha or 0) >= 0 else "neg"),
        metric("Open positions", f"{positions}"),
        metric("Cash", f"{cash_pct:.0f}%"),
        metric("Closed / win%", f"{closed:,} / {f'{win_rate:.0f}%' if win_rate is not None else '—'}"),
        metric("Regime", regime),
    ])
    rows = "".join(
        f'<tr><td class="{"pos" if r.side=="BUY" else "neg"}">{r.side}</td>'
        f'<td>{r.symbol}</td><td style="text-align:right">&#8377;{float(r.fill_price):,.1f}</td>'
        f'<td style="text-align:right;color:#8a93a6">{r.filled_at.strftime("%Y-%m-%d")}</td></tr>'
        for r in recent) or '<tr><td colspan="4" style="color:#8a93a6">no fills yet</td></tr>'

    def _exit_row(r):
        ran = float(r.ran_after) if r.ran_after is not None else 0.0
        warn = ' class="neg"' if ran > 10 else ''
        pnl = float(r.avg_pnl) if r.avg_pnl is not None else 0.0
        pct = f"{int(r.pct_ran)}%" if r.pct_ran is not None else "—"
        return (f'<tr><td>{r.reason}</td><td style="text-align:right">{r.n}</td>'
                f'<td style="text-align:right" class="{"pos" if pnl>=0 else "neg"}">{pnl:+.1f}%</td>'
                f'<td style="text-align:right;color:#8a93a6">{int(r.avg_held or 0)}d</td>'
                f'<td style="text-align:right"{warn}>+{ran:.1f}%</td>'
                f'<td style="text-align:right;color:#8a93a6">{pct}</td></tr>')
    exit_rows = "".join(_exit_row(r) for r in exitq) or \
        '<tr><td colspan="6" style="color:#8a93a6">no closed trades yet</td></tr>'

    def _bar(pct, c1, c2, bg="#23304d"):
        return (f'<div class="bar" style="background:{bg}"><div class="fill" '
                f'style="width:{pct}%;background:linear-gradient(90deg,{c1},{c2})"></div></div>')

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="20">
<title>Pi-PM Pipeline &middot; {stage}</title>
<style>
 body{{font-family:-apple-system,system-ui,Segoe UI,Roboto,sans-serif;margin:0 auto;padding:16px;
   background:#0b1020;color:#e6e9f0;-webkit-text-size-adjust:100%;max-width:680px}}
 .card{{background:#161c2e;border-radius:14px;padding:18px;margin:0 0 14px;box-shadow:0 1px 4px rgba(0,0,0,.4)}}
 h1{{font-size:19px;margin:0 0 2px}} .sub{{color:#8a93a6;font-size:12.5px;line-height:1.5}}
 .big{{font-size:40px;font-weight:700;margin:8px 0 2px;letter-spacing:-1px}}
 .bar{{height:14px;border-radius:9px;overflow:hidden;margin:5px 0 3px}} .fill{{height:100%;transition:width .4s}}
 .stg{{font-size:11.5px;color:#aab3c5;margin:9px 0 1px;font-weight:600}}
 .grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px 10px}}
 @media(max-width:460px){{.grid{{grid-template-columns:1fr 1fr}}}}
 .k{{color:#8a93a6;font-size:11px;text-transform:uppercase;letter-spacing:.4px}}
 .v{{font-size:19px;font-weight:650;margin-top:2px}} .pos{{color:#22c55e}} .neg{{color:#ef4444}}
 table{{width:100%;border-collapse:collapse;font-size:13px}}
 td{{padding:5px 4px;border-bottom:1px solid #23304d}}
 .lbl{{font-size:11px;color:#8a93a6;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px}}
</style></head><body>
<div class="card">
 <h1>Pi-PM &mdash; Replay pipeline</h1>
 <div class="sub">{stage}<br>updated {now} &middot; auto-refresh 20s</div>
 <div class="big">{headline}%</div>
 <div class="stg">&#9312; RANKING &middot; {rank_done:,} / {rank_target:,} runs &middot; to <b>{ranked_to or '—'}</b></div>
 {_bar(rank_pct, '#3b82f6', '#22c55e')}
 <div class="stg">&#9313; RECOMMENDATIONS &middot; {rec_done:,} / {rank_target:,} runs &middot; to <b>{rec_to or '—'}</b></div>
 {_bar(rec_pct, '#8b5cf6', '#22c55e', '#241f3a')}
 <div class="stg">&#9314; PAPER TRADE &middot; {paper_done:,} / {paper_total:,} days &middot; to <b>{paper_cur or '—'}</b></div>
 {_bar(paper_pct, '#a855f7', '#f59e0b', '#2a2433')}
 <div class="sub" style="margin-top:6px">elapsed {_fmt_dur(elapsed)} &middot; {n_strat} sleeves</div>
</div>
<div class="card"><div class="grid">{metrics}</div></div>
<div class="card">
 <div class="lbl">Exit quality &middot; "ran after" = avg move in 90d AFTER exit (red = clipping runners)</div>
 <table>
  <tr style="color:#8a93a6;font-size:11px"><td>reason</td><td style="text-align:right">n</td>
   <td style="text-align:right">avg P&amp;L</td><td style="text-align:right">hold</td>
   <td style="text-align:right">ran after</td><td style="text-align:right">%ran&gt;10</td></tr>
  {exit_rows}
 </table>
</div>
<div class="card">
 <div class="lbl">Recent fills</div>
 <table>{rows}</table>
</div>
<div class="sub" style="text-align:center">&#8377;{initial_capital:,.0f} start &middot; bulk_rank &rarr; bulk_rec &rarr; paper &middot; 18 slots</div>
</body></html>"""
    return HTMLResponse(content=html)
