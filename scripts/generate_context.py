#!/usr/bin/env python3
"""Generate AI-friendly context pack under context/generated/.

Usage:
    uv run python scripts/generate_context.py
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / "context"
GENERATED = CONTEXT / "generated"
REGISTRY = CONTEXT / "registry" / "requirements.yaml"
API_DIR = ROOT / "app" / "api" / "v1"
MODELS_DIR = ROOT / "app" / "models"
FRONTEND_ROUTES = ROOT / "frontend" / "packages" / "navigation" / "src" / "routes.ts"
MIGRATIONS = ROOT / "migrations" / "versions"
CANONICAL = CONTEXT / "canonical"

# Legacy paths referenced in prose — not copied; link check treats as archived.
ARCHIVE_LINK_PREFIXES = (
    "docs/dailyruns",
    "docs/paper-pilot",
    "docs/my-symbols",
    "docs/calibrated-ranking",
    "docs/AI/",
    "docs/po-discovery",
    "docs/audit",
    "frontend/docs/ARCHITECTURE_REPORT",
    "docs/frontend/API_INTEGRATION",
    "../po-discovery/",
    "../AI/",
    "../outcome-attribution",
    "../ranking-calibration",
    "../score-compression",
    "../args-gap",
    "../ROADMAP.md",
    "../HANDOFF",
    "../PLATFORM-HANDOFF",
    "../sprint",
    "dailyruns/",
    "PRODUCT_STATUS",
    "GOVERNANCE_DESIGN",
    "EXIT_RESEARCH_DESIGN",
    "FACTOR_IC_DESIGN",
    "REGIME_DESIGN",
    "RANKING_DESIGN",
    "ARGS_DESIGN",
    "COMMITTEE_DESIGN",
    "SERVICE_MAP",
    "DATABASE_SCHEMA.md",
    "DOMAIN_MODEL",
)


def _run(cmd: list[str], cwd: Path = ROOT) -> str:
    try:
        return subprocess.check_output(cmd, cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def git_sha() -> str:
    return _run(["git", "rev-parse", "--short", "HEAD"]) or "unknown"


def git_branch() -> str:
    return _run(["git", "branch", "--show-current"]) or "unknown"


def alembic_head() -> str:
    heads = sorted(MIGRATIONS.glob("*.py"))
    if not heads:
        return "unknown"
    # Use lexicographically latest revision file as proxy when alembic CLI unavailable
    latest = heads[-1].stem
    return latest.split("_", 1)[0] if "_" in latest else latest


def test_count() -> int | None:
    out = _run(["uv", "run", "pytest", "tests/", "--co", "-q"])
    if not out:
        return None
    m = re.search(r"(\d+)\s+tests?\s+collected", out)
    return int(m.group(1)) if m else None


def file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def load_registry() -> dict:
    with REGISTRY.open() as f:
        return yaml.safe_load(f)


def verify_evidence(paths: list[str]) -> list[str]:
    found = []
    for p in paths:
        if (ROOT / p).exists():
            found.append(p)
    return found


def enrich_requirements(registry: dict) -> list[dict]:
    rows = []
    for req in registry.get("requirements", []):
        evidence = req.get("evidence") or []
        verified = verify_evidence(evidence)
        row = dict(req)
        row["evidence_verified"] = verified
        row["evidence_missing"] = [p for p in evidence if p not in verified]
        if not row.get("status"):
            row["status"] = "NOT_STARTED"
        rows.append(row)
    return rows


def scan_api_routes() -> list[dict]:
    routes: list[dict] = []
    pattern = re.compile(
        r'@router\.(get|post|put|patch|delete)\(\s*["\']([^"\']*)["\']',
        re.MULTILINE,
    )
    for path in sorted(API_DIR.glob("*.py")):
        text = path.read_text()
        module = path.stem
        for method, route in pattern.findall(text):
            routes.append({"module": module, "method": method.upper(), "path": route})
    return routes


def scan_tables() -> list[str]:
    return sorted({t["table"] for t in scan_model_details()})


def scan_model_details() -> list[dict]:
    """Parse SQLAlchemy models for table/column/FK detail without DB connection."""
    details: list[dict] = []
    fk_re = re.compile(r'ForeignKey\(\s*["\']([^"\']+)["\']')
    type_re = re.compile(r"(String|Numeric|Boolean|Date|DateTime|Integer|BigInteger|JSONB|UUID)")

    for path in sorted(MODELS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        text = path.read_text()
        class_splits = re.split(r"(?=^class \w+)", text, flags=re.MULTILINE)
        for chunk in class_splits:
            table_m = re.search(r'__tablename__\s*=\s*["\']([^"\']+)["\']', chunk)
            cls_m = re.match(r"class (\w+)", chunk)
            if not table_m or not cls_m:
                continue
            cls_name, table = cls_m.group(1), table_m.group(1)
            columns: list[dict] = []
            for col_m in re.finditer(r"(\w+):\s*Mapped\[", chunk):
                name = col_m.group(1)
                if name.startswith("_"):
                    continue
                snippet = chunk[col_m.start() : col_m.start() + 400]
                fk = fk_re.search(snippet)
                type_m = type_re.search(snippet)
                columns.append(
                    {
                        "name": name,
                        "type": type_m.group(1) if type_m else "other",
                        "fk": fk.group(1) if fk else None,
                    }
                )
            details.append(
                {
                    "model": cls_name,
                    "file": str(path.relative_to(ROOT)),
                    "table": table,
                    "columns": columns,
                }
            )
    return sorted(details, key=lambda d: d["table"])


def scan_frontend_hooks() -> list[str]:
    hooks_dir = ROOT / "frontend" / "packages" / "hooks" / "src" / "queries"
    if not hooks_dir.exists():
        return []
    return sorted(p.name for p in hooks_dir.glob("use*.ts"))


def export_openapi() -> dict | None:
    """Export FastAPI OpenAPI schema (offline, no running server)."""
    try:
        os.environ.setdefault(
            "DATABASE_URL", "postgresql+psycopg://pipm:pipm@localhost:5432/pipm"
        )
        os.environ.setdefault("AUTH_ENABLED", "false")
        sys.path.insert(0, str(ROOT))
        from app.main import app  # noqa: WPS433

        return app.openapi()
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc), "paths": {}}


def scan_env_catalog() -> list[dict]:
    """Settings fields from app/core/config.py + .env.example comments."""
    sys.path.insert(0, str(ROOT))
    from app.core.config import Settings  # noqa: WPS433

    fields = []
    for name, field in Settings.model_fields.items():
        env_key = name.upper()
        default = field.default
        if default is None and field.default_factory is not None:
            default = "<factory>"
        fields.append(
            {
                "field": name,
                "env": env_key,
                "default": default,
                "annotation": str(field.annotation).replace("typing.", ""),
            }
        )
    return fields


def scan_ops_scripts() -> list[dict]:
    """Index operational scripts with one-line purpose from module docstring."""
    scripts_dir = ROOT / "scripts"
    priority = [
        "run_daily_nifty500_batch.py",
        "replay_paper_trade.py",
        "replay_paper_trade_v2.py",
        "run_replay.py",
        "run_historical_committee_paper_pilot.py",
        "generate_context.py",
        "generate_pilot_reports.py",
        "run_walkforward.py",
        "backtest_all_strategies.py",
    ]
    entries: list[dict] = []
    for name in priority:
        path = scripts_dir / name
        if path.exists():
            entries.append(_script_entry(path))
    for path in sorted(scripts_dir.glob("*.py")):
        if path.name not in priority and path.name != "__init__.py":
            entries.append(_script_entry(path))
    return entries


def _script_entry(path: Path) -> dict:
    text = path.read_text()
    doc = ""
    try:
        tree = ast.parse(text)
        doc = (ast.get_docstring(tree) or "").split("\n")[0].strip()
    except SyntaxError:
        doc = ""
    return {"name": path.name, "path": str(path.relative_to(ROOT)), "purpose": doc or "—"}


def scan_ranking_strategies() -> dict:
    strategies_dir = ROOT / "app" / "ranking" / "strategies"
    strategies = []
    for path in sorted(strategies_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        name = path.stem
        strategies.append({"name": name, "module": str(path.relative_to(ROOT))})
    default = "momentum_v1"
    config = ROOT / "app" / "core" / "config.py"
    if config.exists():
        m = re.search(r'ranking_default_strategy:\s*str\s*=\s*"([^"]+)"', config.read_text())
        if m:
            default = m.group(1)
    return {"strategies": strategies, "default": default}


def scan_canonical_links() -> dict:
    """Verify relative markdown links under context/canonical resolve to files."""
    link_re = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    broken: list[dict] = []
    archived: list[dict] = []
    ok_count = 0

    for md in sorted(CANONICAL.rglob("*.md")):
        text = md.read_text()
        for target in link_re.findall(text):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            if any(target.startswith(p) or p in target for p in ARCHIVE_LINK_PREFIXES):
                archived.append({"from": str(md.relative_to(ROOT)), "to": target})
                continue
            if target.startswith("context/"):
                resolved = (ROOT / target).resolve()
            elif "/app/" in target or target.startswith("../../app/") or target.startswith("../../tests/"):
                # PRD evidence links to source code
                rel = target.replace("../../", "")
                resolved = (ROOT / rel).resolve()
            else:
                resolved = (md.parent / target).resolve()
            if resolved.exists():
                ok_count += 1
            else:
                broken.append({"from": str(md.relative_to(ROOT)), "to": target})

    return {"ok": ok_count, "broken": broken, "archived": archived}


def render_canonical_link_check(report: dict) -> str:
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "---",
        f"generated_at: {ts}",
        "generator: scripts/generate_context.py",
        "---",
        "",
        "# Canonical Link Check",
        "",
        f"> **OK:** {report['ok']} resolved links | **Broken:** {len(report['broken'])} | **Archived refs:** {len(report['archived'])}",
        "",
    ]
    if report["broken"]:
        lines.append("## Broken links (fix required)")
        lines.append("")
        for item in report["broken"]:
            lines.append(f"- `{item['from']}` → `{item['to']}`")
        lines.append("")
    else:
        lines.append("**No broken internal links.** Safe for `docs/` archive from link perspective.")
        lines.append("")

    if report["archived"]:
        lines.append("## Archived external refs (intentional — legacy not copied)")
        lines.append("")
        seen = set()
        for item in report["archived"]:
            key = item["to"]
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"- `{key}`")
        lines.append("")

    return "\n".join(lines)


def scan_test_map() -> list[dict]:
    """Map app modules to test files."""
    tests_root = ROOT / "tests"
    mapping: dict[str, list[str]] = {}
    for test_file in sorted(tests_root.rglob("test_*.py")):
        rel = str(test_file.relative_to(ROOT))
        parts = test_file.parts
        if "unit" in parts:
            idx = parts.index("unit")
            module = "/".join(parts[idx + 1 : -1]) if idx + 1 < len(parts) - 1 else "root"
        elif "integration" in parts:
            module = "integration/" + "/".join(parts[parts.index("integration") + 1 : -1])
        else:
            module = "other"
        mapping.setdefault(module, []).append(rel)
    return [{"module": k, "tests": v} for k, v in sorted(mapping.items())]


def status_emoji(status: str) -> str:
    return {
        "IMPLEMENTED": "done",
        "PARTIALLY_IMPLEMENTED": "partial",
        "NOT_STARTED": "todo",
        "PROPOSED": "proposed",
        "DOCUMENTED_ONLY": "doc",
    }.get(status, status.lower())


def render_platform_state(
    *,
    sha: str,
    branch: str,
    head: str,
    tests: int | None,
    tables: list[str],
    routes: list[dict],
) -> str:
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    test_line = str(tests) if tests is not None else "run `uv run pytest tests/ -q`"
    return f"""---
