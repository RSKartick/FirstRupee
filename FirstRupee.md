# FirstRupee — Complete Project Development Plan



Recommended project direction

Fintech



# FirstRupee

## Invest with understanding, not uncertainty.

[FinSight — Investment Dashboard & Portfolio Management UI Design by Trakshym LLP on Dribbble](https://images.openai.com/static-rsc-4/LR-XEsC1kV34RbkBUZEHYmCE8hqaG8b0cJXpYLwkAnMEfoq-X0CEufjBeTe2m-dS_ZCYZ7y4ibOjjqJiG0dC_BObqilVLaHkS30ch-q8_Itf2HAgxxDaogbNV1cb3s2XMXzJNFgDVB4yZZCdkHo03R_4ZF_BRWavnGcZAZK99Ro?purpose=inline)

[dribbble.com](https://dribbble.com/shots/27344116-FinSight-Investment-Dashboard-Portfolio-Management-UI-Design?utm_source=chatgpt.com)

Product vision

An AI-powered investment decision assistant that helps first-time investors understand their financial position, explore suitable investment options, evaluate risks, and make informed decisions about when and how to invest.

The product should not be positioned as another AI stock-picking application.

FirstRupee is an investment decision intelligence platform.

It should understand the investor before analysing the investment.

That distinction should drive the entire architecture.

# 1. Problem definition

## The problem we are solving

A significant number of new retail investors face three related problems:

Problem 1 — Investment confusion

People have money available but do not understand the differences between stocks, mutual funds, ETFs, bonds, fixed deposits and other investment avenues.

They often depend on friends, social media, influencers and random online recommendations.

Problem 2 — No understanding of personal financial suitability

Someone earning ₹30,000 monthly with no emergency savings has a very different financial situation from someone earning ₹1,00,000 with substantial savings.

Yet both people might receive the same investment recommendation from a generic AI chatbot.

Problem 3 — Timing uncertainty

Beginners struggle with questions such as:

- Should I invest now or wait?
- Should I invest everything at once?
- Should I invest monthly?
- What if the market falls immediately after I invest?
- What if I need the money unexpectedly?

Most importantly, they do not understand the consequences of different decisions.

## Our solution

FirstRupee creates a structured process:

Understand the investor

Financial profile, goals, obligations, experience

Assess investment readiness

Financial capacity and risk tolerance

Explore investment opportunities

Asset classes, research and comparisons

Evaluate both sides

Investment thesis, counter-thesis, risk analysis

Simulate possible outcomes

Historical performance and hypothetical scenarios

Generate Decision Passport

Transparent, evidence-backed investment analysis

The output is not necessarily a stock recommendation. It could be an explanation of why investing is premature, which asset categories deserve research, or how to approach a long-term investment goal.

# 2. Product modules

I would divide FirstRupee into seven functional modules. Six should form the main working product; the seventh is the future expansion.

## Module 1 — Investor Onboarding and Financial DNA

Essential

This is the first interaction with FirstRupee.

Instead of immediately displaying a chatbot, introduce the user to a guided onboarding process.

[Vinay Singh Chouhan — Design Lead & Product Designer](https://images.openai.com/static-rsc-4/2CPTC_fec3HDY_oomhoxRxB0h9RKpbW6Y3uxwNimkGcEh6xOmYVvj2pzsw4fbkaKNrKL0IXxytheA1NNe-9xzV1V8dqOwRS3lADR0_OjUUNp_PiWH8Pe32FFgJNEhs3bNYQHirDJr0cuIvX8mUowtipFyOU4ViUSk8qT_dHXYIE?purpose=inline)

[vinaysinghchouhan.com](https://vinaysinghchouhan.com/?utm_source=chatgpt.com)

### Information to collect

| Category            | Information                            |
| ------------------- | -------------------------------------- |
| Basic profile       | Age range, employment status           |
| Income              | Monthly take-home income               |
| Expenditure         | Monthly essential expenses             |
| Liabilities         | Loans, EMIs, other obligations         |
| Savings             | Existing liquid savings                |
| Investments         | Current stocks, MFs, FDs etc.          |
| Experience          | Beginner, intermediate, experienced    |
| Goal                | Wealth creation, education, home, etc. |
| Goal duration       | When the money will be needed          |
| Investment capacity | Amount potentially available monthly   |
| Risk tolerance      | Comfort with fluctuations and losses   |

Avoid asking for PAN, Aadhaar, bank credentials or brokerage passwords in the prototype.

### Risk questionnaire

Don't ask only:

"What is your risk appetite?"

That's too vague.

Ask behavioural and financial-capacity questions separately.

For example:

Question 1: Suppose an investment of ₹10,000 falls to ₹8,000. What would you do?

- Sell immediately.
- Wait until it recovers.
- Reassess the underlying investment.
- Invest more, provided the original reasons remain valid.

Question 2: Would losing ₹2,000 affect your ability to pay monthly expenses?

- Yes, significantly.
- Somewhat.
- No.

These questions measure different things:

- Risk tolerance: how much volatility the investor is psychologically comfortable with.
- Risk capacity: how much loss the investor can financially absorb.

Do not treat them as interchangeable.

### Output: Financial DNA

The application generates an understandable profile:

Your Financial DNA

# First-time investor

Needs preparation

| Attribute          | Assessment   |
| ------------------ | ------------ |
| Experience         | Beginner     |
| Investment horizon | Short-term   |
| Risk tolerance     | Moderate     |
| Financial capacity | Limited      |
| Emergency buffer   | Insufficient |
| Monthly surplus    | ₹4,000       |

AI explanation

Your willingness to take investment risk appears higher than your current financial capacity to absorb losses. These should be considered separately.

Use clear status explanations rather than presenting an arbitrary readiness score as a scientifically validated result.

## Module 2 — Investment Readiness Engine

Major differentiator

This is the first major intelligence layer.

Most investment applications focus on finding investments.

FirstRupee should first determine whether the user has money that is genuinely available for investment.

### How it works

The financial engine calculates:

A. Monthly available cash

\\[ \text{Surplus} = \text{Income} - \text{Expenses} - \text{EMIs} - \text{Commitments} \\]

B. Emergency fund coverage

\\[ \text{Coverage} = \frac{\text{Liquid emergency savings}} {\text{Essential monthly expenditure}} \\]

C. Investment horizon

The number of months until the user's goal.

D. Financial risk capacity

Derived from cash reserves, debt obligations, income stability and the user's ability to withstand losses.

### Example decision rules

| Financial situation             | FirstRupee response                              |
| ------------------------------- | ----------------------------------------------- |
| Negative monthly surplus        | Address cash flow first                         |
| Insufficient emergency savings  | Prioritise financial buffer                     |
| High-interest debt              | Assess debt repayment priority                  |
| Goal approaching soon           | Separate goal money from long-term risk capital |
| Stable finances, long horizon   | Explore diversified investment options          |
| High concentration in one asset | Highlight concentration risk                    |

Thresholds should be configurable, documented and treated as educational guardrails, not universal financial laws.

### Output: Readiness status

Three possible outcomes:

Not ready

Build financial stability

The system identifies financial constraints that make taking investment risk inappropriate for the user's stated goal.

Preparation

Understand and plan

The user has some investment capacity but should consider liquidity, existing obligations and knowledge gaps.

Ready to explore

Compare investment options

The financial profile supports exploring suitable investment approaches, subject to further assessment.

The key is that the AI cannot override the financial engine just because a user asks it to recommend a trending stock.

## Module 3 — Investment Discovery Engine

Essential

This addresses the original purpose of your idea: helping users understand where they could invest.

[Fintech Investment Dashboard UI Design — Portfolio & Analytics by Nasir Uddin  on Dribbble](https://images.openai.com/static-rsc-4/jRGmZH0xc22IuiUHSHhjyihfodT4jrmPCttBWurJ9R6RyNIgbfkI1xFH9j4FyiJFFaE1jzg7QKwGOQKg5AIXwU9QrbxxwYTTTAPdTre8ckbBEOqNCZWPbhhFn35I4NAbSU2bm87bA2Q0KxD9DqNYF_AVRdZmUDPpbtoewUn6RVY?purpose=inline)

[dribbble.com](https://dribbble.com/shots/27119550-Fintech-Investment-Dashboard-UI-Design-Portfolio-Analytics?utm_source=chatgpt.com)

### Asset categories

For the first version, support:

| Category              | What FirstRupee explains                           |
| --------------------- | ------------------------------------------------- |
| Stocks                | Individual company ownership and associated risks |
| Index mutual funds    | Diversified market exposure                       |
| Other mutual funds    | Different investment objectives and strategies    |
| ETFs                  | Exchange-traded fund structures                   |
| Fixed deposits        | Interest, maturity and liquidity                  |
| Government securities | Sovereign debt and interest-rate risks            |
| Gold                  | Exposure to gold prices                           |

You don't need to implement every category fully during the hackathon. Three or four well-supported categories are sufficient.

### How discovery works

Suppose a user says:

"I want to invest ₹5,000 every month for 10 years."

The system considers:

1. Their financial readiness.
2. Their goal.
3. Their ability to absorb losses.
4. Their investment knowledge.
5. The characteristics of different asset classes.

It then displays an educational shortlist with explanations.

For example:

Investment research explorer

Broad-market index funds

Explore

What it is: A mutual fund or ETF designed to track a specified market index.

Potential advantages: Diversification and transparent index-based exposure.

Risks: Market-wide losses, tracking error, valuation risk and fund expenses.

Fixed-income options

Explore

What it is: Instruments that provide interest or other contractual cash flows.

Potential advantages: Different risk and cash-flow characteristics from equities.

Risks: Interest-rate risk, credit risk and liquidity constraints depending on the product.

For individual stocks, add a research explorer that allows users to investigate companies rather than presenting an unqualified buy list.

### What makes it different?

Each suggestion must contain a Why this fits / Why this might not fit explanation.

This prevents the product from becoming a ranking engine that simply selects the highest historical return.

## Module 4 — AI Research Analyst and Devil's Advocate

Technical differentiator

This is the main AI component.

I recommend two research agents and a deterministic evaluator.

[Traidechart – AI Bull vs Bear Analysis](https://images.openai.com/static-rsc-4/XcWQDZD6ju4t3IBS6gnpJz75oXvWX3FM_aglqsBoBQpxDUrwjVCeptPgi6hUDca8JpLRuHPste-z0iiqc695DYZ8ML__jh3_wbYn_JZuW4RWu92bN-DPhaoz2FnU1y58Xy8Ac5x7XMMG2Dms4esy2a0pjf8jk7X41eLbqMTyqtQ?purpose=inline)

[traidechart.com](https://traidechart.com/?utm_source=chatgpt.com)

### Agent A — Research Analyst

Its responsibilities:

- Examine available financial information.
- Study revenue and profitability.
- Examine financial statements.
- Identify debt and cash-flow trends.
- Calculate or retrieve relevant financial ratios.
- Summarise relevant developments.
- Explain the investment thesis.

Example output:

"The company's revenue has increased over the available reporting periods, while operating profitability has also improved. However, the valuation and cash-flow characteristics require further investigation."

It must cite the underlying data.

### Agent B — Devil's Advocate

Its job is deliberately different.

It tries to disprove the research thesis.

It examines:

- Rising debt.
- Falling margins.
- Declining cash flow.
- Excessive valuation.
- Unusual financial changes.
- Negative corporate developments.
- Industry-specific risks.
- Conflicting evidence.

Example:

"Despite revenue growth, operating cash flow has weakened. This creates a potential discrepancy between reported growth and cash generation."

### Final Evaluator — Evidence and Suitability Check

This should not be another LLM that simply votes on whether the company is good.

It is primarily a deterministic validation layer.

It checks:

- Whether the required source data exists.
- Whether the data is recent enough for the analysis.
- Whether numerical values are internally consistent.
- Whether the research conflicts with the investor's stated goal.
- Whether the conclusion is supported by the evidence.

It can return:

- Evidence supports further investigation.
- Material risks identified.
- Insufficient evidence.
- Investment horizon mismatch.
- Financial readiness constraints.

The key feature: FirstRupee must be capable of returning "insufficient evidence."

That is a better design than manufacturing a confident answer.

### AI orchestration

```
User selects an asset
        |
        v
Fetch verified financial data
        |
        v
Calculate financial metrics
        |
        +-------------------------+
        |                         |
        v                         v
  Research Analyst          Devil's Advocate
        |                         |
        v                         v
  Bullish thesis             Bearish thesis
        |                         |
        +------------+------------+
                     |
                     v
             Evidence Evaluator
                     |
                     v
            Suitability Checks
                     |
                     v
              Final Analysis
```

You can use the same LLM with separate system prompts for the two analysis roles. You do not need multiple expensive models.

## Module 5 — Three-Clock Timing Engine

Core differentiator

This is how FirstRupee addresses the question of when to invest.

Don't attempt to predict the exact next market bottom. That's a difficult and often misleading promise.

Instead, distinguish three different timing dimensions.

The Three-Clock Engine

Money Clock

When will the user have available money?

Income dates, monthly surplus, cash reserves and obligations.

Goal Clock

When will the user need the money?

Goal deadlines, expected expenses, planned withdrawals.

Market Clock

What is happening in the market?

Volatility, valuations, historical trends and financial developments.

### Example

A person receives ₹30,000 salary on the 1st of every month.

They have:

- ₹18,000 in monthly essential expenses.
- ₹4,000 in monthly EMI obligations.
- A goal of purchasing something worth ₹50,000 in 10 months.
- Some existing savings.

The Money Clock calculates when money may become available.

The Goal Clock establishes that this money is intended for a relatively near-term expense.

The Market Clock provides market context but cannot override the goal deadline.

### Possible outputs

- Do not use short-term goal money for volatile investments.
- Consider establishing a periodic investing schedule for long-term funds.
- Reassess when income, liabilities or goals change.
- Investigate whether current market conditions introduce additional risks.

The system explains its reasoning rather than issuing an unsupported "buy today" alert.

## Module 6 — What-If Investment Simulator

Essential demo feature

[Scenario & Stress Testing | Uptick Product Documentation](https://images.openai.com/static-rsc-4/BkJ8LyRg_4SzgENG2l4pCngdVkAXl4_L2H6pATuT5XX1URlz6PoOB76k4qE0DzT2LCVWDo1rKto7lCYao9AIxCNCgIRnDyxSx1FyBwyDWTLLHEHeCYUF-ZeUXJDvlF0Z8iiy0lSIxynIqz3gqaIE7x50cMjG4PoXXZGC8raD0Ao?purpose=inline)

[docs.uptick.co](https://docs.uptick.co/prism/scenario-and-stress-testing?utm_source=chatgpt.com)

This module allows users to understand the consequences of different decisions.

### Example input

A user has ₹30,000 available for a hypothetical investment plan.

FirstRupee compares:

| Scenario | Approach                              |
| -------- | ------------------------------------- |
| A        | Invest ₹30,000 at once                |
| B        | Invest ₹5,000 monthly for six months  |
| C        | Delay investing and retain liquidity  |
| D        | Compare an alternative asset category |

### What to calculate

1\. Return calculations

For historical performance:

\\[ R = \left(\frac{P_t}{P_0}-1\right)\times100 \\]

2\. Annualised volatility

For daily returns:

\\[ \sigma\_{annual}=\sigma\_{daily}\sqrt{252} \\]

3\. Maximum drawdown

\\[ MDD=\min\left(\frac{P_t}{P\_{peak}}-1\right) \\]

4\. Hypothetical loss scenarios

If someone invests ₹30,000:

| Market movement | Portfolio value |
| --------------- | --------------- |
| -10%            | ₹27,000         |
| -20%            | ₹24,000         |
| -30%            | ₹21,000         |
| +10%            | ₹33,000         |

These are hypothetical scenarios, not forecasts.

### Important features

Show:

- Historical rolling returns where reliable data exists.
- Best and worst historical windows.
- Maximum drawdown.
- Risk comparisons.
- Different contribution schedules.
- Goal completion under hypothetical assumptions.

The simulator should visibly state the data period, assumptions and limitations.

Do not invent a 12% expected return merely to make the graph look attractive.

## Module 7 — Decision Passport

Signature feature

This combines the findings of every module into one structured result.

[How to Analyze a Stock Portfolio: Steps, Metrics and Tools](https://images.openai.com/static-rsc-4/ZOiBh4qomd4P7P4hIwgeRW5GBMonVu4VTTk-UBrkkOo3Kk_oNVEZ0PjsqBnsQIvlCDoMrkbPkfGc9pjffTVPHBT5K7VPMgYlvxdAFMlPgR8PnR-1GFSiho93ue7agIsFldsUD47OZgPv-mk9QOSLAHTEZHIrqzvpJBrp5iP2pdY?purpose=inline)

[ziggma.com](https://ziggma.com/how-to-analyze-stock-portfolio?utm_source=chatgpt.com)

Every analysis generates an individual Decision Passport.

### Suggested structure

| Section           | Information                                 |
| ----------------- | ------------------------------------------- |
| Investor profile  | Financial DNA                               |
| Readiness         | Financial readiness assessment              |
| Objective         | Investment goal and duration                |
| Investment thesis | Reasons to investigate an opportunity       |
| Counter-thesis    | Reasons the opportunity could be unsuitable |
| Risk assessment   | Possible financial downside                 |
| Timing rationale  | Why now, later or periodically              |
| Scenario analysis | Alternative outcomes                        |
| Evidence          | Source links and dates                      |
| Review triggers   | Events that require reassessment            |

### An interesting addition: Thesis Expiry Conditions

This is worth implementing if time allows.

Suppose an investment thesis depends on:

- Revenue growth continuing.
- Debt remaining manageable.
- Profit margins improving.

FirstRupee records these assumptions.

When new data contradicts one of them, the system highlights that the original reasoning may no longer hold.

This makes the Decision Passport useful beyond the initial recommendation.

# 3. User interface and application structure

I recommend a desktop-first responsive web application. It will be easier for judges to interact with on their laptops.

## Main screens

[Savvy | Index Ventures](https://images.openai.com/static-rsc-4/-bxZ5f8FB3YImUYLk8RG0QKYFysErwy2YY3aHJNfq1G01wBMu8KfRl8Q6G1Diqdb5rgnQrHYLQu3LZyO7iBHaEnpVg3kTJtyJuFMM1LNXoayZxaBNlFzmWAWkRPIL0csBbZsISY75EhgCdlBt2f-O53wha1CYek1Mv1NcMvI3uU?purpose=inline)

1\. Landing page

FirstRupee introduction, key value proposition and start assessment button.

[Onboarding Step by Step Template by brigit_dev on Dribbble](https://images.openai.com/static-rsc-4/DpPcedJSVhR4V35xtc-2tWwi4aUtvIBrxr75gpklk-EdY__Ih-fyASmCJggz-RIBQFEnSQ1-K9iVdDGYs1pJVYqPKelAJgnME4hAkwZhxDEdD80_6slUCQASqCNBn0KUAYWmAFAedT4CVNOndiprdUoGk6tokL_LMvIptdEM0bk?purpose=inline)

2\. Financial onboarding

Guided financial profile and investment goals questionnaire.

[New portfolio analytics tool in the Scalable Broker  - identify opportunities and risks with “Insights”](https://images.openai.com/static-rsc-4/FIndgUu7F96L5X7I1rHOgcOlbNn47RRchxis8MuCpC0bJx0KCFqGLHSC1gMQq1huo7yUo7c565ZR9bN7oP46qgW0ksqNiLrdSqLh9M-w8CjAd7pMagLB9L7YPI-qOudxLec5hUazo1XIFbJz5tL1ZNRkmRtfZUvA_91B0yQJI1I?purpose=inline)

3\. Investor dashboard

Financial DNA, readiness status, goals and available actions.

[PredictRAM – AI-Powered Investment Intelligence](https://images.openai.com/static-rsc-4/nOk9Osy_oSjMQE1cEqhO1Gc7OyDbDKXbhFRnu9Nsyy4HzTe6sFwYXv4Jk2qY-lVNHUaEOe2dgz5Ybj6besW1MA92VRFxdJlnnPWpjhUVsJ-rY9V5MUDXnrcF4N5Hcadw-K-NDN8PJE-spOEuU1eQnOwN0Hr-lUm5Ff4cgQ8Zyos?purpose=inline)

4\. Discovery explorer

Asset categories, comparison, risk profiles and research.

[StockSense — The investing app that teaches you](https://images.openai.com/static-rsc-4/k34Zd-QovmmfDdrFXXKqP5nHMwQhY_9J3u73WN15Ml_FuMpRZdmec74BZFCtTrlfTXiVRxI1ms95_yAshab3Wmp4L1bJahWG0Ow91d8VxgmXDvc0pjMMSIbJsKDK5wqXGIdjbZbMiPNwJNPc4fnSCW7MO73fxN2iFeg1CXRuaO0?purpose=inline)

5\. AI research assistant

Analyst findings, Devil's Advocate findings and source references.

[Free Wealth Education for Australians | Ripper Wealth | Ripper Wealth](https://images.openai.com/static-rsc-4/a62wweJeaNHwhSwBbrqKoiEVsQ8NL8YLu7RXusF_mMrlUywJED_W7uUvuhBOQaGIWU1Kl2lnsBBgnT0zEz5eIngqMdrYwHvlr3xBlIThokT-Op_344b-i1HebbSUwe2MhDps4R5p71C68xFAZEk3By9vPwm8gY9ExP07GCOMMAo?purpose=inline)

6\. Simulator

Interactive scenarios, drawdowns and investment comparisons.

[Fund Information Dashboard by Ganidu Ranasinghe on Dribbble](https://images.openai.com/static-rsc-4/ZzpdRhH3Xu8s51F9IRNjHJVYnA8k_UVKY5LQVlGaJNsCDBEqU13WL3s2f1zG6vqAqy9LFZbHR0gFyePet1MUq61-xOmZ513BozGWdJZ7ySwzUzP8zLenJ-0Mi03ir8lgMzS_Sy24x1r1Ykrj-Gny_JkTLITPJJgl-mQdB0cSnTM?purpose=inline)

7\. Decision Passport

Final structured report with evidence and review triggers.

### Recommended navigation

```
FirstRupee
|
+-- Dashboard
|
+-- My Financial DNA
|
+-- Investment Explorer
|   +-- Stocks
|   +-- Mutual Funds
|   +-- ETFs
|   +-- Fixed Income
|
+-- AI Research
|
+-- What-If Simulator
|
+-- Decision Passports
|
+-- Settings
```

A conversational assistant can be accessible throughout the application, but it should not replace the dedicated interfaces.

# 4. Technical architecture

This is the architecture I recommend for your implementation.

## FirstRupee system architecture

React / Vite Frontend

Dashboard · Onboarding · AI Assistant · Charts · Simulator

REST API

FastAPI Backend

Validation · User profile · Orchestration · API endpoints

Financial Engine

Python · Pandas · NumPy

Readiness, risk metrics, simulations

AI Orchestrator

LLM · Structured outputs

Analyst, skeptic, explanations

Market Data Layer

API adapters · CSV

Prices, NAV, fundamentals

Evidence Layer

Source metadata · Retrieval

Documents, timestamps, citations

SQLite / PostgreSQL

Profiles · Assets · Historical data · Analysis results · Decision Passports

## Technology stack

| Layer                 | Recommended technology                      |
| --------------------- | ------------------------------------------- |
| Frontend              | React + Vite                                |
| Styling               | Tailwind CSS                                |
| Components            | shadcn/ui                                   |
| Charts                | Recharts                                    |
| Backend               | Python + FastAPI                            |
| Financial computation | Pandas + NumPy                              |
| Validation            | Pydantic                                    |
| Database              | SQLite for MVP                              |
| AI                    | LLM API with structured JSON outputs        |
| Data retrieval        | REST API adapters                           |
| Deployment            | Vercel + Render or a single deployed server |

Don't introduce microservices, Kubernetes or distributed queues. You have a short build window and a small team.

## Backend API design

These are the principal endpoints.

| Endpoint                      | Purpose                          |
| ----------------------------- | -------------------------------- |
| `POST /api/profile`           | Save investor profile            |
| `POST /api/readiness/analyze` | Assess investment readiness      |
| `GET /api/assets`             | Retrieve asset catalogue         |
| `GET /api/assets/{id}`        | Retrieve asset details           |
| `POST /api/research/analyze`  | Run Analyst and Devil's Advocate |
| `POST /api/simulator/run`     | Run scenarios                    |
| `POST /api/passport/generate` | Generate Decision Passport       |
| `GET /api/passport/{id}`      | Retrieve saved analysis          |

### Suggested database structure

```
users
-----
id
created_at

investor_profiles
-----------------
id
user_id
monthly_income
monthly_expenses
monthly_emi
liquid_savings
emergency_savings
monthly_surplus
investment_experience
risk_tolerance
goal_name
goal_amount
goal_deadline

assets
------
id
name
symbol
asset_type
description
currency

market_data
-----------
id
asset_id
date
open
high
low
close
volume
source
retrieved_at

research_analyses
-----------------
id
asset_id
analyst_output
devils_advocate_output
evidence_json
created_at

decision_passports
------------------
id
profile_id
readiness_status
investment_thesis
counter_thesis
risk_assessment
timing_rationale
simulation_json
sources_json
created_at
```

For the hackathon, authentication can be omitted or kept simple using a demo session. Avoid spending hours on account management instead of the actual product.

# 5. Market data and information sources

This is one of the most important engineering decisions.

A financial AI application is only as reliable as its input data.

Do not allow the LLM to generate current stock prices, financial ratios or historical returns from memory.

### Recommended data sources

| Information                  | Source                                                |
| ---------------------------- | ----------------------------------------------------- |
| Mutual fund NAV              | AMFI                                                  |
| Equity market data           | Licensed market-data API                              |
| Company financial statements | Company investor-relations pages and official filings |
| Macroeconomic data           | RBI DBIE                                              |
| Investment regulations       | SEBI                                                  |

AMFI offers latest and historical mutual fund NAV information through its official website.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.amfiindia.com\&sz=32)

AMFI India+1



For equity data, evaluate licensed providers such as Twelve Data. Its documentation covers stocks, funds, historical time series and financial statements, but verify the availability of the Indian symbols and the access level of your API plan before committing to it.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://twelvedata.com\&sz=32)

Twelve Data



Important: NSE's market-data usage policy governs access, use and redistribution, and its commercial market-data products require applicable agreements. Don't build a commercial product around unofficial scraping of NSE pages.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.nseindia.in\&sz=32)

NSE India



### Hackathon data strategy

I recommend:

- A small curated equity dataset.
- Historical NAV samples for a few mutual funds.
- A few company financial-statement snapshots.
- A fixed collection of trustworthy financial documents.

For the demo, use clearly labelled data with its source and date. An offline sample-data mode is perfectly acceptable.

This gives you predictable demonstrations without depending on API availability or rate limits.

# 6. AI implementation strategy

Do not give the AI unrestricted access to everything.

Give it structured information and specific jobs.

## Example research response format

Your AI analysis endpoint should return a structured object like this:

```
{
  "asset": "Example Company",
  "data_as_of": "2026-10-30",
  "research": {
    "thesis": [
      "Revenue increased in the supplied reporting periods.",
      "Operating margins improved."
    ],
    "counter_thesis": [
      "Operating cash flow requires further investigation.",
      "Valuation may already reflect expected growth."
    ],
    "risks": [
      "Debt exposure",
      "Valuation risk",
      "Industry concentration"
    ]
  },
  "suitability_checks": {
    "goal_horizon_match": "requires_review",
    "financial_readiness": "ready_to_explore"
  },
  "evidence_quality": "medium",
  "uncertainties": [
    "Latest reporting period unavailable"
  ],
  "sources": [
    {
      "title": "Company annual report",
      "url": "https://example.com/report",
      "date": "2026-09-30"
    }
  ],
  "status": "further_research_required"
}
```

The source URL here is a placeholder for the schema, not an actual source.

### Important AI rules

The system prompt should explicitly instruct the model:

1. Never fabricate financial figures.
2. Never invent source URLs.
3. Use only the provided financial dataset and retrieved documents.
4. Distinguish historical facts from hypothetical scenarios.
5. Present bullish and bearish evidence.
6. Clearly identify missing information.
7. Never guarantee investment returns.
8. Never treat recent price appreciation as proof of future growth.
9. Never override the readiness engine.
10. Explain results in language suitable for first-time investors.

### Model selection

You don't need the most expensive model.

Choose a model that reliably follows JSON schemas, handles financial reasoning and can produce grounded summaries.

Keep the financial engine independent of the model so that the application continues working even when the LLM API fails.

# 7. Security, privacy and regulatory considerations

This cannot be an afterthought because FirstRupee will process financial information.

### Privacy and security

- Never collect bank or broker passwords.
- Don't request unnecessary personal identifiers.
- Store API keys in environment variables.
- Validate user-submitted financial values.
- Avoid logging complete financial profiles.
- Provide a way to delete stored user data.
- Use synthetic profiles during the public demonstration.

### SEBI considerations

This is particularly important for the long-term product.

SEBI's Investment Advisers Regulations define investment advice broadly, including advice about investing in, purchasing or selling securities, and financial planning. The regulatory position depends on the actual nature of the service and how it is offered.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.sebi.gov.in\&sz=32)

Securities and Exchange Board of India



The regulations also address risk profiling, assessing the capacity to absorb losses, suitability of recommendations and the use of AI by registered investment advisers.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.sebi.gov.in\&sz=32)

Securities and Exchange Board of India+1



For the hackathon:

- Position FirstRupee as an educational and investment research prototype.
- Use simulated investor profiles.
- Avoid executing trades.
- Avoid presenting personalised securities buy/sell instructions as regulated advice.
- Do not assume a disclaimer alone removes regulatory obligations.

For a commercial launch, obtain appropriate regulatory advice before offering personalised investment advice.

# 8. Development plan for GRAVITON

The official GRAVITON page specifies a 24-hour build, teams of 3–4 and working-prototype judging. It lists the main hacking start at 11:00 on October 31, the mentor round at 17:00, the midnight checkpoint and code freeze at 10:00 on November 1.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://iste.cgcuniversity.in\&sz=32)

iste.cgcuniversity.in



The schedule below is organised around those checkpoints.

## Phase 1 — Foundation

11:00–13:00

Objective: Establish a running application and a common data contract.

Tasks:

- Create the GitHub repository.
- Set up React frontend.
- Set up FastAPI backend.
- Create project structure.
- Define database schema.
- Define API contracts.
- Finalise one demo investor profile.
- Create frontend and backend running locally.

Deliverable: Frontend and backend communicate successfully.

## Phase 2 — Financial DNA and Readiness

13:00–17:00

Objective: Build the first functional financial intelligence module.

Tasks:

- Investor onboarding form.
- Financial profile storage.
- Monthly surplus calculations.
- Emergency buffer assessment.
- Goal duration calculations.
- Risk tolerance and capacity assessment.
- Readiness classification.
- Dashboard display.

At the 17:00 mentor checkpoint, you should be able to demonstrate a user completing onboarding and receiving a meaningful financial readiness assessment.

Deliverable: Working financial profile and readiness engine.

## Phase 3 — Investment Discovery and Data

17:00–20:00

Objective: Enable investment research.

Tasks:

- Build asset catalogue.
- Implement sample market-data loading.
- Create asset comparison interface.
- Integrate source and timestamp information.
- Add risk and performance metrics.
- Build an asset details page.

Do not spend too long searching for a perfect API. Get your data adapter working with a reliable sample dataset first.

Deliverable: Users can explore and compare investment options.

## Phase 4 — AI Research and Devil's Advocate

20:00–00:00

Objective: Implement the differentiating AI functionality.

Tasks:

- Connect the selected LLM API.
- Create research analyst prompt.
- Create Devil's Advocate prompt.
- Pass verified financial metrics to both.
- Add structured JSON outputs.
- Implement evidence references.
- Implement final validation and synthesis.
- Add failure fallback.

At the midnight checkpoint, demonstrate that one investment receives both positive and negative analysis.

Deliverable: Working dual-perspective research engine.

## Phase 5 — Simulator and Three-Clock Engine

00:00–03:00

Objective: Demonstrate decision-making rather than merely chatting.

Tasks:

- Create the timing engine.
- Build hypothetical market-shock scenarios.
- Implement investment contribution simulations.
- Add historical performance calculations if the dataset supports them.
- Visualise the outcomes.
- Connect the simulator to the investor profile.

Deliverable: Interactive investment simulator.

## Phase 6 — Decision Passport and Full Integration

03:00–06:00

Objective: Connect all modules together.

Tasks:

- Build Decision Passport template.
- Connect profile and readiness.
- Connect research output.
- Connect simulation results.
- Add source references.
- Save passport to database.
- Add review conditions.
- Implement final report page.

Deliverable: Complete end-to-end workflow.

## Phase 7 — Testing and UI Polish

06:00–08:00

Objective: Remove failures that could ruin the demonstration.

Test:

- No income or negative surplus.
- Missing savings information.
- Short-term goals.
- High existing debt.
- Inconsistent questionnaire answers.
- Invalid financial data.
- Missing market data.
- Expired API responses.
- LLM timeout or malformed response.
- Missing source references.

Also check responsive layout, loading states and error messages.

## Phase 8 — Finalisation

08:00–10:00

Objective: Prepare a stable submission.

Tasks:

- Final bug fixes.
- Remove debug logs.
- Check API keys and environment configuration.
- Prepare README.
- Verify every screen.
- Rehearse the demo.
- Push the final repository.
- Complete submission before the organiser's code freeze.

Do not introduce major new features during this phase.

# 9. Team allocation

For four people, use this arrangement.

| Member   | Responsibility                   | Main deliverable                              |
| -------- | -------------------------------- | --------------------------------------------- |
| Person 1 | Frontend developer               | UI, onboarding, dashboard, charts             |
| Person 2 | Backend developer                | FastAPI, database, readiness and calculations |
| Person 3 | AI and data engineer             | LLM, analyst, skeptic, market-data adapters   |
| Person 4 | Integration and product engineer | Simulator, Passport, QA, deployment           |

For three people:

- Person 1: Frontend and UI.
- Person 2: Backend and financial calculations.
- Person 3: AI, data integration and Passport.

Everyone should work against agreed API contracts. Avoid having two people independently build the same backend functionality.

### Git collaboration

Use a simple repository structure:

```
firstrupee/
|
+-- frontend/
|   +-- src/
|       +-- components/
|       +-- pages/
|       +-- services/
|       +-- charts/
|
+-- backend/
|   +-- app/
|       +-- api/
|       +-- models/
|       +-- services/
|       +-- financial_engine/
|       +-- ai_engine/
|       +-- data_sources/
|
+-- sample_data/
|
+-- docs/
|
+-- README.md
+-- .gitignore
```

Use separate branches:

```
main
|
+-- feature/frontend
+-- feature/financial-engine
+-- feature/ai-research
+-- feature/simulator
```

Integrate small changes frequently. Keep `main` deployable.

# 10. What NOT to build during the hackathon

This matters just as much as the features you build.

| Feature                     | Decision | Reason                                    |
| --------------------------- | -------- | ----------------------------------------- |
| Real broker integration     | Skip     | Authentication and transaction complexity |
| Automatic trading           | Skip     | Not necessary for the problem             |
| Real-time market prediction | Skip     | Unreliable and time-consuming             |
| 50+ asset categories        | Skip     | Difficult to validate                     |
| Full portfolio tracking     | Later    | Requires extensive data integration       |
| Complex ML forecasting      | Skip     | Hard to validate                          |
| Multiple LLM models         | Skip     | Unnecessary orchestration overhead        |
| Tax optimisation engine     | Later    | Additional complexity                     |
| Regional-language support   | Optional | Add only after core works                 |

Do not confuse technical complexity with product quality.

A reliable 6-module workflow will score better than 15 unfinished features.

# 11. Demonstration strategy

Your demo should tell a story, not just show screens.

I'd prepare two fictional investors.

## Investor A — The investor who is not ready

Demo profile: Rahul

Completely fictional investor profile

| Attribute         | Value                |
| ----------------- | -------------------- |
| Monthly income    | ₹30,000              |
| Monthly expenses  | ₹20,000              |
| Monthly EMI       | ₹4,000               |
| Savings           | ₹20,000              |
| Goal              | ₹50,000 in 10 months |
| Experience        | Beginner             |
| Available surplus | ₹6,000               |

User asks:

"I have ₹20,000. Everyone is talking about a particular stock. Should I invest?"

FirstRupee responds:

Your existing savings represent only one month of essential expenditure. You also have a goal approaching within 10 months.

Using your goal money for volatile equity exposure could create a liquidity problem.

Outcome: Build financial stability and separate short-term goal money from long-term investment capital.

Show the Anti-FOMO challenge, readiness calculation and decision explanation.

## Investor B — The investor ready to explore

Demo profile: Priya

Completely fictional investor profile

| Attribute         | Value     |
| ----------------- | --------- |
| Monthly income    | ₹80,000   |
| Monthly expenses  | ₹35,000   |
| Monthly EMI       | ₹5,000    |
| Emergency savings | ₹2,50,000 |
| Monthly surplus   | ₹40,000   |
| Goal horizon      | 10 years  |
| Experience        | Beginner  |

User asks:

"I want to invest ₹10,000 monthly for long-term wealth creation. What should I understand before choosing?"

FirstRupee responds:

It explores diversified investment categories, compares risks and historical performance, and provides both positive and negative research perspectives.

The simulator illustrates what different market conditions could mean for the user's contributions.

Outcome: Educational investment comparison and a Decision Passport.

Showing both investors makes a crucial point: FirstRupee does not give everyone the same recommendation.

# 12. Presentation to the judges

Use a five-slide pitch.

| Slide | Content                                                              |
| ----- | -------------------------------------------------------------------- |
| 1     | Problem: Beginners don't understand where, when or whether to invest |
| 2     | Solution: FirstRupee and its investment decision workflow             |
| 3     | Differentiation: Readiness Engine, Three Clocks and Devil's Advocate |
| 4     | Live demonstration                                                   |
| 5     | Architecture, scalability, impact and future scope                   |

### Suggested opening pitch

Imagine someone has saved their first ₹20,000.

They want to invest, but they don't know where to start. They open social media, see a trending stock and decide to put their savings into it.

Most investment applications will help them find an investment.

But what if the more important question is whether they should invest that money at all?

This is the problem we are solving with FirstRupee.

FirstRupee is an AI-powered investment decision companion designed for first-time investors.

It first understands the user's financial situation, assesses their investment readiness, explores investment options, challenges investment assumptions through opposing AI research perspectives, and simulates possible outcomes.

Instead of blindly telling people where to invest, FirstRupee helps them understand the decision they're making.

Because the first step towards smarter investing isn't picking a stock. It's understanding your money.

# 13. How FirstRupee can evolve after the hackathon

The hackathon MVP is only the starting point.

I would divide the future roadmap into three stages.

1. Stage 1 — Financial Decision Companion

   Hackathon MVP
   - Financial DNA.
   - Readiness Engine.
   - Investment Discovery.
   - AI Analyst and Devil's Advocate.
   - Three-Clock Engine.
   - What-If Simulator.
   - Decision Passport.
2. Stage 2 — Continuous Investment Intelligence
   - Portfolio import using permitted integrations.
   - Portfolio concentration analysis.
   - Investment thesis monitoring.
   - Company results and corporate event tracking.
   - Periodic reassessment of investor goals.
   - Multi-language explanations.
   - Better historical backtesting.
3. Stage 3 — Personal Financial Intelligence Platform
   - Broader financial planning.
   - More sophisticated asset-class research.
   - Goal-based planning.
   - Personalised alerts and monitoring.
   - Adviser-assisted workflows.
   - Compliant commercial advisory integration where appropriate.

# 14. Final feature prioritisation

This is the scope I would commit to.

FirstRupee build checklist

0/11 completed

Investor onboarding

Financial profile and goals

P0

Readiness engine

Deterministic financial assessment

P0

Investment discovery

Explore and compare asset categories

P0

AI Analyst

Evidence-based research

P0

Devil's Advocate

Counter-thesis and risk analysis

P0

Three-Clock Engine

Money, goal and market timing

P0

What-If Simulator

Historical and hypothetical outcomes

P0

Decision Passport

Complete evidence-backed report

P0

Live portfolio integration

Connected portfolio tracking

P2

Multi-language assistant

Regional language support

P2

Automatic thesis monitoring

Monitor invalidating developments

P1

Reset checklist

P0 means required for the hackathon demonstration. P1 is a meaningful extension. P2 is future scope.

# 15. The three things that will make FirstRupee stand out

I would concentrate your engineering effort on these:

1\. It can tell someone not to invest.

The Readiness Engine should be capable of rejecting an unsuitable investment path based on the user's financial circumstances.

2\. It challenges its own investment research.

The Devil's Advocate should identify material weaknesses in the original investment thesis, backed by actual evidence.

3\. Every conclusion is explainable and traceable.

The Decision Passport should tell the user what was considered, what assumptions were made, what evidence was used and what could invalidate the reasoning.

These three features reinforce each other. They form a coherent product rather than a collection of unrelated AI features.

My recommended final positioning:

# FirstRupee

## Invest with understanding, not uncertainty.

An AI-powered financial decision intelligence platform for first-time investors.

Understand your money. Evaluate your options. Challenge your assumptions. Make informed decisions.

Core innovation: Financial Readiness Engine + Three-Clock Timing Engine + AI Devil's Advocate + Decision Passport.

The objective for the hackathon should be to demonstrate one complete investor journey, from initial financial assessment to an evidence-backed investment decision report. That is the product worth building.