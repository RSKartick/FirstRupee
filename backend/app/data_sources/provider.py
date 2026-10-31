"""Provider-independent market-data boundary.

The application reads prices and evidence through this interface. PublicMarketDataProvider serves real Indian market instruments
backed by Yahoo Finance v8 API (NSE equities/ETFs) and AMFI MFAPI.in (direct mutual fund NAVs), persisted in SQLite for fast,
deterministic evaluation and simulation.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import EvidenceSource, MarketObservation
from app.services.ai_engine.evaluator import EvidenceView


class MarketDataProvider(Protocol):
    id: str
    is_live: bool
    attribution: str

    def observations(self, db: Session, asset_id: int) -> list[tuple[date, Decimal]]: ...

    def evidence(self, db: Session, asset_id: int) -> list[EvidenceView]: ...


class PublicMarketDataProvider:
    id = "nse-amfi-public-market-data"
    is_live = True
    attribution = "Real Indian market historical prices and NAVs via Yahoo Finance (NSE) and AMFI (api.mfapi.in), plus audited filings and statutory fund factsheets."

    def observations(self, db: Session, asset_id: int) -> list[tuple[date, Decimal]]:
        rows = db.execute(
            select(MarketObservation.obs_date, MarketObservation.close)
            .where(MarketObservation.asset_id == asset_id)
            .order_by(MarketObservation.obs_date)
        ).all()
        return [(row.obs_date, Decimal(str(row.close))) for row in rows]

    def evidence(self, db: Session, asset_id: int) -> list[EvidenceView]:
        rows = db.scalars(
            select(EvidenceSource).where(EvidenceSource.asset_id == asset_id).order_by(EvidenceSource.evidence_key)
        ).all()
        return [
            EvidenceView(
                key=row.evidence_key,
                asset_id=row.asset_id,
                title=row.title,
                source_type=row.source_type,
                verification_status=row.verification_status,
                publication_date=row.publication_date,
                period=row.period,
                summary=row.summary,
                payload={k: str(v) for k, v in (row.payload or {}).items()},
            )
            for row in rows
        ]


def get_provider() -> MarketDataProvider:
    return PublicMarketDataProvider()
