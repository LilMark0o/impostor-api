import pytest
import respx
import httpx
from app.auth import create_access_token


@pytest.fixture
def google_mocks():
    with respx.mock:
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=httpx.Response(200, json={"access_token": "fake-google-token"})
        )
        respx.get("https://www.googleapis.com/oauth2/v2/userinfo").mock(
            return_value=httpx.Response(
                200, json={"id": "g-123", "email": "alice@example.com", "name": "Alice"}
            )
        )
        yield


async def test_google_auth_creates_user(client, google_mocks):
    resp = await client.post(
        "/auth/google",
        json={"code": "fake-code", "redirect_uri": "http://localhost:3000"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "alice@example.com"
    assert data["user"]["lang"] == "es"


async def test_google_auth_bad_code_returns_400(client):
    with respx.mock:
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=httpx.Response(400, json={"error": "invalid_grant"})
        )
        resp = await client.post(
            "/auth/google",
            json={"code": "bad-code", "redirect_uri": "http://localhost:3000"},
        )
    assert resp.status_code == 400


async def test_get_me(client, google_mocks):
    auth_resp = await client.post(
        "/auth/google",
        json={"code": "fake-code", "redirect_uri": "http://localhost:3000"},
    )
    token = auth_resp.json()["access_token"]

    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@example.com"


async def test_get_me_without_token_returns_401(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


async def test_delete_me(client, google_mocks):
    auth_resp = await client.post(
        "/auth/google",
        json={"code": "fake-code", "redirect_uri": "http://localhost:3000"},
    )
    token = auth_resp.json()["access_token"]

    resp = await client.delete("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 204

    me_resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 404
