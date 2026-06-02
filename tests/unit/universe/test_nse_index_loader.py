from pathlib import Path

from app.universe.nse_index_loader import (
    load_index_constituents,
    load_nifty1000_constituents,
    parse_nse_index_csv,
    to_yahoo_symbol,
)

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "nifty1000_sample.csv"


def test_to_yahoo_symbol() -> None:
    assert to_yahoo_symbol(" reliance ") == "RELIANCE.NS"


def test_parse_skips_blank_symbol_rows() -> None:
    text = "Company Name,Industry,Symbol\nFoo Ltd.,Tech,FOO\nBar Ltd.,Tech,\n"
    constituents = parse_nse_index_csv(text)
    assert len(constituents) == 1
    assert constituents[0].yahoo_symbol == "FOO.NS"


def test_load_sample_fixture() -> None:
    constituents = load_index_constituents(FIXTURE)
    assert len(constituents) == 4
    assert constituents[0].yahoo_symbol == "RELIANCE.NS"
    assert constituents[0].company_name == "Reliance Industries Ltd."
    assert all(item.yahoo_symbol.endswith(".NS") for item in constituents)


def test_load_bundled_nifty1000_csv() -> None:
    constituents = load_nifty1000_constituents()
    assert len(constituents) >= 1000
    assert all(item.yahoo_symbol.endswith(".NS") for item in constituents)
    symbols = [c.nse_symbol for c in constituents]
    assert len(symbols) == len(set(symbols))
