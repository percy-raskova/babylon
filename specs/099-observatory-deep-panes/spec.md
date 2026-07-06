# Feature Specification: Observatory Deep Panes

**Feature Branch**: `099-observatory-deep-panes`
**Created**: 2026-07-04
**Status**: Draft
**Program**: 09 Full-Game Build — Lane O (Observatory). Provisional number 099.
**Stacks on**: spec-096 (Observatory foundation) — unmerged; 099 branches off it.
**Input**: "Observatory deep panes: boundary-flow explorer, hash-chain verification, conservation-audit browser, two-session diff, archived-session reading via DuckDB."

## Overview

Spec-096 shipped the Observatory foundation: a read-only bridge to the
simulation Postgres with session/series/commit/hex endpoints and a session
picker + series browser. Spec-099 adds the **deep diagnostic panes** a
developer reaches for when a run looks wrong, and — crucially — makes every
Observatory read work over **archived sessions** too, not just live ones.

Five capabilities:

1. **Boundary-flow explorer** — inspect the cross-boundary flow register
   (drain / trade / commute flows). Ships against the empty-state first (today
   these are empty until spec-101 activates trade); becomes the human
   verification surface for trade when 101 lands.
2. **Hash-chain verification pane** — read the per-tick commit chain and verify
   its structural integrity (contiguity, checkpoint cadence, hash format,
   gaps/duplicates), surfacing any anomaly.
3. **Conservation-audit browser** — browse the per-tick conservation invariants
   (computed vs expected vs residual, severity), filterable to non-OK rows.
4. **Two-session diff** — compare two sessions' national series and commit
   chains side by side.
5. **Archived-session reading** — the same endpoints accept
   `source=live|archive`. `live` reads the runner Postgres (as 096 does);
   `archive` reads a session's exported Parquet under the archive root via an
   embedded analytical engine, read-only. A real archived 520-tick session
   exists to verify against.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse an archived session (Priority: P1)

A developer archived a finished run (exported to Parquet, purged from Postgres).
They open the Observatory, switch the source to "archive", pick the archived
session, and read its commit chain and national series exactly as if it were
live.

**Why this priority**: Archived sessions are the ONLY copy of a finished run
(archival drops the Postgres partition). Without archive reading, the
Observatory goes blind the moment a run is archived — and archiving is the
standard end-of-run step.

**Independent Test**: Point the source at `archive`, select the known archived
session, and confirm its commit chain (per-tick hash + checkpoint flags) and
national series render from the Parquet, read-only.

**Acceptance Scenarios**:

1. **Given** an archived session under the archive root, **When** the developer
   lists sessions with `source=archive`, **Then** that session appears.
2. **Given** `source=archive` and the archived session, **When** the developer
   opens its commit chain, **Then** every committed tick's hash, hex-rows-written
   and checkpoint flag render — identical to what the live session held before
   archival.
3. **Given** `source=archive`, **When** any request is served, **Then** no write
   ever touches the archive files (read-only analytical queries only).

### User Story 2 - Verify the commit hash chain (Priority: P1)

A developer suspects a persistence or determinism problem. They open the
hash-chain verification pane for a session; it walks the commit chain and reports
whether it is well-formed — ticks contiguous, checkpoints on the expected
cadence, every hash the right length, no gaps or duplicates — and lists any
anomalies.

**Why this priority**: The commit chain is the project's III.7 determinism
record; a silent gap or a checkpoint on the wrong tick is a persistence bug the
naked series view hides.

**Independent Test**: Run the verification over a seeded session and assert it
reports `ok` with the expected checkpoint ticks; introduce a gap in a fixture
and assert it is flagged.

**Acceptance Scenarios**:

1. **Given** a well-formed session, **When** the developer verifies its chain,
   **Then** the pane reports it valid with the committed range, checkpoint ticks,
   and zero anomalies.
2. **Given** a session missing an interior committed tick, **When** verified,
   **Then** the pane flags the gap (the missing tick) as an anomaly.
3. **Given** the same session read `live` and `archive`, **When** both chains are
   verified, **Then** the per-tick hashes agree.

### User Story 3 - Explore boundary flows (empty-state-first) (Priority: P2)

A developer wants to see cross-boundary flows (drain / trade / commute). Today
the register is empty (trade activates in spec-101); the pane must render a clean
empty-state now and light up automatically when flows exist.

**Why this priority**: This becomes trade's human verification surface at 101,
but must ship now without trade data — empty-state correctness is the deliverable.

**Independent Test**: Query the boundary explorer for a session with zero flow
rows and confirm a clean empty result; for a session with sparse flows, confirm
the rows group by flow type.

