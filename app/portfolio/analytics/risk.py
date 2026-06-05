"""Portfolio risk analytics — pure functions.

Generates risk metrics and alerts. No DB access. No LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RiskAlert:
    code: str
    level: str  # LOW | MEDIUM | HIGH | CRITICAL
    message: str
    details: dict = field(default_factory=dict)


@dataclass
class RiskMetrics:
    # Exposure
    gross_exposure_pct: float | None
    net_exposure_pct: float | None
    cash_pct: float | None
    largest_position_pct: float | None
    top_3_concentration_pct: float | None

    # Sector
    sector_exposures: dict[str, float]  # sector → weight %
    max_sector_pct: float | None
    max_sector_name: str | None

    # Position
    open_positions: int
    max_positions_allowed: int
    slots_used_pct: float | None

    # Drawdown
    current_drawdown_pct: float | None

    # Alerts
    alerts: list[RiskAlert]
    risk_level: str  # LOW | MEDIUM | HIGH | CRITICAL


def compute_risk(
    positions: list[dict],  # [{symbol, market_value, weight_pct, sector, unrealized_pnl_pct}, ...]
    total_equity: float,
    cash_balance: float,
    max_positions: int = 6,
    single_name_cap_pct: float = 18.0,
    sector_cap_pct: float = 30.0,
    cash_floor_pct: float = 15.0,
    current_drawdown_pct: float | None = None,
    drawdown_alert_pct: float = 10.0,
) -> RiskMetrics:
    alerts: list[RiskAlert] = []

    open_count = len(positions)
    total_mv = sum(p.get("market_value", 0) or 0 for p in positions)
    cash_pct = (cash_balance / total_equity * 100) if total_equity > 0 else 0
    gross_exposure = (total_mv / total_equity * 100) if total_equity > 0 else 0

    # Largest position
    weights = sorted([p.get("weight_pct", 0) or 0 for p in positions], reverse=True)
    largest = weights[0] if weights else None
    top3 = sum(weights[:3]) if len(weights) >= 3 else sum(weights)

    # Sector exposures
    sector_map: dict[str, float] = {}
    for pos in positions:
        sector = pos.get("sector") or "Unknown"
        sector_map[sector] = sector_map.get(sector, 0) + (pos.get("weight_pct", 0) or 0)
    max_sector_pct = max(sector_map.values()) if sector_map else None
    max_sector_name = max(sector_map, key=sector_map.get) if sector_map else None

    # ── Alert generation ──────────────────────────────────────────────────────

    # Cash floor
    if cash_pct < cash_floor_pct:
        level = "CRITICAL" if cash_pct < cash_floor_pct / 2 else "HIGH"
        alerts.append(
            RiskAlert(
                code="LOW_CASH",
                level=level,
                message=f"Cash {cash_pct:.1f}% below floor {cash_floor_pct:.1f}%",
                details={"cash_pct": cash_pct, "floor_pct": cash_floor_pct},
            )
        )

    # Single-name concentration
    for pos in positions:
        w = pos.get("weight_pct", 0) or 0
        if w > single_name_cap_pct:
            alerts.append(
                RiskAlert(
                    code="CONCENTRATION_RISK",
                    level="HIGH" if w < single_name_cap_pct * 1.3 else "CRITICAL",
                    message=f"{pos.get('symbol', '?')} at {w:.1f}% exceeds {single_name_cap_pct:.1f}% cap",
                    details={
                        "symbol": pos.get("symbol"),
                        "weight_pct": w,
                        "cap_pct": single_name_cap_pct,
                    },
                )
            )

    # Sector limit
    for sector, pct in sector_map.items():
        if pct > sector_cap_pct:
            alerts.append(
                RiskAlert(
                    code="SECTOR_LIMIT_BREACH",
                    level="HIGH",
                    message=f"Sector {sector} at {pct:.1f}% exceeds {sector_cap_pct:.1f}% limit",
                    details={"sector": sector, "weight_pct": pct, "cap_pct": sector_cap_pct},
                )
            )

    # Drawdown
    if current_drawdown_pct is not None and current_drawdown_pct > drawdown_alert_pct:
        level = "CRITICAL" if current_drawdown_pct > drawdown_alert_pct * 2 else "HIGH"
        alerts.append(
            RiskAlert(
                code="DRAWDOWN_ALERT",
                level=level,
                message=f"Portfolio drawdown {current_drawdown_pct:.1f}% exceeds {drawdown_alert_pct:.1f}% threshold",
                details={"drawdown_pct": current_drawdown_pct, "threshold_pct": drawdown_alert_pct},
            )
        )

    # Position slots nearing limit
    slots_used_pct = (open_count / max_positions * 100) if max_positions > 0 else None
    if slots_used_pct and slots_used_pct >= 100:
        alerts.append(
            RiskAlert(
                code="PORTFOLIO_FULL",
                level="MEDIUM",
                message=f"All {max_positions} slots occupied",
                details={"open_positions": open_count, "max_positions": max_positions},
            )
        )

    # Overall risk level
    if any(a.level == "CRITICAL" for a in alerts):
        risk_level = "CRITICAL"
    elif any(a.level == "HIGH" for a in alerts):
        risk_level = "HIGH"
    elif any(a.level == "MEDIUM" for a in alerts):
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return RiskMetrics(
        gross_exposure_pct=round(gross_exposure, 2),
        net_exposure_pct=round(gross_exposure, 2),  # no shorts — same as gross
        cash_pct=round(cash_pct, 2),
        largest_position_pct=round(largest, 2) if largest is not None else None,
        top_3_concentration_pct=round(top3, 2),
        sector_exposures={k: round(v, 2) for k, v in sector_map.items()},
        max_sector_pct=round(max_sector_pct, 2) if max_sector_pct is not None else None,
        max_sector_name=max_sector_name,
        open_positions=open_count,
        max_positions_allowed=max_positions,
        slots_used_pct=round(slots_used_pct, 1) if slots_used_pct is not None else None,
        current_drawdown_pct=current_drawdown_pct,
        alerts=alerts,
        risk_level=risk_level,
    )
