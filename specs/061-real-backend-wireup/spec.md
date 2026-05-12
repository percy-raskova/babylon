# Feature Specification: Real Backend Wire-Up

**Feature Branch**: `061-real-backend-wireup`
**Created**: 2026-05-11
**Status**: Draft
**Input**: User description: "Lets formally codify all of this into a specification then!"

## Overview

The player-facing application currently presents the Babylon simulation through six routed pages (Briefing, Orgs, Verb, Intel, Results, Analysis). These pages were authored with hard-coded fixture data so that the UI could be designed in parallel with the simulation engine — an intentional choice. The fixtures must now be replaced with live data flowing from the simulation engine through the persistence layer to the API to the frontend, so that players see the consequences of their own actions inside their own sessions rather than the same canned arrays every time.

Investigation across the engine persistence layer, the application bridge layer, the API serializers, the frontend stores, and the routed pages has surfaced five concrete obstacles to a clean cutover from fixtures to live data:

1. **A semantic-search schema mismatch** that means the embedding store will reject every write and read against its current table definition.
2. **A bridge-initialization fragility** that silently substitutes a non-deterministic placeholder bridge whenever boot-time persistence setup fails, with historical production logs already showing this happening.
3. **An orphan table** (`sim.hex_states`) created by an early migration that is no longer read by any code path, with a management command whose documentation lies about which table it targets.
4. **A field-shape gap** between what the engine bridge serializes and what the v2 pages consume — 36 distinct fixture fields have no source in the current serialized output, including five fields that block three or more pages at once.
5. **A mock-bridge sunset**: the mock bridge that backs the current fixture-driven flow stores state as a single JSON blob, while the real engine writes normalized rows; the two cannot interoperate on the same session. The mock is treated as disposable scaffolding and removed after cutover; existing fixture-era sessions are discarded.

This specification codifies what "real backend wired up" means in terms players, operators, and contributors can verify, independent of the order in which the implementation work is done.

## Clarifications

### Session 2026-05-11

- Q: How does the system identify a fixture-era game session at load time? → A: Don't — purge all pre-existing game sessions in the cutover migration. After cutover there are no fixture-era sessions to detect.
- Q: Is the engine health endpoint publicly reachable or auth-gated? → A: Two endpoints. Public `/health/` returns up/down only (suitable for orchestrator liveness probes). Auth-gated `/health/detail/` returns bridge identity, retry attempts, and deployment version (operator diagnostics).
- Q: Who can override an already-resolved tick? → A: No one. Once a tick is resolved, it is immutable. There is no override path — neither for players nor for staff. The audit-trail concept is removed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Semantic Search Functions At All (Priority: P1)

A contributor or future narrative feature invokes semantic retrieval against the embedding store (for theory citations, scenario narrative, or RAG-backed prompts). The call returns results in the expected shape rather than failing with an undefined-column error at the database layer.

**Why this priority**: The current state is undefined-column failure on first execution because the schema definition and the read/write code reference incompatible column sets. Any code path that touches the embedding store is broken today. This is the lowest-effort, highest-leverage fix on the list and it unblocks every downstream feature that depends on retrieval.

**Independent Test**: Add a single embedding to the store under a chosen collection, query it back by similarity against the same vector, and observe that the call returns one row with the expected content. No frontend changes required.

**Acceptance Scenarios**:

1. **Given** an empty embedding store, **When** a contributor adds five embeddings under a named collection, **Then** the writes succeed without database errors.
2. **Given** five embeddings stored under collection `rag_documents`, **When** a similarity query is run against a known vector with `k=3`, **Then** the response contains three rows ordered by ascending cosine distance.
3. **Given** an embedding model whose output dimension differs from the configured store dimension, **When** an add call is attempted, **Then** a clear dimension-mismatch error is raised at the application layer before reaching the database.

---

### User Story 2 - Engine Failures Are Visible, Not Silent (Priority: P1)

