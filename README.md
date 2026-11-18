# El Impostor — API

Backend for **El Impostor**, a social deduction party game. Everyone gets the
same word except the impostor, who has to bluff without knowing it.

FastAPI + SQLAlchemy (async). SQLite for local use, Postgres in production.

> **Playable with zero API keys.** The word pools and the curated hints ship
> inside `app/config.py`. LLM keys only unlock custom categories.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

That's it: the SQLite database and its tables are created on first boot.
Interactive docs at <http://localhost:8000/docs>, health check at `/api/health`.

You don't need a `.env` file to run locally. If you want one:

```bash
cp .env.example .env
```

## Configuration

Every variable is optional for local play. Only `JWT_SECRET_KEY` and a real
`DATABASE_URL` matter once you deploy.

| Variable | Required | What it unlocks |
|---|---|---|
| `DATABASE_URL` | No (SQLite default) | Persistence. Postgres: `postgresql+asyncpg://…` |
| `JWT_SECRET_KEY` | **Yes in production** | Signing auth tokens. `openssl rand -hex 32` |
| `OPENAI_API_KEY` | No | Custom category validation, word and hint generation |
| `OPENAI_MODEL` | No | Defaults to `gpt-4.1-mini` |
| `OPENROUTER_API_KEY` | No | Same as above, via OpenRouter |
| `OPENROUTER_MODEL` | No | Defaults to a free Llama 3.3 model |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | No | Google login, saved history |
| `TELEGRAM_TOKEN` | No | Legacy: DMs each player their word |

With both LLM keys set, `OPENAI_API_KEY` wins (`provider="auto"`). With
neither, every LLM call fails soft and the static pools take over — a round
never breaks because a key is missing.

## Content: words and hints

Two dictionaries in `app/config.py` drive the whole game:

- `WORD_POOLS` — `{category: {"f": [...], "d": [...], "b": [...]}}`, where the
  tiers are *fácil*, *difícil* and *brutal*. A round picks from the preferred
  tier and falls back through the others, so a category never runs dry.
- `WORD_HINTS` — `{category: {word: [hint, ...]}}`. One-word nudges the
  impostor can bluff with (`1989 Milan` → `Gullit`). Each hint is a single
  word on purpose: it has to fit on the card at a glance. Adding a second hint
  for the same word lets a round with two impostors give each one a different
  one.

Tests guard the content: hints only for words that exist in a pool, no hint
containing its own word, one word per hint, and every football category using
the `year + winner` form.

To add a category, add it to `WORD_POOLS`, optionally to `WORD_HINTS`, and list
it in `CATEGORY_GROUPS` so it shows up in the app:

```python
WORD_POOLS["mi categoría"] = {"f": ["uno", "dos"], "d": ["tres"], "b": []}
WORD_HINTS["mi categoría"] = {"uno": ["pista sin decir la palabra"]}
CATEGORY_GROUPS["🌍 General"].append("mi categoría")
```

Two tests guard the content: every hint must belong to a real pool word, and
no hint may contain its own word. A third one enforces the one-word rule.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/categories` | Available categories and packs |
| `POST` | `/api/game/start` | Create a round, return words per player |
| `GET` | `/p/{token}` | Reveal one player's card |
| `GET` | `/api/health` | Liveness probe |
| `GET` | `/api/analytics/*` | First-party stats (auth required when a user exists) |

Round creation works anonymously; player ids are generated server-side and
scoped to the session.

## Development

```bash
pytest                    # 60+ tests against in-memory SQLite
ruff check .              # lint
```

### Migrations

SQLite is the zero-setup path: `create_all` builds the schema on boot and no
migration step is needed. Alembic migrations exist for **Postgres**, which is
what you'd run in production:

```bash
DATABASE_URL=postgresql://… alembic upgrade head
```

Note that the older migrations use Postgres-specific `ALTER COLUMN`, so they
don't apply to SQLite. Use a fresh SQLite file instead of migrating one.

## Docker

```bash
docker build -t impostor-api .
docker run -p 8000:8000 -e JWT_SECRET_KEY=dev impostor-api
```

Or use the `docker-compose.yml` in the
[umbrella project](https://github.com/LilMark0o/impostor) to run
this together with the web app.

## License

MIT — see [LICENSE](LICENSE).
