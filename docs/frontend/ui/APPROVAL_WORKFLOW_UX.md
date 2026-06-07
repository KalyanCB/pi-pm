# Approval Workflow UX

## Decision Chain

```
Recommendation → Committee Advisory → Copilot Explanation → Approve / Reject
```

## Entry Points

| Context | Actions |
|---------|---------|
| Recommendation Detail | Approve, Reject, Ask Copilot |
| EXIT recommendation | Confirm Exit, Reject Exit |
| Committee HIGH_CONCERN | Review → Copilot → Reject (default caution) |

## `ApprovalActionBar`

- **Approve** — `POST /recommendations/{id}/approve`
- **Reject** — `POST /recommendations/{id}/reject` (optional note)
- **Confirm Exit** — `POST /portfolio/exits/{id}/confirm`
- **Reject Exit** — `POST /portfolio/exits/{id}/reject`

## Confirmation

- Approve/Reject: inline confirmation dialog (not modal stack)
- Success: toast-style banner + invalidate queries
- Error: `ErrorState` inline with retry

## Trust Gating (UX only)

When trust score < threshold (visual warning only — no engine change):

- Amber strip: "Below average trust — review committee advisory"
- Does not block approval (owner decision)

## Review Stepper (Detail Screen)

Visual steps: Engine → Committee → Your Decision — checkmarks as user reviews each section.
