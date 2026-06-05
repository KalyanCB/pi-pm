from __future__ import annotations

from app.outcome_attribution.constants import (
    ATTRIBUTION_BUCKETS,
    ATTRIBUTION_HORIZONS,
    RANK_BANDS_TOP_20,
)
from app.outcome_attribution.models import BucketMetrics, OutcomeAttributionReport, SegmentMetrics


def _fmt_pct(value: float | None, *, digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{100 * value:.{digits}f}%"


def _fmt_num(value: float | None, *, digits: int = 3) -> str:
    if value is None:
        return "—"
    return f"{value:.{digits}f}"


def _metrics_row(label: str, metrics: BucketMetrics) -> str:
    return (
        f"| {label} | {metrics.horizon}d | {_fmt_pct(metrics.hit_rate)} | "
        f"{_fmt_pct(metrics.average_return)} | {_fmt_pct(metrics.alpha)} | "
        f"{_fmt_num(metrics.sharpe)} | {_fmt_pct(metrics.max_drawdown)} | "
        f"{metrics.run_count} | {metrics.observation_count} | {metrics.status} |"
    )


def _bucket_table(segment: SegmentMetrics, horizon: int) -> list[str]:
    lines = [
        f"#### {horizon}-day horizon",
        "",
        "| Bucket | Horizon | Hit rate | Avg return | Alpha | Sharpe | Max DD | Runs | Obs | Status |",
        "|--------|---------|----------|------------|-------|--------|--------|------|-----|--------|",
    ]
    bucket_metrics = segment.horizons.get(horizon, {})
    labels = {
        "top_5": "Top 5",
        "top_10": "Top 10",
        "top_20": "Top 20",
        "benchmark": "Benchmark",
    }
    for bucket in ATTRIBUTION_BUCKETS:
        metrics = bucket_metrics.get(bucket)
        if metrics is None:
            continue
        lines.append(_metrics_row(labels.get(bucket, bucket), metrics))
    lines.append("")
    return lines


def _rank_band_table(segment: SegmentMetrics, horizon: int) -> list[str]:
    lines = [
        f"#### Rank bands within Top 20 ({horizon}d)",
        "",
        "| Rank band | Horizon | Hit rate | Avg return | Alpha | Sharpe | Max DD | Runs | Obs | Status |",
        "|-----------|---------|----------|------------|-------|--------|--------|------|-----|--------|",
    ]
    band_metrics = segment.rank_bands.get(horizon, {})
    labels = {
        "rank_1_5": "Rank 1–5",
        "rank_6_10": "Rank 6–10",
        "rank_11_20": "Rank 11–20",
    }
    for band in RANK_BANDS_TOP_20:
        metrics = band_metrics.get(band)
        if metrics is None:
            continue
        lines.append(_metrics_row(labels.get(band, band), metrics))
    lines.append("")
    return lines


def build_markdown_report(report: OutcomeAttributionReport) -> str:
    cfg = report.config
    strategies = ", ".join(cfg.strategy_names)
    lines = [
        "# Outcome Attribution Report",
        "",
        "## Executive summary",
        "",
        "**Question:** Does higher rank reliably lead to better future outcomes?",
        "",
        f"**Verdict:** `{report.verdict}` — {report.verdict_summary}",
        "",
        "## Scope",
        "",
        f"- Universe: `{cfg.universe_code}`",
        f"- Strategies: {strategies}",
        f"- Date window: {cfg.start_date.isoformat()} → {cfg.end_date.isoformat()}",
        f"- Ranking runs analyzed: {report.ranked_run_count}",
        f"- Runs with 20d forward data: {report.runs_with_forward_data}",
        "",
    ]

    for segment in report.segments:
        lines.extend(
            [
                f"## {segment.strategy_name} — {segment.regime_label}",
                "",
            ]
        )
        for horizon in ATTRIBUTION_HORIZONS:
            lines.extend(_bucket_table(segment, horizon))
        for horizon in ATTRIBUTION_HORIZONS:
            lines.extend(_rank_band_table(segment, horizon))

    lines.extend(
        [
            "## Appendix: Methodology",
            "",
            "### Data sources",
            "",
            "- `ranking_runs` / `ranking_results` for rank and strategy metadata",
            "- `ranking_performance_snapshots` for forward returns (5/10/20/60 trading days)",
            "- `ranking_validation_reports.regime_label` for regime segmentation (fallback: `ranking_runs.regime_label`)",
            "- Benchmark forward returns computed from `market_data` using each run's `benchmark_symbol`",
            "",
            "### Bucket construction",
            "",
            "- **Top N buckets:** equal-weight average forward return of stocks ranked 1..N on each run date",
            "- **Benchmark:** buy-and-hold forward return of the run benchmark index over the same horizon",
            "- **Rank bands:** Rank 1–5, 6–10, 11–20 within the top-20 cohort",
            "",
            "### Metrics",
            "",
            "- **Hit rate:** fraction of stock-level observations with positive forward return",
            "- **Average return:** mean of per-run equal-weight bucket returns (one point per ranking date)",
            "- **Alpha:** bucket average return minus benchmark average return (same horizon, matched runs)",
            "- **Sharpe:** `mean(r)/std(r) × sqrt(252 / horizon)` on the per-run bucket return series",
            "- **Max drawdown:** peak-to-trough decline on the compounded cumulative path of per-run bucket returns",
            "",
            "### Limitations",
            "",
            "- Overlapping forward windows when ranking runs are daily; treat Sharpe/drawdown as descriptive, not live-trading P&L",
            "- Runs missing forward return fields are excluded from that horizon's averages",
            "- Read-only analytics; no changes to ranking engines, ARGS, or governance layers",
            "",
        ]
    )
    return "\n".join(lines)
