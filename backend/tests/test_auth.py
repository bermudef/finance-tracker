"""Auth endpoint tests: register, login, me, refresh, validation."""
from __future__ import annotations

API = "/api/v1"


async def test_register_success(client, user_data):
    resp = await client.post(f"{API}/auth/register", json=user_data)
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"

    me = await client.get(
        f"{API}/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == user_data["email"]


async def test_register_duplicate_email(client, user_data):
    first = await client.post(f"{API}/auth/register", json=user_data)
    assert first.status_code == 201
    second = await client.post(f"{API}/auth/register", json=user_data)
    assert second.status_code == 409
    assert "already registered" in second.json()["detail"].lower()


async def test_register_weak_password_rejected(client, user_data):
    user_data["password"] = "short"
    resp = await client.post(f"{API}/auth/register", json=user_data)
    assert resp.status_code == 422


async def test_register_invalid_email_rejected(client, user_data):
    user_data["email"] = "not-an-email"
    resp = await client.post(f"{API}/auth/register", json=user_data)
    assert resp.status_code == 422


async def test_login_success(client, user_data):
    await client.post(f"{API}/auth/register", json=user_data)
    resp = await client.post(
        f"{API}/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_login_wrong_password(client, user_data):
    await client.post(f"{API}/auth/register", json=user_data)
    resp = await client.post(
        f"{API}/auth/login",
        json={"email": user_data["email"], "password": "wrong-password"},
    )
    assert resp.status_code == 401
    assert "incorrect" in resp.json()["detail"].lower()


async def test_login_unknown_email(client):
    resp = await client.post(
        f"{API}/auth/login",
        json={"email": "nobody@example.com", "password": "whatever123"},
    )
    assert resp.status_code == 401


async def test_me_requires_token(client):
    assert (await client.get(f"{API}/auth/me")).status_code == 401


async def test_me_with_garbage_token(client):
    resp = await client.get(f"{API}/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert resp.status_code == 401


async def test_refresh_rotates_tokens(client, user_data):
    registered = await client.post(f"{API}/auth/register", json=user_data)
    refresh_token = registered.json()["refresh_token"]

    resp = await client.post(f"{API}/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"] != refresh_token  # rotation


async def test_refresh_rejects_access_token(client, user_data):
    registered = await client.post(f"{API}/auth/register", json=user_data)
    access_token = registered.json()["access_token"]

    resp = await client.post(f"{API}/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401
    assert "type" in resp.json()["detail"].lower()


async def test_refresh_rejects_garbage(client):
    resp = await client.post(f"{API}/auth/refresh", json={"refresh_token": "garbage"})
    assert resp.status_code == 401
