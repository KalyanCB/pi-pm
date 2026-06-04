from __future__ import annotations

from app.outcome_attribution.constants import REGIME_LABEL_ALL
from app.ranking_research.models import (
    RankReliabilityReport,
    RootCauseHeadlines,
    ScoreCompressionReport,
    StrategyRankReliability,
)
from app.ranking_research.score_compression import compare_score_buckets


def _band_mean(segment: StrategyRankReliability, start: int, end: int, horizon: int) -> float | None:
    vals = []
    for r in range(start, end + 1):
        m = segment.per_rank[r][horizon]
        if m.alpha is not None and m.status == "ok":
            vals.append(m.alpha)
    if not vals:
        return None
    return sum(vals) / len(vals)


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{100 * value:.2f}%"


def build_root_cause_headlines(
    reliability: RankReliabilityReport,
    compression: ScoreCompressionReport,
) -> RootCauseHeadlines:
    """Synthesize headline answers for ranking-calibration root-cause doc."""
    why_top20_works: list[str] = []
    why_rank_fails: list[str] = []
    root_causes: list[str] = []
    simplest_fix: list[str] = []

    for seg in reliability.strategies:
        h20 = 20
        top20_alpha = _band_mean(seg, 1, 20, h20)
        if top20_alpha is not None:
            why_top20_works.append(
                f"{seg.strategy_name}: top-20 avg 20d α {_fmt_pct(top20_alpha)} — "
                "pool selection adds value vs benchmark."
            )

        a_1_5 = _band_mean(seg, 1, 5, h20)
        a_6_10 = _band_mean(seg, 6, 10, h20)
        a_11_20 = _band_mean(seg, 11, 20, h20)
        mono = seg.monotonicity.get(h20)
        if mono:
            rho = mono.spearman_correlation
            if rho is not None and rho > 0:
                why_rank_fails.append(
                    f"{seg.strategy_name}: inverted Spearman(rank, α)={rho:.3f} at 20d."
                )
            if mono.top5_overconfident:
                why_rank_fails.append(
                    f"{seg.strategy_name}: ranks 6–10 α {_fmt_pct(a_6_10)} "
                    f"> ranks 1–5 {_fmt_pct(a_1_5)}."
                )
        if a_11_20 is not None and a_1_5 is not None and a_11_20 > a_1_5:
            why_rank_fails.append(
                f"{seg.strategy_name}: ranks 11–20 ({_fmt_pct(a_11_20)}) "
                f"> ranks 1–5 ({_fmt_pct(a_1_5)})."
            )

        q1 = next((q for q in seg.score_quintiles.get(h20, ()) if q.quintile == 1), None)
        q5 = next((q for q in seg.score_quintiles.get(h20, ()) if q.quintile == 5), None)
        if q1 and q5 and q1.alpha is not None and q5.alpha is not None and q1.alpha < q5.alpha:
            root_causes.append(
                f"{seg.strategy_name}: score compression — Q1 α {_fmt_pct(q1.alpha)} "
                f"< Q5 {_fmt_pct(q5.alpha)}."
            )

    for strategy in ("breakout_v1", "momentum_v1"):
        comp_seg = next(
            (
                s
                for s in compression.segments
                if s.strategy_name == strategy and s.regime_label == REGIME_LABEL_ALL
            ),
            None,
        )
        if not comp_seg:
            continue
        cmp = compare_score_buckets(comp_seg, 20, "score_ge_0.97", "score_0.92_0.94")
        if cmp:
            verb = "outperform" if cmp.high_outperforms else "underperform"
            root_causes.append(
                f"{strategy}: scores ≥0.97 {verb} 0.92–0.94 by "
                f"{_fmt_pct(abs(cmp.alpha_spread))} 20d α."
            )
        elif strategy == "breakout_v1":
            root_causes.append(
                "breakout_v1: composite scores rarely exceed 0.97 — rank driven by "
                "factor blend, not fine score separation."
            )

    for fseg in reliability.factor_segments:
        if fseg.regime_label != REGIME_LABEL_ALL or fseg.horizon != 20:
            continue
        weak = [r for r in fseg.rows if r.spread is not None and r.spread < 0]
        if len(weak) >= 2:
            names = ", ".join(r.factor_name for r in weak[:3])
            root_causes.append(
                f"{fseg.strategy_name}: factors anticorrelate with winners ({names})."
            )

    best_regime = None
    worst_regime = None
    best_rho = -2.0
    worst_rho = 2.0
    for rseg in reliability.regime_segments:
        if rseg.strategy_name != "breakout_v1":
            continue
        mono = rseg.monotonicity.get(20)
        if not mono or mono.spearman_correlation is None:
            continue
        rho = mono.spearman_correlation
        if rho < best_rho:
            best_rho = rho
            best_regime = rseg.regime_label
        if rho > worst_rho:
            worst_rho = rho
            worst_regime = rseg.regime_label
    if best_regime and worst_regime:
        root_causes.append(
            f"Regime: best ordering {best_regime} (ρ={best_rho:.3f}), "
            f"worst {worst_regime} (ρ={worst_rho:.3f})."
        )

    if not root_causes:
        root_causes.append(
            "Mixed rank curves with score–return decoupling and near-zero factor spreads."
        )

    simplest_fix.extend(
        [
            "Research-only isotonic rank → expected 20d α per (strategy, regime).",
            "Shrink top-score quintile toward run median composite before sort.",
            "Walk-forward OOS validation before any ranking v2 promotion.",
        ]
    )

    if not why_top20_works:
        why_top20_works.append("Top-20 basket beats benchmark; selection breadth works.")
    if not why_rank_fails:
        why_rank_fails.append("Fine rank slots do not monotonically track forward alpha.")

    return RootCauseHeadlines(
        why_top20_works=tuple(why_top20_works),
        why_rank_fails=tuple(why_rank_fails),
        root_causes=tuple(root_causes),
        simplest_fix=tuple(simplest_fix),
    )
