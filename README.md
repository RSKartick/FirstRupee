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

## Vercel deployment

The root `vercel.toml` deploys the SvelteKit web app and FastAPI API as one Vercel project. The project is connected to
GitHub; pushes to `main` deploy production and other branches create previews. Prisma Postgres is the persistent
database. `DATABASE_URL` is used for migrations and `DATABASE_URL_POOLED` for request traffic. Registration saves each
account in PostgreSQL, while passwords are stored as Argon2id hashes.

### Linux and macOS

```bash
# Ensure you are inside the cloned repository root:
cd FirstRupee

# 1. Frontend dependencies
npm --prefix frontend ci

# 2. Backend virtual environment and dependencies
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd ..

# 3. Build frontend
npm run build

# 4. Start the stack on http://localhost:3000
npm run start
```

### Windows (PowerShell)

Make sure you run PowerShell as a regular user and navigate inside the cloned repository directory:

```powershell
# 1. Ensure you are inside the FirstRupee directory, NOT the parent folder:
cd FirstRupee

# Verify package.json exists in your current folder:
Get-ChildItem package.json

# 2. Install frontend dependencies:
npm --prefix frontend ci

# 3. Create backend virtual environment and install dependencies:
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cd ..

# 4. Build the frontend:
npm run build

# 5. Start the full application stack on http://localhost:3000:
npm run start
```

#### Windows Troubleshooting

- **npm error ENOENT (Could not read package.json)**:
  This error happens if PowerShell is open in the parent folder (for example `C:\Users\...\Desktop\graviton`) instead of the project directory. Use `dir` or `ls` to find the `FirstRupee` folder, then run `cd FirstRupee` before executing npm commands.
- **Python script execution blocked**:
  If PowerShell says running scripts is disabled on this system when running `Activate.ps1`, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in the current terminal window.
- **Python error: No module named uvicorn**:
  This happens when `npm start` is run before creating the backend virtual environment in `backend/.venv`. Run `cd backend; python -m venv .venv; .venv\Scripts\pip install -r requirements.txt; cd ..` to install the backend packages.
- **Python command not found**:
  Ensure Python was installed with the "Add python.exe to PATH" checkbox checked.

### Development mode (two terminals)

Terminal 1 (Backend):
```bash
# Linux/macOS:
cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8000

# Windows:
cd backend; .venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Terminal 2 (Frontend):
```bash
# Linux/macOS:
BACKEND_URL=http://127.0.0.1:8000 npm --prefix frontend run dev

# Windows PowerShell:
$env:BACKEND_URL="http://127.0.0.1:8000"; npm --prefix frontend run dev
```

### Database

Migrations run automatically when the API starts (`app/main.py` lifespan -> `app/db/migrate.py` -> Alembic `upgrade head`). They
can also be run explicitly. Market data is not fetched or seeded during normal API startup. To explicitly bootstrap or refresh
the public catalogue with live provider data, run this once from the backend directory:

```bash
cd backend
.venv/bin/python -m app.seed_cli --live
```

Set `SEED_ON_STARTUP=1` only when startup seeding is intentionally needed. The default is off, which avoids outbound
market-data calls on new request-serving instances. The manual command uses the existing database configuration and does
not change account or profile data.

Migrations can also be run explicitly:

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
| Readiness | `readiness-rules-v2.1` | NOT_READY / PREPARATION / READY_TO_EXPLORE with reasons, inputs, next steps and portfolio recommendations |
| Timing | `timing-rules-v2.0` | Three clocks and an explicit precedence list (R1-R9) |
| Simulator | `simulator-v2.0` | Historical and hypothetical scenarios, cash-flow-neutral metrics |
| Evaluator | `evaluator-rules-v2.0` | Claim-by-claim verification and deterministic material-risk rules |
| Prompts | `prompts-v2.0` | Analyst, devil's advocate and assistant prompts |
| Passport | `passport-v2.0` | Snapshot schema |

Thresholds and their rationale are documented in `backend/app/services/financial_engine/rules.py`. They are educational guardrails,
not universal financial rules or regulatory compliance.

Key definitions used throughout:

- **Monthly surplus** = income - essential expenses - non-essential expenses - EMIs - other commitments.
- **Emergency coverage** = liquid emergency reserve / essential expenses. Unknown when essentials are zero. Unknown is never treated as adequate.
- **Investable monthly money** = surplus - monthly goal need - emergency replenishment (gap to 6 months / 12). Never negative.
- **Time-weighted return** = the cash-flow-neutral return of the strategy (unitised NAV). **Money-weighted return** = XIRR on your dated flows.
  Contributions are never presented as gains.

## Market data

The catalogue covers 8 real Indian exchange-traded securities and AMFI-registered direct mutual funds (`TCS.NS`, `TATAPOWER.NS`,
`UTI-NIFTY50`, `PPFAS-FLEXI`, `NIPPON-LIQUID`, `SETF10GILT.NS`, `GOLDBEES.NS`, and `NIFTYBEES.NS`) plus 5 Indian market benchmarks.
Historical daily prices and NAVs are fetched from public feeds (Yahoo Finance v8 chart API for NSE equities/ETFs and `api.mfapi.in`
for AMFI mutual fund schemes), with a deterministic baseline series used when running in an offline or sandboxed test environment
(`FIRSTRUPEE_OFFLINE_SEED=1`). Evidence records are backed by audited annual filings and statutory fund factsheets with official
issuer URLs (`source_url`) and `VERIFIED` provenance status. The data boundary is `app/data_sources/provider.py`.

## Known limitations

- The Playwright browser end-to-end suite is **not included**. Verification covers the backend API, the frontend unit tests, the type
  check, the production build and the live API journey script. Browser-level testing remains to be added.
- Dividends, corporate actions, fees, taxes and inflation are excluded from simulations (stated on every run).
- The language-model path supports Google AI Studio (`GEMINI_API_KEY`) and OpenAI-compatible providers (`LLM_API_KEY`) with deterministic
  guardrails that reject prescriptive buy/sell advice and fall back to rule-based outputs.
- Docker Compose files are written but were not executed in this environment.
- When running offline (`FIRSTRUPEE_OFFLINE_SEED=1` or when Yahoo Finance / MFAPI.in are unreachable), seeding falls back to a
  deterministic baseline series and tags observations as `SAMPLE` rather than `LIVE`.
- No authentication hardening beyond the measures above (no MFA, lockout or email verification).
- The readiness and timing rules are educational heuristics, not validated psychometric or financial ratings.
- A commercial deployment requires separate review of applicable SEBI requirements, data licences and privacy obligations.

## Stack note

The earlier Next.js/Drizzle implementation was replaced to meet the SvelteKit + FastAPI requirement. The previous code is preserved
outside this repository. Its engine-level tests were ported to pytest, and its product screens were rebuilt in SvelteKit.
