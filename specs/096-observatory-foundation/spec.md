# Feature Specification: Observatory Foundation

**Feature Branch**: `096-observatory-foundation`
**Created**: 2026-07-03
**Status**: Draft
**Program**: 09 Full-Game Build — Lane O (Observatory). Provisional program number 096.
**Input**: User description: "Observatory foundation (spec-096, Lane O of Program 09): a dev-facing debug dashboard over the SIMULATION database."

## Overview

The Observatory is a **developer-facing debug dashboard** over the running
simulation's Postgres database. Percy's directive (Program 09 §0.2): "a GUI
to analyze time-series economic data 'and everything' straight from the
simulation database, for development troubleshooting."

Today there is a **two-database split** with no bridge between the halves.
The web product (Django) runs against its own Postgres (the spec-037 product
schema — game sessions, hex snapshots). The headless simulation runner writes
a *different* Postgres (the spec-062 `dynamic_*` schema plus the spec-087–089
additions: `tick_commit`, `v_hex_state_asof`, the value-aggregate views,
session partitioning). Nothing in the product reads the runner's database.
Developers troubleshooting a run today drop to raw `psql`.

The Observatory adds the missing **read-only bridge**: a second database
connection the product uses to *read* the runner's tables, plus a small set
of read endpoints and dashboard pages so a developer can pick a session and
plot national / state / county economic series, inspect the per-tick commit
hash chain, and read the hex frame at any committed tick — all without
touching the simulation or its schema.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Plot a session's economic time-series (Priority: P1)

A developer has run a simulation (canonical Michigan run, or a small probe
session) and wants to see whether value production, surplus, and biocapacity
behave as expected over the run. They open the Observatory, pick the session
from a list, and view national / state / county time-series charts for the
committed tick range, with the ability to export the underlying numbers.

**Why this priority**: This is the core troubleshooting loop and the reason
the feature exists — "analyze time-series economic data straight from the
simulation database." Everything else supports or extends it.

**Independent Test**: Seed one session's committed ticks into the simulation
database, open the Observatory, select the session, and confirm a national
series renders across the committed tick range and its CSV export contains a
row per committed tick.

**Acceptance Scenarios**:

1. **Given** a simulation database holding at least one committed session,
   **When** the developer opens the Observatory session picker, **Then** that
   session appears with its committed tick range and tick count.
2. **Given** a selected session, **When** the developer views the national
   series for a metric (e.g. value produced), **Then** a point appears for
   every committed tick in the range.
3. **Given** a rendered series, **When** the developer requests a CSV export,
   **Then** they receive a file with one row per committed tick and columns
   for the selected aggregate metrics.
4. **Given** a selected session and a chosen scope (county or state) plus an
   identifier, **When** the developer views the series, **Then** the chart
   shows that scope's aggregates over the committed range.

### User Story 2 - Inspect the commit hash chain and hex frame (Priority: P2)

A developer suspects a determinism or persistence problem. They open a
session's commit chain to see, per tick, the determinism hash, how many hex
rows were written, and whether the tick was a checkpoint frame. They can then
read the full hex frame reconstructed at any committed tick.

**Why this priority**: The tick-commit hash chain and the as-of hex view are
the project's declared determinism and persistence read interfaces
(spec-089); surfacing them turns "drop to psql" debugging into a UI.

**Independent Test**: For a seeded session, request the commit-chain summary
and confirm each committed tick reports a 64-character hash, a non-negative
hex-rows-written count, and a checkpoint flag; request the hex frame at a
committed tick and confirm one row per hex with its value tuple.

**Acceptance Scenarios**:

1. **Given** a selected session, **When** the developer opens the commit
   chain, **Then** every committed tick shows tick number, determinism hash,
   hex-rows-written, and checkpoint flag, ordered by tick.
2. **Given** a selected session and a committed tick, **When** the developer
   requests the hex frame at that tick, **Then** each hex's reconstructed
   value tuple is returned (the sparse delta store is reconstructed on read,
   never read raw).

### User Story 3 - Never perturb the simulation (Priority: P1)

The Observatory is a strict observer. It must be impossible for the dashboard
to modify simulation state or the runner-owned schema, so a developer can
safely browse a session while it is still running.

**Why this priority**: Constitution II.11 (subsystem table ownership) and the
project's "AI/UI observes, never controls" principle. A debug tool that could
corrupt the very run being debugged is worse than useless.

