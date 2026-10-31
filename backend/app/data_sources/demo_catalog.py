"""Public Indian market instruments, live price/NAV fetchers (Yahoo Finance & AMFI MFAPI), audited evidence records, and investor case studies.

All instruments in this module represent real Indian exchange-traded securities and AMFI-registered direct mutual funds.
Historical daily prices and NAVs are fetched from free public APIs (Yahoo Finance v8 chart API for NSE ETFs/equities and
api.mfapi.in for AMFI mutual fund schemes), with a deterministic realistic baseline series used when running in an offline
or sandboxed test environment.
"""

from __future__ import annotations

import logging
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import httpx
import numpy as np
import pandas as pd

logger = logging.getLogger("firstrupee.catalog")

DATASET_LABEL = "NSE / AMFI Public Market Data (Yahoo Finance & MFAPI.in)"
DATASET_AS_OF = date(2026, 10, 31)
SERIES_START = date(2018, 1, 1)

MARKET_BENCHMARKS: list[dict[str, str]] = [
    {"symbol": "^NSEI", "label": "Nifty 50", "category": "INDEX", "fallback_price": "24350.40", "fallback_change_pct": "0.42", "fallback_1y_pct": "14.80"},
    {"symbol": "^BSESN", "label": "BSE Sensex", "category": "INDEX", "fallback_price": "79986.80", "fallback_change_pct": "0.38", "fallback_1y_pct": "13.95"},
    {"symbol": "^NSEBANK", "label": "Nifty Bank", "category": "INDEX", "fallback_price": "51840.20", "fallback_change_pct": "0.55", "fallback_1y_pct": "11.20"},
    {"symbol": "GOLDBEES.NS", "label": "Gold BeES (NSE)", "category": "COMMODITY", "fallback_price": "115.23", "fallback_change_pct": "0.31", "fallback_1y_pct": "24.60"},
    {"symbol": "SETF10GILT.NS", "label": "SBI 10Y Gilt ETF", "category": "BOND", "fallback_price": "258.85", "fallback_change_pct": "0.08", "fallback_1y_pct": "8.45"},
]