When the simulation engine cannot initialize at application boot — because the database is unreachable, the schema is missing, or any other startup dependency fails — the worker process retries with exponential backoff and, after exhausting its retries, exits with a non-zero status code so the orchestrator surfaces the failure rather than the application silently serving random data.

**Why this priority**: Historical production logs from 2026-03-03 show five `RuntimeError: EngineBridge not initialized` errors in a single hour. The application kept running, swallowed the exception, fell back to a non-deterministic placeholder bridge, and continued serving "game state" to players. This pattern can recur at any point and is undetectable from the UI side. The fix is foundational to operating the game responsibly and must land before player-facing wire-up is announced.

**Independent Test**: Boot the application with an unreachable database, observe three retry attempts with exponential backoff in the logs, observe the worker exit with a non-zero status, observe the orchestrator restart it. Restart with a reachable database, confirm that the public health endpoint returns up and that the auth-gated health-detail endpoint identifies the real engine implementation.

**Acceptance Scenarios**:

1. **Given** a reachable database with the expected schema, **When** the application boots, **Then** the real simulation engine is wired up on the first attempt and the auth-gated health-detail endpoint reports its identity as the engine implementation.
2. **Given** a database that is unreachable for the entire boot window, **When** the application boots, **Then** initialization is retried three times with exponential backoff, the worker logs each retry, and the worker exits with a non-zero status code after the third failure.
3. **Given** a database that is unreachable on the first attempt but reachable by the second or third attempt, **When** the application boots, **Then** initialization succeeds on the successful attempt and the worker continues to run normally.
4. **Given** placeholder/stub bridge implementations exist for development and testing, **When** the application runs in production configuration, **Then** the auth-gated health-detail endpoint never reports a placeholder bridge as the active implementation.
5. **Given** the engine has booted successfully and the database becomes unreachable mid-session, **When** a player issues an engine-dependent request, **Then** the request receives an explicit service-unavailable response rather than placeholder data.
6. **Given** the auth-gated health-detail endpoint exists, **When** an unauthenticated caller requests it, **Then** the response is a not-found status, not an authentication-challenge status.

---

### User Story 3 - Briefing Page Shows Real Session State (Priority: P2)

A player who loads a game session sees their actual current tick, real priority events generated by the simulation engine during the most recent tick resolution, and trend sparklines drawn from the session's own tick history. The values change across tick boundaries.

**Why this priority**: The Briefing page is the first page a player sees on entering a game session. Today it is rendered entirely from a static fixture module, so two different players in two different sessions see the same six "events" and the same flat sparklines. Wiring this page proves the end-to-end pipeline works for the simplest read-only case.

**Independent Test**: Create a session, advance through three ticks via the resolve endpoint, then load the Briefing page and confirm that the displayed tick number matches the session's tick, that priority events shown belong to recent tick events of this session, and that each sparkline contains at least three distinct values rather than the same constant repeated.

**Acceptance Scenarios**:

1. **Given** a fresh session at tick 0, **When** the player loads the Briefing page, **Then** the tick badge displays 0 and the sparklines display the initial values.
2. **Given** a session that has advanced three ticks, **When** the player loads the Briefing page, **Then** the sparklines display a sequence of three or more distinct values per metric.
3. **Given** the most recent tick produced two events tagged critical and three events tagged informational, **When** the player loads the Briefing page, **Then** the Priority Dispatch panel surfaces the two critical events ahead of the informational events.
4. **Given** two simultaneous sessions with different player orgs, **When** each player loads their Briefing page, **Then** each sees a different player-org name in the subtitle.

---

### User Story 4 - Organizations Page Shows True Ownership and Live State (Priority: P2)

A player on the Orgs page sees a roster of their player-controlled organizations distinguished from NPC organizations. Each org row shows its real cohesion, its current OODA decision phase, and its vanguard resource pools (cadre labor, sympathizer labor, reputation, budget, heat). Selecting an org reveals additional fields (legitimacy, opacity, community memberships) sourced from live state.

