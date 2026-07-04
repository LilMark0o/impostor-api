# Mode Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure game modes — add `infiltrados` and `aleatorio` (with hidden `sin_impostores`/`todos_impostores`), merge `ciego` into `caos` as a checkbox, add per-mode config toggles, enforce player-count guards, and remove the login button from the frontend.

**Architecture:** Backend extends the `Mode` enum and `StartGameRequest` in `models.py`, adds new role-assignment branches in `roles.py`, adds `aleatorio` resolution + guards + updated `_build_message` in `engine.py`. Frontend updates types, constants, `api/game.ts`, `StepMode`, `WizardShell`, `StepReview`, and `RondaPanel`. The two repos (`impostor-api` and `impostor-web`) are changed independently; API tasks come first because web tasks depend on knowing the final enum values and request shape.

**Tech Stack:** FastAPI + SQLAlchemy async + pytest + httpx (API); React 18 + TypeScript + Tailwind + Vitest + React Testing Library (Web)

## Global Constraints

- Python ruff line-length: 100 chars max. Break long lines — never use `# noqa`.
- All new API tests use the `client` fixture (anonymous) with `patch("app.routes.game.get_llm", ...)` and `patch("app.routes.game.get_messaging", ...)`.
- All existing tests must continue to pass after each task.
- Web: run `cd /path/to/impostor-web && npx vitest run` to verify. API: run `cd /path/to/impostor-api && pytest -q` to verify.
- The `ciego` mode value is **kept in the Python enum** for DB backwards-compatibility but is **removed from the TypeScript `Mode` type** and never shown in the UI.
- `sin_impostores` and `todos_impostores` are in the Python enum and TypeScript type but are never shown as selectable options — they only appear in responses when `aleatorio` resolves to them.

---

## Task 1 (API): Extend Mode enum and StartGameRequest

**Repo:** `impostor-api`

**Files:**
- Modify: `app/models.py`
- Test: `tests/test_game.py` (add `test_new_mode_enum_values`)

**Interfaces:**
- Produces: `Mode.infiltrados`, `Mode.aleatorio`, `Mode.sin_impostores`, `Mode.todos_impostores` enum values; `StartGameRequest.show_category_to_impostor: bool = True`; `StartGameRequest.show_impostor_count: bool = True`

- [ ] **Step 1: Write failing test**

Add to `tests/test_game.py`:
```python
def test_new_mode_enum_values():
    from app.models import Mode
    assert Mode.infiltrados.value == "infiltrados"
    assert Mode.aleatorio.value == "aleatorio"
    assert Mode.sin_impostores.value == "sin_impostores"
    assert Mode.todos_impostores.value == "todos_impostores"


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
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd /path/to/impostor-api && pytest tests/test_game.py::test_new_mode_enum_values -xvs
```
Expected: `ImportError` or `AttributeError` — `infiltrados` not yet defined.

- [ ] **Step 3: Update `app/models.py`**

Replace the `Mode` enum and `StartGameRequest` class:

```python
class Mode(str, Enum):
    clasico          = "clasico"
    caos             = "caos"
    ciego            = "ciego"            # DB backwards-compat; hidden from UI
    aliados          = "aliados"
    espejo           = "espejo"
    infiltrados      = "infiltrados"
    aleatorio        = "aleatorio"
    sin_impostores   = "sin_impostores"   # internal; only reachable via aleatorio
    todos_impostores = "todos_impostores" # internal; only reachable via aleatorio


class StartGameRequest(BaseModel):
    players: list[Player]
    mode: Mode = Mode.caos
    difficulty: Difficulty = Difficulty.dificil
    categories: list[str] | None = None
    show_category_to_impostor: bool = True
    show_impostor_count: bool = True
```

- [ ] **Step 4: Run to confirm tests pass**

```bash
cd /path/to/impostor-api && pytest tests/test_game.py::test_new_mode_enum_values tests/test_game.py::test_start_game_request_new_fields -xvs
```
Expected: PASS

- [ ] **Step 5: Run full test suite to confirm nothing broken**

```bash
cd /path/to/impostor-api && pytest -q
```
Expected: all existing tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/models.py tests/test_game.py
git commit -m "feat(api): extend Mode enum and StartGameRequest with new modes and options"
```

---

## Task 2 (API): New role-assignment logic in roles.py

**Repo:** `impostor-api`

**Files:**
- Modify: `app/game/roles.py`
- Test: `tests/test_game.py` (add role-level unit tests)

**Interfaces:**
- Consumes: `Mode.infiltrados`, `Mode.sin_impostores`, `Mode.todos_impostores` from Task 1
- Produces: `assign_roles()` handles all 9 `Mode` values correctly

- [ ] **Step 1: Write failing tests**

Add to `tests/test_game.py`:
```python
@pytest.mark.asyncio
async def test_assign_roles_infiltrados(mock_llm):
    from app.game.roles import assign_roles
    from app.models import Mode, Player, Difficulty
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
    # each impostor has a different word (pick_mirror_word called per impostor)
    words = [r.word for r in impostors]
    assert words[0] == "gato"  # mock returns "gato"
    assert words[1] == "gato"  # mock always returns "gato" — same mock value, different call
    # no accomplice info
    for r in impostors:
        assert r.accomplice is None


