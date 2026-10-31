"""Idempotent seeding and live refreshing of the public Indian market catalogue."""

from __future__ import annotations

import logging
import os

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.data_sources.demo_catalog import ASSETS, DATASET_AS_OF, DATASET_LABEL, fetch_all_observations_with_provenance
from app.models.tables import Asset, EvidenceSource, MarketObservation

logger = logging.getLogger("firstrupee.seed")


def seed_catalog(db: Session, *, force_refresh: bool = False) -> bool:
    """Add or update catalogue metadata and market observations."""
    now = utcnow()
    allow_network = os.environ.get("FIRSTRUPEE_OFFLINE_SEED", "").lower() not in ("1", "true", "yes")
    all_obs = fetch_all_observations_with_provenance(DATASET_AS_OF, allow_network=allow_network)
    changed = False

    for defn in ASSETS:
        observations, is_live_fetched, source_label = all_obs.get(
            defn["symbol"], ([], False, defn.get("data_source", DATASET_LABEL))
        )
        last_obs_date = observations[-1][0] if observations else DATASET_AS_OF
        asset = db.scalar(select(Asset).where(Asset.symbol == defn["symbol"]))
        is_new_asset = asset is None
        if asset is None:
            asset = Asset(symbol=defn["symbol"], is_synthetic=False)
            db.add(asset)
            changed = True

        has_live_rows = False
        if not is_new_asset:
            has_live_rows = db.scalar(
                select(MarketObservation.id).where(
                    MarketObservation.asset_id == asset.id, MarketObservation.data_type == "LIVE"
                ).limit(1)
            ) is not None

        for field in (
            "name", "asset_type", "description", "what_it_is", "how_it_works", "advantages", "risks",
            "liquidity", "min_horizon_months", "fees", "expense_ratio_pct", "volatility_class",
        ):
            setattr(asset, field, defn[field])
        asset.is_synthetic = False
        if is_new_asset or (force_refresh and (is_live_fetched or not has_live_rows)):
            asset.data_source = source_label
            asset.data_as_of = last_obs_date
            changed = True
        db.flush()

        obs_data_type = "LIVE" if is_live_fetched else "SAMPLE"
        if has_live_rows and not is_live_fetched:
            logger.warning("Skipping fallback observations for %s because LIVE history is already stored.", defn["symbol"])
            existing_dates = set(db.scalars(
                select(MarketObservation.obs_date).where(MarketObservation.asset_id == asset.id)
            ))
            missing_observations = []
        elif force_refresh and observations:
            db.execute(delete(MarketObservation).where(MarketObservation.asset_id == asset.id))
            existing_dates: set = set()
            missing_observations = list(observations)
        else:
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
                        "data_type": obs_data_type,
                        "source": source_label,
                        "retrieved_at": now,
                    }
                    for d, price in missing_observations
                ],
            )
            changed = True
        for item in defn["evidence"]:
            evidence = db.scalar(select(EvidenceSource).where(EvidenceSource.evidence_key == item["key"]))
            verified_status = item.get("verification_status") or ("VERIFIED" if item.get("source_url") else "SYNTHETIC")
            if evidence is None:
                evidence = EvidenceSource(
                    evidence_key=item["key"], asset_id=asset.id, verification_status=verified_status
                )
                db.add(evidence)
                changed = True
            evidence.verification_status = verified_status
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
        logger.info("Updated public market catalogue metadata and observations (force_refresh=%s).", force_refresh)
    return changed