generated_at: {ts}
git_sha: {sha}
git_branch: {branch}
generator: scripts/generate_context.py
stale_after_hours: 24
---

# Platform State

> Auto-generated. Do not edit. Run `uv run python scripts/generate_context.py` to refresh.

| Field | Value |
|-------|-------|
| Git SHA | `{sha}` |
| Branch | `{branch}` |
| Migration head (latest file) | `{head}` |
| Tests collected | {test_line} |
| API route handlers | {len(routes)} |
| DB tables (models) | {len(tables)} |

## Pipeline

```
Market Data → Ranking → Validation → Recommendation Engine → HITL → Execution (Paper/Live)
                                      ↓
                              Exit Monitor (daily; ADR-033 intraday PROPOSED)
                                      ↓
                              ARGS / Committee (advisory)
```

## Environment flags (see `.env.example`)

| Flag | Purpose |
|------|---------|
| `HITL_ENABLED` | `false` = paper auto-approve; `true` = human approval required |
| `PAPER_TRADING_ENABLED` | Enables paper pilot execution path |
| `AUTH_ENABLED` | JWT gate on API |

## Key commands

```bash
docker compose -f docker/docker-compose.yml up --build
uv run pytest tests/ -q
uv run python scripts/generate_context.py
uv run python scripts/replay_paper_trade.py   # historical paper replay
```
"""


def render_api_surface(routes: list[dict]) -> str:
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "---",
        f"generated_at: {ts}",
        "generator: scripts/generate_context.py",
        "---",
        "",
        "# API Surface",
        "",
        "> Prefix: `/api/v1`. Scan of `app/api/v1/*.py` route decorators.",
        "",
        "| Module | Method | Path |",
        "|--------|--------|------|",
    ]
    for r in routes:
        lines.append(f"| `{r['module']}` | {r['method']} | `{r['path']}` |")
    lines.append("")
    lines.append("OpenAPI: http://localhost:8000/docs")
    return "\n".join(lines)


def render_database_schema(model_details: list[dict]) -> str:
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "---",
        f"generated_at: {ts}",
        "generator: scripts/generate_context.py",
        "---",
        "",
        "# Database Schema",
        "",
        "> Parsed from `app/models/*.py`. See `migrations/versions/` for migrations.",
        "",
        "## Table index",
        "",
    ]
    for d in model_details:
        lines.append(f"- `{d['table']}` — `{d['model']}` (`{d['file']}`)")
    lines.extend(["", "## Key tables (detail)", ""])
    key_tables = {
        "portfolio_positions",
        "portfolio_exit_recommendations",
        "recommendation_results",
        "paper_trades",
        "execution_orders",
        "portfolio_nav_history",
        "ranking_runs",
        "ranking_results",
    }
    for d in model_details:
        if d["table"] not in key_tables:
            continue
        lines.append(f"### `{d['table']}`")
        lines.append("")
        lines.append("| Column | Type | FK |")
        lines.append("|--------|------|-----|")
        for c in d["columns"][:25]:
            fk = f"`{c['fk']}`" if c["fk"] else "—"
            lines.append(f"| `{c['name']}` | {c['type']} | {fk} |")
        if len(d["columns"]) > 25:
            lines.append(f"| … | +{len(d['columns']) - 25} more | |")
        lines.append("")
    return "\n".join(lines)


def render_api_schemas_summary(openapi: dict) -> str:
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    paths = openapi.get("paths") or {}
    if "error" in openapi:
        return f"""---
