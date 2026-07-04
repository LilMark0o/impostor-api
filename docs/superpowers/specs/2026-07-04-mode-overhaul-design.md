# Mode Overhaul — Implementation Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure game modes — remove `ciego` as a standalone mode, add `infiltrados` and `aleatorio` (with hidden special modes `sin_impostores`/`todos_impostores`), add per-mode config toggles, enforce player-count guards, and remove login UI from the frontend.

**Architecture:** Backend extends the `Mode` enum and `StartGameRequest`, updates `assign_roles()` + `_build_message()`, and adds validation guards. Frontend updates the mode grid with per-card toggles, disables incompatible modes based on player count, and removes the login button.

**Tech Stack:** FastAPI + SQLAlchemy async (impostor-api), React + TypeScript + Tailwind (impostor-web)

**Repos:** `impostor-api` and `impostor-web` — both need changes.

---

## Modes: Before → After

| Before | After | Change |
|--------|-------|--------|
| `clasico` | `clasico` | New option: `show_category_to_impostor` |
| `caos` | `caos` | New option: `show_impostor_count` |
| `ciego` | *(kept in DB enum, hidden from UI)* | Was caos + show_impostor_count=False. Backend still handles it gracefully. |
| `aliados` | `aliados` | Add min-4-player guard |
| `espejo` | `espejo` | Unchanged |
| *(new)* | `infiltrados` | 2 impostors, different fake words, don't know each other. Min 5 players. |
| *(new)* | `aleatorio` | Backend picks randomly. Can land on `sin_impostores` or `todos_impostores`. |

`sin_impostores` and `todos_impostores` are **internal states only** — not selectable directly, only reachable via `aleatorio`. The response `mode` field always reflects the actual mode that ran.

---

## File Map

### impostor-api

| File | Change |
|------|--------|
| `app/models.py` | Add `infiltrados`, `aleatorio` to `Mode` enum; add `show_category_to_impostor` + `show_impostor_count` to `StartGameRequest` |
| `app/game/roles.py` | Add `infiltrados`, `sin_impostores`, `todos_impostores` role assignment logic |
| `app/game/engine.py` | Handle `aleatorio` mode resolution; pass new options to `_build_message`; add player-count validation |

### impostor-web

| File | Change |
|------|--------|
| `src/types/index.ts` | Update `Mode` union: add `infiltrados`, `aleatorio`; remove `ciego` |
| `src/constants/labels.ts` | Add labels/icons for new modes; remove `ciego` |
| `src/api/game.ts` | Add `showCategoryToImpostor` + `showImpostorCount` to `startGame` payload |
| `src/components/wizard/StepMode.tsx` | New mode grid; per-card toggles; player-count-aware disabling |
| `src/components/wizard/StepReview.tsx` | Fix `computeImpostors` to match backend formula |
| `src/components/wizard/WizardShell.tsx` | Thread new mode options through state; remove `<AuthButton />` |
| `src/components/RondaPanel.tsx` | Mirror StepMode changes |

---

## Backend Design

### models.py — Mode enum + Request

```python
class Mode(str, Enum):
    clasico     = "clasico"
    caos        = "caos"
    ciego       = "ciego"       # kept for DB backwards-compat; hidden from UI
    aliados     = "aliados"
    espejo      = "espejo"
    infiltrados = "infiltrados"
    aleatorio   = "aleatorio"

class StartGameRequest(BaseModel):
    players: list[Player]
    mode: Mode = Mode.clasico
    difficulty: Difficulty = Difficulty.dificil
    categories: list[str] = []
    show_category_to_impostor: bool = True   # clasico: show/hide category name to impostor
    show_impostor_count: bool = True          # caos/ciego: show/hide impostor count to all players
```

### roles.py — assign_roles() additions

Current function handles `clasico`, `caos`, `ciego`, `aliados`, `espejo`. New cases:

