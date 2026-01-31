# Feature Specification: MVP Simulation Engine

**Feature Branch**: `001-mvp-sim-engine` **Created**: 2026-01-30 **Status**: Draft **Input**: User description: "Build
the minimal viable simulation engine for Babylon that can run one complete tick and be visualized."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run a Single Tick (Priority: P1)

As a developer building the GUI, I need to call `simulation.step()` and see the state change, so that I can build
visualization panels that react to simulation progress.

**Why this priority**: This is the fundamental capability—without it, nothing else works. The GUI cannot render
meaningful visualizations unless the simulation can advance state.

**Independent Test**: Can be fully tested by initializing a simulation, calling `step()`, and verifying that at least
one numeric value (profit_rate) changed between tick 0 and tick 1.

**Acceptance Scenarios**:

1. **Given** a freshly initialized simulation at tick 0, **When** I call `step()` once, **Then** the tick counter
   advances to 1 AND at least one territory's profit_rate differs from its tick-0 value.

1. **Given** a simulation at any tick N, **When** I call `step()` twice from a checkpoint, **Then** both runs produce
   identical tick N+1 states (determinism guarantee).

1. **Given** a simulation at tick 0 with identical initial conditions, **When** I run 10 ticks on two separate
   instances, **Then** both instances have identical final states (reproducibility).

______________________________________________________________________

### User Story 2 - Query Territory State (Priority: P1)

As a GUI panel developer, I need to call `get_territory_state(territory_id)` and receive a structured object with
numeric properties, so that I can bind those values to visual elements without parsing internal data structures.

**Why this priority**: Tied with US1—the GUI needs both advancement and queryability to function.

**Independent Test**: Can be fully tested by querying a known territory (Wayne County) and verifying the response
includes expected fields (territory_id, profit_rate, hex_claims).

**Acceptance Scenarios**:

1. **Given** an initialized simulation with Wayne County (FIPS 26163), **When** I call `get_territory_state("26163")`,
   **Then** I receive a response with `territory_id`, `profit_rate` (a float), and `hex_claims` (a set of H3 strings).

1. **Given** a simulation with territories, **When** I call `get_territory_state("invalid_id")`, **Then** I receive a
   clear indication (exception or None) that the territory doesn't exist.

1. **Given** a simulation at tick N, **When** I call `get_snapshot()`, **Then** I receive a complete state object
   containing all territories keyed by ID.

______________________________________________________________________

### User Story 3 - Hydrate from SQLite (Priority: P2)

As a simulation operator, I need the simulation to initialize its graph from the SQLite reference database, so that I
work with real QCEW/BEA data rather than hardcoded test values.

**Why this priority**: Depends on US1/US2 being functional first. Real data makes the simulation meaningful but isn't
strictly required for initial GUI development.

**Independent Test**: Can be fully tested by initializing a simulation and verifying that Wayne County's profit_rate is
derived from actual QCEW wages and BEA ratios (not default/placeholder values).

**Acceptance Scenarios**:

1. **Given** a SQLite reference database with QCEW fact records for Wayne County (26163), **When** I initialize the
   simulation, **Then** Wayne County appears as a territory with profit_rate computed from its QCEW wages and BEA c/v
   ratio.

1. **Given** a SQLite reference database with H3 index mappings for Wayne and Oakland counties, **When** I initialize
   the simulation, **Then** each territory's `hex_claims` contains H3 indices from `bridge_county_h3`.

1. **Given** missing data for a required county, **When** I attempt to initialize, **Then** the system fails fast with a
   clear error message identifying the missing data.

______________________________________________________________________

### User Story 4 - Protocol-Based Interface (Priority: P2)

As a GUI developer, I need the simulation to implement defined protocols (SimulationState, SimulationControl), so that
my GUI code depends only on stable interfaces while simulation internals can evolve.

**Why this priority**: Architectural hygiene that enables parallel development. Not blocking for MVP but essential for
sustainable iteration.