generated_at: {ts}
generator: scripts/generate_context.py
---

# API Schemas Summary

OpenAPI export failed: `{openapi.get('error')}`

Use http://localhost:8000/docs when API is running.
"""
    lines = [
        "---",
        f"generated_at: {ts}",
        "generator: scripts/generate_context.py",
        "---",
        "",
        "# API Schemas Summary",
        "",
        f"> {len(paths)} paths from FastAPI OpenAPI. Full spec: `context/generated/API_SCHEMAS.json`",
        "",
        "| Method | Path | Summary |",
        "|--------|------|---------|",
    ]
    for path, methods in sorted(paths.items()):
        for method, spec in methods.items():
            if method.startswith("x-"):
                continue
            summary = (spec.get("summary") or spec.get("operationId") or "—")[:60]
            lines.append(f"| {method.upper()} | `{path}` | {summary} |")
    return "\n".join(lines)


def render_env_catalog(fields: list[dict]) -> str:
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "---",
        f"generated_at: {ts}",
        "generator: scripts/generate_context.py",
        "---",
        "",
        "# Environment Catalog",
        "",
        "> From `app/core/config.py` Settings. See also `.env.example`.",
        "",
        "| Env var | Field | Default | Type |",
        "|---------|-------|---------|------|",
    ]
    key_flags = {
        "hitl_enabled",
        "paper_trading_enabled",
        "auth_enabled",
        "enable_live_trading",
        "intraday_exit_monitor_enabled",
        "auto_exit_on_critical_stop",
        "advisory_stop_pct",
        "critical_stop_pct",
        "ranking_default_strategy",
    }
    for f in fields:
        if f["field"] in key_flags or f["field"].startswith("args_llm"):
            default = str(f["default"])
            if len(default) > 40:
                default = default[:37] + "..."
            lines.append(
                f"| `{f['env']}` | `{f['field']}` | `{default}` | {f['annotation']} |"
            )
    lines.extend(["", "## All settings fields", ""])
    for f in fields:
        lines.append(f"- `{f['env']}` → `{f['field']}`")
    return "\n".join(lines)


def render_ops_scripts(scripts: list[dict]) -> str:
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "---",
        f"generated_at: {ts}",
        "generator: scripts/generate_context.py",
        "---",
        "",
        "# Ops & Scripts Index",
        "",
        "| Script | Purpose |",
        "|--------|---------|",
    ]
    for s in scripts[:40]:
        purpose = s["purpose"][:70] + ("..." if len(s["purpose"]) > 70 else "")
        lines.append(f"| `{s['path']}` | {purpose} |")
    lines.extend(
        [
            "",
            "## Experiment configs (`configs/`)",
            "",
        ]
    )
    configs = ROOT / "configs"
    if configs.exists():
        for c in sorted(configs.glob("*.yaml")):
            lines.append(f"- `{c.relative_to(ROOT)}`")
    return "\n".join(lines)


def render_ranking_strategies(data: dict) -> str:
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "---",
        f"generated_at: {ts}",
        "generator: scripts/generate_context.py",
        "---",
        "",
        "# Ranking Strategies",
        "",
        f"**Default:** `{data['default']}` (`app/core/config.py`)",
        "",
        "| Strategy | Module |",
        "|----------|--------|",
    ]
    for s in data["strategies"]:
        lines.append(f"| `{s['name']}` | `{s['module']}` |")
    return "\n".join(lines)


def render_test_map(modules: list[dict]) -> str:
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "---",
        f"generated_at: {ts}",
        "generator: scripts/generate_context.py",
        "---",
        "",
        "# Test Coverage Map",
        "",
        "> Test files grouped by module area.",
        "",
    ]
    for entry in modules:
        lines.append(f"## `{entry['module']}`")
        lines.append("")
        for t in entry["tests"][:12]:
            lines.append(f"- `{t}`")
        if len(entry["tests"]) > 12:
            lines.append(f"- … +{len(entry['tests']) - 12} more")
        lines.append("")
    return "\n".join(lines)


def render_frontend_surface(hooks: list[str]) -> str:
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    routes_text = ""
    if FRONTEND_ROUTES.exists():
        routes_text = FRONTEND_ROUTES.read_text()
    lines = [
        "---",
        f"generated_at: {ts}",
        "generator: scripts/generate_context.py",
        "---",
        "",
        "# Frontend Surface",
        "",
        "## Routes (`frontend/packages/navigation/src/routes.ts`)",
        "",
        "```typescript",
        routes_text.strip(),
        "```",
        "",
        "## React Query hooks",
        "",
    ]
    for h in hooks:
        lines.append(f"- `frontend/packages/hooks/src/queries/{h}`")
    lines.extend(
        [
            "",
            "## Screens (`frontend/packages/ui/src/screens/`)",
            "",
        ]
    )
    screens_dir = ROOT / "frontend" / "packages" / "ui" / "src" / "screens"
    if screens_dir.exists():
        for s in sorted(screens_dir.glob("*.tsx")):
            lines.append(f"- `{s.name}`")
    return "\n".join(lines)


def render_implementation_status(rows: list[dict]) -> str:
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "---",
        f"generated_at: {ts}",
        "generator: scripts/generate_context.py",
        "---",
        "",
        "# Implementation Status",
        "",
        "Designed → Planned → Implemented → Left off. Source: `context/registry/requirements.yaml`.",
        "",
        "| ID | Capability | Designed | Planned | Status | Left off |",
        "|----|------------|----------|---------|--------|----------|",
    ]
    for r in rows:
        left = "; ".join(r.get("left_off") or []) or "—"
        if len(left) > 80:
            left = left[:77] + "..."
        lines.append(
            f"| {r['id']} | {r['title']} | "
            f"{'yes' if r.get('designed') else 'no'} | "
            f"{'yes' if r.get('planned') else 'no'} | "
            f"**{r['status']}** | {left} |"
        )

    # Summary counts
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    lines.extend(["", "## Summary", ""])
    for status, n in sorted(counts.items()):
        lines.append(f"- **{status}**: {n}")
    return "\n".join(lines)


def render_gaps(rows: list[dict]) -> str:
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "---",
        f"generated_at: {ts}",
        "generator: scripts/generate_context.py",
        "---",
        "",
        "# Gaps & Deferred Work",
        "",
        "> Aggregated `left_off` from requirements registry + proposed ADRs.",
        "",
    ]
    for r in rows:
        left = r.get("left_off") or []
        if not left and r["status"] not in ("NOT_STARTED", "PROPOSED", "PARTIALLY_IMPLEMENTED"):
            continue
        lines.append(f"## {r['id']} — {r['title']} ({r['status']})")
        lines.append("")
        if left:
            for item in left:
                lines.append(f"- [ ] {item}")
        else:
            lines.append("- [ ] Not started — see source PRD/ADR")
        if r.get("evidence_verified"):
            lines.append("")
            lines.append("Evidence:")
            for e in r["evidence_verified"][:5]:
                lines.append(f"- `{e}`")
        missing = r.get("evidence_missing") or []
        if missing:
            lines.append("")
            lines.append("**Missing evidence paths:**")
            for e in missing:
                lines.append(f"- `{e}`")
        lines.append("")

    return "\n".join(lines)


def render_rtm_yaml(rows: list[dict], meta: dict) -> str:
    payload = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": git_sha(),
        "registry_version": meta.get("version", "1.0.0"),
        "requirements": rows,
    }
    return yaml.dump(payload, sort_keys=False, allow_unicode=True, default_flow_style=False)


def render_rtm_md(rows: list[dict]) -> str:
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "---",
        f"generated_at: {ts}",
        "generator: scripts/generate_context.py",
        "---",
        "",
        "# Requirements Traceability (human view)",
        "",
        "| ID | Area | Status | Evidence (verified) |",
        "|----|------|--------|---------------------|",
    ]
    for r in rows:
        ev = ", ".join(f"`{e}`" for e in (r.get("evidence_verified") or [])[:2]) or "—"
        lines.append(f"| {r['id']} | {r.get('area', '—')} | {r['status']} | {ev} |")
    lines.append("")
    lines.append("Machine-readable: `context/generated/REQUIREMENTS.rtm.yaml`")
    return "\n".join(lines)


def render_architecture_map() -> str:
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"""---
generated_at: {ts}
generator: scripts/generate_context.py
---

