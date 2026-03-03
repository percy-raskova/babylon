# Data Model: MVP Nationwide Simulation

**Feature**: 041-mvp-nationwide-sim | **Date**: 2026-03-03

## Entity Overview

All entities below already exist in the codebase. This document captures their current schema and the modifications needed for Feature 041.

---

## 1. GameSession (Django ORM)

**Table**: `game_session` | **File**: `web/game/models.py` | **Managed**: `False` (schema owned by Feature 037)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | Auto-generated |
| player_id | Integer | FK → auth_user | Session owner |
| scenario | CharField(64) | nullable | Scenario key used at creation |
| current_tick | Integer | default=0 | Last committed tick |
| status | CharField(16) | default="active" | **Modified**: add "resolving" as transient state for idempotency |
| config_json | JSONField | nullable | SimulationConfig overrides |
| created_at | DateTimeField | auto_now_add | Creation timestamp |

**Status transitions**:
```
active → resolving → active       (tick resolution cycle)
active → completed                (endgame detected)
active → paused                   (player choice, future)
active → abandoned                (player choice, future)
```

**Modification for 041**: Use `status = "resolving"` as a transient guard during tick resolution. Not a schema change — the column already accepts any string up to 16 chars.

---

## 2. PlayerAction (Django ORM)

**Table**: `game_turn` | **File**: `web/game/models.py` | **Managed**: `False`

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | BigAutoField | PK | Auto-generated |
| session | FK(GameSession) | db_column="session_id" | Parent game |
| tick | Integer | | Turn submitted for |
| org_id | CharField(64) | | Organization performing the action |
| verb | CharField(16) | | **Validated**: must be one of 9 canonical verbs |
| action_type | CharField(32) | nullable | Engine ActionType (mapped from verb) |
| target_id | CharField(64) | nullable | Target entity/territory ID |
| target_community | CharField(32) | nullable | Target community type |
| params_json | JSONField | nullable | Additional parameters |
| submitted_at | DateTimeField | auto_now_add | Submission timestamp |
| resolved | BooleanField | default=False | Marked True after tick processing |

**Unique constraint**: `(session, tick, org_id)` — one action per org per tick.

**Validation rules (FR-003)**:
1. `org_id` must reference a PoliticalFaction with `is_player=True` in current game state
2. `verb` must be one of: educate, reproduce, investigate, attack, mobilize, campaign, aid, move, negotiate
3. `target_id` must reference an existing entity or territory in current game state (unless verb is "reproduce", which is self-targeted)

---

## 3. ActionResult (Django ORM)

**Table**: `action_result` | **File**: `web/game/models.py` | **Managed**: `False`

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | BigAutoField | PK | Auto-generated |
| session | FK(GameSession) | db_column="session_id" | Parent game |
| tick | Integer | | Tick this result belongs to |
| org_id | CharField(64) | | Organization that acted |
| action_type | CharField(32) | | Engine ActionType value |
| target_id | CharField(64) | nullable | Target entity/territory |
| target_community | CharField(32) | nullable | Target community |
| initiative_score | Float | | Org's initiative score for this tick |
| action_cost | Float | | Action point cost |
| success | Boolean | | Whether the action succeeded |
| consciousness_delta | Float | nullable | Change in consciousness at target |
| heat_delta | Float | nullable | Change in heat at target |
| details | JSONField | nullable | Additional result data |

**Creation**: Rows are created by `engine_bridge.py:resolve_tick()` after `step()` completes. For each submitted player action, one ActionResult row is written with computed deltas.

---

## 4. GameEventLog (Django ORM)

**Table**: `game_event_log` | **File**: `web/game/models.py` | **Managed**: `True`

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | BigAutoField | PK | Auto-generated |
| session_id | UUID | indexed | Game session reference |
| tick | Integer | | Tick the event occurred |
| event_type | CharField(64) | | Event type string |
| event_data | JSONField | nullable | Event payload |
| timestamp | DateTimeField | auto_now_add | When logged |

**Index**: `(session_id, tick)` named `idx_event_session_tick`

**Migration needed**: This is the only `managed=True` model in the game app. No `migrations/` directory exists. Must run `makemigrations game` to create initial migration including this table.

---

## 5. WorldState (Engine Pydantic Model)

**File**: `src/babylon/models/world_state.py` | **No modification needed**

The simulation engine's core state model. Serialized to/from PostgreSQL graph via `to_graph()`/`from_graph()`. Contains:

| Field | Type | Role in Feature 041 |
|-------|------|---------------------|
| tick | int | Incremented by `step()` |
| entities | dict[str, SocialClass] | Target for consciousness delta computation |
| territories | dict[str, Territory] | Target for heat delta computation |
| organizations | dict[str, Organization] | Source for org validation (is_player check) |
| institutions | dict[str, Institution] | Read-only for feature 041 |
| relationships | list[Relationship] | Read-only for feature 041 |
| economy | EconomyState | Read-only for feature 041 |
| events | list[Event] | Checked for endgame events post-step |

---

## 6. Verb-to-ActionType Mapping (New, in engine_bridge.py)

Not a persistent entity — a static mapping table used at the Django/engine boundary.

| UI Verb (string) | ActionType (enum) | Constitution Reference |
|-------------------|-------------------|----------------------|
| "educate" | ActionType.EDUCATE | V. Build Org |
| "reproduce" | ActionType.RECRUIT | V. Build Org |
| "investigate" | ActionType.MAP_NETWORK | V. Build Org |
| "attack" | ActionType.ATTACK_INFRASTRUCTURE | V. Project Power |
| "mobilize" | ActionType.PROTEST | V. Project Power |
| "campaign" | ActionType.PROPAGANDIZE | V. Project Power |
| "aid" | ActionType.PROVIDE_SERVICE | V. Manage Resources |
| "move" | ActionType.ORGANIZE | V. Manage Resources |
| "negotiate" | ActionType.PROPOSE_ALLIANCE | V. Manage Resources |

---

## Relationships

```
GameSession 1──* PlayerAction     (session_id FK)
GameSession 1──* ActionResult     (session_id FK)
GameSession 1──* GameEventLog     (session_id, no FK constraint)
PlayerAction ···> ActionResult    (matched by session+tick+org_id, no FK)
```

PlayerAction and ActionResult are correlated by `(session_id, tick, org_id)` but have no formal foreign key between them. This is by design — ActionResult rows are created by the engine bridge after step(), not by the API action submission flow.
