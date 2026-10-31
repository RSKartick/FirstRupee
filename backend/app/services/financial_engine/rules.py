"""Versioned rule constants.

Every threshold is an EDUCATIONAL GUARDRAIL chosen for first-time investors. They are not universal financial rules,
not validated psychometric scales, not investment advice and not a regulatory determination. Each rule set carries a
version string that is stored with every result, so a later change cannot silently rewrite an earlier conclusion.

Rationale summary
- Emergency floor 2 months / target 6 months: below 2 months an income shock forces selling into a market fall; 6 months
  is a widely used planning baseline for salaried households and is conservative for self-employed households.
- EMI burden 30% warning / 45% blocker: above 45% of take-home pay there is little room to absorb any volatility.
- Surplus under 10% of income is "thin": one unplanned expense consumes the whole surplus.
- Horizon under 12 months is treated as short-term money, which is not long-term risk capital.
- High-interest debt above 15% per year usually costs more than typical long-run investment outcomes assumed by beginners.
- Capacity caps are deliberately blunt: a single failed condition should prevent a "high capacity" label.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

READINESS_RULE_VERSION = "readiness-rules-v2.1"
TIMING_RULE_VERSION = "timing-rules-v2.0"
SIMULATOR_VERSION = "simulator-v2.0"
EVALUATOR_VERSION = "evaluator-rules-v2.0"
PROMPT_VERSION = "prompts-v2.0"
PASSPORT_SCHEMA_VERSION = "passport-v2.0"
MARKET_STALE_AFTER_DAYS = 45


@dataclass(frozen=True)
class ReadinessThresholds:
    emergency_floor_months: Decimal = Decimal("2")
    emergency_target_months: Decimal = Decimal("6")
    emergency_replenish_months: int = 12
    emi_warning_ratio: Decimal = Decimal("0.30")
    emi_blocker_ratio: Decimal = Decimal("0.45")
    thin_surplus_ratio: Decimal = Decimal("0.10")
    capacity_surplus_full_ratio: Decimal = Decimal("0.30")
    short_horizon_months: int = 12
    medium_horizon_months: int = 36
    high_interest_pct: Decimal = Decimal("15")
    high_debt_to_annual_income: Decimal = Decimal("1.0")
    ready_capacity_min: int = 55
    ready_tolerance_min: int = 40
    capacity_low_max: int = 55
    capacity_high_min: int = 70
    tolerance_low_max: int = 40
    tolerance_high_min: int = 70
    cap_loss_affects_essentials: int = 30
    cap_irregular_income: int = 55
    cap_high_liquidity_goal: int = 40
    cap_coverage_below_floor: int = 25
    cap_no_surplus: int = 20
    cap_overdue_debt: int = 25


READINESS = ReadinessThresholds()
