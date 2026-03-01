# Feature Specification: Postgres Runtime Database

**Feature Branch**: `037-postgres-runtime-db`
**Created**: 2026-03-01
**Status**: Draft
**Input**: User description: "PostgreSQL database replacing all non-reference runtime storage, covering game management, simulation state persistence, trace logging, archival pipeline, and vector search extensions"
**Supersedes**: SQLite runtime database (`babylon/persistence/runtime_db.py`, `runtime_schema.py`)
**Depends On**: Constitution, ADR030/031/032/033, Features 011-036

## Clarifications

### Session 2026-03-01

- Q: Should Feature 036 infrastructure topology state (terrain, biocapacity, internet consciousness, infrastructure links) have dedicated persistence entities, or is it already covered by Node State/Edge State JSONB attributes? → A: Add dedicated infrastructure entities. Feature 036 state requires its own persistence tables, not generic JSONB blobs.
- Q: Should Feature 002 contradiction field and edge curvature tables be included in the initial schema or deferred? → A: Include as standard (non-provisional) tables. Feature 002 is fully implemented in the codebase (3 engine systems, field registry, curvature formula, full test suite), so these are required tables, not forward-looking.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Simulation State Survives Restarts (Priority: P1)

A player starts a game session, plays through several ticks, then closes the application. When they return later, the game resumes exactly where they left off with full fidelity: all economic data, social class states, organizational positions, community dynamics, hex-level economics, and edge relationships are intact.

**Why this priority**: Without reliable state persistence, no other feature matters. The simulation engine currently holds state in-memory; a crash or restart loses everything. This is the foundation that every other user story builds on.

**Independent Test**: Start a game, advance 10 ticks, restart the application, verify all state matches pre-restart values exactly (node attributes, edge weights, community consciousness, hex economics, infrastructure topology).

**Acceptance Scenarios**:

1. **Given** a game at tick 42 with 35 nodes, 55 edges, 14 communities, and 1500 hex cells, **When** the application restarts and reloads the session, **Then** all state values match the pre-restart snapshot exactly (zero data loss).
2. **Given** a game session in progress, **When** the engine completes a tick, **Then** the full state snapshot is persisted before the player sees results, ensuring crash safety.
3. **Given** a game session with active player organizations, **When** a new tick begins, **Then** the engine hydrates the complete state from persistent storage, including graph metadata (economy, state finances, tick dynamics), community memberships, spatial hex data, and infrastructure topology (terrain, biocapacity, internet access).

______________________________________________________________________

### User Story 2 - Player Turn Submission and Resolution (Priority: P1)

A player submits strategic actions (one per organization per tick) through the game interface. The system records each action, processes it during tick resolution, and persists the outcome including initiative scores, success/failure, consciousness and heat deltas.

**Why this priority**: Player agency is the core gameplay loop. Without persistent turn tracking and outcome recording, the game has no interactivity.

**Independent Test**: Submit a player action for an organization, advance the tick, verify the action was resolved and outcomes are persisted and retrievable.

**Acceptance Scenarios**:

1. **Given** a player with an active organization in a running session, **When** they submit an action for the current tick, **Then** the action is recorded with organization, verb, target, and parameters.
2. **Given** multiple organizations in the same tick, **When** the tick resolves, **Then** each action receives an initiative score, cost accounting, and success/failure determination that persists across restarts.
3. **Given** a player attempting to submit two actions for the same organization in the same tick, **When** the second submission occurs, **Then** the system rejects the duplicate (one action per organization per tick).

______________________________________________________________________

### User Story 3 - Multi-Session Game Management (Priority: P1)

A player can create new game sessions with specific scenarios and configurations, pause and resume games, and maintain multiple concurrent sessions. Each session is fully isolated with its own configuration snapshot, RNG seed, and state history.

**Why this priority**: Session management is the entry point for all gameplay. Players need to start games, choose scenarios, and return to them later.

**Independent Test**: Create two game sessions with different scenarios, advance each independently, verify no state leakage between sessions.