**Acceptance Scenarios**:

1. **Given** a session with no boundary flows, **When** the explorer is opened,
   **Then** it returns an empty result (not an error) and the UI shows an
   empty-state.
2. **Given** a session with boundary rows, **When** the explorer is opened,
   **Then** flows are returned grouped/aggregated by flow type over the tick
   range.

### User Story 4 - Browse conservation audits (Priority: P2)

A developer wants to see where conservation invariants deviated. They open the
conservation-audit browser for a session, optionally filtered to warn/alarm
severities, and see per-tick invariant residuals.

**Independent Test**: Query the browser for a session and confirm audit rows
(scale, invariant, computed/expected/residual, severity); filter to non-OK and
confirm only warn/alarm rows return.

**Acceptance Scenarios**:

1. **Given** a session with audit rows, **When** browsed, **Then** rows return
   with scale, invariant name, computed/expected/residual, and severity.
2. **Given** a `severity != ok` filter, **When** browsed, **Then** only warn and
   alarm rows return.
3. **Given** a session with no audit rows, **When** browsed, **Then** an empty
   result renders (not an error).

### User Story 5 - Diff two sessions (Priority: P3)

A developer compares a suspect run against a known-good one: two sessions'
national series and commit-chain summaries side by side, with the deltas.

**Independent Test**: Diff two seeded sessions and confirm the response pairs
their national series by tick and reports commit-count / range differences.

**Acceptance Scenarios**:

1. **Given** two session ids, **When** diffed, **Then** the response contains
   both national series aligned by tick plus a per-tick value delta.
2. **Given** two sessions of different lengths, **When** diffed, **Then** the
   tick range difference and commit-count difference are reported without error.

### Edge Cases

- **Archive root unset / session not archived**: `source=archive` for a missing
  session returns an empty/absent result, not a crash.
- **Archived table absent** (e.g. `boundary_flow_register` has zero rows → no
  Parquet file): the explorer returns empty, not a file-not-found error.
- **Mixed availability**: a session may be live-only, archive-only, or both; each
  source reports only what it holds.
- **Verification on a single-tick session**: reports valid (checkpoint at tick 0).
- **Diff a session against itself**: all deltas zero (not an error).
- **Archive read never writes**: analytical queries over Parquet are read-only by
  construction.

## Requirements *(mandatory)*

### Functional Requirements

**Source abstraction**

- **FR-001**: Every Observatory read endpoint (096's and 099's) MUST accept a
  `source` selector with values `live` (default) and `archive`. **Note
  (2026-07-04 fix)**: `hex/` now dispatches on `source` per this requirement,
  but `source=archive` is not implemented for `hex/` — it returns an explicit
  `501`, not a silent empty/stale frame — because the archived Parquet export
  excludes `hex_spatial_map` (reference data; see the Assumptions section and
  the contract doc's hash-chain/hex-source-scope note). This is a documented,
  deliberate deferral, not an FR-001 violation: the endpoint accepts and
  validates `source`, it simply cannot yet serve the archive branch correctly.
- **FR-002**: `source=live` MUST read the runner Postgres through the read-only
  `sim` alias (unchanged from 096). `source=archive` MUST read a session's
  exported Parquet under the archive root, read-only, via an embedded analytical
  engine — no new dependency (the engine already ships in the project).
- **FR-003**: Archive reads MUST resolve a session's directory under the archive
  root (env-configurable, with the project default) and MUST NOT write to it.
- **FR-004**: When an archived table has zero rows (no Parquet file), the
  endpoint MUST return an empty result, not an error.

**Boundary-flow explorer**

- **FR-005**: The explorer MUST return cross-boundary flows for a session over a
  bounded tick range, grouped/aggregated by flow type (drain / trade / commute /
  physical), from the boundary flow register.
- **FR-006**: The explorer MUST return an empty result for a session with no
  flows (empty-state-first), for both sources.

**Hash-chain verification**

- **FR-007**: The verification pane MUST read the commit chain and report:
  committed range, checkpoint ticks, whether ticks are contiguous, whether every
  hash is the expected length, and any gaps or duplicate ticks — plus an overall
  valid/invalid verdict and an anomaly list.
- **FR-008**: The verification MUST NOT re-run the engine; it verifies the
  persisted chain's structural integrity only, and its per-tick hashes MUST equal
  those read directly from the commit record (so live and archive agree).
  **Clarified (2026-07-04 fix)**: "structural integrity only" means
  contiguity, checkpoint cadence, and hash FORMAT (length) — it does NOT mean
  hash CONTENT is recomputed or compared. `tick_commit.determinism_hash` is a
  shallow identity hash (`sha256(session_id:tick:seed)`) whose `seed` input is
  not reliably recoverable from persisted session metadata for headless-runner
  sessions, so genuine content verification is not implementable without a
  schema change or re-running the engine (the latter forbidden by this same
  FR). The result payload and UI MUST label this scope explicitly
  (`verification_scope: "structural"`) and MUST NOT present it as
  content/tamper verification.

**Conservation-audit browser**

- **FR-009**: The browser MUST return conservation-audit rows for a session over
  a bounded tick range: scale, invariant name, computed/expected/residual value,
  and severity.
- **FR-010**: The browser MUST support filtering to non-OK severities.
- **FR-011**: The browser MUST return an empty result when no audit rows exist.

**Two-session diff**

- **FR-012**: The diff MUST return two sessions' national series aligned by tick
  with a per-tick value delta, plus a commit-chain summary comparison (range,
  count).
- **FR-013**: The diff MUST handle sessions of differing lengths and a session
  diffed against itself (all-zero deltas) without error.

**Cross-cutting (inherited from 096)**

- **FR-014**: All 099 endpoints MUST be flag-gated by `OBSERVATORY_ENABLED`
  (404 when off, before auth/DB), auth-gated, and return a clean 503 on a data
  error with no internals leaked (server-side logged).
- **FR-015**: 099 MUST add no new tables and change no simulation dynamics; it is
  a read-only observer. No new third-party dependency.

**Dashboard**

- **FR-016**: The Observatory UI MUST add deep-pane views for verification,
  boundary flows, conservation audits, and two-session diff, plus a source
  (live/archive) selector, loaded within the existing lazy Observatory chunk.

### Key Entities *(include if feature involves data)*

- **Source**: `live` (runner Postgres) or `archive` (exported Parquet under the
  archive root) — the read backend for any Observatory query.
- **Boundary flow**: one cross-boundary transfer (source/dest node + kind, flow
  type, magnitude) at a tick.
- **Chain verification**: a verdict over a session's commit chain (range,
  checkpoints, contiguity, anomalies).