# Architecture Map

## Backend modules (`app/`)

| Module | Responsibility |
|--------|----------------|
| `ranking/` | Deterministic factor ranking (momentum_v1, breakout_v1, reversal_v1, low_vol_v1) |
| `validation/` | Forward-return IC, deciles, insufficient_data tail |
| `recommendation/` | BUY/WATCH/EXIT/HOLD engine, conviction, RCEE |
| `portfolio/` | Positions, sizing, exit monitor, reconciliation, NAV |
| `execution/` | Unified ExecutionService, paper + Zerodha adapters |
| `args/` | Investment committee packets, LLM agents (advisory only) |
| `copilot/` | Grounded investor Q&A |
| `ops/` | Daily batch, paper pilot, HITL gate, pilot alerting |
| `replay/` | Experiment replay engine (configs in `configs/`) |
| `api/v1/` | FastAPI routers |

## Domain boundaries

- **Ranking/Validation** never call LLM for scores.
- **Recommendation engine** sets `action`; committee cannot mutate it.
- **Exit monitor** creates recommendations; human confirms (except paper auto / ADR-033 proposed).
- **ExecutionService** is the only path from APPROVED → position change.

## Canonical decisions

Self-contained under `context/canonical/` — see `context/canonical/INDEX.md`.

## Gotchas

