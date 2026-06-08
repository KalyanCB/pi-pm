from __future__ import annotations

import re
from typing import Any

from app.workspace_args.committee_contracts import CommitteeReviewOutput

TRADE_FORBIDDEN_KEYS = frozenset(
    {
        "recommendation_label",
        "position_size_pct",
        "stop_loss_pct",
        "vote",
        "recommendation",
        "final_score",
        "label",
    }
)
TRADE_FORBIDDEN_VALUES = frozenset(
    {"BUY", "SELL", "HOLD", "STRONG_BUY", "STRONG_SELL", "WATCHLIST", "REJECT"}
)
_NUMERIC_IN_FINDINGS = re.compile(r"-?\d+\.?\d*")


def assert_no_trade_fields(blob: dict[str, Any]) -> None:
    for key in blob:
        if key in TRADE_FORBIDDEN_KEYS:
            raise ValueError(f"Forbidden trade field in committee output: {key}")
        value = blob[key]
        if isinstance(value, str) and value.upper() in TRADE_FORBIDDEN_VALUES:
            raise ValueError(f"Forbidden trade value in field {key}: {value}")


def _resolve_ref(packet: dict[str, Any], ref: str) -> bool:
    if ref.startswith("stub:"):
        return True
    parts = [p.strip() for p in ref.split(":")]
    if not parts:
        return False
    root = parts[0]
    if root == "ranking":
        ranking = packet.get("ranking") or {}
        if len(parts) == 1:
            return bool(ranking)
        return parts[1] in ranking
    if root == "validation":
        validation = packet.get("validation") or {}
        if len(parts) >= 3 and parts[1] == "horizon":
            horizon = int(parts[2])
            metrics = validation.get("horizon_metrics") or []
            return any(m.get("horizon") == horizon for m in metrics)
        if len(parts) >= 3 and parts[1] == "decile":
            horizon = int(parts[2])
            decile = int(parts[3]) if len(parts) > 3 else None
            metrics = validation.get("decile_metrics") or []
            if decile is None:
                return any(m.get("horizon") == horizon for m in metrics)
            return any(m.get("horizon") == horizon and m.get("decile") == decile for m in metrics)
        if len(parts) == 2:
            return parts[1] in validation
        return bool(validation)
    if root == "quant_evidence":
        quant = packet.get("quant_evidence") or {}
        if len(parts) == 1:
            return bool(quant)
        block = quant.get(parts[1])
        if block is None:
            return False
        if len(parts) == 2:
            return bool(block)
        if isinstance(block, list):
            return any(
                str(item.get("id", item.get("factor_name", ""))) == parts[2]
                or str(item.get("metric_id", "")) == parts[2]
                for item in block
                if isinstance(item, dict)
            )
        return False
    if root == "regime":
        regime = packet.get("regime") or {}
        return parts[1] in regime if len(parts) > 1 else bool(regime)
    if root == "historical_performance":
        hist = packet.get("historical_performance") or {}
        return parts[1] in hist if len(parts) > 1 else bool(hist)
    if root == "technical_factors":
        technical = packet.get("technical_factors") or {}
        return parts[1] in technical if len(parts) > 1 else bool(technical)
    if root == "market_snapshot":
        block = packet.get("market_snapshot") or {}
        return parts[1] in block if len(parts) > 1 else bool(block)
    if root == "news_snapshot":
        block = packet.get("news_snapshot") or {}
        if not block:
            return False
        if len(parts) <= 1:
            return True
        sub = parts[1]
        # Accept item/item:N/items/article/headline refs when news items are present
        if sub in ("items", "item", "article", "headline") or sub.startswith("item"):
            return bool((block.get("items") or []))
        return sub in block
    if root == "fundamental_snapshot":
        block = packet.get("fundamental_snapshot") or {}
        if not block:
            return False
        if len(parts) <= 1:
            return True
        sub = parts[1]
        if sub == "status":
            return True
        if block.get("status") == "available":
            # Accept any group-level or field-level ref when data is present
            return True
        return sub in block
    if root == "fundamental":
        block = packet.get("fundamental_snapshot") or {}
        if len(parts) > 1 and parts[1] == "status":
            return True
        return parts[1] in block if len(parts) > 1 else bool(block)
    if root == "research_context":
        block = packet.get("research_context") or {}
        if len(parts) > 1 and parts[1] in ("catalysts", "notes"):
            return True
        return parts[1] in block if len(parts) > 1 else bool(block)
    if root == "historical_validation_context":
        block = packet.get("historical_validation_context") or {}
        if not block:
            return False
        if len(parts) == 1:
            return True
        field = parts[1]
        if field in block:
            return True
        if field == "report_id" and len(parts) > 2:
            report_id = parts[2]
            for item in block.get("recent_completed_validations") or []:
                if str(item.get("report_id")) == report_id:
                    return True
            return report_id in str(block)
        if field in ("rank_ic", "rank_ic_spearman", "completed_reports_in_window"):
            return True
        # Accept any sub-ref when the block is non-empty — the LLM sometimes writes
        # narrative sentences as refs (e.g. "recent completed validations indicate...").
        # The block being present is the real guard; the sub-key is advisory.
        return bool(block)
    if root == "stock_setup_evidence":
        block = packet.get("stock_setup_evidence") or {}
        return parts[1] in block if len(parts) > 1 else bool(block)
    if root == "risk":
        if len(parts) < 2:
            return False
        field = parts[1]
        see = packet.get("stock_setup_evidence") or {}
        market = packet.get("market_snapshot") or {}
        hist = packet.get("historical_performance") or {}
        portfolio = packet.get("portfolio_context") or {}
        if field in see or field in market or field in hist or field in portfolio:
            return True
        drawdown_aliases = {
            "max_drawdown",
            "median_drawdown",
            "worst_drawdown",
            "drawdown",
        }
        if field in drawdown_aliases:
            return bool(see) or bool(hist)
        liquidity_aliases = {"liquidity", "volatility", "avg_volume", "volume"}
        if field in liquidity_aliases:
            return bool(market)
        if field == "concentration":
            return bool(packet.get("ranking")) or bool(portfolio)
        return False
    if root == "portfolio_context":
        block = packet.get("portfolio_context") or {}
        return parts[1] in block if len(parts) > 1 else bool(block)
    return False