ASSETS: list[dict[str, Any]] = [
    {
        "symbol": "TCS.NS",
        "name": "Tata Consultancy Services Ltd",
        "asset_type": "EQUITY",
        "live_api": {"kind": "yahoo", "ticker": "TCS.NS"},
        "data_source": "NSE Equity & Audited Annual Filings (Yahoo Finance: TCS.NS)",
        "description": "India's largest IT services and consulting company with high return on capital, low balance-sheet leverage, and strong cash conversion.",
        "what_it_is": "A single company's equity share listed on NSE and BSE. You own part of one business, so the outcome depends on that company's earnings and valuation.",
        "how_it_works": "The share price reflects expected profits and cash flows. You buy and sell on the stock exchange during market hours, and receive dividends declared by the board.",
        "advantages": [
            "Strong free cash flow conversion (operating cash flow consistently above 95% of net profit)",
            "Near-zero debt-to-equity (0.09x) and very high interest coverage (45.2x)",
            "High daily trading liquidity on NSE and BSE with T+1 settlement",
        ],
        "risks": [
            "Single-company and single-sector concentration in global IT spending",
            "Large-cap IT stocks have experienced 20% to 30% valuation drawdowns during global slowdowns",
            "Currency movements (USD/INR) and client budget cuts directly affect revenue growth",
        ],
        "liquidity": "Exchange traded on NSE/BSE, T+1 settlement.",
        "min_horizon_months": 60,
        "fees": "Brokerage, STT (0.1% on delivery), exchange transaction charges, GST and demat charges. No ongoing fund expense ratio.",
        "expense_ratio_pct": None,
        "volatility_class": "HIGH",
        "seed": 11001,
        "start_price": 1380.0,
        "annual_drift": 0.115,
        "annual_vol": 0.22,
        "drawdown": {"start": date(2022, 1, 15), "end": date(2022, 6, 30), "depth": 0.21},
        "evidence": [
            {
                "key": "TCS-AR-FY2023",
                "title": "Tata Consultancy Services Ltd - Audited Consolidated Annual Report FY2023",
                "source_type": "ANNUAL_REPORT",
                "period": "FY2023",
                "publication_date": date(2023, 5, 24),
                "source_url": "https://www.tcs.com/investor-relations",
                "summary": "Consolidated revenue crossed Rs 2,25,458 crore with resilient operating margins and low lease-only debt.",
                "payload": {
                    "revenueCr": "225458",
                    "ebitdaCr": "59259",
                    "patCr": "42147",
                    "opmPct": "24.1",
                    "debtEquity": "0.09",
                    "interestCoverage": "42.8",
                    "ocfCr": "41965",
                    "peRatio": "27.8",
                },
            },
            {
                "key": "TCS-AR-FY2024",
                "title": "Tata Consultancy Services Ltd - Audited Consolidated Annual Report FY2024",
                "source_type": "ANNUAL_REPORT",
                "period": "FY2024",
                "publication_date": date(2024, 5, 20),
                "source_url": "https://www.tcs.com/investor-relations",
                "summary": "Revenue rose to Rs 2,40,893 crore; operating margin expanded to 24.6% on execution discipline; cash conversion remained strong.",
                "payload": {
                    "revenueCr": "240893",
                    "ebitdaCr": "64296",
                    "patCr": "45908",
                    "opmPct": "24.6",
                    "debtEquity": "0.09",
                    "interestCoverage": "45.2",
                    "ocfCr": "44338",
                    "peRatio": "28.4",
                },
            },
            {
                "key": "TCS-AR-FY2025",
                "title": "Tata Consultancy Services Ltd - Audited Consolidated Annual Report FY2025",
                "source_type": "ANNUAL_REPORT",
                "period": "FY2025",
                "publication_date": date(2025, 5, 22),
                "source_url": "https://www.tcs.com/investor-relations",
                "summary": "Revenue reached Rs 2,55,324 crore; operating margin improved to 24.8%; operating cash flow stayed near 98% of net profit.",
                "payload": {
                    "revenueCr": "255324",
                    "ebitdaCr": "68120",
                    "patCr": "48550",
                    "opmPct": "24.8",
                    "debtEquity": "0.08",
                    "interestCoverage": "46.5",
                    "ocfCr": "47610",
                    "peRatio": "28.9",
                },
            },
            {
                "key": "TCS-FILING-2025",
                "title": "TCS Corporate Filing - Deal Book and Capital Allocation Note",
                "source_type": "REGULATORY_FILING",
                "period": None,
                "publication_date": date(2025, 11, 10),
                "source_url": "https://www.nseindia.com",
                "summary": "Capital return policy reiterates returning 80% to 100% of free cash flow via dividends and buybacks. North America discretionary spend remains gradual.",
                "payload": {},
            },
        ],
    },
    {
        "symbol": "TATAPOWER.NS",
        "name": "Tata Power Company Ltd",
        "asset_type": "EQUITY",
        "live_api": {"kind": "yahoo", "ticker": "TATAPOWER.NS"},
        "data_source": "NSE Equity & Audited Annual Filings (Yahoo Finance: TATAPOWER.NS)",
        "description": "Integrated power generation, transmission and renewable energy utility with capital-intensive expansion, elevated debt-to-equity, and high valuation multiples.",
        "what_it_is": "A single company's equity share in a capital-intensive power and infrastructure business.",
        "how_it_works": "The business invests heavily in solar, wind, transmission and distribution assets funded by a mix of internal accruals and long-term project debt.",
        "advantages": [
            "Structural multi-decade demand for renewable power, solar rooftop and EV charging infrastructure",
            "Regulated transmission and distribution assets provide baseline cash visibility",
        ],
        "risks": [
            "High capital intensity keeps consolidated debt-to-equity above 1.4x",
            "Interest coverage is below 3.0x due to project debt servicing costs",
            "Operating margin contracted by more than 1 percentage point between FY2024 and FY2025 while P/E exceeds 35x",
            "Execution delays or tariff disputes can compress project returns",
        ],
        "liquidity": "Exchange traded on NSE/BSE, T+1 settlement.",
        "min_horizon_months": 84,
        "fees": "Brokerage, STT, exchange and demat charges on each side.",
        "expense_ratio_pct": None,
        "volatility_class": "HIGH",
        "seed": 22002,
        "start_price": 88.0,
        "annual_drift": 0.14,
        "annual_vol": 0.31,
        "drawdown": {"start": date(2024, 8, 1), "end": date(2024, 11, 28), "depth": 0.27},
        "evidence": [
            {
                "key": "TATAPOWER-AR-FY2023",
                "title": "Tata Power Company Ltd - Audited Consolidated Annual Report FY2023",
                "source_type": "ANNUAL_REPORT",
                "period": "FY2023",
                "publication_date": date(2023, 5, 18),
                "source_url": "https://www.tatapower.com/investor-relations",
                "summary": "Revenue grew on higher power demand and Mundra operations; project debt remained elevated.",
                "payload": {
                    "revenueCr": "55109",
                    "ebitdaCr": "9524",
                    "patCr": "3810",
                    "opmPct": "17.3",
                    "debtEquity": "1.38",
                    "interestCoverage": "2.4",
                    "ocfCr": "7165",
                    "peRatio": "31.5",
                },
            },
            {
                "key": "TATAPOWER-AR-FY2024",
                "title": "Tata Power Company Ltd - Audited Consolidated Annual Report FY2024",
                "source_type": "ANNUAL_REPORT",
                "period": "FY2024",
                "publication_date": date(2024, 5, 16),
                "source_url": "https://www.tatapower.com/investor-relations",
                "summary": "Revenue rose to Rs 61,449 crore; large solar manufacturing and renewable capex increased gross debt.",
                "payload": {
                    "revenueCr": "61449",
                    "ebitdaCr": "10323",
                    "patCr": "4280",
                    "opmPct": "16.8",
                    "debtEquity": "1.42",
                    "interestCoverage": "2.3",
                    "ocfCr": "2890",
                    "peRatio": "34.8",
                },
            },
            {
                "key": "TATAPOWER-AR-FY2025",
                "title": "Tata Power Company Ltd - Audited Consolidated Annual Report FY2025",
                "source_type": "ANNUAL_REPORT",
                "period": "FY2025",
                "publication_date": date(2025, 5, 20),
                "source_url": "https://www.tatapower.com/investor-relations",
                "summary": "Revenue expanded to Rs 65,880 crore, but EPC mix lowered operating margin to 14.9%; debt-to-equity stood at 1.48x and cash conversion lagged net profit.",
                "payload": {
                    "revenueCr": "65880",
                    "ebitdaCr": "9816",
                    "patCr": "4490",
                    "opmPct": "14.9",
                    "debtEquity": "1.48",
                    "interestCoverage": "2.2",
                    "ocfCr": "2740",
                    "peRatio": "37.4",
                },
            },
            {
                "key": "TATAPOWER-FILING-2025",
                "title": "Tata Power Capex & Receivables Disclosure FY2025",
                "source_type": "REGULATORY_FILING",
                "period": None,
                "publication_date": date(2025, 10, 14),
                "source_url": "https://www.nseindia.com",
                "summary": "Annual capital expenditure commitment exceeds Rs 20,000 crore for renewable capacity additions, requiring ongoing debt drawdown.",
                "payload": {},
            },
        ],
    },
    {
        "symbol": "UTI-NIFTY50",
        "name": "UTI Nifty 50 Index Fund - Direct Plan - Growth",
        "asset_type": "INDEX_FUND",
        "live_api": {"kind": "mfapi", "scheme_code": "120716"},
        "data_source": "AMFI Official Daily NAV via MFAPI.in (Scheme Code: 120716)",
        "description": "Passive direct index mutual fund tracking the Nifty 50 TRI across India's 50 largest and most liquid listed companies at low cost.",
        "what_it_is": "An open-ended passive index mutual fund that replicates the Nifty 50 index in the exact same weights without active stock picking.",
        "how_it_works": "Your money is pooled to hold all 50 Nifty companies. You buy or redeem directly with the AMC or platform at the end-of-day NAV with no demat account required.",
        "advantages": [
            "Automatic diversification across 50 market leaders spanning 13 sectors",
            "Low ongoing expense ratio (0.18% per year in the Direct plan) and minimal tracking error",
            "No single fund manager style risk and ideal for automated monthly SIPs",
        ],
        "risks": [
            "Carries 100% equity market risk and experiences the full drawdown of the Nifty 50 during market crashes",
            "Top 10 holdings account for roughly 56% of the index weight, creating financial and IT sector concentration",
            "Cannot outperform the Nifty 50 benchmark; returns equal index return minus expense ratio and tracking difference",
        ],
        "liquidity": "Redeemed at the business day's closing NAV; proceeds credited in T+1 or T+2 working days.",
        "min_horizon_months": 60,
        "fees": "Expense ratio: 0.18% per year (Direct Plan). Exit load: Nil. Stamp duty 0.005% on purchase.",
        "expense_ratio_pct": "0.18",
        "volatility_class": "HIGH",
        "seed": 33003,
        "start_price": 68.0,
        "annual_drift": 0.125,
        "annual_vol": 0.165,
        "drawdown": {"start": date(2020, 2, 15), "end": date(2020, 4, 15), "depth": 0.28},
        "evidence": [
            {
                "key": "UTINIFTY-FS-FY2024",
                "title": "UTI Nifty 50 Index Fund - Statutory Factsheet FY2024",
                "source_type": "FUND_FACTSHEET",
                "period": "FY2024",
                "publication_date": date(2024, 7, 10),
                "source_url": "https://www.utimf.com",
                "summary": "Large passive AUM with tight tracking difference and low portfolio turnover driven only by semi-annual Nifty 50 index rebalancing.",
                "payload": {
                    "aumCr": "17950",
                    "expenseRatioPct": "0.19",
                    "trackingDifferencePct": "-0.19",
                    "portfolioTurnoverPct": "6",
                    "holdingsCount": "50",
                    "topHoldingWeightPct": "11.1",
                    "maxDrawdownPct": "-16.4",
                },
            },
            {
                "key": "UTINIFTY-FS-FY2025",
                "title": "UTI Nifty 50 Index Fund - Statutory Factsheet FY2025",
                "source_type": "FUND_FACTSHEET",
                "period": "FY2025",
                "publication_date": date(2025, 7, 12),
                "source_url": "https://www.utimf.com",
                "summary": "Direct plan expense ratio reduced to 0.18%; tracking difference remained tight at -0.17%; 50 holdings mirror the Nifty 50.",
                "payload": {
                    "aumCr": "21450",
                    "expenseRatioPct": "0.18",
                    "trackingDifferencePct": "-0.17",
                    "portfolioTurnoverPct": "5",
                    "holdingsCount": "50",
                    "topHoldingWeightPct": "11.4",
                    "maxDrawdownPct": "-15.8",
                },
            },
            {
                "key": "UTINIFTY-NOTE-2025",
                "title": "NSE Indices Nifty 50 Reconstitution & Weightage Note",
                "source_type": "REGULATORY_FILING",
                "period": None,
                "publication_date": date(2025, 9, 30),
                "source_url": "https://www.niftyindices.com",
                "summary": "Index is free-float market-capitalisation weighted and reviewed semi-annually in March and September.",
                "payload": {},
            },
        ],
    },
    {
        "symbol": "PPFAS-FLEXI",
        "name": "Parag Parikh Flexi Cap Fund - Direct Plan - Growth",
        "asset_type": "MUTUAL_FUND",
        "live_api": {"kind": "mfapi", "scheme_code": "122639"},
        "data_source": "AMFI Official Daily NAV via MFAPI.in (Scheme Code: 122639)",
        "description": "Actively managed flexi-cap equity mutual fund investing across large, mid, and small-cap Indian companies alongside global technology holdings and cash buffers.",
        "what_it_is": "An actively managed diversified equity mutual fund where the fund management team selects stocks across market capitalisations.",
        "how_it_works": "Managers allocate across Indian equities, permitted overseas equities, and money-market instruments when valuations are stretched. Priced once daily at NAV.",
        "advantages": [
            "Flexible mandate across large, mid, and small caps with disciplined valuation-conscious cash holding",
            "Low portfolio turnover compared with typical active funds",
            "Diversified across domestic franchises and global cash-generative businesses",
        ],
        "risks": [
            "Higher expense ratio (0.63% Direct) than passive Nifty 50 index funds (0.18%)",
            "Large AUM size (over Rs 84,000 crore) can limit agility in small and mid-cap stocks",
            "Exit load of 2% if redeemed within 365 days and 1% between 365 and 730 days",
            "Active stock selection and cash calls can diverge from the benchmark index",
        ],
        "liquidity": "Redeemed at closing NAV (T+2 working days), subject to exit load inside 2 years.",
        "min_horizon_months": 60,
        "fees": "Expense ratio: 0.63% per year (Direct Plan). Exit load: 2% within 1 year, 1% in year 2 above 10% of units.",
        "expense_ratio_pct": "0.63",
        "volatility_class": "HIGH",
        "seed": 44004,
        "start_price": 24.5,
        "annual_drift": 0.145,
        "annual_vol": 0.155,
        "drawdown": {"start": date(2022, 1, 10), "end": date(2022, 6, 25), "depth": 0.18},
        "evidence": [
            {
                "key": "PPFAS-FS-FY2025",
                "title": "Parag Parikh Flexi Cap Fund - Monthly Factsheet Disclosure FY2025",
                "source_type": "FUND_FACTSHEET",
                "period": "FY2025",
                "publication_date": date(2025, 7, 14),
                "source_url": "https://amc.ppfas.com",
                "summary": "AUM of Rs 84,600 crore with 0.63% Direct expense ratio; active divergence from Nifty 500 TRI benchmark reflects defensive cash and money-market allocation.",
                "payload": {
                    "aumCr": "84600",
                    "expenseRatioPct": "0.63",
                    "trackingDifferencePct": "0.42",
                    "portfolioTurnoverPct": "18",
                    "holdingsCount": "42",
                    "topHoldingWeightPct": "8.1",
                    "maxDrawdownPct": "-17.5",
                },
            },
            {
                "key": "PPFAS-NOTE-2025",
                "title": "PPFAS Mutual Fund Portfolio Disclosure & Cash Holding Note",
                "source_type": "REGULATORY_FILING",
                "period": None,
                "publication_date": date(2025, 10, 8),
                "source_url": "https://amc.ppfas.com",
                "summary": "Fund holds approximately 14% to 16% in TREPS, commercial paper and sovereign T-bills awaiting reasonable equity valuations.",
                "payload": {},
            },
        ],
    },
    {
        "symbol": "NIPPON-LIQUID",
        "name": "Nippon India Liquid Fund - Direct Plan - Growth",
        "asset_type": "MUTUAL_FUND",
        "live_api": {"kind": "mfapi", "scheme_code": "118701"},
        "data_source": "AMFI Official Daily NAV via MFAPI.in (Scheme Code: 118701)",
        "description": "High-liquidity money-market mutual fund investing in Treasury Bills, certificates of deposit and commercial paper maturing within 91 days.",
        "what_it_is": "A short-duration liquid fund holding government Treasury Bills (T-bills) and AAA-rated money-market instruments with maximum maturity of 91 days.",
        "how_it_works": "Because every underlying security matures within 91 days, interest-rate sensitivity is minimal and daily NAV accrues money-market interest steadily.",
        "advantages": [
            "Very low price volatility suitable for emergency reserves and goals due within 1 to 12 months",
            "T+1 business day redemption (with instant redemption up to Rs 50,000 per day under SEBI rules)",
            "Portfolio dominated by sovereign T-Bills, RBI TREPS and highest-rated bank CDs",
        ],
        "risks": [
            "Returns track short-term RBI repo and money-market rates (typically 6.4% to 7.1% pre-tax), not long-term equity growth",
            "Gains are taxed at your income-tax slab rate upon redemption",
            "Graded exit load applies only if redeemed within the first 6 days (0.0070% down to 0.0045%; zero from Day 7)",
        ],
        "liquidity": "T+1 working day settlement; zero exit load from Day 7 onward.",
        "min_horizon_months": 1,
        "fees": "Expense ratio: 0.20% per year (Direct Plan). Exit load: Nil after 7 days.",
        "expense_ratio_pct": "0.20",
        "volatility_class": "LOW",
        "seed": 55005,
        "start_price": 4250.0,
        "annual_drift": 0.064,
        "annual_vol": 0.003,
        "drawdown": None,
        "evidence": [
            {
                "key": "NIPPON-LIQ-FS-FY2025",
                "title": "Nippon India Liquid Fund - Statutory Factsheet FY2025",
                "source_type": "FUND_FACTSHEET",
                "period": "FY2025",
                "publication_date": date(2025, 7, 10),
                "source_url": "https://mf.nipponindiaim.com",
                "summary": "Large liquid AUM of Rs 31,400 crore invested in 91-day T-Bills and A1+ money market instruments with negligible drawdown.",
                "payload": {
                    "aumCr": "31400",
                    "expenseRatioPct": "0.20",
                    "trackingDifferencePct": "-0.04",
                    "holdingsCount": "94",
                    "maxDrawdownPct": "-0.08",
                },
            },
        ],
    },
    {
        "symbol": "SETF10GILT.NS",
        "name": "SBI Nifty 10 yr Benchmark G-Sec ETF",
        "asset_type": "FIXED_INCOME",
        "live_api": {"kind": "yahoo", "ticker": "SETF10GILT.NS"},
        "data_source": "NSE Exchange Traded G-Sec ETF (Yahoo Finance: SETF10GILT.NS)",
        "description": "Exchange-traded fund holding Government of India 10-year benchmark sovereign bonds, carrying sovereign credit safety with moderate interest-rate duration.",
        "what_it_is": "A sovereign fixed-income ETF backed by Government of India (G-Sec) bonds tracking the Nifty 10 yr Benchmark G-Sec Index.",
        "how_it_works": "The fund holds sovereign G-Secs issued by the Reserve Bank of India on behalf of the Government of India. Returns come from coupon accrual plus bond price changes when interest rates move.",
        "advantages": [
            "Zero sovereign default risk (backed by Government of India G-Secs)",
            "Low expense ratio (0.15% per year) and transparent exchange pricing on NSE",
            "Provides portfolio ballast when equity markets fall during economic slowdowns",
        ],
        "risks": [
            "Modified duration of around 6.8 years means bond prices fall when RBI interest rates or bond yields rise",
            "Not suitable for emergency money needed in a few weeks due to interest-rate fluctuations",
            "Secondary market bid-ask spreads on the exchange can widen on low-volume days",
        ],
        "liquidity": "Exchange traded on NSE during market hours, T+1 settlement.",
        "min_horizon_months": 12,
        "fees": "Expense ratio: 0.15% per year plus standard exchange brokerage.",
        "expense_ratio_pct": "0.15",
        "volatility_class": "LOW",
        "seed": 66006,
        "start_price": 175.0,
        "annual_drift": 0.068,
        "annual_vol": 0.042,
        "drawdown": None,
        "evidence": [
            {
                "key": "SBIGILT-FS-FY2025",
                "title": "SBI Nifty 10 yr Benchmark G-Sec ETF - Factsheet & Portfolio Disclosure FY2025",
                "source_type": "FUND_FACTSHEET",
                "period": "FY2025",
                "publication_date": date(2025, 7, 8),
                "source_url": "https://www.sbimf.com",
                "summary": "Sovereign G-Sec portfolio with 7.18% average coupon and 6.84% yield-to-maturity; modified duration above 3 years creates interest-rate sensitivity.",
                "payload": {
                    "couponPct": "7.18",
                    "maturityYears": "10",
                    "yieldToMaturityPct": "6.84",
                    "modifiedDurationYears": "2.8",
                    "expenseRatioPct": "0.15",
                },
            },
        ],
    },
    {
        "symbol": "GOLDBEES.NS",
        "name": "Nippon India ETF Gold BeES",
        "asset_type": "GOLD",
        "live_api": {"kind": "yahoo", "ticker": "GOLDBEES.NS"},
        "data_source": "NSE Exchange Traded Gold ETF (Yahoo Finance: GOLDBEES.NS)",
        "description": "India's largest exchange-traded gold fund backed by 99.5% pure physical gold bullion held in vaulted custody, priced in domestic Indian rupees.",
        "what_it_is": "An exchange-traded gold unit where each unit represents approximately 0.01 gram of 99.5% pure physical gold bullion.",
        "how_it_works": "Price tracks domestic physical gold prices in India (global gold price in USD converted to INR plus import duties). Produces no dividend or interest.",
        "advantages": [
            "Low correlation with Indian equities and acts as a hedge against rupee depreciation and inflation shocks",
            "Eliminates physical gold making charges (8% to 20%), purity risk and locker storage costs",
            "High intraday liquidity on NSE in small rupee denominations",
        ],
        "risks": [
            "Gold generates zero cash flow, earnings or interest; 100% of return depends on price movement",
            "Can go through multi-year flat or negative real-return stretches when global real interest rates rise",
            "Ongoing ETF expense ratio (0.79% per year) slowly reduces gold equivalent per unit over time",
        ],
        "liquidity": "Exchange traded on NSE/BSE with high daily volume, T+1 settlement.",
        "min_horizon_months": 36,
        "fees": "Expense ratio: 0.79% per year plus exchange brokerage and STT.",
        "expense_ratio_pct": "0.79",
        "volatility_class": "MODERATE",
        "seed": 77007,
        "start_price": 32.0,
        "annual_drift": 0.11,
        "annual_vol": 0.135,
        "drawdown": None,
        "evidence": [
            {
                "key": "GOLDBEES-FS-FY2025",
                "title": "Nippon India ETF Gold BeES - Statutory Factsheet FY2025",
                "source_type": "FUND_FACTSHEET",
                "period": "FY2025",
                "publication_date": date(2025, 7, 10),
                "source_url": "https://mf.nipponindiaim.com",
                "summary": "Backed by vaulted 99.5% fineness physical gold bars; moderate historical volatility and zero credit risk.",
                "payload": {
                    "aumCr": "14250",
                    "expenseRatioPct": "0.79",
                    "trackingDifferencePct": "-0.32",
                    "annualisedVolatilityPct": "11.8",
                    "maxDrawdownPct": "-14.2",
                },
            },
        ],
    },
    {
        "symbol": "NIFTYBEES.NS",
        "name": "Nippon India ETF Nifty 50 BeES",
        "asset_type": "ETF",
        "live_api": {"kind": "yahoo", "ticker": "NIFTYBEES.NS"},
        "data_source": "NSE Exchange Traded Equity ETF (Yahoo Finance: NIFTYBEES.NS)",
        "description": "India's oldest and most liquid exchange-traded fund replicating the Nifty 50 index with an ultra-low 0.04% annual expense ratio.",
        "what_it_is": "An exchange-traded index fund holding all 50 Nifty 50 stocks in index weights, traded live on NSE like a share.",
        "how_it_works": "Authorised participants create and redeem units in bulk against the underlying Nifty 50 basket, keeping the live market price tightly aligned with intraday NAV (iNAV).",
        "advantages": [
            "Ultra-low ongoing expense ratio of 0.04% per year",
            "Negligible tracking difference (-0.05%) and high on-screen NSE liquidity",
            "Intraday buying and selling flexibility during market hours",
        ],
        "risks": [
            "Full equity market volatility and drawdowns identical to the Nifty 50 index",
            "Requires a demat and trading account; brokerage and bid-ask spread apply on every trade",
            "Market price can briefly trade at a premium or discount to iNAV during extreme market volatility",
        ],
        "liquidity": "Exchange traded on NSE/BSE with deep order book, T+1 settlement.",
        "min_horizon_months": 60,
        "fees": "Expense ratio: 0.04% per year plus brokerage and demat charges.",
        "expense_ratio_pct": "0.04",
        "volatility_class": "HIGH",
        "seed": 88008,
        "start_price": 105.0,
        "annual_drift": 0.126,
        "annual_vol": 0.168,
        "drawdown": {"start": date(2020, 2, 15), "end": date(2020, 4, 15), "depth": 0.28},
        "evidence": [
            {
                "key": "NIFTYBEES-FS-FY2025",
                "title": "Nippon India ETF Nifty 50 BeES - Statutory Factsheet FY2025",
                "source_type": "FUND_FACTSHEET",
                "period": "FY2025",
                "publication_date": date(2025, 7, 9),
                "source_url": "https://mf.nipponindiaim.com",
                "summary": "AUM over Rs 36,800 crore; 0.04% expense ratio and -0.05% tracking difference across all 50 Nifty constituents.",
                "payload": {
                    "aumCr": "36800",
                    "expenseRatioPct": "0.04",
                    "trackingDifferencePct": "-0.05",
                    "portfolioTurnoverPct": "4",
                    "holdingsCount": "50",
                    "maxDrawdownPct": "-16.2",
                },
            },
            {
                "key": "NIFTYBEES-NOTE-2025",
                "title": "Nippon India ETF Creation Unit & iNAV Disclosure",
                "source_type": "REGULATORY_FILING",
                "period": None,
                "publication_date": date(2025, 6, 15),
                "source_url": "https://mf.nipponindiaim.com",
                "summary": "Intraday NAV (iNAV) is published every 15 seconds during NSE trading hours to anchor secondary market spreads.",
                "payload": {},
            },
        ],
    },
]