See `context/GOTCHAS.md` before changing validation, HITL, exit monitor, or batch flows.
"""


def render_agents(
    *,
    sha: str,
    branch: str,
    head: str,
    tests: int | None,
    rows: list[dict],
) -> str:
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    test_line = str(tests) if tests is not None else "unknown"

    proposed = [r for r in rows if r["status"] in ("PROPOSED", "NOT_STARTED")]
    partial = [r for r in rows if r["status"] == "PARTIALLY_IMPLEMENTED"]

    snap_lines = []
    for r in rows[:12]:
        snap_lines.append(f"| {r['id']} | {r['title'][:40]} | {r['status']} |")

    return f"""---
generated_at: {ts}
git_sha: {sha}
git_branch: {branch}
---

# Pi-PM Agent Context

**Universal entry point** for Cursor, Claude Code, Devin, and human developers.

## 1. What this system is

Personal Intelligence Portfolio Manager — deterministic **ingest → rank → validate → recommend → HITL → paper/live execution** for Indian NSE swing book (~15–30 sessions).

## 2. Non-negotiables (PO sign-off)

1. Deterministic ranking is sacred — same inputs → same outputs.
2. Validation tail is sacred — do not fake `completed` status.
3. LLMs **must not** influence ranking, conviction, sizing, or trade approval.
4. Human approves entries and exits (ADR-033 critical stop override is **PROPOSED** only).
5. ARGS / committee is **advisory** — cannot change `action`.

