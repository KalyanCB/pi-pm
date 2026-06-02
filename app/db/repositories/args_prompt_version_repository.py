from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.args import PromptVersion


class ArgsPromptVersionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create_stub(self, committee_code: str, version: str = "1.0.0") -> PromptVersion:
        existing = self.db.scalar(
            select(PromptVersion).where(
                PromptVersion.committee_code == committee_code,
                PromptVersion.version == version,
            )
        )
        if existing is not None:
            return existing
        template = f"stub-prompt-{committee_code}-{version}"
        template_hash = hashlib.sha256(template.encode()).hexdigest()
        row = PromptVersion(
            committee_code=committee_code,
            version=version,
            template=template,
            template_hash=template_hash,
            created_at=datetime.now(UTC),
        )
        self.db.add(row)
        self.db.flush()
        return row
