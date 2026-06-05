"""Committee-scoped evidence validation and abstention templates (Phase 2)."""

from __future__ import annotations

from typing import Any

from app.args.analytics.committee_effectiveness import evidence_refs
from app.workspace_args.committee_contracts import CommitteeReviewOutput

COMMITTEE_EVIDENCE_PREFIXES: dict[str, tuple[str, ...]] = {
    "TARC": ("ranking:", "technical_factors:", "technical:", "historical_performance:"),
    "QRC": (
        "validation:",
        "quant_evidence:",
        "regime:",
        "stock_setup_evidence:",
        "historical_validation",
        "historical_validation_context:",
    ),
    "NRCC": ("news_snapshot:", "research_context:"),
    "FRC": ("fundamental:", "fundamental_snapshot:"),
    "RC": (
        "risk:",
        "stock_setup_evidence:",
        "regime:",
        "market_snapshot:",
        "portfolio_context:",
    ),
}

_SHARED_GENERIC_REFS = frozenset(
    {
        "ranking:rank",
        "ranking:composite_score",
        "regime:regime_label",
    }
)


def ref_matches_committee_allowlist(ref: str, committee_code: str) -> bool:
    prefixes = COMMITTEE_EVIDENCE_PREFIXES.get(committee_code, ())
    return any(ref.startswith(prefix) or ref == prefix.rstrip(":") for prefix in prefixes)


def ref_unique_to_committee(ref: str, committee_code: str) -> bool:
    """True when ref is in this committee's scope but not any peer committee's scope."""
    if not ref_matches_committee_allowlist(ref, committee_code):
        return False
    for peer_code, prefixes in COMMITTEE_EVIDENCE_PREFIXES.items():
        if peer_code == committee_code:
            continue
        if any(ref.startswith(prefix) or ref == prefix.rstrip(":") for prefix in prefixes):
            return False
    return True


def validate_committee_evidence_scope(
    committee_code: str,
    evidence: list[dict[str, Any]],
) -> tuple[bool, str]:
    """Return (ok, reason). Checks allowlist + at least one committee-unique ref."""
    refs = evidence_refs(evidence)
    if not refs:
        return False, "no supporting_evidence refs"

    out_of_scope = [r for r in refs if not ref_matches_committee_allowlist(r, committee_code)]
    if out_of_scope:
        return False, f"refs outside {committee_code} mandate: {', '.join(sorted(out_of_scope))}"

    unique_refs = [r for r in refs if ref_unique_to_committee(r, committee_code)]
    if unique_refs:
        return True, ""

    # All refs are shared across committee mandates (e.g. only regime:regime_label).
    only_generic = refs <= _SHARED_GENERIC_REFS
    if only_generic or not unique_refs:
        return False, "no committee-unique evidence ref in mandate scope"
    return True, ""


def build_evidence_repair_prompt(reason: str) -> str:
    return (
        "Previous answer failed evidence scope validation. "
        f"Reason: {reason}. "
        "Cite at least 3 supporting_evidence refs within your committee mandate, "
        "including at least one ref unique to your committee (not shared with TARC/QRC/FRC/NRCC/RC). "
        "Include contrarian_view disagreeing with another committee's likely conclusion."
    )


def build_frc_abstention(
    *, committee_code: str, committee_version: str, symbol: str
) -> CommitteeReviewOutput:
    return CommitteeReviewOutput(
        committee_code=committee_code,
        committee_version=committee_version,
        findings=(
            f"Insufficient fundamental evidence for {symbol}. "
            "The packet contains no usable fundamental_snapshot fields (profitability, balance sheet, "
            "earnings trajectory, or valuation). FRC abstains from imputing business quality from "
            "technical rank or regime labels."
        ),
        strengths=[
            "Fundamental mandate boundary preserved — no ranking/regime filler.",
            "Explicit insufficient-evidence disclosure for CRO weighting.",
            "Abstention avoids clone degraded templates shared with RC.",
        ],
        risks=[
            "Business quality cannot be assessed from available packet fields.",
            "CRO must down-weight the fundamental leg for this symbol.",
            "Re-run when fundamental_snapshot enrichment is available.",
        ],
        supporting_evidence=[
            {"ref": "fundamental_snapshot:status", "note": "no fundamental data"},
            {"ref": "fundamental:status", "note": "mandate boundary"},
            {"ref": "fundamental_snapshot:status", "note": "abstention marker"},
        ],
        confidence=0.15,
        extensions={
            "abstention": True,
            "fundamental_evidence_status": "insufficient",
            "contrarian_view": (
                "TARC/QRC constructive signals cannot be confirmed without fundamental evidence."
            ),
        },
        research_label="neutral",
    )