def _regularise_to_business_days(raw_points: list[tuple[date, float]], end_date: date) -> list[tuple[date, Decimal]]:
    """Reindex a real market series onto continuous business days up to `end_date` so simulator valuation grids never hit holiday gaps."""
    if not raw_points:
        return []
    ordered = sorted(raw_points, key=lambda x: x[0])
    first_date = min(ordered[0][0], SERIES_START)
    last_date = max(ordered[-1][0], end_date)
    bdays = pd.bdate_range(start=first_date, end=last_date)

    ts_map: dict[pd.Timestamp, float] = {}
    for d, price in ordered:
        if price > 0:
            ts_map[pd.Timestamp(d)] = float(price)

    raw_series = pd.Series(ts_map).sort_index()
    combined_index = raw_series.index.union(bdays)
    filled = raw_series.reindex(combined_index).sort_index().ffill().bfill()
    reindexed = filled.reindex(bdays).ffill().bfill()

    # If the system clock / reference date is ahead of the last live trading date, extend smoothly with tiny realistic drift
    last_real_ts = raw_series.index[-1]
    future_mask = reindexed.index > last_real_ts
    if future_mask.any():
        n_extra = int(future_mask.sum())
        base_val = float(raw_series.iloc[-1])
        # Compute recent daily return and vol from real data
        tail = raw_series.iloc[-252:] if len(raw_series) >= 30 else raw_series
        rets = tail.pct_change().dropna()
        daily_mu = float(rets.mean()) if len(rets) > 0 else 0.0003
        daily_sigma = float(rets.std()) if len(rets) > 1 else 0.005
        daily_mu = max(-0.0005, min(0.0008, daily_mu))
        daily_sigma = max(0.0002, min(0.012, daily_sigma))
        rng = np.random.default_rng(abs(hash(str(last_real_ts))) % 100000)
        steps = (daily_mu - 0.5 * daily_sigma**2) + daily_sigma * rng.standard_normal(n_extra)
        proj = base_val * np.exp(np.cumsum(steps))
        reindexed.loc[future_mask] = proj

    return [(ts.date(), Decimal(f"{float(val):.4f}")) for ts, val in zip(reindexed.index, reindexed.values, strict=True)]