**`infiltrados`** (2 impostors, different words, don't know each other):
```python
# n_impostors = 2 (fixed)
# Each impostor: pick_mirror_word() independently → different fake word
# Neither impostor is told about the other (no accomplice field)
# is_impostor=True, word=fake_word, hint=pick_hint(category, fake_word, difficulty)
```

**`sin_impostores`** (0 impostors, internal only):
```python
# n_impostors = 0
# All players: is_impostor=False, word=real_word
# Standard innocent message for everyone
```

**`todos_impostores`** (everyone is impostor, internal only):
```python
# n_impostors = len(players)
# LLM picks a word (never revealed to anyone — only used to generate hints)
# All players: is_impostor=True
# Each gets their own pick_hint(category, real_word, difficulty) call → hints vary per player
# Message shows category + hint only, no real word revealed
```

### engine.py — aleatorio resolution + validation

```python
# Internal-only mode strings (not in Mode enum — never sent by clients directly)
_SIN_IMPOSTORES = "sin_impostores"
_TODOS_IMPOSTORES = "todos_impostores"

_ALEATORIO_POOL = [
    Mode.clasico, Mode.caos, Mode.aliados,
    Mode.espejo, Mode.infiltrados,
    _SIN_IMPOSTORES, _TODOS_IMPOSTORES,
]

# In run(), before assign_roles():
# resolved_mode is str | Mode — may be an internal string after aleatorio resolves
if mode == Mode.aleatorio:
    eligible = [m for m in _ALEATORIO_POOL if _mode_is_eligible(m, len(players))]
    resolved_mode = random.choice(eligible)
else:
    resolved_mode = mode

def _mode_is_eligible(mode, n: int) -> bool:
    if mode == Mode.aliados: return n >= 4
    if mode == Mode.infiltrados: return n >= 5
    return True

# Player-count validation (raises HTTPException 400):
if mode == Mode.aliados and len(players) < 4:
    raise HTTPException(status_code=400, detail="aliados requires at least 4 players")
if mode == Mode.infiltrados and len(players) < 5:
    raise HTTPException(status_code=400, detail="infiltrados requires at least 5 players")
```

### _build_message() — new options

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
        return f"🎯 *Categoría:* {category}\n🔤 *Tu palabra:* {assignment.word.upper()}"

    # todos_impostores: special message (no "you are THE impostor" since everyone is)
    if mode == "todos_impostores":
        return f"🎭 *¡Todos son impostores!*\n\n📂 {category} — [{assignment.hint}]"

    lines = ["🎭 *¡Eres el IMPOSTOR!*"]

    if show_category_to_impostor:
        lines.append(f"\n📂 {category} — [{assignment.hint}]")
    else:
        lines.append(f"\n🕵️ Pista: [{assignment.hint}]")

    if mode == Mode.aliados and assignment.accomplice:
        lines.append(f"🤝 *Tu cómplice:* {assignment.accomplice}")

    if mode == Mode.espejo or mode == Mode.infiltrados:
        lines.append(f"🪞 *Tu palabra (diferente):* {assignment.word.upper()}")

    if show_impostor_count:
        lines.append(f"👥 *Impostores en juego:* {n_impostors}")

    return "\n".join(lines)
```

---

## Frontend Design

### types/index.ts

```typescript
export type Mode =
  | "clasico"
  | "caos"
  | "aliados"
  | "espejo"
  | "infiltrados"
  | "aleatorio"
// "ciego" removed from UI type (still in DB, backend handles gracefully)
```

### constants/labels.ts

```typescript
export const MODE_LABELS: Record<Mode, string> = {
  clasico:     "Clásico",
  caos:        "Caos",
  aliados:     "Aliados",
  espejo:      "Espejo",
  infiltrados: "Infiltrados",
  aleatorio:   "Aleatorio",
}

export const MODE_ICONS: Record<Mode, string> = {
  clasico:     "🎯",
  caos:        "🎲",
  aliados:     "🤝",
  espejo:      "🪞",
  infiltrados: "🕵️",
  aleatorio:   "🎰",
}

export const MODE_DESCRIPTIONS: Record<Mode, string> = {
  clasico:     "1 impostor. No sabe la palabra.",
  caos:        "Impostores aleatorios. Todos saben cuántos hay.",
  aliados:     "2 impostores que se conocen entre sí.",
  espejo:      "El impostor tiene una palabra diferente de la misma categoría.",
  infiltrados: "2 impostores con palabras distintas. No se conocen.",
  aleatorio:   "El destino elige. Puede pasar cualquier cosa.",
}
```

### StepMode.tsx — mode grid

Layout: 2×3 grid (clasico, caos, aliados, espejo, infiltrados, aleatorio).

Each card: icon + name + 1-line description. Selected = amber border + amber-50 bg.

**Clasico card** — shows a small toggle below the description:
```
[ ] Impostor ve la categoría  (default: checked/on)
```
Toggle state: `showCategoryToImpostor: boolean` (prop up to WizardShell).

**Caos card** — shows a small checkbox:
```
[ ] Revelar número de impostores  (default: checked/on)
```
Checkbox state: `showImpostorCount: boolean` (prop up to WizardShell).

**Aliados card** — when `playerCount < 4`:
- Card is visually dimmed (`opacity-40 cursor-not-allowed`)
- Non-clickable
- Small label below: "Necesitas 4+ jugadores"

**Infiltrados card** — when `playerCount < 5`:
- Same disabled treatment
- Small label: "Necesitas 5+ jugadores"

**Aleatorio card** — always enabled. Amber/gold styling to distinguish it as special.

### StepReview.tsx — computeImpostors fix

```typescript
function computeImpostors(playerCount: number, mode: Mode): string {
  const half = Math.floor(playerCount / 2)
  switch (mode) {
    case "clasico":     return "1"
    case "caos":        return half <= 1 ? "1" : `1–${half}`
    case "aliados":     return "2"
    case "espejo":      return half <= 1 ? "1" : `1–${half}`
    case "infiltrados": return "2"
    case "aleatorio":   return "?"
  }
}
```

### WizardShell.tsx — new state + login removal

New state fields:
```typescript
const [showCategoryToImpostor, setShowCategoryToImpostor] = useState(true)
const [showImpostorCount, setShowImpostorCount] = useState(true)
```

Passed as props to `StepMode` and `RondaPanel`.

Passed to `startGame` call:
```typescript
await startGame({
  players, mode, difficulty, categories,
  show_category_to_impostor: showCategoryToImpostor,
  show_impostor_count: showImpostorCount,
})
```

**Login removal:** Remove `<AuthButton />` render from the header/shell. Do not delete the component — just stop rendering it.

### RondaPanel.tsx

Mirror all StepMode changes: same 6 modes, same per-card toggles, same player-count disabling. Add `showCategoryToImpostor` and `showImpostorCount` props to `RondaLaunchConfig`.

---

## Edge Cases & Guards

| Scenario | Handling |
|----------|----------|
| `aliados` + 3 players | Frontend: card disabled. Backend: 400 |
| `infiltrados` + 4 players | Frontend: card disabled. Backend: 400 |
| `aleatorio` picks `aliados` with 3 players | Backend eligibility filter excludes it |
| `aleatorio` picks `infiltrados` with 4 players | Backend eligibility filter excludes it |
| `ciego` arrives from old client | Backend treats as `caos` + `show_impostor_count=False` |
| `todos_impostores` / `sin_impostores` sent directly | Not in frontend Mode type. Backend should guard: only reachable via `aleatorio`. |

---

## Tests

### impostor-api

- `test_infiltrados_mode`: 5 players → 2 impostors, each gets different word, neither sees accomplice name
- `test_aliados_guard`: aliados + 3 players → 400
- `test_infiltrados_guard`: infiltrados + 4 players → 400
- `test_aleatorio_resolves`: aleatorio → response mode is NOT "aleatorio" (it resolved to a real mode)
- `test_sin_impostores`: sin_impostores internal mode → 0 impostors in response, all players get word
- `test_todos_impostores`: todos_impostores internal mode → all players are impostors
- `test_show_category_false`: clasico + show_category_to_impostor=False → impostor message has no category line
- `test_show_impostor_count_false`: caos + show_impostor_count=False → messages omit impostor count line

### impostor-web

- `StepMode` disables aliados chip when playerCount < 4
- `StepMode` disables infiltrados chip when playerCount < 5
- `computeImpostors` returns correct ranges for each mode
- `RondaPanel` respects same player-count guards
