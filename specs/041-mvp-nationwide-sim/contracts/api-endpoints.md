# API Contracts: MVP Nationwide Simulation

**Feature**: 041-mvp-nationwide-sim | **Date**: 2026-03-03

All endpoints require Django session authentication. All responses use the standard envelope:
```json
{ "status": "ok"|"error", "data": <payload>, "message": "<optional>" }
```

---

## Existing Endpoints (modifications noted)

### POST /api/games/{id}/actions/

Submit a player action for the current tick.

**Request**:
```json
{
  "org_id": "political_faction_1",
  "verb": "educate",
  "target_id": "8428309bfffffff",
  "params_json": null
}
```

**Validation (FR-003 — NEW)**:
1. `org_id` must reference a PoliticalFaction with `is_player=True` in current game state → 403 if not
2. `verb` must be one of: `educate`, `reproduce`, `investigate`, `attack`, `mobilize`, `campaign`, `aid`, `move`, `negotiate` → 400 if invalid
3. `target_id` must reference an existing entity or territory in current game state → 400 if not found
4. `target_id` not required when `verb` is `reproduce` (self-targeted)
5. One action per org per tick (existing UniqueConstraint) → 409 if duplicate

**Success Response** (201):
```json
{
  "status": "ok",
  "data": { "turn_id": 42 }
}
```

**Error Responses**:
- 400: Invalid verb or missing/invalid target
- 403: Organization not controllable by player
- 404: Game not found or not owned by user
- 409: Action already submitted for this org this tick

---

### POST /api/games/{id}/resolve/

Resolve the current tick — run one simulation step.

**Request**: Empty body.

**Modifications (FR-001, FR-002, FR-004 — NEW)**:
1. Acquires row lock on GameSession via `select_for_update()`
2. Rejects if `status != "active"` (idempotency guard) → 409
3. Sets `status = "resolving"` during engine step
4. Reads pending PlayerAction rows and injects into engine `step()` via `persistent_context["player_actions"]`
5. After step: computes per-action deltas, writes ActionResult rows
6. Checks for endgame events; if detected, sets `status = "completed"`
7. Sets `status = "active"` (or "completed") and commits

**Success Response** (200):
```json
{
  "status": "ok",
  "data": {
    "session_id": "uuid",
    "tick": 5,
    "entities": [...],
    "territories": [...],
    "organizations": [...],
    "institutions": [...],
    "edges": [...],
    "economy": {...},
    "events": [
      { "type": "ORGANIZATIONAL_ACTION", "tick": 5, "data": {...} }
    ],
    "endgame": null
  },
  "tick": 5,
  "session_id": "uuid"
}
```

**Endgame Response** (200, when endgame detected):
```json
{
  "status": "ok",
  "data": {
    "...snapshot fields...",
    "endgame": {
      "outcome": "REVOLUTIONARY_VICTORY",
      "tick": 42,
      "summary": "Solidarity percolation exceeded threshold..."
    }
  },
  "tick": 42,
  "session_id": "uuid"
}
```

**Error Responses**:
- 404: Game not found or not owned by user
- 400: Game not in "active" status
- 409: Tick already resolving (concurrent request blocked)
- 500: Engine error (tick rolled back, error toast shown to player)

---

### GET /api/games/{id}/results/{tick}/

Retrieve action results for a specific tick. **No modifications needed** — already exists.

**Response** (200):
```json
{
  "status": "ok",
  "data": [
    {
      "org_id": "political_faction_1",
      "action_type": "EDUCATE",
      "target_id": "8428309bfffffff",
      "initiative_score": 7.3,
      "action_cost": 1.0,
      "success": true,
      "consciousness_delta": 0.023,
      "heat_delta": 0.0,
      "details": null
    }
  ]
}
```

---

### GET /api/games/{id}/state/

Get current game state snapshot. **No modifications needed** — already exists.

---

### GET /api/games/{id}/actions/

Get pending (unresolved) actions for current tick. **No modifications needed** — already exists.

---

### GET /api/games/{id}/actions/available/

Get available actions for all organizations. **Modification**: filter to only return PoliticalFaction orgs with `is_player=True`.

---

## New Endpoints

### GET /api/scenarios/

List available game scenarios (FR-013).

**Response** (200):
```json
{
  "status": "ok",
  "data": [
    {
      "key": "us_nationwide",
      "name": "United States — Nationwide",
      "description": "Full CONUS simulation with ~1,100 H3 territories",
      "territory_count": 1100
    },
    {
      "key": "minimal_test",
      "name": "Minimal Test",
      "description": "Small scenario for testing with 4 territories",
      "territory_count": 4
    }
  ]
}
```

### POST /api/games/

Create a new game. **Modification**: accept optional `scenario` field.

**Request**:
```json
{
  "scenario": "us_nationwide"
}
```

Default scenario is `us_nationwide` if not provided.

**Response** (201):
```json
{
  "status": "ok",
  "data": {
    "id": "uuid",
    "scenario": "us_nationwide",
    "current_tick": 0,
    "status": "active",
    "created_at": "2026-03-03T16:00:00Z"
  }
}
```

---

## Frontend Routes (FR-011)

| Route | Component | Description |
|-------|-----------|-------------|
| `/login` | `LoginPage` | Authentication form |
| `/games` | `GameList` | Game list + create game |
| `/games/:id` | `GameShell` | Full game view |
| `*` | Redirect → `/games` | Catch-all for authenticated users |
