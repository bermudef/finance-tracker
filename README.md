# Finance Tracker

Production-quality personal finance web application. Track income, expenses, accounts, credit cards, debt, investments, savings goals, bills, and net worth — with dashboards and analytics.

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
- Credit cards, debts, investments, savings goals, bills (full CRUD)
- CSV export/import for transactions (bank-statement-friendly, per-row error reporting)
- Dashboard: net worth, cash flow, spending by category, debt, investments, savings progress
- Ownership isolation: every query and mutation is scoped to the authenticated user

## Getting Started

### 1. Prerequisites

- PostgreSQL 17 (local, or `docker compose up postgres`)
- Python 3.9+ with a venv in `backend/venv`
- Node 20+ with `npm ci` in `frontend`

### 2. Configure

```bash
cp .env.example .env   # fill in JWT_SECRET_KEY, database URL, etc.
```

### 3. Backend

```bash
cd backend
./venv/bin/pip install -r requirements-dev.txt
./venv/bin/alembic upgrade head
./venv/bin/uvicorn main:app --host 127.0.0.1 --port 8010
```

Seed demo data (idempotent — safe to rerun):

```bash
cd backend
DATABASE_URL=postgresql+asyncpg://finance:...@localhost:5432/finance_db \
  PYTHONPATH=. ./venv/bin/python scripts/seed_demo.py
# demo login: test@example.com / testpass123
```

### 4. Frontend

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

For Azure App Service: push the `backend` and `frontend` images to ACR, set app settings (`DATABASE_URL`, `JWT_SECRET_KEY`, `CORS_ORIGINS`) from Key Vault references, and point the custom domain at the frontend container. `npm run build` in CI gates regressions before deploy.

## Testing

```bash
cd backend
./venv/bin/python -m pytest tests/ -q     # 87 tests: auth, CRUD, ownership isolation, dashboard, CSV
```

The suite runs against a throwaway `finance_test_db` with tables truncated between tests.

## Roadmap

See `docs/roadmap.md` for the phased development plan.
