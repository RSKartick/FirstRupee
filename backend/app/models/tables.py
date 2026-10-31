"""ORM models.

Ownership model: every user-owned row carries `user_id` (or reaches it through a profile whose `user_id` is checked).
All repository reads filter by the authenticated user, so an id guessed from another account returns "not found".
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utcnow
from app.db.base import Base
from app.db.types import Money, Pct


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_guest: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    profiles: Mapped[list[InvestorProfile]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    token_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class InvestorProfile(Base):
    __tablename__ = "investor_profiles"
    __table_args__ = (Index("ix_investor_profiles_user_updated", "user_id", "updated_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    age_range: Mapped[str] = mapped_column(String(30), nullable=False)
    employment_status: Mapped[str] = mapped_column(String(30), nullable=False)

    monthly_income: Mapped[Decimal] = mapped_column(Money, nullable=False)
    essential_expenses: Mapped[Decimal] = mapped_column(Money, nullable=False)
    nonessential_expenses: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))
    monthly_emi: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))
    other_commitments: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))

    total_savings: Mapped[Decimal] = mapped_column(Money, nullable=False)
    liquid_savings: Mapped[Decimal] = mapped_column(Money, nullable=False)
    emergency_reserves: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))
    goal_reserved_amount: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))
    current_investments: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))
    existing_liabilities: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))
    monthly_investment_designated: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0"))

    investment_experience: Mapped[str] = mapped_column(String(20), nullable=False)
    goal_name: Mapped[str | None] = mapped_column(String(120))
    goal_category: Mapped[str | None] = mapped_column(String(30))
    goal_amount: Mapped[Decimal | None] = mapped_column(Money)
    goal_deadline: Mapped[date | None] = mapped_column(Date)
    goal_importance: Mapped[str | None] = mapped_column(String(10))
    goal_liquidity: Mapped[str | None] = mapped_column(String(10))
    questionnaire: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    is_demo_clone: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    demo_key: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="profiles")
    debts: Mapped[list[ProfileDebt]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", passive_deletes=True, order_by="ProfileDebt.id"
    )


class ProfileDebt(Base):
    __tablename__ = "profile_debts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("investor_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    debt_type: Mapped[str] = mapped_column(String(30), nullable=False)
    outstanding_amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    interest_rate_pct: Mapped[Decimal] = mapped_column(Pct, nullable=False)
    emi_amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    remaining_months: Mapped[int] = mapped_column(Integer, nullable=False)
    is_overdue: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    profile: Mapped[InvestorProfile] = relationship(back_populates="debts")


class ReadinessResultRow(Base):
    """Cached readiness output. Reused only when the profile timestamp, rule version AND reference date all match."""

    __tablename__ = "readiness_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("investor_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    rule_version: Mapped[str] = mapped_column(String(40), nullable=False)
    profile_updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    as_of: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    what_it_is: Mapped[str] = mapped_column(Text, nullable=False)
    how_it_works: Mapped[str] = mapped_column(Text, nullable=False)
    advantages: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    risks: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    liquidity: Mapped[str] = mapped_column(Text, nullable=False)
    min_horizon_months: Mapped[int] = mapped_column(Integer, nullable=False)
    fees: Mapped[str] = mapped_column(Text, nullable=False)
    expense_ratio_pct: Mapped[Decimal | None] = mapped_column(Pct)
    volatility_class: Mapped[str] = mapped_column(String(10), nullable=False)
    data_source: Mapped[str] = mapped_column(String(200), nullable=False)
    data_as_of: Mapped[date] = mapped_column(Date, nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class MarketObservation(Base):
    __tablename__ = "market_observations"
    __table_args__ = (UniqueConstraint("asset_id", "obs_date", name="uq_market_observations_asset_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False)
    obs_date: Mapped[date] = mapped_column(Date, nullable=False)
    close: Mapped[Decimal] = mapped_column(Money, nullable=False)
    data_type: Mapped[str] = mapped_column(String(12), nullable=False)  # SYNTHETIC | SAMPLE | LIVE
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class EvidenceSource(Base):
    __tablename__ = "evidence_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evidence_key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)  # VERIFIED | UNVERIFIED | SYNTHETIC
    source_url: Mapped[str | None] = mapped_column(String(500))  # never invented: demo records keep this NULL
    publication_date: Mapped[date | None] = mapped_column(Date)
    period: Mapped[str | None] = mapped_column(String(20))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)


class ResearchAnalysisRow(Base):
    __tablename__ = "research_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("investor_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    evaluator_status: Mapped[str] = mapped_column(String(40), nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class SimulationRow(Base):
    __tablename__ = "simulation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("investor_profiles.id", ondelete="CASCADE"), index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    scenario_type: Mapped[str] = mapped_column(String(30), nullable=False)
    amount_source: Mapped[str] = mapped_column(String(30), nullable=False)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class DecisionPassportRow(Base):
    """Immutable snapshot. Reads return the stored JSON; they never recompute it, so later rule changes cannot rewrite it."""

    __tablename__ = "decision_passports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("investor_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    research_analysis_id: Mapped[int | None] = mapped_column(ForeignKey("research_analyses.id", ondelete="SET NULL"))
    simulation_id: Mapped[int | None] = mapped_column(ForeignKey("simulation_results.id", ondelete="SET NULL"))
    schema_version: Mapped[str] = mapped_column(String(30), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class ChatMessageRow(Base):
    """Persistent chatbot conversation history scoped to the authenticated user account across all sessions."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("investor_profiles.id", ondelete="SET NULL"), index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