**Why this priority**: Five of the six v2 pages need to know which orgs the player controls and need to show each org's short display name. Without these two fields, none of the action-submission pages function correctly. The Orgs page is the simplest place to exercise the full org schema.

**Independent Test**: In a session where the player controls two orgs and there are six NPC orgs, confirm that the player-controlled tab shows exactly two rows and the NPC tab shows exactly six. Confirm that each row's cohesion value matches the value persisted for that org at the current tick. Confirm that the OODA phase displayed is one of observe/orient/decide/act.

**Acceptance Scenarios**:

1. **Given** a session with two player orgs and six NPC orgs, **When** the player loads the Orgs page, **Then** the player-controlled roster shows two cards and the NPC index shows six cards.
2. **Given** a player org whose engine state has cohesion 0.62 and OODA phase "orient", **When** the player selects the org, **Then** the detail panel shows cohesion 0.62 and the OODA badge reads "orient".
3. **Given** a player org with vanguard cadre-labor 12 of 24 maximum, **When** the player views the org card, **Then** a gauge shows 12/24 with the bar half-filled.
4. **Given** a player org that holds memberships in two communities, **When** the player opens the community panel, **Then** both communities are listed with their names and the player's role in each.

---

### User Story 5 - Verb Actions Execute Through the Real Engine (Priority: P2)

A player composes an action on any verb page (Educate, Mobilize, Attack, Campaign, Aid, Reproduce, Investigate, Move, Negotiate), selects an actor org and a target, and submits. The action is queued against the current tick. When the next tick resolves, the action is processed by the real simulation engine and the resulting state changes are visible on the Results page.

**Why this priority**: Verb pages are the entire interactive surface of the game. Without action execution working end-to-end, the game is read-only. The verb-target endpoints are already implemented on the API side, so the gap is mostly about wiring the page's submit button and reading back results.

**Independent Test**: Submit an Educate action against a known target territory from a known actor. Resolve the tick. On the Results page, find the action result row showing actor, target, action type, and outcome deltas. Replay the same action sequence against the same session seed and confirm identical outcomes.

**Acceptance Scenarios**:

1. **Given** a player org with sufficient resources, **When** the player submits an Educate action against an eligible target, **Then** the action appears in the pending action list for the current tick.
2. **Given** a pending Educate action, **When** the tick resolves, **Then** the engine produces an action result row attributing the resulting consciousness and heat deltas to the submitted action.
3. **Given** a session created with a known random seed, **When** the same sequence of submitted actions is replayed against a session with the same seed, **Then** the resulting action results match field-for-field.
4. **Given** a player org with insufficient resources for an action, **When** the player attempts to submit, **Then** the submit is rejected before reaching the engine and an affordability error is surfaced in the UI.
5. **Given** three verbs that currently have no engine handler (Investigate, Move, Negotiate), **When** the player attempts to submit one, **Then** the application either refuses the verb with a clear "not yet supported" message or processes the verb through a real engine handler — never silently no-ops while reporting success.

---

### User Story 6 - Intel, Results, and Analysis Pages Show Real Entities (Priority: P2)

A player on the Intel page browses live surveillance data over territories, orgs, edges, and communities sourced from the current tick. The Results page shows the actual action outcomes from the most recent tick resolution. The Analysis page displays time-series trends drawn from the session's own tick history.

**Why this priority**: These three pages cover surveillance, post-tick feedback, and longitudinal analysis — the three feedback channels a player relies on to make decisions across ticks. They share data dependencies with the Briefing and Orgs pages, so once those are wired the marginal work to add these is small.

**Independent Test**: For Intel, navigate to a territory detail page and confirm that population, heat, rent level, and the dominant community match the session's persisted state. For Results, after a tick resolves, confirm that every submitted action appears with non-zero outcome metadata. For Analysis, confirm that all six sparklines contain at least N distinct points for a session of N+1 ticks.

