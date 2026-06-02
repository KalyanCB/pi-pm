from app.args.plugins.registry import CommitteeRegistry
from app.workspace_args.constants import COMMITTEE_QRC, COMMITTEE_TARC


def test_registry_has_phase1_committees():
    reg = CommitteeRegistry()
    codes = {p.committee_code for p in reg.resolve(None)}
    assert COMMITTEE_TARC in codes
    assert COMMITTEE_QRC in codes
    assert len(codes) == 5


def test_registry_resolve_subset():
    reg = CommitteeRegistry()
    plugins = reg.resolve(["TARC", "QRC"])
    assert [p.committee_code for p in plugins] == ["TARC", "QRC"]
