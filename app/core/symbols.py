from __future__ import annotations

import re

from app.core.constants import (
    EQUITY_SYMBOL_PATTERN,
    INDEX_SYMBOL_PATTERN,
    SymbolKind,
)


def normalize_symbol(value: str) -> str:
    return value.strip().upper()


def classify_symbol(symbol: str) -> SymbolKind:
    normalized = normalize_symbol(symbol)
    if not normalized:
        return SymbolKind.UNKNOWN
    if re.match(EQUITY_SYMBOL_PATTERN, normalized):
        return SymbolKind.EQUITY
    if re.match(INDEX_SYMBOL_PATTERN, normalized):
        return SymbolKind.INDEX
    return SymbolKind.UNKNOWN


def validate_ingest_symbol(raw: str) -> str:
    symbol = normalize_symbol(raw)
    kind = classify_symbol(symbol)
    if kind not in (SymbolKind.EQUITY, SymbolKind.INDEX):
        raise ValueError(f"Invalid symbol format: {raw}")
    return symbol
