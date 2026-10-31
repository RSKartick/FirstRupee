"""Idempotent seeding of the synthetic catalogue. Demo investors are NOT created here: each visitor receives a private copy."""

from __future__ import annotations

import logging

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.data_sources.demo_catalog import ASSETS, DATASET_AS_OF, DATASET_LABEL, generate_observations
from app.models.tables import Asset, EvidenceSource, MarketObservation

logger = logging.getLogger("firstrupee.seed")


def seed_catalog(db: Session) -> bool:
    """Returns True when rows were inserted. Existing catalogues are left untouched."""
    if db.scalar(select(func.count(Asset.id))):
        return False
    now = utcnow()
    for defn in ASSETS:
        asset = Asset(
            symbol=defn["symbol"],
            name=defn["name"],
            asset_type=defn["asset_type"],
            description=defn["description"],
            what_it_is=defn["what_it_is"],
            how_it_works=defn["how_it_works"],
            advantages=defn["advantages"],
            risks=defn["risks"],
            liquidity=defn["liquidity"],
            min_horizon_months=defn["min_horizon_months"],
            fees=defn["fees"],
            expense_ratio_pct=defn["expense_ratio_pct"],
            volatility_class=defn["volatility_class"],
            data_source=DATASET_LABEL,
            data_as_of=DATASET_AS_OF,
            is_synthetic=True,
        )
        db.add(asset)
        db.flush()
        observations = generate_observations(defn, DATASET_AS_OF)
        db.execute(
            insert(MarketObservation),
            [
                {"asset_id": asset.id, "obs_date": d, "close": price, "data_type": "SYNTHETIC",
                 "source": DATASET_LABEL, "retrieved_at": now}
                for d, price in observations
            ],
        )
        for item in defn["evidence"]:
            db.add(
                EvidenceSource(
                    evidence_key=item["key"],
                    asset_id=asset.id,
                    title=item["title"],
                    source_type=item["source_type"],
                    verification_status="SYNTHETIC",
                    source_url=None,
                    publication_date=item["publication_date"],
                    period=item["period"],
                    retrieved_at=now,
                    summary=item["summary"],
                    payload=item["payload"],
                )
            )
    db.commit()
    logger.info("Seeded synthetic catalogue with %d instruments.", len(ASSETS))
    return True

