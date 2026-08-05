from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.models_db import GamePlayerResult, GameSession, Player, User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_user(db, *, google_id="gid-analytics", email="a@test.com", name="Host"):
    user = User(google_id=google_id, email=email, name=name)
    db.add(user)
    await db.flush()
    return user


async def _make_player(db, user_id, *, name="Alice", token="tok-analytics"):
    player = Player(user_id=user_id, name=name, token=token)
    db.add(player)
    await db.flush()
    return player


async def _make_session(db, *, category, mode, difficulty="dificil", n_impostors=1, created_at):
    session = GameSession(
        category=category,
        mode=mode,
        difficulty=difficulty,
        n_impostors=n_impostors,
        created_at=created_at,
    )
    db.add(session)
    await db.flush()
    return session


async def _make_result(db, session_id, player_id, *, player_name, is_impostor, word=""):
    result = GamePlayerResult(
        session_id=session_id,
        player_id=player_id,
        player_name=player_name,
        is_impostor=is_impostor,
        category_shown=word,
    )
    db.add(result)
    await db.flush()
    return result


# ---------------------------------------------------------------------------
# Auth gating
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_daily_requires_auth(client):
    resp = await client.get("/api/analytics/daily")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sessions_requires_auth(client):
    resp = await client.get("/api/analytics/sessions")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# /api/analytics/daily
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_daily_groups_by_day_with_mode_category_breakdown(auth_client, db_session):
    user = await _make_user(db_session)
    alice = await _make_player(db_session, user.id, name="Alice", token="tok-alice")
    bob = await _make_player(db_session, user.id, name="Bob", token="tok-bob")

    today = datetime.utcnow()
    yesterday = today - timedelta(days=1)

    s1 = await _make_session(db_session, category="animal", mode="clasico", created_at=today)
    await _make_result(
        db_session, s1.id, alice.id, player_name="Alice", is_impostor=False, word="León"
    )
    await _make_result(db_session, s1.id, bob.id, player_name="Bob", is_impostor=True)

    s2 = await _make_session(db_session, category="país", mode="caos", created_at=today)
    await _make_result(
        db_session, s2.id, alice.id, player_name="Alice", is_impostor=False, word="Chile"
    )

    s3 = await _make_session(db_session, category="animal", mode="clasico", created_at=yesterday)
    await _make_result(
        db_session, s3.id, bob.id, player_name="Bob", is_impostor=False, word="Tigre"
    )

    await db_session.commit()

    resp = await auth_client.get("/api/analytics/daily", params={"days": 30})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    by_date = {d["date"]: d for d in data}
    today_key = today.date().isoformat()
    yesterday_key = yesterday.date().isoformat()

    assert by_date[today_key]["sessions"] == 2
    assert by_date[today_key]["unique_players"] == 2  # alice + bob, deduped across s1/s2
    assert by_date[today_key]["by_mode"] == {"clasico": 1, "caos": 1}
    assert by_date[today_key]["by_category"] == {"animal": 1, "país": 1}

    assert by_date[yesterday_key]["sessions"] == 1
    assert by_date[yesterday_key]["unique_players"] == 1
    assert by_date[yesterday_key]["by_mode"] == {"clasico": 1}


@pytest.mark.asyncio
async def test_daily_respects_days_window(auth_client, db_session):
    user = await _make_user(db_session)
    alice = await _make_player(db_session, user.id, name="Alice", token="tok-old")

    old = datetime.utcnow() - timedelta(days=90)
    s = await _make_session(db_session, category="fruta", mode="clasico", created_at=old)
    await _make_result(
        db_session, s.id, alice.id, player_name="Alice", is_impostor=False, word="Mango"
    )
    await db_session.commit()

    resp = await auth_client.get("/api/analytics/daily", params={"days": 7})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_daily_empty_when_no_sessions(auth_client):
    resp = await auth_client.get("/api/analytics/daily")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# /api/analytics/sessions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sessions_orders_newest_first_and_shows_words(auth_client, db_session):
    user = await _make_user(db_session)
    alice = await _make_player(db_session, user.id, name="Alice", token="tok-a2")
    bob = await _make_player(db_session, user.id, name="Bob", token="tok-b2")

    older = datetime.utcnow() - timedelta(hours=2)
    newer = datetime.utcnow()

    s_old = await _make_session(db_session, category="fruta", mode="clasico", created_at=older)
    await _make_result(
        db_session, s_old.id, alice.id, player_name="Alice", is_impostor=False, word="Mango"
    )

    s_new = await _make_session(
        db_session, category="animal", mode="caos", n_impostors=1, created_at=newer
    )
    await _make_result(
        db_session, s_new.id, alice.id, player_name="Alice", is_impostor=False, word="León"
    )
    await _make_result(db_session, s_new.id, bob.id, player_name="Bob", is_impostor=True, word="")

    await db_session.commit()

    resp = await auth_client.get("/api/analytics/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    assert data[0]["id"] == s_new.id
    assert data[0]["category"] == "animal"
    players_by_name = {p["player_name"]: p for p in data[0]["players"]}
    assert players_by_name["Alice"]["word_shown"] == "León"
    assert players_by_name["Alice"]["is_impostor"] is False
    assert players_by_name["Bob"]["is_impostor"] is True
    assert players_by_name["Bob"]["word_shown"] == ""

    assert data[1]["id"] == s_old.id


@pytest.mark.asyncio
async def test_sessions_pagination(auth_client, db_session):
    user = await _make_user(db_session)
    alice = await _make_player(db_session, user.id, name="Alice", token="tok-page")

    base = datetime.utcnow()
    for i in range(5):
        s = await _make_session(
            db_session, category="país", mode="clasico", created_at=base - timedelta(minutes=i)
        )
        await _make_result(
            db_session, s.id, alice.id, player_name="Alice", is_impostor=False, word="Chile"
        )
    await db_session.commit()

    resp = await auth_client.get("/api/analytics/sessions", params={"limit": 2, "offset": 0})
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp2 = await auth_client.get("/api/analytics/sessions", params={"limit": 2, "offset": 4})
    assert resp2.status_code == 200
    assert len(resp2.json()) == 1


# ---------------------------------------------------------------------------
# End-to-end: a real round played via /api/game/start shows up in both views
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_real_round_appears_in_analytics(auth_client, mock_llm, mock_messaging):
    players = [
        {"name": "Marco", "telegram_id": 111},
        {"name": "Ana", "telegram_id": 222},
    ]
    with (
        patch("app.routes.game.get_llm", return_value=mock_llm),
        patch("app.routes.game.get_messaging", return_value=mock_messaging),
    ):
        start_resp = await auth_client.post(
            "/api/game/start", json={"players": players, "mode": "clasico"}
        )
    assert start_resp.status_code == 200
    session_id = start_resp.json()["session_id"]

    daily_resp = await auth_client.get("/api/analytics/daily")
    assert daily_resp.status_code == 200
    daily = daily_resp.json()
    assert len(daily) == 1
    assert daily[0]["sessions"] == 1
    assert daily[0]["unique_players"] == 2

    sessions_resp = await auth_client.get("/api/analytics/sessions")
    assert sessions_resp.status_code == 200
    sessions = sessions_resp.json()
    assert len(sessions) == 1
    assert sessions[0]["id"] == session_id
    assert len(sessions[0]["players"]) == 2
