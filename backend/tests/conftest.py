"""
Test fixtures.

Design notes:
- DATABASE_URL is pointed at finance_test_db *before* app imports so the
  engine in app.models.database binds to the test database.
- A single session-scoped event loop is used for every test (see pytest.ini)
  so SQLAlchemy's async pool never crosses event-loop boundaries.
- Tables are truncated (with RESTART IDENTITY) before each test for isolation.
"""
from __future__ import annotations

import os

os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://finance:finance_dev_password@localhost:5432/finance_test_db"
)

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

import app.models.finance  # noqa: E402,F401  (register tables)
import app.models.password_reset  # noqa: E402,F401
import app.models.user  # noqa: E402,F401
from app.models.database import Base, engine  # noqa: E402
from main import app  # noqa: E402

API = "/api/v1"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_schema():
    """Create the full schema once for the whole test session."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    """Truncate all tables before every test for deterministic isolation."""
    async with engine.begin() as conn:
        tables = ", ".join(f'"{t}"' for t in Base.metadata.tables)
        await conn.exec_driver_sql(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE")
    yield


@pytest_asyncio.fixture
async def client():
    """ASGI test client with no authentication by default."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def user_data():
    """Unique registration payload for a fresh user."""
    return {
        "email": f"user_{os.urandom(4).hex()}@example.com",
        "password": "testpassword123",
        "full_name": "Test User",
    }


@pytest_asyncio.fixture
async def auth_client(client, user_data):
    """Authenticated test client. Registers a user and attaches a bearer token."""
    resp = await client.post(f"{API}/auth/register", json=user_data)
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield client


@pytest_asyncio.fixture
async def second_user_headers(client):
    """Bearer headers for a second user (ownership-isolation tests)."""
    resp = await client.post(
        f"{API}/auth/register",
        json={
            "email": f"other_{os.urandom(4).hex()}@example.com",
            "password": "testpassword123",
        },
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
