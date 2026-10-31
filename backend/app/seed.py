"""Idempotent seeding and live refreshing of the public Indian market catalogue."""

from __future__ import annotations

import logging
import os

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.data_sources.demo_catalog import ASSETS, DATASET_AS_OF, DATASET_LABEL, fetch_all_observations
from app.models.tables import Asset, EvidenceSource, MarketObservation

logger = logging.getLogger("firstrupee.seed")


def seed_catalog(db: Session, *, force_refresh: bool = False) -> bool:
    """Seeds or upgrades the public market catalogue. Replaces legacy synthetic rows automatically."""
    existing_count = db.scalar(select(func.count(Asset.id))) or 0
    has_synthetic = (db.scalar(select(func.count(Asset.id)).where(Asset.is_synthetic.is_(True))) or 0) > 0

    if existing_count > 0 and not has_synthetic and not force_refresh:
        return False

    if existing_count > 0:
        logger.info("Upgrading or refreshing market catalogue (existing=%d, has_synthetic=%s, force=%s).",
                    existing_count, has_synthetic, force_refresh)
        db.execute(delete(MarketObservation))
        db.execute(delete(EvidenceSource))
        db.execute(delete(Asset))
        db.flush()

    now = utcnow()
    allow_network = os.environ.get("FIRSTRUPEE_OFFLINE_SEED", "").lower() not in ("1", "true", "yes")
    all_obs = fetch_all_observations(DATASET_AS_OF, allow_network=allow_network)

    for defn in ASSETS:
        observations = all_obs.get(defn["symbol"], [])
        last_obs_date = observations[-1][0] if observations else DATASET_AS_OF
        source_label = defn.get("data_source", DATASET_LABEL)
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
            data_source=source_label,
            data_as_of=last_obs_date,
            is_synthetic=False,
        )
        db.add(asset)
        db.flush()
        if observations:
            db.execute(
                insert(MarketObservation),
                [
                    {
                        "asset_id": asset.id,
                        "obs_date": d,
                        "close": price,
                        "data_type": "LIVE",
                        "source": source_label,
                        "retrieved_at": now,
                    }
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
                    verification_status="VERIFIED",
                    source_url=item.get("source_url"),
                    publication_date=item["publication_date"],
                    period=item["period"],
                    retrieved_at=now,
                    summary=item["summary"],
                    payload=item["payload"],
                )
            )
    db.commit()
    logger.info("Seeded public Indian market catalogue with %d real instruments.", len(ASSETS))
    return True
