# Feature Specification: Engine Frontend Integration

**Feature Branch**: `051-engine-frontend-integration`
**Created**: 2026-04-13
**Status**: Draft
**Input**: User description: "Replace the MSW mock layer with the real Babylon simulation engine for the Wayne County vertical slice, while preserving the exact HTTP contracts consumed by the mounted GameShell frontend."

## Source Integrity Note

The repository path named in the request, [../../docs/043_wiring_verification_report.md](../../docs/043_wiring_verification_report.md), is a simplex wiring report and does not contain frontend HTTP contract evidence. It cannot be used as the authoritative source for this feature's falsifiability criteria.

The authoritative contract source for this specification is [../../docs/043_frontend_mock_wiring_audit.md](../../docs/043_frontend_mock_wiring_audit.md), specifically Sections 1.1, 1.4, 2.1, 5.1, 5.2, and 5.3. Every contract requirement below is derived from that audit so the spec remains verifiable against the current mounted frontend rather than an unrelated report.

## Scope Control

### In Scope: Adapter-Owned Game Routes

These routes are in scope because the mounted runtime or its `fetchState()` pipeline calls them directly.

| Route | Method | Frontend caller | Required adapter behavior |
| --- | --- | --- | --- |
| `/api/games/:id/state/` | `GET` | `useGameStore.fetchState()` | Serialize real engine `WorldState` to exact `GameSnapshot` envelope |
| `/api/games/:id/actions/available/` | `GET` | `useGameStore.fetchState()` | Normalize engine action availability into flat `AvailableAction[]` |
| `/api/games/:id/map/` | `GET` | `useGameStore.fetchState()` | Return a valid `FeatureCollection` envelope so `Promise.all()` succeeds |
| `/api/games/:id/actions/preview/` | `POST` | `ActionPreview.tsx` raw `fetch()` | Flatten preview output to exact `ActionPreviewResult` |
| `/api/games/:id/actions/:verb/` | `POST` | `useGameStore.submitAction()` | Accept flat frontend body and enqueue engine action |
| `/api/games/:id/resolve/` | `POST` | `useGameStore.resolveTick()` | Advance engine one tick and return top-level `tick` |
| `/api/games/:id/results/:tick/` | `GET` | `useGameStore.resolveTick()` | Return exact `ActionResultData[]` for the resolved tick |

### In Scope: Existing Compatibility Routes, No Contract Changes Required

These routes are part of Audit Section 5.1 and remain valid application prerequisites, but this feature does not redefine their contracts.

| Route | Method | Status |
| --- | --- | --- |
| `/accounts/whoami/` | `GET` | Retain existing contract |
| `/accounts/login/` | `GET` | Retain existing contract |
| `/accounts/login/` | `POST` | Retain existing contract |
| `/accounts/logout/` | `POST` | Retain existing contract |
| `/api/scenarios/` | `GET` | Retain existing contract |
| `/api/games/` | `GET` | Retain existing contract |
| `/api/games/` | `POST` | Retain existing contract |

### Deferred / Out of Scope

These routes are explicitly deferred because Audit Section 5.4 identifies them as unused by the mounted runtime, and Article VI forbids widening scope beyond the current frontend contract.

