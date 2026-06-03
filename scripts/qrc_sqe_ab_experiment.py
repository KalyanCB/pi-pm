#!/usr/bin/env python3
"""A/B experiment: legacy QRC brief vs SQE condensation (deterministic metrics)."""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
from dataclasses import dataclass
from typing import Any

from app.args.plugins.quant_payload import build_qrc_user_payload
from app.args.plugins.stock_quality_evidence import build_stock_quality_evidence
from app.core.config import get_settings
from app.validation.constants import VALIDATION_STATUS_PENDING


FOCUS_SYMBOLS = ("HFCL.NS", "WOCKPHARMA.NS", "THERMAX.NS", "TRITURBINE.NS")

_HFCL_COMPONENTS = {
    "volatility_adjusted_momentum": {"normalized": "1.0", "weighted": "0.20"},
    "relative_strength": {"normalized": "1.0", "weighted": "0.15"},
    "high_proximity": {"normalized": "0.992", "weighted": "0.149"},
    "consolidation_breakout": {"normalized": "0.031", "weighted": "0.003"},
}

_THERMAX_COMPONENTS = {
    "volatility_adjusted_momentum": {"normalized": "0.95", "weighted": "0.19"},
    "relative_strength": {"normalized": "0.92", "weighted": "0.14"},
    "high_proximity": {"normalized": "0.88", "weighted": "0.13"},
    "consolidation_breakout": {"normalized": "0.279", "weighted": "0.028"},
}


@dataclass(frozen=True)
class StockFixture:
    symbol: str
    rank: int
    composite: float
    see_score: float
    qualifying: int
    win_rate: float
    median_return: float
    score_components: dict[str, dict[str, str]]


BREAKOUT_FIXTURES: tuple[StockFixture, ...] = (
    StockFixture("HFCL.NS", 1, 0.8873, 62.89, 97, 0.429, -0.037, _HFCL_COMPONENTS),
    StockFixture("WOCKPHARMA.NS", 2, 0.887, 71.54, 110, 0.625, 0.015, _HFCL_COMPONENTS),
    StockFixture("THERMAX.NS", 3, 0.886, 59.88, 40, 0.40, -0.02, _THERMAX_COMPONENTS),
    StockFixture("TRITURBINE.NS", 12, 0.842, 62.04, 50, 0.375, -0.01, _THERMAX_COMPONENTS),
)


def _breakout_base_packet(strategy: str = "breakout_v1") -> dict[str, Any]:
    return {
        "strategy": {"name": strategy, "version": "1.0.0"},
        "validation": {
            "status": VALIDATION_STATUS_PENDING,
            "database_status": "insufficient_data",
            "regime_label": "BEAR_LOW_VOL",
        },
        "historical_validation_context": {
            "completed_reports_in_window": 3,
            "recent_completed_validations": [
                {
                    "as_of_date": "2026-05-11",
                    "report_id": "hist-1",
                    "regime_label": "BEAR_LOW_VOL",
                    "horizon_metrics": [
                        {
                            "horizon": 5,
                            "sample_size": 347,
                            "rank_ic_spearman": 0.14,
                            "hit_rate": 0.54,
                        }
                    ],
                    "decile_metrics": [
                        {"horizon": 5, "decile": 10, "avg_return": 0.02},
                        {"horizon": 5, "decile": 1, "avg_return": -0.03},
                    ],
                }
            ],
        },
        "regime": {
            "strategy_regime_performance": [
                {
                    "regime_label": "BEAR_LOW_VOL",
                    "horizon": 5,
                    "avg_ic": -0.091,
                    "avg_spread": -0.032,
                    "sample_count": 116,
                    "is_current_regime": True,
                },
                {
                    "regime_label": "BULL_LOW_VOL",
                    "horizon": 5,
                    "avg_ic": 0.038,
                    "avg_spread": 0.016,
                    "sample_count": 98,
                    "is_current_regime": False,
                },
            ]
        },
        "quant_evidence": {
            "factor_ic": [
                {"factor_name": "high_proximity", "ic_spearman": -0.146, "regime_label": "BEAR_LOW_VOL"},
                {"factor_name": "relative_strength", "ic_spearman": -0.141, "regime_label": "BEAR_LOW_VOL"},
                {
                    "factor_name": "relative_strength_acceleration",
                    "ic_spearman": 0.024,
                    "regime_label": "BEAR_LOW_VOL",
                },
                {
                    "factor_name": "volatility_adjusted_momentum",
                    "ic_spearman": -0.12,
                    "regime_label": "BEAR_LOW_VOL",
                },
                {
                    "factor_name": "consolidation_breakout",
                    "ic_spearman": -0.08,
                    "regime_label": "BEAR_LOW_VOL",
                },
            ],
            "exit_research": [
                {
                    "policy_family": "FIXED_HOLD",
                    "policy_variant": "60",
                    "mean_return": 0.047,
                    "hit_rate": 0.637,
                    "sample_size": 400,
                },
                {
                    "policy_family": "TRAILING_STOP",
                    "policy_variant": "10",
                    "mean_return": -0.01,
                    "hit_rate": 0.42,
                    "sample_size": 200,
                },
            ],
        },
    }


