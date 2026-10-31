"""Shared investment-advice guardrail patterns used by the assistant, research evaluator, and passport composer.

Detects imperative buy/sell/hold commands, guaranteed or risk-free return claims, price target predictions,
and urgency-pumping language while allowing descriptive educational explanations.
"""

from __future__ import annotations

import re
from typing import Any

ADVICE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "IMPERATIVE_BUY_SELL",
        re.compile(
            r"\b("
            r"buy\s+(?:[a-z0-9.\-]+\s+)?now|"
            r"sell\s+(?:[a-z0-9.\-]+\s+)?now|"
            r"you\s+(?:should|must|need\s+to)\s+(?:buy|sell|invest\s+in|put\s+(?:your|all)\s+money\s+in|accumulate|load\s+up\s+on)|"
            r"invest\s+your\s+(?:entire\s+)?(?:emergency\s+fund|savings|salary)\s+in|"
            r"strong\s+(?:buy|sell)\s+(?:call|signal|recommendation)|"
            r"we\s+recommend\s+(?:buying|selling|investing\s+in)"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "GUARANTEED_OR_RISK_FREE_RETURN",
        re.compile(
            r"\b("
            r"\d+%\s*guaranteed\s*(?:profit|return|returns|gain|gains)|"
            r"guaranteed\s+(?:profit|return|returns|to\s+multiply|to\s+double|gain|gains|wealth)|"
            r"guaranteed\s+returns?\s+of\s+\d+%?|"
            r"risk[-\s]?free\s+(?:profit|return|returns|gain|gains|equity|stock)|"
            r"sure[-\s]?shot\s+(?:profit|return|returns|multibagger)|"
            r"zero[-\s]?risk\s+(?:profit|return|returns|high\s+return)"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "PRICE_TARGET_OR_MULTIPLIER_PREDICTION",
        re.compile(
            r"\b("
            r"(?:price|stock|nav|it)\s+will\s+(?:reach|touch|hit|cross|double|triple|multiply)\s+(?:rs\.?\s*|inr\s*|₹\s*)?\d+|"
            r"multiply\s+\d+\s*x|"
            r"\b\d+\s*x\s+(?:return|returns|multibagger|guaranteed)|"
            r"target\s+price\s+(?:of|is)\s+(?:rs\.?\s*|inr\s*|₹\s*)?\d+"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "URGENCY_PUMPING",
        re.compile(
            r"\b("
            r"act\s+fast\s+before|"
            r"don'?t\s+miss\s+this\s+(?:rally|jackpot|multibagger|guaranteed)|"
            r"once[-\s]+in[-\s]+a[-\s]+lifetime\s+(?:buy|stock|investment)|"
            r"buy\s+immediately"
            r")\b",
            re.IGNORECASE,
        ),
    ),
]

REDACTED_PROSE_NOTICE = (
    "[Redacted by FirstRupee guardrail: promotional or prescriptive buy/sell advice language was removed. "
    "FirstRupee provides educational evidence checks only, not buy or sell instructions.]"
)


def detect_advice_violations(text: str | None) -> list[dict[str, str]]:
    """Return a list of matched advice violations in `text`."""
    if not text:
        return []
    violations: list[dict[str, str]] = []
    for category, pattern in ADVICE_PATTERNS:
        match = pattern.search(text)
        if match:
            violations.append({
                "category": category,
                "matched": match.group(0),
            })
    return violations


def contains_advice(text: str | None) -> bool:
    """Return True if `text` triggers any advice guardrail pattern."""
    return bool(detect_advice_violations(text))


def scan_research_prose(analyst: dict[str, Any] | None, devil: dict[str, Any] | None) -> list[dict[str, str]]:
    """Scan all free-text fields and claims in `analyst` and `devil` for prescriptive advice."""
    findings: list[dict[str, str]] = []

    def _check(field_name: str, value: Any) -> None:
        if isinstance(value, str):
            for v in detect_advice_violations(value):
                findings.append({
                    "field": field_name,
                    "category": v["category"],
                    "matched": v["matched"],
                })
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                if isinstance(item, str):
                    _check(f"{field_name}[{idx}]", item)
                elif isinstance(item, dict) and "claim" in item:
                    _check(f"{field_name}[{idx}].claim", item.get("claim"))

    if analyst:
        _check("analyst.overview", analyst.get("overview"))
        _check("analyst.thesis", analyst.get("thesis"))
        _check("analyst.developments", analyst.get("developments"))
        _check("analyst.claims", analyst.get("claims"))
    if devil:
        _check("devil.counter_thesis", devil.get("counter_thesis"))
        _check("devil.missing_information", devil.get("missing_information"))
        _check("devil.claims", devil.get("claims"))
    return findings


def sanitize_prose(text: str | None) -> str:
    """Return `text` if clean, or a safe redaction notice if it contains prescriptive advice."""
    if not text:
        return ""
    if contains_advice(text):
        return REDACTED_PROSE_NOTICE
    return text
