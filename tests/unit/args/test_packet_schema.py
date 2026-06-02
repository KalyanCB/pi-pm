import json
from pathlib import Path

from app.workspace_args.packet_schema import compute_packet_hash, payload_for_hash

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "packets" / "golden_breakout_v1.json"


def test_packet_hash_is_stable():
    payload = json.loads(FIXTURE.read_text())
    h1 = compute_packet_hash(payload)
    h2 = compute_packet_hash(json.loads(FIXTURE.read_text()))
    assert h1 == h2
    assert len(h1) == 64


def test_packet_hash_changes_when_payload_changes():
    payload = json.loads(FIXTURE.read_text())
    payload["ranking"]["rank"] = 2
    assert compute_packet_hash(payload) != compute_packet_hash(json.loads(FIXTURE.read_text()))


def test_packet_built_at_excluded_from_hash():
    payload = json.loads(FIXTURE.read_text())
    base_hash = compute_packet_hash(payload)
    payload["packet_built_at"] = "2026-06-02T00:00:00+00:00"
    assert compute_packet_hash(payload) == base_hash
    assert "packet_built_at" in payload
    assert "packet_built_at" not in payload_for_hash(payload)