def _fixture_packet(base: dict[str, Any], fixture: StockFixture) -> dict[str, Any]:
    payload = dict(base)
    payload["ranking"] = {
        "ranking_run_id": "b8e993e4-a049-4f3a-bcd0-29574a0f7e47",
        "as_of_date": "2026-06-02",
        "rank": fixture.rank,
        "composite_score": fixture.composite,
        "score_components": fixture.score_components,
    }
    payload["stock_setup_evidence"] = {
        "status": "completed",
        "setup_evidence_score": fixture.see_score,
        "qualifying_matches": fixture.qualifying,
        "total_matches": fixture.qualifying + 5,
        "regime_statistics": [
            {
                "regime_label": "BEAR_LOW_VOL",
                "sample_size": max(fixture.qualifying, 8),
                "win_rate_20d": fixture.win_rate,
                "avg_return_20d": 0.035 if fixture.win_rate >= 0.5 else -0.005,
                "median_return_20d": fixture.median_return,
                "avg_max_drawdown_20d": 0.139,
                "avg_max_runup_20d": 0.125,
            }
        ],
    }
    sqe = build_stock_quality_evidence(payload, fixture.symbol)
    payload["stock_quality_evidence"] = sqe
    return payload


def _momentum_factor_ic() -> list[dict[str, Any]]:
    return [
        {"factor_name": "momentum", "ic_spearman": 0.06, "regime_label": "BEAR_LOW_VOL"},
        {"factor_name": "volatility_adjusted_momentum", "ic_spearman": 0.04, "regime_label": "BEAR_LOW_VOL"},
        {"factor_name": "relative_strength", "ic_spearman": 0.03, "regime_label": "BEAR_LOW_VOL"},
    ]