**Acceptance Scenarios**:

1. **Given** a player creating a new game, **When** they select a scenario and configuration, **Then** a session is created with a unique identifier, the full configuration is captured, and the initial state (tick 0) is persisted.
2. **Given** two active game sessions, **When** one advances to tick 50 and the other to tick 10, **Then** querying either session returns only its own state with no cross-contamination.
3. **Given** a completed game session, **When** the player marks it finished, **Then** the session status transitions to completed and the session remains queryable for historical review.

______________________________________________________________________

### User Story 4 - Execution Trace Debugging (Priority: P2)

A developer investigating unexpected simulation behavior can enable detailed execution tracing for a specific game session. The trace captures formula evaluations, edge mode transitions, OODA initiative breakdowns, and coefficient smoothing steps, enabling root-cause analysis of any tick's behavior.

**Why this priority**: Without debugging visibility, tuning the simulation's 60+ parameters is guesswork. Traces connect "what happened" (state tables) to "why it happened" (formula inputs and intermediate values).

**Independent Test**: Create a session with trace logging enabled at DEBUG level, run 5 ticks, query traces to reconstruct why a specific node's profit rate changed.

**Acceptance Scenarios**:

1. **Given** a session with trace level set to SUMMARY, **When** a tick completes, **Then** one trace entry per system records wall time, mutation count, and node I/O counts.
2. **Given** a session with trace level set to DEBUG, **When** a formula evaluates for a node, **Then** the trace captures all formula inputs and the computed output.
3. **Given** a session with trace level set to NONE (default), **When** ticks execute, **Then** zero trace data is generated and no performance overhead is incurred.
4. **Given** trace data for a completed session, **When** the session is cleaned up, **Then** all trace data for that session is removed instantly without affecting other sessions' traces.

______________________________________________________________________

### User Story 5 - Spatial Map Queries (Priority: P2)

The game interface displays a hex-based economic map of the simulation region. Each hex cell shows economic indicators (capital composition, employment, profit rate, exploitation rate) that update each tick. Analysts can query hex economics by geographic region (county boundaries) across time.

**Why this priority**: The hex map is the primary visual interface for understanding spatial economic dynamics. Without efficient spatial queries, the map view requires full-table scans.

**Independent Test**: Load the hex map for a specific tick, verify all ~1,500 hex cells render with correct economic values. Query hex time-series for a specific county and verify profit rate trends.

**Acceptance Scenarios**:

1. **Given** a running game with ~1,500 hex cells, **When** the map view requests current tick data, **Then** all hex economic states are returned efficiently for rendering.
2. **Given** a hex cell identified by its H3 index, **When** a time-series query spans ticks 0-100, **Then** the full economic history for that cell is returned in tick order.
3. **Given** a county boundary (FIPS code), **When** querying aggregate economics, **Then** only hexes within that county are included in the aggregation.

______________________________________________________________________

### User Story 6 - Game Archival and Cold Storage (Priority: P3)

Completed games are automatically exported to compressed columnar files and uploaded to cloud storage. This frees active database space while preserving full game history for cross-game analytics. Archived games can be queried directly from cloud storage without re-importing.

**Why this priority**: Without archival, the active database grows unboundedly (~125MB per completed game). Archival enables both storage management and cross-game analytical workloads.

**Independent Test**: Complete a game, trigger archival, verify the game data is removed from active storage and queryable from the archive.

**Acceptance Scenarios**:

1. **Given** a completed game session older than 24 hours, **When** the archival process runs, **Then** all session data is exported to compressed columnar files, uploaded to cloud storage, and purged from active storage.
2. **Given** an archived game, **When** a cross-game analytical query runs, **Then** the archived data is queryable directly from cloud storage without import.
3. **Given** an archived game session, **When** querying the session index, **Then** the session record (configuration, scenario, RNG seed) remains available with status "archived".
4. **Given** 10 completed games totaling ~1.25GB of active data, **When** all are archived, **Then** cloud storage contains ~150MB of compressed data and active storage is freed.

