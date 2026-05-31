from __future__ import annotations

import csv
import io
import urllib.request
from dataclasses import dataclass
from pathlib import Path

NSE_NIFTY500_CSV_URL = (
    "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
)
DEFAULT_NIFTY500_CSV_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "nifty500_constituents.csv"
)


@dataclass(frozen=True)
class Nifty500Constituent:
    yahoo_symbol: str
    nse_symbol: str
    company_name: str
    industry: str


def to_yahoo_symbol(nse_symbol: str) -> str:
    return f"{nse_symbol.strip().upper()}.NS"


def _parse_csv_text(text: str) -> list[Nifty500Constituent]:
    reader = csv.DictReader(io.StringIO(text))
    constituents: list[Nifty500Constituent] = []
    for row in reader:
        nse_symbol = (row.get("Symbol") or "").strip()
        if not nse_symbol:
            continue
        constituents.append(
            Nifty500Constituent(
                yahoo_symbol=to_yahoo_symbol(nse_symbol),
                nse_symbol=nse_symbol.upper(),
                company_name=(row.get("Company Name") or nse_symbol).strip(),
                industry=(row.get("Industry") or "").strip(),
            )
        )
    return constituents


def load_nifty500_constituents(path: Path | None = None) -> list[Nifty500Constituent]:
    csv_path = path or DEFAULT_NIFTY500_CSV_PATH
    text = csv_path.read_text(encoding="utf-8")
    return _parse_csv_text(text)


def fetch_nifty500_constituents(url: str = NSE_NIFTY500_CSV_URL) -> list[Nifty500Constituent]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/csv,*/*",
            "Referer": "https://www.nseindia.com/",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        text = response.read().decode("utf-8")
    return _parse_csv_text(text)
