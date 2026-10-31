"""Grounded assistant. Deterministic answers come first; a language model only phrases answers when configured.

Guardrails: the investor's readiness status and figures are injected as fixed facts and are quoted, never rewritten. Model output
containing buy/sell instructions, guarantees or price predictions is discarded in favour of the deterministic answer.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.config import get_settings
from app.services.ai_engine.llm import call_json
from app.services.ai_engine.prompts import ASSISTANT_SYSTEM, untrusted_block
from app.services.financial_engine.money import fmt_inr, D
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

BLOCKED_PATTERNS = [
    re.compile(r"\bguarantee[ds]?\b", re.IGNORECASE),
    re.compile(r"\b(buy|sell) (it |this |them )?now\b", re.IGNORECASE),
    re.compile(r"\byou should (buy|sell|invest in)\b", re.IGNORECASE),
    re.compile(r"\bwill (double|triple|rise|fall|crash)\b", re.IGNORECASE),
    re.compile(r"\bcertain (return|profit)s?\b", re.IGNORECASE),
]


class AssistantDraft(BaseModel):
    answer: str = Field(min_length=3, max_length=3000)


def _deterministic(question: str, ctx: dict[str, Any]) -> tuple[str, list[str]]:
    q = question.lower()
    readiness = ctx.get("readiness")
    grounding: list[str] = []
    if readiness:
        m = readiness["metrics"]
        grounding.append(f"Readiness {readiness['status']} ({readiness['rule_version']}); surplus {fmt_inr(D(m['monthly_surplus']))}.")

    for term, text in GLOSSARY.items():
        if term in q:
            if readiness and term in ("emergency fund", "surplus", "risk capacity", "risk tolerance"):
                return f"{text}\n\nFor your profile: readiness is {readiness['status']}.", grounding
            return text, grounding

    if re.search(r"recommend|allocat|where to invest|what to invest|how much|plan|portfolio|beginner|intermediate|experienced", q):
        if not readiness:
            return ("Complete your financial assessment first so I can calculate your exact monthly rupee allocation and "
                    "experience-tailored recommendations."), grounding
        rec = readiness.get("recommendations") or {}
        allocs = rec.get("asset_allocations") or []
        alloc_lines = ", ".join(
            f"{a['name']} ({a['allocation_pct']}%: {fmt_inr(D(a['monthly_amount_inr']))}/month)"
            for a in allocs
        )
        mp = rec.get("monthly_plan") or {}
        return (
            f"{rec.get('headline', readiness['explanation'])}\n\n"
            f"{rec.get('summary', '')}\n\n"
            f"Numerical monthly breakdown (from {fmt_inr(D(mp.get('monthly_surplus_inr', '0')))} surplus): "
            f"Emergency top-up {fmt_inr(D(mp.get('emergency_topup_inr', '0')))}/month, "
            f"Goal reserve {fmt_inr(D(mp.get('goal_reserve_inr', '0')))}/month, "
            f"Market deployment {fmt_inr(D(mp.get('recommended_market_deployment_inr', '0')))}/month. "
            f"Instrument split ({rec.get('tone_label', 'tailored')}): {alloc_lines}."
        ), grounding

    if re.search(r"ready|can i invest|should i invest", q):
        if not readiness:
            return ("I don't have a stored readiness result for you yet. Complete the financial assessment first; I won't estimate "
                    "readiness without your figures."), grounding
        steps = "; ".join(readiness["improvement_steps"][:3])
        blockers = "; ".join(readiness["blockers"]) or "none recorded"
        return (
            f"Your readiness is {readiness['status']}. {readiness['explanation']} Blockers: {blockers}. "
            f"Next steps: {steps}. This classification comes from the deterministic engine and cannot be changed by a request."
        ), grounding
    if re.search(r"simulat|scenario|sip|lump", q):
        runs = ctx.get("simulations") or []
        base = ("The simulator compares lump-sum, staged, delayed and comparison scenarios on the same evaluation date. "
                "Hypothetical paths are labelled and are not forecasts.")
        if runs:
            base += f" Your latest run: {runs[0]['scenario_type']}, time-weighted return {runs[0]['twr']}%."
        return base, grounding
    if re.search(r"research|analyst|devil|evidence", q):
        items = ctx.get("research") or []
        if not items:
            return "No research analysis is stored for you yet. Choose an instrument on the Research page to run one.", grounding
        names = ", ".join(f"{r['asset_name']} ({r['status']})" for r in items[:5])
        return f"Your stored analyses: {names}. Evaluator statuses are evidence assessments, not buy or sell signals.", grounding
    if re.search(r"passport", q):
        return GLOSSARY["decision passport"], grounding
    if re.search(r"cash flow|surplus|budget|income|expense", q) and readiness:
        m = readiness["metrics"]
        return (f"Your monthly surplus is {fmt_inr(D(m['monthly_surplus']))} after recorded commitments. Investable money after goal and "
                f"reserve needs is {fmt_inr(D(m['investable_monthly']))} per month."), grounding
    return ("I can explain investment terms and your own stored results: readiness, research, simulations and passports. "
            "I cannot recommend a specific investment, predict markets or change your readiness result. "
            "Try asking about NAV, expense ratio, drawdown, volatility, surplus, risk capacity or the three clocks."), grounding


def answer(messages: list[dict[str, str]], ctx: dict[str, Any]) -> dict[str, Any]:
    question = messages[-1]["content"]
    settings = get_settings()
    guardrails = ["FirstRupee is educational decision support, not investment advice, and does not execute trades."]
    if settings.llm_enabled:
        context = untrusted_block("investor_context_and_question", {
            "investor_constraints": ctx.get("readiness"),
            "stored_research": ctx.get("research", []),
            "stored_simulations": ctx.get("simulations", []),
            "conversation": messages[-6:],
        })
        result = call_json(ASSISTANT_SYSTEM, context, AssistantDraft)
        if result.ok and not any(p.search(result.data.answer) for p in BLOCKED_PATTERNS):
            return {"answer": result.data.answer, "mode": "LLM", "provider": result.provider,
                    "grounding": ["Readiness figures are quoted from the deterministic engine."], "guardrails": guardrails}
        reason = result.kind if not result.ok else "UNSAFE_OUTPUT"
        guardrails.append(f"Language model answer unavailable ({reason}); deterministic answer shown.")
    text, grounding = _deterministic(question, ctx)
    return {"answer": text, "mode": "DETERMINISTIC", "provider": "deterministic", "grounding": grounding, "guardrails": guardrails}
