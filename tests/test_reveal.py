import pytest

from app.models_db import GamePlayerResult, GameSession, Player, User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_user(db, *, google_id="gid-reveal", email="reveal@test.com", name="Host"):
    user = User(google_id=google_id, email=email, name=name)
    db.add(user)
    await db.flush()
    return user


async def _make_player(db, user_id, *, name="Alice", token="test-token-abc"):
    player = Player(user_id=user_id, name=name, token=token)
    db.add(player)
    await db.flush()
    return player


async def _make_session(db, user_id):
    session = GameSession(
        user_id=user_id,
        category="animals",
        mode="clasico",
        difficulty="medium",
        n_impostors=1,
    )
    db.add(session)
    await db.flush()
    return session


async def _make_result(db, session_id, player_id, *, is_impostor=False, category_shown="perro"):
    result = GamePlayerResult(
        session_id=session_id,
        player_id=player_id,
        player_name="Alice",
        is_impostor=is_impostor,
        category_shown=category_shown,
    )
    db.add(result)
    await db.flush()
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reveal_404_unknown_token(client):
    resp = await client.get("/p/no-such-token-xyz")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reveal_waiting_no_results(client, db_session):
    user = await _make_user(db_session)
    await _make_player(db_session, user.id, token="token-waiting-123")
    await db_session.commit()

    resp = await client.get("/p/token-waiting-123")
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "waiting"
    assert data["player_name"] == "Alice"
    assert data["session_id"] is None
    assert data["is_impostor"] is None
    assert data["category"] is None


@pytest.mark.asyncio
async def test_reveal_ready_non_impostor(client, db_session):
    user = await _make_user(db_session, google_id="gid2", email="u2@test.com")
    player = await _make_player(db_session, user.id, token="token-ready-456")
    session = await _make_session(db_session, user.id)
    await _make_result(db_session, session.id, player.id, is_impostor=False, category_shown="perro")
    await db_session.commit()

    resp = await client.get("/p/token-ready-456")
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "ready"
    assert data["player_name"] == "Alice"
    assert data["is_impostor"] is False
    assert data["category"] == "perro"
    assert data["session_id"] is not None


@pytest.mark.asyncio
async def test_reveal_ready_impostor(client, db_session):
    user = await _make_user(db_session, google_id="gid3", email="u3@test.com")
    player = await _make_player(db_session, user.id, token="token-impostor-789")
    session = await _make_session(db_session, user.id)
    await _make_result(
        db_session, session.id, player.id, is_impostor=True, category_shown="perro"
    )
    await db_session.commit()

    resp = await client.get("/p/token-impostor-789")
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "ready"
    assert data["is_impostor"] is True
    assert data["category"] is None  # impostors don't see the category