| Route | Method | Status | Reason |
| --- | --- | --- | --- |
| `/api/games/:id/summary/` | `GET` | Deferred / Out of Scope | Mounted frontend does not call it |
| `/api/games/:id/timeseries/` | `GET` | Deferred / Out of Scope | Mounted frontend computes charts from `tickSummaries` |
| `/api/games/:id/economy/` | `GET` | Deferred / Out of Scope | Not called by mounted frontend |
| `/api/games/:id/communities/` | `GET` | Deferred / Out of Scope | Not called by mounted frontend |
| `/api/games/:id/organizations/` | `GET` | Deferred / Out of Scope | Not called by mounted frontend |
| `/api/games/:id/edges/` | `GET` | Deferred / Out of Scope | Not called by mounted frontend |
| `/api/games/:id/state-apparatus/` | `GET` | Deferred / Out of Scope | Not called by mounted frontend |
| `/api/games/:id/journal/` | `GET` | Deferred / Out of Scope | Not called by mounted frontend |
| `/api/games/:id/alerts/` | `GET` | Deferred / Out of Scope | Not called by mounted frontend |
| `/api/games/:id/node/:node_id/` | `GET` | Deferred / Out of Scope | Inspector is snapshot-driven |
| `/api/games/:id/org/:org_id/` | `GET` | Deferred / Out of Scope | Inspector is snapshot-driven |
| `/api/games/:id/community/:hyperedge_id/` | `GET` | Deferred / Out of Scope | Inspector is snapshot-driven |
| `/api/games/:id/edge/:edge_id/` | `GET` | Deferred / Out of Scope | Graph view is snapshot-driven |
| `/api/games/:id/hex/:h3_index/` | `GET` | Deferred / Out of Scope | Inspector is snapshot-driven |
| `/api/games/:id/actions/` | `GET` | Deferred / Out of Scope | Mounted frontend does not read pending actions |
| `/api/games/:id/actions/:action_id/` | `DELETE` | Deferred / Out of Scope | Mounted frontend does not cancel pending actions |
| `/api/games/:id/v2/world/` | `GET` | Deferred / Out of Scope | No mounted UI imports the v2 dialectic views |
| `/api/games/:id/v2/dialectics/:dialectic_id/` | `GET` | Deferred / Out of Scope | No mounted UI imports the v2 dialectic views |
| `/api/games/:id/verbs/*` | `GET`, `POST` | Deferred / Out of Scope | Current frontend posts to `/actions/:verb/`, not `/verbs/:verb/` |

## Assumptions

- The mounted runtime remains [../../web/frontend/src/components/layout/GameShell.tsx](../../web/frontend/src/components/layout/GameShell.tsx) with no frontend contract rewrite.
- Wayne County is the only scenario required for this feature.
- The engine remains the material source of truth. The adapter reshapes engine outputs to match the frontend contract rather than changing the frontend.
- The existing [../../web/game/engine_bridge.py](../../web/game/engine_bridge.py) remains the raw engine integration surface. This feature adds a compatibility adapter around it where shapes diverge.
- `useGameStore.fetchState()` continues to issue `Promise.all()` requests to `/state/`, `/actions/available/`, and `/map/`; therefore all three routes must return valid envelopes even if the mounted shell ignores `available` and `mapData`.

## User Scenarios & Testing

### User Story 1 - Hydrate GameShell From Real Engine State (Priority: P1)

The player opens a Wayne County game route. The frontend polls `/state/`, `/actions/available/`, and `/map/` in parallel. The backend must satisfy all three calls with real engine-backed data or compatibility envelopes so the mounted shell can render without MSW.

**Why this priority**: `GameShell` cannot mount without the state pipeline, and `fetchState()` will fail if any of its three requests break contract.

**Independent Test**: Create a Wayne County game, hit `/api/games/:id/state/`, `/api/games/:id/actions/available/`, and `/api/games/:id/map/` with the same game id, then load `/games/:id` and verify the shell renders without frontend changes.

**Acceptance Scenarios**:

1. **AC-001**: Given an active Wayne County game, when the frontend calls `GET /api/games/:id/state/`, then the response matches `ApiResponse<GameSnapshot>` exactly enough for `useGameStore.fetchState()` to assign `snapshot` and `tickSummaries` without any transform outside the store. Maps to `CR-001`, `CR-002`.
1. **AC-002**: Given the same request cycle, when the frontend calls `GET /api/games/:id/actions/available/`, then the response is a flat `ApiResponse<AvailableAction[]>`, not the nested per-org shape currently emitted by `EngineBridge.get_available_actions()`. Maps to `CR-003`.
1. **AC-003**: Given the same request cycle, when the frontend calls `GET /api/games/:id/map/`, then the response is a valid `ApiResponse<FeatureCollection>` so the `Promise.all()` in `fetchState()` succeeds even though mounted `GameShell` does not consume `mapData`. Maps to `CR-004`.

______________________________________________________________________

### User Story 2 - Preview Action Effects Without Mutating State (Priority: P1)

