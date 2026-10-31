"""Owner-scoped data access. Every user-owned query takes the authenticated user id as a required argument, so a record that belongs to
another account is indistinguishable from a record that does not exist."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.tables import (
    Asset,
    AuthSession,
    ChatMessageRow,
    DecisionPassportRow,
    InvestorProfile,
    ReadinessResultRow,
    ResearchAnalysisRow,
    SimulationRow,
    User,
)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_session_by_digest(db: Session, digest: str) -> AuthSession | None:
    return db.scalar(select(AuthSession).where(AuthSession.token_digest == digest))


def get_profile(db: Session, user_id: int, profile_id: int) -> InvestorProfile | None:
    return db.scalar(select(InvestorProfile).where(InvestorProfile.id == profile_id, InvestorProfile.user_id == user_id))


def list_profiles(db: Session, user_id: int) -> list[InvestorProfile]:
    return list(db.scalars(select(InvestorProfile).where(InvestorProfile.user_id == user_id).order_by(InvestorProfile.updated_at.desc())).all())


def latest_readiness(db: Session, profile_id: int) -> ReadinessResultRow | None:
    return db.scalar(
        select(ReadinessResultRow).where(ReadinessResultRow.profile_id == profile_id).order_by(ReadinessResultRow.id.desc()).limit(1)
    )


def get_research(db: Session, user_id: int, research_id: int) -> ResearchAnalysisRow | None:
    return db.scalar(select(ResearchAnalysisRow).where(ResearchAnalysisRow.id == research_id, ResearchAnalysisRow.user_id == user_id))


def list_research(db: Session, user_id: int, profile_id: int, limit: int = 20) -> list[ResearchAnalysisRow]:
    return list(db.scalars(
        select(ResearchAnalysisRow)
        .where(ResearchAnalysisRow.user_id == user_id, ResearchAnalysisRow.profile_id == profile_id)
        .order_by(ResearchAnalysisRow.id.desc()).limit(limit)
    ).all())


def get_simulation(db: Session, user_id: int, simulation_id: int) -> SimulationRow | None:
    return db.scalar(select(SimulationRow).where(SimulationRow.id == simulation_id, SimulationRow.user_id == user_id))


def list_simulations(db: Session, user_id: int, profile_id: int, limit: int = 5) -> list[SimulationRow]:
    return list(db.scalars(
        select(SimulationRow)
        .where(SimulationRow.user_id == user_id, SimulationRow.profile_id == profile_id)
        .order_by(SimulationRow.id.desc()).limit(limit)
    ).all())


def get_passport(db: Session, user_id: int, passport_id: int) -> DecisionPassportRow | None:
    return db.scalar(select(DecisionPassportRow).where(DecisionPassportRow.id == passport_id, DecisionPassportRow.user_id == user_id))


def list_passports(db: Session, user_id: int, profile_id: int, limit: int = 50) -> list[DecisionPassportRow]:
    return list(db.scalars(
        select(DecisionPassportRow)
        .where(DecisionPassportRow.user_id == user_id, DecisionPassportRow.profile_id == profile_id)
        .order_by(DecisionPassportRow.id.desc())
        .limit(limit)
    ).all())


def get_asset(db: Session, asset_id: int) -> Asset | None:
    return db.get(Asset, asset_id)


def list_chat_messages(db: Session, user_id: int, limit: int = 100) -> list[ChatMessageRow]:
    rows = list(
        db.scalars(
            select(ChatMessageRow)
            .where(ChatMessageRow.user_id == user_id)
            .order_by(ChatMessageRow.id.desc())
            .limit(limit)
        ).all()
    )
    rows.reverse()
    return rows


def add_chat_message(
    db: Session,
    user_id: int,
    profile_id: int | None,
    role: str,
    content: str,
    meta: dict | None = None,
) -> ChatMessageRow:
    row = ChatMessageRow(user_id=user_id, profile_id=profile_id, role=role, content=content, meta=meta)
    db.add(row)
    db.flush()
    return row


def clear_chat_messages(db: Session, user_id: int) -> None:
    db.execute(delete(ChatMessageRow).where(ChatMessageRow.user_id == user_id))
    db.commit()
