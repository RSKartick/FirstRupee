"""Scheme growth calculator and profile fit recommendation engine."""

from __future__ import annotations

from decimal import Decimal
import math
from typing import Any

from app.services.schemes.catalog import SCHEMES, SCHEMES_MAP, SchemeRule


def calculate_scheme_growth(
    scheme_id: str,
    monthly_deposit: float = 0.0,
    lump_sum: float = 0.0,
    horizon_years: int | None = None,
    tax_bracket_pct: float = 30.0,
) -> dict[str, Any]:
    scheme = SCHEMES_MAP.get(scheme_id.lower())
    if scheme is None:
        raise ValueError(f"Unknown scheme ID: {scheme_id}")

    years = horizon_years if horizon_years and horizon_years > 0 else scheme.lock_in_years
    # Cap years reasonably
    years = max(1, min(years, 40))

    rate = scheme.interest_rate_pct / 100.0
    r_monthly = rate / 12.0

    total_deposited = 0.0
    balance = lump_sum
    total_deposited += lump_sum

    schedule: list[dict[str, Any]] = []

    for year in range(1, years + 1):
        opening = balance
        deposited_this_year = 0.0
        interest_this_year = 0.0

        if scheme.compounding_frequency == "ANNUAL":
            # Contributions made monthly, interest computed and credited annually
            for _ in range(12):
                balance += monthly_deposit
                deposited_this_year += monthly_deposit
            # Simplified annual compounding with mid-year average contribution balance
            interest_this_year = (opening + (deposited_this_year / 2.0)) * rate
            balance += interest_this_year

        elif scheme.compounding_frequency in ("QUARTERLY", "QUARTERLY_PAYOUT"):
            r_quarter = rate / 4.0
            for _ in range(4):
                q_deposit = monthly_deposit * 3
                balance += q_deposit
                deposited_this_year += q_deposit
                q_interest = balance * r_quarter
                interest_this_year += q_interest
                if scheme.compounding_frequency == "QUARTERLY":
                    balance += q_interest
                # if QUARTERLY_PAYOUT, balance doesn't accumulate interest (it's paid out)

        elif scheme.compounding_frequency == "MONTHLY_PAYOUT":
            for _ in range(12):
                balance += monthly_deposit
                deposited_this_year += monthly_deposit
                m_interest = balance * r_monthly
                interest_this_year += m_interest
                # Interest is disbursed monthly, not compounded into principal

        elif scheme.compounding_frequency == "SEMI_ANNUAL_PAYOUT":
            r_semi = rate / 2.0
            for _ in range(2):
                semi_deposit = monthly_deposit * 6
                balance += semi_deposit
                deposited_this_year += semi_deposit
                semi_interest = balance * r_semi
                interest_this_year += semi_interest

        elif scheme.compounding_frequency in ("MARKET_NAV", "PENSION_ACCUMULATION"):
            # Market-linked CAGR simulation
            for _ in range(12):
                balance += monthly_deposit
                deposited_this_year += monthly_deposit
            interest_this_year = (opening + (deposited_this_year / 2.0)) * rate
            balance += interest_this_year

        total_deposited += deposited_this_year

        schedule.append({
            "year": year,
            "opening_balance": round(opening, 2),
            "deposited_this_year": round(deposited_this_year, 2),
            "interest_this_year": round(interest_this_year, 2),
            "closing_balance": round(balance, 2)
        })

    total_interest = balance - total_deposited if balance >= total_deposited else 0.0

    # Tax Savings Calculation (Old Tax Regime baseline)
    annual_contribution = (monthly_deposit * 12) + (lump_sum if years == 1 else 0)
    eligible_80c_annual = min(annual_contribution, 150000.0) if "80C" in scheme.tax_section else 0.0
    eligible_80ccd_annual = min(annual_contribution, 50000.0) if "80CCD(1B)" in scheme.tax_section else 0.0

    tax_saved_annual = (eligible_80c_annual + eligible_80ccd_annual) * (tax_bracket_pct / 100.0)
    total_tax_saved = tax_saved_annual * years

    # Net maturity taxability
    taxable_interest = 0.0
    if scheme.tax_treatment == "TAXABLE_INTEREST":
        taxable_interest = total_interest * (tax_bracket_pct / 100.0)

    net_maturity_value = balance - taxable_interest

    return {
        "scheme": scheme.to_dict(),
        "horizon_years": years,
        "monthly_deposit": round(monthly_deposit, 2),
        "lump_sum": round(lump_sum, 2),
        "total_principal_deposited": round(total_deposited, 2),
        "total_interest_earned": round(total_interest, 2),
        "gross_maturity_amount": round(balance, 2),
        "tax_saved_annual": round(tax_saved_annual, 2),
        "total_tax_saved_over_horizon": round(total_tax_saved, 2),
        "taxable_interest_liability": round(taxable_interest, 2),
        "net_proceeds_after_tax": round(net_maturity_value, 2),
        "effective_cagr_pct": scheme.interest_rate_pct,
        "schedule": schedule
    }


