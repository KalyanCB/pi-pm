import pytest

from app.core.constants import SymbolKind
from app.core.symbols import classify_symbol, validate_ingest_symbol


@pytest.mark.parametrize(
    ("symbol", "expected"),
    [
        ("RELIANCE.NS", SymbolKind.EQUITY),
        ("HAL.NS", SymbolKind.EQUITY),
        ("^NSEI", SymbolKind.INDEX),
        ("^NSEBANK", SymbolKind.INDEX),
        ("^CNXAUTO", SymbolKind.INDEX),
    ],
)
def test_classify_symbol_valid(symbol: str, expected: SymbolKind) -> None:
    assert classify_symbol(symbol) == expected


@pytest.mark.parametrize(
    "symbol",
    ["^", "BAD^SYM", "", "   "],
)
def test_classify_symbol_invalid(symbol: str) -> None:
    assert classify_symbol(symbol) == SymbolKind.UNKNOWN


def test_validate_ingest_symbol_index() -> None:
    assert validate_ingest_symbol("^NSEI") == "^NSEI"
    assert validate_ingest_symbol("  ^nsebank  ") == "^NSEBANK"


def test_validate_ingest_symbol_equity() -> None:
    assert validate_ingest_symbol("reliance.ns") == "RELIANCE.NS"


@pytest.mark.parametrize("symbol", ["^", "BAD^SYM", ""])
def test_validate_ingest_symbol_rejects_invalid(symbol: str) -> None:
    with pytest.raises(ValueError, match="Invalid symbol format"):
        validate_ingest_symbol(symbol)
