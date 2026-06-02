from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

HASH_EXCLUDED_KEYS = frozenset({"packet_built_at"})


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()


def payload_for_hash(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a copy suitable for content-addressed hashing (excludes volatile fields)."""
    cleaned = deepcopy(payload)
    for key in HASH_EXCLUDED_KEYS:
        cleaned.pop(key, None)
    return cleaned


def compute_packet_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload_for_hash(payload))).hexdigest()
