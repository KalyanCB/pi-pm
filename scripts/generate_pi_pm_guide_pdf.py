#!/usr/bin/env python3
"""Render docs/pi-pm-complete-guide.html to PDF (Mermaid via browser)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = REPO_ROOT / "docs" / "pi-pm-complete-guide.html"
PDF_PATH = REPO_ROOT / "docs" / "Pi-PM-Complete-Guide.pdf"


def main() -> int:
    if not HTML_PATH.is_file():
        print(f"Missing guide HTML: {HTML_PATH}", file=sys.stderr)
        return 1

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "playwright not installed. Run:\n"
            "  pip install playwright\n"
            "  playwright install chromium",
            file=sys.stderr,
        )
        return 1

    file_url = HTML_PATH.resolve().as_uri()
    PDF_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(file_url, wait_until="networkidle")
        # Allow Mermaid diagrams to finish layout
        page.wait_for_timeout(4000)
        page.pdf(
            path=str(PDF_PATH),
            format="A4",
            print_background=True,
            margin={"top": "14mm", "bottom": "14mm", "left": "12mm", "right": "12mm"},
        )
        browser.close()

    print(f"Wrote {PDF_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