**Acceptance Scenarios**:

1. **Given** a territory whose persisted state has heat 0.42 and population 80,000, **When** the player opens the territory detail page, **Then** the page displays heat 0.42 and population 80,000.
2. **Given** a tick in which the player submitted three actions, **When** the tick resolves and the player loads the Results page, **Then** all three action result rows are present with their respective outcome deltas.
3. **Given** a session at tick 10 with non-trivial economic dynamics, **When** the player loads the Analysis page, **Then** each of the six metric sparklines displays at least 10 plotted points with visible variation.
4. **Given** an edge between two orgs with mode `tribute` and value-flow 5.0, **When** the player opens the edge inspector, **Then** the displayed source, target, mode, and value-flow match the engine's edge state.

---

### User Story 7 - Mock Scaffolding Is Sunset Cleanly (Priority: P3)

After the wire-up is complete, the mock bridge implementation, mock defines module, mock-only management commands, and orphan database objects from the fixture era are removed entirely from the codebase. Code paths that selected the mock implementation in production no longer exist. Sessions in the database from the fixture era are documented as discardable.

**Why this priority**: Sunsetting reduces ambiguity for future contributors. A second implementation of "the bridge" that nobody runs accumulates confusion faster than it provides value, especially when its docstring is the source of truth for "what fields the frontend expects." The work is non-trivial but does not block players. Aligning with the explicit "disposable scaffolding" docstring intent of the mock modules keeps the codebase honest.

**Independent Test**: After cutover, search the codebase for the mock implementation class and confirm there are zero references anywhere. Run the full test suite and confirm nothing imports the mock module. Run an end-to-end UI smoke test against the real engine in a stub-table environment to confirm the dev loop still works without the mock.

**Acceptance Scenarios**:

1. **Given** the wire-up is complete and verified, **When** a contributor greps the codebase for the mock bridge class name (`MockEngineBridge`), the mock defines module name (`mock_defines`), and the mock-only management command (`seed_mock_game`), **Then** zero references exist anywhere in the source tree.
2. **Given** the orphan `sim.hex_states` table created by the early migration, **When** a developer runs the latest migration set against a clean database, **Then** the table is dropped by a subsequent migration.
3. **Given** the `seed_hex_data` management command whose docstring claims it seeds a table it doesn't actually target, **When** a developer reads the command help, **Then** the documentation accurately reflects which table receives the seeded rows.
4. **Given** the cutover migration has run, **When** any client attempts to load a session that existed before cutover, **Then** the session is not found (it was purged by the migration) and the player is invited to create a new session.
5. **Given** the `BABYLON_MOCK_MODE` configuration flag exists today, **When** the cutover is complete, **Then** the flag is removed from settings modules and any remaining reference to it is purged.

---

### Edge Cases

- **Partial tick persistence**: a tick resolution writes to seven separate snapshot tables in sequence. If one write fails after others have committed, what is the player's view of the resulting partial state? Is the tick visible at all, or is it rolled back?
- **Action submitted against an org that no longer exists**: a player queues an action at tick N. Before tick N+1 resolves, the actor org's state is purged or transformed. How is the queued action handled?
- **Re-resolution of an already-resolved tick**: a client or automation triggers tick resolution twice for the same `(session_id, tick)` (e.g., due to a duplicate request, retry from a flaky network, or concurrent resolve calls). Resolved ticks are immutable per FR-005, so the second call MUST return an "already resolved" error and leave the persisted state unchanged. The check MUST be race-safe under concurrent calls (the second of two concurrent resolves at the same tick must lose).
- **Engine restart mid-tick**: the worker process is killed during a tick resolution. On restart, the engine encounters a partially-written tick. How is the next tick identified and resumed?
- **Reference to a purged session after cutover**: a player has a bookmarked URL or browser session pointing at a fixture-era session ID that was deleted by the cutover migration. What is the player-visible response when they navigate to it?
- **Embedding dimension change**: the configured embedding model is changed and the new model outputs a different vector dimension than the existing stored embeddings. What happens to existing rows? Are they re-embedded, archived, or rejected on read?
- **Health check during a long-running tick resolution**: a tick is resolving (which can take several seconds). A health check arrives. Does the health check block on the tick lock or return immediately with a "resolving" status?
- **Three verbs with no engine handler**: if Investigate, Move, and Negotiate are exposed to players but their engine implementations are stubs, the player can submit them and receive results that look successful but reflect no state change. How are unsupported verbs surfaced?
- **Snapshot field added after sessions exist**: a player has an active session. The engine is updated to emit a new field on the snapshot. The session's previously persisted ticks lack this field. How are time-series queries that cross the upgrade boundary handled?

