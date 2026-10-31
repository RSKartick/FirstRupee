"""Idempotent seeding and live refreshing of the public Indian market catalogue."""

from __future__ import annotations

import logging
import os

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.data_sources.demo_catalog import ASSETS, DATASET_AS_OF, DATASET_LABEL, fetch_all_observations
from app.models.tables import Asset, EvidenceSource, MarketObservation

logger = logging.getLogger("firstrupee.seed")


def seed_catalog(db: Session, *, force_refresh: bool = False) -> bool:
    """Add or update catalogue metadata without deleting existing assets or history."""
    now = utcnow()
    allow_network = os.environ.get("FIRSTRUPEE_OFFLINE_SEED", "").lower() not in ("1", "true", "yes")
    all_obs = fetch_all_observations(DATASET_AS_OF, allow_network=allow_network)
    changed = False

    for defn in ASSETS:
        observations = all_obs.get(defn["symbol"], [])
        last_obs_date = observations[-1][0] if observations else DATASET_AS_OF
        source_label = defn.get("data_source", DATASET_LABEL)
        asset = db.scalar(select(Asset).where(Asset.symbol == defn["symbol"]))
        is_new_asset = asset is None
        if asset is None:
            asset = Asset(symbol=defn["symbol"], is_synthetic=True)
            db.add(asset)
            changed = True

        for field in (
            "name", "asset_type", "description", "what_it_is", "how_it_works", "advantages", "risks",
            "liquidity", "min_horizon_months", "fees", "expense_ratio_pct", "volatility_class",
        ):
            setattr(asset, field, defn[field])
        # Existing classification and observation history are deliberately retained.
        if is_new_asset:
            asset.data_source = source_label
            asset.data_as_of = last_obs_date
        db.flush()

        existing_dates = set(db.scalars(
            select(MarketObservation.obs_date).where(MarketObservation.asset_id == asset.id)
        ))
        missing_observations = [(d, price) for d, price in observations if d not in existing_dates]
        if missing_observations:
            db.execute(
                insert(MarketObservation),
                [
                    {
                        "asset_id": asset.id,
                        "obs_date": d,
                        "close": price,
                        # The fetcher may return a generated fallback when a provider is unavailable.
                        "data_type": "SYNTHETIC",
                        "source": DATASET_LABEL,
                        "retrieved_at": now,
                    }
                    for d, price in missing_observations
                ],
            )
            changed = True
        for item in defn["evidence"]:
            evidence = db.scalar(select(EvidenceSource).where(EvidenceSource.evidence_key == item["key"]))
            if evidence is None:
                evidence = EvidenceSource(
                    evidence_key=item["key"], asset_id=asset.id, verification_status="SYNTHETIC"
                )
                db.add(evidence)
                changed = True
            evidence.title = item["title"]
            evidence.source_type = item["source_type"]
            evidence.source_url = item.get("source_url")
            evidence.publication_date = item["publication_date"]
            evidence.period = item["period"]
            evidence.summary = item["summary"]
            evidence.payload = item["payload"]
            evidence.retrieved_at = now
    db.commit()
    if changed:
        logger.info("Updated public market catalogue metadata while preserving existing history.")
    return changed
