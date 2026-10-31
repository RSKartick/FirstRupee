from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app import seed
from app.data_sources.demo_catalog import ASSETS
from app.db.base import Base
from app.models.tables import Asset, MarketObservation


def _seed_database(tmp_path, *, live_observation: bool):
    engine = create_engine(f"sqlite:///{tmp_path / 'seed-provenance.sqlite3'}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    defn = ASSETS[0]
    if live_observation:
        asset = Asset(
            symbol=defn["symbol"], name=defn["name"], asset_type=defn["asset_type"],
            description=defn["description"], what_it_is=defn["what_it_is"], how_it_works=defn["how_it_works"],
            advantages=defn["advantages"], risks=defn["risks"], liquidity=defn["liquidity"],
            min_horizon_months=defn["min_horizon_months"], fees=defn["fees"],
            expense_ratio_pct=defn["expense_ratio_pct"], volatility_class=defn["volatility_class"],
            data_source="Live provider", data_as_of=date(2026, 10, 30), is_synthetic=False,
        )
        session.add(asset)
        session.flush()
        session.add(MarketObservation(
            asset_id=asset.id, obs_date=date(2026, 10, 30), close=Decimal("100"),
            data_type="LIVE", source="Live provider",
        ))
        session.commit()
    return engine, session, defn["symbol"]


def _failed_live_fetch(monkeypatch):
    observations = {
        item["symbol"]: ([(date(2026, 10, 31), Decimal("101"))], False, "Fallback reference")
        for item in ASSETS
    }
    monkeypatch.setattr(seed, "fetch_all_observations_with_provenance", lambda *_args, **_kwargs: observations)


def test_seed_skips_fallback_rows_when_live_history_exists(monkeypatch, tmp_path, caplog):
    engine, db, symbol = _seed_database(tmp_path, live_observation=True)
    _failed_live_fetch(monkeypatch)
    try:
        assert seed.seed_catalog(db)
        rows = list(db.scalars(
            select(MarketObservation).join(Asset).where(Asset.symbol == symbol)
        ))
        assert [row.data_type for row in rows] == ["LIVE"]
        assert f"Skipping fallback observations for {symbol}" in caplog.text
    finally:
        db.close()
        engine.dispose()


def test_seed_still_adds_sample_rows_when_no_history_exists(monkeypatch, tmp_path):
    engine, db, symbol = _seed_database(tmp_path, live_observation=False)
    _failed_live_fetch(monkeypatch)
    try:
        assert seed.seed_catalog(db)
        rows = list(db.scalars(
            select(MarketObservation).join(Asset).where(Asset.symbol == symbol)
        ))
        assert len(rows) == 1
        assert rows[0].data_type == "SAMPLE"
        assert rows[0].source == "Fallback reference"
    finally:
        db.close()
        engine.dispose()