## Requirements *(mandatory)*

### Functional Requirements

**Persistence integrity**

- **FR-001**: The embedding store's table definition and the code that reads and writes it MUST reference an identical set of columns and the canonical vector dimension of 768. The canonical model is `sentence-transformers/all-mpnet-base-v2` (Apache 2.0, 768-dim), pinned by HuggingFace revision SHA per Constitution III.6.
- **FR-002**: The system MUST raise a clear dimension-mismatch error at the application layer before the database is asked to store or compare embeddings whose dimension does not match the canonical 768.
- **FR-003**: Per-tick snapshot writes (the seven append-only snapshot tables produced during tick resolution) MUST be atomic: either all seven tables receive the tick's data or none do.
- **FR-004**: Append-only result tables (action_result, simulation_event) MUST be protected against duplicate rows when a tick resolution is retried.
- **FR-005**: A tick that has already been resolved for a session MUST NOT be re-resolvable under any circumstances. Resolved ticks are immutable; no API endpoint, management command, or admin path may re-execute a tick that already has a resolution row. Attempts to do so MUST return an explicit "already resolved" error. The immutability guard is enforced at the persistence layer (`tick_log` PK uniqueness check) so it applies uniformly regardless of which entry path invokes resolution.

**Engine wiring and observability**

- **FR-006**: At application boot, the system MUST attempt to initialize the real simulation engine when production configuration is detected.
- **FR-007**: When initialization fails, the system MUST retry up to three times with exponential backoff between attempts; if all three retries fail, the worker process MUST exit with a non-zero status code so the orchestrator surfaces the failure.
- **FR-008**: The system MUST NOT silently substitute a placeholder implementation in production, regardless of initialization state.
- **FR-009**: The system MUST expose two health endpoints. A **public** endpoint (e.g., `/health/`) returns only an up-or-down status code with no diagnostic payload, suitable for orchestrator liveness probes by unauthenticated callers. An **auth-gated** endpoint (e.g., `/health/detail/`) requires staff-level credentials and returns a structured payload including the active engine implementation's identity, the count of initialization retry attempts at last boot, and the deployment version. Unauthenticated callers to the auth-gated endpoint MUST receive a not-found response (not a 401, to avoid revealing the endpoint's existence).
- **FR-010**: When the real engine is healthy at boot but its database connection is lost mid-session, player-facing requests that depend on the engine MUST receive an explicit service-unavailable response, not placeholder data.

**Data shape — engine to API**

- **FR-011**: Each serialized organization MUST include: a short display name, a boolean indicating player control, the current OODA decision phase as an enumerated string (observe/orient/decide/act), a legitimacy scalar, an opacity scalar, and the list of community memberships the org currently holds.
- **FR-012**: Each serialized event MUST include: a stable identifier, a severity classification (critical/warning/informational at minimum), a short human-readable title, and a longer body. The existing structured `data` payload MUST be preserved.
- **FR-013**: Each serialized territory MUST include: heat, population, rent level, biocapacity, consciousness scalar, solidarity scalar, wealth, and the dominant community identifier for the current tick.
- **FR-014**: Each serialized edge MUST expose its mode, value-flow, tension, and a stable edge identifier; additional Marxian per-edge metrics (rate of profit, rent burden, age in ticks) MUST be exposed when available and clearly absent when not.
- **FR-015**: The serialized snapshot MUST include hyperedge membership data, replacing the current empty-array placeholder.
- **FR-016**: Frontend-consumed field names MUST be stable across the cutover. The chosen direction is **engine field names are canonical**: the frontend renames its bindings to match the engine (e.g., `cl` → `cadre_labor`, `biocap` → `biocapacity`, `rent` → `rent_level`, `verb` → `action_type`). The engine MUST NOT introduce frontend-style aliases. This direction is applied consistently across every v2 page.

