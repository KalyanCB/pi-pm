# Live Trading Safety Checklist

Complete **all** items before enabling LIVE execution in any environment.

## Pre-Enablement

- [ ] Paper pilot completed with acceptable metrics (90-day plan)
- [ ] Reconciliation reports show zero unexplained discrepancies for 30+ days
- [ ] Execution audit trail reviewed — all transitions logged
- [ ] OWNER/ADMIN access list verified; no VIEWER has execution write
- [ ] Zerodha API credentials rotated and stored in secrets manager (not source code)
- [ ] `ENABLE_LIVE_TRADING=true` set only in production secrets
- [ ] `execution_mode=LIVE` set via `POST /api/v1/execution/config` or `portfolio_configs`
- [ ] `KITE_API_KEY`, `KITE_API_SECRET`, `KITE_ACCESS_TOKEN` configured via environment
- [ ] Kill switch documented: set `ENABLE_LIVE_TRADING=false` to block all live orders

## Verification Steps

1. `GET /api/v1/execution/health` — expect `healthy: true` with credentials configured
2. Submit a **small test order** with explicit human approval
3. Confirm `execution_events` shows full lifecycle
4. Confirm portfolio updates only after `FILLED`
5. Test `POST /api/v1/execution/orders/{id}/cancel` on a pending order

## Rollback

1. Set `ENABLE_LIVE_TRADING=false` (immediate block)
2. Set `execution_mode=PAPER` via config API
3. Verify `GET /api/v1/execution/health` shows `healthy: true` for paper adapter
4. Review open orders in `execution_orders` where `status NOT IN (FILLED, CANCELLED, REJECTED, FAILED)`

## Non-Negotiables

- No broker credentials in source code or git
- No automatic execution without human approval
- Adapters must not alter recommendation or conviction logic
- LIVE disabled by default in all environments
