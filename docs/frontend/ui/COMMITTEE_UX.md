# Committee UX

## Purpose

Surface **Investment Committee advisory** — especially HIGH_CONCERN — as a first-class decision input.

## Overview Screen

1. **Status header** — review date, status badge, candidates reviewed
2. **HIGH_CONCERN hero** — impossible to miss; red border section at top
3. **Consensus grid** — `CommitteeConsensusCard` per symbol
4. **Report panel** — governance narratives

## Committee Actions Display

| Action | Visual |
|--------|--------|
| APPROVE | `success` badge |
| WATCH | `warning` badge |
| REJECT | `danger` badge |
| HIGH_CONCERN | `HighConcernBanner` + left border |

## Components

- `HighConcernBanner` — committees list, tappable to detail
- `CommitteeConsensusCard` — per-committee actions grid
- `CommitteeEvidenceCard` — packet payload summary
- `CommitteeReportPanel` — narrative + confidence

## Desktop Detail

Selecting a symbol in overview opens evidence card + link to recommendation detail.

## Mobile

Stacked cards; HIGH_CONCERN section sticky-collapsed summary at top when scrolling.
