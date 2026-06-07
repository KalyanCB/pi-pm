# Color System

Dark-first palette for professional investor interfaces.

## Background Layers

| Token | Hex | Use |
|-------|-----|-----|
| `background` | `#0a0e14` | App canvas |
| `backgroundElevated` | `#111820` | Cards on canvas |
| `backgroundPanel` | `#151d28` | Nested panels, inputs |
| `sidebar` | `#0d1219` | Navigation chrome |
| `sidebarActive` | `#1a2838` | Active nav item |

## Text

| Token | Hex | Use |
|-------|-----|-----|
| `textPrimary` | `#e8edf4` | Headlines, symbols |
| `textSecondary` | `#8b9cb3` | Supporting copy |
| `textMuted` | `#5c6d82` | Labels, metadata |
| `textMono` | `#c5d4e8` | Numeric values |

## Accent & Data

| Token | Hex | Use |
|-------|-----|-----|
| `accent` | `#3d8fd1` | Links, active states, trust bar |
| `positive` | `#3dba7a` | Gains, BUY, low risk |
| `negative` | `#e05252` | Losses, reject |
| `warning` | `#d4a017` | WATCH, medium risk |
| `danger` | `#c0392b` | Critical alerts |

## HIGH_CONCERN (Non-negotiable visibility)

| Token | Hex | Use |
|-------|-----|-----|
| `highConcern` | `#c0392b` | Border, text, icons |
| `highConcernBg` | `#2a1515` | Banner fill |

HIGH_CONCERN elements use **left border 3px**, bold label, and appear **above** standard content.

## Conviction Bands

`convictionBlocked` → `convictionExceptional` — mapped in `ConvictionBadge`.

## Risk Levels

`riskLow` → `riskCritical` — mapped in `RiskIndicator` and `RiskCard`.

## Usage Rules

1. Never use pure white (`#fff`) for body text
2. Semantic colors only for data meaning — not decoration
3. Borders over shadows (RN cross-platform consistency)
4. Action badges always use action tokens, not generic semantic colors
