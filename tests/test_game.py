from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_categories(client):
    resp = await client.get("/api/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert "categories" in data
    assert isinstance(data["categories"], list)
    assert len(data["categories"]) > 0


@pytest.mark.asyncio
async def test_start_game(auth_client, mock_llm, mock_messaging):
    players = [
        {"name": "Marco", "telegram_id": 6823166566},
        {"name": "Ana", "telegram_id": 1234567890},
    ]
    with (
        patch("app.routes.game.get_llm", return_value=mock_llm),
        patch("app.routes.game.get_messaging", return_value=mock_messaging),
    ):
        resp = await auth_client.post(
            "/api/game/start",
            json={"players": players, "mode": "clasico"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["n_impostors"] == 1
    total = len(data["sent"]) + len(data["failed"])
    assert total == 2


@pytest.mark.asyncio
async def test_custom_categories(auth_client, mock_llm, mock_messaging):
    players = [
        {"name": "Marco", "telegram_id": 6823166566},
        {"name": "Ana", "telegram_id": 1234567890},
    ]
    with (
        patch("app.routes.game.get_llm", return_value=mock_llm),
        patch("app.routes.game.get_messaging", return_value=mock_messaging),
    ):
        resp = await auth_client.post(
            "/api/game/start",
            json={
                "players": players,
                "mode": "clasico",
                "categories": ["deportista famoso"],
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] == "deportista famoso"
