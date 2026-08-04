#!/usr/bin/env bash
# =============================================================================
# Finance Tracker — Local Setup Script (no Docker required)
# =============================================================================
# Prerequisites:
#   - PostgreSQL 17+ installed via Homebrew and running
#   - Python 3.9+ with venv support
#   - Node.js 18+ and npm
#
# Usage:
#   chmod +x scripts/setup_local.sh
#   ./scripts/setup_local.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
ENV_FILE="$PROJECT_ROOT/.env"

echo "============================================"
echo "  Finance Tracker — Local Setup"
echo "============================================"
echo ""

# ---------- 1. Ensure PostgreSQL is running ----------
echo "[1/7] Checking PostgreSQL..."
if ! pg_isready -q 2>/dev/null; then
  echo "  PostgreSQL is not running. Starting via Homebrew..."
  brew services start postgresql@17 2>/dev/null || brew services start postgresql 2>/dev/null || {
    echo "  ERROR: Could not start PostgreSQL. Please start it manually."
    exit 1
  }
  sleep 2
fi
echo "  PostgreSQL is running."

# ---------- 2. Create database user and database ----------
echo "[2/7] Ensuring database user and database exist..."
psql -U postgres -tc "SELECT 1 FROM pg_roles WHERE rolname = 'finance'" 2>/dev/null | grep -q 1 || \
  psql -U postgres -c "CREATE USER finance WITH PASSWORD 'finance_dev_password';"

psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'finance_db'" 2>/dev/null | grep -q 1 || \
  psql -U postgres -c "CREATE DATABASE finance_db OWNER finance;"

echo "  Database user and database ready."

# ---------- 3. Create .env file ----------
echo "[3/7] Creating .env file..."
if [ ! -f "$ENV_FILE" ]; then
  cat > "$ENV_FILE" <<'EOF'
# Finance Tracker — local development environment
# Copy from .env.example and adjust as needed.

DATABASE_URL=postgresql+asyncpg://finance:finance_dev_password@localhost:5432/finance_db

JWT_SECRET_KEY=change-me-to-a-long-random-string
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8010
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

BCRYPT_ROUNDS=12

VITE_API_URL=http://localhost:8010/api/v1
EOF
  echo "  Created .env (APP_PORT=8010 to match frontend proxy)."
else
  echo "  .env already exists — skipping."
fi

# ---------- 4. Install Python dependencies ----------
echo "[4/7] Checking Python dependencies..."
if [ ! -d "$BACKEND_DIR/venv" ]; then
  echo "  Creating virtual environment..."
  python3 -m venv "$BACKEND_DIR/venv"
fi

source "$BACKEND_DIR/venv/bin/activate"
pip install -q -r "$BACKEND_DIR/requirements.txt"
echo "  Python dependencies installed."

# ---------- 5. Run Alembic migrations ----------
echo "[5/7] Running database migrations..."
cd "$BACKEND_DIR"
export $(grep -v '^#' "$ENV_FILE" | xargs)
alembic upgrade head
echo "  Migrations applied."

# ---------- 6. Seed demo data ----------
echo "[6/7] Seeding demo data..."
python scripts/seed_demo.py
echo "  Demo data seeded."

# ---------- 7. Start backend and frontend ----------
echo "[7/7] Starting services..."
echo ""
echo "  Backend  → http://localhost:8010"
echo "  Frontend → http://localhost:5173"
echo ""
echo "  Starting backend (port 8010)..."
uvicorn main:app --host 0.0.0.0 --port 8010 &
BACKEND_PID=$!

sleep 3

echo "  Starting frontend dev server (port 5173)..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "============================================"
echo "  Setup complete!"
echo "  Backend PID:  $BACKEND_PID"
echo "  Frontend PID: $FRONTEND_PID"
echo "  Demo login:   test@example.com / testpass123"
echo "============================================"
echo ""
echo "  To stop both services:"
echo "    kill $BACKEND_PID $FRONTEND_PID"
echo ""

# Wait for both processes
wait
