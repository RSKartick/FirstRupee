"""Fictional instruments, synthetic price series, synthetic evidence records and the two fictional demonstration investors.

EVERYTHING in this module is synthetic. Instruments are fictional, price paths are generated with fixed seeds, evidence is
labelled SYNTHETIC, source_url is always NULL, and the demo investors are fictional. Nothing here describes a real company,
fund or person, and nothing is live market data.
"""

from __future__ import annotations

import math
from datetime import date
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd

DATASET_LABEL = "FirstRupee synthetic demonstration dataset v2 (fictional instruments, fixed seeds)"
DATASET_AS_OF = date(2026, 6, 30)
SERIES_START = date(2018, 1, 1)

ASSETS: list[dict[str, Any]] = [
    {
        "symbol": "SYN-EQ-MERIDIAN", "name": "Meridian Foods Ltd (fictional)", "asset_type": "EQUITY",
        "description": "A fictional packaged-foods company used to demonstrate equity analysis: growing revenue, improving margins and moderate leverage.",
        "what_it_is": "A single company's share. You own part of one business, so the outcome depends on that company.",
        "how_it_works": "The price reflects expected profits and what investors will pay for them. You buy and sell through an exchange; the price is set by trades.",
        "advantages": ["Direct exposure to one company's growth", "Audited financial statements are published each year", "Large-cap shares are usually easy to sell on trading days"],
        "risks": ["Concentration in one business, management team and balance sheet", "Drawdowns of 20–40% have happened to good businesses", "Accounting and governance risk cannot be diversified away inside one stock"],
        "liquidity": "Exchange traded, T+1 settlement.", "min_horizon_months": 60,
        "fees": "Brokerage, STT, exchange and demat charges on each side. No ongoing expense ratio.", "expense_ratio_pct": None,
        "volatility_class": "HIGH", "seed": 11001, "start_price": 412.0, "annual_drift": 0.12, "annual_vol": 0.26,
        "drawdown": {"start": date(2023, 9, 1), "end": date(2023, 12, 29), "depth": 0.22},
        "evidence": [
            {"key": "MERIDIAN-AR-FY2023", "title": "Meridian Foods — synthetic annual report FY2023", "source_type": "ANNUAL_REPORT", "period": "FY2023", "publication_date": date(2023, 5, 18),
             "summary": "Synthetic record: revenue growth led by staples; margin recovering; borrowing broadly flat.",
             "payload": {"revenueCr": "1580", "ebitdaCr": "216", "patCr": "108", "opmPct": "13.7", "debtEquity": "0.68", "interestCoverage": "4.9", "ocfCr": "142", "peRatio": "31.4"}},
            {"key": "MERIDIAN-AR-FY2024", "title": "Meridian Foods — synthetic annual report FY2024", "source_type": "ANNUAL_REPORT", "period": "FY2024", "publication_date": date(2024, 5, 22),
             "summary": "Synthetic record: revenue up; operating margin up on mix; debt-to-equity slightly lower.",
             "payload": {"revenueCr": "1840", "ebitdaCr": "268", "patCr": "142", "opmPct": "14.6", "debtEquity": "0.62", "interestCoverage": "5.4", "ocfCr": "210", "peRatio": "33.8"}},
            {"key": "MERIDIAN-AR-FY2025", "title": "Meridian Foods — synthetic annual report FY2025", "source_type": "ANNUAL_REPORT", "period": "FY2025", "publication_date": date(2025, 5, 20),
             "summary": "Synthetic record: continued revenue growth; margin expansion; coverage comfortable.",
             "payload": {"revenueCr": "2165", "ebitdaCr": "331", "patCr": "178", "opmPct": "15.3", "debtEquity": "0.58", "interestCoverage": "6.1", "ocfCr": "262", "peRatio": "34.6"}},
            {"key": "MERIDIAN-NOTE-2025", "title": "Meridian Foods — synthetic business note", "source_type": "SYNTHETIC_DOCUMENT", "period": None, "publication_date": date(2025, 11, 8),
             "summary": "Synthetic note: a plant expansion was disclosed, partly funded from internal accruals. Customer concentration is not disclosed.",
             "payload": {}},
        ],
    },
    {
        "symbol": "SYN-EQ-SOLARIS", "name": "Solaris Power Systems Ltd (fictional)", "asset_type": "EQUITY",
        "description": "A fictional electrical-equipment company used to demonstrate the Devil's Advocate: growing revenue, falling margins, rising leverage and weak cash conversion.",
        "what_it_is": "A single company's share in a cyclical, working-capital-heavy industry.",
        "how_it_works": "Same mechanics as any share, but the business consumes cash as it grows, so reported profit and actual cash can diverge.",
        "advantages": ["Revenue growth in a sector with structural demand", "Order book can give multi-year visibility"],
        "risks": ["Margins falling while revenue grows", "Rising debt and thinning interest cover", "Operating cash flow well below reported profit", "Cyclical order inflows can reverse quickly"],
        "liquidity": "Exchange traded, T+1 settlement; wider spreads than large caps in this sample.", "min_horizon_months": 84,
        "fees": "Brokerage, STT, exchange and demat charges on each side.", "expense_ratio_pct": None,
        "volatility_class": "HIGH", "seed": 22002, "start_price": 268.0, "annual_drift": 0.05, "annual_vol": 0.31,
        "drawdown": {"start": date(2024, 4, 1), "end": date(2024, 8, 30), "depth": 0.30},
        "evidence": [
            {"key": "SOLARIS-AR-FY2023", "title": "Solaris Power Systems — synthetic annual report FY2023", "source_type": "ANNUAL_REPORT", "period": "FY2023", "publication_date": date(2023, 6, 2),
             "summary": "Synthetic record: strong revenue growth; margin already slipping; borrowing rising to fund working capital.",
             "payload": {"revenueCr": "940", "ebitdaCr": "121", "patCr": "47", "opmPct": "12.9", "debtEquity": "1.12", "interestCoverage": "2.8", "ocfCr": "18", "peRatio": "42.1"}},
            {"key": "SOLARIS-AR-FY2024", "title": "Solaris Power Systems — synthetic annual report FY2024", "source_type": "ANNUAL_REPORT", "period": "FY2024", "publication_date": date(2024, 6, 10),
             "summary": "Synthetic record: revenue higher; margin lower; coverage thinner; cash conversion weak.",
             "payload": {"revenueCr": "1180", "ebitdaCr": "138", "patCr": "49", "opmPct": "11.7", "debtEquity": "1.34", "interestCoverage": "2.2", "ocfCr": "26", "peRatio": "48.7"}},
            {"key": "SOLARIS-AR-FY2025", "title": "Solaris Power Systems — synthetic annual report FY2025", "source_type": "ANNUAL_REPORT", "period": "FY2025", "publication_date": date(2025, 6, 5),
             "summary": "Synthetic record: revenue growth continues but operating margin falls further; leverage rises; cash flow far below profit.",
             "payload": {"revenueCr": "1462", "ebitdaCr": "156", "patCr": "51", "opmPct": "10.7", "debtEquity": "1.58", "interestCoverage": "1.8", "ocfCr": "34", "peRatio": "52.3"}},
            {"key": "SOLARIS-NOTE-2025", "title": "Solaris Power Systems — synthetic business note", "source_type": "SYNTHETIC_DOCUMENT", "period": None, "publication_date": date(2025, 9, 15),
             "summary": "Synthetic note: order inflows described as lumpy; receivable days elevated in the sample period.",
             "payload": {}},
        ],
    },
    {
        "symbol": "SYN-IDX-BROAD50", "name": "Sample Broad Market Index Fund — Direct (fictional)", "asset_type": "INDEX_FUND",
        "description": "A fictional index mutual fund that replicates a fictional 50-share broad market index, used to demonstrate passive investing.",
        "what_it_is": "A mutual fund that copies an index instead of trying to beat it. You own a slice of the whole index.",
        "how_it_works": "The fund holds the index's companies in the same weights. Your return is the index return minus costs. You buy and sell at the day's NAV.",
        "advantages": ["Instant diversification across many companies", "Low cost because there is no stock-picking decision", "No dependence on one manager's skill"],
        "risks": ["You receive the index return, including full drawdowns", "Tracking difference means returns can differ slightly from the index", "Large index weights concentrate risk in a few companies"],
        "liquidity": "Redeemed at the day's NAV; units usually credited in 2–3 working days.", "min_horizon_months": 60,
        "fees": "Expense ratio only (sample: 0.20% a year). Exit load of 1% if redeemed within 15 days in this sample.", "expense_ratio_pct": "0.20",
        "volatility_class": "HIGH", "seed": 33003, "start_price": 118.0, "annual_drift": 0.11, "annual_vol": 0.17,
        "drawdown": {"start": date(2022, 2, 1), "end": date(2022, 6, 30), "depth": 0.20},
        "evidence": [
            {"key": "BROAD50-FS-FY2024", "title": "Sample Broad Market Index Fund — synthetic factsheet FY2024", "source_type": "FUND_FACTSHEET", "period": "FY2024", "publication_date": date(2024, 7, 12),
             "summary": "Synthetic record: costs and tracking behaviour of the sample index fund.",
             "payload": {"aumCr": "12400", "expenseRatioPct": "0.22", "trackingDifferencePct": "-0.18", "portfolioTurnoverPct": "6", "holdingsCount": "50", "topHoldingWeightPct": "9.4", "maxDrawdownPct": "-22.6"}},
            {"key": "BROAD50-FS-FY2025", "title": "Sample Broad Market Index Fund — synthetic factsheet FY2025", "source_type": "FUND_FACTSHEET", "period": "FY2025", "publication_date": date(2025, 7, 11),
             "summary": "Synthetic record: costs slightly lower; tracking difference small; drawdown recorded in the sample.",
             "payload": {"aumCr": "15200", "expenseRatioPct": "0.20", "trackingDifferencePct": "-0.12", "portfolioTurnoverPct": "5", "holdingsCount": "50", "topHoldingWeightPct": "9.9", "maxDrawdownPct": "-24.8"}},
            {"key": "BROAD50-NOTE-2025", "title": "Sample Broad Market Index Fund — synthetic methodology note", "source_type": "SYNTHETIC_DOCUMENT", "period": None, "publication_date": date(2025, 3, 1),
             "summary": "Synthetic note: the index is market-cap weighted and rebalanced semi-annually.", "payload": {}},
        ],
    },
    {
        "symbol": "SYN-MF-FLEXI", "name": "Sample Flexi-Cap Fund — Direct (fictional)", "asset_type": "MUTUAL_FUND",
        "description": "A fictional actively managed flexi-cap fund used to demonstrate active-management costs, turnover and manager dependence.",
        "what_it_is": "An actively managed mutual fund: a manager chooses companies across market-capitalisation ranges.",
        "how_it_works": "A manager and research team select holdings. You buy units at the daily NAV. Results depend on those decisions and costs are higher than passive funds.",
        "advantages": ["Professional research and portfolio construction", "Flexibility to hold cash or shift exposure", "Diversification across many holdings"],
        "risks": ["Higher expense ratio compounds against you", "Manager and process can change", "No guarantee of beating the index after costs"],
        "liquidity": "Redeemed at the day's NAV; units usually credited in 2–3 working days.", "min_horizon_months": 60,
        "fees": "Expense ratio only (sample: 1.04% a year). Exit load of 1% if redeemed within 365 days in this sample.", "expense_ratio_pct": "1.04",
        "volatility_class": "HIGH", "seed": 44004, "start_price": 46.0, "annual_drift": 0.12, "annual_vol": 0.19,
        "drawdown": None,
        "evidence": [
            {"key": "FLEXI-FS-FY2025", "title": "Sample Flexi-Cap Fund — synthetic factsheet FY2025", "source_type": "FUND_FACTSHEET", "period": "FY2025", "publication_date": date(2025, 7, 14),
             "summary": "Synthetic record: higher cost, meaningful turnover, moderate tracking gap versus the sample index.",
             "payload": {"aumCr": "6100", "expenseRatioPct": "1.04", "trackingDifferencePct": "-1.35", "portfolioTurnoverPct": "62", "holdingsCount": "38", "topHoldingWeightPct": "7.8", "maxDrawdownPct": "-26.2"}},
            {"key": "FLEXI-NOTE-2025", "title": "Sample Flexi-Cap Fund — synthetic manager note", "source_type": "SYNTHETIC_DOCUMENT", "period": None, "publication_date": date(2025, 4, 2),
             "summary": "Synthetic note: the fund's mandate allows cash holdings of up to 20% when the manager is defensive.", "payload": {}},
        ],
    },
    {
        "symbol": "SYN-ETF-LIQUID", "name": "Sample Liquid ETF (fictional)", "asset_type": "ETF",
        "description": "A fictional exchange-traded liquid fund used to demonstrate low-volatility, high-liquidity instruments for money that may be needed soon.",
        "what_it_is": "An exchange-traded fund holding very short-dated money-market instruments, so its value moves very little.",
        "how_it_works": "The fund holds short-dated paper. Units trade on an exchange during market hours, so you can exit intraday.",
        "advantages": ["Very low volatility in the sample history", "Intraday exchange liquidity", "Suitable for money that may be needed soon"],
        "risks": ["Modest returns that can lag inflation", "Not a growth instrument", "Exchange price can differ slightly from underlying value"],
        "liquidity": "Exchange traded during market hours.", "min_horizon_months": 1,
        "fees": "Expense ratio only (sample: 0.16% a year).", "expense_ratio_pct": "0.16",
        "volatility_class": "LOW", "seed": 55005, "start_price": 1000.0, "annual_drift": 0.065, "annual_vol": 0.004,
        "drawdown": None,
        "evidence": [
            {"key": "LIQUID-ETF-FS-FY2025", "title": "Sample Liquid ETF — synthetic factsheet FY2025", "source_type": "FUND_FACTSHEET", "period": "FY2025", "publication_date": date(2025, 7, 10),
             "summary": "Synthetic record: low cost; negligible drawdown; short-dated holdings.",
             "payload": {"aumCr": "18300", "expenseRatioPct": "0.16", "trackingDifferencePct": "-0.05", "holdingsCount": "96", "maxDrawdownPct": "-0.4"}},
        ],
    },
    {
        "symbol": "SYN-FI-GSEC5Y", "name": "Sample 5-Year Government Bond (fictional)", "asset_type": "FIXED_INCOME",
        "description": "A fictional central-government bond used to demonstrate fixed income: a known coupon, price risk if sold early and minimal credit risk.",
        "what_it_is": "A loan to the government that pays a fixed coupon and returns face value at maturity.",
        "how_it_works": "You receive fixed interest on fixed dates. Held to maturity the outcome is known; sold early, the price depends on prevailing yields.",
        "advantages": ["Known coupon and maturity value if held to maturity", "Minimal credit risk for a central-government bond", "Ballast against equity drawdowns"],
        "risks": ["Selling early exposes you to yield-driven price changes", "A fixed coupon loses real value to inflation", "Returns are usually below long-run equity returns"],
        "liquidity": "Tradeable in the secondary market; deepest in the most-traded maturities.", "min_horizon_months": 12,
        "fees": "No expense ratio; brokerage and possibly a bid-ask spread.", "expense_ratio_pct": None,
        "volatility_class": "LOW", "seed": 66006, "start_price": 1000.0, "annual_drift": 0.068, "annual_vol": 0.035,
        "drawdown": None,
        "evidence": [
            {"key": "GSEC5Y-TS-FY2025", "title": "Sample 5-Year Government Bond — synthetic term sheet FY2025", "source_type": "SYNTHETIC_DOCUMENT", "period": "FY2025", "publication_date": date(2025, 4, 8),
             "summary": "Synthetic record: fixed coupon, bullet maturity, price sensitivity to yield changes.",
             "payload": {"couponPct": "6.75", "maturityYears": "5", "yieldToMaturityPct": "6.7", "modifiedDurationYears": "4.2"}},
        ],
    },
    {
        "symbol": "SYN-GOLD", "name": "Gold (synthetic price series)", "asset_type": "GOLD",
        "description": "A synthetic gold price series used to demonstrate a non-income, non-company asset class.",
        "what_it_is": "A physical commodity. Gold produces no profit, dividend or interest; return comes only from price change.",
        "how_it_works": "Price moves with global demand, real interest rates, currency moves and central-bank activity. Exposure is available through ETFs, sovereign bonds or physical gold.",
        "advantages": ["Weak correlation with equities in the sample series", "No issuer default risk", "Can be held in small units through funds"],
        "risks": ["No income: the whole return depends on price", "Long flat periods are possible", "Currency movement can dominate a domestic investor's return"],
        "liquidity": "High for ETFs and bonds; physical gold has making charges and resale friction.", "min_horizon_months": 36,
        "fees": "ETF expense ratio (sample: 0.50% a year), or making charges and GST for physical gold.", "expense_ratio_pct": "0.50",
        "volatility_class": "MODERATE", "seed": 77007, "start_price": 3140.0, "annual_drift": 0.09, "annual_vol": 0.14,
        "drawdown": None,
        "evidence": [
            {"key": "GOLD-NOTE-FY2025", "title": "Gold — synthetic reference note FY2025", "source_type": "SYNTHETIC_DOCUMENT", "period": "FY2025", "publication_date": date(2025, 6, 30),
             "summary": "Synthetic reference note: the price series is generated and has no income component.",
             "payload": {"annualisedVolatilityPct": "14.1", "maxDrawdownPct": "-16.8"}},
        ],
    },
    {
        "symbol": "SYN-ETF-BROAD", "name": "Sample Broad Market ETF (fictional)", "asset_type": "ETF",
        "description": "A fictional exchange-traded fund on the same fictional broad index as the sample index fund, used to compare fund structures.",
        "what_it_is": "An index fund that trades on an exchange like a share instead of at a daily NAV.",
        "how_it_works": "Units are created and redeemed in bulk by institutions, which normally keeps the exchange price close to underlying value.",
        "advantages": ["Index exposure with intraday liquidity", "Low cost (sample: 0.07% a year)", "Transparent holdings"],
        "risks": ["Same market risk as the index, including full drawdowns", "Exchange price can deviate from underlying value in stress", "Needs a demat and trading account"],
        "liquidity": "Exchange traded during market hours; depends on on-screen volume.", "min_horizon_months": 60,
        "fees": "Expense ratio (sample: 0.07% a year) plus brokerage and STT per trade.", "expense_ratio_pct": "0.07",
        "volatility_class": "HIGH", "seed": 88008, "start_price": 96.0, "annual_drift": 0.11, "annual_vol": 0.18,
        "drawdown": {"start": date(2020, 3, 1), "end": date(2020, 5, 29), "depth": 0.25},
        "evidence": [
            {"key": "BROAD-ETF-FS-FY2025", "title": "Sample Broad Market ETF — synthetic factsheet FY2025", "source_type": "FUND_FACTSHEET", "period": "FY2025", "publication_date": date(2025, 7, 9),
             "summary": "Synthetic record: lowest cost in the sample; negligible tracking difference; intraday trading.",
             "payload": {"aumCr": "24800", "expenseRatioPct": "0.07", "trackingDifferencePct": "-0.08", "portfolioTurnoverPct": "4", "holdingsCount": "50", "maxDrawdownPct": "-25.4"}},
            {"key": "BROAD-ETF-NOTE-2025", "title": "Sample Broad Market ETF — synthetic creation note", "source_type": "SYNTHETIC_DOCUMENT", "period": None, "publication_date": date(2025, 2, 10),
             "summary": "Synthetic note: authorised participants create and redeem units in bulk.", "payload": {}},
        ],
    },
]


