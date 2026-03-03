# Implementation Plan: MVP Nationwide Simulation

**Branch**: `041-mvp-nationwide-sim` | **Date**: 2026-03-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/041-mvp-nationwide-sim/spec.md`

## Summary

Make Babylon playable as a nationwide geopolitical simulation by fixing 6 defects and implementing 7 new features across the Django backend, simulation engine bridge, and React frontend. The core work is wiring player actions into the simulation engine's `step()` function via the existing `persistent_context["player_actions"]` injection point in OODASystem, computing and persisting ActionResult records, and adding URL-based navigation with endgame detection display.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript 5.x (frontend)
**Primary Dependencies**: Django 5.x, Pydantic 2.x, NetworkX 3.x, psycopg 3.x, React 19, Zustand 5, Vite 6, deck.gl 9, react-router-dom 7 (installed, unused)
**Storage**: PostgreSQL 16+ (runtime state via `postgres_runtime.py`), SQLite (reference data)
**Testing**: pytest (backend unit/integration), Vitest (frontend), Playwright (E2E)
**Target Platform**: Web application (Django + React SPA), single-user local/deployed
**Project Type**: Web (Django backend + React frontend)
**Performance Goals**: Game creation < 10s, tick resolution reasonable for ~1,100 H3 territories
**Constraints**: Single-player MVP, no engine modifications (integration layer only)
**Scale/Scope**: ~1,100 CONUS territories, 5 user stories, 13 functional requirements

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Justification |
|-----------|--------|---------------|
| II.6 State is Data, Engine is Transformation | PASS | No engine modifications. `step()` remains pure. Actions injected via existing `persistent_context` parameter. |
| II.8 Client as Presentation Layer | PASS | Frontend receives JSON, renders it, emits player intents as JSON. No simulation logic in browser. |
| V. Player Verbs (9 canonical) | PASS | Using the constitutional 9 verbs: Educate, Aid, Attack, Mobilize, Campaign, Move, Investigate, Reproduce, Negotiate. |
| V. State AI Verbs (6) | PASS | NPC orgs use the 21-value ActionType enum via OODASystem's NPC stub. No change needed. |
| VII.1 UI Observes, Never Controls | PASS | Frontend emits intents (action submissions), never mutates state directly. |
| I.11 Emergent Pedagogy | PASS | All 9 verbs always available. No hidden win conditions. Consequences modeled. |
| III.1 No Magic Constants | PASS | All verb effects use coefficients from `OODADefines` in `defines.py`. No hardcoded values introduced. |

**Pre-design gate: PASS. No violations.**

## Project Structure

### Documentation (this feature)

```text
specs/041-mvp-nationwide-sim/
├── plan.md              # This file
├── research.md          # Phase 0 output — key technical decisions
├── data-model.md        # Phase 1 output — entity model documentation
├── quickstart.md        # Phase 1 output — implementation getting-started
├── contracts/           # Phase 1 output — API endpoint contracts
│   └── api-endpoints.md
├── checklists/
│   └── requirements.md  # Quality checklist (already exists)
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
# Backend (Django + Engine Bridge)
web/
├── game/
│   ├── api.py                    # MODIFY: add validation, idempotency guard
│   ├── apps.py                   # MODIFY: fix import boundary (FR-008)
│   ├── engine_bridge.py          # MODIFY: wire player actions, persist ActionResults
│   ├── tick_resolver.py          # MODIFY: add transaction wrapper
│   ├── serializers.py            # MODIFY: add verb validation
│   ├── models.py                 # READ ONLY (managed=False models)
│   ├── migrations/               # CREATE: GameEventLog migration (FR-009)
│   └── tests/                    # CREATE: 20+ Django backend tests (SC-006)
│       ├── __init__.py
│       ├── test_api.py
│       ├── test_engine_bridge.py
│       └── test_validation.py

