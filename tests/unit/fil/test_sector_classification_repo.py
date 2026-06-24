"""Tests for SectorClassificationRepository (ADR-039) — also covers the seed path."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.repositories.sector_classification_repository import SectorClassificationRepository
from app.models.stock import Stock


def _stock(db: Session, symbol: str, sector: str | None, industry: str | None = None) -> Stock:
    s = Stock(symbol=symbol, name=symbol, exchange="NSE", sector=sector, industry=industry)
    db.add(s)
    db.flush()
    return s


def test_upsert_inserts_then_updates(db_session: Session):
    repo = SectorClassificationRepository(db_session)
    stock = _stock(db_session, "RVNL", "Railways", "Rail Infra")

    row = repo.upsert(stock_id=stock.id, sector="Railways", sub_sector="Rail Infra")
    assert row.sector == "Railways"
    assert row.sub_sector == "Rail Infra"

    # Same (stock, sector) → updates in place, no duplicate.
    again = repo.upsert(stock_id=stock.id, sector="Railways", sub_sector="Construction")
    assert again.id == row.id
    assert again.sub_sector == "Construction"


def test_lookups_by_sector_and_stock(db_session: Session):
    repo = SectorClassificationRepository(db_session)
    a = _stock(db_session, "RVNL", "Railways")
    b = _stock(db_session, "IRFC", "Railways")
    c = _stock(db_session, "SUNPHARMA", "Pharma")
    for s in (a, b, c):
        repo.upsert(stock_id=s.id, sector=s.sector)

    railways = set(repo.stock_ids_for_sector("Railways"))
    assert railways == {a.id, b.id}
    assert repo.sector_for_stock(c.id) == "Pharma"


def test_seed_skips_stocks_without_sector(db_session: Session):
    """Mirror of scripts/seed_sector_classifications: only stocks with a sector seed."""
    repo = SectorClassificationRepository(db_session)
    with_sector = _stock(db_session, "RVNL", "Railways", "Rail Infra")
    _stock(db_session, "NOSEC", None)

    all_stocks = db_session.query(Stock).all()
    seeded = 0
    for s in all_stocks:
        if s.sector:
            repo.upsert(stock_id=s.id, sector=s.sector, sub_sector=s.industry)
            seeded += 1

    assert seeded == 1
    assert repo.sector_for_stock(with_sector.id) == "Railways"
