# Feature Specification: MVP Nationwide Simulation

**Feature Branch**: `041-mvp-nationwide-sim`
**Created**: 2026-03-03
**Status**: Draft
**Input**: Comprehensive audit of running server and codebase, followed by specification of the minimum viable product needed to make Babylon playable as a nationwide geopolitical simulation.

## Audit Summary

A full audit was conducted against the running server (Django + Vite), the Babylon simulation engine, and the React frontend. Key findings:

| Area | Tests | Status | Critical Gap |
| --- | --- | --- | --- |
| Engine (Python) | 7,631 passed, 1 failed, 10 skipped | Solid | Player actions not woven into engine step |
| Frontend (React) | 213 passed, 0 failed | Solid | No URL routing; game state lost on refresh |
| Django backend | 0 tests exist | Gap | No test coverage at all |
| Playwright E2E | 3 files (auth, game-loop, navigation) | Exists but untested against live server | Requires `testuser/testpass` credentials |
| Database | 8 sessions, 0 player actions, 0 action results | Active but unused | ActionResult records never persisted |

### Defects Found

1. **Import boundary violation**: `game/apps.py` imports `babylon.persistence.postgres_runtime` directly instead of going through `engine_bridge.py` (1 failing test)
2. **Player actions ignored by engine**: `resolve_tick()` calls `step()` but does not pass submitted player actions into the simulation — they are stored in the `game_turn` table but never read back
3. **ActionResult records never written**: After `step()` completes, no code maps simulation outcomes back to individual player actions for persistence
4. **No server-side action validation**: POST `/api/games/{id}/actions/` accepts any org_id, verb, and target with no game-rule checks
5. **GameEventLog table not migrated**: Django model defined but table does not exist in database
6. **HexMap TypeScript error**: `HexMap.tsx:86` has a possibly-undefined invocation (pre-existing, blocks `tsc --noEmit` and `npm run build`)

### What Works End-to-End

- Game creation with ~1,100 H3 CONUS territories
- State hydration from PostgreSQL and serialization to JSON snapshot
- Full 7-system simulation engine executing per tick (Imperial Rent, Solidarity, Consciousness, Survival, Struggle, Contradiction, Territory)
- Frontend rendering hex map, graph view, time series, event log, organization dashboard, entity inspectors
- Action composition UI (9-verb grid, target selection, submit)
- Tick resolution (button triggers engine step, state refreshes)
- Authentication, session management, CORS proxying

---

## User Scenarios & Testing

### User Story 1 — Play a Complete Game Session (Priority: P1)

A player logs in, creates a new game using the US nationwide scenario, and plays through multiple turns by selecting organizations, choosing actions, resolving ticks, and observing how the simulation state evolves across the map, charts, and event log. The player continues until the simulation reaches an endgame condition or they choose to stop.

**Why this priority**: Without a functioning game loop from start to finish, there is no product. Every other feature depends on this working.

**Independent Test**: Create a game, submit 3 actions across 3 ticks, and verify that (a) the simulation state changes meaningfully after each resolution, (b) action results appear with success/failure status, and (c) the time series charts show diverging data across ticks.

**Acceptance Scenarios**:

1. **Given** a logged-in player on the game list page, **When** they click "New Game", **Then** a new game is created with ~1,100 CONUS territories and the game shell loads with a populated hex map within 10 seconds.
1. **Given** a game at tick 0, **When** the player selects an organization, chooses a verb (e.g., Educate), picks a valid target, and submits, **Then** the action is recorded and visible in a pending actions list.
1. **Given** a game with pending actions, **When** the player clicks "Resolve Tick", **Then** the engine runs one simulation step, the tick counter increments, action results appear showing success/failure and deltas (consciousness, heat), and the map/charts/event log reflect the new state.
1. **Given** a game that has been played for 20+ ticks, **When** conditions trigger an endgame (Revolutionary Victory, Ecological Collapse, or Fascist Consolidation), **Then** the player sees a clear notification of the outcome with a summary of what happened.

______________________________________________________________________

### User Story 2 — Understand the Simulation State (Priority: P2)

A player can inspect any territory, entity, organization, or institution to understand the material conditions driving the simulation. Economic flows, class consciousness, survival probabilities, and heat levels are all visible and comprehensible.

**Why this priority**: A simulation is meaningless if the player cannot understand what is happening. Legibility is the difference between a game and a random number generator.

**Independent Test**: Click on 3 different territories and 2 different organizations, and verify that each inspector shows distinct, non-zero, changing data that corresponds to what the simulation engine is computing.

**Acceptance Scenarios**:

1. **Given** a game with populated state, **When** the player clicks a hex on the map, **Then** a territory inspector appears showing heat, sector type, operational profile, rent level, biocapacity, and population.
1. **Given** a game with populated state, **When** the player clicks an entity in the graph or inspector, **Then** survival probabilities (P(Acquiescence), P(Revolution)), wealth, consciousness, organization level, and agitation are displayed with visual gauges.
1. **Given** a game across multiple ticks, **When** the player views the time series panel, **Then** charts show wealth, heat, consciousness, and organization trends over time with data points for each resolved tick.

______________________________________________________________________

### User Story 3 — Make Strategic Decisions (Priority: P2)

A player can evaluate which organizations to control, what actions to take, and where to focus effort based on the available information. The action system provides meaningful choices with visible consequences.

**Why this priority**: Player agency is the core of what makes this a game rather than a screensaver. Actions must have visible consequences.

**Independent Test**: Submit the same verb (Educate) targeting two different territories over 5 ticks, and verify that consciousness values diverge between the targeted and untargeted territories.

**Acceptance Scenarios**:

1. **Given** a game in progress, **When** the player opens the action composer, **Then** they see a list of player-controlled PoliticalFaction organizations (is_player=True), each showing budget, cohesion, and class character.
1. **Given** an organization selected, **When** the player views the verb grid, **Then** each verb shows a tooltip explaining what it does (e.g., "Educate: raise consciousness in target territory").
1. **Given** an action submitted and tick resolved, **When** the player views action results, **Then** each result shows the initiative score, action cost, success/failure, and specific deltas (consciousness change, heat change) for that action.

______________________________________________________________________

### User Story 4 — Return to a Game in Progress (Priority: P3)

A player can close their browser, return later, and resume exactly where they left off. Game state persists across sessions, and the player can navigate directly to a specific game.

