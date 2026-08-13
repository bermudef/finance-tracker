# Finance Tracker

Production-quality personal finance web application. Track income, expenses, accounts, recurring transactions, credit cards, debt, investments, savings goals, and net worth — with dashboards and analytics.

## AI Capstone Summary

### Project Title

Finance Tracker: AI-Assisted Personal Finance Dashboard and Analytics Web App

### Problem Statement

Many people can record transactions, but still struggle to understand their real month-to-month financial position. Inconsistent treatment of pending transactions, unclear cash-flow visualizations, fragmented debt tracking, and poor recurring-payment visibility make it hard to answer simple questions like:

- How much cash do I actually have left this month?
- How much have I really spent so far?
- How heavy is my debt burden relative to my income?
- Which recurring charges are automatic and which are manual?

This project solves that problem by building a web application that keeps balances, statements, debt, recurring payments, and dashboard analytics consistent across the product.

### Successful Outcome

A successful solution would:

- show accurate balances and statements
- exclude pending transactions from official totals while still displaying them in the transaction feed
- present debt, mortgage, and recurring-payment data consistently across pages
- provide a clear current-month cash-flow visualization
- support realistic demo data for multiple household profiles

### AI Tools Used

- AI coding assistant for architecture review, prompt iteration, implementation, refactoring, and debugging
- Terminal/database tools for verifying live PostgreSQL data and API behavior
- Git/GitHub workflow for version control and final delivery

### Why These Tools Were Selected

- The AI assistant was useful for iterative prompt-based software development, code review, UI refinement, and cross-file consistency checks.
- Live database and API verification were necessary to confirm that fixes were not only correct in code, but also correct in runtime behavior.

### Prompt Development and Iteration

The project was built through iterative prompting rather than a single one-shot instruction. Representative prompt patterns included:

1. Initial diagnosis
- identify why statements, charts, and transactions were inconsistent
- inspect frontend and backend data flow before changing code

2. Refinement and correction
- align dashboard, statement, and health-score calculations
- define a consistent rule for pending transactions
- correct debt-burden logic so status matched actual DTI bands

3. Product-level iteration
- remove unnecessary frontend sections (Tools and Bills)
- move auto-pay into Recurring Transactions
- improve chart semantics and transaction status UX
- update seed data and documentation so the app matched the intended product scope

### Results

The final system now includes:

- consistent pending-transaction behavior across balances, dashboard, statements, budgets, health, and net worth
- current-month running cash-flow chart showing remaining cash and cumulative expenses
- mortgage included in debt tracking and debt summaries
- recurring transactions with auto-pay support
- improved transaction status visibility (`posted`, `pending`, `cleared`)
- updated seed data with more realistic insurance values and mortgage debt for the Parker profile
- frontend cleanup removing Bills and Tools from the shipped webapp scope

### Output / Evidence

Evidence of the workflow and results includes:

- backend tests covering dashboard, reports, health, notifications, accounts, tools, and recurring logic
- frontend typechecking across the updated UI
- seeded demo households with realistic financial profiles
- commit history in the GitHub repository documenting incremental changes

### Reflection

This project showed that the most valuable use of AI was not just code generation, but structured iteration:

- define the problem clearly
- inspect the real data flow first
- change one rule at a time
- verify the result with tests and live data

The biggest lesson was that small inconsistencies in sign conventions, date bounds, status handling, and UI wording can make a finance app feel untrustworthy even when most of the code is technically correct. AI was most effective when used as a collaborator for repeated diagnosis, implementation, and verification cycles rather than as a shortcut.

### Future Improvements

- add full migrations for every schema change automatically in the development workflow
- reintroduce advanced tools only when their scope clearly fits the core product
- expand automated tests around visual/reporting semantics and seeded demo expectations
- add user-facing reporting exports and deeper analytics once the core financial model is stable

## Stack

- **Frontend:** React 19, TypeScript, Tailwind CSS v4, React Router 7, Recharts (route-level code splitting)
- **Backend:** FastAPI, SQLAlchemy 2 (async), Pydantic v2, Alembic migrations
- **Database:** PostgreSQL 17
- **Auth:** JWT (access + rotating refresh tokens), bcrypt password hashing, password reset tokens
- **Cloud (deployment target):** Azure App Service, Azure Database for PostgreSQL, Azure Key Vault, Azure Monitor
- **CI:** GitHub Actions (pytest against a Postgres service container + frontend build)

## Features

