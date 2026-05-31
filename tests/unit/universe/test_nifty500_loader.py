from pathlib import Path

from app.universe.nifty500_loader import (
    load_nifty500_constituents,
    to_yahoo_symbol,
)


def test_to_yahoo_symbol() -> None:
    assert to_yahoo_symbol("reliance") == "RELIANCE.NS"


def test_load_sample_fixture() -> None:
    path = Path(__file__).resolve().parents[2] / "fixtures" / "nifty500_sample.csv"
    constituents = load_nifty500_constituents(path)
    assert len(constituents) == 3
    assert constituents[0].yahoo_symbol == "RELIANCE.NS"
    assert constituents[0].company_name == "Reliance Industries Ltd."


def test_load_bundled_nifty500_csv() -> None:
    constituents = load_nifty500_constituents()
    assert len(constituents) >= 500
    assert all(item.yahoo_symbol.endswith(".NS") for item in constituents)
