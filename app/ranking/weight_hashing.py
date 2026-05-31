from __future__ import annotations

import hashlib
import json
from decimal import Decimal


def hash_weight_config(weights: dict[str, Decimal] | dict[str, str]) -> str:
    normalized = {key: str(weights[key]) for key in sorted(weights)}
    payload = json.dumps(normalized, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()