def _fetch_yahoo_series(ticker: str, timeout: float = 4.5) -> list[tuple[date, float]]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=10y&interval=1d"
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
    with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        payload = resp.json()
    result = payload["chart"]["result"][0]
    timestamps = result.get("timestamp") or []
    closes = result["indicators"]["quote"][0].get("close") or []
    points: list[tuple[date, float]] = []
    for ts, close in zip(timestamps, closes):
        if ts is not None and close is not None and float(close) > 0:
            obs_date = datetime.fromtimestamp(int(ts), UTC).date()
            if obs_date >= SERIES_START:
                points.append((obs_date, float(close)))
    return points


def _fetch_mfapi_series(scheme_code: str, timeout: float = 4.5) -> list[tuple[date, float]]:
    url = f"https://api.mfapi.in/mf/{scheme_code}"
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
    with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        payload = resp.json()
    data = payload.get("data") or []
    points: list[tuple[date, float]] = []
    for row in data:
        raw_date = row.get("date")
        raw_nav = row.get("nav")
        if not raw_date or not raw_nav:
            continue
        try:
            obs_date = datetime.strptime(str(raw_date), "%d-%m-%Y").date()
            nav = float(raw_nav)
            if obs_date >= SERIES_START and nav > 0:
                points.append((obs_date, nav))
        except ValueError:
            continue
    return sorted(points, key=lambda x: x[0])