______________________________________________________________________

### User Story 7 - Semantic Search Over Game Corpus (Priority: P3)

The AI narrative system can search game documents and theory corpus by semantic similarity. Document chunks with vector embeddings support retrieval-augmented generation (RAG) for narrative output. Both session-specific and global theory documents are searchable.

**Why this priority**: Semantic search powers the AI observer's narrative generation. Without it, the AI cannot ground its commentary in relevant theory or game history.

**Independent Test**: Embed a set of theory documents, perform a semantic search query, verify results are ranked by relevance and returned with source metadata.

**Acceptance Scenarios**:

1. **Given** a corpus of theory documents chunked and embedded, **When** searching for "imperial rent extraction mechanisms", **Then** the most semantically similar chunks are returned ranked by relevance.
2. **Given** a game session with session-specific documents, **When** searching within that session's scope, **Then** only session-relevant chunks are returned (not other sessions' documents).
3. **Given** a global theory corpus, **When** searching without session scope, **Then** all theory chunks are searchable regardless of game session.

______________________________________________________________________

### Edge Cases

- What happens when the database connection drops mid-tick? No state is written because no DB I/O occurs during tick computation. The tick can be re-executed from the last persisted snapshot.
- What happens when two processes attempt to persist the same tick? Session-scoped composite keys prevent duplicate writes; the second write fails with a constraint violation.
- What happens when archival export fails after partial upload? Checksum verification prevents premature purge; data remains in active storage until export is verified.
- What happens when a game session is abandoned without completion? Session remains in active storage with "abandoned" status; archival process handles it identically to completed games after timeout.
- What happens when trace logging is enabled at TRACE level for many ticks? Trace data is session-partitioned; dropping a partition is instant with no performance impact on other sessions.
- How does the system handle 10+ concurrent active games? Each game session is fully isolated via session_id scoping; composite keys prevent cross-session interference.

## Requirements *(mandatory)*

### Functional Requirements

**Game Management**

- **FR-001**: System MUST create game sessions with unique identifiers, capturing scenario name, full configuration snapshot, RNG seed, and trace level preference.
- **FR-002**: System MUST track session lifecycle through states: active, paused, completed, abandoned, archived.
- **FR-003**: System MUST record player turn submissions with one action per organization per tick, enforced by uniqueness constraint.
- **FR-004**: System MUST persist action resolution outcomes including initiative scores, action costs, success/failure, and state deltas.

**Simulation State Persistence**

- **FR-005**: System MUST persist complete state snapshots each tick (full snapshots, not diffs) covering graph nodes (4 types: social_class, territory, organization, key_figure), graph edges (all edge types), graph-level metadata (economy, state finances, tick dynamics), and community hypergraph state.
- **FR-006**: System MUST persist per-hex economic state (~1,500 rows per tick for tri-county Detroit) including capital composition, employment, departmental shares, profit rate, and exploitation rate.
- **FR-007**: System MUST hydrate complete simulation state from persistent storage at tick start, reconstructing nodes, edges, metadata, community hypergraph, hex grid, and infrastructure topology.
- **FR-008**: System MUST scope ALL simulation data by session identifier to ensure complete isolation between concurrent games.
- **FR-009**: System MUST persist pre-aggregated tick summaries for time-series display including key economic ratios, edge mode counts, organization counts, and event counts.
- **FR-010**: System MUST persist tick replay metadata including RNG state, mutation summaries, invariant checks, per-system timings, and total wall time.
- **FR-011**: System MUST perform zero database I/O during tick computation (hydrate before, persist after).

**Trace Logging**

- **FR-012**: System MUST support four trace verbosity levels: NONE (zero overhead), SUMMARY (~20 entries/tick), DEBUG (~200-500 entries/tick), TRACE (~1,000-2,000 entries/tick).
- **FR-013**: System MUST buffer trace events in memory during tick execution and flush to storage after tick completion (respecting the no-I/O-during-tick rule).
- **FR-014**: System MUST support instant cleanup of trace data per session without affecting other sessions' traces.