- **Conservation audit**: a per-tick invariant record (scale, name,
  computed/expected/residual, severity).
- **Session diff**: aligned national series + commit-chain comparison of two
  sessions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The known archived 520-tick session's commit chain renders fully
  via `source=archive` (520 ticks, checkpoints at every 52nd tick), read-only.
- **SC-002**: For any session, the per-tick commit hashes returned by
  `source=live` and `source=archive` are identical (100% match).
- **SC-003**: Hash-chain verification reports a well-formed session valid with
  zero anomalies, and flags an introduced gap 100% of the time.
- **SC-004**: The boundary explorer and conservation browser both return a clean
  empty result (not an error) for a zero-row session.
- **SC-005**: A two-session diff aligns national series by tick and reports range
  and commit-count differences.
- **SC-006**: 099 changes no existing product test outcome and no simulation
  baseline; archive files are never modified (0 writes).

## Assumptions

- The archive layout is one directory per session under the archive root, each
  holding `<table>.parquet` files plus an `archive_manifest.json` (per
  `tools/archive_sessions.py`). A table with zero rows has no Parquet file (its
  manifest entry has `file: null`).
- The embedded analytical engine used for archive reads is already a project
  dependency (`duckdb`); `pyarrow` is likewise present. No new deps are added.
- Archived sessions store the RAW tables (`dynamic_hex_state`, `tick_commit`,
  `boundary_flow_register`, `conservation_audit_log`, …), NOT the aggregate
  views; archive-source series/verification reconstruct over the raw tables. The
  archive does not carry `hex_spatial_map`, so archive-source state/county
  aggregation is out of scope (national + commit chain + boundary + audit are the
  archive-supported reads); documented as a known limitation. The same
  `hex_spatial_map` gap ALSO blocks a faithful `hex/` archive reconstruction
  (2026-07-04 fix): `dynamic_hex_state.county_fips`/`state_fips`/`region_id`
  are persisted NULL (verified empirically against the real archived session),
  so `hex/?source=archive` returns an explicit `501` rather than a
  spatially-blank frame — tracked as an owner-review item, not implemented.
- "Recompute the hash chain" means verify the persisted chain's structural
  integrity (contiguity, cadence, format, gaps) — not re-execute the engine (the
  Observatory only reads). This keeps every claim verifiable against persisted
  data.
- Deep-pane UI reuses the existing Observatory chunk, chart component, and visual
  language (Tufte-minimal, palette tokens).