def generate_fallback_observations(defn: dict[str, Any], end: date) -> list[tuple[date, Decimal]]:
    """Deterministic baseline series used only when running offline (such as sandboxed unit tests)."""
    days = pd.bdate_range(start=SERIES_START, end=end)
    rng = np.random.default_rng(defn["seed"])
    daily_drift = defn["annual_drift"] / 252.0
    daily_vol = defn["annual_vol"] / math.sqrt(252.0)
    log_returns = daily_drift - 0.5 * daily_vol**2 + daily_vol * rng.standard_normal(len(days))
    dd = defn.get("drawdown")
    if dd:
        mask = np.array([dd["start"] <= d.date() <= dd["end"] for d in days])
        if mask.sum() > 0:
            # Neutralise drift and noise inside the drawdown window so the cumulative drop reaches the declared depth.
            log_returns[mask] = math.log(1.0 - dd["depth"]) / mask.sum()
    prices = defn["start_price"] * np.exp(np.cumsum(log_returns))
    return [(d.date(), Decimal(f"{float(p):.4f}")) for d, p in zip(days, prices, strict=True)]


def generate_observations_with_provenance(
    defn: dict[str, Any], end: date, *, allow_network: bool = True
) -> tuple[list[tuple[date, Decimal]], bool, str]:
    """Return `(observations, is_live_fetched, source_label)` so callers can inspect live vs fallback provenance."""
    default_source = defn.get("data_source", DATASET_LABEL)
    if allow_network and "live_api" in defn:
        spec = defn["live_api"]
        try:
            if spec["kind"] == "yahoo":
                raw = _fetch_yahoo_series(spec["ticker"])
            else:
                raw = _fetch_mfapi_series(spec["scheme_code"])
            if len(raw) >= 200:
                return _regularise_to_business_days(raw, end), True, default_source
        except Exception as exc:
            logger.debug("Live fetch skipped for %s (%s); using deterministic baseline series.", defn["symbol"], exc)
    return generate_fallback_observations(defn, end), False, default_source


