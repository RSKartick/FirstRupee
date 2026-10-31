"""Indian Government and Statutory Investment Schemes Catalog.
Provides verified, up-to-date specifications, interest rates, tax regimes,
and eligibility guardrails for retail Indian investors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

SchemeCategory = Literal[
    "TAX_SAVING_AND_WEALTH",
    "RETIREMENT",
    "CHILD_FUTURE",
    "SENIOR_CITIZENS",
    "REGULAR_INCOME",
    "WOMEN_SAVINGS",
    "MACRO_AND_GOLD"
]

TaxTreatment = Literal["EEE", "EET", "TAXABLE_INTEREST", "CAPITAL_GAINS_EXEMPT"]


@dataclass(frozen=True)
class SchemeRule:
    id: str
    name: str
    short_name: str
    authority: str
    category: SchemeCategory
    interest_rate_pct: float
    is_market_linked: bool
    rate_description: str
    compounding_frequency: str
    payout_frequency: str
    min_investment: int
    max_investment_annual: int | None
    lock_in_years: int
    lock_in_description: str
    tax_treatment: TaxTreatment
    tax_section: str
    tax_summary: str
    sovereign_backed: bool
    liquidity_notes: str
    target_demographic: str
    eligibility_summary: str
    fiduciary_role: str
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "short_name": self.short_name,
            "authority": self.authority,
            "category": self.category,
            "interest_rate_pct": self.interest_rate_pct,
            "is_market_linked": self.is_market_linked,
            "rate_description": self.rate_description,
            "compounding_frequency": self.compounding_frequency,
            "payout_frequency": self.payout_frequency,
            "min_investment": self.min_investment,
            "max_investment_annual": self.max_investment_annual,
            "lock_in_years": self.lock_in_years,
            "lock_in_description": self.lock_in_description,
            "tax_treatment": self.tax_treatment,
            "tax_section": self.tax_section,
            "tax_summary": self.tax_summary,
            "sovereign_backed": self.sovereign_backed,
            "liquidity_notes": self.liquidity_notes,
            "target_demographic": self.target_demographic,
            "eligibility_summary": self.eligibility_summary,
            "fiduciary_role": self.fiduciary_role,
            "pros": self.pros,
            "cons": self.cons,
        }


SCHEMES: list[SchemeRule] = [
    SchemeRule(
        id="ppf",
        name="Public Provident Fund (PPF)",
        short_name="PPF",
        authority="Ministry of Finance / National Savings Institute",
        category="TAX_SAVING_AND_WEALTH",
        interest_rate_pct=7.10,
        is_market_linked=False,
        rate_description="7.10% p.a. (Compounded annually, set quarterly by GoI)",
        compounding_frequency="ANNUAL",
        payout_frequency="AT_MATURITY",
        min_investment=500,
        max_investment_annual=150000,
        lock_in_years=15,
        lock_in_description="15 Years (extendable indefinitely in 5-year blocks)",
        tax_treatment="EEE",
        tax_section="Section 80C (up to ₹1,50,000/year)",
        tax_summary="Exempt-Exempt-Exempt: Deposit qualifies for 80C, annual interest is 100% tax-free, and maturity amount is completely exempt from income tax.",
        sovereign_backed=True,
        liquidity_notes="Partial withdrawal allowed from 7th year (up to 50% of balance). Loan facility available between 3rd and 6th financial year.",
        target_demographic="All resident Indian individuals seeking risk-free, long-term wealth compounding.",
        eligibility_summary="Indian residents only. Single account per individual (plus guardian account for minor).",
        fiduciary_role="Anchor for the 20% Fixed Income allocation for horizons > 7 years. Supreme downside capital preservation.",
        pros=[
            "100% Sovereign backing with zero credit or default risk",
            "True EEE tax status with completely tax-free maturity",
            "Cannot be attached by any court order for debts or liabilities",
            "Flexible deposit options from ₹500 to ₹1,50,000 per year"
        ],
        cons=[
            "Strict 15-year initial commitment horizon",
            "Annual deposit capped at ₹1.5 Lakhs per individual",
            "Interest rates are subject to quarterly review by the Government"
        ]
    ),
    SchemeRule(
        id="nps_tier1",
        name="National Pension System (NPS Tier 1)",
        short_name="NPS Tier 1",
        authority="Pension Fund Regulatory and Development Authority (PFRDA)",
        category="RETIREMENT",
        interest_rate_pct=10.20,
        is_market_linked=True,
        rate_description="~9.5% - 11.5% historical CAGR across balanced Equity (E) and Debt (C/G) fund choices",
        compounding_frequency="MARKET_NAV",
        payout_frequency="AT_RETIREMENT",
        min_investment=1000,
        max_investment_annual=None,
        lock_in_years=35,
        lock_in_description="Locked in until age 60 (extendable up to age 75)",
        tax_treatment="EET",
        tax_section="Section 80CCD(1B) extra ₹50k + 80CCD(1) up to ₹1.5L + 80CCD(2) employer",
        tax_summary="Exclusive ₹50,000 deduction under 80CCD(1B) over and above 80C. At age 60, 60% corpus is tax-free lump-sum; 40% mandatory annuity pays taxable pension.",
        sovereign_backed=False,
        liquidity_notes="Partial withdrawal up to 25% of own contribution permitted after 3 years for specific life events (children higher education, home purchase, medical emergency).",
        target_demographic="Working professionals and self-employed individuals building a disciplined retirement nest egg.",
        eligibility_summary="Any Indian citizen aged 18 to 70 years. Resident and Non-Resident Indians (NRIs) eligible.",
        fiduciary_role="Supercharges retirement compounding with ultra-low fund management fees (0.09%) and unmatched ₹50,000 exclusive tax deduction.",
        pros=[
            "Exclusive ₹50,000 tax deduction under 80CCD(1B) unavailable in any other product",
            "Lowest fund management cost in the world (<0.09% p.a.)",
            "Choice of Active allocation (up to 75% equity) or Auto Lifecycle Funds",
            "Additional employer contribution benefits under Section 80CCD(2)"
        ],
        cons=[
            "Mandatory 40% annuity purchase at retirement (pension is taxable)",
            "Strict lock-in until age 60 reduces intermediate liquidity",
            "Market-linked returns can fluctuate during economic drawdowns"
        ]
    ),
    SchemeRule(
        id="ssy",
        name="Sukanya Samriddhi Yojana (SSY)",
        short_name="SSY",
        authority="Ministry of Finance / Beti Bachao Beti Padhao",
        category="CHILD_FUTURE",
        interest_rate_pct=8.20,
        is_market_linked=False,
        rate_description="8.20% p.a. (Highest rate among fixed small-savings schemes; compounded annually)",
        compounding_frequency="ANNUAL",
        payout_frequency="AT_MATURITY",
        min_investment=250,
        max_investment_annual=150000,
        lock_in_years=21,
        lock_in_description="21 Years from account opening (deposits required only for first 15 years)",
        tax_treatment="EEE",
        tax_section="Section 80C (up to ₹1,50,000/year)",
        tax_summary="Triple tax exemption (EEE). 100% tax-free interest and tax-free maturity proceeds under Section 10(11A).",
        sovereign_backed=True,
        liquidity_notes="Partial withdrawal of up to 50% of the balance permitted for higher education once the girl child turns 18 or completes 10th standard.",
        target_demographic="Parents or legal guardians of a girl child below 10 years of age.",
        eligibility_summary="Opened for a girl child from birth up to 10 years. Maximum 2 accounts per family (exception for twin/triplet girls).",
        fiduciary_role="The premier sovereign vehicle for child education milestone goals exceeding 10 years.",
        pros=[
            "Highest guaranteed sovereign interest rate (8.20% p.a.)",
            "EEE tax-exempt status with zero tax on maturity",
            "Affordable minimum deposit (₹250/year)",
            "Protects child's education corpus from household spending pressures"
        ],
        cons=[
            "Strict eligibility: Only for families with a girl child under age 10",
            "Maximum annual contribution limited to ₹1.5 Lakhs",
            "21-year tenure requires patient capital commitment"
        ]
    ),
    SchemeRule(
        id="scss",
        name="Senior Citizens Savings Scheme (SCSS)",
        short_name="SCSS",
        authority="Ministry of Finance",
        category="SENIOR_CITIZENS",
        interest_rate_pct=8.20,
        is_market_linked=False,
        rate_description="8.20% p.a. (Quarterly payout on 1st of April, July, October, January)",
        compounding_frequency="QUARTERLY_PAYOUT",
        payout_frequency="QUARTERLY",
        min_investment=1000,
        max_investment_annual=3000000,
        lock_in_years=5,
        lock_in_description="5 Years (extendable once for 3 additional years)",
        tax_treatment="TAXABLE_INTEREST",
        tax_section="Section 80C (Principal up to ₹1.5L) / Sec 80TTB for interest up to ₹50,000",
        tax_summary="Deposit eligible for 80C deduction. Interest is taxable at slab rate; senior citizens can claim up to ₹50,000 interest deduction under Section 80TTB.",
        sovereign_backed=True,
        liquidity_notes="Premature exit permitted after 1 year (1.5% penalty before 2 years; 1% penalty after 2 years). Fully refundable on account holder demise.",
        target_demographic="Senior citizens aged 60+ (or 55-60 for voluntary retired civil staff / 50+ for defence).",
        eligibility_summary="Resident individuals aged 60 and above. High cumulative ceiling of ₹30 Lakhs per individual.",
        fiduciary_role="Golden benchmark for retired investors requiring sovereign quarterly cash flow and zero credit risk.",
        pros=[
            "High guaranteed yield (8.20% p.a.) backed by the Central Government",
            "Substantial investment ceiling of ₹30 Lakhs (₹60 Lakhs for married couples aged 60+)",
            "Automated quarterly payouts directly credited to bank account",
            "Principal qualifies for Section 80C deduction"
        ],
        cons=[
            "Interest income is taxable as per individual slab rates",
            "Eligibility strictly restricted to seniors (age 60+ or 55+ with VRS)",
            "5-year lock-in with penalty for early withdrawal"
        ]
    ),
    SchemeRule(
        id="pomis",
        name="Post Office Monthly Income Scheme (POMIS)",
        short_name="POMIS",
        authority="Department of Posts / Ministry of Finance",
        category="REGULAR_INCOME",
        interest_rate_pct=7.40,
        is_market_linked=False,
        rate_description="7.40% p.a. (Credited monthly into investor's savings account)",
        compounding_frequency="MONTHLY_PAYOUT",
        payout_frequency="MONTHLY",
        min_investment=1000,
        max_investment_annual=900000,
        lock_in_years=5,
        lock_in_description="5 Years (premature closure permitted after 1 year with minor penalty)",
        tax_treatment="TAXABLE_INTEREST",
        tax_section="None (Interest taxed under Income from Other Sources)",
        tax_summary="No Section 80C deduction. Monthly interest is taxable at applicable slab rates, but no TDS is deducted at source by the Post Office.",
        sovereign_backed=True,
        liquidity_notes="Premature closure after 1 year: 2% deduction from principal between 1 and 3 years; 1% deduction after 3 years.",
        target_demographic="Investors seeking reliable monthly supplementary income with zero capital volatility.",
        eligibility_summary="Any resident Indian adult. Single account ceiling ₹9 Lakhs; Joint account ceiling ₹15 Lakhs.",
        fiduciary_role="Guaranteed monthly cash flow provider for conservative investors needing predictable income.",
        pros=[
            "Reliable monthly cash flow credited on auto-pilot",
            "Enhanced limit of ₹9 Lakhs (Single) and ₹15 Lakhs (Joint)",
            "Zero credit risk backed by the Government of India",
            "No TDS deducted on interest payouts"
        ],
        cons=[
            "No tax deduction on initial principal investment",
            "Interest payout is fully taxable at your income tax slab",
            "Rate of 7.4% is lower than SCSS or SSY"
        ]
    ),
    SchemeRule(
        id="nsc",
        name="National Savings Certificate (NSC VIII Issue)",
        short_name="NSC",
        authority="Department of Posts / Ministry of Finance",
        category="TAX_SAVING_AND_WEALTH",
        interest_rate_pct=7.70,
        is_market_linked=False,
        rate_description="7.70% p.a. (Compounded annually, payable at maturity)",
        compounding_frequency="ANNUAL",
        payout_frequency="AT_MATURITY",
        min_investment=1000,
        max_investment_annual=None,
        lock_in_years=5,
        lock_in_description="5 Years fixed tenure",
        tax_treatment="TAXABLE_INTEREST",
        tax_section="Section 80C (Investment + Reinvested interest for first 4 years)",
        tax_summary="Eligible for 80C deduction. Unique benefit: Annual interest for years 1-4 is deemed reinvested and also qualifies for Section 80C.",
        sovereign_backed=True,
        liquidity_notes="Cannot be withdrawn prematurely except on death of holder or court forfeiture. Accepted as collateral/pledge for bank loans across India.",
        target_demographic="Taxpayers looking for guaranteed 5-year capital compounding and annual 80C deduction.",
        eligibility_summary="Resident Indian individuals (single, joint, or guardian for minor). No maximum investment limit.",
        fiduciary_role="5-year fixed income builder for medium-term goals (down payment, planned sabbatical) with statutory tax shield.",
        pros=[
            "Attractive 7.70% guaranteed rate for a 5-year tenure",
            "No upper ceiling on total investment amount",
            "Reinvested interest for first 4 years qualifies for 80C tax deduction",
            "Can be pledged at commercial banks for quick emergency liquidity"
        ],
        cons=[
            "Year 5 maturity interest is taxable at slab rate",
            "Strict lock-in with zero partial withdrawal facility",
            "Does not pay periodic income (accumulated till maturity)"
        ]
    ),
    SchemeRule(
        id="mssc",
        name="Mahila Samman Savings Certificate (MSSC)",
        short_name="MSSC",
        authority="Ministry of Finance",
        category="WOMEN_SAVINGS",
        interest_rate_pct=7.50,
        is_market_linked=False,
        rate_description="7.50% p.a. (Compounded quarterly, paid on 2-year maturity)",
        compounding_frequency="QUARTERLY",
        payout_frequency="AT_MATURITY",
        min_investment=1000,
        max_investment_annual=200000,
        lock_in_years=2,
        lock_in_description="2 Years tenure (short-term sovereign lock-in)",
        tax_treatment="TAXABLE_INTEREST",
        tax_section="None (No 80C deduction; interest taxable at slab rate)",
        tax_summary="Interest earned is taxable at income slab. No TDS is deducted under Section 194A for MSSC accounts.",
        sovereign_backed=True,
        liquidity_notes="Partial withdrawal of up to 40% permitted after 1 year. Premature closure permitted after 6 months at 5.5% interest rate.",
        target_demographic="Women and minor girls seeking a high-yielding, short-term safe haven for liquid funds.",
        eligibility_summary="Open to women for themselves, or by guardians on behalf of a minor girl. Maximum ₹2 Lakhs per individual.",
        fiduciary_role="Intermediate 2-year capital parking yielding 7.5%, outperforming standard 2-year bank fixed deposits.",
        pros=[
            "High 7.50% quarterly-compounded yield for a short 2-year horizon",
            "40% partial withdrawal allowed after just 12 months",
            "Zero credit risk sovereign certificate",
            "No TDS deducted on interest earnings"
        ],
        cons=[
            "Maximum investment capped at ₹2 Lakhs per person",
            "Strict gender requirement (women and minor girls only)",
            "No Section 80C tax deduction on deposit"
        ]
    ),
    SchemeRule(
        id="sgb",
        name="Sovereign Gold Bonds (SGB) & RBI Retail Direct",
        short_name="SGB / RBI Direct",
        authority="Reserve Bank of India (RBI)",
        category="MACRO_AND_GOLD",
        interest_rate_pct=2.50,
        is_market_linked=True,
        rate_description="2.50% p.a. cash coupon + Market price appreciation of 999 purity Gold",
        compounding_frequency="SEMI_ANNUAL_PAYOUT",
        payout_frequency="SEMI_ANNUAL",
        min_investment=6000,
        max_investment_annual=4000000,
        lock_in_years=8,
        lock_in_description="8 Years (early exit window with RBI in 5th, 6th, and 7th year; tradeable on NSE/BSE)",
        tax_treatment="CAPITAL_GAINS_EXEMPT",
        tax_section="Section 47(viic) - 100% Tax-Free Capital Gains on RBI Redemption",
        tax_summary="Entire capital gains at 8-year maturity redemption are 100% exempt from income tax. Semi-annual 2.5% coupon is taxable at slab rate.",
        sovereign_backed=True,
        liquidity_notes="Secondary market liquidity on NSE/BSE. Premature redemption window directly with RBI after 5 years on coupon payout dates.",
        target_demographic="Investors seeking a physical-gold hedge without making charges, storage risk, or purity issues.",
        eligibility_summary="Resident Indian individuals, HUFs, and trusts. Up to 4 kg gold equivalent per financial year.",
        fiduciary_role="The optimal vehicle for the FirstRupee 10% Gold allocation, generating coupon income on top of gold appreciation.",
        pros=[
            "100% Capital gains tax exemption upon 8-year maturity redemption",
            "Guaranteed 2.50% p.a. additional coupon paid directly to bank account",
            "Zero storage fees, zero GST on purchase, and zero theft risk",
            "Can be held conveniently in demat format or physical RBI certificate"
        ],
        cons=[
            "Subject to international gold price volatility and currency fluctuations",
            "Secondary market trading volume can have liquidity discounts",
            "New tranches depend on RBI issuance calendars"
        ]
    ),
    SchemeRule(
        id="epf",
        name="Employees' Provident Fund & VPF",
        short_name="EPF / VPF",
        authority="Employees' Provident Fund Organisation (EPFO)",
        category="RETIREMENT",
        interest_rate_pct=8.25,
        is_market_linked=False,
        rate_description="8.25% p.a. (Compounded annually, set annually by the CBT EPFO)",
        compounding_frequency="ANNUAL",
        payout_frequency="AT_RETIREMENT",
        min_investment=1800,
        max_investment_annual=None,
        lock_in_years=25,
        lock_in_description="Locked in until retirement or 2 months of job cessation",
        tax_treatment="EEE",
        tax_section="Section 80C (up to ₹1.5L) / Tax-free interest up to ₹2.5L employee contribution",
        tax_summary="EEE tax status for annual employee contributions up to ₹2,50,000. Interest on employee contributions above ₹2.5 Lakhs is taxable.",
        sovereign_backed=True,
        liquidity_notes="Partial advances allowed for home loan repayment, house purchase, daughter/son marriage, and medical emergency.",
        target_demographic="Salaried corporate and government employees covered under the EPF Act.",
        eligibility_summary="Salaried employees in organizations with 20+ staff. Can voluntarily increase contribution up to 100% of Basic via VPF.",
        fiduciary_role="Foundational capital preservation anchor for salaried retail investors.",
        pros=[
            "High 8.25% risk-free compounding rate",
            "Automatic payroll deduction enforces savings discipline",
            "Employer matching contribution (12% of Basic)",
            "Voluntary Provident Fund (VPF) allows surplus deployment at 8.25%"
        ],
        cons=[
            "Only accessible to salaried employees in covered organizations",
            "Interest on employee contribution exceeding ₹2.5L/year is taxable",
            "EPFO claim settlement process can experience administrative delays"
        ]
    ),
    SchemeRule(
        id="apy",
        name="Atal Pension Yojana (APY)",
        short_name="APY",
        authority="PFRDA / Government of India",
        category="RETIREMENT",
        interest_rate_pct=8.00,
        is_market_linked=False,
        rate_description="Guaranteed monthly pension (₹1,000 to ₹5,000/month) for life after age 60",
        compounding_frequency="PENSION_ACCUMULATION",
        payout_frequency="MONTHLY_POST_60",
        min_investment=500,
        max_investment_annual=18000,
        lock_in_years=20,
        lock_in_description="Locked until age 60",
        tax_treatment="EET",
        tax_section="Section 80CCD",
        tax_summary="Contributions eligible for Section 80CCD deduction. Monthly pension received after age 60 is taxable at slab rate.",
        sovereign_backed=True,
        liquidity_notes="Premature exit before age 60 is permitted only under exceptional cases (death of subscriber or terminal illness).",
        target_demographic="Young workers aged 18 to 40 in unorganized sectors or beginning modest careers.",
        eligibility_summary="Indian citizens aged 18 to 40 with a savings bank account. Must not be an income tax payer.",
        fiduciary_role="Guaranteed sovereign safety floor ensuring minimum dignified retirement pension.",
        pros=[
            "Guaranteed minimum pension backed by Central Government co-contribution",
            "Spouse receives the exact same pension on subscriber death; corpus returns to nominee",
            "Extremely low monthly contribution if started early (e.g., ₹210/month at age 18 for ₹5,000 pension)",
            "Deductions under Section 80CCD"
        ],
        cons=[
            "Maximum pension capped at ₹5,000/month (may face inflation erosion over decades)",
            "Income tax payers are legally ineligible to join since October 2022",
            "Strict exit restrictions before age 60"
        ]
    )
]

SCHEMES_MAP = {s.id: s for s in SCHEMES}


def get_all_schemes(category: str | None = None) -> list[SchemeRule]:
    if not category or category.upper() == "ALL":
        return SCHEMES
    cat_upper = category.upper()
    return [s for s in SCHEMES if s.category == cat_upper]


def get_scheme_by_id(scheme_id: str) -> SchemeRule | None:
    return SCHEMES_MAP.get(scheme_id.lower())
