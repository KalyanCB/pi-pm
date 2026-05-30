from __future__ import annotations

import hashlib
import json
from datetime import date
from uuid import UUID

from app.validation.models import HorizonMetrics, RegimeClassification, StockForwardReturns


def build_validation_hash(
    ranking_run_id: UUID,
    inputs_hash: str | None,
    as_of_date: date,
    regime: RegimeClassification | None,
    stock_returns: tuple[StockForwardReturns, ...],
    horizon_metrics: dict[int, HorizonMetrics],
) -> str:
    payload = {
        "ranking_run_id": str(ranking_run_id),
        "inputs_hash": inputs_hash,
        "as_of_date": as_of_date.isoformat(),
        "regime_label": regime.regime_label if regime else None,
        "stock_returns": [
            {
                "stock_id": str(item.stock_id),
                "symbol": item.symbol,
                "score": str(item.score),
                "rank": item.rank,
                "returns": {
                    str(k): str(v) if v is not None else None for k, v in item.returns.items()
                },
            }
            for item in sorted(stock_returns, key=lambda s: s.symbol)
        ],
        "horizon_metrics": {
            str(h): {
                "ic_spearman": str(m.ic_spearman) if m.ic_spearman is not None else None,
                "top_minus_bottom_spread": (
                    str(m.top_minus_bottom_spread)
                    if m.top_minus_bottom_spread is not None
                    else None
                ),
                "sample_size": m.sample_size,
            }
            for h, m in sorted(horizon_metrics.items())
        },
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
