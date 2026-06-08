# Component Styling Guide

## Metric Card

```tsx
// Standard investor metric card
borderWidth: 1
borderRadius: 6  // theme.borderRadius.md
padding: 12      // theme.spacing.md
gap: 4           // theme.spacing.xs
backgroundColor: theme.colors.backgroundPanel
borderColor: theme.colors.border
```

## HIGH_CONCERN Banner

```tsx
backgroundColor: theme.colors.highConcernBg
borderColor: theme.colors.highConcern
borderWidth: 1
borderLeftWidth: 3
padding: 8–12
```

## Recommendation Card

- Default border: `border`
- HIGH_CONCERN: border `highConcern`, optional glow via `highConcernBg` tint
- Header row: symbol + action badge + rank + conviction badge
- Footer: reason codes (mono chips) + committee strip

## Trust Indicator Strip

Horizontal pills: Calibration · Stability · Reliability — each shows score or `—`.

## Approval Action Bar

Fixed bottom (mobile) or inline panel (desktop):

- Primary: Approve (`actionBuy` border)
- Secondary: Reject (`actionReject` border)
- Tertiary: Ask Copilot (`accent`)

## Copilot Response Block

```
┌─ Answer (prose) ─────────────────┐
├─ Citations (chips, tappable) ────┤
├─ Lineage (collapsed IDs) ────────┤
└─ Evidence refs by domain ──────────┘
```

## Chart Containers

- Height: 80px (sparkline), 160px (donut), 120px (bar)
- Background: `background` inset
- No grid lines — axis labels only on bar charts
- Empty state: "No history available" in `textMuted`

## Spacing Grid

Use `theme.spacing` only: xs(4), sm(8), md(12), lg(16), xl(20), xxl(24).

Section gaps: `lg` between sections, `md` within sections.
