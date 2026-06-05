from __future__ import annotations

from pathlib import Path

from app.universe.nse_index_loader import (
    IndexConstituent as Nifty500Constituent,
)
from app.universe.nse_index_loader import (
    fetch_index_constituents,
    load_index_constituents,
    to_yahoo_symbol,
)

NSE_NIFTY500_CSV_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
DEFAULT_NIFTY500_CSV_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "nifty500_constituents.csv"
)

__all__ = [
    "DEFAULT_NIFTY500_CSV_PATH",
    "NSE_NIFTY500_CSV_URL",
    "Nifty500Constituent",
    "fetch_nifty500_constituents",
    "load_nifty500_constituents",
    "to_yahoo_symbol",
]


def load_nifty500_constituents(path: Path | None = None) -> list[Nifty500Constituent]:
    return load_index_constituents(path or DEFAULT_NIFTY500_CSV_PATH)


def fetch_nifty500_constituents(url: str = NSE_NIFTY500_CSV_URL) -> list[Nifty500Constituent]:
    return fetch_index_constituents(url)
