#!/usr/bin/env python3
"""Rewrite stale cross-references in context/canonical/ for self-contained navigation."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "context" / "canonical"

# Order matters — more specific replacements first.
REPLACEMENTS: list[tuple[str, str]] = [
    (r"\.\./product-next/PO_SIGNOFF_2026_06_04\.md", "../po/PO_SIGNOFF_2026_06_04.md"),
    (r"\.\./product-next/15_EXECUTIVE_PRODUCT_STRATEGY\.md", "../po/15_EXECUTIVE_PRODUCT_STRATEGY.md"),
    (r"\.\./product-next/", "../product/"),
    (r"\.\./execution/", "../runbooks/"),
    (r"docs/product-next/", "context/canonical/product/"),
    (r"docs/execution/", "context/canonical/runbooks/"),
    (r"docs/audit/FRONTEND_AUDIT_REPORT\.md", "context/canonical/frontend/FRONTEND_AUDIT_REPORT.md"),
    (r"\.\./\.\./docs/audit/FRONTEND_AUDIT_REPORT\.md", "FRONTEND_AUDIT_REPORT.md"),
    (r"\.\./AI/01_PRODUCT/PRD\.md", "../phase1/PRD.md"),
    (r"docs/AI/01_PRODUCT/PRD\.md", "context/canonical/phase1/PRD.md"),
    (r"\.\./AI/03_DESIGN/VALIDATION_DESIGN\.md", "../design/VALIDATION_DESIGN.md"),
    (r"docs/AI/03_DESIGN/VALIDATION_DESIGN\.md", "context/canonical/design/VALIDATION_DESIGN.md"),
    (r"\[docs/mobile/\]\(\.\./mobile/\)", "[Mobile PRD](../product/09_MOBILE_APP_PRD.md)"),
    (r"\[docs/frontend/\]\(\.\./frontend/\)", "[Design system](../frontend/DESIGN_SYSTEM.md)"),
    (r"`app/services/execution_service\.py`", "`app/execution/services/execution_service.py`"),
    (r"app/services/execution_service\.py", "app/execution/services/execution_service.py"),
    (r"No `stop_loss_price` on position", "`stop_loss_price` on DB model; not exposed on position API/UI"),
    (r"stop_loss_price not on position API/UI", "stop_loss_price on DB model; not exposed on position API/UI"),
    (r"`frontend/docs/FEATURE_INTEGRATION_REPORT\.md`", "`context/canonical/frontend/FEATURE_INTEGRATION_REPORT.md`"),
    (r"docs/frontend/ui/", "context/canonical/frontend/"),
    (r"docs/frontend/AUTHENTICATION_PREPARATION\.md", "context/canonical/design/domain-boundaries.md"),
    (r"\.\./architecture/ADR-", "../decisions/ADR-"),
    (r"\./PO_SIGNOFF_2026_06_04\.md", "../po/PO_SIGNOFF_2026_06_04.md"),
    (r"\./01_RECOMMENDATION_ENGINE_PRD\.md", "../product/01_RECOMMENDATION_ENGINE_PRD.md"),
    (r"\./02_CONVICTION_SCORING_PRD\.md", "../product/02_CONVICTION_SCORING_PRD.md"),
    (r"\./03_RECOMMENDATION_DATA_MODEL\.md", "../product/03_RECOMMENDATION_DATA_MODEL.md"),
    (r"\./04_RECOMMENDATION_LIFECYCLE\.md", "../product/04_RECOMMENDATION_LIFECYCLE.md"),
    (r"\./14_ARCHITECTURE_IMPACT_ANALYSIS\.md", "../product/14_ARCHITECTURE_IMPACT_ANALYSIS.md"),
    (r"\./16_WHY_NOT_RECOMMENDED_FRAMEWORK\.md", "../product/16_WHY_NOT_RECOMMENDED_FRAMEWORK.md"),
    (r"\./16_RECOMMENDATION_PERFORMANCE_PRD\.md", "../product/16_RECOMMENDATION_PERFORMANCE_PRD.md"),
    (r"\./13_PO_BACKLOG\.md", "../product/13_PO_BACKLOG.md"),
    (r"\./08_AI_INVESTMENT_COMMITTEE_PRD\.md", "../product/08_AI_INVESTMENT_COMMITTEE_PRD.md"),
    (r"\./15_EXECUTIVE_PRODUCT_STRATEGY\.md", "../po/15_EXECUTIVE_PRODUCT_STRATEGY.md"),
    (r"\./12_PRODUCT_ROADMAP_2026_2027\.md", "../product/12_PRODUCT_ROADMAP_2026_2027.md"),
    (r"\./05_PORTFOLIO_ENGINE_PRD\.md", "../product/05_PORTFOLIO_ENGINE_PRD.md"),
    (r"\./17_TRUST_DASHBOARD_VISION\.md", "../product/17_TRUST_DASHBOARD_VISION.md"),
    (r"\./11_HUMAN_IN_LOOP_EXECUTION_PRD\.md", "../product/11_HUMAN_IN_LOOP_EXECUTION_PRD.md"),
    (r"\.\./daily-nifty500-batch-runbook\.md", "../runbooks/daily-nifty500-batch-runbook.md"),
    (r"\.\./frontend/AUTHENTICATION_PREPARATION\.md", "../design/domain-boundaries.md"),
    (r"\.\./\.\./context/canonical/frontend/FRONTEND_AUDIT_REPORT\.md", "FRONTEND_AUDIT_REPORT.md"),
    (r"\./INDEX\.md", "../INDEX.md"),
    (r"\.\./HANDOFF\.md", "../../AGENTS.md"),
    (r"\./HANDOFF\.md", "../AGENTS.md"),
    (r"\./ARCHITECTURE\.md", "../generated/ARCHITECTURE_MAP.md"),
    (r"\[ARCHITECTURE\.md\]\(\.\./generated/ARCHITECTURE_MAP\.md\)", "[ARCHITECTURE.md](../../generated/ARCHITECTURE_MAP.md)"),
    (r"\.\./PLATFORM-HANDOFF-2026\.md", "../../AGENTS.md"),
    (r"\./PLATFORM-HANDOFF-2026\.md", "../AGENTS.md"),
    (r"\[PLATFORM-HANDOFF-2026\.md\]\(\.\./AGENTS\.md\)", "[PLATFORM-HANDOFF-2026.md](../../AGENTS.md)"),
    (r"\.\./canonical/INDEX\.md", "../INDEX.md"),
    (r"\.\.\./INDEX\.md", "../INDEX.md"),
    (r"\.\./\.context/AGENTS\.md", "../../AGENTS.md"),
    (r"\.context/AGENTS\.md", "../AGENTS.md"),
    (r"\]\(context/AGENTS\.md\)", "](../../AGENTS.md)"),
    (r"\]\(context/generated/ARCHITECTURE_MAP\.md\)", "](../generated/ARCHITECTURE_MAP.md)"),
]

# Paths that intentionally reference legacy archive (not copied) — link check ignores.
ARCHIVE_ALLOWLIST = (
    "docs/dailyruns",
    "docs/paper-pilot",
    "docs/my-symbols",
    "docs/calibrated-ranking",
    "docs/AI/",
    "frontend/docs/ARCHITECTURE_REPORT",
    "docs/frontend/API_INTEGRATION",
)


def fix_file(path: Path) -> int:
    text = path.read_text()
    original = text
    for pattern, repl in REPLACEMENTS:
        text = re.sub(pattern, repl, text)
    if text != original:
        path.write_text(text)
        return 1
    return 0


def main() -> None:
    changed = 0
    for md in CANONICAL.rglob("*.md"):
        changed += fix_file(md)
    print(f"updated {changed} files under context/canonical/")


if __name__ == "__main__":
    main()