**Spatial Queries**

- **FR-015**: System MUST maintain a static hex cell reference table mapping H3 indices to county FIPS codes, parent cells, and geographic boundaries.
- **FR-016**: System MUST support spatial queries filtering hex cells by geographic region (county, polygon intersection).
- **FR-017**: System MUST support time-series queries on individual hex cells or aggregated county regions.

**Infrastructure Topology (Feature 036)**

- **FR-026**: System MUST persist per-hex terrain classification (land/water/resource type, coverage fractions) and biocapacity stock state (stock type, initial value, current value, depletion status) each tick.
- **FR-027**: System MUST persist per-edge infrastructure link state (link type, capacity per flow category, condition/health, ownership) and aggregated edge capacity each tick.
- **FR-028**: System MUST persist per-hex internet access state (access level, response mode, surveillance coupling) and internet consciousness field values each tick.

**Archival Pipeline**

- **FR-018**: System MUST export completed game sessions to compressed columnar files with integrity verification before purging active data.
- **FR-019**: System MUST preserve session index records (configuration, scenario, seed) permanently even after data archival.
- **FR-020**: System MUST support direct analytical queries over archived data in cloud storage without re-importing.

**Semantic Search**

- **FR-021**: System MUST store document chunks with vector embeddings supporting semantic similarity search.
- **FR-022**: System MUST scope document searches by session (session-specific documents) or globally (theory corpus).

**Compatibility**

- **FR-023**: System MUST maintain the existing RuntimePersistence protocol interface so the simulation engine remains backend-agnostic.
- **FR-024**: System MUST NOT modify WorldState, SimulationEngine, or in-memory computation (NetworkX, XGI) -- only the persistence boundary changes.
- **FR-025**: SQLite reference database MUST remain read-only and unchanged; it continues to serve as the initialization data source.

### Key Entities

