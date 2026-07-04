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


@pytest.mark.asyncio
async def test_anonymous_token_reuse(client, mock_llm, mock_messaging):
    """Second game returns the same token when the stored token is provided."""
    with (
        patch("app.routes.game.get_llm", return_value=mock_llm),
        patch("app.routes.game.get_messaging", return_value=mock_messaging),
    ):
        r1 = await client.post(
            "/api/game/start",
            json={
                "players": [{"name": "Marco", "id": "", "telegram_id": None, "token": ""}],
                "mode": "clasico",
            },
        )
    assert r1.status_code == 200
    token = next(p["token"] for p in r1.json()["players"] if p["name"] == "Marco")
    assert token != ""

    with (
        patch("app.routes.game.get_llm", return_value=mock_llm),
        patch("app.routes.game.get_messaging", return_value=mock_messaging),
    ):
        r2 = await client.post(
            "/api/game/start",
            json={
                "players": [{"name": "Marco", "id": "", "telegram_id": None, "token": token}],
                "mode": "caos",
            },
        )
    assert r2.status_code == 200
    token2 = next(p["token"] for p in r2.json()["players"] if p["name"] == "Marco")
    assert token2 == token  # same token returned


@pytest.mark.asyncio
async def test_stale_token_creates_fresh(client, mock_llm, mock_messaging):
    """When a provided token doesn't exist in DB, a new player + token is created."""
    with (
        patch("app.routes.game.get_llm", return_value=mock_llm),
        patch("app.routes.game.get_messaging", return_value=mock_messaging),
    ):
        r = await client.post(
            "/api/game/start",
            json={
                "players": [
                    {"name": "Ghost", "id": "", "telegram_id": None, "token": "stale-tok-xyz"}
                ],
                "mode": "clasico",
            },
        )
    assert r.status_code == 200
    ghost = next(p for p in r.json()["players"] if p["name"] == "Ghost")
    assert ghost["token"] != "stale-tok-xyz"
    assert ghost["token"] != ""


def test_new_mode_enum_values():
    from app.models import Mode
    assert Mode.infiltrados.value == "infiltrados"
    assert Mode.aleatorio.value == "aleatorio"
    assert Mode.sin_impostores.value == "sin_impostores"
    assert Mode.todos_impostores.value == "todos_impostores"


@pytest.mark.asyncio
async def test_assign_roles_infiltrados(mock_llm):
    from app.game.roles import assign_roles
    from app.models import Difficulty, Mode, Player
    players = [
        Player(name="A"), Player(name="B"), Player(name="C"),
        Player(name="D"), Player(name="E"),
    ]
    result = await assign_roles(
        players=players, mode=Mode.infiltrados,
        category="animal", word="perro",
        difficulty=Difficulty.dificil.value, llm=mock_llm,
    )
    impostors = [r for r in result if r.is_impostor]
    assert len(impostors) == 2
    # each impostor gets mirror word (mock returns "gato")
    for r in impostors:
        assert r.word == "gato"
    # no accomplice info (infiltrados are solo, not allied)
    for r in impostors:
        assert r.accomplice is None


@pytest.mark.asyncio
async def test_assign_roles_sin_impostores(mock_llm):
    from app.game.roles import assign_roles
    from app.models import Difficulty, Mode, Player
    players = [Player(name="A"), Player(name="B"), Player(name="C")]
    result = await assign_roles(
        players=players, mode=Mode.sin_impostores,
        category="animal", word="perro",
        difficulty=Difficulty.dificil.value, llm=mock_llm,
    )
    assert all(not r.is_impostor for r in result)
    assert all(r.word == "perro" for r in result)


@pytest.mark.asyncio
async def test_assign_roles_todos_impostores(mock_llm):
    from app.game.roles import assign_roles
    from app.models import Difficulty, Mode, Player
    players = [Player(name="A"), Player(name="B"), Player(name="C")]
    result = await assign_roles(
        players=players, mode=Mode.todos_impostores,
        category="animal", word="perro",
        difficulty=Difficulty.dificil.value, llm=mock_llm,
    )
    assert all(r.is_impostor for r in result)
    # word is empty — not revealed
    assert all(r.word == "" for r in result)
    # each gets their own hint (mock returns "fiel")
    assert all(r.hint == "fiel" for r in result)


def test_start_game_request_new_fields():
    from app.models import StartGameRequest
    req = StartGameRequest(
        players=[],
        show_category_to_impostor=False,
        show_impostor_count=False,
    )
    assert req.show_category_to_impostor is False
    assert req.show_impostor_count is False
    # defaults
    req2 = StartGameRequest(players=[])
    assert req2.show_category_to_impostor is True
    assert req2.show_impostor_count is True


