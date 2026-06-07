# Copilot UX

## Positioning

Copilot is **decision support**, not a chat widget. It answers institutional questions with grounded evidence.

## Canonical Questions (Quick Chips)

- Why recommended?
- Why not recommended?
- Why exit?
- Why is conviction high?
- What concerns the committee?
- What is portfolio risk?
- How is performance trending?

## Layout

| Platform | Layout |
|----------|--------|
| Desktop | Side panel (400px) — toggled from top bar or recommendation detail |
| Mobile | Full-screen `/copilot` tab |
| Tablet | Collapsible bottom sheet or split view |

## Response Structure

Every assistant message displays:

1. **Answer** — prose block
2. **Sources** — `CitationPanel` (tappable → navigate)
3. **Lineage** — `LineagePanel` (IDs by domain)
4. **Evidence refs** — grouped: Recommendations · Committee · Portfolio

## Refused Responses

Left border `highConcern`, REFUSED label, no approve affordance suggested.

## Session

- "New" clears session
- Prefill from recommendation detail ("Why is {symbol} a BUY?")