- **Game Session**: Represents a single playthrough. Captures scenario, configuration snapshot, RNG seed, trace preferences, lifecycle status, and current tick. Scopes all other entities.
- **Game Turn**: A player action submission for a specific tick and organization. Contains verb, target, parameters. One per organization per tick.
- **Node State**: Per-tick snapshot of a graph node (social class, territory, organization, or key figure). Contains full attribute blob plus promoted query-accelerator fields.
- **Edge State**: Per-tick snapshot of a graph edge. Contains edge type, mode, full attributes, and promoted flow/tension/solidarity fields.
- **Graph Metadata**: Per-tick graph-level data: global economy, state finances, tick dynamics. One row per tick per session.
- **Community State**: Per-tick hypergraph community data (14 community types). Contains heat, cohesion, infrastructure, visibility, consciousness, and legal status.
- **Community Membership**: Per-tick hyperedge incidence records mapping agents to communities with role, strength, visibility, and overt/covert status.
- **Hex Cell**: Static spatial reference mapping H3 indices to geographic boundaries and county assignments. Shared across sessions.
- **Hex State**: Per-tick economic state of each hex cell. Contains capital composition, employment, departmental shares, and derived ratios.
- **Action Result**: Resolution outcome of a player action. Contains initiative score, cost, success flag, and state deltas applied.
- **Contradiction Field**: Per-tick dialectical field values at each node (exploitation, immiseration, imperial rent, displacement) with spatial Laplacian and temporal derivatives (df/dt, d2f/dt2). Computed by ContradictionFieldSystem and FieldDerivativeSystem each tick.
- **Edge Curvature**: Ollivier-Ricci curvature per edge, computed via Wasserstein-1 optimal transport LP. Contains per-field gradients along each edge. Recomputed by FieldDerivativeSystem.
- **Simulation Event**: Append-only ledger of simulation events (uprisings, repressions, edge transitions, etc.) with tick, type, entity, and detail payload.
- **Tick Summary**: Pre-aggregated metrics per tick for time-series endpoints: economic totals, ratios, edge counts, organization counts, event counts.
- **Tick Log**: Deterministic replay metadata: RNG state, mutation summaries, invariant checks, per-system timings.
- **Trace Entry**: Structured execution trace event: system name, verbosity level, event type, optional node reference, and data payload.
- **Terrain State**: Per-tick terrain classification for each hex cell. Contains land/water/resource type and coverage fractions. Derived from Natural Earth data at initialization, mutable during simulation.
- **Biocapacity State**: Per-tick biocapacity stock for each hex cell. Contains stock type, initial value, current value, depletion history, and depletion flag. Tracks ecological resource dynamics.
- **Infrastructure Link State**: Per-tick infrastructure link on graph edges. Contains link type, capacity per flow category, condition/health, and ownership. Tracks transport and utility infrastructure.
- **Internet Access State**: Per-tick internet access and consciousness field for each hex cell. Contains access level, response mode (permit/throttle/sever), and surveillance coupling. Tracks state apparatus control of information flow.
- **Document Chunk**: Text chunk from theory or game corpus with vector embedding for semantic similarity search. Optionally scoped to a session.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Game sessions persist and restore with zero data loss: a restored game at any tick is bit-identical to the state at persistence time.
- **SC-002**: Complete state persistence (all tables) completes within 2 seconds per tick for the tri-county Detroit scenario (~1,500 hexes, ~35 nodes, ~55 edges, ~200 memberships).
- **SC-003**: State hydration (loading a tick's complete state) completes within 1 second for the tri-county Detroit scenario.
- **SC-004**: Trace logging at DEBUG level adds less than 20% overhead to tick execution time compared to NONE level.
- **SC-005**: Ten concurrent game sessions operate without cross-session data leakage or performance degradation beyond 10%.
- **SC-006**: Completed game archival achieves at least 8:1 compression ratio (125MB active to under 16MB archived).
- **SC-007**: Cross-game analytical queries over 100+ archived sessions return results within 30 seconds.
- **SC-008**: Semantic search queries return ranked results within 500ms for a corpus of 10,000+ document chunks.
- **SC-009**: The simulation engine operates identically regardless of which persistence backend is active (SQLite or Postgres), verified by running the same scenario with the same RNG seed and comparing outputs.
- **SC-010**: Active database storage for 10 concurrent beta testers stays under 2GB with archival pipeline active.

## Assumptions

- The deployment target is a single VPS with one Postgres instance. No clustering, replication, or multi-region concerns at beta scale.
- The tri-county Detroit scenario (~1,500 hexes) is the primary sizing reference. Larger scenarios may require additional performance work.
- The existing RuntimePersistence protocol from ADR030 is the interface boundary. The new backend implements this protocol plus extensions for subsystems added after the protocol was defined.
- Django ORM manages game management tables (user accounts, sessions, turns). Simulation state tables use raw SQL for bulk write performance.
- ChromaDB is replaced by vector search in the database. The RagPipeline interface remains unchanged.
- The archival destination is S3-compatible cloud storage (Cloudflare R2). DuckDB provides the analytical query layer over archived Parquet files.
- Full-snapshot persistence (not diffs) is the strategy for correctness over storage efficiency.
- Legacy SQLite runtime tables (agent_state, production_event, network_edge, territorial_control, simulation_metadata) are superseded and do not migrate.

## Dependencies

- **ADR030**: RuntimeDatabase protocol and SessionRecorder observer pattern
- **ADR031**: Tick-keyed temporal storage pattern with (session_id, tick, entity_id) composite keys
- **ADR032**: OODA action system (action results, initiative scoring)
- **Features 011-036**: All simulation subsystems that produce state requiring persistence
- **Feature 002**: Contradiction field topology (fully implemented: ContradictionFieldSystem, FieldDerivativeSystem, EdgeTransitionSystem, FieldRegistry, Ollivier-Ricci curvature)
