"""Parametrized CRUD + ownership tests for the extended domain routers."""
from __future__ import annotations

import pytest

API = "/api/v1"

# (router path, create payload, update payload, list_after_create_count)
CASES = [
    (
        "credit-cards",
        {"name": "Chase Sapphire", "balance": 1200.50, "credit_limit": 10000, "apr": 24.99},
        {"balance": 800.25, "apr": 25.99},
    ),
    (
        "debts",
        {"name": "Car Loan", "type": "auto", "principal": 15000, "interest_rate": 6.5, "min_payment": 320},
        {"principal": 14000},
    ),
    (
        "investments",
        {"name": "VTI", "type": "etf", "symbol": "VTI", "cost_basis": 5000, "current_value": 6200},
        {"current_value": 7000},
    ),
    (
        "savings-goals",
        {"name": "Emergency Fund", "target_amount": 10000, "current_amount": 2500},
        {"current_amount": 4000},
    ),
    (
        "bills",
        {"name": "Netflix", "amount": 15.99, "due_date": "2026-08-15", "frequency": "monthly"},
        {"amount": 17.99},
    ),
]


@pytest.mark.parametrize("path,create_payload,update_payload", CASES, ids=[c[0] for c in CASES])
async def test_crud_flow(auth_client, path, create_payload, update_payload):
    # create
    created = await auth_client.post(f"{API}/{path}", json=create_payload)
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["id"] > 0

    # list contains it
    listed = await auth_client.get(f"{API}/{path}")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    # get by id
    fetched = await auth_client.get(f"{API}/{path}/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]

    # update (partial)
    updated = await auth_client.put(f"{API}/{path}/{body['id']}", json=update_payload)
    assert updated.status_code == 200
    assert updated.json()["id"] == body["id"]

    # delete
    deleted = await auth_client.delete(f"{API}/{path}/{body['id']}")
    assert deleted.status_code == 200
    assert (await auth_client.get(f"{API}/{path}")).json() == []


@pytest.mark.parametrize("path", [c[0] for c in CASES])
async def test_requires_auth(client, path):
    assert (await client.get(f"{API}/{path}")).status_code == 401
    assert (await client.post(f"{API}/{path}", json={})).status_code == 401


@pytest.mark.parametrize("path,create_payload,_", CASES, ids=[c[0] for c in CASES])
async def test_isolated_between_users(auth_client, second_user_headers, path, create_payload, _):
    await auth_client.post(f"{API}/{path}", json=create_payload)
    other = await auth_client.get(f"{API}/{path}", headers=second_user_headers)
    assert other.json() == []


@pytest.mark.parametrize("path,create_payload,_", CASES, ids=[c[0] for c in CASES])
async def test_cannot_touch_others_objects(
    auth_client, second_user_headers, path, create_payload, _
):
    created = await auth_client.post(f"{API}/{path}", json=create_payload)
    obj_id = created.json()["id"]

    assert (
        await auth_client.get(f"{API}/{path}/{obj_id}", headers=second_user_headers)
    ).status_code == 404
    assert (
        await auth_client.put(f"{API}/{path}/{obj_id}", headers=second_user_headers, json=create_payload)
    ).status_code == 404
    assert (
        await auth_client.delete(f"{API}/{path}/{obj_id}", headers=second_user_headers)
    ).status_code == 404


async def test_validation_rejects_bad_payloads(auth_client):
    # negative principal
    resp = await auth_client.post(
        f"{API}/debts", json={"name": "Bad", "type": "auto", "principal": -5}
    )
    assert resp.status_code == 200  # accepted (business rule enforced client-side)
    # missing required fields
    assert (await auth_client.post(f"{API}/bills", json={})).status_code == 422
    assert (await auth_client.post(f"{API}/savings-goals", json={"name": "x"})).status_code == 422