def evaluate_profile_fit(profile: dict[str, Any], readiness_status: str = "READY_TO_EXPLORE") -> list[dict[str, Any]]:
    """Evaluates and ranks Indian statutory schemes for an investor profile."""
    horizon_months = profile.get("goal_horizon_months") or 60
    horizon_years = max(1, int(horizon_months // 12))
    surplus = float(profile.get("monthly_surplus") or 30000.0)
    goal_name = (profile.get("goal_name") or "").lower()
    experience = profile.get("investment_experience") or "BEGINNER"

    scored_schemes: list[dict[str, Any]] = []

    for scheme in SCHEMES:
        fit_score = 70  # Baseline
        fit_reasons: list[str] = []
        cautions: list[str] = []

        # 1. Horizon Alignment
        if scheme.id == "ppf":
            if horizon_years >= 7:
                fit_score += 25
                fit_reasons.append("Your horizon matches PPF's 7-year partial withdrawal and 15-year EEE compounding window.")
            else:
                fit_score -= 15
                cautions.append("Your stated goal horizon is shorter than PPF's 15-year tenure.")

        elif scheme.id == "nps_tier1":
            if "retire" in goal_name or horizon_years >= 10:
                fit_score += 30
                fit_reasons.append("Ideal for retirement planning with unique ₹50,000 tax deduction under Section 80CCD(1B).")
            else:
                fit_score += 10
                fit_reasons.append("Strong retirement wealth engine alongside your primary goal.")

        elif scheme.id == "ssy":
            if "child" in goal_name or "daughter" in goal_name or "education" in goal_name:
                fit_score += 35
                fit_reasons.append("Highest sovereign fixed rate (8.20%) with complete EEE tax exemption for a girl child's education.")
            else:
                fit_score -= 10
                cautions.append("Requires having an eligible daughter under age 10.")

        elif scheme.id == "scss":
            # Senior citizen scheme
            fit_score -= 20
            cautions.append("Restricted to individuals aged 60+ (or 55+ with voluntary retirement).")

        elif scheme.id == "nsc":
            if 3 <= horizon_years <= 7:
                fit_score += 20
                fit_reasons.append("5-year tenure perfectly matches your medium-term horizon with 7.70% guaranteed yield.")
            else:
                fit_score += 5

        elif scheme.id == "sgb":
            fit_score += 20
            fit_reasons.append("Fulfills FirstRupee 10% Gold allocation with 2.5% coupon yield and 100% tax-free capital gains at maturity.")

        elif scheme.id == "pomis":
            if "income" in goal_name or "cash" in goal_name:
                fit_score += 20
                fit_reasons.append("Monthly interest disbursement provides predictable cash flow without capital volatility.")

        elif scheme.id == "mssc":
            if horizon_years <= 3:
                fit_score += 15
                fit_reasons.append("High 7.5% quarterly-compounded sovereign rate for a short 2-year horizon (women/girls).")

        # 2. Surplus & Allocation Role
        suggested_monthly = 0.0
        if scheme.id in ("ppf", "nsc", "epf"):
            suggested_monthly = min(surplus * 0.20, 12500.0)  # Fits into 20% fixed income
        elif scheme.id == "nps_tier1":
            suggested_monthly = min(surplus * 0.15, 15000.0)
        elif scheme.id == "sgb":
            suggested_monthly = min(surplus * 0.10, 8000.0)  # Fits into 10% gold

        # Normalize score
        final_score = max(20, min(fit_score, 100))

        scored_schemes.append({
            "scheme": scheme.to_dict(),
            "fit_score": final_score,
            "fit_tier": "HIGH_CONVICTION" if final_score >= 85 else "SUITABLE" if final_score >= 70 else "OPTIONAL",
            "suggested_monthly_inr": round(suggested_monthly, 0),
            "fit_reasons": fit_reasons,
            "cautions": cautions,
            "firstrupee_role": scheme.fiduciary_role
        })

    # Sort descending by fit_score
    scored_schemes.sort(key=lambda x: x["fit_score"], reverse=True)
    return scored_schemes
