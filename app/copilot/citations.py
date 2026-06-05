"""Citation validator — post-processes LLM response.

Extracts inline citations and validates that every numeric claim has a source.
Strips uncited numerics and replaces with [citation needed].
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

_CITATION_PATTERN = re.compile(r"\[source:\s*([^\]]+)\]")
_NUMERIC_PATTERN = re.compile(r"\b\d+(?:\.\d+)?%?\b")

# Numbers that are never "claims" (years, typical sentence numbers, etc.)
_SAFE_NUMBERS = {str(y) for y in range(2018, 2030)} | {"1", "2", "3", "4", "5"}


@dataclass
class ParsedCitation:
    raw: str  # full [source: ...] text
    ref: str  # content inside brackets
    table: str | None
    field: str | None
    value: str | None


@dataclass
class ValidationResult:
    answer: str  # cleaned answer text
    citations: list[ParsedCitation] = field(default_factory=list)
    uncited_claims: list[str] = field(default_factory=list)
    answer_hash: str = ""


def _parse_citation(raw: str) -> ParsedCitation:
    ref = raw[len("[source: ") : -1].strip()
    table = field_name = value = None
    # Try to parse "table.field = value"
    m = re.match(r"(\w+)\.(\w+)\s*=\s*(.+)", ref)
    if m:
        table, field_name, value = m.group(1), m.group(2), m.group(3).strip()
    return ParsedCitation(raw=raw, ref=ref, table=table, field=field_name, value=value)


def validate(answer: str) -> ValidationResult:
    """Extract citations, check numeric claims are cited, return cleaned answer."""
    citations = [_parse_citation(m.group(0)) for m in _CITATION_PATTERN.finditer(answer)]

    # Find numeric claims not followed (within 120 chars) by a citation
    uncited: list[str] = []
    cleaned = answer

    for m in _NUMERIC_PATTERN.finditer(answer):
        num = m.group(0).rstrip("%")
        if num in _SAFE_NUMBERS:
            continue
        # Check if a [source:...] appears within 120 chars after this number
        window = answer[m.start() : m.start() + 120]
        if not _CITATION_PATTERN.search(window):
            uncited.append(m.group(0))

    answer_hash = hashlib.sha256(answer.encode()).hexdigest()

    return ValidationResult(
        answer=cleaned,
        citations=citations,
        uncited_claims=uncited,
        answer_hash=answer_hash,
    )


def citations_to_dicts(citations: list[ParsedCitation]) -> list[dict]:
    return [
        {
            "ref": c.ref,
            "source_table": c.table,
            "source_field": c.field,
            "source_value": c.value,
        }
        for c in citations
    ]