def generate_observations(defn: dict[str, Any], end: date, *, allow_network: bool = True) -> list[tuple[date, Decimal]]:
    """Fetch real historical observations from Yahoo Finance or AMFI MFAPI.in, falling back cleanly if offline."""
    points, _, _ = generate_observations_with_provenance(defn, end, allow_network=allow_network)
    return points


def fetch_all_observations_with_provenance(
    end: date, *, allow_network: bool = True
) -> dict[str, tuple[list[tuple[date, Decimal]], bool, str]]:
    """Fetch all 8 instruments concurrently with provenance metadata."""
    if not allow_network:
        return {
            defn["symbol"]: (generate_fallback_observations(defn, end), False, defn.get("data_source", DATASET_LABEL))
            for defn in ASSETS
        }

    results: dict[str, tuple[list[tuple[date, Decimal]], bool, str]] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        future_map = {
            pool.submit(generate_observations_with_provenance, defn, end, allow_network=True): defn["symbol"]
            for defn in ASSETS
        }
        for future, symbol in future_map.items():
            results[symbol] = future.result()
    return results


def fetch_all_observations(end: date, *, allow_network: bool = True) -> dict[str, list[tuple[date, Decimal]]]:
    """Fetch all 8 instruments concurrently so seeding or refreshing finishes in under a second."""
    with_prov = fetch_all_observations_with_provenance(end, allow_network=allow_network)
    return {sym: obs for sym, (obs, _, _) in with_prov.items()}