**Independent Test**: Attempt any write through the Observatory's database
connection and confirm the database rejects it; attempt to migrate the
runner-owned schema through the product's migration command and confirm the
Observatory's tables are never created or altered.

**Acceptance Scenarios**:

1. **Given** the Observatory database connection, **When** any statement
   attempts to write (INSERT/UPDATE/DELETE/DDL), **Then** the database rejects
   it as a read-only transaction.
2. **Given** the product's schema-migration process, **When** it runs, **Then**
   it makes no schema change to the simulation database.
3. **Given** a session actively being written by the runner, **When** the
   developer reads it in the Observatory, **Then** reads succeed against
   already-committed ticks and never block or alter the writer.

### User Story 4 - Keep the dashboard out of production (Priority: P3)

The Observatory is a development tool. It is enabled by default in the
development environment and disabled by default in production, so it does not
expose internal simulation data to end users.

**Why this priority**: Least-privilege / information-hiding; mirrors the
existing staff-only diagnostic surfaces. Lower priority because it is a
configuration guard rather than core capability.

**Independent Test**: With the feature flag off, confirm the Observatory
endpoints report "not available" and the dashboard shows a disabled state;
with it on, confirm the dashboard operates normally.

**Acceptance Scenarios**:

1. **Given** the feature is disabled, **When** a client calls any Observatory
   endpoint, **Then** the endpoint responds "not found / not available" and
   reveals no session data.
2. **Given** the feature is disabled, **When** the developer opens the
   Observatory page, **Then** it shows a clear disabled/unavailable state
   rather than an error.
3. **Given** the feature is enabled, **When** the developer opens the page,
   **Then** the full session-picker and series-browser flow works.

### Edge Cases

- **No committed sessions**: The session picker shows an empty state, not an
  error.
- **Session with only tick 0**: A single-point series renders; CSV export has
  exactly one data row.
- **Requested county/state has no hexes in the session**: The series is empty
  (no points), not an error.
- **Tick requested for the hex frame is not a committed tick**: The frame
  reconstructs the value valid *as of* the requested committed tick; a tick
  beyond the committed range returns an empty frame.
- **Simulation database unreachable**: Endpoints return a clear service-
  unavailable signal; the dashboard surfaces a connection error state without
  crashing the product.
- **Sparse delta store**: Per-tick hex reads must go through the as-of
  reconstruction interface — reading the raw sparse store by tick would miss
  fill-forward rows and is prohibited.
- **Large tick range**: A series request supports a bounded tick window so a
  multi-hundred-tick run does not return an unbounded payload.

## Requirements *(mandatory)*

### Functional Requirements

**Read-only bridge & isolation**

- **FR-001**: The product MUST expose a distinct, read-only connection to the
  simulation database, separate from its own product database, addressed by a
  configurable connection string that defaults to the canonical local
  simulation database.
- **FR-002**: The Observatory MUST read the simulation database exclusively
  through its declared read interfaces (the value-aggregate views, the as-of
  hex view, and the tick-commit table). It MUST NOT read another subsystem's
  internal tables directly (Constitution II.11).
- **FR-003**: The Observatory's database connection MUST refuse all writes:
  every transaction on it is read-only at the database level.
- **FR-004**: The product's schema-migration process MUST NEVER create, alter,
  or drop any object in the simulation database; the runner's own idempotent
  migrations remain the sole owner of that schema.
- **FR-005**: The Observatory MUST add no new tables to any database and MUST
  change no simulation dynamics (zero baseline impact).

**Session & tick discovery**

- **FR-006**: The Observatory MUST list the sessions present in the simulation
  database that have at least one committed tick, each with its minimum tick,
  maximum tick, and committed-tick count.
- **FR-007**: Where session metadata (scenario, status, creation time) is
  available in the simulation database, the session list MAY include it; its
  absence MUST NOT break the listing.
- **FR-008**: For a given session, the Observatory MUST report its committed
  tick range and identify which ticks are checkpoint frames.

**Time-series**

- **FR-009**: The Observatory MUST return national-scope value-aggregate
  time-series (constant/variable capital, surplus, k, biocapacity, hex count)
  for a session over a bounded, inclusive tick range.
- **FR-010**: The Observatory MUST return state-scope and county-scope
  value-aggregate time-series for a session, a scope identifier, and a bounded
  tick range.
