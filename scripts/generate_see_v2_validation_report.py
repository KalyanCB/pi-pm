#!/usr/bin/env python3
"""Generate SEE v2 validation report for breakout and momentum top-20 runs."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.db.repositories.market_data_repository import MarketDataRepository
from app.db.repositories.run_lineage_repository import RunLineageRepository
from app.db.repositories.stock_repository import StockRepository
from app.db.repositories.stock_setup_research_repository import StockSetupResearchRepository
from app.db.session import get_session_factory
from app.market_data.cache import MarketDataCache
from app.ranking.loader import MarketDataLoader
from app.services.stock_setup_research_service import StockSetupResearchService

DEFAULT_BREAKOUT_RUN = "b8e993e4-a049-4f3a-bcd0-29574a0f7e47"
DEFAULT_MOMENTUM_RUN = "097bddfe-1cb3-4073-b00b-bfd056040115"
OUTPUT_PATH = Path("docs/see-v2-validation-report.md")


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{100 * value:.1f}%"


def _run_section(
    svc: StockSetupResearchService, repo: StockSetupResearchRepository, run_id: str, label: str
) -> str:
    from uuid import UUID

    rid = UUID(run_id)
    summary = svc.run_for_ranking_run(rid, limit=20)
    rows = repo.list_for_ranking_run(rid)
    payloads = [svc.to_payload(r) for r in rows]
    scored = sorted(
        payloads,
        key=lambda p: p.get("setup_evidence_score") or 0,
        reverse=True,
    )

    lines = [
        f"## {label}",
        "",
        f"- Run ID: `{run_id}`",
        f"- Completed: {summary['completed']}/{summary['candidates']}",
        "",
        "### Evidence score ranking (top 20)",
        "",
        "| Rank | Symbol | Score | Qualifying | Total scored | ALL win20 | ALL avg20 |",
        "|------|--------|-------|------------|--------------|-----------|-----------|",
    ]
    for idx, p in enumerate(scored, 1):
        stats = {m["regime_label"]: m for m in p.get("regime_statistics", [])}
        all_m = stats.get("ALL_REGIMES", {})
        lines.append(
            f"| {idx} | {p['symbol']} | {p.get('setup_evidence_score', '—')} | "
            f"{p.get('qualifying_matches', 0)} | {p.get('total_matches', 0)} | "
            f"{_fmt_pct(all_m.get('win_rate_20d'))} | {_fmt_pct(all_m.get('average_return_20d'))} |"
        )

    match_counts = [p.get("qualifying_matches", 0) for p in payloads]
    lines.extend(
        [
            "",
            f"- Match count range: {min(match_counts) if match_counts else 0} – "
            f"{max(match_counts) if match_counts else 0}",
            "",
        ]
    )

    if scored:
        lines.extend(["### Strongest setup evidence", ""])
        for p in scored[:5]:
            lines.append(f"- **{p['symbol']}** — score {p.get('setup_evidence_score')}")
        lines.extend(["", "### Weakest setup evidence", ""])
        for p in scored[-5:]:
            lines.append(f"- **{p['symbol']}** — score {p.get('setup_evidence_score')}")

    return "\n".join(lines)


def _highlight_symbols(
    svc: StockSetupResearchService, repo: StockSetupResearchRepository, run_id: str
) -> str:
    from uuid import UUID

    rid = UUID(run_id)
    lines = ["", "### HFCL vs THERMAX vs WOCKPHARMA (breakout)", ""]
    for sym in ("HFCL.NS", "THERMAX.NS", "WOCKPHARMA.NS"):
        row = next((r for r in repo.list_for_ranking_run(rid) if r.symbol == sym), None)
        if row is None:
            lines.append(f"- {sym}: not in run")
            continue
        p = svc.to_payload(row)
        all_m = next(
            (m for m in p["regime_statistics"] if m["regime_label"] == "ALL_REGIMES"),
            {},
        )
        bear = next(
            (m for m in p["regime_statistics"] if m["regime_label"] == "BEAR_LOW_VOL"),
            {},
        )
        lines.append(
            f"- **{sym}**: score={p.get('setup_evidence_score')} | "
            f"qualifying={p.get('qualifying_matches')} | "
            f"ALL n={all_m.get('sample_size')} win20={_fmt_pct(all_m.get('win_rate_20d'))} "
            f"avg20={_fmt_pct(all_m.get('average_return_20d'))} | "
            f"BEAR n={bear.get('sample_size')} win20={_fmt_pct(bear.get('win_rate_20d'))} "
            f"avg20={_fmt_pct(bear.get('average_return_20d'))}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--breakout-run", default=DEFAULT_BREAKOUT_RUN)
    parser.add_argument("--momentum-run", default=DEFAULT_MOMENTUM_RUN)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    Session = get_session_factory()
    with Session() as db:
        svc = StockSetupResearchService(
            db,
            research_repo=StockSetupResearchRepository(db),
            stock_repo=StockRepository(db),
            lineage_repo=RunLineageRepository(db),
            market_data_loader=MarketDataLoader(MarketDataCache(MarketDataRepository(db))),
        )
        repo = StockSetupResearchRepository(db)

        body = [
            "# SEE v2 Validation Report",
            "",
            "Generated by `scripts/generate_see_v2_validation_report.py`.",
            "",
            _run_section(svc, repo, args.breakout_run, "Breakout v1 (top 20)"),
            _highlight_symbols(svc, repo, args.breakout_run),
            _run_section(svc, repo, args.momentum_run, "Momentum v1 (top 20)"),
        ]
        args.output.write_text("\n".join(body) + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
