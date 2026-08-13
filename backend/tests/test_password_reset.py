"""Password reset flow tests: token issuance, validation, single-use, expiry."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select

API = "/api/v1"


async def test_forgot_password_for_unknown_email_still_200(client):
    resp = await client.post(
        f"{API}/auth/forgot-password", json={"email": "nobody@example.com"}
    )
    assert resp.status_code == 200
    assert resp.json().get("reset_token") is None  # unknown email -> no token


async def test_full_reset_flow(client, user_data):
    await client.post(f"{API}/auth/register", json=user_data)

    forgot = await client.post(
        f"{API}/auth/forgot-password", json={"email": user_data["email"]}
    )
    assert forgot.status_code == 200
    reset_token = forgot.json()["reset_token"]
    assert reset_token

    reset = await client.post(
        f"{API}/auth/reset-password",
        json={"token": reset_token, "new_password": "brandnewpassword1"},
    )
    assert reset.status_code == 200

    # Old password no longer works; new one does.
    old_login = await client.post(
        f"{API}/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        f"{API}/auth/login",
        json={"email": user_data["email"], "password": "brandnewpassword1"},
    )
    assert new_login.status_code == 200


async def test_reset_token_is_single_use(client, user_data):
    await client.post(f"{API}/auth/register", json=user_data)
    forgot = await client.post(
        f"{API}/auth/forgot-password", json={"email": user_data["email"]}
    )
    token = forgot.json()["reset_token"]

    first = await client.post(
        f"{API}/auth/reset-password", json={"token": token, "new_password": "brandnewpassword1"}
    )
    assert first.status_code == 200

    second = await client.post(
        f"{API}/auth/reset-password", json={"token": token, "new_password": "anotherpassword2"}
    )
    assert second.status_code == 400
    assert "already-used" in second.json()["detail"]


async def test_reset_token_rejects_garbage(client):
    resp = await client.post(
        f"{API}/auth/reset-password", json={"token": "garbage", "new_password": "whatever123"}
    )
    assert resp.status_code == 400


async def test_reset_requires_min_password_length(client, user_data):
    await client.post(f"{API}/auth/register", json=user_data)
    forgot = await client.post(
        f"{API}/auth/forgot-password", json={"email": user_data["email"]}
    )
    resp = await client.post(
        f"{API}/auth/reset-password",
        json={"token": forgot.json()["reset_token"], "new_password": "short"},
    )
    assert resp.status_code == 422


async def test_expired_token_rejected(client, user_data, monkeypatch):
    """Expired tokens must be rejected (simulate by back-dating expiry)."""
    from app.models.database import async_session
    from app.models.password_reset import PasswordResetToken

    await client.post(f"{API}/auth/register", json=user_data)
    forgot = await client.post(
        f"{API}/auth/forgot-password", json={"email": user_data["email"]}
    )
    token = forgot.json()["reset_token"]

    async with async_session() as db:
        result = await db.execute(select(PasswordResetToken))
        row = result.scalar_one()
        row.expires_at = datetime.utcnow() - timedelta(minutes=1)
        await db.commit()

    resp = await client.post(
        f"{API}/auth/reset-password", json={"token": token, "new_password": "whatever123"}
    )
    assert resp.status_code == 400
    assert "expired" in resp.json()["detail"]


async def test_new_forgot_request_invalidates_previous_token(client, user_data):
    await client.post(f"{API}/auth/register", json=user_data)
    first = await client.post(
        f"{API}/auth/forgot-password", json={"email": user_data["email"]}
    )
    second = await client.post(
        f"{API}/auth/forgot-password", json={"email": user_data["email"]}
    )

    old_resp = await client.post(
        f"{API}/auth/reset-password",
        json={"token": first.json()["reset_token"], "new_password": "brandnewpassword1"},
    )
    assert old_resp.status_code == 400

    new_resp = await client.post(
        f"{API}/auth/reset-password",
        json={"token": second.json()["reset_token"], "new_password": "brandnewpassword1"},
    )
    assert new_resp.status_code == 200