**Currently-stub bridge methods**

- **FR-017**: The time-series endpoint MUST return at minimum six metrics over the session's tick history: imperial rent, consciousness, solidarity, heat, wealth, biocapacity.
- **FR-018**: The communities dashboard endpoint MUST return per-community ternary consciousness, member count, and contradiction-partner identifiers for the current tick.
- **FR-019**: The five inspector endpoints (node, organization, community, edge, hex) MUST each return a populated detail object for any valid identifier in the current tick.
- **FR-020**: The economy summary endpoint MUST return national aggregate Marxian indicators sourced from the persisted economic-summary table.

**Action execution**

- **FR-021**: Each player-submitted action MUST be persisted before tick resolution and MUST be readable as a pending action through the actions endpoint.
- **FR-022**: Each tick resolution MUST process every pending action for the current tick and MUST produce a corresponding action result row.
- **FR-023**: Action submission MUST be deterministic: for a given session, seed, and ordered action sequence, the resulting action result rows MUST be byte-identical across repeated executions.
- **FR-024**: The RNG seed stored on the session MUST be threaded into every engine call that consumes randomness during the session's lifetime.
- **FR-025**: Verbs without a real engine handler MUST either be rejected at submission time with a clear "not yet supported" message OR be removed from the available-actions list — they MUST NOT silently no-op while reporting success.

**Frontend wire-up**

- **FR-026**: Each of the six v2 pages (Briefing, Orgs, Verb, Intel, Results, Analysis) MUST fetch its data from the live API rather than from a static fixture module.
- **FR-027**: Each page MUST display a loading state during its initial data fetch and an error state when the fetch fails. The loading state MUST render a visible placeholder (skeleton elements OR a spinner — pick one consistently across pages) before data arrives; an entirely-blank page is not acceptable. The error state MUST surface the error message text plus a "Retry" control that re-invokes the failed fetch. Both states are exercised by e2e tests against a deliberately-delayed and a deliberately-failing fetch.
- **FR-028**: Page-level polling MUST be aligned to tick boundaries: when a tick advances on the server, the page's data updates within the same poll interval as the existing live polling mechanism.
- **FR-029**: The fixture module that backs the six v2 pages MUST be removed or relocated to test-only scope after every page is wired.

**Cleanup**

- **FR-030**: The orphan `sim.hex_states` table created by an early migration MUST be removed by a follow-up migration.
- **FR-031**: The `seed_hex_data` management command's documentation MUST accurately describe which table receives the seeded rows.
- **FR-032**: The mock bridge implementation (`MockEngineBridge`), mock defines module (`mock_defines`), mock-only management command (`seed_mock_game`), and the `BABYLON_MOCK_MODE` configuration flag MUST be removed entirely from the codebase.
- **FR-033**: The cutover migration MUST purge every pre-existing row from `game_session` (cascading to `game_turn`, `action_result`, and any other session-scoped tables). After cutover, every session in the database is a real-engine session by construction. Requests targeting a purged session ID MUST return a not-found response.

### Key Entities

