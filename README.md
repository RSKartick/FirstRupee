# FirstRupee

**Invest with understanding, not uncertainty.**

FirstRupee is an educational decision-intelligence platform for first-time investors. It starts by understanding the investor
(Financial DNA and a deterministic Investment Readiness Engine) before analysing any investment. It can explain why an investor
should postpone taking risk. It does not give buy or sell instructions, predict markets or act as a regulated adviser.

| Layer | Technology |
| --- | --- |
| Frontend | SvelteKit 2, Svelte 5, TypeScript (strict), Tailwind CSS v4, Lucide icons, Vitest |
| Backend | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, Pandas, NumPy, HTTPX, argon2-cffi, pytest |
| Database | SQLite by default; any SQLAlchemy URL (for example PostgreSQL) through `DATABASE_URL` |
| AI | Optional OpenAI-compatible model behind a provider-independent client; deterministic engines otherwise |

## Repository layout

```
frontend/   SvelteKit application (routes, components, typed API client, Vitest tests)
backend/    FastAPI application
  app/core        configuration, Argon2id hashing, sessions helpers, errors
  app/db          engine/session factory, Decimal-safe column type, migrations runner
  app/models      SQLAlchemy 2 ORM tables (owner-scoped)
  app/schemas     Pydantic request/response contracts and money validation
  app/services
    financial_engine  dates, exact money, versioned rules, readiness, timing, market metrics
    simulator         Pandas/NumPy scenario engine (no look-ahead, cash-flow-neutral returns, XIRR)
    ai_engine         LLM client, prompts, research analyst/devil's advocate, evaluator, assistant
    passport          reproducible Decision Passport composition
  app/data_sources  provider boundary and the synthetic demonstration catalogue
  app/repositories  owner-scoped queries
  alembic/          migrations (versions/ holds the schema history)
  tests/            pytest suite (engines, AI failure paths, security, API journeys, migrations)
scripts/start.mjs   production launcher (backend + SvelteKit server on one public port)
docker-compose.yml  two-service deployment (written; see the status note below)
```

## Quick start (local)

Requirements: Node.js 20+ (22 recommended), Python 3.11+ with `venv`, and optionally Docker.

```bash
# 1. Frontend dependencies
npm --prefix frontend ci

# 2. Backend virtual environment and pinned dependencies
#    Debian/Ubuntu: sudo apt install python3.11-venv   (venv needs ensurepip)
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt        # exact pins also in requirements.lock.txt
cd ..

# 3. Optional configuration (the demo needs none)
cp .env.example backend/.env

# 4. Automated tests
npm --prefix frontend run test          # Vitest unit tests
(cd backend && .venv/bin/python -m pytest -q)

# 5. Type check and production build
npm run check
npm run build

# 6. Run the production stack on http://localhost:3000
npm run start
```

Development mode (two terminals):

```bash
(cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8000)
BACKEND_URL=http://127.0.0.1:8000 npm --prefix frontend run dev    # http://localhost:5173
```

### Database

Migrations run automatically when the API starts (`app/main.py` lifespan → `app/db/migrate.py` → Alembic `upgrade head`). They
can also be run explicitly:

```bash
cd backend
.venv/bin/alembic -c alembic.ini upgrade head          # apply all migrations
.venv/bin/alembic -c alembic.ini revision --autogenerate -m "describe change"   # create a new migration after editing models
```

Money is stored as exact decimal values (`DecimalText`): `NUMERIC(20,4)` on PostgreSQL and decimal text on SQLite. It is never
stored as binary floating point. To use PostgreSQL, set `DATABASE_URL=postgresql+psycopg://user:password@host/db`, install a
driver (`psycopg`) and run the same migrations.

## Demo

Open `http://localhost:3000` and choose **Open Rahul's workspace** or **Open Priya's workspace**. Each button creates a private guest
copy of a fictional investor, so visitors never share edits. You can also register an account.

Live API walk-through against a running server (no API keys needed):

```bash
(cd backend && .venv/bin/python scripts/demo_journey.py http://localhost:3000)
```

## Security model

