# Pi-PM Context Pack

AI-friendly, always-current project context for Cursor, Claude Code, Devin, and humans.

## Start here

**[AGENTS.md](./AGENTS.md)** — session bootstrap (read first in any new AI chat).

## Structure

```
context/
├── AGENTS.md              # Universal entry (regenerated)
├── MANIFEST.yaml          # Artifact index + freshness hashes
├── canonical/             # Human decisions (ADRs, PRDs) — see INDEX.md
├── generated/             # Auto-generated from code — never hand-edit
└── registry/
    └── requirements.yaml  # Requirement IDs + status seeds for RTM
```

## Regenerate

```bash
uv run python scripts/generate_context.py
```

Produces 15+ artifacts: platform state, RTM (70 reqs), OpenAPI JSON, schema detail, env catalog, ops scripts, test map, etc.

Run after merges, before PO reviews, or when `git_sha` in AGENTS.md is stale.

## Tool setup

| Tool | Entry |
|------|-------|
| Cursor | `.cursor/rules/platform.mdc` → `context/AGENTS.md` |
| Claude Code | `CLAUDE.md` at repo root → this pack |
| Devin | Upload `context/` folder as knowledge base |
| Human | `README.md` → `context/AGENTS.md` |

## Self-contained canonical docs

ADRs, PRDs, runbooks, and design refs live under `context/canonical/` (copied from legacy `docs/`). Legacy `docs/` can be archived once you confirm parity.

## Gotchas

[context/GOTCHAS.md](GOTCHAS.md) — validation tail, HITL flags, exit monitor scope.