**Why this priority**: Session persistence is necessary for any game longer than one sitting, but the game is technically playable without it (as long as you don't refresh).

**Independent Test**: Create a game, play 5 ticks, close the browser tab, reopen the app, and verify the game appears in the list at tick 5 with full state intact.

**Acceptance Scenarios**:

1. **Given** a player who has played game X to tick 10, **When** they return to the game list, **Then** game X appears showing "Tick 10" and current status.
1. **Given** a player selecting a game from the list, **When** the game loads, **Then** the map, charts, and event log show the full accumulated state up to the current tick.

______________________________________________________________________

### User Story 5 — Choose a Scenario (Priority: P3)

A player can select from multiple scenario configurations when creating a new game, choosing between different starting conditions (nationwide CONUS, minimal test scenarios, custom configurations).

**Why this priority**: The nationwide US scenario is the default and most important. Other scenarios are useful for testing and learning but not required for MVP.

**Independent Test**: Create games with two different scenarios and verify that the initial territory count and entity composition differ.

**Acceptance Scenarios**:

1. **Given** a player on the game creation screen, **When** they view available scenarios, **Then** at least the US nationwide scenario (~1,100 territories) and one smaller scenario are listed with descriptions.
1. **Given** a player selecting a scenario, **When** the game is created, **Then** the game state reflects the chosen scenario's initial conditions.

______________________________________________________________________

### Edge Cases

- What happens when a player submits an action for an organization that no longer exists (destroyed in a previous tick)? → Server rejects at submission time via FR-003 validation (org must exist in current state).
- How does the system handle two rapid clicks on "Resolve Tick" (double-resolution)? → Button is disabled (greyed + spinner) during resolution; server rejects concurrent requests as a secondary guard.
- What happens when the simulation engine crashes mid-step (partially persisted state)? → Rollback to pre-tick state; tick not committed, error toast shown, player can retry.
- What happens when a player tries to act through an organization they don't control? → Server rejects with 403; only PoliticalFaction orgs with is_player=True are controllable.
- How does the system handle a browser refresh mid-tick-resolution? → Server completes or rolls back the tick independently of the browser. On reload, the game resumes at whichever tick was last fully committed.
- What happens when the database connection drops during `persist_tick()`? → Same as engine crash: rollback, error toast, player retries.

## Requirements

### Functional Requirements

- **FR-001**: System MUST integrate submitted player actions into the simulation engine's `step()` function, so that player decisions affect simulation outcomes.
- **FR-002**: System MUST persist ActionResult records to the database after each tick resolution, mapping simulation outcomes back to the specific player actions that were submitted.
- **FR-003**: System MUST validate player action submissions server-side, rejecting actions where the organization does not exist, is not a PoliticalFaction with is_player=True, the verb is not one of the 9 canonical verbs (educate, reproduce, investigate, attack, mobilize, campaign, aid, move, negotiate), or the target is unreachable.
- **FR-004**: System MUST prevent double-resolution of the same tick (idempotency guard on resolve endpoint).
- **FR-005**: System MUST display action results to the player after tick resolution, including success/failure status, initiative score, action cost, and any state deltas.
- **FR-006**: System MUST persist game state to PostgreSQL such that a page refresh or new browser session can resume from the current tick with full state intact.
- **FR-007**: System MUST display an endgame notification when the simulation reaches a terminal condition (Revolutionary Victory, Ecological Collapse, Fascist Consolidation).
- **FR-008**: System MUST fix the import boundary violation in `game/apps.py` so all engine access goes through `engine_bridge.py`.
- **FR-009**: System MUST run database migrations for the `GameEventLog` table so audit logging does not silently fail.
- **FR-010**: System MUST fix the TypeScript error in `HexMap.tsx` so that `npm run build` succeeds without errors.
- **FR-011**: System MUST provide URL-based navigation so that game sessions are addressable (bookmarkable, refreshable).
- **FR-012**: System MUST display verb descriptions/tooltips in the action composer so players understand what each action does.
- **FR-013**: System MUST allow scenario selection when creating a new game, presenting at least the US nationwide and one smaller scenario.

### Key Entities

- **GameSession**: A single playthrough — tracks scenario, current tick, status (active/paused/completed/abandoned), simulation configuration, and player ownership.
- **PlayerAction (game_turn)**: A player's decision — which organization acts, what verb, against what target, with what parameters. Marked resolved after tick processing.
- **ActionResult**: The outcome of a specific action after tick resolution — success/failure, initiative score, action cost, consciousness and heat deltas.
- **WorldState**: The complete simulation state at a given tick — all entities, territories, organizations, institutions, relationships, economy, and events. Serialized as a graph in PostgreSQL.
- **EndgameCondition**: A terminal state detected by the EndgameDetector — type (Revolutionary Victory, Ecological Collapse, Fascist Consolidation) with supporting data.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A new player can create a game, submit actions, and resolve 10 ticks within 15 minutes of first login, without external documentation.
- **SC-002**: After resolving a tick, at least 80% of submitted actions produce visible ActionResult records with non-null consciousness or heat deltas.
- **SC-003**: Refreshing the browser at any point during gameplay resumes the game at the correct tick with no data loss.
- **SC-004**: The simulation reaches a detectable endgame condition within 200 ticks for the US nationwide scenario.
- **SC-005**: All existing test suites (engine unit tests, frontend unit tests) continue to pass with zero regressions.
- **SC-006**: Django backend has at least 20 tests covering game creation, action submission, tick resolution, and error cases.
- **SC-007**: The `npm run build` command completes without TypeScript errors.
- **SC-008**: The Playwright E2E suite passes against a running server, covering login, game creation, action submission, and tick resolution.

## Clarifications

### Session 2026-03-03

- Q: Which organizations can a player control? → A: Only PoliticalFaction orgs where is_player=True.
- Q: What is the canonical verb set for MVP validation? → A: The 9 UI verbs (educate, reproduce, investigate, attack, mobilize, campaign, aid, move, negotiate). The 21-value ActionType enum serves NPC organizations.
- Q: What should the player see on a double-click of Resolve Tick? → A: Button is disabled during resolution (greyed out + spinner); server also guards against concurrent requests.
- Q: Which endgame conditions should MVP detect? → A: The 3 the engine already detects (Revolutionary Victory, Ecological Collapse, Fascist Consolidation). Imperial Collapse and Stable Necropolis are deferred.
- Q: What should happen when the engine or database fails mid-tick? → A: Rollback to pre-tick state. Tick is not committed, player sees an error toast, and can retry Resolve Tick. No partial state persisted.

## Assumptions

- The simulation engine's 7-system pipeline is correct and does not need modification — only the integration layer (wiring player actions in, extracting results out) needs work.
- The existing frontend component architecture is sufficient — new features extend existing components rather than replacing them.
- Single-player is the target for MVP. Multi-player, spectator mode, and turn timers are out of scope.
- The US nationwide scenario (~1,100 H3 territories) is the primary scenario. Performance optimization for larger scenarios is out of scope.
- The existing authentication system (Django sessions, admin-created accounts) is sufficient for MVP. Self-registration is out of scope.
- "Playable" means a player can make meaningful decisions that visibly affect simulation outcomes, not that the game is balanced or polished.