def generate_observations(defn: dict[str, Any], end: date) -> list[tuple[date, Decimal]]:
    """Seeded geometric random walk on business days, with an optional deterministic drawdown window."""
    days = pd.bdate_range(start=SERIES_START, end=end)
    rng = np.random.default_rng(defn["seed"])
    daily_drift = defn["annual_drift"] / 252.0
    daily_vol = defn["annual_vol"] / math.sqrt(252.0)
    log_returns = daily_drift - 0.5 * daily_vol**2 + daily_vol * rng.standard_normal(len(days))
    dd = defn.get("drawdown")
    if dd:
        mask = np.array([dd["start"] <= d.date() <= dd["end"] for d in days])
        if mask.sum() > 0:
            log_returns[mask] += math.log(1.0 - dd["depth"]) / mask.sum()
    prices = defn["start_price"] * np.exp(np.cumsum(log_returns))
    return [(d.date(), Decimal(f"{float(p):.4f}")) for d, p in zip(days, prices, strict=True)]


DEMO_PROFILES: dict[str, dict[str, Any]] = {
    "rahul": {
        "display_name": "Rahul (fictional demo investor)",
        "age_range": "TWENTY_TO_THIRTY", "employment_status": "SALARIED",
        "monthly_income": "30000.00", "essential_expenses": "20000.00", "nonessential_expenses": "2000.00",
        "monthly_emi": "4000.00", "other_commitments": "0.00",
        "total_savings": "30000.00", "liquid_savings": "25000.00", "emergency_reserves": "20000.00",
        "goal_reserved_amount": "5000.00", "current_investments": "0.00", "existing_liabilities": "60000.00",
        "monthly_investment_designated": "0.00",
        "debts": [{"debt_type": "PERSONAL_LOAN", "outstanding_amount": "60000.00", "interest_rate_pct": "14.00",
                   "emi_amount": "4000.00", "remaining_months": 18, "is_overdue": False}],
        "investment_experience": "BEGINNER",
        "goal_name": "Laptop and relocation fund", "goal_category": "OTHER", "goal_amount": "50000.00",
        "goal_horizon_months": 10, "goal_importance": "HIGH", "goal_liquidity": "HIGH",
        "questionnaire": {"drawdown_reaction": "WAIT", "preferred_horizon": "UNDER_1_YEAR", "gains_reaction": "KEEP_PLAN",
                          "loss_impact_on_expenses": "AFFECTS_ESSENTIALS", "income_stability": "SOMEWHAT_STABLE"},
        "note": "Fictional demonstration. Shows why liquidity, reserves and a 10-month goal come before volatile investing. The ₹30,000 of savings is NOT investable.",
    },
    "priya": {
        "display_name": "Priya (fictional demo investor)",
        "age_range": "TWENTY_TO_THIRTY", "employment_status": "SALARIED",
        "monthly_income": "80000.00", "essential_expenses": "30000.00", "nonessential_expenses": "5000.00",
        "monthly_emi": "5000.00", "other_commitments": "0.00",
        "total_savings": "300000.00", "liquid_savings": "280000.00", "emergency_reserves": "250000.00",
        "goal_reserved_amount": "30000.00", "current_investments": "0.00", "existing_liabilities": "400000.00",
        "monthly_investment_designated": "15000.00",
        "debts": [{"debt_type": "CAR_LOAN", "outstanding_amount": "400000.00", "interest_rate_pct": "9.50",
                   "emi_amount": "5000.00", "remaining_months": 96, "is_overdue": False}],
        "investment_experience": "BEGINNER",
        "goal_name": "Long-term wealth creation (assumed ₹25 lakh target)", "goal_category": "WEALTH_CREATION", "goal_amount": "2500000.00",
        "goal_horizon_months": 120, "goal_importance": "HIGH", "goal_liquidity": "LOW",
        "questionnaire": {"drawdown_reaction": "REASSESS_THESIS", "preferred_horizon": "OVER_SEVEN_YEARS", "gains_reaction": "KEEP_PLAN",
                          "loss_impact_on_expenses": "NO_IMPACT", "income_stability": "VERY_STABLE"},
        "note": "Fictional demonstration. Shows a profile that can explore diversified categories while the risks and missing information are still explained.",
    },
}
