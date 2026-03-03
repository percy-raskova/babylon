# Quickstart: MVP Nationwide Simulation

**Feature**: 041-mvp-nationwide-sim | **Date**: 2026-03-03

## Prerequisites

- Running PostgreSQL instance with game database
- Python 3.12+ with Poetry
- Node.js 20+ with npm
- Mise task runner (recommended)

## Development Setup

```bash
# Ensure you're on the feature branch
git checkout 041-mvp-nationwide-sim

# Install dependencies
poetry install
cd web/frontend && npm install && cd ../..

# Start dev servers
mise run web:dev          # Django (8000) + Vite (5173) as daemons
mise run web:status       # Verify both running
```

## Implementation Order

Work through phases sequentially. Each phase has clear exit criteria.

### Phase 1: Defect Fixes

Start here — these unblock everything else.

1. **Import boundary** (`web/game/apps.py`):
   - Move `PostgresRuntime` initialization into `engine_bridge.py`
   - `apps.py` should call a bridge function, not import engine internals
   - Verify: `poetry run pytest tests/unit/web/test_import_boundary.py`

2. **GameEventLog migration** (`web/game/migrations/`):
   - `cd web && python manage.py makemigrations game && python manage.py migrate`
   - Verify: `python manage.py showmigrations game`

3. **TypeScript fix** (`web/frontend/src/components/HexMap.tsx`):
   - Add null/undefined guard at the error location
   - Verify: `cd web/frontend && npx tsc --noEmit && npm run build`

### Phase 2: Action Integration

The core game loop. Work in `web/game/engine_bridge.py` primarily.

1. **Read pending actions**: In `resolve_tick()`, before calling `step()`, call `self.get_pending_actions(session_id, state.tick)` to get submitted PlayerAction rows.

2. **Format for engine**: Transform the list of action dicts into:
   ```python
   player_actions = {}
   for action in pending:
       player_actions.setdefault(action["org_id"], []).append({
           "action_type": VERB_TO_ACTION_TYPE[action["verb"]].value,
           "target_id": action.get("target_id", action["org_id"]),
           "org_id": action["org_id"],
           "action_point_cost": 1,
       })
   persistent_context = {"player_actions": player_actions}
   ```

3. **Snapshot pre-step state**: Before calling `step()`, capture target node attributes:
   ```python
   pre_step = {}
   for action in pending:
       tid = action.get("target_id")
       if tid and tid in graph.nodes:
           pre_step[tid] = {
               "consciousness": graph.nodes[tid].get("class_consciousness", 0.0),
               "heat": graph.nodes[tid].get("heat", 0.0),
           }
   ```

4. **Persist ActionResults**: After `step()` and before `persist_tick()`, compute deltas and write results:
   ```python
   new_graph = new_state.to_graph()
   for action in pending:
       tid = action.get("target_id")
       pre = pre_step.get(tid, {})
       post_consciousness = new_graph.nodes[tid].get("class_consciousness", 0.0) if tid in new_graph.nodes else 0.0
       post_heat = new_graph.nodes[tid].get("heat", 0.0) if tid in new_graph.nodes else 0.0
       # Write ActionResult row via persistence layer or Django ORM
   ```

5. **Validation** (`web/game/api.py`): Add checks before `bridge.submit_action()`:
   - Load current game state snapshot
   - Verify org_id exists and is PoliticalFaction with is_player
   - Verify verb is in canonical set
   - Verify target_id exists (unless self-targeted verb)

6. **Idempotency**: Wrap resolve in `transaction.atomic()` + `select_for_update()`.

### Phase 3: Frontend

Mostly wiring existing components to new data.

1. **React Router**: Replace `View` state in `App.tsx` with `BrowserRouter` + `Routes`
2. **Endgame modal**: Check `snapshot.endgame` or `snapshot.events` for endgame types after resolve
3. **Org filtering**: In `ActionComposer.tsx`, filter orgs to `is_player === true`
4. **Resolve button**: Already has `resolving` state — ensure it disables both buttons in `TopBar` and `ActionComposer`

### Phase 4: Scenarios

1. **Backend**: Add `GET /api/scenarios/` endpoint listing available scenario factory functions
2. **Frontend**: Add scenario dropdown to game creation in `GameList.tsx`

### Phase 5: Testing

1. **Django tests**: Create `web/game/tests/` with pytest fixtures using test DB
2. **Verify**: `mise run check` (engine), `mise run web:check` (frontend)
3. **E2E**: Update Playwright tests to match current UI

## Verification Commands

```bash
# Phase 1 verification
poetry run pytest tests/unit/web/test_import_boundary.py -v
cd web/frontend && npm run build
cd web && python manage.py showmigrations game

# Phase 2 verification
poetry run pytest web/game/tests/ -v
# Manual: submit action via API, resolve tick, check action_result table

# Phase 3 verification
cd web/frontend && npm run check
# Manual: navigate to /games/UUID, refresh, verify state persists

# Phase 5 verification
mise run check                    # Full engine + lint gate
mise run web:check                # Frontend quality gate
cd web/frontend && npx playwright test  # E2E
```

## Key Files Reference

| File | Role |
|------|------|
| `web/game/engine_bridge.py` | **Primary modification target** — action wiring, result persistence |
| `web/game/api.py` | Validation, idempotency, scenario endpoint |
| `web/game/tick_resolver.py` | Transaction wrapper |
| `web/game/apps.py` | Import boundary fix |
| `web/frontend/src/App.tsx` | React Router |
| `web/frontend/src/components/layout/GameShell.tsx` | Endgame modal |
| `web/frontend/src/components/action/ActionComposer.tsx` | Org filtering |
| `src/babylon/engine/systems/ooda.py:113-119` | Engine injection point (read-only) |
| `src/babylon/ooda/layer3.py` | Verb→effect mapping (read-only) |