## 3. Session bootstrap (load in order)

| Depth | File | When |
|-------|------|------|
| **L0** | `context/generated/PLATFORM_STATE.md` | Always — branch, tests, migration |
| **L0b** | `context/GOTCHAS.md` | Before batch/HITL/exit changes |
| **L1** | `context/generated/IMPLEMENTATION_STATUS.md` | Feature work — designed/planned/done/gaps |
| **L2** | `context/generated/REQUIREMENTS.rtm.yaml` | Traceability, audits |
| **L3** | `context/generated/GAPS_AND_DEBT.md` | What's left off |
| **L4** | `context/canonical/INDEX.md` | ADRs & PRDs (self-contained) |
| **L4b** | `context/GOTCHAS.md` | Batch/HITL/exit anti-patterns |
| **L5** | `context/generated/API_SCHEMAS.json` | API contracts |
| **L5** | `context/generated/DATABASE_SCHEMA.md` | Schema detail |
| **L5** | `context/generated/ENV_CATALOG.md` | All env flags |
| **L5** | `context/generated/OPS_SCRIPTS.md` | Batch/replay scripts |
| **L5** | `context/generated/CANONICAL_LINK_CHECK.md` | Broken link report |

**If `git_sha` below ≠ current `git rev-parse --short HEAD`, run:**
```bash
uv run python scripts/generate_context.py
```

