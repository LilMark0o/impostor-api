import pytest

from app.auth import create_access_token
from app.db import _new_uuid
from app.models_db import User


@pytest.fixture
async def auth_user(db_session):
    user = User(id=_new_uuid(), google_id="g-test", email="t@t.com", name="Tester")
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
def auth_headers(auth_user):
    token = create_access_token(auth_user.id)
    return {"Authorization": f"Bearer {token}"}


async def test_list_players_empty(client, auth_user, auth_headers):
    resp = await client.get("/users/players", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_player(client, auth_user, auth_headers):
    resp = await client.post(
        "/users/players",
        json={"name": "Marco", "telegram_id": 123456},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Marco"
    assert data["telegram_id"] == 123456
    assert "id" in data


async def test_delete_player(client, auth_user, auth_headers):
    create_resp = await client.post(
        "/users/players",
        json={"name": "Pipe", "telegram_id": 999},
        headers=auth_headers,
    )
    player_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/users/players/{player_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    list_resp = await client.get("/users/players", headers=auth_headers)
    assert list_resp.json() == []


async def test_delete_other_users_player_returns_404(client, db_session, auth_user, auth_headers):
    other = User(id=_new_uuid(), google_id="g-other", email="o@o.com", name="Other")
    db_session.add(other)
    await db_session.commit()

    other_token = create_access_token(other.id)
    create_resp = await client.post(
        "/users/players",
        json={"name": "X", "telegram_id": 1},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    player_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/users/players/{player_id}", headers=auth_headers)
    assert del_resp.status_code == 404


async def test_players_requires_auth(client):
    resp = await client.get("/users/players")
    assert resp.status_code == 401