- **Game Session**: a single playthrough belonging to one player. Carries scenario identifier, simulation configuration, game defines snapshot, current tick, status, random seed, and a session identifier. The unit of player progression.
- **Simulation Tick**: an atomic time step in a game session. A tick has a number, a wall-time at which it resolved, and a complete set of snapshot rows recording the state of every entity at that tick. Ticks are append-only and totally ordered within a session.
- **Organization**: a player- or NPC-controlled collective actor characterized by class character, org type, cohesion, legitimacy, opacity, OODA decision phase, vanguard resources, territorial presence, and community memberships. Has a stable identifier across ticks and a short display name.
- **Territory**: a spatial unit indexed by a hex resolution and a county identifier. Carries Marxian economic indicators (constant capital, variable capital, surplus value, profit rate, exploitation rate, imperial rent), demographic indicators (population, class distribution), and gameplay indicators (heat, rent level, biocapacity, dominant community).
- **Edge**: a directed connection between two entities (org-to-org, org-to-territory, etc.) characterized by mode, value flow, tension, solidarity strength, and additional per-mode metrics. Edges have stable identifiers within a tick.
- **Community (Hyperedge)**: a multi-member affiliation among entities characterized by category, contradiction partner, member roster, material basis, and ideological dimension. Has ternary consciousness composition and infiltration resistance.
- **Player Action**: a command submitted by a player against the current tick, characterized by actor org, verb, action type, target, parameters, and submission timestamp. Transitions from pending to resolved when its parent tick resolves.
- **Action Result**: the outcome record produced by the engine for a single resolved player action, characterized by actor, target, success flag, consciousness delta, heat delta, and structured detail payload. Append-only.
- **Event**: a narrative occurrence produced by the engine during tick resolution, characterized by stable identifier, severity classification, title, body, structured data, source and target identifiers, county identifier, and hex identifier.
- **Embedding**: a vector representation of textual content (theory citation, scenario narrative, prompt fragment) stored under a named collection with associated metadata, source identifier, and chunk index. Retrieved by similarity against a query vector.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A player who creates a fresh session, advances three ticks via the resolve endpoint, and loads the Briefing page sees three or more distinct values on every sparkline. (Today: every sparkline shows the same five constants regardless of session.)
- **SC-002**: A player in a session with two player-controlled orgs and six NPC orgs sees the player-controlled tab populated with exactly two rows and the NPC tab populated with exactly six rows, sourced from that session's persisted state. (Today: every player sees the same six fixture orgs.)
- **SC-003**: An action submitted by a player is reflected as a non-empty action result row on the Results page within one tick boundary of submission, 100% of the time across a sequence of at least 50 submitted actions over a single session.
- **SC-004**: Replaying an identical action sequence against a session created with the same random seed produces byte-identical action result rows on 100% of replays, demonstrating engine determinism.
- **SC-005**: Two simultaneous sessions belonging to two different players display different player-org names, different priority events, and different time-series values across all six pages.
- **SC-006**: A semantic similarity query against the embedding store returns at least one result for any query vector whose nearest neighbor is within the cosine distance threshold, with zero database-level undefined-column errors across a test set of at least 100 queries.
- **SC-007**: Authenticated operators can determine via a single auth-gated health-detail endpoint call whether the application is serving real-engine data, with the endpoint returning the active engine implementation's identity for 100% of authenticated post-boot requests across a test of 100 boot sequences. Unauthenticated callers to the same endpoint receive a not-found response.
- **SC-008**: When the simulation engine cannot initialize at boot after three retry attempts, the worker process exits with a non-zero status code; the orchestrator restart loop is observed to fire on 100% of unrecoverable-failure tests.
- **SC-009**: Zero instances of `sim.hex_states` rows exist in production databases after the cleanup migration runs, and the management command's help text accurately names its target table.
- **SC-010**: After the mock bridge is sunset, zero code paths anywhere in the source tree reference the mock implementation class, mock defines module, mock-only management command, or `BABYLON_MOCK_MODE` flag, verifiable by grep.
- **SC-011**: When a tick resolution fails mid-write, post-failure inspection shows that the affected tick has either all seven snapshot tables populated or none of them populated — no partial-tick state exists for any session.
- **SC-012**: Time from action submission to action result visibility on the Results page is under 10 seconds for a single-tick resolution on a typical session, 95th percentile, with no measurable change attributable to the wire-up itself.