## 4. Live snapshot

| Field | Value |
|-------|-------|
| git_sha | `{sha}` |
| branch | `{branch}` |
| migration_head | `{head}` |
| tests_collected | {test_line} |
| proposed_items | {len(proposed)} |
| partial_items | {len(partial)} |

| ID | Capability | Status |
|----|------------|--------|
{chr(10).join(snap_lines)}

## 5. Do not use for truth

- Legacy `docs/HANDOFF.md`, `docs/PLATFORM-HANDOFF-2026.md` — **stale**, being replaced by `context/`.
- Sprint reports, `docs/dailyruns/`, experiment result dumps — **archive only**.
- Always prefer `context/generated/` over hand-written status docs.

## 6. Key areas — quick orientation

| Area | Implemented | Next |
|------|-------------|------|
| Recommendation engine | Engine + APIs + UI history | ADR-032 gate modes (PO decision) |
| Exit monitor | Daily OPEN positions, UI EXIT tab | ADR-033 intraday + notifications |
| Paper trading | Replay + auto when HITL off | Backfill exit_recommendations in old DB |
| Live execution | Paper adapter + Zerodha stub | S1 broker orders, risk gates |
| Frontend | Dashboard, Recs, Portfolio, Committee, Copilot | /analytics, push alerts |

## 7. Commands

```bash
docker compose -f docker/docker-compose.yml up --build
uv run pytest tests/ -q
uv run python scripts/generate_context.py
```

## 8. Agent rules

