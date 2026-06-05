#!/usr/bin/env python3
"""Validate Alembic migration chain integrity.

Exit codes:
  0 — single head, revision graph is consistent
  1 — validation failure
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REVISION_PATTERN = re.compile(r'^revision:\s*str\s*=\s*"([^"]+)"', re.MULTILINE)


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _check_duplicate_revisions() -> list[str]:
    versions_dir = Path(__file__).resolve().parent.parent / "migrations" / "versions"
    seen: dict[str, str] = {}
    duplicates: list[str] = []

    for path in sorted(versions_dir.glob("*.py")):
        content = path.read_text(encoding="utf-8")
        match = REVISION_PATTERN.search(content)
        if not match:
            continue
        revision = match.group(1)
        if revision in seen:
            duplicates.append(f"{revision} in {seen[revision]} and {path.name}")
        else:
            seen[revision] = path.name

    return duplicates


def main() -> int:
    duplicates = _check_duplicate_revisions()
    if duplicates:
        print("ERROR: Duplicate migration revision IDs detected:")
        for item in duplicates:
            print(f"  - {item}")
        return 1

    heads = _run(["alembic", "heads"])
    if heads.returncode != 0:
        print(heads.stderr or heads.stdout)
        return 1

    head_lines = [line.strip() for line in heads.stdout.splitlines() if line.strip()]
    revision_heads = [line.split()[0] for line in head_lines if "(head)" in line]

    if not revision_heads:
        print("ERROR: No migration heads found")
        return 1

    if len(revision_heads) > 1:
        print(f"ERROR: Multiple migration heads detected: {revision_heads}")
        return 1

    print(f"OK: Single migration head — {revision_heads[0]}")

    history = _run(["alembic", "history", "-v"])
    if history.returncode != 0:
        print(history.stderr or history.stdout)
        return 1

    print("OK: Migration history is readable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
