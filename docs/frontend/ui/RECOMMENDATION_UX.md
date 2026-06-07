# Recommendation UX

## 5-Second Comprehension Rule

Each card must communicate within 5 seconds:

- **Why** — top 3 reason codes
- **Confidence** — conviction band + score
- **Committee** — HIGH_CONCERN banner if applicable
- **Action** — BUY / WATCH / EXIT badge

## List Screen

- Tabs: BUY | WATCH | EXIT
- Desktop: master-detail (list left, detail right)
- Mobile: list → tap → detail screen
- Trust pill on every card (overall trust context)

## Detail Screen (`/recommendations/[symbol]`)

| Section | Content |
|---------|---------|
| Header | Symbol, action, rank, strategy |
| Conviction | Score, band, component breakdown if available |
| Reasons | Full reason code list |
| Committee | `CommitteeAdvisoryCard` + consensus |
| Trust | Calibration context strip |
| Actions | Approve / Reject / Ask Copilot |

## Approval Flow

```
Recommendation Detail → Committee Advisory (inline) → Copilot (prefill) → Approve/Reject
```

## Visual Priority

1. Action badge (color-coded)
2. HIGH_CONCERN (if present) — above fold
3. Conviction band
4. Reason codes
5. Rank / strategy metadata
