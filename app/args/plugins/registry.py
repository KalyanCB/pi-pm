from __future__ import annotations

from app.args.plugins.base import CommitteePlugin
from app.args.plugins.frc import FrcCommitteePlugin
from app.args.plugins.nrcc import NrccCommitteePlugin
from app.args.plugins.qrc import QrcCommitteePlugin
from app.args.plugins.rc import RcCommitteePlugin
from app.args.plugins.tarc import TarcCommitteePlugin
from app.workspace_args.constants import DEFAULT_COMMITTEE_CODES


class CommitteeRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, CommitteePlugin] = {}
        for plugin in (
            TarcCommitteePlugin(),
            FrcCommitteePlugin(),
            QrcCommitteePlugin(),
            NrccCommitteePlugin(),
            RcCommitteePlugin(),
        ):
            self.register(plugin)

    def register(self, plugin: CommitteePlugin) -> None:
        self._plugins[plugin.committee_code] = plugin

    def get(self, committee_code: str) -> CommitteePlugin:
        plugin = self._plugins.get(committee_code)
        if plugin is None:
            raise KeyError(f"Unknown committee: {committee_code}")
        return plugin

    def resolve(self, committee_codes: list[str] | None) -> list[CommitteePlugin]:
        codes = committee_codes or list(DEFAULT_COMMITTEE_CODES)
        return [self.get(code) for code in codes]