- Cite requirement IDs (`R-EXIT`, `ADR-033`) and file paths from `REQUIREMENTS.rtm.yaml`.
- Check `status` before assuming a feature exists.
- Do not infer implementation from PRD prose alone.
- Minimize scope; match existing code conventions.
"""


def render_manifest(artifacts: list[tuple[str, Path]], sha: str) -> str:
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    entries = []
    for role, path in artifacts:
        entries.append(
            {
                "path": str(path.relative_to(ROOT)),
                "role": role,
                "sha256_prefix": file_hash(path),
                "exists": path.exists(),
            }
        )
    payload = {
        "generated_at": ts,
        "git_sha": sha,
        "generator": "scripts/generate_context.py",
        "artifacts": entries,
    }
    return yaml.dump(payload, sort_keys=False, default_flow_style=False)


def main() -> int:
    GENERATED.mkdir(parents=True, exist_ok=True)
    (CONTEXT / "canonical").mkdir(parents=True, exist_ok=True)

    sha = git_sha()
    branch = git_branch()
    head = alembic_head()
    tests = test_count()
    registry = load_registry()
    rows = enrich_requirements(registry)
    routes = scan_api_routes()
    model_details = scan_model_details()
    tables = [d["table"] for d in model_details]
    hooks = scan_frontend_hooks()
    openapi = export_openapi()
    env_fields = scan_env_catalog()
    ops_scripts = scan_ops_scripts()
    ranking = scan_ranking_strategies()
    test_map = scan_test_map()

    outputs: list[tuple[str, str, Path]] = [
        ("platform_state", render_platform_state(sha=sha, branch=branch, head=head, tests=tests, tables=tables, routes=routes), GENERATED / "PLATFORM_STATE.md"),
        ("api_surface", render_api_surface(routes), GENERATED / "API_SURFACE.md"),
        ("api_schemas_summary", render_api_schemas_summary(openapi or {}), GENERATED / "API_SCHEMAS.md"),
        ("database_schema", render_database_schema(model_details), GENERATED / "DATABASE_SCHEMA.md"),
        ("env_catalog", render_env_catalog(env_fields), GENERATED / "ENV_CATALOG.md"),
        ("ops_scripts", render_ops_scripts(ops_scripts), GENERATED / "OPS_SCRIPTS.md"),
        ("ranking_strategies", render_ranking_strategies(ranking), GENERATED / "RANKING_STRATEGIES.md"),
        ("test_map", render_test_map(test_map), GENERATED / "TEST_MAP.md"),
        ("frontend_surface", render_frontend_surface(hooks), GENERATED / "FRONTEND_SURFACE.md"),
        ("implementation_status", render_implementation_status(rows), GENERATED / "IMPLEMENTATION_STATUS.md"),
        ("gaps", render_gaps(rows), GENERATED / "GAPS_AND_DEBT.md"),
        ("rtm_yaml", render_rtm_yaml(rows, registry.get("meta", {})), GENERATED / "REQUIREMENTS.rtm.yaml"),
        ("rtm_md", render_rtm_md(rows), GENERATED / "REQUIREMENTS.rtm.md"),
        ("architecture_map", render_architecture_map(), GENERATED / "ARCHITECTURE_MAP.md"),
        ("agents", render_agents(sha=sha, branch=branch, head=head, tests=tests, rows=rows), CONTEXT / "AGENTS.md"),
    ]

    artifacts: list[tuple[str, Path]] = []
    for role, content, path in outputs:
        path.write_text(content)
        artifacts.append((role, path))
        print(f"wrote {path.relative_to(ROOT)}")

    # Re-run link check after all generated files exist
    link_report = scan_canonical_links()
    link_check_path = GENERATED / "CANONICAL_LINK_CHECK.md"
    link_check_path.write_text(render_canonical_link_check(link_report))
    artifacts.append(("canonical_link_check", link_check_path))
    print(f"wrote {link_check_path.relative_to(ROOT)}")

    if openapi and "error" not in openapi:
        api_json = GENERATED / "API_SCHEMAS.json"
        api_json.write_text(json.dumps(openapi, indent=2))
        artifacts.append(("api_schemas_json", api_json))
        print(f"wrote {api_json.relative_to(ROOT)}")

    gotchas = CONTEXT / "GOTCHAS.md"
    artifacts.append(("gotchas", gotchas))

    manifest_path = CONTEXT / "MANIFEST.yaml"
    manifest_path.write_text(render_manifest(artifacts, sha))
    print(f"wrote {manifest_path.relative_to(ROOT)}")

    # Root symlinks/files for tool discovery
    root_agents = ROOT / "AGENTS.md"
    root_claude = ROOT / "CLAUDE.md"
    pointer = (
        "# Pi-PM — start here\n\n"
        "Read **[context/AGENTS.md](context/AGENTS.md)** for AI session bootstrap.\n\n"
        "Regenerate context: `uv run python scripts/generate_context.py`\n"
    )
    root_agents.write_text(pointer)
    root_claude.write_text(pointer)
    print(f"wrote {root_agents.relative_to(ROOT)}")
    print(f"wrote {root_claude.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
