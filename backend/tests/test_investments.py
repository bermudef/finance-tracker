"""Investment analytics endpoint tests."""
from __future__ import annotations

API = "/api/v1"


async def test_investment_analytics_requires_auth(client):
    resp = await client.get(f"{API}/investments/analytics")
    assert resp.status_code == 401


async def test_investment_analytics_empty(auth_client):
    resp = await auth_client.get(f"{API}/investments/analytics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["investment_count"] == 0
    assert body["allocation_by_type"] == {}
    assert body["performance"]["total_value"] == 0.0


async def test_investment_analytics_structure(auth_client):
    await auth_client.post(
        f"{API}/investments",
        json={
            "name": "VTSAX",
            "type": "etf",
            "symbol": "VTSAX",
            "cost_basis": 50000,
            "current_value": 75000,
        },
    )
    await auth_client.post(
        f"{API}/investments",
        json={
            "name": "AAPL",
            "type": "stock",
            "symbol": "AAPL",
            "cost_basis": 10000,
            "current_value": 18000,
        },
    )
    resp = await auth_client.get(f"{API}/investments/analytics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["investment_count"] == 2
    assert "allocation_by_type" in body
    assert "performance" in body
    assert "dividends" in body
    assert "allocation_by_sector" in body
    # Performance should show gain
    assert body["performance"]["total_value"] == 93000.0
    assert body["performance"]["gain_loss"] == 33000.0
    # Allocation should sum to ~100%
    total_pct = sum(body["allocation_by_type"].values())
    assert 99.9 <= total_pct <= 100.1


async def test_investment_analytics_dividends(auth_client):
    await auth_client.post(
        f"{API}/investments",
        json={
            "name": "VYM",
            "type": "etf",
            "symbol": "VYM",
            "cost_basis": 20000,
            "current_value": 25000,
        },
    )
    resp = await auth_client.get(f"{API}/investments/analytics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["dividends"]["weighted_yield"] == 0.0
    assert body["dividends"]["total_annual_dividends"] == 0.0
    assert body["has_dividend_data"] is False
