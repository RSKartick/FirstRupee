"""Request contracts for analysis endpoints. Responses for analysis are versioned JSON snapshots produced by the engines."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Money, Pct

MarketPath = Literal["HISTORICAL", "ZERO_RETURN", "HYPOTHETICAL_UP", "HYPOTHETICAL_DOWN", "SEEDED_GBM"]
ScenarioType = Literal["LUMP_SUM", "STAGED_INITIAL", "DELAYED_START", "COMPARISON"]
AmountSource = Literal["PROFILE_DERIVED", "USER_HYPOTHETICAL"]


class ProfileRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: int = Field(gt=0)


class TimingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: int = Field(gt=0)
    asset_id: int | None = Field(default=None, gt=0)


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: int = Field(gt=0)
    asset_id: int = Field(gt=0)


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: int | None = Field(default=None, gt=0)
    asset_id: int = Field(gt=0)
    compare_asset_id: int | None = Field(default=None, gt=0)
    scenario_type: ScenarioType
    amount_source: AmountSource = "USER_HYPOTHETICAL"
    initial_amount: Money | None = None
    monthly_contribution: Money | None = None
    contribution_frequency: Literal["MONTHLY", "QUARTERLY"] = "MONTHLY"
    duration_months: int = Field(ge=1, le=360)
    evaluation_date: date | None = None
    market_path: MarketPath = "HISTORICAL"
    cash_interest_pct: Pct = Decimal("3.5")
    delay_months: int = Field(default=0, ge=0, le=360)
    seed: int = Field(default=42, ge=0, le=1_000_000_000)


class PassportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: int = Field(gt=0)
    research_analysis_id: int | None = Field(default=None, gt=0)
    simulation_id: int | None = Field(default=None, gt=0)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: int | None = Field(default=None, gt=0)
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)
