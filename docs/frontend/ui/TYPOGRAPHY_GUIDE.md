# Typography Guide

## Families

| Token | Value | Use |
|-------|-------|-----|
| `sans` | System | UI labels, prose, committee narratives |
| `mono` | monospace | NAV, prices, IDs, reason codes, lineage |

## Scale

| Token | Size | Use |
|-------|------|-----|
| `xs` | 11px | Metadata, timestamps |
| `sm` | 12px | Secondary labels |
| `md` | 14px | Body, card content |
| `lg` | 16px | Symbols, section values |
| `xl` | 20px | Screen subtitles |
| `xxl` | 24px | Primary metrics |
| `display` | 32px | NAV hero (dashboard only) |

## Label Convention

Section and metric labels:

```
fontSize: 10
fontWeight: '600' | '700'
letterSpacing: 1
textTransform: 'uppercase'
color: textMuted
```

## Symbol Convention

Stock symbols:

```
fontSize: 15–16
fontWeight: '700'
fontFamily: monospace
color: textPrimary
```

## Hierarchy per Screen

1. **Screen title** — 22px bold, `textPrimary`
2. **Section label** — 10px uppercase, `textMuted`
3. **Data value** — mono, sized by importance
4. **Narrative** — 13–14px sans, `textSecondary`/`textPrimary`

## Line Height

- Data-dense blocks: `tight` (1.2)
- Prose (committee report, copilot): `relaxed` (1.75)