- **Authentication**: email and password (Argon2id hashing). Sessions are random opaque tokens sent in an `HttpOnly`, `SameSite=Lax`
  cookie (`Secure` when `COOKIE_SECURE=true`). Only a SHA-256 digest of each token is stored. Logout deletes the session.
- **CSRF**: every state-changing request must echo the per-session token in `X-CSRF-Token`. The token is held in memory on the
  client, never in localStorage.
- **Ownership**: every user-owned table carries `user_id`, and every repository query filters by the authenticated user. A record
  belonging to another account returns `404`, the same as a missing record.
- **Associations**: passports reject research or simulations that belong to another profile, and reject a simulation on a different
  instrument from the research.
- **Errors**: responses contain user-safe messages only. Stack traces, SQL and provider bodies are logged server-side, never returned.
- **Secrets**: read from the environment only. None are committed. `.env` files are ignored by Git.
- **Prompt-injection controls**: documents and user text are passed in delimited untrusted-data blocks. Model output must match a
  schema, and every claim is checked by the deterministic evaluator.

Not yet implemented: rate limiting on login, email verification, password reset, account deletion self-service, and audit logs.

## Financial rules (versioned)

Each engine has a rule-set version that is stored with every result:

| Engine | Version | Purpose |
| --- | --- | --- |
| Readiness | `readiness-rules-v2.0` | NOT_READY / PREPARATION / READY_TO_EXPLORE with reasons, inputs and next steps |
| Timing | `timing-rules-v2.0` | Three clocks and an explicit precedence list (R1–R9) |
| Simulator | `simulator-v2.0` | Historical and hypothetical scenarios, cash-flow-neutral metrics |
| Evaluator | `evaluator-rules-v2.0` | Claim-by-claim verification and deterministic material-risk rules |
| Prompts | `prompts-v2.0` | Analyst, devil's advocate and assistant prompts |
| Passport | `passport-v2.0` | Snapshot schema |

Thresholds and their rationale are documented in `backend/app/services/financial_engine/rules.py`. They are educational guardrails,
not universal financial rules or regulatory compliance.

Key definitions used throughout:

- **Monthly surplus** = income − essential expenses − non-essential expenses − EMIs − other commitments.
- **Emergency coverage** = liquid emergency reserve ÷ essential expenses. Unknown when essentials are zero. Unknown is never treated as adequate.
- **Investable monthly money** = surplus − monthly goal need − emergency replenishment (gap to 6 months ÷ 12). Never negative.
- **Time-weighted return** = the cash-flow-neutral return of the strategy (unitised NAV). **Money-weighted return** = XIRR on your dated flows.
  Contributions are never presented as gains.

## Market data

The demonstration uses a fictional catalogue with synthetic, fixed-seed price series and synthetic evidence records. Every record
is labelled `SYNTHETIC`, and every page shows that label. No record has an invented source URL. The data boundary is
`app/data_sources/provider.py`. A real provider (for example an AMFI NAV feed or a licensed equity feed) would implement the same
interface and write `LIVE` rows. Before any real provider is added, verify Indian coverage, licence terms, usage limits, historical
depth and attribution. Scraping protected exchange data or redistributing licensed data is not permitted.

## Known limitations

- The Playwright browser end-to-end suite is **not included**. Verification covers the backend API, the frontend unit tests, the type
  check, the production build and the live API journey script. Browser-level testing remains to be added.
- Dividends, corporate actions, fees, taxes and inflation are excluded from simulations (stated on every run).
- The language-model path is implemented and tested against mocked responses. It has not been run against a live provider here.
- Docker Compose files are written but were not executed in this environment.
- Live market-data adapters are not implemented. Only the synthetic demonstration dataset is available.
- No authentication hardening beyond the measures above (no MFA, lockout or email verification).
- The readiness and timing rules are educational heuristics, not validated psychometric or financial ratings.
- A commercial deployment requires separate review of applicable SEBI requirements, data licences and privacy obligations.

## Stack note

The earlier Next.js/Drizzle implementation was replaced to meet the SvelteKit + FastAPI requirement. The previous code is preserved
outside this repository. Its engine-level tests were ported to pytest, and its product screens were rebuilt in SvelteKit.
