from __future__ import annotations

import csv
import io
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

DEFAULT_NIFTY1000_CSV_PATH = DATA_DIR / "nifty1000_constituents.csv"


@dataclass(frozen=True)
class IndexConstituent:
    yahoo_symbol: str
    nse_symbol: str
    company_name: str
    industry: str


def to_yahoo_symbol(nse_symbol: str) -> str:
    return f"{nse_symbol.strip().upper()}.NS"


def parse_nse_index_csv(text: str) -> list[IndexConstituent]:
    reader = csv.DictReader(io.StringIO(text))
    constituents: list[IndexConstituent] = []
    for row in reader:
        nse_symbol = (row.get("Symbol") or "").strip()
        if not nse_symbol:
            continue
        constituents.append(
            IndexConstituent(
                yahoo_symbol=to_yahoo_symbol(nse_symbol),
                nse_symbol=nse_symbol.upper(),
                company_name=(row.get("Company Name") or nse_symbol).strip(),
                industry=(row.get("Industry") or "").strip(),
            )
        )
    return constituents


def load_index_constituents(path: Path) -> list[IndexConstituent]:
    return parse_nse_index_csv(Path(path).read_text(encoding="utf-8"))


def fetch_index_constituents(url: str) -> list[IndexConstituent]:
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
    return parse_nse_index_csv(text)


def load_nifty1000_constituents(path: Path | None = None) -> list[IndexConstituent]:
    return load_index_constituents(path or DEFAULT_NIFTY1000_CSV_PATH)