- Register, login, refresh, password reset (email-less demo token via dev endpoint)
- Accounts, categories, budgets, transactions with search + filters
- Credit cards, debts, investments, savings goals, and recurring transactions
- CSV export/import for transactions (bank-statement-friendly, per-row error reporting)
- Dashboard: net worth, current-month running cash flow, spending by category, debt, investments, savings progress
- Monthly statements with pending transactions excluded from totals
- Transaction statuses (`posted`, `pending`, `cleared`) with filters and inline badges
- Recurring transactions with auto-pay tracking
- Ownership isolation: every query and mutation is scoped to the authenticated user

## Getting Started

### 1. Prerequisites

- PostgreSQL 17 (local, or `docker compose up postgres`)
- Python 3.9+ with a venv in `backend/venv`
- Node 20+ with `npm ci` in `frontend`

### 2. One-Command Setup (recommended)

```bash
# Starts PostgreSQL (if needed), creates DB user/database, installs deps,
# runs migrations, seeds demo data, and launches both servers.
chmod +x scripts/setup_local.sh
./scripts/setup_local.sh
```

This starts the backend on `http://localhost:8010` and the frontend on `http://localhost:5173`.

The seeded demo data starts on `2026-01-01` and continues through the present day so each household’s balances, debts, and transactions reflect a realistic year-to-date picture.

If you pull new backend changes later, rerun the database migration before starting the app so schema updates (for example, recurring transaction auto-pay fields) are applied:

```bash
cd backend
./venv/bin/alembic upgrade head
```

### Demo household accounts

The seeded demo data includes three households with different financial situations. Use the email as the username when logging in:

- `parker.family@example.com` / `ParkerFamily!2025` — stable, high-income household with low debt and strong savings
- `nguyen.family@example.com` / `NguyenFamily!2025` — growing household with moderate income, childcare costs, and manageable debt
- `garcia.family@example.com` / `GarciaFamily!2025` — stretched household with higher debt, lower savings, and tighter cash flow

For the original test account used during project setup, the legacy demo login remains:

- `test@example.com` / `testpass123`

### 2b. Manual Setup

```bash
cp .env.example .env   # fill in JWT_SECRET_KEY, database URL, etc.
```

**Backend:**

```bash
cd backend
./venv/bin/pip install -r requirements.txt
./venv/bin/alembic upgrade head
./venv/bin/uvicorn main:app --host 127.0.0.1 --port 8010   # note: main:app, not app.main:app
```

Seed demo data (idempotent — safe to rerun):

```bash
cd backend
./venv/bin/python scripts/seed_demo.py
# demo logins:
# parker.family@example.com / ParkerFamily!2025
# nguyen.family@example.com / NguyenFamily!2025
# garcia.family@example.com / GarciaFamily!2025
# legacy test account: test@example.com / testpass123
```

After reseeding, restart the backend so updated demo profile data and API changes are reflected in the running app.

**Frontend:**

```bash
cd frontend
npm ci
npm run dev   # http://localhost:5173, proxies /api to :8010
```

## Docker / Production Topology

`docker compose up --build` runs the production-style stack (matches Azure):

- `postgres` — managed-DB equivalent
- `backend` — runs `alembic upgrade head` then uvicorn on :8000
- `frontend` — nginx serving the built SPA, reverse-proxying `/api` to the backend

### Run with Docker

1. Copy the environment file:

```bash
cp .env.example .env
```

2. Start the stack:

```bash
docker compose up --build
```

3. Open the app:

```text
Frontend: http://localhost:3000
Backend API: http://localhost:8000
```

4. Seed demo data from the backend container shell if needed:

```bash
docker compose exec backend ./venv/bin/python scripts/seed_demo.py
```

5. Stop the stack:

```bash
docker compose down
```

6. Stop the stack and remove database data too:

```bash
docker compose down -v
```

For Azure App Service: push the `backend` and `frontend` images to ACR, set app settings (`DATABASE_URL`, `JWT_SECRET_KEY`, `CORS_ORIGINS`) from Key Vault references, and point the custom domain at the frontend container. `npm run build` in CI gates regressions before deploy.

## Testing

```bash
cd backend
./venv/bin/python -m pytest tests/ -q     # 87 tests: auth, CRUD, ownership isolation, dashboard, CSV
```

The suite runs against a throwaway `finance_test_db` with tables truncated between tests.

## Roadmap

See `docs/roadmap.md` for the phased development plan.