- **FR-011**: The Observatory MUST provide the same time-series data as a CSV
  download with a header row and one row per committed tick.

**Commit chain & hex frame**

- **FR-012**: The Observatory MUST return, for a session, the per-tick commit
  summary — tick, determinism hash, hex-rows-written, and checkpoint flag —
  ordered by tick.
- **FR-013**: The Observatory MUST return the reconstructed hex frame for a
  session at a specified committed tick, using the as-of reconstruction
  interface (never the raw sparse store), with an optional spatial filter
  (by county) to bound the result.

**Dashboard**

- **FR-014**: The Observatory MUST present a session picker that lists
  available sessions and lets the developer select one.
- **FR-015**: The Observatory MUST present a series browser that plots the
  selected session's national / state / county series and offers CSV export.
- **FR-016**: The dashboard MUST load as an isolated, on-demand part of the
  application so it adds no weight to the main game experience.

**Feature gating**

- **FR-017**: The Observatory MUST be governed by a single feature flag,
  enabled by default in development and disabled by default in production.
- **FR-018**: When the flag is disabled, every Observatory endpoint MUST
  respond as unavailable (revealing no session data) and the dashboard MUST
  render a disabled state.
- **FR-019**: Access to the Observatory MUST require an authenticated user
  (consistent with the rest of the product's API).

### Key Entities *(include if feature involves data)*

- **Session**: A simulation run identified by a session id, characterized by
  the set of committed ticks recorded for it. Source of truth for "which
  sessions exist" is the per-tick commit record.
- **Committed tick**: One tick that was atomically persisted — carries a
  determinism hash, a hex-rows-written count, and a checkpoint flag.
- **Value aggregate**: The summed economic value tuple (c, v, s, k,
  biocapacity, hex count) for a scope (national / state / county) at a
  committed tick, exposed by the declared aggregate views.
- **Hex frame**: The full set of per-hex value tuples reconstructed as of a
  committed tick from the sparse delta store plus checkpoints.
- **Commit chain**: The ordered sequence of committed ticks for a session,
  forming the determinism hash chain.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can go from opening the Observatory to viewing a
  session's national economic series in at most three interactions (open →
  pick session → view series).
- **SC-002**: For any seeded session, the national series contains exactly one
  data point per committed tick in the requested range (100% coverage, no
  gaps, no duplicates).
- **SC-003**: A CSV export of a series contains a header row plus exactly one
  row per committed tick in the requested range.
- **SC-004**: Zero write operations succeed against the simulation database
  through the Observatory: 100% of attempted writes are rejected.
- **SC-005**: The product's migration process makes zero schema changes to the
  simulation database across a full migrate run.
- **SC-006**: With the feature disabled, 100% of Observatory endpoint calls
  return an unavailable response and expose no session data.
- **SC-007**: The commit-chain view reports a determinism hash, a
  hex-rows-written count, and a checkpoint flag for 100% of a session's
  committed ticks.
- **SC-008**: Introducing the Observatory changes no existing product test
  outcome and no simulation baseline (existing suites remain green;
  determinism baselines unchanged).

## Assumptions

- The simulation database's read interfaces already exist and are the sole
  supported read path: the value-aggregate views (`v_county_value_aggregate`,
  `v_state_value_aggregate`, `v_national_value_aggregate`), the as-of hex view
  (`v_hex_state_asof`), and the `tick_commit` table (specs 062 / 087–089).
  The Observatory consumes them as-is and does not modify them.
- "Sessions that exist" is derived from the commit record (`tick_commit`),
  which is authoritative for committed ticks. Product-side session metadata
  (scenario, status) may be absent in the simulation database and is treated
  as optional enrichment.
- The default connection target is the canonical local simulation database
  (`localhost:5433/babylon_test`), overridable by environment variable. The
  Observatory reads only; it never provisions or migrates that database.
- Charting reuses the existing product charting library and visual language
  (Tufte-minimal, palette-token colors) rather than introducing new charting
  dependencies.
- The feature is developer-facing; it reuses the product's existing
  authentication and does not add a separate permission tier beyond
  authenticated access plus the environment feature flag.
- Deep panes (boundary-flow explorer, hash-chain recompute/verify,
  conservation-audit browser, two-session diff, archived-Parquet reading via
  a source switch) are **out of scope** here; they are the follow-on spec-099.
  This spec is the foundation those build on.
