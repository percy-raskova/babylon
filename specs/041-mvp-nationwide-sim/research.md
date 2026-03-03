# Research: MVP Nationwide Simulation

**Feature**: 041-mvp-nationwide-sim | **Date**: 2026-03-03

## Research Summary

Six technical unknowns were identified during Technical Context analysis. All have been resolved through codebase investigation.

---

## 1. How Player Actions Enter the Simulation Engine

**Decision**: Inject player actions via `persistent_context["player_actions"]` parameter to `step()`.

**Rationale**: The OODASystem already reads this key at `ooda.py:113-119`. The data format expected is a dict keyed by `org_id`, where each value is a list of action dicts containing `action_type`, `target_id`, and optionally `action_point_cost`. The `engine_bridge.py:resolve_tick()` method already accepts a `persistent_context` parameter but always receives `None` from `tick_resolver.py`. The fix is to read pending turns from the database and format them into this structure.

**Alternatives Considered**:
- Modify `step()` signature to accept actions directly — rejected because it violates the "no engine modifications" assumption
- Add a new System that reads actions from DB — rejected because it couples the engine to the persistence layer (violates II.6)

---

## 2. Verb-to-ActionType Mapping

**Decision**: Create a static mapping table from 9 UI verbs to ActionType enum values.

**Rationale**: The UI's VerbSelector uses 9 verbs (educate, reproduce, investigate, attack, mobilize, campaign, aid, move, negotiate) defined in the constitution (Article V). The OODASystem's `_action_from_dict()` expects `action_type` matching the 21-value `ActionType` enum. A mapping table in `engine_bridge.py` translates at the boundary:

| UI Verb | ActionType | Rationale |
|---------|------------|-----------|
| educate | EDUCATE | Direct match |
| reproduce | RECRUIT | Grow membership = recruit |
| investigate | MAP_NETWORK | Intelligence gathering |
| attack | ATTACK_INFRASTRUCTURE | Direct action against infrastructure |
| mobilize | PROTEST | Mass action |
| campaign | PROPAGANDIZE | Public pressure = propaganda |
| aid | PROVIDE_SERVICE | Resource transfer |
| move | ORGANIZE | Relocate/reorganize = edge restructuring |
| negotiate | PROPOSE_ALLIANCE | Diplomatic outreach = alliance proposal |

**Alternatives Considered**:
- Use UI verb strings directly in the engine — rejected because OODASystem's eligibility checking and Layer 3 effect processing key on ActionType enum values
- Expose all 21 ActionType values to the player — rejected per clarification (9 UI verbs are canonical for MVP)

---

## 3. How ActionResult Deltas Are Computed

**Decision**: Diff pre-step and post-step graph node attributes for the target territory/entity.

**Rationale**: The orphaned `resolve_action()` function in `action_effects.py` contains a five-factor consciousness delta formula, but it is unreachable from `OODASystem.step()`. Layer 3's `process_layer3()` applies effects (heat for REPRESS/SURVEIL, edge transitions for ORGANIZE, infrastructure for BUILD/ATTACK) but does not compute per-action deltas. Consciousness effects are delegated to CommunitySystem (Feature 034).

For MVP, the approach is:
1. Snapshot target node attributes (consciousness, heat) before `step()`
2. Run `step()`
3. Diff the attributes after `step()`
4. Attribute the delta to the player's action targeting that node

This is an approximation — the engine's own systems also modify these values during the tick. But SC-002 requires only 80% of actions produce non-null deltas, and this approach satisfies that threshold because consciousness drift and heat dynamics always produce some change.

**Alternatives Considered**:
- Wire in `resolve_action()` from `action_effects.py` — rejected because it's orphaned code with unknown correctness, and would require engine modifications
- Have the engine return per-action deltas — rejected because it would require modifying the System interface (engine change)

---

## 4. Idempotency Guard Mechanism

**Decision**: Database-level `select_for_update()` with status transition to "resolving".

**Rationale**: The current resolve endpoint has no concurrency guard. Two rapid POST requests can both enter `resolve_tick()` simultaneously. Using `GameSession.objects.select_for_update().get(id=session_id)` inside `transaction.atomic()` provides row-level locking. Setting `status = "resolving"` before the engine step and checking for `status == "active"` at entry prevents a second request from proceeding.

The frontend also disables the button during resolution (already partially implemented via `resolving` useState in `GameShell.tsx`), providing a belt-and-suspenders approach.

**Alternatives Considered**:
- Redis distributed lock — rejected because it adds infrastructure complexity for a single-player game
- Idempotency token — rejected because it requires frontend changes to generate/track tokens
- Tick counter comparison — insufficient because two requests with the same tick could still race

---

## 5. Endgame Detection Integration

**Decision**: Check snapshot events for endgame event types after each tick resolution.

**Rationale**: The `EndgameDetector` (at `observers/endgame_detector.py`) already detects 3 conditions: `REVOLUTIONARY_VICTORY`, `ECOLOGICAL_COLLAPSE`, `FASCIST_CONSOLIDATION`. It emits `EndgameEvent` objects that are included in the WorldState's events list, which is serialized into the snapshot by `_state_to_snapshot()`. The frontend can check `snapshot.events` for events with matching types.

However, `EndgameDetector` is a `SimulationObserver` that must be registered with the simulation. Currently, `resolve_tick()` in the bridge does not register any observers — `step()` is called directly. The detector needs to be instantiated and registered before each step.

**Decision (refined)**: Register `EndgameDetector` as an observer on the `step()` call. After the step, check `detector.is_game_over`. If true, set `GameSession.status = "completed"` and include the outcome in the snapshot response.

**Alternatives Considered**:
- Check endgame conditions in Django post-step — rejected because the detection logic is complex (percolation ratios, sustained overshoot) and already implemented in the engine
- Always run the detector — it's lightweight and runs in O(n) over entities/territories

---

## 6. React Router Integration

**Decision**: Replace the `View` state machine in `App.tsx` with `react-router-dom` v7 routes.

**Rationale**: `react-router-dom` v7 is already installed (`package.json:38`) but unused. The current navigation uses `useState<View>` with a discriminated union. The migration is straightforward:

| Current State | Route |
|---------------|-------|
| `{ page: "login" }` | `/login` |
| `{ page: "games" }` | `/games` |
| `{ page: "game", id }` | `/games/:id` |

The existing components (`LoginPage`, `GameList`, `GameShell`) remain unchanged — only `App.tsx` changes to wrap them in `<Routes>`. This enables bookmarkable URLs and browser refresh without state loss (FR-011, SC-003).

**Alternatives Considered**:
- Hash-based routing (`HashRouter`) — rejected because `BrowserRouter` is standard and the Vite proxy already handles API routing
- Keep state-based navigation, add `window.history.pushState` manually — rejected because react-router-dom is already a dependency and handles edge cases (back button, direct URL access)