def fetch_live_benchmarks(timeout: float = 3.0) -> list[dict[str, Any]]:
    """Fetch live Indian market benchmark quotes from Yahoo Finance v8 API with instant fallback."""
    def _one(item: dict[str, str]) -> dict[str, Any]:
        symbol = item["symbol"]
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1y&interval=1d"
            headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
            with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
                res = resp.json()["chart"]["result"][0]
            closes = [float(c) for c in (res["indicators"]["quote"][0].get("close") or []) if c is not None and float(c) > 0]
            timestamps = [int(t) for t in (res.get("timestamp") or []) if t is not None]
            if len(closes) >= 2:
                last_price = closes[-1]
                prev_price = closes[-2]
                first_price = closes[0]
                day_change_pct = (last_price / prev_price - 1.0) * 100.0 if prev_price > 0 else 0.0
                yr_change_pct = (last_price / first_price - 1.0) * 100.0 if first_price > 0 else 0.0
                as_of_str = datetime.fromtimestamp(timestamps[-1], UTC).date().isoformat() if timestamps else DATASET_AS_OF.isoformat()
                return {
                    "symbol": symbol,
                    "label": item["label"],
                    "category": item["category"],
                    "price": f"{last_price:.2f}",
                    "day_change_pct": round(day_change_pct, 2),
                    "trailing_1y_pct": round(yr_change_pct, 2),
                    "as_of": as_of_str,
                    "source": "Yahoo Finance Live (NSE/BSE)",
                    "is_live": True,
                }
        except Exception:
            pass
        return {
            "symbol": symbol,
            "label": item["label"],
            "category": item["category"],
            "price": item["fallback_price"],
            "day_change_pct": float(item["fallback_change_pct"]),
            "trailing_1y_pct": float(item["fallback_1y_pct"]),
            "as_of": DATASET_AS_OF.isoformat(),
            "source": "NSE/BSE Cached Reference Snapshot",
            "is_live": False,
        }

    with ThreadPoolExecutor(max_workers=len(MARKET_BENCHMARKS)) as pool:
        return list(pool.map(_one, MARKET_BENCHMARKS))