## Assumptions

- The simulation engine, persistence layer, snapshot table set, and verb-specific endpoints exist and function correctly as currently implemented; this feature does not modify the engine's internal computation or alter the per-tick math.
- The existing scenario set (Wayne County, Detroit) is the supported scenario set; this feature does not add new scenarios.
- Hex map data, county reference data, and game-defines data are pre-populated and out of scope for this specification.
- Player authentication and session handling remain as currently configured; this feature does not change how players sign in.
- Existing fixture-era game sessions in the database are discardable; the cutover migration deletes them outright rather than attempting any state translation. There is no data-migration path from mock-bridge state to real-engine state.
- The Postgres extensions required by the engine schema (PostGIS, pgvector, uuid-ossp) are present in the target deployment.
- The currently-routed v2 pages are the canonical player UI; the older v1 components do not need to be re-wired by this specification.
- The hard-coded empty-array hyperedge output in the current snapshot is a known stub that has not been populated against any real source yet; this feature includes its first real implementation.
- The three verbs without engine handlers (Investigate, Move, Negotiate) may be implemented as part of this work or may be deferred and removed from the available-actions list; either resolution satisfies the relevant requirement.
- Operators have access to logs and a health endpoint as the primary observability surfaces; no new alerting infrastructure is introduced by this specification.
- The canonical embedding model is a sentence-transformers-family local model producing 768-dimensional vectors; the dimension is applied uniformly across DDL, code defaults, RAG initialization, and tests. Operating cost is local CPU/GPU compute only; no third-party embedding API calls.
- The mock bridge sunset is a hard delete, not a relocation. No contract-test variant of `MockEngineBridge` is preserved.
- Engine boot failure mode is a hybrid: three retry attempts with exponential backoff, then hard exit with non-zero status. The orchestrator (systemd/Docker/k8s) is assumed to be configured with appropriate restart backoff so transient database unavailability at deploy time does not produce a crash loop.
- Player-facing endpoint response shapes follow the existing envelope conventions; this feature does not redesign the API protocol.

## Out of Scope

- Implementing new gameplay verbs beyond what currently exists.
- Adding new scenarios beyond Wayne County and Detroit.
- Migrating fixture-era game sessions to real-engine state.
- Redesigning the player-facing UI layout, navigation, or visual style.
- Introducing new infrastructure (message queues, websockets, server-sent events, microservices).
- Re-implementing or replacing the simulation engine's computational core.
- Performance optimization beyond meeting the success criteria.
- Internationalization or accessibility audits.

## Resolved Decisions

The following decisions were resolved during specification authoring and are captured here for traceability:

1. **Embedding model and dimension** — *Resolved 2026-05-11*: The canonical embedding model is sentence-transformers-family (MiniLM/MPNet, 768-dimensional). DDL, code defaults, RAG initialization, and test fixtures all standardize on `vector(768)`. Rationale: local-only execution, no third-party API dependency.

2. **Mock bridge fate post-cutover** — *Resolved 2026-05-11*: Delete entirely. `MockEngineBridge`, `mock_defines`, `seed_mock_game`, and `BABYLON_MOCK_MODE` are all removed from the codebase. Rationale: the modules' own docstrings declare them disposable scaffolding; a contract-test variant would carry maintenance burden disproportionate to its regression-detection value.

3. **Engine boot failure mode** — *Resolved 2026-05-11*: Hybrid retry + hard exit. Three initialization attempts with exponential backoff at boot; if all three fail, the worker exits with a non-zero status code. Rationale: tolerates transient database unavailability during deployments while failing loudly on persistent problems. Requires the deployment orchestrator to be configured with appropriate restart backoff to avoid crash loops.
