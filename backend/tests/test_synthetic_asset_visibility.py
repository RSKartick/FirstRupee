from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.tables import Asset


def test_legacy_synthetic_assets_are_hidden_but_preserved(new_client):
    symbol = "SYN-TEST-HIDDEN"
    with SessionLocal() as db:
        asset = Asset(
            symbol=symbol,
            name="Legacy fictional test asset",
            asset_type="ETF",
            description="Test-only legacy row",
            what_it_is="Test-only",
            how_it_works="Test-only",
            advantages=[],
            risks=[],
            liquidity="Test-only",
            min_horizon_months=1,
            fees="Test-only",
            volatility_class="LOW",
            data_source="Test",
            data_as_of=date(2026, 10, 31),
            is_synthetic=True,
        )
        db.add(asset)
        db.commit()
        asset_id = asset.id

    try:
        listed = new_client.get("/api/assets")
        assert listed.status_code == 200
        assert symbol not in {item["symbol"] for item in listed.json()["assets"]}
        assert new_client.get(f"/api/assets/{asset_id}").status_code == 404
        assert new_client.get(f"/api/assets/{asset_id}/history").status_code == 404

        with SessionLocal() as db:
            preserved = db.scalar(select(Asset).where(Asset.id == asset_id))
            assert preserved is not None
            assert preserved.symbol == symbol
            assert preserved.is_synthetic is True
    finally:
        with SessionLocal() as db:
            row = db.scalar(select(Asset).where(Asset.id == asset_id))
            if row is not None:
                db.delete(row)
                db.commit()