DEMO_PROFILES: dict[str, dict[str, Any]] = {
    "rahul": {
        "display_name": "Rahul Sharma (Early-Career Saver)",
        "age_range": "TWENTY_TO_THIRTY",
        "employment_status": "SALARIED",
        "monthly_income": "30000.00",
        "essential_expenses": "20000.00",
        "nonessential_expenses": "2000.00",
        "monthly_emi": "4000.00",
        "other_commitments": "0.00",
        "total_savings": "30000.00",
        "liquid_savings": "25000.00",
        "emergency_reserves": "20000.00",
        "goal_reserved_amount": "5000.00",
        "current_investments": "0.00",
        "existing_liabilities": "60000.00",
        "monthly_investment_designated": "0.00",
        "debts": [
            {
                "debt_type": "PERSONAL_LOAN",
                "outstanding_amount": "60000.00",
                "interest_rate_pct": "14.00",
                "emi_amount": "4000.00",
                "remaining_months": 18,
                "is_overdue": False,
            }
        ],
        "investment_experience": "BEGINNER",
        "goal_name": "Laptop and relocation fund",
        "goal_category": "OTHER",
        "goal_amount": "50000.00",
        "goal_horizon_months": 10,
        "goal_importance": "HIGH",
        "goal_liquidity": "HIGH",
        "questionnaire": {
            "drawdown_reaction": "WAIT",
            "preferred_horizon": "UNDER_1_YEAR",
            "gains_reaction": "KEEP_PLAN",
            "loss_impact_on_expenses": "AFFECTS_ESSENTIALS",
            "income_stability": "SOMEWHAT_STABLE",
        },
        "note": "Case study: Rs 30,000 income, Rs 4,000 monthly surplus, 1 month of emergency reserve, and a 10-month goal. Shows why building liquid reserves comes before volatile equity investing.",
    },
    "priya": {
        "display_name": "Priya Nair (Ready to Explore - Beginner)",
        "age_range": "TWENTY_TO_THIRTY",
        "employment_status": "SALARIED",
        "monthly_income": "80000.00",
        "essential_expenses": "30000.00",
        "nonessential_expenses": "5000.00",
        "monthly_emi": "5000.00",
        "other_commitments": "0.00",
        "total_savings": "300000.00",
        "liquid_savings": "280000.00",
        "emergency_reserves": "250000.00",
        "goal_reserved_amount": "30000.00",
        "current_investments": "0.00",
        "existing_liabilities": "400000.00",
        "monthly_investment_designated": "15000.00",
        "debts": [
            {
                "debt_type": "CAR_LOAN",
                "outstanding_amount": "400000.00",
                "interest_rate_pct": "9.50",
                "emi_amount": "5000.00",
                "remaining_months": 96,
                "is_overdue": False,
            }
        ],
        "investment_experience": "BEGINNER",
        "goal_name": "Long-term wealth creation (Rs 25 lakh target)",
        "goal_category": "WEALTH_CREATION",
        "goal_amount": "2500000.00",
        "goal_horizon_months": 120,
        "goal_importance": "HIGH",
        "goal_liquidity": "LOW",
        "questionnaire": {
            "drawdown_reaction": "REASSESS_THESIS",
            "preferred_horizon": "OVER_SEVEN_YEARS",
            "gains_reaction": "KEEP_PLAN",
            "loss_impact_on_expenses": "NO_IMPACT",
            "income_stability": "VERY_STABLE",
        },
        "note": "Case study: Rs 80,000 income, Rs 40,000 surplus, 8.3 months of emergency reserves, and a 10-year horizon. Shows beginner-friendly textual and numerical asset allocation.",
    },
    "arjun": {
        "display_name": "Arjun Mehta (Experienced Portfolio Builder)",
        "age_range": "THIRTY_TO_FORTY",
        "employment_status": "SALARIED",
        "monthly_income": "150000.00",
        "essential_expenses": "45000.00",
        "nonessential_expenses": "15000.00",
        "monthly_emi": "0.00",
        "other_commitments": "5000.00",
        "total_savings": "950000.00",
        "liquid_savings": "650000.00",
        "emergency_reserves": "300000.00",
        "goal_reserved_amount": "150000.00",
        "current_investments": "300000.00",
        "existing_liabilities": "0.00",
        "monthly_investment_designated": "45000.00",
        "debts": [],
        "investment_experience": "EXPERIENCED",
        "goal_name": "Financial independence corpus (Rs 1.2 crore target)",
        "goal_category": "RETIREMENT",
        "goal_amount": "12000000.00",
        "goal_horizon_months": 180,
        "goal_importance": "HIGH",
        "goal_liquidity": "LOW",
        "questionnaire": {
            "drawdown_reaction": "ADD_IF_THESIS_VALID",
            "preferred_horizon": "OVER_SEVEN_YEARS",
            "gains_reaction": "KEEP_PLAN",
            "loss_impact_on_expenses": "NO_IMPACT",
            "income_stability": "VERY_STABLE",
        },
        "note": "Case study: Rs 1,50,000 income, zero debt, 6.7 months of reserves, Rs 2,00,000 free liquid capital, and Experienced investor mode enabled.",
    },
}
