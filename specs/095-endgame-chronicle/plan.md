# Implementation Plan: Endgame Chronicle + Journal + Dialectic Screen

**Spec**: 095-endgame-chronicle
**Branch**: `095-endgame-chronicle` (off `8a521a33`)
**Lane**: W (web product — owns `web/**`)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (web/frontend/src/)                            │
│                                                          │
│  App.tsx                                                 │
│  ├─ <Route path="dialectic" <DialecticPage/> />          │
│  ├─ <Route path="chronicle" <ChroniclePage/> />         │
│  └─ <Route path="objectives" <ObjectivesPage/> />       │
│                                                          │
│  NavRail.tsx — 3 new entries (ANALYZE group)            │
│                                                          │
│  components/                                              │
│  ├─ pages/DialecticPage.tsx     (route wrapper)          │
│  ├─ pages/ChroniclePage.tsx     (route wrapper)          │
│  ├─ pages/ObjectivesPage.tsx    (route wrapper)          │
│  ├─ dialectic/DialecticSpread.tsx (card grid)            │
│  ├─ chronicle/EndStateScreen.tsx  (end-state)            │
│  ├─ objectives/ObjectivesTracker.tsx (Vic3 tracker)      │
│  ├─ dialectic/dialectic.css                               │
│  ├─ chronicle/chronicle.css                               │
│  └─ objectives/objectives.css                             │
│                                                          │
│  hooks/                                                   │
│  ├─ useContradiction.ts                                    │
│  ├─ useEndgame.ts                                         │
│  └─ useObjectives.ts                                      │
│                                                          │
│  types/                                                   │
│  └─ dialectic.ts  (ContradictionSnapshot, etc.)          │
│                                                          │
│  test/handlers.ts — 3 new MSW handlers                   │
│  __tests__/integration/ — 3 contract tests               │
└─────────────────────────────────────────────────────────┘
                         │  HTTP GET
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Backend (web/game/)                                     │
│                                                          │
│  api.py — 3 new views:                                   │
│  ├─ game_contradiction  (GET /api/games/{id}/contradiction/)│
│  ├─ game_endgame        (GET /api/games/{id}/endgame/)    │
│  └─ game_objectives     (GET /api/games/{id}/objectives/) │
│                                                          │
│  urls.py — 3 new routes                                  │
│                                                          │
│  engine_bridge.py — 3 new methods:                      │
│  ├─ get_contradiction_snapshot(session_id)               │
│  │   Reads contradiction_field rows (SQL via pool) +     │
│  │   graph attrs (contradiction_frames,                  │
│  │   dialectical_regime) via hydrate_graph.              │
│  ├─ get_endgame_state(session_id)                        │
│  │   Reads terminal outcome from snapshot.               │
│  └─ get_journal_objectives(session_id)                   │
│      Derives Vic3-style objectives from state.           │
│                                                          │
│  FIX: resolve_tick line 1058 — endgame_types set         │
│  expanded from 3 to all 5 GameOutcome event types.       │
└─────────────────────────────────────────────────────────┘
                         │  READ ONLY
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Engine (src/babylon/ — READ ONLY, cross-lane)           │
│                                                          │
│  engine/observers/endgame_detector.py                    │
│  ├─ on_tick: FR-033 order (code is correct)              │
│  └─ docstring: STALE (Slice 1.6, says REV-first)          │
│     → FLAGGED cross-lane, not edited                     │
│                                                          │
│  dialectics/core/opposition.py — OppositionRegistry       │
│  dialectics/core/regime.py — classify_regime               │
│  dialectics/core/level.py — LevelLattice / Aufhebung       │
│  engine/systems/contradiction.py — ContradictionSystem    │
│  persistence/postgres_schema.py — contradiction_field DDL  │
│  models/enums/events.py — GameOutcome (5 outcomes + IN_PROGRESS) │
└─────────────────────────────────────────────────────────┘
```

## File Changes

### Backend (web/game/) — owned by this spec

| File | Change | TDD |
|------|--------|-----|
| `engine_bridge.py` | +3 methods (`get_contradiction_snapshot`, `get_endgame_state`, `get_journal_objectives`); FIX `resolve_tick` endgame_types (3→5) | RED first |
| `api.py` | +3 views (`game_contradiction`, `game_endgame`, `game_objectives`) | RED first |
| `urls.py` | +3 routes | — |

### Frontend (web/frontend/src/) — owned by this spec

| File | Change | TDD |
|------|--------|-----|
| `App.tsx` | +3 routes under GameRouteShell | — |
| `components/layout/NavRail.tsx` | +3 NavItems (ANALYZE group) | — |
| `components/pages/DialecticPage.tsx` | NEW — route wrapper | — |
| `components/pages/ChroniclePage.tsx` | NEW — route wrapper | — |
| `components/pages/ObjectivesPage.tsx` | NEW — route wrapper | — |
| `components/dialectic/DialecticSpread.tsx` | NEW — card grid (ports mockup) | Vitest |
| `components/dialectic/dialectic.css` | NEW | — |
| `components/chronicle/EndStateScreen.tsx` | NEW — end-state (ports mockup) | Vitest |
| `components/chronicle/chronicle.css` | NEW | — |
| `components/objectives/ObjectivesTracker.tsx` | NEW — Vic3 tracker | Vitest |
| `components/objectives/objectives.css` | NEW | — |
| `hooks/useContradiction.ts` | NEW — polling hook | — |
| `hooks/useEndgame.ts` | NEW — polling hook | — |
| `hooks/useObjectives.ts` | NEW — polling hook | — |
| `types/dialectic.ts` | NEW — ContradictionSnapshot types | — |
| `test/handlers.ts` | +3 MSW handlers | — |
| `__tests__/integration/contradiction-contract.test.tsx` | NEW — contract test | Vitest |
| `__tests__/integration/endgame-contract.test.tsx` | NEW — contract test | Vitest |
| `__tests__/integration/objectives-contract.test.tsx` | NEW — contract test | Vitest |

### Tests (tests/unit/web/) — owned by this spec

| File | Change | TDD |
|------|--------|-----|
| `test_engine_bridge.py` | +tests for 3 new bridge methods | RED first |
| `test_endgame_priority.py` | NEW — EndgameDetector FR-033 priority test | RED first |
| `test_api.py` | +tests for 3 new views | RED first |

### Engine (src/babylon/) — READ ONLY (cross-lane flags)

| File | Change | Owner |
|------|--------|-------|
| `engine/observers/endgame_detector.py` | Docstring fix (stale Slice-1.6 → FR-033 order) | CROSS-LANE (engine lane) |

## Constitution Gate Checklist

- [ ] **III (AI observes, never controls)**: All 3 new endpoints are GET reads. Zero
      engine state writes. Frontend has zero `babylon.*` imports.
- [ ] **V (Deterministic hash)**: No new state mutations; bridge methods are pure reads.
- [ ] **Aleksandrov Test**: Every contradiction field traces to a material relation
      (OppositionRegistry defect over graph inputs). No ungrounded tensors.
- [ ] **VIII (Cold Collapse)**: All new components use ratified spec-090 tokens.
- [ ] **TDD red phase**: Contradiction-snapshot, endgame-priority, and 5-outcome tests
      written RED before implementation.
- [ ] **Cross-lane**: EndgameDetector docstring fix flagged, not edited.