@pytest.mark.asyncio
async def test_infiltrados_integration(client, mock_llm, mock_messaging):
    """infiltrados: 2 impostors with mirror words, no accomplice info."""
    with (
        patch("app.routes.game.get_llm", return_value=mock_llm),
        patch("app.routes.game.get_messaging", return_value=mock_messaging),
    ):
        r = await client.post(
            "/api/game/start",
            json={
                "players": [
                    {"name": "A", "id": "", "telegram_id": None, "token": ""},
                    {"name": "B", "id": "", "telegram_id": None, "token": ""},
                    {"name": "C", "id": "", "telegram_id": None, "token": ""},
                    {"name": "D", "id": "", "telegram_id": None, "token": ""},
                    {"name": "E", "id": "", "telegram_id": None, "token": ""},
                ],
                "mode": "infiltrados",
            },
        )
    assert r.status_code == 200
    data = r.json()
    assert data["n_impostors"] == 2
    assert data["mode"] == "infiltrados"


@pytest.mark.asyncio
async def test_aliados_guard(client, mock_llm, mock_messaging):
    """aliados with 3 players → 400."""
    with (
        patch("app.routes.game.get_llm", return_value=mock_llm),
        patch("app.routes.game.get_messaging", return_value=mock_messaging),
    ):
        r = await client.post(
            "/api/game/start",
            json={
                "players": [
                    {"name": "A", "id": "", "telegram_id": None, "token": ""},
                    {"name": "B", "id": "", "telegram_id": None, "token": ""},
                    {"name": "C", "id": "", "telegram_id": None, "token": ""},
                ],
                "mode": "aliados",
            },
        )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_infiltrados_guard(client, mock_llm, mock_messaging):
    """infiltrados with 4 players → 400."""
    with (
        patch("app.routes.game.get_llm", return_value=mock_llm),
        patch("app.routes.game.get_messaging", return_value=mock_messaging),
    ):
        r = await client.post(
            "/api/game/start",
            json={
                "players": [
                    {"name": "A", "id": "", "telegram_id": None, "token": ""},
                    {"name": "B", "id": "", "telegram_id": None, "token": ""},
                    {"name": "C", "id": "", "telegram_id": None, "token": ""},
                    {"name": "D", "id": "", "telegram_id": None, "token": ""},
                ],
                "mode": "infiltrados",
            },
        )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_internal_mode_blocked(client, mock_llm, mock_messaging):
    """sin_impostores and todos_impostores cannot be selected directly."""
    with (
        patch("app.routes.game.get_llm", return_value=mock_llm),
        patch("app.routes.game.get_messaging", return_value=mock_messaging),
    ):
        for internal_mode in ("sin_impostores", "todos_impostores"):
            r = await client.post(
                "/api/game/start",
                json={
                    "players": [
                        {"name": "A", "id": "", "telegram_id": None, "token": ""},
                        {"name": "B", "id": "", "telegram_id": None, "token": ""},
                        {"name": "C", "id": "", "telegram_id": None, "token": ""},
                    ],
                    "mode": internal_mode,
                },
            )
            assert r.status_code == 400, f"{internal_mode} should be blocked"


@pytest.mark.asyncio
async def test_aleatorio_resolves(client, mock_llm, mock_messaging):
    """aleatorio mode returns a resolved mode (not 'aleatorio') in the response."""
    with (
        patch("app.routes.game.get_llm", return_value=mock_llm),
        patch("app.routes.game.get_messaging", return_value=mock_messaging),
    ):
        r = await client.post(
            "/api/game/start",
            json={
                "players": [
                    {"name": "A", "id": "", "telegram_id": None, "token": ""},
                    {"name": "B", "id": "", "telegram_id": None, "token": ""},
                    {"name": "C", "id": "", "telegram_id": None, "token": ""},
                ],
                "mode": "aleatorio",
            },
        )
    assert r.status_code == 200
    assert r.json()["mode"] != "aleatorio"


@pytest.mark.asyncio
async def test_show_category_false(client, mock_llm, mock_messaging):
    """show_category_to_impostor=False: game starts successfully."""
    with (
        patch("app.routes.game.get_llm", return_value=mock_llm),
        patch("app.routes.game.get_messaging", return_value=mock_messaging),
    ):
        r = await client.post(
            "/api/game/start",
            json={
                "players": [
                    {"name": "A", "id": "", "telegram_id": None, "token": ""},
                    {"name": "B", "id": "", "telegram_id": None, "token": ""},
                    {"name": "C", "id": "", "telegram_id": None, "token": ""},
                ],
                "mode": "clasico",
                "show_category_to_impostor": False,
            },
        )
    assert r.status_code == 200
