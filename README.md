# Finance Tracker

Production-quality personal finance web application. Track income, expenses, accounts, recurring transactions, credit cards, debt, investments, savings goals, and net worth — with dashboards and analytics.

## AI Capstone

The full AI capstone write-up is in [`README_CAPSTONE.md`](./README_CAPSTONE.md).

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
