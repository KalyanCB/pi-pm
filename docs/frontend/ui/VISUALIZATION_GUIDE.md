# Visualization Guide

## Library

Custom SVG charts via `react-native-svg` in `@pipm/ui/src/charts/`. No mock series — all data from live APIs.

## Chart Types

| Component | API | Fields |
|-----------|-----|--------|
| `SparklineChart` | `/portfolio/nav-history` | `total_equity`, `alpha_pct`, `day_return_pct` |
| `DonutChart` | `/portfolio/positions` | `weight_pct` by symbol |
| `BarChart` | `/portfolio/attribution` | `contribution_pct` by sector |
| `DistributionBar` | `/pilot/dashboard/recommendations` | `today` buy/watch counts |

## Trust Trend

`/pilot/dashboard/trust` → `trend_weekly` array for sparkline.

## Styling

- Line: `accent` 1.5px, no fill (or 10% accent fill for area)
- Positive segment: `positive`; negative: `negative`
- Donut segments: categorical palette from `accent`, `info`, `warning`, `positive`
- Labels: 10px `textMuted` mono

## Empty States

| Condition | Message |
|-----------|---------|
| No nav history | "Insufficient NAV history" |
| No positions | "No open positions" |
| Analytics gate | "Analytics unavailable — reconciliation required" |
| Single data point | Show dot, no line |

## Performance

- Max 90 points on sparklines (slice tail)
- Memoize path generation
- No animation on first render (RN perf)

## Accessibility

Sparklines include `accessibilityLabel` with min/max/latest summary.
