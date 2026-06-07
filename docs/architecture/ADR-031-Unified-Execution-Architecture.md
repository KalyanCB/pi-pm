# ADR-031: Unified Execution Architecture (Paper + Live Trading)

**Status:** Accepted  
**Date:** 2026-06-10  
**Track:** K — Unified Execution Platform

## Context

Pi-PM generates investment recommendations through deterministic ranking, validation, conviction scoring, and committee advisory. Human approval is mandatory before any capital is deployed. Today, approved recommendations flow directly into `PaperTradeService`, bypassing a broker abstraction and making live trading a separate future effort.

Track K introduces a **unified execution workflow** that supports both PAPER (default) and LIVE (Zerodha Kite) execution through identical APIs, persistence, and audit trails — without modifying recommendation, conviction, committee, or copilot logic.

## Decision

Implement a broker-agnostic execution platform behind an **adapter layer**:

```
Recommendation → Human Approval → Execution Request → Execution Service
    → Execution Adapter → Paper or Live Broker
```

### Execution Lifecycle

| State | Meaning |
|-------|---------|
| `EXECUTION_PENDING` | Order created locally; not yet sent to broker |
| `SUBMITTED` | Order transmitted to adapter/broker |
| `ACCEPTED` | Broker acknowledged the order |
| `PARTIALLY_FILLED` | Partial fill received |
| `FILLED` | Terminal — full fill; portfolio may update |
| `CANCELLED` | Terminal — user or system cancelled |
| `REJECTED` | Terminal — broker rejected |
| `FAILED` | Terminal — system/adapter failure |

Only `FILLED` orders trigger portfolio position and cash ledger updates.

### Adapter Pattern

```python
class ExecutionAdapter(Protocol):
    def place_order(request: TradeRequest) -> TradeResult: ...
    def cancel_order(broker_order_id: str) -> TradeResult: ...
    def get_order_status(broker_order_id: str) -> TradeResult: ...
    def health_check() -> HealthStatus: ...
```

| Mode | Adapter | Default |
|------|---------|---------|
| `PAPER` | `PaperExecutionAdapter` | Yes |
| `LIVE` | `ZerodhaKiteExecutionAdapter` | No (requires `ENABLE_LIVE_TRADING=true`) |

Adapters **must not** influence `recommendation.action`, `conviction_score`, or portfolio allocation logic. Allocation is computed before the adapter is invoked; the adapter only executes the approved quantity.

### Paper / Live Parity

- Identical REST API (`/api/v1/execution/*`)
- Identical tables: `execution_orders`, `execution_events`, `execution_configs`, `execution_audit`
- Identical state machine and transition audit
- `execution_mode` on `portfolio_configs` (default `PAPER`)

Live trading is **disabled by default**. Enabling requires:

1. `execution_mode=LIVE` on portfolio config
2. Zerodha credentials via environment (`KITE_API_KEY`, `KITE_API_SECRET`, `KITE_ACCESS_TOKEN`)
3. `ENABLE_LIVE_TRADING=true`

No credentials are stored in source code.

### Human-in-the-Loop (HITL) Controls

| Rule | Enforcement |
|------|-------------|
| K-03 | Approval endpoint unchanged; no auto-execution on approve |
| K-04 | `POST /execution/orders` requires prior `APPROVED` decision |
| K-13 | Only `OWNER` and `ADMIN` may submit orders; `VIEWER` denied |

Audit fields: `requested_by`, `approved_by`, `executed_by` on every order.

### Audit Requirements

Every state transition writes to `execution_events`. Every broker interaction writes to `execution_audit`. No broker action occurs without a preceding audit record.

### Broker Abstraction

`ZerodhaKiteExecutionAdapter` implements the contract only. Holdings sync and position sync are adapter methods for reconciliation; they do not alter recommendation logic.

`PaperExecutionAdapter` delegates fill simulation to the existing `PaperTradeService` engine at the `FILLED` transition only, preserving slippage, fees, and allocation behavior.

## Consequences

### Positive

- Single execution path for paper pilot and future live trading
- Full audit trail for compliance and pilot operations
- Mode switch without code changes

### Negative

- Additional latency from state machine persistence (acceptable for HITL workflow)
- Portfolio trade endpoints now route through execution service (thin wrapper)

## Non-Goals

- Changing ranking, validation, recommendation engine, conviction scoring, portfolio sizing, committee logic, or copilot logic
- Enabling live trading in development environments
- Storing broker credentials in the database

## References

- ADR-028: Paper Trading Readiness
- ADR-030: Live Investing Architecture (design precursor)
- Track K specification (PI-PM)