# Frontend (React + Zustand)
web/frontend/src/
├── App.tsx                       # MODIFY: add React Router (FR-011)
├── stores/
│   └── gameStore.ts              # MODIFY: handle endgame, action results
├── components/
│   ├── HexMap.tsx                # MODIFY: fix TS error (FR-010)
│   ├── layout/GameShell.tsx      # MODIFY: endgame notification (FR-007)
│   ├── action/VerbSelector.tsx   # MODIFY: enhance tooltips (FR-012)
│   ├── action/ActionComposer.tsx # MODIFY: filter to is_player orgs
│   ├── TopBar.tsx                # MODIFY: disable resolve button during resolution
│   └── GameList.tsx              # MODIFY: scenario selection (FR-013)

# Engine (read-only reference, no modifications)
src/babylon/engine/systems/ooda.py          # READ: player_actions injection point
src/babylon/ooda/layer3.py                  # READ: verb→effect application
src/babylon/engine/observers/endgame_detector.py  # READ: 3 endgame conditions
```

**Structure Decision**: Existing web application structure. Backend modifications are confined to `web/game/` (the Django app) and specifically to `engine_bridge.py` which is the documented sole boundary between Django and the engine. Frontend modifications extend existing React components. No new directories created except `web/game/tests/` and `web/game/migrations/`.

## Implementation Phases

### Phase 1: Defect Fixes (FR-008, FR-009, FR-010)

Quick wins that unblock downstream work and CI.

| Task | File(s) | Description |
|------|---------|-------------|
| Fix import boundary | `web/game/apps.py` | Move `PostgresRuntime` import into `engine_bridge.py`, call bridge initialization from `apps.py` |
| Create migration | `web/game/migrations/` | `makemigrations game` for `GameEventLog` table |
| Fix TypeScript error | `web/frontend/src/components/HexMap.tsx` | Add null guard on possibly-undefined invocation |

**Exit criteria**: Import boundary test passes, `npm run build` succeeds, migration applies cleanly.

### Phase 2: Action Integration (FR-001, FR-002, FR-003, FR-004)

The core game loop — making player actions affect the simulation.

| Task | File(s) | Description |
|------|---------|-------------|
| Wire actions into step() | `web/game/engine_bridge.py` | In `resolve_tick()`: read pending turns via `get_pending_actions()`, format as `persistent_context["player_actions"]` dict keyed by org_id, pass to `step()` |
| Map UI verbs to ActionType | `web/game/engine_bridge.py` | Create `VERB_TO_ACTION_TYPE` mapping table (9 UI verbs → ActionType enum values) |
| Persist ActionResults | `web/game/engine_bridge.py` | After `step()`, extract `TurnResolution` from engine context, diff graph state to compute consciousness/heat deltas per action, write `ActionResult` rows |
| Server-side validation | `web/game/api.py`, `serializers.py` | Validate: org exists in current state AND is PoliticalFaction with is_player=True, verb is one of 9 canonical verbs, target_id exists in state |
| Idempotency guard | `web/game/api.py`, `tick_resolver.py` | Add `select_for_update()` on GameSession, set status to "resolving" during step, wrap in transaction |

**Exit criteria**: Submitted actions change simulation outcomes (consciousness/heat deltas visible), ActionResult records persist to database, invalid actions rejected with 4xx errors.

### Phase 3: Frontend Completion (FR-005, FR-007, FR-011, FR-012)

Player experience — seeing results, navigating, understanding the game.

| Task | File(s) | Description |
|------|---------|-------------|
| Action results display | Already works via `TickResults.tsx` | Verify `GET /results/{tick}/` returns populated data after Phase 2. No frontend changes needed if ActionResult records are persisted correctly. |
| Endgame notification | `GameShell.tsx`, `gameStore.ts` | Check snapshot for endgame events after each tick resolution. Display modal/banner with outcome type and summary. |
| URL-based navigation | `App.tsx` | Replace `View` state machine with `react-router-dom` v7 routes: `/login`, `/games`, `/games/:id`. Preserve existing component structure. |
| Resolve button UX | `TopBar.tsx`, `ActionComposer.tsx` | Disable button + show spinner while `resolving` state is true. Already partially implemented (`resolving` state exists in `GameShell`). |
| Verb tooltips | `VerbSelector.tsx` | Verb descriptions already exist as inline text. Add HTML `title` attributes for hover tooltips matching the existing `description` field. |
| Org filtering | `ActionComposer.tsx` | Filter org dropdown to only show PoliticalFaction orgs with `is_player=true` from snapshot organizations. |

**Exit criteria**: Action results visible after tick resolution, endgame condition triggers notification, URLs are bookmarkable, verbs have tooltips.

### Phase 4: Scenario Selection (FR-013)

| Task | File(s) | Description |
|------|---------|-------------|
| Backend scenario list | `web/game/api.py`, `engine_bridge.py` | Add `GET /api/scenarios/` endpoint returning available scenarios from `scenarios.py` factory functions |
| Frontend scenario picker | `GameList.tsx` | Add scenario dropdown/cards to game creation flow, send selected scenario key with create request |

**Exit criteria**: Player can choose between US nationwide (~1,100 territories) and at least one smaller scenario when creating a game.

### Phase 5: Testing & Verification (SC-005 through SC-008)

| Task | File(s) | Description |
|------|---------|-------------|
| Django backend tests | `web/game/tests/` | 20+ tests covering: game creation, action submission (valid/invalid), tick resolution, idempotency, action results retrieval, endgame detection, scenario selection |
| Verify existing tests | CI | Run `mise run check` (engine unit tests) and `mise run web:check` (frontend tests) — zero regressions |
| Verify npm build | CI | `npm run build` completes without TypeScript errors |
| Playwright E2E | `web/frontend/e2e/` | Update existing E2E files to run against live server: login, create game, submit action, resolve tick, verify results |

**Exit criteria**: All 8 success criteria met.

## Key Technical Decisions

### 1. Action Injection Point

The OODASystem already reads `context.persistent_data["player_actions"]` (ooda.py:113-119). The fix is in `engine_bridge.py:resolve_tick()` — read pending turns, format as the expected dict structure `{org_id: [{action_type, target_id, ...}]}`, and pass as `persistent_context`.

### 2. Verb→ActionType Mapping

| UI Verb | ActionType | Layer 3 Effect |
|---------|------------|----------------|
| educate | EDUCATE | Consciousness (via CommunitySystem) |
| reproduce | RECRUIT | Membership growth (via CommunitySystem) |
| investigate | MAP_NETWORK | None (intelligence gathering) |
| attack | ATTACK_INFRASTRUCTURE | Infrastructure −0.1 |
| mobilize | PROTEST | None (mass action, affects struggle dynamics) |
| campaign | PROPAGANDIZE | Consciousness (via CommunitySystem) |
| aid | PROVIDE_SERVICE | Consciousness (via CommunitySystem) |
| move | ORGANIZE | Edge transition TRANSACTIONAL→SOLIDARISTIC |
| negotiate | PROPOSE_ALLIANCE | None (diplomatic, org-org edge) |

### 3. ActionResult Delta Computation

After `step()`, diff the pre-step and post-step graph node attributes for the action's `target_id`:
- `consciousness_delta` = new `class_consciousness` − old `class_consciousness`
- `heat_delta` = new `heat` − old `heat`

This attributes ALL changes in the target territory to the player's action, which is an approximation (the engine's own systems also modify these values). Acceptable for MVP per SC-002 (80% threshold).

### 4. Idempotency Guard

Use database-level optimistic locking: `GameSession.objects.select_for_update().get(id=session_id)` inside a `transaction.atomic()` block. Set `status = "resolving"` before step, `status = "active"` after. Reject requests where `status != "active"`.

### 5. Endgame Detection

The `EndgameDetector` emits events with `event_type` matching the 3 conditions. After each tick, check `snapshot.events` for endgame event types. Display a modal with the outcome and set game status to "completed".

## Complexity Tracking

No constitution violations. No complexity justification needed.

## Post-Design Constitution Re-Check

| Principle | Status | Notes |
|-----------|--------|-------|
| II.6 State/Engine separation | PASS | All modifications in bridge layer. Engine `step()` unchanged. |
| II.8 Client as Presentation | PASS | Frontend only renders JSON and emits intents. No computation added. |
| V. 9 Player Verbs | PASS | Mapping table preserves all 9 constitutional verbs. |
| VII.1 UI Observes | PASS | Endgame modal is display-only. Resolve button emits intent. |

**Post-design gate: PASS.**