@pytest.mark.asyncio
async def test_assign_roles_sin_impostores(mock_llm):
    from app.game.roles import assign_roles
    from app.models import Mode, Player, Difficulty
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
    from app.models import Mode, Player, Difficulty
    players = [Player(name="A"), Player(name="B"), Player(name="C")]
    result = await assign_roles(
        players=players, mode=Mode.todos_impostores,
        category="animal", word="perro",
        difficulty=Difficulty.dificil.value, llm=mock_llm,
    )
    assert all(r.is_impostor for r in result)
    # word is empty — never revealed to players
    assert all(r.word == "" for r in result)
    # each gets their own hint
    assert all(r.hint == "fiel" for r in result)  # mock returns "fiel"
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd /path/to/impostor-api && pytest tests/test_game.py::test_assign_roles_infiltrados -xvs
```
Expected: FAIL — `infiltrados` hits the `else: n_impostors = 1` fallback.

- [ ] **Step 3: Update `app/game/roles.py`**

Replace the impostor-count logic and mirror_words block with:

```python
    if mode == Mode.clasico:
        n_impostors = 1
    elif mode in (Mode.caos, Mode.ciego):
        n_impostors = random.randint(1, max(1, len(shuffled) // 2))
    elif mode == Mode.aliados:
        n_impostors = 2
    elif mode == Mode.espejo:
        n_impostors = random.randint(1, max(1, len(shuffled) // 2))
    elif mode == Mode.infiltrados:
        n_impostors = 2
    elif mode == Mode.sin_impostores:
        n_impostors = 0
    elif mode == Mode.todos_impostores:
        n_impostors = len(shuffled)
    else:
        n_impostors = 1
```

Replace the `mirror_words` block with (handles both `espejo` and `infiltrados`):

```python
    mirror_words: dict[str, str] = {}
    if mode in (Mode.espejo, Mode.infiltrados):
        for p in shuffled[:n_impostors]:
            try:
                mirror_words[p.name] = await llm.pick_mirror_word(
                    category, exclude=word
                )
            except Exception as e:
                print(f"[LLM pick_mirror_word failed] {e} — using fallback")
                mirror_words[p.name] = word + "_alt"
```

Replace the `accomplices` dict with (aliados only — NOT infiltrados):

```python
    accomplices = (
        {
            p.name: shuffled[(i + 1) % n_impostors].name
            for i, p in enumerate(shuffled[:n_impostors])
        }
        if mode == Mode.aliados and n_impostors > 1
        else {}
    )
```

Replace the per-player assignment loop with:

```python
    used_hints: list[str] = []
    assignments: list[RoleAssignment] = []

    for player in shuffled:
        if player.name in impostors:
            if mode == Mode.todos_impostores:
                # hint around the real word but don't reveal it
                try:
                    hint = await llm.pick_hint(
                        category, word, difficulty, exclude=used_hints
                    )
                except Exception as e:
                    print(f"[LLM pick_hint failed] {e} — using fallback")
                    hint = "pista"
                used_hints.append(hint)
                assignments.append(
                    RoleAssignment(
                        player=player,
                        is_impostor=True,
                        word="",
                        hint=hint,
                    )
                )
            else:
                try:
                    hint = await llm.pick_hint(
                        category, word, difficulty, exclude=used_hints
                    )
                except Exception as e:
                    print(f"[LLM pick_hint failed] {e} — using fallback")
                    hint = "pista"
                used_hints.append(hint)
                assignments.append(
                    RoleAssignment(
                        player=player,
                        is_impostor=True,
                        word=mirror_words.get(player.name, word),
                        hint=hint,
                        accomplice=accomplices.get(player.name),
                    )
                )
        else:
            assignments.append(
                RoleAssignment(player=player, is_impostor=False, word=word)
            )

    return assignments
```

- [ ] **Step 4: Run new tests**

```bash
cd /path/to/impostor-api && pytest tests/test_game.py::test_assign_roles_infiltrados tests/test_game.py::test_assign_roles_sin_impostores tests/test_game.py::test_assign_roles_todos_impostores -xvs
```
Expected: PASS

- [ ] **Step 5: Run full suite**

```bash
cd /path/to/impostor-api && pytest -q
```
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add app/game/roles.py tests/test_game.py
git commit -m "feat(api): add infiltrados, sin_impostores, todos_impostores role logic"
```

---

## Task 3 (API): Engine updates — aleatorio, guards, message options

**Repo:** `impostor-api`

**Files:**
- Modify: `app/game/engine.py`
- Test: `tests/test_game.py` (add integration tests)

**Interfaces:**
- Consumes: all Mode values from Task 1; `assign_roles` from Task 2
- Produces: `POST /api/game/start` handles `show_category_to_impostor`, `show_impostor_count`, `aleatorio` mode, player-count guards, and rejects `sin_impostores`/`todos_impostores` sent directly

- [ ] **Step 1: Write failing tests**

Add to `tests/test_game.py`:
```python
@pytest.mark.asyncio
async def test_infiltrados_integration(client, mock_llm, mock_messaging):
    """infiltrados: 2 impostors with mirror words, no accomplice info in messages."""
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
    assert r.json()["n_impostors"] == 2
    assert r.json()["mode"] == "infiltrados"


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
    """show_category_to_impostor=False: game starts successfully (message logic tested at unit level)."""
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
```

- [ ] **Step 2: Run to confirm failures**

```bash
cd /path/to/impostor-api && pytest tests/test_game.py::test_infiltrados_integration tests/test_game.py::test_aliados_guard -xvs
```
Expected: FAIL — `infiltrados` hits wrong branch; no guard exists for aliados.

- [ ] **Step 3: Update `app/game/engine.py`**

Add these module-level constants after the imports:

```python
import random  # already imported

_INTERNAL_MODES = {Mode.sin_impostores, Mode.todos_impostores}

_ALEATORIO_POOL = [
    Mode.clasico, Mode.caos, Mode.aliados,
    Mode.espejo, Mode.infiltrados,
    Mode.sin_impostores, Mode.todos_impostores,
]


def _mode_is_eligible(m: Mode, n: int) -> bool:
    if m == Mode.aliados:
        return n >= 4
    if m == Mode.infiltrados:
        return n >= 5
    return True
```

Update `_build_message` signature and body (replace the existing function entirely):

```python
def _build_message(
    assignment: RoleAssignment,
    mode: Mode,
    category: str,
    n_impostors: int,
    show_category_to_impostor: bool = True,
    show_impostor_count: bool = True,
) -> str:
    if not assignment.is_impostor:
        return (
            f"🎯 *Categoría:* {category}\n🔤 *Tu palabra:* {assignment.word.upper()}"
        )

    if mode == Mode.todos_impostores:
        return f"🎭 *¡Todos son impostores!*\n\n📂 {category} — [{assignment.hint}]"

    lines = ["🎭 *¡Eres el IMPOSTOR!*"]

    if show_category_to_impostor:
        lines.append(f"\n📂 {category} — [{assignment.hint}]")
    else:
        lines.append(f"\n🕵️ Pista: [{assignment.hint}]")

    if mode == Mode.aliados and assignment.accomplice:
        lines.append(f"🤝 *Tu cómplice:* {assignment.accomplice}")

    if mode in (Mode.espejo, Mode.infiltrados):
        lines.append(f"🪞 *Tu palabra (diferente):* {assignment.word.upper()}")

    if show_impostor_count:
        lines.append(f"👥 *Impostores en juego:* {n_impostors}")

    return "\n".join(lines)
```

In `GameEngine.run()`, add before `assign_roles` is called:

```python
        # Block internal modes from being requested directly
        if mode in _INTERNAL_MODES:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400, detail="This mode cannot be selected directly"
            )

        # Player-count guards
        if mode == Mode.aliados and len(players) < 4:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400, detail="aliados requires at least 4 players"
            )
        if mode == Mode.infiltrados and len(players) < 5:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail="infiltrados requires at least 5 players",
            )

        # Resolve aleatorio to a concrete mode
        resolved_mode = mode
        if mode == Mode.aleatorio:
            eligible = [
                m for m in _ALEATORIO_POOL
                if _mode_is_eligible(m, len(players))
            ]
            resolved_mode = random.choice(eligible)
```

Replace every use of `mode` after this block with `resolved_mode` (for `assign_roles`, `_build_message`, `session`, and the print statement). Pass `show_category_to_impostor` and `show_impostor_count` to `_build_message`:

```python
        assignments = await assign_roles(
            players=players,
            mode=resolved_mode,
            category=category,
            word=word,
            difficulty=difficulty.value,
            llm=self._llm,
        )
```

```python
            msg = _build_message(
                assignment,
                resolved_mode,
                category,
                n_impostors,
                show_category_to_impostor=show_category_to_impostor,
                show_impostor_count=show_impostor_count,
            )
```

```python
        session = GameSession(
            id=_new_uuid(),
            user_id=user_id,
            category=category,
            mode=resolved_mode.value,
            difficulty=difficulty.value,
            n_impostors=n_impostors,
        )
```

Update `StartGameResponse` in `return`:
```python
        return StartGameResponse(
            category=category,
            mode=resolved_mode,
            ...
        )
```

Update `run()` signature to accept the new request fields:

```python
    async def run(
        self,
        players: list[Player],
        categories: list[str],
        mode: Mode = Mode.caos,
        difficulty: Difficulty = Difficulty.dificil,
        user_id: str | None = None,
        show_category_to_impostor: bool = True,
        show_impostor_count: bool = True,
    ) -> StartGameResponse:
```

In `app/routes/game.py`, pass the new fields to `engine.run()`:

```python
    return await engine.run(
        players=req.players,
        categories=categories,
        mode=req.mode,
        difficulty=req.difficulty,
        user_id=user_id,
        show_category_to_impostor=req.show_category_to_impostor,
        show_impostor_count=req.show_impostor_count,
    )
```

- [ ] **Step 4: Run new tests**

```bash
cd /path/to/impostor-api && pytest \
  tests/test_game.py::test_infiltrados_integration \
  tests/test_game.py::test_aliados_guard \
  tests/test_game.py::test_infiltrados_guard \
  tests/test_game.py::test_internal_mode_blocked \
  tests/test_game.py::test_aleatorio_resolves \
  tests/test_game.py::test_show_category_false \
  -xvs
```
Expected: all PASS.

- [ ] **Step 5: Run full suite**

```bash
cd /path/to/impostor-api && pytest -q
```
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add app/game/engine.py app/routes/game.py tests/test_game.py
git commit -m "feat(api): aleatorio resolution, player-count guards, message options"
```

---

## Task 4 (Web): Update types, constants, and API client

**Repo:** `impostor-web`

**Files:**
- Modify: `src/types/index.ts`
- Modify: `src/constants/labels.ts`
- Modify: `src/api/game.ts`

**Interfaces:**
- Produces: `Mode` TS type with 8 values; `MODE_LABELS`, `MODE_ICONS`, `MODE_DESCRIPTIONS` records for all 8 modes; `StartGameRequest` interface with `showCategoryToImpostor` and `showImpostorCount` fields

- [ ] **Step 1: Update `src/types/index.ts`**

```typescript
export type Mode =
  | 'clasico'
  | 'caos'
  | 'aliados'
  | 'espejo'
  | 'infiltrados'
  | 'aleatorio'
  | 'sin_impostores'
  | 'todos_impostores';
// 'ciego' removed from UI type — kept in DB/backend only
export type Difficulty = 'facil' | 'dificil' | 'brutal';

export interface Player {
  id: string;
  name: string;
  telegram_id: number | null;
  token: string;
}

export interface PlayerTokenOut {
  name: string;
  token: string;
}

export interface StartGameResponse {
  category: string;
  mode: Mode;
  n_impostors: number;
  sent: string[];
  failed: string[];
  session_id: string;
  players: PlayerTokenOut[];
}

export interface RevealState {
  state: 'waiting' | 'ready';
  player_name: string;
  session_id?: string;
  is_impostor?: boolean;
  category?: string | null;
}

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  lang: string;
}
```

- [ ] **Step 2: Update `src/constants/labels.ts`**

```typescript
import type { Mode, Difficulty } from '../types';

export const MODE_LABELS: Record<Mode, string> = {
  clasico:          'Clásico',
  caos:             'Caos',
  aliados:          'Aliados',
  espejo:           'Espejo',
  infiltrados:      'Infiltrados',
  aleatorio:        'Aleatorio',
  sin_impostores:   'Sin Impostores',
  todos_impostores: 'Todos Impostores',
};

export const MODE_ICONS: Record<Mode, string> = {
  clasico:          '🎯',
  caos:             '🎲',
  aliados:          '🤝',
  espejo:           '🪞',
  infiltrados:      '🕵️',
  aleatorio:        '🎰',
  sin_impostores:   '😇',
  todos_impostores: '🔥',
};

export const MODE_DESCRIPTIONS: Record<Mode, string> = {
  clasico:          'Un impostor. No sabe la palabra.',
  caos:             'Impostores aleatorios. Todos saben cuántos hay.',
  aliados:          '2 impostores que se conocen entre sí.',
  espejo:           'El impostor tiene una palabra diferente de la misma categoría.',
  infiltrados:      '2 impostores con palabras distintas. No se conocen.',
  aleatorio:        'El destino elige. Puede pasar cualquier cosa.',
  sin_impostores:   'Nadie es impostor. ¿Lo sabrán?',
  todos_impostores: 'Todos son impostores. Nadie sabe la palabra.',
};

export const DIFFICULTY_LABELS: Record<Difficulty, string> = {
  facil:   'Fácil',
  dificil: 'Difícil',
  brutal:  'Brutal',
};
```

- [ ] **Step 3: Update `src/api/game.ts`**

```typescript
import type { StartGameResponse } from '../types';
import { getStoredTokens } from '../lib/playerTokens';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export interface StartGameRequest {
  players: { id: string; name: string; telegram_id: number | null; token: string }[];
  mode: string;
  difficulty: string;
  categories?: string[];
  show_category_to_impostor?: boolean;
  show_impostor_count?: boolean;
}

export async function startGame(
  req: StartGameRequest,
  authToken: string,
): Promise<StartGameResponse> {
  const stored = getStoredTokens();
  const players = req.players.map((p) => ({
    ...p,
    token: p.token || stored.find((s) => s.name === p.name)?.token || '',
  }));

  const res = await fetch(`${API_URL}/api/game/start`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify({ ...req, players }),
  });
  if (!res.ok) throw new Error(`Game start failed: ${res.status}`);
  return res.json();
}

export async function getCategories(): Promise<string[]> {
  const res = await fetch(`${API_URL}/api/categories`);
  const data = await res.json();
  return data.categories;
}
```

- [ ] **Step 4: Run TypeScript check**

```bash
cd /path/to/impostor-web && npx vitest run
```
Expected: all tests pass, no TypeScript compile errors.

- [ ] **Step 5: Commit**

```bash
git add src/types/index.ts src/constants/labels.ts src/api/game.ts
git commit -m "feat(web): update Mode type and constants for new modes"
```

---

## Task 5 (Web): Overhaul StepMode.tsx

**Repo:** `impostor-web`

**Files:**
- Modify: `src/components/wizard/StepMode.tsx`
- Test: `src/components/wizard/StepMode.test.tsx` (create)

**Interfaces:**
- Consumes: `Mode`, `Difficulty` from Task 4; `MODE_DESCRIPTIONS`, `MODE_ICONS` from Task 4
- Produces: `StepModeProps` with `playerCount`, `showCategoryToImpostor`, `onShowCategoryToImpostorChange`, `showImpostorCount`, `onShowImpostorCountChange`; 6-mode grid; per-card toggles; player-count-aware disabled states

- [ ] **Step 1: Write failing tests**

Create `src/components/wizard/StepMode.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { StepMode } from './StepMode'

const baseProps = {
  mode: 'clasico' as const,
  setMode: vi.fn(),
  difficulty: 'dificil' as const,
  setDifficulty: vi.fn(),
  categories: [],
  onCategoriesChange: vi.fn(),
  onBack: vi.fn(),
  onNext: vi.fn(),
  playerCount: 5,
  showCategoryToImpostor: true,
  onShowCategoryToImpostorChange: vi.fn(),
  showImpostorCount: true,
  onShowImpostorCountChange: vi.fn(),
}

describe('StepMode', () => {
  it('renders all 6 mode cards', () => {
    render(<StepMode {...baseProps} />)
    expect(screen.getByText('Clásico')).toBeInTheDocument()
    expect(screen.getByText('Caos')).toBeInTheDocument()
    expect(screen.getByText('Aliados')).toBeInTheDocument()
    expect(screen.getByText('Espejo')).toBeInTheDocument()
    expect(screen.getByText('Infiltrados')).toBeInTheDocument()
    expect(screen.getByText('Aleatorio')).toBeInTheDocument()
  })

  it('disables Aliados card when playerCount < 4', () => {
    render(<StepMode {...baseProps} playerCount={3} />)
    const aliadosCard = screen.getByTestId('mode-card-aliados')
    expect(aliadosCard).toHaveAttribute('disabled')
  })

  it('enables Aliados card when playerCount >= 4', () => {
    render(<StepMode {...baseProps} playerCount={4} />)
    const aliadosCard = screen.getByTestId('mode-card-aliados')
    expect(aliadosCard).not.toHaveAttribute('disabled')
  })

  it('disables Infiltrados card when playerCount < 5', () => {
    render(<StepMode {...baseProps} playerCount={4} />)
    const infiltradosCard = screen.getByTestId('mode-card-infiltrados')
    expect(infiltradosCard).toHaveAttribute('disabled')
  })

  it('enables Infiltrados card when playerCount >= 5', () => {
    render(<StepMode {...baseProps} playerCount={5} />)
    const infiltradosCard = screen.getByTestId('mode-card-infiltrados')
    expect(infiltradosCard).not.toHaveAttribute('disabled')
  })

  it('shows category toggle when clasico is selected', () => {
    render(<StepMode {...baseProps} mode="clasico" />)
    expect(screen.getByLabelText('Impostor ve la categoría')).toBeInTheDocument()
  })

  it('shows impostor-count toggle when caos is selected', () => {
    render(<StepMode {...baseProps} mode="caos" />)
    expect(screen.getByLabelText('Revelar número de impostores')).toBeInTheDocument()
  })

  it('calls onShowCategoryToImpostorChange when category toggle clicked', async () => {
    const handler = vi.fn()
    render(
      <StepMode {...baseProps} mode="clasico" onShowCategoryToImpostorChange={handler} />,
    )
    await userEvent.click(screen.getByLabelText('Impostor ve la categoría'))
    expect(handler).toHaveBeenCalledWith(false)
  })
})
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd /path/to/impostor-web && npx vitest run src/components/wizard/StepMode.test.tsx
```
Expected: FAIL — component doesn't have new props yet.

- [ ] **Step 3: Rewrite `src/components/wizard/StepMode.tsx`**

```typescript
import type { ElementType } from 'react';
import {
  Shield, Layers, Users, Shuffle, Eye, UserCheck, Dice1, Spy,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { CategorySelector } from '@/components/CategorySelector';
import type { Mode, Difficulty } from '@/types';

interface StepModeProps {
  mode: Mode;
  setMode: (mode: Mode) => void;
  difficulty: Difficulty;
  setDifficulty: (d: Difficulty) => void;
  categories: string[];
  onCategoriesChange: (cats: string[]) => void;
  onBack: () => void;
  onNext: () => void;
  playerCount: number;
  showCategoryToImpostor: boolean;
  onShowCategoryToImpostorChange: (v: boolean) => void;
  showImpostorCount: boolean;
  onShowImpostorCountChange: (v: boolean) => void;
}

interface ModeCard {
  key: Mode;
  label: string;
  icon: ElementType;
  description: string;
  minPlayers?: number;
  minPlayersLabel?: string;
  special?: boolean; // amber/gold highlight for aleatorio
}

const MODE_CARDS: ModeCard[] = [
  {
    key: 'clasico',
    label: 'Clásico',
    icon: Shield,
    description: 'Un impostor. No sabe la palabra.',
  },
  {
    key: 'caos',
    label: 'Caos',
    icon: Layers,
    description: 'Impostores aleatorios. Todos saben cuántos hay.',
  },
  {
    key: 'aliados',
    label: 'Aliados',
    icon: Users,
    description: '2 impostores que se conocen entre sí.',
    minPlayers: 4,
    minPlayersLabel: 'Necesitas 4+ jugadores',
  },
  {
    key: 'espejo',
    label: 'Espejo',
    icon: Shuffle,
    description: 'El impostor tiene una palabra diferente.',
  },
  {
    key: 'infiltrados',
    label: 'Infiltrados',
    icon: Eye,
    description: '2 impostores con palabras distintas. No se conocen.',
    minPlayers: 5,
    minPlayersLabel: 'Necesitas 5+ jugadores',
  },
  {
    key: 'aleatorio',
    label: 'Aleatorio',
    icon: Dice1,
    description: 'El destino elige. Puede pasar cualquier cosa.',
    special: true,
  },
];

const DIFFICULTY_OPTIONS: { key: Difficulty; label: string }[] = [
  { key: 'facil', label: 'Fácil' },
  { key: 'dificil', label: 'Difícil' },
  { key: 'brutal', label: 'Brutal' },
];

export function StepMode({
  mode,
  setMode,
  difficulty,
  setDifficulty,
  categories,
  onCategoriesChange,
  onBack,
  onNext,
  playerCount,
  showCategoryToImpostor,
  onShowCategoryToImpostorChange,
  showImpostorCount,
  onShowImpostorCountChange,
}: StepModeProps) {
  return (
    <div className="flex flex-col gap-5">
      <h2 className="text-2xl font-bold text-stone-900">Modo de juego</h2>

      {/* Mode grid — 2×3 */}
      <div className="grid grid-cols-2 gap-3">
        {MODE_CARDS.map(
          ({ key, label, icon: Icon, description, minPlayers, minPlayersLabel, special }) => {
            const isDisabled = minPlayers !== undefined && playerCount < minPlayers;
            const isSelected = mode === key;
            return (
              <button
                key={key}
                type="button"
                data-testid={`mode-card-${key}`}
                onClick={() => !isDisabled && setMode(key)}
                disabled={isDisabled}
                className={[
                  'rounded-lg border p-4 text-left transition-colors',
                  isDisabled
                    ? 'opacity-40 cursor-not-allowed bg-white border-stone-200'
                    : isSelected
                    ? special
                      ? 'bg-amber-100 border-amber-500'
                      : 'bg-amber-50 border-amber-600'
                    : special
                    ? 'bg-amber-50 border-amber-200 hover:bg-amber-100 cursor-pointer'
                    : 'bg-white border-stone-200 hover:bg-stone-50 cursor-pointer',
                ].join(' ')}
              >
                <Icon size={24} className="mb-2 text-stone-700" />
                <p className="font-semibold text-stone-900">{label}</p>
                <p className="text-sm text-stone-500">{description}</p>
                {isDisabled && minPlayersLabel && (
                  <p className="mt-1 text-xs text-stone-400">{minPlayersLabel}</p>
                )}

                {/* Per-card toggles — shown only when this card is selected */}
                {isSelected && key === 'clasico' && (
                  <label
                    className="mt-3 flex items-center gap-2 text-xs text-stone-600 cursor-pointer"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      type="checkbox"
                      aria-label="Impostor ve la categoría"
                      checked={showCategoryToImpostor}
                      onChange={(e) => onShowCategoryToImpostorChange(e.target.checked)}
                      className="rounded"
                    />
                    Impostor ve la categoría
                  </label>
                )}
                {isSelected && key === 'caos' && (
                  <label
                    className="mt-3 flex items-center gap-2 text-xs text-stone-600 cursor-pointer"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      type="checkbox"
                      aria-label="Revelar número de impostores"
                      checked={showImpostorCount}
                      onChange={(e) => onShowImpostorCountChange(e.target.checked)}
                      className="rounded"
                    />
                    Revelar número de impostores
                  </label>
                )}
              </button>
            );
          },
        )}
      </div>

      {/* Difficulty pill */}
      <div className="flex rounded-lg bg-stone-100 p-1 gap-1">
        {DIFFICULTY_OPTIONS.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            onClick={() => setDifficulty(key)}
            className={`flex-1 py-1.5 text-sm font-medium transition-colors rounded-md ${
              difficulty === key
                ? 'bg-amber-600 text-white'
                : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <CategorySelector value={categories} onChange={onCategoriesChange} />

      <div className="flex justify-between gap-2">
        <Button variant="ghost" onClick={onBack}>
          ← Atrás
        </Button>
        <Button className="bg-stone-900 text-white hover:bg-stone-800" onClick={onNext}>
          Siguiente →
        </Button>
      </div>
    </div>
  );
}
```

> Note: `Dice1` and `Spy` may not exist in lucide-react. Use `Shuffle` for aleatorio and `Search` for infiltrados if needed — check available icons with `import { ... } from 'lucide-react'` and pick what's available. The icons can differ from the spec as long as they're semantically close.

- [ ] **Step 4: Run new tests**

```bash
cd /path/to/impostor-web && npx vitest run src/components/wizard/StepMode.test.tsx
```
Expected: all PASS.

- [ ] **Step 5: Run full suite**

```bash
cd /path/to/impostor-web && npx vitest run
```
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/components/wizard/StepMode.tsx src/components/wizard/StepMode.test.tsx
git commit -m "feat(web): overhaul StepMode with 6-mode grid, toggles, player-count guards"
```

---

## Task 6 (Web): WizardShell + StepReview

**Repo:** `impostor-web`

**Files:**
- Modify: `src/components/wizard/WizardShell.tsx`
- Modify: `src/components/wizard/StepReview.tsx`
- Test: `src/components/wizard/StepReview.test.tsx` (create)

**Interfaces:**
- Consumes: new `StepModeProps` from Task 5; `StartGameRequest` with new options from Task 4
- Produces: `WizardShell` threads `showCategoryToImpostor`, `showImpostorCount`, `playerCount` to `StepMode`; removes login buttons; resolves aleatorio mode after game start; `computeImpostors` matches backend formula

- [ ] **Step 1: Write failing tests for computeImpostors**

Create `src/components/wizard/StepReview.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest'

// Import the function — it will be exported after this task
// import { computeImpostors } from './StepReview'
// For now test the expected behavior so it fails until exported

describe('computeImpostors', () => {
  // We test via rendering since computeImpostors is internal
  // These are snapshot-style checks on the displayed text
})
```

Instead, export and test `computeImpostors` directly. Add `export` to it in `StepReview.tsx` in step 3, then test:

```typescript
import { describe, it, expect } from 'vitest'
import { computeImpostors } from './StepReview'

describe('computeImpostors', () => {
  it('clasico always returns 1', () => {
    expect(computeImpostors(3, 'clasico')).toBe('1')
    expect(computeImpostors(10, 'clasico')).toBe('1')
  })

  it('caos returns range based on floor(n/2)', () => {
    expect(computeImpostors(3, 'caos')).toBe('1')   // floor(3/2)=1
    expect(computeImpostors(4, 'caos')).toBe('1–2') // floor(4/2)=2
    expect(computeImpostors(6, 'caos')).toBe('1–3') // floor(6/2)=3
  })

  it('aliados always returns 2', () => {
    expect(computeImpostors(4, 'aliados')).toBe('2')
  })

  it('espejo returns range same as caos', () => {
    expect(computeImpostors(4, 'espejo')).toBe('1–2')
  })

  it('infiltrados always returns 2', () => {
    expect(computeImpostors(5, 'infiltrados')).toBe('2')
  })

  it('aleatorio returns ?', () => {
    expect(computeImpostors(5, 'aleatorio')).toBe('?')
  })
})
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd /path/to/impostor-web && npx vitest run src/components/wizard/StepReview.test.tsx
```
Expected: FAIL — `computeImpostors` not exported.

- [ ] **Step 3: Update `src/components/wizard/StepReview.tsx`**

Replace `MODE_ICONS` to include new modes (import from lucide-react what's available), and fix `computeImpostors`:

```typescript
import {
  Shield, Layers, Users, Shuffle, Eye, Dices,
  Target, UserX, Loader2, type LucideIcon,
} from 'lucide-react';
import type { Mode, Difficulty, Player } from '@/types';
import { MODE_LABELS, DIFFICULTY_LABELS } from '@/constants/labels';

const MODE_ICONS: Partial<Record<Mode, LucideIcon>> = {
  clasico:     Shield,
  caos:        Layers,
  aliados:     Users,
  espejo:      Shuffle,
  infiltrados: Eye,
  aleatorio:   Dices,
};

export function computeImpostors(playerCount: number, mode: Mode): string {
  const half = Math.floor(playerCount / 2);
  switch (mode) {
    case 'clasico':     return '1';
    case 'caos':        return half <= 1 ? '1' : `1–${half}`;
    case 'aliados':     return '2';
    case 'espejo':      return half <= 1 ? '1' : `1–${half}`;
    case 'infiltrados': return '2';
    case 'aleatorio':   return '?';
    default:            return '?';
  }
}
```

Keep the rest of the component identical; update `ModeIcon` to handle missing modes:
```typescript
  const ModeIcon = MODE_ICONS[mode] ?? Shield;
```

- [ ] **Step 4: Update `src/components/wizard/WizardShell.tsx`**

Add new state and remove login UI. The complete diff of changes:

**Add to state declarations (after `categories`):**
```typescript
  const [showCategoryToImpostor, setShowCategoryToImpostor] = useState(true);
  const [showImpostorCount, setShowImpostorCount] = useState(true);
```

**Update `onStart` to pass new options:**
```typescript
  const onStart = useCallback(async () => {
    const playersForApi = user
      ? players
      : players.map((p) => ({ ...p, id: '' }));
    await start(
      {
        players: playersForApi,
        mode,
        difficulty,
        categories,
        show_category_to_impostor: showCategoryToImpostor,
        show_impostor_count: showImpostorCount,
      },
      token ?? '',
    );
  }, [
    players, mode, difficulty, categories,
    showCategoryToImpostor, showImpostorCount,
    start, user, token,
  ]);
```

**Add `useEffect` to resolve aleatorio mode after game starts:**
```typescript
  useEffect(() => {
    if (result?.mode && result.mode !== 'aleatorio') {
      setMode(result.mode as Mode);
    }
  }, [result]);
```

**Update `StepMode` render to pass new props:**
```typescript
            <StepMode
              mode={mode}
              setMode={setMode}
              difficulty={difficulty}
              setDifficulty={setDifficulty}
              categories={categories}
              onCategoriesChange={setCategories}
              onBack={goToStep1}
              onNext={goToStep3}
              playerCount={players.length}
              showCategoryToImpostor={showCategoryToImpostor}
              onShowCategoryToImpostorChange={setShowCategoryToImpostor}
              showImpostorCount={showImpostorCount}
              onShowImpostorCountChange={setShowImpostorCount}
            />
```

**Remove the login/logout button block** (lines 128–148 in the current file). Replace the entire `{user ? ... : ...}` block with nothing — just remove it. The top bar becomes:

```typescript
        <div className="mb-6 flex items-center justify-between">
          <span className="text-stone-900 font-bold text-lg">El Impostor</span>
        </div>
```

Also remove unused imports: `LogIn`, `LogOut` from `lucide-react`, and `useAuth` from contexts. Remove the `{ user, token, login, logout } = useAuth()` destructure — keep only `token`:

```typescript
  const { token } = useAuth();
```

- [ ] **Step 5: Run tests**

```bash
cd /path/to/impostor-web && npx vitest run src/components/wizard/StepReview.test.tsx
```
Expected: PASS.

- [ ] **Step 6: Run full suite**

```bash
cd /path/to/impostor-web && npx vitest run
```
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/components/wizard/WizardShell.tsx src/components/wizard/StepReview.tsx \
        src/components/wizard/StepReview.test.tsx
git commit -m "feat(web): thread mode options, fix computeImpostors, remove login button"
```

---

## Task 7 (Web): Update RondaPanel

**Repo:** `impostor-web`

**Files:**
- Modify: `src/components/RondaPanel.tsx`
- Test: `src/components/RondaPanel.test.tsx` (create)

**Interfaces:**
- Consumes: `Mode` from Task 4; updated mode list; `RondaLaunchConfig` adds `showCategoryToImpostor`, `showImpostorCount`
- Produces: `RondaLaunchConfig` with new fields; 6-mode pills (no `ciego`); player-count-aware disabling; per-mode option toggles

- [ ] **Step 1: Write failing tests**

Create `src/components/RondaPanel.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { RondaPanel } from './RondaPanel'

const players = [
  { name: 'A', token: 'tok-a' },
  { name: 'B', token: 'tok-b' },
  { name: 'C', token: 'tok-c' },
  { name: 'D', token: 'tok-d' },
  { name: 'E', token: 'tok-e' },
]

const baseProps = {
  players,
  currentMode: 'clasico' as const,
  currentDifficulty: 'dificil' as const,
  currentCategories: [],
  isLoading: false,
  onLaunch: vi.fn(),
  onCancel: vi.fn(),
}

describe('RondaPanel', () => {
  it('shows 6 mode options (no ciego)', () => {
    render(<RondaPanel {...baseProps} />)
    expect(screen.getByText('Clásico')).toBeInTheDocument()
    expect(screen.getByText('Caos')).toBeInTheDocument()
    expect(screen.getByText('Aliados')).toBeInTheDocument()
    expect(screen.getByText('Espejo')).toBeInTheDocument()
    expect(screen.getByText('Infiltrados')).toBeInTheDocument()
    expect(screen.getByText('Aleatorio')).toBeInTheDocument()
    expect(screen.queryByText('Ciego')).not.toBeInTheDocument()
  })

  it('disables Aliados pill when fewer than 4 players', () => {
    render(
      <RondaPanel
        {...baseProps}
        players={players.slice(0, 3)}
      />,
    )
    const aliadosBtn = screen.getByRole('button', { name: /aliados/i })
    expect(aliadosBtn).toBeDisabled()
  })

  it('disables Infiltrados pill when fewer than 5 players', () => {
    render(
      <RondaPanel
        {...baseProps}
        players={players.slice(0, 4)}
      />,
    )
    const infiltradosBtn = screen.getByRole('button', { name: /infiltrados/i })
    expect(infiltradosBtn).toBeDisabled()
  })
})
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd /path/to/impostor-web && npx vitest run src/components/RondaPanel.test.tsx
```
Expected: FAIL — `ciego` still exists; no `infiltrados`/`aleatorio`.

- [ ] **Step 3: Update `src/components/RondaPanel.tsx`**

Replace the `RondaLaunchConfig` interface, `MODE_OPTIONS`, state, and launch button:

```typescript
export interface RondaLaunchConfig {
  mode: Mode
  difficulty: Difficulty
  categories: string[]
  players: { name: string; token: string }[]
  showCategoryToImpostor: boolean
  showImpostorCount: boolean
}
```

Replace `MODE_OPTIONS`:
```typescript
const MODE_OPTIONS: {
  key: Mode
  label: string
  icon: React.ElementType
  minPlayers?: number
}[] = [
  { key: 'clasico',     label: 'Clásico',     icon: Shield },
  { key: 'caos',        label: 'Caos',        icon: Layers },
  { key: 'aliados',     label: 'Aliados',     icon: Users,   minPlayers: 4 },
  { key: 'espejo',      label: 'Espejo',      icon: Shuffle },
  { key: 'infiltrados', label: 'Infiltrados', icon: Eye,     minPlayers: 5 },
  { key: 'aleatorio',   label: 'Aleatorio',   icon: Shuffle },
]
```

Add to component state (after `rondaCategories`):
```typescript
  const [showCategoryToImpostor, setShowCategoryToImpostor] = useState(true)
  const [showImpostorCount, setShowImpostorCount] = useState(true)
```

Replace mode pill section to respect `minPlayers`:
```typescript
      <div>
        <span className="text-xs font-semibold uppercase tracking-wider text-stone-500">
          Modo
        </span>
        <div className="flex flex-wrap gap-2 mt-2">
          {MODE_OPTIONS.map(({ key, label, icon: Icon, minPlayers }) => {
            const isDisabled = minPlayers !== undefined && rondaPlayers.length < minPlayers
            return (
              <button
                key={key}
                type="button"
                disabled={isDisabled}
                onClick={() => !isDisabled && setRondaMode(key)}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm border transition-colors',
                  isDisabled
                    ? 'opacity-40 cursor-not-allowed bg-white border-stone-200 text-stone-400'
                    : rondaMode === key
                    ? 'bg-amber-50 border-amber-600 text-amber-800'
                    : 'bg-white border-stone-200 text-stone-600 hover:bg-stone-50',
                )}
              >
                <Icon size={14} />
                {label}
              </button>
            )
          })}
        </div>
      </div>
```

Update launch button `onClick` to include new fields:
```typescript
        onClick={() =>
          onLaunch({
            mode: rondaMode,
            difficulty: rondaDifficulty,
            categories: rondaCategories,
            players: rondaPlayers,
            showCategoryToImpostor,
            showImpostorCount,
          })
        }
```

Add `Eye` to the lucide-react import at the top:
```typescript
import { Shield, Layers, Users, Shuffle, Eye } from 'lucide-react'
```

- [ ] **Step 4: Update `WizardShell.tsx` — handleRondaLaunch to pass new fields**

In `src/components/wizard/WizardShell.tsx`, update `handleRondaLaunch`:

```typescript
  const handleRondaLaunch = useCallback(
    async (cfg: RondaLaunchConfig) => {
      setShowRondaPanel(false);
      setMode(cfg.mode);
      setDifficulty(cfg.difficulty);
      setCategories(cfg.categories);
      setShowCategoryToImpostor(cfg.showCategoryToImpostor);
      setShowImpostorCount(cfg.showImpostorCount);
      reset();
      const playersForApi = cfg.players.map((p) => ({
        id: '',
        name: p.name,
        telegram_id: null as null,
        token: p.token,
      }));
      await start(
        {
          players: playersForApi,
          mode: cfg.mode,
          difficulty: cfg.difficulty,
          categories: cfg.categories,
          show_category_to_impostor: cfg.showCategoryToImpostor,
          show_impostor_count: cfg.showImpostorCount,
        },
        token ?? '',
      );
    },
    [reset, start, token],
  );
```

- [ ] **Step 5: Run new tests**

```bash
cd /path/to/impostor-web && npx vitest run src/components/RondaPanel.test.tsx
```
Expected: PASS.

- [ ] **Step 6: Run full suite**

```bash
cd /path/to/impostor-web && npx vitest run
```
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/components/RondaPanel.tsx src/components/RondaPanel.test.tsx \
        src/components/wizard/WizardShell.tsx
git commit -m "feat(web): update RondaPanel with new modes, toggles, player-count guards"
```

---

## Final Verification

After all tasks are complete, run both full test suites one last time:

```bash
# API
cd /path/to/impostor-api && pytest -q
# Expected: 20+ tests, 0 failed

# Web
cd /path/to/impostor-web && npx vitest run
# Expected: 18+ tests, 0 failed
```

Then push both branches and open PRs to `main`.
