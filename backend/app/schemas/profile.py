"""Investor profile contracts and the cross-field financial validation layer.

Frontend validation is a convenience only. The rules below are the authority: they are enforced on every create and update.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import Money, Pct

AgeRange = Literal["TEN_TO_TWENTY", "TWENTY_TO_THIRTY", "THIRTY_TO_FORTY", "FORTY_TO_SIXTY", "SIXTY_PLUS"]
EmploymentStatus = Literal["SALARIED", "SELF_EMPLOYED", "BUSINESS", "STUDENT", "RETIRED", "NOT_EMPLOYED"]
Experience = Literal["BEGINNER", "INTERMEDIATE", "EXPERIENCED"]
GoalCategory = Literal["WEALTH_CREATION", "EDUCATION", "HOME_PURCHASE", "RETIREMENT", "EMERGENCY_RESERVE", "OTHER"]
Level = Literal["LOW", "MEDIUM", "HIGH"]
DebtType = Literal["HOME_LOAN", "PERSONAL_LOAN", "CAR_LOAN", "CREDIT_CARD", "EDUCATION_LOAN", "OTHER"]
DrawdownReaction = Literal["SELL_IMMEDIATELY", "WAIT", "REASSESS_THESIS", "ADD_IF_THESIS_VALID"]
PreferredHorizon = Literal["UNDER_1_YEAR", "ONE_TO_THREE_YEARS", "THREE_TO_SEVEN_YEARS", "OVER_SEVEN_YEARS"]
GainsReaction = Literal["KEEP_PLAN", "INVEST_MORE_ON_GAINS", "WITHDRAW_SOME"]
LossImpact = Literal["NO_IMPACT", "TIGHTEN_BUDGET", "AFFECTS_ESSENTIALS"]
IncomeStability = Literal["VERY_STABLE", "SOMEWHAT_STABLE", "IRREGULAR"]


class DebtIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    debt_type: DebtType
    outstanding_amount: Money
    interest_rate_pct: Pct
    emi_amount: Money
    remaining_months: int = Field(ge=0, le=600)
    is_overdue: bool = False


class QuestionnaireIn(BaseModel):
    """Behavioural questions (tolerance) and capacity questions are kept in separate fields and scored separately."""

    model_config = ConfigDict(extra="forbid")

    drawdown_reaction: DrawdownReaction
    preferred_horizon: PreferredHorizon
    gains_reaction: GainsReaction
    loss_impact_on_expenses: LossImpact
    income_stability: IncomeStability


class ProfileIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=2, max_length=80)
    age_range: AgeRange
    employment_status: EmploymentStatus
    monthly_income: Money
    essential_expenses: Money
    nonessential_expenses: Money = Decimal("0")
    monthly_emi: Money = Decimal("0")
    other_commitments: Money = Decimal("0")
    total_savings: Money
    liquid_savings: Money
    emergency_reserves: Money = Decimal("0")
    goal_reserved_amount: Money = Decimal("0")
    current_investments: Money = Decimal("0")
    existing_liabilities: Money = Decimal("0")
    monthly_investment_designated: Money = Decimal("0")
    debts: list[DebtIn] = Field(default_factory=list, max_length=20)
    investment_experience: Experience
    goal_name: str | None = Field(default=None, max_length=120)
    goal_category: GoalCategory | None = None
    goal_amount: Money | None = None
    goal_deadline: date | None = None
    goal_importance: Level | None = None
    goal_liquidity: Level | None = None
    questionnaire: QuestionnaireIn | None = None

    @model_validator(mode="after")
    def _cross_field_rules(self) -> ProfileIn:
        errors: list[str] = []
        if self.monthly_income <= 0:
            errors.append("monthly_income must be greater than zero")
        if self.liquid_savings > self.total_savings:
            errors.append("liquid_savings cannot exceed total_savings")
        if self.emergency_reserves > self.liquid_savings:
            errors.append("emergency_reserves cannot exceed liquid_savings")
        if self.goal_reserved_amount > self.liquid_savings:
            errors.append("goal_reserved_amount cannot exceed liquid_savings")
        if self.emergency_reserves + self.goal_reserved_amount > self.liquid_savings:
            errors.append("emergency_reserves plus goal_reserved_amount cannot exceed liquid_savings (the same rupee cannot be reserved twice)")
        if self.debts:
            emi_total = sum((debt.emi_amount for debt in self.debts), Decimal("0"))
            outstanding_total = sum((debt.outstanding_amount for debt in self.debts), Decimal("0"))
            if emi_total != self.monthly_emi:
                errors.append("monthly_emi must equal the sum of loan EMIs listed in debts (EMIs must not be counted twice)")
            if outstanding_total != self.existing_liabilities:
                errors.append("existing_liabilities must equal the sum of outstanding amounts listed in debts")
        if self.goal_amount is not None and self.goal_deadline is None:
            errors.append("goal_deadline is required when goal_amount is entered")
        if errors:
            raise ValueError("; ".join(errors))
        return self


class DebtOut(BaseModel):
    id: int
    debt_type: str
    outstanding_amount: Money
    interest_rate_pct: Pct
    emi_amount: Money
    remaining_months: int
    is_overdue: bool


class ProfileOut(BaseModel):
    id: int
    display_name: str
    age_range: str
    employment_status: str
    monthly_income: Money
    essential_expenses: Money
    nonessential_expenses: Money
    monthly_emi: Money
    other_commitments: Money
    total_savings: Money
    liquid_savings: Money
    emergency_reserves: Money
    goal_reserved_amount: Money
    current_investments: Money
    existing_liabilities: Money
    monthly_investment_designated: Money
    debts: list[DebtOut]
    investment_experience: str
    goal_name: str | None
    goal_category: str | None
    goal_amount: Money | None
    goal_deadline: date | None
    goal_importance: str | None
    goal_liquidity: str | None
    questionnaire: dict[str, str] | None
    is_demo_clone: bool
    demo_key: str | None
    created_at: datetime
    updated_at: datetime


class ProfileSummary(BaseModel):
    id: int
    display_name: str
    monthly_income: Money
    goal_name: str | None
    is_demo_clone: bool
    updated_at: datetime
