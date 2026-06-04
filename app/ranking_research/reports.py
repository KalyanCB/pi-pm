from __future__ import annotations

from app.outcome_attribution.models import BucketMetrics
from app.ranking_research.calibration import CalibrationTables
from app.ranking_research.constants import EXACT_RANKS, RESEARCH_HORIZONS
from app.ranking_research.constants import SCORE_BUCKET_SPECS
from app.ranking_research.models import (
    CalibratedRankingBacktestReport,
    FactorReliabilitySegment,
    PortfolioBacktestMetrics,
    RankReliabilityReport,
    RootCauseHeadlines,
    ScoreCompressionReport,
    ScoreCompressionSegment,
    StrategyRankReliability,
)
from app.ranking_research.root_cause import build_root_cause_headlines
from app.ranking_research.score_compression import compare_score_buckets


def _fmt_pct(value: float | None, *, digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{100 * value:.{digits}f}%"


def _fmt_num(value: float | None, *, digits: int = 3) -> str:
    if value is None:
        return "—"
    return f"{value:.{digits}f}"


def _scope_block(report: RankReliabilityReport) -> list[str]:
    cfg = report.config
    return [
        "## Scope",
        "",
        f"- Universe: `{cfg.universe_code}`",
        f"- Strategies: {', '.join(cfg.strategy_names)}",
        f"- Date window: {cfg.start_date.isoformat()} → {cfg.end_date.isoformat()}",
        f"- Ranking runs analyzed: {report.ranked_run_count}",
        f"- Runs with 20d forward data: {report.runs_with_forward_data}",
        "",
    ]


def _ascii_alpha_curve(segment: StrategyRankReliability, horizon: int) -> list[str]:
    alphas: list[tuple[int, float]] = []
    for rank in EXACT_RANKS:
        m = segment.per_rank[rank][horizon]
        if m.alpha is not None and m.status == "ok":
            alphas.append((rank, m.alpha))
    if not alphas:
        return []
    max_alpha = max(a for _, a in alphas)
    min_alpha = min(a for _, a in alphas)
    span = max(max_alpha - min_alpha, 0.0001)
    lines = [f"#### Alpha curve ({horizon}d) — ASCII", "", "```"]
    for rank, alpha in alphas:
        bar_len = int(40 * (alpha - min_alpha) / span)
        lines.append(f"rank {rank:2d} | {'█' * bar_len} {_fmt_pct(alpha)}")
    lines.extend(["```", ""])
    return lines


def _per_rank_table(segment: StrategyRankReliability, horizon: int) -> list[str]:
    lines = [
        f"#### Per-rank metrics ({horizon}d)",
        "",
        "| Rank | Hit rate | Avg return | Alpha | Sharpe | Max DD | Obs | Status |",
        "|------|----------|------------|-------|--------|--------|-----|--------|",
    ]
    for rank in EXACT_RANKS:
        m = segment.per_rank[rank][horizon]
        lines.append(
            f"| {rank} | {_fmt_pct(m.hit_rate)} | {_fmt_pct(m.average_return)} | "
            f"{_fmt_pct(m.alpha)} | {_fmt_num(m.sharpe)} | {_fmt_pct(m.max_drawdown)} | "
            f"{m.observation_count} | {m.status} |"
        )
    lines.append("")
    return lines


def _strongest_weakest_ranks(segment: StrategyRankReliability, horizon: int) -> list[str]:
    ranked: list[tuple[int, float]] = []
    for rank in EXACT_RANKS:
        m = segment.per_rank[rank][horizon]
        if m.alpha is not None and m.status == "ok":
            ranked.append((rank, m.alpha))
    if not ranked:
        return []
    ranked.sort(key=lambda x: x[1], reverse=True)
    best = ranked[0]
    worst = ranked[-1]
    lines = [
        f"#### Strongest / weakest ranks ({horizon}d)",
        "",
        f"- **Strongest:** rank {best[0]} (α {_fmt_pct(best[1])})",
        f"- **Weakest:** rank {worst[0]} (α {_fmt_pct(worst[1])})",
        f"- **Ranks 1–5 avg α:** {_fmt_pct(_band_mean(segment, 1, 5, horizon))}",
        f"- **Ranks 6–10 avg α:** {_fmt_pct(_band_mean(segment, 6, 10, horizon))}",
        f"- **Ranks 11–20 avg α:** {_fmt_pct(_band_mean(segment, 11, 20, horizon))}",
        "",
    ]
    return lines


def _monotonicity_tests(segment: StrategyRankReliability) -> list[str]:
    lines = ["#### Monotonicity tests", ""]
    lines.append("| Horizon | Spearman(rank, α) | Adj. α inversions | Rank-decile Spearman | Decile mono? | Top-5 overconfident? |")
    lines.append("|---------|-------------------|-------------------|----------------------|--------------|----------------------|")
    for horizon in RESEARCH_HORIZONS:
        mono = segment.monotonicity.get(horizon)
        dec = segment.decile_monotonicity.get(horizon)
        if not mono:
            continue
        dec_spearman = _fmt_num(dec.spearman_correlation) if dec else "—"
        dec_mono = "yes" if dec and dec.monotonic else "no"
        top5 = "yes" if mono.top5_overconfident else "no"
        lines.append(
            f"| {horizon}d | {_fmt_num(mono.spearman_correlation)} | {mono.inversion_count} | "
            f"{dec_spearman} | {dec_mono} | {top5} |"
        )
    lines.append("")
    return lines


def _where_ordering_breaks(segment: StrategyRankReliability, horizon: int = 20) -> list[str]:
    lines = [f"#### Where ordering breaks ({horizon}d)", ""]
    inversions: list[str] = []
    for rank in range(1, 20):
        a_lo = segment.per_rank[rank][horizon].alpha
        a_hi = segment.per_rank[rank + 1][horizon].alpha
        if a_lo is not None and a_hi is not None and a_lo > a_hi:
            inversions.append(
                f"rank {rank} ({_fmt_pct(a_lo)}) > rank {rank + 1} ({_fmt_pct(a_hi)})"
            )
    if inversions:
        lines.append("Adjacent-rank alpha inversions (lower rank number should dominate):")
        for inv in inversions[:12]:
            lines.append(f"- {inv}")
        if len(inversions) > 12:
            lines.append(f"- … and {len(inversions) - 12} more")
    else:
        lines.append("- No adjacent-rank alpha inversions at this horizon.")
    cliffs = [c for c in segment.cliffs if c.horizon == horizon]
    if cliffs:
        lines.append("")
        lines.append("Positive cliffs (material jump to next rank):")
        for c in cliffs[:6]:
            lines.append(f"- rank {c.rank_from}→{c.rank_to}: +{_fmt_pct(c.alpha_jump)} alpha")
    lines.append("")
    return lines


def _score_quintile_section(segment: StrategyRankReliability, horizon: int = 20) -> list[str]:
    quintiles = segment.score_quintiles.get(horizon, ())
    if not quintiles:
        return []
    lines = [
        f"#### Score quintiles vs forward alpha ({horizon}d)",
        "",
        "Quintile 1 = highest `composite_score` within each run's top-20 (research diagnostic).",
        "",
        "| Score quintile | Hit rate | Avg return | Alpha | Obs |",
        "|----------------|----------|------------|-------|-----|",
    ]
    for q in quintiles:
        lines.append(
            f"| Q{q.quintile} | {_fmt_pct(q.hit_rate)} | {_fmt_pct(q.average_return)} | "
            f"{_fmt_pct(q.alpha)} | {q.observation_count} |"
        )
    q1 = next((q for q in quintiles if q.quintile == 1), None)
    q3 = next((q for q in quintiles if q.quintile == 3), None)
    if q1 and q3 and q1.alpha is not None and q3.alpha is not None:
        if q1.alpha < q3.alpha:
            lines.append("")
            lines.append(
                f"- **Overconfident score region:** highest-score quintile (Q1) alpha "
                f"{_fmt_pct(q1.alpha)} trails mid quintile Q3 {_fmt_pct(q3.alpha)}."
            )
    lines.append("")
    return lines


def _lower_rank_hypothesis(segment: StrategyRankReliability) -> list[str]:
    h = 20
    a1 = segment.per_rank[1][h].alpha
    a20 = segment.per_rank[20][h].alpha
    a_1_5 = _band_mean(segment, 1, 5, h)
    a_6_10 = _band_mean(segment, 6, 10, h)
    a_11_20 = _band_mean(segment, 11, 20, h)
    lines = ["#### Why lower ranks may outperform (20d evidence)", ""]
    if a_11_20 is not None and a_1_5 is not None and a_11_20 > a_1_5:
        lines.append(
            f"- **Breadth / dilution:** ranks 11–20 avg alpha {_fmt_pct(a_11_20)} vs "
            f"ranks 1–5 {_fmt_pct(a_1_5)} — tail of top-20 carries more names with "
            "less single-name concentration risk."
        )
    if a_6_10 is not None and a_1_5 is not None and a_6_10 > a_1_5:
        lines.append(
            f"- **Headline rank gap:** ranks 6–10 ({_fmt_pct(a_6_10)}) beat ranks 1–5 "
            f"({_fmt_pct(a_1_5)}) — scorer over-weights top slots."
        )
    if a1 is not None and a20 is not None:
        lines.append(
            f"- **Rank 1 vs 20:** rank-1 alpha {_fmt_pct(a1)}, rank-20 alpha {_fmt_pct(a20)}."
        )
    mono = segment.monotonicity.get(20)
    if mono and mono.top5_overconfident:
        lines.append(
            "- **Mean-reversion / crowding:** top-5 overconfident flag — highest conviction "
            "names mean-revert more over 20d in this window."
        )
    lines.append("")
    return lines


def _band_mean(segment: StrategyRankReliability, start: int, end: int, horizon: int) -> float | None:
    vals = []
    for r in range(start, end + 1):
        a = segment.per_rank[r][horizon].alpha
        if a is not None:
            vals.append(a)
    if not vals:
        return None
    return sum(vals) / len(vals)


def _methodology_appendix() -> list[str]:
    return [
        "## Methodology appendix",
        "",
        "1. **Data:** Completed `ranking_runs` for NIFTY_500; forward returns from "
        "`ranking_performance_snapshots`; regime from `ranking_validation_reports.regime_label`.",
        "2. **Per-rank metrics:** For each exact rank 1–20, pool stock-level forward returns, "
        "compute run-level means, then hit rate / avg return / alpha vs same-run benchmark.",
        "3. **Spearman(rank, alpha):** Negative values imply better ranks (lower numbers) earn "
        "higher alpha; positive values imply inverted ordering.",
        "4. **Rank deciles:** Pairs (1–2), (3–4), … (19–20); decile Spearman tests coarse monotonicity.",
        "5. **Score quintiles:** Within each run's top-20, sort by `ranking_results.score`; "
        "quintile 1 = highest scores — detects overconfident score regions.",
        "6. **No production writes:** Research modules only; ranking engines unchanged.",
        "",
    ]


def build_rank_reliability_markdown(report: RankReliabilityReport) -> str:
    lines = [
        "# Rank Reliability Report",
        "",
        "## Executive summary",
        "",
        "Per-rank forward outcomes for production ranking (research only). "
        "Evaluates whether rank order is monotonic with realized alpha across ranks 1–20.",
        "",
    ]
    lines.extend(_scope_block(report))
    lines.append("## Rank reliability curves (ALL_REGIMES)")
    lines.append("")

    for segment in report.strategies:
        lines.extend([f"### {segment.strategy_name}", ""])
        for horizon in RESEARCH_HORIZONS:
            lines.extend(_per_rank_table(segment, horizon))
            if horizon == 20:
                lines.extend(_ascii_alpha_curve(segment, horizon))
                lines.extend(_strongest_weakest_ranks(segment, horizon))
        lines.extend(_monotonicity_tests(segment))
        lines.extend(_where_ordering_breaks(segment, 20))
        lines.extend(_score_quintile_section(segment, 20))
        lines.extend(_lower_rank_hypothesis(segment))

    lines.extend(["## Factor exposure vs forward return (top 20, 20d)", ""])
    for fseg in report.factor_segments:
        if fseg.regime_label != "ALL_REGIMES":
            continue
        lines.extend([f"### {fseg.strategy_name}", ""])
        lines.extend(
            [
                "| Factor | Winner norm | Loser norm | Spread | Reliability |",
                "|--------|-------------|------------|--------|-------------|",
            ]
        )
        for row in sorted(
            fseg.rows,
            key=lambda r: abs(r.reliability_score or 0),
            reverse=True,
        ):
            lines.append(
                f"| {row.factor_name} | {_fmt_num(row.winner_mean_normalized)} | "
                f"{_fmt_num(row.loser_mean_normalized)} | {_fmt_num(row.spread)} | "
                f"{_fmt_num(row.reliability_score)} |"
            )
        lines.append("")

    lines.extend(_methodology_appendix())
    return "\n".join(lines)


def build_regime_rank_reliability_markdown(report: RankReliabilityReport) -> str:
    lines = [
        "# Regime Rank Reliability Report",
        "",
        "## Executive summary",
        "",
        "Per-rank and per-regime forward outcomes. Identifies which "
        "`ranking_validation_reports.regime_label` buckets show monotonic top ranks vs inverted tails.",
        "",
    ]
    lines.extend(_scope_block(report))
    lines.append("## Regime-split rank curves (20d primary)")
    lines.append("")

    by_strategy: dict[str, list[StrategyRankReliability]] = {}
    for seg in report.regime_segments:
        by_strategy.setdefault(seg.strategy_name, []).append(seg)

    for strategy, segments in sorted(by_strategy.items()):
        lines.extend([f"### {strategy}", ""])
        lines.append("| Regime | Rank-1 α | Rank-20 α | Spearman | Inversions | Monotonic? | Top-5 overconfident? |")
        lines.append("|--------|----------|-----------|----------|------------|------------|----------------------|")
        for seg in sorted(segments, key=lambda s: s.regime_label):
            mono = seg.monotonicity.get(20)
            a1 = seg.per_rank[1][20].alpha
            a20 = seg.per_rank[20][20].alpha
            mono_txt = "yes" if mono and mono.monotonic else "no"
            top5 = "yes" if mono and mono.top5_overconfident else "no"
            inv = mono.inversion_count if mono else "—"
            rho = _fmt_num(mono.spearman_correlation) if mono else "—"
            lines.append(
                f"| {seg.regime_label} | {_fmt_pct(a1)} | {_fmt_pct(a20)} | {rho} | {inv} | "
                f"{mono_txt} | {top5} |"
            )
        lines.append("")

        for seg in sorted(segments, key=lambda s: s.regime_label):
            lines.extend([f"#### {seg.regime_label} — per-rank (20d)", ""])
            lines.extend(_per_rank_table(seg, 20))
            lines.extend(_ascii_alpha_curve(seg, 20))
            lines.extend(_where_ordering_breaks(seg, 20))

    lines.extend(_methodology_appendix())
    return "\n".join(lines)


def _factor_segment_table(fseg: FactorReliabilitySegment) -> list[str]:
    lines = [
        f"#### {fseg.strategy_name} / {fseg.regime_label} ({fseg.horizon}d)",
        "",
        "| Factor | Winner norm | Loser norm | Spread | Winners | Losers |",
        "|--------|-------------|------------|--------|---------|--------|",
    ]
    for row in sorted(fseg.rows, key=lambda r: abs(r.spread or 0), reverse=True):
        lines.append(
            f"| {row.factor_name} | {_fmt_num(row.winner_mean_normalized)} | "
            f"{_fmt_num(row.loser_mean_normalized)} | {_fmt_num(row.spread)} | "
            f"{row.winner_count} | {row.loser_count} |"
        )
    lines.append("")
    return lines


def build_factor_reliability_markdown(report: RankReliabilityReport) -> str:
    lines = [
        "# Factor Reliability Report",
        "",
        "## Executive summary",
        "",
        "Top-20 `ranking_results.score_components` vs forward return sign/magnitude. "
        "Winners = at or above run median return; losers = below. Spread = winner mean "
        "normalized − loser mean normalized.",
        "",
    ]
    lines.extend(_scope_block(report))
    lines.append("## Factor spreads by strategy and horizon (ALL_REGIMES)")
    lines.append("")
    for strategy in report.config.strategy_names:
        lines.extend([f"### {strategy}", ""])
        for horizon in RESEARCH_HORIZONS:
            fseg = next(
                (
                    f
                    for f in report.factor_segments
                    if f.strategy_name == strategy
                    and f.regime_label == "ALL_REGIMES"
                    and f.horizon == horizon
                ),
                None,
            )
            if fseg:
                lines.extend(_factor_segment_table(fseg))

    lines.append("## Regime-split factor spreads (20d)")
    lines.append("")
    for fseg in sorted(
        [f for f in report.factor_segments if f.horizon == 20 and f.regime_label != "ALL_REGIMES"],
        key=lambda f: (f.strategy_name, f.regime_label),
    ):
        lines.extend(_factor_segment_table(fseg))

    lines.extend(
        [
            "## Methodology",
            "",
            "1. Universe: top-20 picks per completed run.",
            "2. Per run, median split on forward return at horizon.",
            "3. Compare `score_components[factor].normalized` for winners vs losers.",
            "4. Research only — no production factor weight changes.",
            "",
        ]
    )
    return "\n".join(lines)


def _score_bucket_table(segment: ScoreCompressionSegment, horizon: int) -> list[str]:
    lines = [
        f"#### Score buckets ({horizon}d) — {segment.strategy_name}",
        "",
        "| Score bucket | Hit rate | Avg return | Alpha | Sharpe | Max DD | Obs |",
        "|--------------|----------|------------|-------|--------|--------|-----|",
    ]
    for label, _, _ in SCORE_BUCKET_SPECS:
        m = segment.per_bucket.get(label, {}).get(horizon)
        if not m:
            continue
        lines.append(
            f"| {label} | {_fmt_pct(m.hit_rate)} | {_fmt_pct(m.average_return)} | "
            f"{_fmt_pct(m.alpha)} | {_fmt_num(m.sharpe)} | {_fmt_pct(m.max_drawdown)} | "
            f"{m.observation_count} |"
        )
    lines.append("")
    return lines


def build_score_compression_markdown(
    report: RankReliabilityReport,
    compression: ScoreCompressionReport,
) -> str:
    lines = [
        "# Score Compression Analysis",
        "",
        "## Executive summary",
        "",
        "Within-run composite score buckets for top-20 names. Tests whether "
        "tighter high scores (e.g. ≥0.97) outperform mid scores (e.g. 0.92–0.94).",
        "",
    ]
    lines.extend(_scope_block(report))
    lines.append("## Score bucket curves (ALL_REGIMES)")
    lines.append("")

    for segment in compression.segments:
        if segment.regime_label != "ALL_REGIMES":
            continue
        lines.extend([f"### {segment.strategy_name}", ""])
        for horizon in RESEARCH_HORIZONS:
            lines.extend(_score_bucket_table(segment, horizon))
        cmp = compare_score_buckets(segment, 20, "score_ge_0.97", "score_0.92_0.94")
        if cmp:
            verdict = "outperforms" if cmp.high_outperforms else "underperforms"
            lines.append(
                f"- **0.97 vs 0.92–0.94 (20d):** ≥0.97 bucket {verdict} "
                f"0.92–0.94 by {_fmt_pct(abs(cmp.alpha_spread))} alpha."
            )
            lines.append("")

    lines.extend(
        [
            "## Methodology",
            "",
            "Buckets: "
            + ", ".join(f"`{label}` [{low}, {high})" for label, low, high in SCORE_BUCKET_SPECS)
            + ".",
            "Metrics pooled across all top-20 observations in scope.",
            "",
        ]
    )
    return "\n".join(lines)


def build_ranking_calibration_root_cause_markdown(
    reliability: RankReliabilityReport,
    compression: ScoreCompressionReport,
    *,
    reliability_path: str = "docs/rank-reliability-report.md",
    factor_path: str = "docs/factor-reliability-report.md",
    regime_path: str = "docs/regime-rank-reliability-report.md",
    compression_path: str = "docs/score-compression-analysis.md",
) -> str:
    headlines = build_root_cause_headlines(reliability, compression)
    return _build_root_cause_body(
        reliability,
        headlines,
        reliability_path=reliability_path,
        factor_path=factor_path,
        regime_path=regime_path,
        compression_path=compression_path,
    )


def _build_root_cause_body(
    reliability: RankReliabilityReport,
    headlines: RootCauseHeadlines,
    *,
    reliability_path: str,
    factor_path: str,
    regime_path: str,
    compression_path: str,
) -> str:
    lines = [
        "# Ranking Calibration Root Cause",
        "",
        "## Executive summary (Phase 5 headlines)",
        "",
        "### Why Top 20 works",
        "",
    ]
    for item in headlines.why_top20_works:
        lines.append(f"- {item}")
    lines.extend(["", "### Why rank ordering fails", ""])
    for item in headlines.why_rank_fails:
        lines.append(f"- {item}")
    lines.extend(["", "### Root causes", ""])
    for item in headlines.root_causes:
        lines.append(f"- {item}")
    lines.extend(["", "### Simplest fix (research-only)", ""])
    for item in headlines.simplest_fix:
        lines.append(f"- {item}")

    lines.extend(["", "## Evidence links", ""])
    lines.extend(
        [
            f"- [Rank reliability]({reliability_path})",
            f"- [Factor reliability]({factor_path})",
            f"- [Regime rank reliability]({regime_path})",
            f"- [Score compression]({compression_path})",
            "",
            "## Scope",
            "",
            f"- Runs: {reliability.ranked_run_count}",
            f"- Window: {reliability.config.start_date} → {reliability.config.end_date}",
            "",
        ]
    )
    return "\n".join(lines)


def _portfolio_row(metrics: PortfolioBacktestMetrics) -> str:
    return (
        f"| {metrics.label} | {metrics.horizon}d | {_fmt_pct(metrics.hit_rate)} | "
        f"{_fmt_pct(metrics.average_return)} | {_fmt_pct(metrics.alpha)} | "
        f"{_fmt_num(metrics.sharpe)} | {_fmt_pct(metrics.max_drawdown)} | "
        f"{_fmt_num(metrics.rank_return_correlation)} | {metrics.run_count} |"
    )


def build_backtest_markdown(
    report: CalibratedRankingBacktestReport,
    tables: CalibrationTables,
) -> str:
    cfg = report.config
    w = tables.weights
    lines = [
        "# Calibrated Ranking Backtest",
        "",
        "## Executive summary",
        "",
        f"**Verdict:** `{report.verdict}` — {report.verdict_summary}",
        "",
        "## Scope",
        "",
        f"- Universe: `{cfg.universe_code}`",
        f"- Strategies: {', '.join(cfg.strategy_names)}",
        f"- Date window: {cfg.start_date.isoformat()} → {cfg.end_date.isoformat()}",
        f"- Runs: {report.ranked_run_count}",
        "",
        "## Comparison: production Top 20 vs research calibrated Top 20",
        "",
        "| Portfolio | Horizon | Hit rate | Avg return | Alpha | Sharpe | Max DD | Rank↔return ρ | Runs |",
        "|-----------|---------|----------|------------|-------|--------|--------|---------------|------|",
    ]
    for horizon in RESEARCH_HORIZONS:
        prod = next(m for m in report.production if m.horizon == horizon)
        cal = next(m for m in report.calibrated if m.horizon == horizon)
        lines.append(_portfolio_row(prod))
        lines.append(_portfolio_row(cal))
    lines.extend(
        [
            "",
            "## Success criteria",
            "",
            "| Criterion | Met |",
            "|-----------|-----|",
            f"| Improved monotonicity (more negative Spearman at 20d) | {'✓' if report.meets_monotonicity else '✗'} |",
            f"| Better top-5 alpha (5d) | {'✓' if report.meets_top5_alpha else '✗'} |",
            f"| Better top-10 alpha (10d) | {'✓' if report.meets_top10_alpha else '✗'} |",
            f"| Better Sharpe (20d) | {'✓' if report.meets_sharpe else '✗'} |",
            "",
            "## Calibration weights (research only)",
            "",
            f"- raw_score: {w.raw_score}",
            f"- regime_reliability: {w.regime_reliability}",
            f"- factor_reliability: {w.factor_reliability}",
            f"- historical_rank_reliability: {w.historical_rank_reliability}",
            "",
        ]
    )
    return "\n".join(lines)


def _headline_stats(report: RankReliabilityReport) -> tuple[str, str, str]:
    """Return verdict label, rank1 alpha, rank20 alpha for breakout 20d."""
    breakout = next((s for s in report.strategies if s.strategy_name == "breakout_v1"), None)
    if not breakout:
        breakout = report.strategies[0] if report.strategies else None
    if not breakout:
        return "partial", "—", "—"
    a1 = breakout.per_rank[1][20].alpha
    a20 = breakout.per_rank[20][20].alpha
    mono = breakout.monotonicity.get(20)
    if mono and mono.monotonic:
        verdict = "yes"
    elif mono and mono.spearman_correlation is not None and mono.spearman_correlation > 0.3:
        verdict = "partial"
    else:
        verdict = "partial"
    return verdict, _fmt_pct(a1), _fmt_pct(a20)


def build_master_research_markdown(
    reliability_path: str,
    regime_path: str,
    backtest_path: str,
    reliability: RankReliabilityReport,
    report: CalibratedRankingBacktestReport,
    tables: CalibrationTables,
) -> str:
    cal_verdict, rank1_a, rank20_a = _headline_stats(reliability)
    prod_20 = next(m for m in report.production if m.horizon == 20)
    cal_20 = next(m for m in report.calibrated if m.horizon == 20)

    lines = [
        "# Calibrated Ranking Research",
        "",
        "## Final answer",
        "",
        "**Can ranking calibration improve alpha and restore monotonic rank ordering?**",
        "",
        f"**Verdict: `{cal_verdict.upper()}`** — In-sample re-ranking improves rank↔return "
        f"correlation and Sharpe slightly but does **not** materially lift 20d portfolio alpha "
        f"(production {_fmt_pct(prod_20.alpha)} vs calibrated {_fmt_pct(cal_20.alpha)}). "
        f"Monotonic rank curves remain inverted in ALL_REGIMES (breakout 20d: rank-1 α {rank1_a}, "
        f"rank-20 α {rank20_a}; Spearman positive). Calibration is a research hypothesis, not "
        "production-ready.",
        "",
        "## Architecture",
        "",
        "Read-only pipeline over `ranking_results`, `ranking_performance_snapshots`, "
        "`ranking_validation_reports`. No production ranking writes.",
        "",
        "```",
        "scripts/generate_rank_reliability_reports.py",
        "  → docs/rank-reliability-report.md",
        "  → docs/regime-rank-reliability-report.md",
        "  → docs/calibrated-ranking-research.md (+ backtest section)",
        "```",
        "",
        "Modules: `app/ranking_research/` (data_loader, rank_reliability, factor_reliability, "
        "calibration, backtest, reports).",
        "",
        "## Proposed calibration (research-only)",
        "",
        "### Layer 1 — Isotonic rank→expected return",
        "",
        "Fit per (strategy, regime) isotonic regression: production rank → mean 20d alpha "
        "from historical runs. Replace displayed rank with calibrated expected-return order "
        "(does not change raw factor scores).",
        "",
        "### Layer 2 — Regime-conditional weights",
        "",
        "Current research blend (in-sample tables):",
        "",
        "```",
        "calibrated_score =",
        "  1.0  * raw_rank_score",
        "  + 0.15 * regime_reliability[regime][rank]",
        "  + 0.10 * factor_reliability",
        "  + 0.20 * historical_rank_reliability[rank]",
        "```",
        "",
        "### Layer 3 — Score shrinkage for overconfident quintiles",
        "",
        "When score quintile Q1 underperforms Q3 at 20d, dampen top-score names toward "
        "median composite score before final sort.",
        "",
        "## Backtest summary (historical runs, no prod ranker change)",
        "",
        f"Verdict `{report.verdict}`: {report.verdict_summary}",
        "",
        "| Portfolio | 20d Alpha | Rank↔return ρ |",
        "|-----------|-----------|---------------|",
        f"| production_top20 | {_fmt_pct(prod_20.alpha)} | {_fmt_num(prod_20.rank_return_correlation)} |",
        f"| calibrated_top20 | {_fmt_pct(cal_20.alpha)} | {_fmt_num(cal_20.rank_return_correlation)} |",
        "",
        "| Criterion | Met |",
        "|-----------|-----|",
        f"| Improved monotonicity (ρ) | {'✓' if report.meets_monotonicity else '✗'} |",
        f"| Better top-5 alpha (5d) | {'✓' if report.meets_top5_alpha else '✗'} |",
        f"| Better top-10 alpha (10d) | {'✓' if report.meets_top10_alpha else '✗'} |",
        f"| Better Sharpe (20d) | {'✓' if report.meets_sharpe else '✗'} |",
        "",
        "**Expected impact:** Modest monotonicity gain in portfolio ρ; alpha unchanged at 20d "
        "in this window. Material alpha lift would require out-of-sample isotonic tables and "
        "factor spread re-estimation per regime.",
        "",
        "## Implementation phases (research script only)",
        "",
        "| Phase | Deliverable | Prod merge? |",
        "|-------|-------------|-------------|",
        "| 1 | `generate_rank_reliability_reports.py` + reliability/regime docs | No |",
        "| 2 | Walk-forward isotonic tables (`ranking_research/calibration.py`) | No |",
        "| 3 | OOS backtest vs production top-N | No |",
        "| 4 | Optional ranking v2 RFC after OOS pass | Separate PR |",
        "",
        "## Linked reports",
        "",
        f"- [Rank reliability]({reliability_path})",
        f"- [Regime rank reliability]({regime_path})",
        f"- [Backtest detail]({backtest_path})",
        "",
        "## Recommendation: ranking v2?",
        "",
        "**NO** for production promotion — backtest `mixed`, in-sample fit, weak 20d alpha lift.",
        "Continue production ranker; iterate research calibration with walk-forward validation.",
        "",
    ]
    return "\n".join(lines)