**Independent Test**: Can be fully tested by type-checking GUI code against the protocol definitions without importing
simulation implementation modules.

**Acceptance Scenarios**:

1. **Given** a simulation instance, **When** I check `isinstance(sim, SimulationState)` and
   `isinstance(sim, SimulationControl)`, **Then** both return True.

1. **Given** GUI code importing only protocol definitions, **When** I run mypy type checking, **Then** the GUI
   type-checks successfully without importing simulation internals.

1. **Given** the protocol definitions, **When** a new simulation implementation is created, **Then** it can be
   substituted without changing GUI code.

______________________________________________________________________

### Edge Cases

- What happens when step() is called on an already-completed simulation (if endgame detection existed)?

  - For MVP: No endgame detection. step() always advances the tick.

- What happens when a territory has no QCEW data for the requested year?

  - Fail fast with descriptive error during initialization, not during step().

- What happens when H3 mapping is incomplete (county has no hex claims)?

  - Initialize with empty hex_claims set; log a warning but don't fail.

- What happens when profit_rate computation produces invalid values (negative, NaN)?

  - Clamp profit_rate to [0.0, 1.0] range; log warning if clamping occurred.

- What happens when step(n) is called with n \<= 0?

  - Raise ValueError with message "step count must be positive".

- What happens when from_sqlite() is called with an empty fips_codes list?

  - Raise ValueError with message "at least one FIPS code required".

- What happens when from_sqlite() is called with duplicate fips_codes?

  - Deduplicate silently; process each unique FIPS code once.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST define a `SimulationState` protocol with methods: `get_current_tick()`, `get_snapshot()`,
  `get_territory_state(id)`, `get_hexes_for_territory(id)`.

- **FR-002**: System MUST define a `SimulationControl` protocol with methods: `step(n)`, `reset()`.

- **FR-003**: System MUST provide a concrete implementation that satisfies both protocols.

- **FR-004**: System MUST hydrate initial graph state from SQLite reference database tables: `dim_county`, `fact_qcew`,
  `bridge_county_h3`.

- **FR-005**: System MUST compute `profit_rate` for each territory using the formula: `r = s / (c + v)` where c, v, s
  derive from QCEW wages and BEA ratios.

- **FR-006**: System MUST update profit_rate deterministically each tick using a placeholder rule:
  `r_new = r_old * (1 - decay_rate) + equilibrium_r * decay_rate` where decay_rate is a configurable constant and
  equilibrium_r is territory-specific (set to initial_r at hydration). This prevents all territories from converging to
  a universal constant.

- **FR-007**: System MUST use NetworkX as the graph implementation.

- **FR-008**: System MUST use Pydantic for state validation (TerritoryState, SimulationSnapshot).

- **FR-009**: System MUST guarantee determinism: identical initial state + identical step count = identical final state.

- **FR-010**: System MUST include Wayne County (26163) and Oakland County (26125) as the minimum test geography.

- **FR-011**: System MUST store hex claims per territory from `bridge_county_h3` table.

- **FR-012**: Each TerritoryState MUST include: `territory_id`, `profit_rate`, `equilibrium_r`, `hex_claims`, `tick`.

### Key Entities

- **SimulationSnapshot**: Complete state at a tick. Contains tick number, dictionary of territories keyed by ID,
  dictionary of hexes keyed by H3 index, list of edges.

- **TerritoryState**: A polity's state at a given tick. Contains territory_id, controlling_polity, hex_claims (set of H3
  indices), tick, profit_rate, equilibrium_r (territory-specific equilibrium to prevent convergence).

- **HexState**: Immutable geographic cell. Contains h3_index. Hexes are substrate; they don't change during simulation.

- **EdgeState**: Relationship between entities at a tick. Contains source_id, target_id, edge_type, weight.

## Assumptions

The following reasonable defaults are assumed and documented here:

1. **Profit rate decay model**: The placeholder `r_new = r_old * 0.95 + equilibrium_r * 0.05` uses territory-specific
   equilibrium (equilibrium_r = initial_r) to prevent all territories converging to a universal constant. This is a stub
   to be replaced by TRPF mechanics.

1. **Single year of data**: MVP uses 2022 QCEW data. Multi-year support is deferred.

1. **No inter-territory edges for MVP**: Edges (EXTRACTION, SOLIDARITY) exist in the protocol but are empty for MVP. The
   graph is a set of disconnected territory nodes.

1. **Resolution 5 H3**: Hexes are at H3 resolution 5 (~252 km²) matching the existing `bridge_county_h3` table.

1. **Controlling polity is territory name**: For MVP, `controlling_polity` equals `territory_id` (counties don't change
   hands yet).

1. **reset() restores cached state**: The `reset()` method restores the initial state cached at construction time, NOT
   by re-querying SQLite. This ensures reset is fast and deterministic regardless of database state changes.

1. **Material base disconnects after tick 0**: The MarxianHydrator computes c/v/s → profit_rate once at initialization.
   Subsequent ticks evolve via placeholder formula with no reference to c/v/s. This MVP tests GUI plumbing, not ongoing
   economic dynamics.

1. **Single-threaded execution only**: Thread safety is explicitly out of scope. SQLite is single-threaded; the
   simulation assumes single-threaded access. Concurrent calls to step(), reset(), or query methods from multiple
   threads produce undefined behavior.

1. **No concurrent access during step()**: Calling reset() or query methods while step() is executing is undefined
   behavior. Callers must wait for step() to complete before issuing other commands.

1. **step(n) executes as n sequential single-steps**: Calling step(10) is equivalent to calling step(1) ten times. There
   is no batch optimization—each tick computes independently in sequence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The GUI readiness test passes:

  ```python
  snapshot = simulation.get_snapshot()
  territory = snapshot.territories["26163"]
  first_profit_rate = territory.profit_rate
  print(territory.profit_rate)  # prints a float
  print(territory.hex_claims)   # prints a set of H3 strings
  simulation.step()
  snapshot = simulation.get_snapshot()
  assert snapshot.territories["26163"].profit_rate != first_profit_rate
  ```

- **SC-002**: Running 100 ticks from identical initial state on two separate simulation instances produces identical
  final profit_rate values (determinism).

- **SC-003**: Simulation initializes from SQLite within 2 seconds for the Detroit test case (2 counties, their H3
  cells).

- **SC-004**: All protocol methods are callable without raising NotImplementedError.

- **SC-005**: GUI code can be type-checked against protocol definitions without importing simulation implementation.

- **SC-006**: Wayne County's initial profit_rate differs from Oakland County's (demonstrating data-driven
  initialization, not identical defaults).

## Deferred Items (Explicit Scope Boundary)

The following are explicitly OUT OF SCOPE for this spec:

- Full tensor engine with UseValue types
- Crisis detection and endgame logic
- George Jackson bifurcation model
- Department III reproductive labor mechanics
- TRPF with counter-tendencies (placeholder decay used instead)
- Multi-year QCEW integration
- Save/restore checkpoints
- Parameter injection (`set_parameter`, `get_parameter`)
- Event injection (`inject_event`)
- Time series queries (`get_time_series`)
- Event log queries (`get_events`)
- Inter-territory edges (EXTRACTION, SOLIDARITY)
- Tick-history persistence to simulation SQLite database

**GUI Panel Alignment Note**: The GUI guiding star document lists a time series panel (r, s/v, c/v, Φ over ticks) as
Phase 1. However, `get_time_series()` is deferred here because it requires tick-history storage. The MVP GUI should use
the simpler panels (territory map, current-tick metrics) that depend only on `get_snapshot()`. Time series panel
implementation requires a follow-up spec that adds history storage.
