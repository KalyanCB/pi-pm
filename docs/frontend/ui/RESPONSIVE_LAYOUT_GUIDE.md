# Responsive Layout Guide

## Breakpoints

| Name | Width | Shell |
|------|-------|-------|
| mobile | 0–767 | Bottom tabs |
| tablet | 768–1023 | Bottom tabs or narrow sidebar |
| desktop | 1024+ | Sidebar 240px |
| wide | 1440+ | Sidebar + copilot panel + master-detail |

## Navigation Hierarchy

```
Primary: Dashboard → Recommendations → Portfolio → Committee → Copilot
Secondary: Settings (sidebar footer / overflow)
Auth: /login (no shell)
```

## Desktop Flows

- Dashboard: 3-column metric grid + 2-column charts
- Recommendations: 40% list / 60% detail
- Copilot: side panel overlay (does not unmount main content)
- Committee: full width with HIGH_CONCERN band

## Tablet Flows

- 2-column grids where desktop uses 3
- Copilot: collapsible panel or full screen
- Master-detail: stack on narrow tablet

## Mobile Flows

- Single column everywhere
- Priority-first: alerts → metrics → lists
- Detail screens full-page push
- Approval bar fixed bottom with safe area

## Copilot Panel

- Desktop: `AppShell` renders `CopilotSidePanel` when `uiStore.copilotPanelOpen`
- Toggle: top bar button + recommendation "Ask Copilot"
- Width: 400px, `backgroundElevated`

## Touch Targets

Minimum 44px height for tabs, buttons, citation chips.
