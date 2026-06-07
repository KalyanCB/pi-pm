# Pi-PM Design System

**Track UI-X · Investor Experience Platform**

## Design Philosophy

Pi-PM is an **institutional decision-support workstation** — not a retail trading app. The interface prioritizes:

1. **Trust** — explainability visible at every level
2. **Density** — maximum information per viewport without clutter
3. **Hierarchy** — portfolio health → recommendations → committee → action
4. **Restraint** — dark palette, monospace data, minimal decoration

**Inspiration:** Bloomberg Terminal Lite, Morningstar, FactSet.

## Token Architecture

```
@pipm/theme
├── colors.ts      — semantic palette (dark-first)
├── typography.ts  — scale + families
├── spacing.ts     — 4px grid
├── elevation.ts   — panel depth (border-based)
├── breakpoints.ts — mobile / tablet / desktop / wide
└── theme.ts       — composed Theme object
```

## Component Tiers

| Tier | Purpose | Examples |
|------|---------|----------|
| **Atoms** | Primitives | `Badge`, `MetricValue`, `Button`, `SectionLabel` |
| **Molecules** | Single-concept blocks | `TrustScoreCard`, `RecommendationCard`, `HighConcernBanner` |
| **Organisms** | Composed sections | `DashboardHealthGrid`, `CopilotSidePanel`, `ApprovalActionBar` |
| **Templates** | Screen layouts | `InvestorScreenShell`, `MasterDetailLayout`, `PanelGrid` |
| **Charts** | Data visualization | `SparklineChart`, `DonutChart`, `BarChart` |

## Card Pattern

All metric cards share:

- `backgroundPanel` fill
- `border` 1px solid
- `borderRadius.md` (6px)
- Label: 10px uppercase, `textMuted`, letter-spacing 1
- Value: `MetricValue` mono, `textMono`
- Optional sparkline in footer

## Action Colors

| Action | Token | Use |
|--------|-------|-----|
| BUY | `actionBuy` | Recommendation badge, approve affordance |
| WATCH | `actionWatch` | Advisory hold |
| EXIT | `actionExit` | Exit approved |
| REJECT | `actionReject` | Reject / deny |
| HIGH_CONCERN | `highConcern` | Committee alert — always prominent |

## Accessibility

- Minimum touch target 44×44 on mobile
- Color never sole indicator — pair with label/icon
- `accessibilityRole` on all interactive elements
- Contrast ratio ≥ 4.5:1 for body text on panel backgrounds

## Responsive Strategy

| Breakpoint | Layout |
|------------|--------|
| Mobile (<768) | Bottom tabs, single column, priority-first |
| Tablet (768–1023) | Collapsible panels, 2-column grids |
| Desktop (≥1024) | Sidebar, multi-panel, copilot side panel |

See `RESPONSIVE_LAYOUT_GUIDE.md` for flows.

## File Locations

- Theme: `frontend/packages/theme/src/`
- Components: `frontend/packages/ui/src/`
- Navigation shell: `frontend/packages/navigation/src/`
