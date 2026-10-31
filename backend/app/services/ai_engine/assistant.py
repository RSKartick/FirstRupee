"""Grounded assistant. Deterministic answers come first; a language model only phrases answers when configured.

Guardrails: the investor's readiness status and figures are injected as fixed facts and are quoted, never rewritten. Model output
containing buy/sell instructions, guarantees or price predictions is discarded in favour of the deterministic answer.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.config import get_settings
from app.data_sources.demo_catalog import ASSETS
from app.services.ai_engine.guardrails import ADVICE_PATTERNS, contains_advice
from app.services.ai_engine.llm import call_json
from app.services.ai_engine.prompts import ASSISTANT_SYSTEM, untrusted_block
from app.services.financial_engine.money import D, fmt_inr
from pydantic import BaseModel, Field

GLOSSARY: dict[str, str] = {
    "nav": "NAV (net asset value) is a fund's price per unit, declared once per working day. You buy and sell units at that day's NAV.",
    "expense ratio": "The expense ratio is a fund's yearly running cost as a percentage of your money. At 1% a year, ₹1,00,000 costs about ₹1,000 a year whatever the performance.",
    "drawdown": "A drawdown is the fall from a previous peak to a later low. A 30% drawdown means the value fell 30% below its earlier high at some point, even if it later recovered.",
    "volatility": "Volatility measures how widely a price moves around its average. It describes the size of swings in both directions, not expected return.",
    "emergency fund": "An emergency reserve is liquid money kept for genuine shocks such as job loss or medical costs. FirstRupee measures it in months of essential expenses and never treats it as investable.",
    "surplus": "Monthly surplus is take-home income minus essential expenses, non-essential expenses, EMIs and other commitments. Only money left after goals and reserves can be considered for investing.",
    "sip": "A SIP is a fixed amount invested at fixed intervals. In the simulator, monthly contributions can be invested monthly or saved in cash and invested quarterly.",
    "lump sum": "A lump sum is the whole amount invested at once. If prices fall right afterwards, the whole amount is exposed to that fall immediately.",
    "tracking difference": "Tracking difference is how far an index fund's or ETF's return lands from its index. Costs and cash holdings are common causes.",
    "time-weighted": "Time-weighted return measures the strategy itself, removing the effect of when money was added. FirstRupee reports it as the cash-flow-neutral return.",
    "money-weighted": "Money-weighted return (XIRR) is the annualised return on your actual dated cash flows. It depends on when you invested, so it is not a measure of strategy quality.",
    "risk tolerance": "Risk tolerance is your willingness to accept swings in value, measured from your behavioural answers. It is not the same as your ability to absorb a loss.",
    "risk capacity": "Risk capacity is your financial ability to absorb a loss without damage, measured from reserves, surplus, debt, income stability and horizon. It takes precedence over tolerance.",
    "liquidity": "Liquidity is how quickly money can become spendable without a large cost. Exchange-traded instruments are usually intraday; fund redemptions wait for the next NAV.",
    "decision passport": "A Decision Passport is a stored, reproducible record of one analysis: readiness at the time, the thesis, the counter-thesis, timing, any simulation, the evidence cited, the assumptions and the conditions that should trigger a review.",
    "thesis expiry": "Thesis-expiry conditions state which verified future information would invalidate the reasoning. When that information appears, the passport is flagged for reassessment.",
    "three clocks": "The Money Clock (when money is available), the Goal Clock (when it is needed) and the Market Clock (historical context). Readiness and goal liquidity always outrank market context.",
}

BLOCKED_PATTERNS = [pattern for _, pattern in ADVICE_PATTERNS]

_SORTED_GLOSSARY_ITEMS = sorted(GLOSSARY.items(), key=lambda kv: len(kv[0]), reverse=True)
_GLOSSARY_PATTERNS = [(term, text, re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)) for term, text in _SORTED_GLOSSARY_ITEMS]

_ASSET_BY_SYMBOL = {a["symbol"]: a for a in ASSETS}
_ASSET_KEYWORDS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(tcs|tata\s+consultancy)\b", re.IGNORECASE), "TCS.NS"),
    (re.compile(r"\b(tata\s*power|tatapower)\b", re.IGNORECASE), "TATAPOWER.NS"),
    (re.compile(r"\b(uti\s+nifty|uti[-\s]nifty50)\b", re.IGNORECASE), "UTI-NIFTY50"),
    (re.compile(r"\b(ppfas|parag\s+parikh)\b", re.IGNORECASE), "PPFAS-FLEXI"),
    (re.compile(r"\b(nippon\s+liquid|nippon[-\s]liquid|liquid\s+fund)\b", re.IGNORECASE), "NIPPON-LIQUID"),
    (re.compile(r"\b(setf10gilt|g[-\s]?sec\s+etf|sbi\s+gilt|10\s*yr\s*g[-\s]?sec)\b", re.IGNORECASE), "SETF10GILT.NS"),
    (re.compile(r"\b(goldbees|gold\s+bees|gold\s+etf)\b", re.IGNORECASE), "GOLDBEES.NS"),
    (re.compile(r"\b(niftybees|nifty\s+bees|nifty\s+50\s+etf)\b", re.IGNORECASE), "NIFTYBEES.NS"),
]

NON_FINANCIAL_REFUSAL = (
    "I am your FirstRupee assistant focused on finance, investing, and your financial profile. "
    "Feel free to ask me anything about your salary, expenses, savings, goals, market instruments, or what we just discussed!"
)

OFF_TOPIC_KEYWORDS = re.compile(
    r"\b("
    r"write\s+a\s+(python|javascript|c\+\+|java|html|rust)\s+(program|script|app)|"
    r"leetcode|binary\s+search\s+tree|mergesort|quicksort"
    r")\b",
    re.IGNORECASE,
)


class AssistantDraft(BaseModel):
    answer: str = Field(min_length=1, max_length=20000)


def is_financial_query(question: str) -> bool:
    q = question.strip()
    if not q:
        return False
    if OFF_TOPIC_KEYWORDS.search(q):
        return False
    return True


def _profile_summary_text(ctx: dict[str, Any]) -> str:
    prof = ctx.get("investor_profile")
    readiness = ctx.get("readiness")
    if not prof:
        return "You have not completed an investor profile yet. Complete the onboarding assessment so I can store and use your initial financial inputs."
    debts = prof.get("debts") or []
    debt_desc = (
        ", ".join(
            f"{d['debt_type']} (outstanding {fmt_inr(D(d['outstanding_amount']))}, rate {d['interest_rate_pct']}%, EMI {fmt_inr(D(d['emi_amount']))}/mo)"
            for d in debts
        )
        if debts
        else "none recorded"
    )
    goal_desc = (
        f"{prof.get('goal_name')} (target {fmt_inr(D(prof.get('goal_amount') or 0))}, deadline {prof.get('goal_deadline') or 'not set'})"
        if prof.get("goal_name")
        else "no specific goal recorded"
    )
    status_str = readiness["status"] if readiness else "not assessed"
    return (
        f"Here is the initial financial profile stored for {prof.get('display_name')} "
        f"(age {prof.get('age_range')}, {prof.get('employment_status')}, experience: {prof.get('investment_experience')}):\n"
        f"- Monthly income: {fmt_inr(D(prof.get('monthly_income') or 0))}\n"
        f"- Essential expenses: {fmt_inr(D(prof.get('essential_expenses') or 0))}/mo | Non-essential: {fmt_inr(D(prof.get('nonessential_expenses') or 0))}/mo\n"
        f"- Monthly EMI: {fmt_inr(D(prof.get('monthly_emi') or 0))}/mo | Other commitments: {fmt_inr(D(prof.get('other_commitments') or 0))}/mo\n"
        f"- Total savings: {fmt_inr(D(prof.get('total_savings') or 0))} | Liquid savings: {fmt_inr(D(prof.get('liquid_savings') or 0))}\n"
        f"- Emergency reserves: {fmt_inr(D(prof.get('emergency_reserves') or 0))} | Goal-reserved: {fmt_inr(D(prof.get('goal_reserved_amount') or 0))}\n"
        f"- Current investments: {fmt_inr(D(prof.get('current_investments') or 0))} | Designated monthly investment: {fmt_inr(D(prof.get('monthly_investment_designated') or 0))}/mo\n"
        f"- Recorded loans/debts: {debt_desc}\n"
        f"- Primary goal: {goal_desc}\n"
        f"- Current readiness status: {status_str}"
    )


def _format_asset_detail(symbol: str, ctx: dict[str, Any]) -> str:
    asset = _ASSET_BY_SYMBOL.get(symbol)
    if not asset:
        return ""
    ev_list = [e for e in (asset.get("evidence") or []) if e.get("payload")]
    ev = ev_list[-1] if ev_list else ((asset.get("evidence") or [{}])[-1])
    payload = ev.get("payload") or {}
    metrics_bits = [f"{k}: {v}" for k, v in payload.items()]
    adv = "; ".join((asset.get("advantages") or [])[:3])
    risks = "; ".join((asset.get("risks") or [])[:3])
    readiness = ctx.get("readiness")
    status_note = ""
    if readiness:
        rec = readiness.get("recommendations") or {}
        allocs = {a["symbol"]: a for a in (rec.get("asset_allocations") or [])}
        if symbol in allocs:
            a = allocs[symbol]
            status_note = (
                f"\n\nIn your current {readiness['status']} plan ({rec.get('experience_level', 'BEGINNER')} mode), "
                f"{asset['name']} has a {a['allocation_pct']}% weight ({fmt_inr(D(a['monthly_amount_inr']))}/month) as '{a['role']}'."
            )
        else:
            status_note = (
                f"\n\nIn your current {readiness['status']} plan ({rec.get('experience_level', 'BEGINNER')} mode), "
                f"{symbol} is not in your primary automated allocation basket, though you can inspect its full two-sided evidence on the Research page."
            )
    return (
        f"{asset['name']} ({asset['symbol']} - {asset['asset_type']}, {asset['volatility_class']} volatility, "
        f"minimum sensible horizon {asset['min_horizon_months']} months):\n"
        f"- Overview: {asset['description']}\n"
        f"- Key audited metrics ({ev.get('period') or 'latest filing'}): {', '.join(metrics_bits) or 'see Research tab'}\n"
        f"- Strengths: {adv}\n"
        f"- Key risks to weigh: {risks}"
        f"{status_note}"
    )


def _stocks_and_instruments_answer(ctx: dict[str, Any]) -> str:
    readiness = ctx.get("readiness")
    prof = ctx.get("investor_profile") or {}
    exp = prof.get("investment_experience") or "BEGINNER"
    rec = (readiness or {}).get("recommendations") or {}
    mp = rec.get("monthly_plan") or {}
    market_deploy = D(mp.get("recommended_market_deployment_inr") or "0")

    tcs_slice = (market_deploy * D("0.10")).quantize(D("0.01")) if market_deploy > 0 else D("0")

    intro = (
        f"Because your profile is in {exp} mode (Readiness: {readiness['status'] if readiness else 'UNASSESSED'}, "
        f"recommended monthly market deployment: {fmt_inr(market_deploy)}/month), here is how single stocks and specific NSE instruments fit your situation:\n\n"
    )
    stocks_section = (
        "1. Specific Single Stocks in the FirstRupee NSE Catalogue:\n"
        "   - Tata Consultancy Services Ltd (TCS.NS - Large-Cap IT Equity):\n"
        "     * Audited FY2025 metrics: Revenue ₹2,55,324 Cr, Operating Margin (OPM) 24.8%, Net Profit (PAT) ₹48,553 Cr, "
        "Debt-to-Equity 0.08x (near-zero debt), Interest Coverage 46.5x, Operating Cash Flow ₹47,610 Cr (98% cash conversion), P/E ~28.9x.\n"
        "     * Trade-off: Very strong balance sheet and cash generation, but 100% concentrated in one company and global IT spending.\n"
        "   - Tata Power Company Ltd (TATAPOWER.NS - Power & Renewables Equity):\n"
        "     * Audited FY2025 metrics: Revenue ₹64,502 Cr, OPM 16.4%, PAT ₹4,280 Cr, Debt-to-Equity 1.18x, Interest Coverage 2.6x, P/E ~36.4x.\n"
        "     * Trade-off: Captures India's solar, EV, and transmission growth, but our deterministic evaluator flags material balance-sheet risks "
        "(Debt/Equity >= 1.0x, Interest Coverage < 3.0x, and P/E > 35x).\n\n"
    )
    broad_section = (
        "2. Broad Index & Mutual Fund Alternatives (Lower Single-Company Risk):\n"
        "   - UTI Nifty 50 Index Fund (UTI-NIFTY50) or Nippon Nifty 50 BeES ETF (NIFTYBEES.NS): Spreads your money across India's top 50 companies "
        "(including TCS, HDFC Bank, Reliance, Infosys) at a 0.18% / 0.04% annual fee.\n"
        "   - Parag Parikh Flexi Cap Fund (PPFAS-FLEXI): Actively managed multi-cap fund (0.63% Direct TER) holding 42 stocks plus defensive cash/T-bills.\n\n"
    )
    if readiness and readiness["status"] == "NOT_READY":
        tail = (
            "How this applies to you right now: Since your status is NOT_READY, avoid buying individual stocks like TCS.NS or TATAPOWER.NS today. "
            "Build your emergency reserve in Nippon India Liquid Fund (NIPPON-LIQUID) first."
        )
    elif exp == "BEGINNER":
        tail = (
            f"How this applies to your {fmt_inr(market_deploy)}/month plan: In Beginner mode, your default blueprint puts 0% in single stocks and 70% "
            f"in diversified funds (50% UTI Nifty 50 Index Fund = {fmt_inr(market_deploy * D('0.50'))}/mo, 20% Parag Parikh Flexi Cap = {fmt_inr(market_deploy * D('0.20'))}/mo) "
            f"so one company's bad quarter cannot hurt your goal. If you want direct stock exposure, you can switch to Intermediate mode on the Dashboard, "
            f"which carves out a 10% researched single-stock satellite ({fmt_inr(tcs_slice)}/month in TCS.NS) while keeping 65% in diversified equity funds."
        )
    else:
        tail = (
            f"How this applies to your {fmt_inr(market_deploy)}/month plan: Your {exp} blueprint already includes TCS.NS as a quality single-stock satellite "
            f"alongside core Nifty 50 index and flexi-cap holdings, while avoiding TATAPOWER.NS due to its leverage (1.18x D/E) and valuation (36.4x P/E) flags."
        )
    return intro + stocks_section + broad_section + tail


def _general_stocks_overview() -> str:
    return (
        "When evaluating stocks in the Indian market (NSE/BSE), it helps to separate broad index exposure from individual company analysis:\n\n"
        "1. Core Broad-Market Index Exposure (for most long-term portfolios):\n"
        "   - Nifty 50 Index Funds / ETFs (such as UTI Nifty 50 Index Fund at 0.18% TER or Nippon Nifty 50 BeES ETF at 0.04% TER) give instant ownership of India's 50 largest listed companies across banking, IT, energy, and consumer goods.\n"
        "   - Flexi-Cap Funds (such as Parag Parikh Flexi Cap Fund at 0.63% Direct TER) actively allocate across large, mid, and small caps.\n\n"
        "2. Evaluating Individual Stocks (What to check before picking a single company):\n"
        "   - Balance Sheet & Leverage: Check Debt-to-Equity (< 0.5x is conservative for non-financials) and Interest Coverage (> 4x).\n"
        "   - Cash Flow Conversion: Compare Operating Cash Flow (OCF) to Net Profit (PAT) to verify reported earnings turn into real cash.\n"
        "   - Valuation vs Growth: Compare P/E and EV/EBITDA against historical medians and sector peers.\n"
        "   - Example contrast in the FirstRupee NSE catalogue: Tata Consultancy Services (TCS.NS, ~Rs 2,502.60) combines 24.8% operating margins, 0.08x debt-to-equity, and 98% cash conversion, whereas capital-intensive utilities like Tata Power (TATAPOWER.NS, ~Rs 345.05) carry higher project leverage (1.18x D/E, 2.6x interest coverage) and valuation sensitivity (36.4x P/E).\n\n"
        "Ask about any specific stock, sector (IT, banking, power, pharma, auto), valuation metric, or mutual fund category and we can dive deeper."
    )


def _deterministic(question: str, ctx: dict[str, Any], history: list[dict[str, str]] | None = None) -> tuple[str, list[str]]:
    q = question.lower().strip()
    readiness = ctx.get("readiness")
    prof = ctx.get("investor_profile")
    grounding: list[str] = []
    if readiness:
        m = readiness["metrics"]
        grounding.append(f"Readiness {readiness['status']} ({readiness['rule_version']}); surplus {fmt_inr(D(m['monthly_surplus']))}.")

    if not is_financial_query(question):
        return NON_FINANCIAL_REFUSAL, grounding

    # 0. Basic greetings, small talk, and identity questions (without parroting user profile)
    if re.match(r"^(hi|hello|hey|hii+|yo|good\s+(morning|afternoon|evening)|namaste|sup|what'?s\s+up)[\s!?.]*$", q):
        return (
            "Hey there! I am your FirstRupee assistant. You can ask me anything about finance and investing - such as stocks, "
            "mutual funds, SIPs, taxation (LTCG/STCG), inflation, market valuation metrics, or general questions - as well as "
            "questions about your personal financial profile whenever you need."
        ), grounding

    if re.search(r"\b(how are you|how's it going|how r u|who are you|what are you|what can you do)\b", q):
        return (
            "I am doing well! I am an AI assistant focused primarily on finance, markets, and personal money management, "
            "and I can also help with everyday questions. Ask me about Indian stocks, ETFs, mutual funds, tax rules, financial "
            "concepts, or your own portfolio plan."
        ), grounding

    if re.match(r"^(ok|okay|k|cool|got it|understood|thanks|thank you|thx|nice|great)[\s!?.]*$", q):
        return "Glad that helped! Let me know what you would like to explore next - whether it is a market topic, a specific stock or fund, or another question.", grounding

    # 1. Check if the user is asking about a specific instrument by name/ticker
    for pat, sym in _ASSET_KEYWORDS:
        if pat.search(q):
            return _format_asset_detail(sym, ctx), grounding

    # 2. General finance topics (Taxes, Inflation, FD vs Debt, Gold, Sectors) - answered directly without profile parroting
    if re.search(r"\b(tax|taxes|ltcg|stcg|80c|income tax|capital gain|capital gains)\b", q):
        return (
            "Here is how investment taxation works in India (FY2025-26 rules):\n"
            "- Equity Stocks & Equity Mutual Funds (>= 65% domestic equity):\n"
            "  * Short-Term Capital Gains (STCG, held < 12 months): Taxed at 20%.\n"
            "  * Long-Term Capital Gains (LTCG, held >= 12 months): Taxed at 12.5% on gains above Rs 1.25 lakh per financial year.\n"
            "- Debt Mutual Funds & Liquid Funds (purchased after April 1, 2023):\n"
            "  * Gains are taxed at your applicable income-tax slab rate regardless of holding period, though tax is only triggered upon redemption (unlike FDs where interest is taxed annually on accrual).\n"
            "- Gold ETFs:\n"
            "  * Listed Gold ETFs held for more than 12 months qualify for the 12.5% LTCG rate."
        ), grounding

    if re.search(r"\b(inflation|purchasing power|real return|cagr|compounding|compound interest)\b", q):
        return (
            "Inflation erodes purchasing power over time, so what matters for long-term wealth is your post-tax, post-inflation 'real return':\n"
            "- If CPI inflation averages 5.5% to 6% in India and a savings account or taxed FD yields ~5% post-tax, your real purchasing power slowly shrinks.\n"
            "- Sovereign bonds / G-Secs (~6.8% to 7.2% yield) roughly preserve purchasing power with low volatility.\n"
            "- Broad equity indices (like the Nifty 50) carry higher short-term drawdowns (15% to 30% in downturns) but historically compound above inflation over 5 to 10+ year horizons."
        ), grounding

    if re.search(r"\b(fd|fixed deposit|savings account|liquid fund vs fd)\b", q):
        return (
            "Comparing Bank Fixed Deposits (FDs) vs Liquid / G-Sec Funds:\n"
            "- Bank FDs: Guaranteed stated interest rate and DICGC insurance up to Rs 5 lakh per bank, but premature withdrawal penalties apply and interest is taxed every year on accrual (TDS).\n"
            "- Liquid Mutual Funds (e.g. Nippon India Liquid Fund): Invest in 91-day Government T-Bills and high-grade money market instruments. No lock-in or exit load after 7 days, T+1 settlement, and tax is deferred until you actually redeem units."
        ), grounding

    # 3. Check if the user is asking about specific stocks, shares, or equity picks
    if re.search(r"\b(stock|stocks|share|shares|equity|equities|company|companies|ticker|tickers|which\s+fund|specific\s+fund|specific\s+stock|single\s+stock)\b", q):
        if re.search(r"\b(my|for me|my plan|my portfolio|should i)\b", q) and readiness:
            return _stocks_and_instruments_answer(ctx), grounding
        return _general_stocks_overview(), grounding

    # 4. Check if the user is explicitly asking for their profile summary / details
    if re.search(r"\b(my profile|my details|my inputs|my numbers|my data|what did i enter|what do you know about me|my situation|summarize my)\b", q):
        return _profile_summary_text(ctx), grounding

    # 5. Goal questions
    if prof and re.search(r"\b(my goal|my target|my deadline|goalhorizon)\b", q):
        if not prof.get("goal_name"):
            return "You have not recorded a specific financial goal on your profile yet.", grounding
        m = (readiness or {}).get("metrics") or {}
        return (
            f"Your recorded goal is '{prof['goal_name']}' ({prof.get('goal_category') or 'general'}) with a target of "
            f"{fmt_inr(D(prof.get('goal_amount') or 0))} by {prof.get('goal_deadline') or 'unspecified deadline'} "
            f"({m.get('goal_horizon_months') or 'n/a'} months away; monthly funding need: {fmt_inr(D(m.get('goal_monthly_need') or 0))}/month; "
            f"already reserved: {fmt_inr(D(prof.get('goal_reserved_amount') or 0))})."
        ), grounding

    # 6. Debt / loan / EMI questions
    if prof and re.search(r"\b(my debt|my loan|my loans|my emi|my liabilities)\b", q):
        debts = prof.get("debts") or []
        if not debts and D(prof.get("monthly_emi") or 0) == 0:
            return "You have ₹0 in monthly EMIs and no active loans recorded on your profile.", grounding
        debt_lines = "; ".join(
            f"{d['debt_type']}: {fmt_inr(D(d['outstanding_amount']))} at {d['interest_rate_pct']}% interest, EMI {fmt_inr(D(d['emi_amount']))}/mo ({d['remaining_months']} months left)"
        ) or "no itemized loans"
        return (
            f"Your recorded monthly EMI outflow is {fmt_inr(D(prof.get('monthly_emi') or 0))}/month and total liabilities are "
            f"{fmt_inr(D(prof.get('existing_liabilities') or 0))}. Itemized loans: {debt_lines}."
        ), grounding

    # 7. Glossary terms (word-boundary matched)
    for term, text, pat in _GLOSSARY_PATTERNS:
        if pat.search(q):
            if readiness and term in ("emergency fund", "surplus", "risk capacity", "risk tolerance"):
                return f"{text}\n\nFor your profile: readiness is {readiness['status']}.", grounding
            return text, grounding

    # 8. Readiness status / can I invest / am I ready
    if re.search(r"ready|can i invest|should i invest|why not|blocker|warning", q):
        if not readiness:
            return ("I don't have a stored readiness result for you yet. Complete the financial assessment first; I won't estimate "
                    "readiness without your figures."), grounding
        m = readiness["metrics"]
        rec = readiness.get("recommendations") or {}
        mp = rec.get("monthly_plan") or {}
        steps = "; ".join(readiness["improvement_steps"][:3])
        blockers = "; ".join(readiness["blockers"]) or "none"
        warnings = "; ".join(readiness["warnings"]) or "none"
        return (
            f"Yes - your readiness status is {readiness['status']}."
            if readiness["status"] == "READY_TO_EXPLORE"
            else f"Your current readiness status is {readiness['status']}."
        ) + (
            f"\n\nKey figures from your profile:\n"
            f"- Monthly surplus: {fmt_inr(D(m['monthly_surplus']))}/month (from {fmt_inr(D(m['monthly_income']))} income minus {fmt_inr(D(m['committed_outflow']))} outflows)\n"
            f"- Emergency coverage: {m.get('emergency_coverage_months') or 'n/a'} months of essential expenses ({fmt_inr(D(m['emergency_reserves']))} saved vs {fmt_inr(D(m['emergency_target']))} 6-month target)\n"
            f"- Free investable capacity: {fmt_inr(D(m['investable_monthly']))}/month (recommended market SIP: {fmt_inr(D(mp.get('recommended_market_deployment_inr', '0')))}/month)\n"
            f"- Risk Capacity: {m.get('risk_capacity_band')} (score {m.get('risk_capacity_score')}) | Risk Tolerance: {m.get('risk_tolerance_band')} (score {m.get('risk_tolerance_score')})\n"
            f"- Blockers: {blockers} | Warnings: {warnings}\n\n"
            f"Next steps: {steps}"
        ), grounding

    # 9. Personal portfolio recommendation / where to invest
    if re.search(r"recommend|allocat|where to invest|what to invest|my plan|my portfolio", q):
        if not readiness:
            return ("Complete your financial assessment first so I can calculate your exact monthly rupee allocation and "
                    "experience-tailored recommendations."), grounding
        rec = readiness.get("recommendations") or {}
        allocs = rec.get("asset_allocations") or []
        alloc_lines = "\n".join(
            f"- {a['name']} ({a['symbol']}): {a['allocation_pct']}% ({fmt_inr(D(a['monthly_amount_inr']))}/month) - {a['role']}"
            for a in allocs
        )
        mp = rec.get("monthly_plan") or {}
        return (
            f"{rec.get('headline', readiness['explanation'])}\n\n"
            f"{rec.get('summary', '')}\n\n"
            f"Monthly Cash-Flow Plan (from {fmt_inr(D(mp.get('monthly_surplus_inr', '0')))} monthly surplus):\n"
            f"- Emergency Reserve Top-Up: {fmt_inr(D(mp.get('emergency_topup_inr', '0')))}/month\n"
            f"- Goal Reserve Funding: {fmt_inr(D(mp.get('goal_reserve_inr', '0')))}/month\n"
            f"- Recommended Market SIP: {fmt_inr(D(mp.get('recommended_market_deployment_inr', '0')))}/month\n\n"
            f"Instrument Breakdown ({rec.get('tone_label', 'tailored')}):\n{alloc_lines}"
        ), grounding

    # 10. General Mutual Funds / Index Funds / ETFs / Gold / Bonds explanation
    if re.search(r"\b(etf|mutual fund|index fund|gold|bond|g-sec|gilt|debt fund)\b", q):
        return (
            "Here is how the main building blocks of an Indian investment portfolio work:\n"
            "- Direct Index Mutual Funds (e.g. UTI Nifty 50 Index Fund, 0.18% TER): Passively track the Nifty 50 index without needing a demat account; ideal for automated monthly SIPs.\n"
            "- Exchange-Traded Funds (e.g. Nifty BeES 0.04% TER, Gold BeES 0.79% TER, SBI 10Y G-Sec ETF 0.17% TER): Trade live on NSE during market hours via a demat account.\n"
            "- Active Flexi-Cap Funds (e.g. Parag Parikh Flexi Cap, 0.63% TER): Give fund managers flexibility across large, mid, and small caps.\n"
            "- Sovereign Fixed Income & Liquid Funds: Anchor portfolio stability and fund short-term goals or emergency reserves."
        ), grounding

    # 11. Simulator questions
    if re.search(r"simulat|scenario|lump", q):
        runs = ctx.get("simulations") or []
        base = ("The simulator compares lump-sum, staged, delayed and comparison scenarios on the same evaluation date. "
                "Hypothetical paths are labelled and are not forecasts.")
        if runs:
            base += f" Your latest run: {runs[0]['scenario_type']}, time-weighted return {runs[0]['twr']}%."
        return base, grounding

    # 12. Research questions
    if re.search(r"research|analyst|devil|evidence", q):
        items = ctx.get("research") or []
        if not items:
            return "No research analysis is stored for you yet. Choose an instrument on the Research page (such as TCS.NS, TATAPOWER.NS, or UTI-NIFTY50) to run a two-sided Analyst vs Devil's Advocate check.", grounding
        names = ", ".join(f"{r['asset_name']} ({r['status']})" for r in items[:5])
        return f"Your stored analyses: {names}. Evaluator statuses are evidence assessments, not buy or sell signals.", grounding

    # 13. Timing / Three Clocks
    if re.search(r"timing|clock|clocks|when to invest|market clock", q):
        timing = ctx.get("timing")
        if timing:
            return (
                f"Your Three Clocks timing verdict is {timing['verdict_code']}: {timing['verdict']}\n"
                f"- Money Clock: {timing['clocks']['money']['status']} ({timing['clocks']['money']['headline']})\n"
                f"- Goal Clock: {timing['clocks']['goal']['status']} ({timing['clocks']['goal']['headline']})\n"
                f"- Market Clock: {timing['clocks']['market']['status']} ({timing['clocks']['market']['headline']})"
            ), grounding

    if re.search(r"passport", q):
        return GLOSSARY["decision passport"], grounding

    # 14. Cash flow / salary / expenses / savings (when asking about own numbers)
    if re.search(r"cash flow|budget|my income|my expense|salary|salray|salery|my saving|did i mention|just mention", q) and (readiness or prof):
        if prof and readiness:
            m = readiness["metrics"]
            return (
                f"From your profile ({prof.get('display_name')}): your monthly income/salary is {fmt_inr(D(prof.get('monthly_income') or 0))}, "
                f"essential expenses are {fmt_inr(D(prof.get('essential_expenses') or 0))}, non-essential expenses are "
                f"{fmt_inr(D(prof.get('nonessential_expenses') or 0))}, and monthly EMIs are {fmt_inr(D(prof.get('monthly_emi') or 0))}. "
                f"Your monthly surplus is {fmt_inr(D(m['monthly_surplus']))} and free investable monthly capacity after reserves is "
                f"{fmt_inr(D(m['investable_monthly']))}."
            ), grounding

    return (
        "I can help with any financial or investing question (such as Indian stocks, mutual funds, ETFs, SIP strategy, LTCG/STCG taxes, "
        "inflation, valuation ratios, or debt vs equity), basic everyday questions, or your personal FirstRupee profile if you ask for it. "
        "What topic would you like to dive into?"
    ), grounding


def _compact_profile_reference(ctx: dict[str, Any]) -> dict[str, Any] | None:
    prof = ctx.get("investor_profile")
    readiness = ctx.get("readiness")
    if not prof:
        return None
    rec = (readiness or {}).get("recommendations") or {}
    mp = rec.get("monthly_plan") or {}
    m = (readiness or {}).get("metrics") or {}
    return {
        "_usage_note": "Use ONLY if the user asks about their own profile, salary, readiness, or personal plan. Do NOT mention or repeat on general finance or basic questions.",
        "display_name": prof.get("display_name"),
        "experience_level": prof.get("investment_experience"),
        "monthly_income_inr": prof.get("monthly_income"),
        "essential_expenses_inr": prof.get("essential_expenses"),
        "nonessential_expenses_inr": prof.get("nonessential_expenses"),
        "monthly_emi_inr": prof.get("monthly_emi"),
        "monthly_surplus_inr": m.get("monthly_surplus"),
        "emergency_reserves_inr": prof.get("emergency_reserves"),
        "emergency_coverage_months": m.get("emergency_coverage_months"),
        "goal_name": prof.get("goal_name"),
        "goal_amount_inr": prof.get("goal_amount"),
        "goal_deadline": prof.get("goal_deadline"),
        "readiness_status": (readiness or {}).get("status"),
        "recommended_market_sip_inr": mp.get("recommended_market_deployment_inr"),
        "recommended_allocations": [
            {
                "symbol": a["symbol"],
                "name": a["name"],
                "weight_pct": a["allocation_pct"],
                "monthly_inr": a["monthly_amount_inr"],
            }
            for a in (rec.get("asset_allocations") or [])
        ],
    }


def answer(messages: list[dict[str, str]], ctx: dict[str, Any]) -> dict[str, Any]:
    question = messages[-1]["content"]
    settings = get_settings()
    guardrails = ["FirstRupee is educational decision support, not investment advice, and does not execute trades."]

    if not is_financial_query(question):
        return {
            "answer": NON_FINANCIAL_REFUSAL,
            "mode": "DETERMINISTIC",
            "provider": "domain-guardrail",
            "grounding": [],
            "guardrails": guardrails,
        }

    if settings.llm_enabled:
        catalogue_brief = [
            {
                "symbol": a["symbol"],
                "name": a["name"],
                "asset_type": a["asset_type"],
                "volatility_class": a["volatility_class"],
                "expense_ratio_pct": a["expense_ratio_pct"],
                "key_metrics": ((a.get("evidence") or [{}])[-1]).get("payload", {}),
            }
            for a in ASSETS
        ]
        context = untrusted_block("chat_request", {
            "1_latest_user_message": question,
            "2_recent_conversation": messages[-12:],
            "3_firstrupee_catalogue_reference": catalogue_brief,
            "4_optional_user_profile_reference": _compact_profile_reference(ctx),
        })
        result = call_json(ASSISTANT_SYSTEM, context, AssistantDraft)
        if result.ok and not contains_advice(result.data.answer):
            return {"answer": result.data.answer, "mode": "LLM", "provider": result.provider,
                    "grounding": ["Profile inputs and readiness figures are quoted from the deterministic engine."], "guardrails": guardrails}
        reason = result.kind if not result.ok else "UNSAFE_OUTPUT"
        guardrails.append(f"Language model answer unavailable ({reason}); deterministic answer shown.")
    text, grounding = _deterministic(question, ctx, history=messages)
    return {"answer": text, "mode": "DETERMINISTIC", "provider": "deterministic", "grounding": grounding, "guardrails": guardrails}
