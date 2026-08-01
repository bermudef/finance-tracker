# Finance Tracker

Production-quality personal finance web application. Track income, expenses, accounts, credit cards, debt, investments, savings goals, bills, and net worth — with dashboards and analytics.

## Stack

- **Frontend:** React, TypeScript, Tailwind CSS, React Router, Recharts
- **Backend:** FastAPI, SQLAlchemy, Pydantic, JWT auth
- **Database:** PostgreSQL
- **Cloud (future):** Azure App Service, Azure PostgreSQL, Key Vault, Monitor

## Getting Started

1. `cp .env.example .env` and fill in secrets
2. Start PostgreSQL (local or via `docker compose up postgres`)
3. Backend: `cd backend && ./venv/bin/uvicorn main:app --reload`
4. Frontend: `cd frontend && npm run dev`

## Roadmap

See `docs/roadmap.md` for the phased development plan.