The player reaches the preview step in `ActionComposer`. `ActionPreview.tsx` posts a raw JSON body to `/api/games/:id/actions/preview/` and expects a flat `ActionPreviewResult` under `json.data`.

**Why this priority**: The preview component bypasses the shared API client and casts `json.data` directly. Any nested wrapper or renamed field breaks the mounted action flow immediately.

**Independent Test**: Submit `{"org_id":"ORG001","verb":"educate","target_id":"C001"}` to `/api/games/:id/actions/preview/` and verify the response body can be assigned directly to `ActionPreviewResult`.

**Acceptance Scenarios**:

1. **AC-004**: Given a preview request from `ActionPreview.tsx`, when the backend returns, then `json.data` is exactly a flat `ActionPreviewResult` with `estimated_consciousness_delta`, `estimated_heat_delta`, `action_point_cost`, `success_probability`, `affected_territory_ids`, and `warnings`. Maps to `CR-005`.

______________________________________________________________________

### User Story 3 - Submit a Flat Frontend Action Body (Priority: P1)

The player confirms an action. `useGameStore.submitAction()` strips `verb` into the URL path and posts the remaining flat body to `/api/games/:id/actions/:verb/`.

**Why this priority**: The mounted frontend does not call the `/verbs/*` endpoints and will not be rewritten in this feature.

**Independent Test**: Submit `{ "org_id": "ORG001", "target_id": "C001" }` to `/api/games/:id/actions/educate/` and verify that the engine queues a player action without requiring a `/verbs/educate/` route or a nested `params` wrapper.

**Acceptance Scenarios**:

1. **AC-005**: Given a POST to `/api/games/:id/actions/:verb/` with the flat frontend body, when the route parses the request, then the adapter maps it into the engine submission call and returns the standard ok envelope without forcing the frontend to call `/verbs/:verb/`. Maps to `CR-006`, `CR-007`.

______________________________________________________________________

### User Story 4 - Resolve Exactly One Tick (Priority: P1)

The player clicks Resolve Tick. The frontend only requires an ok envelope with a top-level `tick` integer, then it immediately re-fetches state and results.

**Why this priority**: `useGameStore.resolveTick()` depends on `res.tick` from the envelope. If the tick is absent or stale, results fetching breaks.

**Independent Test**: Record the current tick, POST `/api/games/:id/resolve/`, then verify the returned top-level `tick` is `previous_tick + 1` and that subsequent `/state/` returns the same tick.

**Acceptance Scenarios**:

1. **AC-006**: Given an active Wayne County game, when the frontend calls `POST /api/games/:id/resolve/`, then the backend advances the engine by exactly one tick and returns an ok envelope with the new tick at the top level. Maps to `CR-008`.

______________________________________________________________________

### User Story 5 - Fetch Tick Results For The Resolved Turn (Priority: P1)

After tick resolution, the frontend requests `/api/games/:id/results/:tick/` and passes the returned array into `TickResults.tsx`.

**Why this priority**: This is the only mounted path that surfaces action outcomes back to the player.

**Independent Test**: Submit at least one action, resolve one tick, then GET `/api/games/:id/results/:tick/` and verify the array fields exactly match `ActionResultData[]`.

**Acceptance Scenarios**:

1. **AC-007**: Given a tick that resolved after at least one submitted action, when the frontend calls `GET /api/games/:id/results/:tick/`, then the backend returns `ApiResponse<ActionResultData[]>` with the exact field names consumed by `TickResults.tsx`. Maps to `CR-009`.

## Acceptance Criteria to Contract Mapping