def build_fixture_packets(strategy: str) -> list[tuple[str, dict[str, Any]]]:
    base = _breakout_base_packet(strategy)
    if strategy == "momentum_v1":
        base["quant_evidence"] = {
            **base["quant_evidence"],
            "factor_ic": _momentum_factor_ic(),
        }
        fixtures = tuple(
            StockFixture(
                f.symbol.replace(".NS", "_M.NS"),
                f.rank,
                f.composite,
                f.see_score,
                f.qualifying,
                f.win_rate,
                f.median_return,
                {"momentum": {"normalized": "0.95", "weighted": "0.38"}},
            )
            for f in BREAKOUT_FIXTURES
        )
    else:
        fixtures = BREAKOUT_FIXTURES

    return [(f.symbol, _fixture_packet(base, f)) for f in fixtures]


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    den_x = math.sqrt(sum((x - mx) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - my) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return None
    return round(num / (den_x * den_y), 4)


def _confidence_for_mode(payload: dict[str, Any], symbol: str, *, use_sqe: bool) -> float:
    prev = os.environ.get("ARGS_QRC_USE_SQE")
    os.environ["ARGS_QRC_USE_SQE"] = "true" if use_sqe else "false"
    get_settings.cache_clear()
    try:
        user = build_qrc_user_payload(payload, symbol)
        if use_sqe and "qrc_sqe_brief" in user:
            return float(user["overall_stock_quality_score"])
        return float(user["overall_quant_confidence"])
    finally:
        if prev is None:
            os.environ.pop("ARGS_QRC_USE_SQE", None)
        else:
            os.environ["ARGS_QRC_USE_SQE"] = prev
        get_settings.cache_clear()


def _payload_chars(payload: dict[str, Any], symbol: str, *, use_sqe: bool) -> int:
    prev = os.environ.get("ARGS_QRC_USE_SQE")
    os.environ["ARGS_QRC_USE_SQE"] = "true" if use_sqe else "false"
    get_settings.cache_clear()
    try:
        user = build_qrc_user_payload(payload, symbol)
        return len(json.dumps(user, default=str))
    finally:
        if prev is None:
            os.environ.pop("ARGS_QRC_USE_SQE", None)
        else:
            os.environ["ARGS_QRC_USE_SQE"] = prev
        get_settings.cache_clear()


def _dispersion(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "min": None, "max": None, "range": None, "stdev": None, "unique": 0}
    return {
        "count": len(values),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "range": round(max(values) - min(values), 4),
        "stdev": round(statistics.pstdev(values), 4) if len(values) > 1 else 0.0,
        "unique": len(set(round(v, 4) for v in values)),
    }


def analyze_strategy(strategy: str, packets: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    legacy_conf: list[float] = []
    sqe_conf: list[float] = []
    ranks: list[float] = []
    see_scores: list[float] = []
    sqe_scores: list[float] = []
    legacy_chars: list[int] = []
    sqe_chars: list[int] = []
    per_stock: dict[str, Any] = {}

    for symbol, payload in packets:
        rank = float((payload.get("ranking") or {}).get("rank") or 0)
        see = float((payload.get("stock_setup_evidence") or {}).get("setup_evidence_score") or 0)
        sqe = float((payload.get("stock_quality_evidence") or {}).get("overall_stock_quality_score") or 0)
        leg = _confidence_for_mode(payload, symbol, use_sqe=False)
        exp = _confidence_for_mode(payload, symbol, use_sqe=True)
        leg_chars = _payload_chars(payload, symbol, use_sqe=False)
        sqe_mode_chars = _payload_chars(payload, symbol, use_sqe=True)

        legacy_conf.append(leg)
        sqe_conf.append(exp)
        ranks.append(rank)
        see_scores.append(see)
        sqe_scores.append(sqe)
        legacy_chars.append(leg_chars)
        sqe_chars.append(sqe_mode_chars)

        if symbol in FOCUS_SYMBOLS or symbol.endswith("_M.NS"):
            base_sym = symbol.replace("_M.NS", ".NS")
            per_stock[base_sym] = {
                "rank": int(rank),
                "see_score": see,
                "legacy_confidence": round(leg, 4),
                "sqe_confidence": round(exp, 4),
                "sqe_score": round(sqe, 4),
                "legacy_payload_chars": leg_chars,
                "sqe_payload_chars": sqe_mode_chars,
                "delta_confidence": round(exp - leg, 4),
            }

    return {
        "strategy": strategy,
        "as_of_date": "2026-06-02",
        "ranking_run_id": "b8e993e4-a049-4f3a-bcd0-29574a0f7e47",
        "packet_source": "synthetic_fixtures (mirrors breakout 2026-06-02 structure)",
        "legacy": {
            "confidence": _dispersion(legacy_conf),
            "payload_chars_avg": round(statistics.mean(legacy_chars)),
            "correlations": {
                "confidence_vs_rank": _pearson(legacy_conf, ranks),
                "confidence_vs_see": _pearson(legacy_conf, see_scores),
                "confidence_vs_sqe_score": _pearson(legacy_conf, sqe_scores),
            },
        },
        "sqe_experiment": {
            "confidence": _dispersion(sqe_conf),
            "payload_chars_avg": round(statistics.mean(sqe_chars)),
            "correlations": {
                "confidence_vs_rank": _pearson(sqe_conf, ranks),
                "confidence_vs_see": _pearson(sqe_conf, see_scores),
                "confidence_vs_sqe_score": _pearson(sqe_conf, sqe_scores),
            },
        },
        "focus_stocks": per_stock,
    }


def try_load_db_packets(strategy: str, as_of: str) -> list[tuple[str, dict[str, Any]]] | None:
    try:
        from sqlalchemy import select

        from app.db.session import get_session_factory
        from app.models.args import InvestmentReviewPacket as DbPacket
        from app.models.ranking_run import RankingRun
    except Exception:
        return None

    try:
        with get_session_factory()() as db:
            run = db.scalar(
                select(RankingRun)
                .where(RankingRun.as_of_date == as_of)
                .order_by(RankingRun.created_at.desc())
                .limit(1)
            )
            if run is None:
                return None
            rows = db.scalars(
                select(DbPacket).where(DbPacket.ranking_run_id == run.id)
            ).all()
            if not rows:
                return None
            out: list[tuple[str, dict[str, Any]]] = []
            for row in rows:
                payload = dict(row.payload or {})
                if "stock_quality_evidence" not in payload:
                    payload["stock_quality_evidence"] = build_stock_quality_evidence(
                        payload, row.symbol
                    )
                out.append((row.symbol, payload))
            return out
    except Exception:
        return None


def run_experiment(*, use_db: bool) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for strategy in ("breakout_v1", "momentum_v1"):
        packets: list[tuple[str, dict[str, Any]]] | None = None
        source_note = "synthetic_fixtures"
        if use_db:
            packets = try_load_db_packets(strategy, "2026-06-02")
            if packets:
                source_note = "db_packets"
        if not packets:
            packets = build_fixture_packets(strategy)
        analysis = analyze_strategy(strategy, packets)
        analysis["packet_source"] = source_note
        results.append(analysis)
    return {
        "flag_default": get_settings().args_qrc_use_sqe,
        "env_var": "ARGS_QRC_USE_SQE",
        "strategies": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--use-db", action="store_true", help="Try loading packets from DB")
    parser.add_argument("-o", "--output", type=str, default="", help="Write JSON results")
    args = parser.parse_args()

    report = run_experiment(use_db=args.use_db)
    text = json.dumps(report, indent=2)
    print(text)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
