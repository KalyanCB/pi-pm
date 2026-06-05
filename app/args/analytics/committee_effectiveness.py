from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.args import CommitteeReview, CroReview, ResearchRun

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "was",
        "with",
    }
)


@dataclass(frozen=True)
class CommitteeReviewSnapshot:
    committee_code: str
    symbol: str
    packet_id: str
    findings: str
    strengths: list[str]
    risks: list[str]
    supporting_evidence: list[dict[str, Any]]
    confidence: float | None

    @classmethod
    def from_row(cls, review: CommitteeReview, *, symbol: str) -> CommitteeReviewSnapshot:
        return cls(
            committee_code=review.committee_code,
            symbol=symbol,
            packet_id=str(review.packet_id),
            findings=review.findings or "",
            strengths=[str(s) for s in (review.strengths or [])],
            risks=[str(r) for r in (review.risks or [])],
            supporting_evidence=list(review.supporting_evidence or []),
            confidence=float(review.confidence) if review.confidence is not None else None,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CommitteeReviewSnapshot:
        return cls(
            committee_code=str(data["committee_code"]),
            symbol=str(data.get("symbol", "")),
            packet_id=str(data.get("packet_id", "")),
            findings=str(data.get("findings", "")),
            strengths=[str(s) for s in (data.get("strengths") or [])],
            risks=[str(r) for r in (data.get("risks") or [])],
            supporting_evidence=list(data.get("supporting_evidence") or []),
            confidence=(float(data["confidence"]) if data.get("confidence") is not None else None),
        )


def tokenize_text(*parts: str) -> set[str]:
    tokens: set[str] = set()
    for part in parts:
        for match in _TOKEN_RE.finditer(part.lower()):
            tok = match.group(0)
            if len(tok) > 2 and tok not in _STOPWORDS:
                tokens.add(tok)
    return tokens


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def sequence_similarity_ratio(a: str, b: str) -> float:
    """Lightweight character-level similarity (no embeddings)."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if not longer:
        return 1.0
    matches = sum(1 for i, ch in enumerate(shorter) if i < len(longer) and ch == longer[i])
    return (2.0 * matches) / (len(a) + len(b))


def evidence_refs(evidence: list[dict[str, Any]]) -> set[str]:
    refs: set[str] = set()
    for item in evidence:
        if isinstance(item, dict):
            ref = item.get("ref") or item.get("evidence_ref") or item.get("id")
            if ref:
                refs.add(str(ref))
        elif item:
            refs.add(str(item))
    return refs


def review_text_tokens(review: CommitteeReviewSnapshot) -> set[str]:
    return tokenize_text(
        review.findings,
        " ".join(review.strengths),
        " ".join(review.risks),
    )


def strength_tokens(review: CommitteeReviewSnapshot) -> set[str]:
    return tokenize_text(" ".join(review.strengths))


def risk_tokens(review: CommitteeReviewSnapshot) -> set[str]:
    return tokenize_text(" ".join(review.risks))


def compute_committee_uniqueness_score(
    review: CommitteeReviewSnapshot | dict[str, Any],
    peer_reviews: list[CommitteeReviewSnapshot | dict[str, Any]],
) -> dict[str, float | int]:
    """Read-only uniqueness vs peer committees on the same packet."""
    if isinstance(review, dict):
        review = CommitteeReviewSnapshot.from_dict(review)
    peers = [
        CommitteeReviewSnapshot.from_dict(p) if isinstance(p, dict) else p
        for p in peer_reviews
        if (CommitteeReviewSnapshot.from_dict(p) if isinstance(p, dict) else p).committee_code
        != review.committee_code
    ]

    review_tokens = review_text_tokens(review)
    review_refs = evidence_refs(review.supporting_evidence)
    peer_token_union: set[str] = set()
    peer_ref_union: set[str] = set()
    overlaps: list[float] = []

    for peer in peers:
        peer_tokens = review_text_tokens(peer)
        peer_token_union |= peer_tokens
        peer_ref_union |= evidence_refs(peer.supporting_evidence)
        overlaps.append(jaccard_similarity(review_tokens, peer_tokens))

    unique_tokens = review_tokens - peer_token_union
    unique_refs = review_refs - peer_ref_union

    overlap_with_other_committees = mean(overlaps) if overlaps else 0.0
    unique_findings_count = len(unique_tokens)
    unique_evidence_count = len(unique_refs)

    token_uniqueness = len(unique_tokens) / len(review_tokens) if review_tokens else 0.0
    evidence_uniqueness = len(unique_refs) / len(review_refs) if review_refs else 0.0
    overlap_penalty = 1.0 - overlap_with_other_committees
    composite = 0.45 * overlap_penalty + 0.35 * token_uniqueness + 0.20 * evidence_uniqueness
    composite = max(0.0, min(1.0, composite))

    return {
        "committee_code": review.committee_code,
        "overlap_with_other_committees": round(overlap_with_other_committees, 4),
        "unique_findings_count": unique_findings_count,
        "unique_evidence_count": unique_evidence_count,
        "composite_uniqueness": round(composite, 4),
    }


def compute_packet_metrics(
    reviews: list[CommitteeReviewSnapshot],
) -> dict[str, Any]:
    """Aggregate overlap / clustering / disagreement for one packet."""
    if not reviews:
        return {
            "committee_count": 0,
            "mean_finding_jaccard": 0.0,
            "mean_evidence_overlap": 0.0,
            "mean_strength_risk_jaccard": 0.0,
            "confidence_std": 0.0,
            "confidence_unique_values": 0,
            "mean_composite_uniqueness": 0.0,
            "agreement_echo_score": 0.0,
            "disagreement_score": 0.0,
            "has_cross_committee_contradiction": False,
        }

    tokens_by_code = {r.committee_code: review_text_tokens(r) for r in reviews}
    refs_by_code = {r.committee_code: evidence_refs(r.supporting_evidence) for r in reviews}
    strengths_by_code = {r.committee_code: strength_tokens(r) for r in reviews}
    risks_by_code = {r.committee_code: risk_tokens(r) for r in reviews}

    codes = list(tokens_by_code.keys())
    finding_jaccards: list[float] = []
    evidence_overlaps: list[float] = []
    strength_risk_jaccards: list[float] = []

    for i, code_a in enumerate(codes):
        for code_b in codes[i + 1 :]:
            finding_jaccards.append(
                jaccard_similarity(tokens_by_code[code_a], tokens_by_code[code_b])
            )
            refs_a, refs_b = refs_by_code[code_a], refs_by_code[code_b]
            if refs_a or refs_b:
                evidence_overlaps.append(jaccard_similarity(refs_a, refs_b))
            strength_risk_jaccards.append(
                jaccard_similarity(strengths_by_code[code_a], risks_by_code[code_b])
            )
            strength_risk_jaccards.append(
                jaccard_similarity(strengths_by_code[code_b], risks_by_code[code_a])
            )

    confidences = [r.confidence for r in reviews if r.confidence is not None]
    confidence_std = pstdev(confidences) if len(confidences) > 1 else 0.0
    confidence_unique = len({round(c, 2) for c in confidences})

    uniqueness_scores = [
        compute_committee_uniqueness_score(
            r, [p for p in reviews if p.committee_code != r.committee_code]
        )["composite_uniqueness"]
        for r in reviews
    ]

    mean_finding_jaccard = mean(finding_jaccards) if finding_jaccards else 0.0
    mean_evidence_overlap = mean(evidence_overlaps) if evidence_overlaps else 0.0
    mean_strength_risk_jaccard = mean(strength_risk_jaccards) if strength_risk_jaccards else 0.0

    # Thematic opposition: one committee's strengths barely overlap another's risks.
    has_contradiction = any(
        jaccard_similarity(strengths_by_code[a], risks_by_code[b]) < 0.08
        for a in codes
        for b in codes
        if a != b
    )

    mean_uniqueness = mean(uniqueness_scores)
    # Agreement echo: shared citations + similar language + cloned fallback bullets.
    agreement_echo = min(
        1.0,
        0.45 * mean_evidence_overlap + 0.30 * mean_finding_jaccard + 0.25 * (1.0 - mean_uniqueness),
    )
    disagreement_score = round(1.0 - agreement_echo, 4)

    return {
        "committee_count": len(reviews),
        "mean_finding_jaccard": round(mean_finding_jaccard, 4),
        "mean_evidence_overlap": round(mean_evidence_overlap, 4),
        "mean_strength_risk_jaccard": round(mean_strength_risk_jaccard, 4),
        "confidence_std": round(confidence_std, 4),
        "confidence_unique_values": confidence_unique,
        "mean_composite_uniqueness": round(mean_uniqueness, 4),
        "agreement_echo_score": round(agreement_echo, 4),
        "disagreement_score": disagreement_score,
        "has_cross_committee_contradiction": has_contradiction,
        "per_committee_uniqueness": {
            r.committee_code: compute_committee_uniqueness_score(
                r, [p for p in reviews if p.committee_code != r.committee_code]
            )
            for r in reviews
        },
    }


def load_research_run_reviews(
    db: Session, research_run_id: UUID
) -> tuple[ResearchRun, dict[str, list[CommitteeReviewSnapshot]], list[CroReview]]:
    run = db.scalar(
        select(ResearchRun)
        .where(ResearchRun.id == research_run_id)
        .options(
            selectinload(ResearchRun.packets),
            selectinload(ResearchRun.committee_reviews),
            selectinload(ResearchRun.cro_reviews),
        )
    )
    if run is None:
        raise ValueError(f"Research run not found: {research_run_id}")

    symbol_by_packet = {p.id: p.symbol for p in run.packets}
    by_packet: dict[str, list[CommitteeReviewSnapshot]] = defaultdict(list)
    for review in run.committee_reviews:
        symbol = symbol_by_packet.get(review.packet_id, "")
        by_packet[str(review.packet_id)].append(
            CommitteeReviewSnapshot.from_row(review, symbol=symbol)
        )
    return run, dict(by_packet), list(run.cro_reviews)


def summarize_run_metrics(
    by_packet: dict[str, list[CommitteeReviewSnapshot]],
    *,
    disagreement_threshold: float = 0.55,
) -> dict[str, Any]:
    packet_metrics = [compute_packet_metrics(reviews) for reviews in by_packet.values()]
    if not packet_metrics:
        return {"packet_count": 0, "headline_disagreement_rate": 0.0}

    disagreement_flags = [m["disagreement_score"] >= disagreement_threshold for m in packet_metrics]
    all_refs: list[set[str]] = []
    ref_counts: dict[str, int] = defaultdict(int)
    for reviews in by_packet.values():
        for review in reviews:
            refs = evidence_refs(review.supporting_evidence)
            all_refs.append(refs)
            for ref in refs:
                ref_counts[ref] += 1

    total_reviews = sum(len(r) for r in by_packet.values())
    degraded_markers = sum(
        1
        for reviews in by_packet.values()
        for r in reviews
        if "degraded fallback" in r.findings.lower()
    )

    return {
        "packet_count": len(packet_metrics),
        "review_count": total_reviews,
        "mean_finding_jaccard": round(mean(m["mean_finding_jaccard"] for m in packet_metrics), 4),
        "mean_evidence_overlap": round(mean(m["mean_evidence_overlap"] for m in packet_metrics), 4),
        "mean_confidence_std": round(mean(m["confidence_std"] for m in packet_metrics), 4),
        "mean_composite_uniqueness": round(
            mean(m["mean_composite_uniqueness"] for m in packet_metrics), 4
        ),
        # Fraction of packets above disagreement threshold (default 0.55).
        "headline_disagreement_rate": round(sum(disagreement_flags) / len(disagreement_flags), 4),
        # Stricter bar for adversarial independence (evidence + narrative + non-clone).
        "strict_independence_packet_rate": round(
            sum(
                1
                for m in packet_metrics
                if m["disagreement_score"] >= 0.65 and m["mean_evidence_overlap"] < 0.5
            )
            / len(packet_metrics),
            4,
        ),
        "strict_independence_rate": round(
            sum(m["disagreement_score"] >= 0.65 for m in packet_metrics) / len(packet_metrics),
            4,
        ),
        "mean_disagreement_score": round(mean(m["disagreement_score"] for m in packet_metrics), 4),
        "mean_agreement_echo_score": round(
            mean(m["agreement_echo_score"] for m in packet_metrics), 4
        ),
        "effective_independence_rate": round(
            mean(m["mean_composite_uniqueness"] for m in packet_metrics)
            * (1.0 - mean(m["mean_evidence_overlap"] for m in packet_metrics))
            * (1.0 - (degraded_markers / total_reviews if total_reviews else 0.0)),
            4,
        ),
        "degraded_review_fraction": round(degraded_markers / total_reviews, 4)
        if total_reviews
        else 0.0,
        "top_shared_evidence_refs": sorted(ref_counts.items(), key=lambda x: (-x[1], x[0]))[:10],
        "per_packet": packet_metrics,
    }


def confidence_clustering_by_committee(
    by_packet: dict[str, list[CommitteeReviewSnapshot]],
) -> dict[str, dict[str, float | int]]:
    by_code: dict[str, list[float]] = defaultdict(list)
    for reviews in by_packet.values():
        for review in reviews:
            if review.confidence is not None:
                by_code[review.committee_code].append(review.confidence)

    out: dict[str, dict[str, float | int]] = {}
    for code, values in sorted(by_code.items()):
        rounded = [round(v, 2) for v in values]
        out[code] = {
            "count": len(values),
            "mean": round(mean(values), 4) if values else 0.0,
            "std": round(pstdev(values), 4) if len(values) > 1 else 0.0,
            "unique_rounded_values": len(set(rounded)),
        }
    return out