| Acceptance Criterion | Route | Contract Requirement(s) | Primary audit source |
| --- | --- | --- | --- |
| `AC-001` | `GET /api/games/:id/state/` | `CR-001`, `CR-002` | [../../docs/043_frontend_mock_wiring_audit.md](../../docs/043_frontend_mock_wiring_audit.md) Section 5.1 `GET /state/`, Section 5.2 `GameSnapshot` |
| `AC-002` | `GET /api/games/:id/actions/available/` | `CR-003` | [../../docs/043_frontend_mock_wiring_audit.md](../../docs/043_frontend_mock_wiring_audit.md) Section 2.1 `fetchState()`, Section 5.1 `GET /actions/available/`, Section 5.3 nested engine mismatch |
| `AC-003` | `GET /api/games/:id/map/` | `CR-004` | [../../docs/043_frontend_mock_wiring_audit.md](../../docs/043_frontend_mock_wiring_audit.md) Section 2.1 `fetchState()`, Section 5.1 `GET /map/` |
| `AC-004` | `POST /api/games/:id/actions/preview/` | `CR-005` | [../../docs/043_frontend_mock_wiring_audit.md](../../docs/043_frontend_mock_wiring_audit.md) Section 5.1 `POST /actions/preview/`, Section 5.3 preview mismatch |
| `AC-005` | `POST /api/games/:id/actions/:verb/` | `CR-006`, `CR-007` | [../../docs/043_frontend_mock_wiring_audit.md](../../docs/043_frontend_mock_wiring_audit.md) Section 2.1 `submitAction()`, Section 5.1 `POST /actions/:verb/`, Section 5.3 `/verbs/*` mismatch |
| `AC-006` | `POST /api/games/:id/resolve/` | `CR-008` | [../../docs/043_frontend_mock_wiring_audit.md](../../docs/043_frontend_mock_wiring_audit.md) Section 2.1 `resolveTick()`, Section 5.1 `POST /resolve/` |
| `AC-007` | `GET /api/games/:id/results/:tick/` | `CR-009` | [../../docs/043_frontend_mock_wiring_audit.md](../../docs/043_frontend_mock_wiring_audit.md) Section 2.1 results fetch, Section 5.1 `GET /results/:tick/` |

## Contract Requirements

### CR-001 - State Route Envelope

The system MUST expose `GET /api/games/:id/state/` with the envelope:

```json
{
  "status": "ok",
  "data": { "...": "GameSnapshot" },
  "tick": 7,
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

The top-level `tick` MUST equal `data.tick`.

### CR-002 - Exact `GameSnapshot` Payload Shape

The `data` object for `GET /api/games/:id/state/` MUST match this shape exactly:

```json
{
  "tick": 7,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "entities": [
    {
      "id": "C001",
      "name": "Industrial Proletariat",
      "role": "worker",
      "wealth": 12.5,
      "consciousness": 0.42,
      "national_identity": 0.3,
      "agitation": 0.18,
      "organization": 0.61,
      "repression": 0.22,
      "p_acquiescence": 0.54,
      "p_revolution": 0.29,
      "subsistence": 10.0,
      "population": 125000,
      "inequality": 0.67,
      "active": true
    }
  ],
  "territories": [
    {
      "id": "wayne_core",
      "name": "Detroit Core",
      "h3_index": "882a100d67fffff",
      "heat": 0.44,
      "sector_type": "industrial",
      "territory_type": "urban",
      "profile": "high_profile",
      "rent_level": 0.58,
      "population": 95000,
      "under_eviction": false,
      "biocapacity": 0.21,
      "host_id": null,
      "occupant_id": null
    }
  ],
  "organizations": [
    {
      "id": "ORG001",
      "name": "Wayne County Cadre",
      "org_type": "political_faction",
      "class_character": "proletarian",
      "cohesion": 0.73,
      "cadre_level": 0.64,
      "budget": 8.0,
      "heat": 0.17,
      "territory_ids": ["wayne_core"],
      "consciousness_tendency": "revolutionary",
      "vanguard": {
        "cadre_labor": 6.0,
        "sympathizer_labor": 18.0,
        "reputation": 0.4,
        "budget": 8.0,
        "heat": 0.17,
        "max_cadre_labor": 10.0,
        "max_sympathizer_labor": 24.0
      }
    }
  ],
  "institutions": [
    {
      "id": "INST001",
      "name": "City Administration",
      "apparatus_type": "municipal",
      "social_function": "governance",
      "class_inscription": "bourgeois",
      "legitimacy": 0.55,
      "budget": 25.0,
      "housed_org_ids": ["ORG001"],
      "territory_ids": ["wayne_core"],
      "hegemonic_fraction": "liberal_technocratic",
      "liberal_technocratic": 0.62,
      "revanchist_fascist": 0.11,
      "institutionalist_bonapartist": 0.27
    }
  ],
  "edges": [
    {
      "source_id": "C001",
      "target_id": "wayne_core",
      "edge_type": "TENANCY",
      "value_flow": 0.2,
      "tension": 0.34,
      "solidarity_strength": 0.12
    }
  ],
  "economy": {},
  "events": [
    {
      "type": "EXTRACTION",
      "tick": 7,
      "data": {}
    }
  ],
  "endgame": {
    "outcome": "REVOLUTIONARY_VICTORY",
    "tick": 52,
    "summary": "optional when terminal state is reached"
  },
  "traps": {
    "liberal": {
      "trap_type": "liberal",
      "severity": "none",
      "score": 0.0,
      "indicators": [],
      "ticks_at_moderate": 0
    },
    "ultra_left": {
      "trap_type": "ultra_left",
      "severity": "none",
      "score": 0.0,
      "indicators": [],
      "ticks_at_moderate": 0
    },
    "rightist": {
      "trap_type": "rightist",
      "severity": "none",
      "score": 0.0,
      "indicators": [],
      "ticks_at_moderate": 0
    },
    "active_trap": null,
    "game_over_trap": null
  }
}
```

`endgame` and `traps` are optional at the JSON level but, when present, MUST use the field names above. No nested `snapshot` wrapper is permitted.

### CR-003 - Flat Available Actions Compatibility Route

The system MUST expose `GET /api/games/:id/actions/available/` with the envelope:

```json
{
  "status": "ok",
  "data": [
    {
      "org_id": "ORG001",
      "verb": "educate",
      "action_type": "EDUCATE",
      "targets": ["C001", "C004"],
      "cost": 1.0
    }
  ],
  "tick": 7,
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

The adapter MUST flatten any nested engine output such as `{ "actions": { "ORG001": [...] } }` into `AvailableAction[]` before returning it.

### CR-004 - Map Compatibility Route

The system MUST expose `GET /api/games/:id/map/` with the envelope:

```json
{
  "status": "ok",
  "data": {
    "type": "FeatureCollection",
    "features": []
  },
  "tick": 7,
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Additional `metadata` and populated `features[*].properties` are permitted, but `data.type` MUST be `FeatureCollection` and `data.features` MUST be an array.

### CR-005 - Flat Preview Contract

The system MUST expose `POST /api/games/:id/actions/preview/` accepting this request body:

```json
{
  "org_id": "ORG001",
  "verb": "educate",
  "target_id": "C001"
}
```

The response MUST be:

```json
{
  "status": "ok",
  "data": {
    "estimated_consciousness_delta": 0.05,
    "estimated_heat_delta": 0.01,
    "action_point_cost": 1.0,
    "success_probability": 0.8,
    "affected_territory_ids": ["wayne_core"],
    "warnings": []
  },
  "tick": 7,
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

No nested `preview` object is permitted under `data`.

### CR-006 - Flat Submission Compatibility Route

The system MUST expose `POST /api/games/:id/actions/:verb/` accepting the flat frontend request body:

```json
{
  "org_id": "ORG001",
  "target_id": "C001"
}
```

Verb-specific extra keys are permitted as additional top-level fields, for example:

```json
{
  "org_id": "ORG001",
  "target_id": "C001",
  "mode": "targeted",
  "specific_target": "INST001"
}
```

The frontend MUST NOT be required to send `verb` in the request body or to wrap parameters under `params`.

### CR-007 - Submission Response and Queue Semantics

On successful submission, the system MUST enqueue the action in engine-backed persistence and return:

```json
{
  "status": "ok",
  "data": {
    "turn_id": 12
  },
  "tick": 7,
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

On validation or affordability failure, the system MUST return:

```json
{
  "status": "error",
  "data": null,
  "message": "Human-readable rejection reason"
}
```

The adapter MUST translate the compatibility route into the engine submission call and MUST NOT require the frontend to switch to `/api/games/:id/verbs/:verb/`.

### CR-008 - Resolve Route Tick Contract

The system MUST expose `POST /api/games/:id/resolve/` and return:

```json
{
  "status": "ok",
  "data": {
    "resolved": true
  },
  "tick": 8,
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

The top-level `tick` MUST be the new tick after engine advancement. The frontend does not require any other field from this route.

### CR-009 - Results Route Exact Shape

The system MUST expose `GET /api/games/:id/results/:tick/` and return:

```json
{
  "status": "ok",
  "data": [
    {
      "org_id": "ORG001",
      "action_type": "educate",
      "target_id": "C001",
      "initiative_score": 0.75,
      "action_cost": 1.0,
      "success": true,
      "consciousness_delta": 0.05,
      "heat_delta": 0.01,
      "details": {}
    }
  ],
  "tick": 8,
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

The array MUST be derived from persisted action outcomes for that tick. Field names MUST match `ActionResultData` exactly.

### CR-010 - Scope Gate Enforcement

The implementation MUST NOT introduce any frontend dependency on `/api/games/:id/verbs/*` or on any route marked Deferred / Out of Scope in this specification. The compatibility surface for this feature is limited to the seven adapter-owned routes listed in the In Scope table above.

## Adapter Responsibilities

| Adapter input | Adapter output | Required normalization |
| --- | --- | --- |
| `EngineBridge.get_snapshot(session_id)` returning engine-native snapshot dict | `GameSnapshot` inside standard envelope | Normalize field names and optional sections so they match frontend interfaces exactly |
| `EngineBridge.get_available_actions(session_id)` returning nested per-org action dict | Flat `AvailableAction[]` inside standard envelope | Flatten nested org buckets into a single array |
| `EngineBridge.get_map_snapshot(session_id, ...)` returning engine-native `FeatureCollection` | Standard `ApiResponse<FeatureCollection>` | Preserve valid `FeatureCollection` shape; do not return non-GeoJSON wrappers |
| `EngineBridge.preview_action(...)` or `MockEngineBridge.preview_action(...)` | Flat `ActionPreviewResult` inside standard envelope | Strip any nested `preview` wrapper and rename fields if necessary |
| `EngineBridge.submit_action(...)` | Standard ok/error envelope for `/actions/:verb/` | Accept flat frontend body, route verb from URL, map extra top-level keys into engine params |
| `EngineBridge.resolve_tick(session_id)` | Standard resolve envelope with top-level new tick | Guarantee top-level `tick` is authoritative and current |
| Persisted `ActionResult` rows | `ActionResultData[]` inside standard envelope | Serialize exact frontend field names with no nested wrappers |

## Key Entities

- **EngineFrontendAdapter**: Backend compatibility layer that translates between real engine outputs and the mounted frontend's HTTP contract.
- **GameSnapshot**: Exact frontend state document consumed by `useGameStore.fetchState()` and passed through `GameShell`.
- **ActionPreviewResult**: Flat preview payload consumed directly by `ActionPreview.tsx` from `json.data`.
- **AvailableAction**: Flat action availability row used by `fetchState()` compatibility hydration, even though mounted `GameShell` does not currently render it.
- **ActionResultData**: Tick-scoped action outcome row consumed by `TickResults.tsx`.

## Success Criteria

- **SC-001**: A Wayne County game can be created and opened without MSW, and the mounted `GameShell` renders successfully using real backend responses.
- **SC-002**: `GET /api/games/:id/state/` returns a `GameSnapshot` that passes the frontend TypeScript contract with no frontend-side normalization.
- **SC-003**: `POST /api/games/:id/actions/preview/` returns a flat `ActionPreviewResult` under `data` for all 9 constitutional verbs.
- **SC-004**: `POST /api/games/:id/actions/:verb/` accepts the flat frontend body and creates an engine-backed queued action without requiring `/verbs/*` endpoints.
- **SC-005**: `POST /api/games/:id/resolve/` advances exactly one tick and returns the new tick at the envelope top level.
- **SC-006**: `GET /api/games/:id/results/:tick/` returns persisted `ActionResultData[]` rows for the resolved tick.
- **SC-007**: All routes listed in the Deferred / Out of Scope table remain unimplemented or unchanged by this feature and are not required by the mounted frontend.