def build_nrcc_no_news_abstention(
    *, committee_code: str, committee_version: str, symbol: str
) -> CommitteeReviewOutput:
    return CommitteeReviewOutput(
        committee_code=committee_code,
        committee_version=committee_version,
        findings=(
            f"No news evidence available for {symbol}. "
            "news_snapshot contains no items and no actionable catalyst headlines. "
            "NRCC abstains from macro, sector, or event-driven claims."
        ),
        strengths=[
            "News mandate boundary preserved — no invented catalysts.",
            "Structured absence reported with news_snapshot:status only.",
            "Abstention avoids ranking/composite score echo.",
        ],
        risks=[
            "Unobserved headline or event risk may exist outside the packet feed.",
            "Catalyst timing cannot be assessed without news items.",
            "Confidence capped due to missing news evidence.",
        ],
        supporting_evidence=[
            {"ref": "news_snapshot:status", "note": "feed unavailable"},
            {"ref": "news_snapshot:status", "note": "no items"},
            {"ref": "news_snapshot:status", "note": "abstention"},
        ],
        confidence=0.22,
        extensions={
            "abstention": True,
            "news_evidence_status": "no_news_evidence",
            "contrarian_view": (
                "Constructive technical/quant signals lack corroborating news or catalyst evidence."
            ),
        },
        research_label="neutral",
    )


def build_rc_insufficient_abstention(
    *, committee_code: str, committee_version: str, symbol: str
) -> CommitteeReviewOutput:
    return CommitteeReviewOutput(
        committee_code=committee_code,
        committee_version=committee_version,
        findings=(
            f"Insufficient risk evidence for {symbol}. "
            "RC cannot quantify drawdown, liquidity, or concentration risk from the scoped packet view. "
            "Abstaining from generic ranking/regime clone prose."
        ),
        strengths=[
            "Risk mandate boundary preserved — no TARC-style bullish factor promotion.",
            "Explicit insufficient-evidence disclosure for CRO.",
            "Abstention avoids FRC/RC degraded template clones.",
        ],
        risks=[
            "Drawdown and liquidity stack cannot be verified from available fields.",
            "High technical rank may overstate risk-adjusted attractiveness.",
            "CRO should treat risk leg as unverified for this symbol.",
        ],
        supporting_evidence=[
            {"ref": "portfolio_context:existing_position", "note": "minimal risk context"},
            {"ref": "risk:concentration", "note": "rank-only context"},
            {"ref": "market_snapshot:sector", "note": "liquidity proxy"},
        ],
        confidence=0.18,
        extensions={
            "abstention": True,
            "risk_evidence_status": "insufficient",
            "contrarian_view": (
                "Strong rank signals should be treated cautiously until drawdown and liquidity are evidenced."
            ),
        },
        research_label="neutral",
    )


def build_evidence_validation_failed_output(
    *,
    committee_code: str,
    committee_version: str,
    symbol: str,
    reason: str,
) -> CommitteeReviewOutput:
    return CommitteeReviewOutput(
        committee_code=committee_code,
        committee_version=committee_version,
        findings=(
            f"{committee_code} evidence validation failed for {symbol}: {reason}. "
            "Output degraded with committee-specific abstention — not a ranking/regime clone."
        ),
        strengths=[
            "Evidence scope validator rejected out-of-mandate or non-unique refs.",
            "Committee-specific abstention preserves independence boundaries.",
            "CRO should discount this committee leg pending rerun.",
        ],
        risks=[
            "supporting_evidence did not meet Phase 2 uniqueness requirements.",
            "Narrative may under-represent committee mandate without valid refs.",
            "Rerun recommended with mandate-scoped evidence citations.",
        ],
        supporting_evidence=[
            {"ref": "stub:evidence_validation_failed", "note": reason},
            {"ref": "stub:evidence_validation_failed", "note": "scope failure"},
            {"ref": "stub:evidence_validation_failed", "note": "abstention"},
        ],
        confidence=0.20,
        extensions={
            "abstention": True,
            "evidence_validation_failed": True,
            "evidence_validation_reason": reason,
            "contrarian_view": (
                "Peer committee conclusions should be treated skeptically until mandate-scoped evidence is cited."
            ),
        },
        research_label="neutral",
    )