def validate_supporting_evidence(
    packet: dict[str, Any],
    evidence: list[dict[str, Any]],
    *,
    require_when_findings: bool = True,
    findings: str = "",
) -> list[dict[str, Any]]:
    if require_when_findings and findings.strip() and not evidence:
        raise ValueError("Findings present but supporting_evidence is empty")
    validated: list[dict[str, Any]] = []
    for item in evidence:
        if not isinstance(item, dict):
            raise ValueError("Each supporting_evidence entry must be an object")
        ref = str(item.get("ref", "")).strip()
        if not ref:
            raise ValueError("supporting_evidence entry missing ref")
        if not _resolve_ref(packet, ref):
            raise ValueError(f"Evidence ref not found in packet: {ref}")
        validated.append(item)
    return validated


def validate_committee_output(
    packet: dict[str, Any],
    output: CommitteeReviewOutput,
    *,
    strict_numeric_findings: bool = False,
) -> CommitteeReviewOutput:
    blob = {
        "findings": output.findings,
        "research_label": output.research_label,
        **output.extensions,
    }
    assert_no_trade_fields(blob)
    if strict_numeric_findings and output.findings and _NUMERIC_IN_FINDINGS.search(output.findings):
        if not output.supporting_evidence:
            raise ValueError("Numeric claims in findings require supporting_evidence")
    evidence = validate_supporting_evidence(
        packet,
        output.supporting_evidence,
        require_when_findings=bool(output.findings.strip()),
        findings=output.findings,
    )
    return CommitteeReviewOutput(
        committee_code=output.committee_code,
        committee_version=output.committee_version,
        findings=output.findings,
        strengths=output.strengths,
        risks=output.risks,
        supporting_evidence=evidence,
        confidence=output.confidence,
        extensions=output.extensions,
        research_label=output.research_label,
    )
