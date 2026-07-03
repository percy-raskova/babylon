# Feature Specification: Session Partitioning + Local Archival + Hex Normalization

**Feature Branch**: `feature/087-storage-foundations` (program branch)
**Created**: 2026-07-03
**Status**: Draft
**Parent program**: Storage & Database Scaling Program, Sprint 2 (units S2 + S3). Sprint 1 = spec-087 (landed). Owner decisions inherited: national res-7 ceiling, verifiable+replayable trackability, archives **local only**.

## Why

Finished runs accumulate forever in `babylon_test` (~7 GB per canonical Michigan run; 71 GB accumulation caused the 2026-07-03 DiskFull). `archival.py` is 4 `NotImplementedError` stubs (spec-037 Phase 8 T045–T048). Mass `DELETE` of a finished session would create GBs of dead tuples and autovacuum debt; `DROP PARTITION` is instant. Separately, every hex row re-writes 3 immutable TEXT keys (`county_fips`, `state_fips`, `region_id`) every tick — pure duplication (~15–20 B/row).

## Functional Requirements

### S2a — LIST(session_id) partitioning (migration 0026)

- **FR-001**: The 8 per-tick table families (`dynamic_hex_state`,
  `dynamic_external_node_state`, `boundary_flow_register`,
  `conservation_audit_log`, `dynamic_consciousness_state`,
  `dynamic_demographics_state`, `dynamic_employment_state`,
  `dynamic_relationship_state`) become `PARTITION BY LIST (session_id)`.
- **FR-002**: The conversion migration MUST be idempotent under the
  runner's apply-all-every-start policy (`_apply_migrations`): skip when
  already partitioned; on the converting pass, preserve existing rows
  (copied into the DEFAULT partition) and re-apply append-only REVOKEs.
- **FR-003**: Because views bind to table OIDs, the converting pass drops
  the 5 dependent views (`v_county/state/national_value_aggregate`,
  `v_global_phi_balance`, `view_runtime_trace_emission`); a new
  always-run migration `0030_views_current.sql` is the canonical view
  file recreating all 5 at the end of every pass (0027 is reserved for
  S3's `hex_map`). Later specs edit 0028, never 0015/0019/0023.
- **FR-004**: Each table gets a DEFAULT partition so writers that skip
  session init (unit/integration tests inserting directly) keep working.
- **FR-005**: `initialize_session` creates per-session partitions
  (`<table>_p_<uuid.hex>`) before any dynamic-table write (external-node
  bootstrap writes tick 0). New module
  `src/babylon/persistence/partitioning.py`: `ensure_session_partitions`
  (idempotent, graceful no-op on pre-0026 databases) and
  `drop_session_partitions` (instant purge primitive for S2b).

### S3 — Hex row normalization (migration 0027, non-destructive)

- **FR-006**: New static table `hex_map(h3_index PK, county_fips,
  state_fips, region_id)` populated idempotently at hex hydration
  (`INSERT ... ON CONFLICT DO NOTHING`; the mapping is immutable per hex).
- **FR-007**: `dynamic_hex_state.county_fips/state_fips/region_id` become
  NULLable (NOT NULL dropped in-migration) and writers stop populating
  them; NULLs cost ~nothing on disk. Columns are NOT dropped — the
  re-run-every-start migration architecture makes destructive column
  drops break earlier view-DDL passes; this is a recorded deviation from
  the program plan's "move columns out" phrasing with identical byte
  effect. (h3 TEXT→BIGINT deferred to the national dress rehearsal —
  ~7% of row vs. high churn; recorded in the ADR.)
- **FR-008**: All 5 views in 0028 source spatial keys from `hex_map`
  (JOIN on `h3_index`); `trace.csv` stays byte-identical.
- **FR-009**: The determinism-hash input is computed from in-memory state
  and MUST NOT change (verified by the e2e gate's Δ=0.000%).

### S2b — Local archival lifecycle (`archival.py`)

- **FR-010**: `export_session_to_parquet(pool, session_id, output_dir)` —
  one Parquet file (zstd) per table family with rows for the session,
  plus `archive_manifest.json` (row counts, sha256 per file, session
  metadata). Default archive root `/media/user/data/babylon-archives/`
  overridable via `BABYLON_ARCHIVE_ROOT`.
- **FR-011**: `purge_session(pool, session_id)` — refuses unless a
  verified export manifest is supplied; drops the session's partitions
  (instant) and DELETEs session rows from non-partitioned leftovers
  (`contradiction_field`, `immutable_reference_*` copies, `game_session`
  kept with archived status where the table exists).
- **FR-012**: `query_archived_session(archive_dir)` — DuckDB view over
  the Parquet files; returns a connection/relation for analytics.
- **FR-013**: `upload_to_r2` is retired per the owner's local-only
  ruling: it raises `NotImplementedError` with a message pointing to the
  ruling (kept only because `test:int-pg` imports the symbol).
- **FR-014**: `tools/archive_sessions.py` CLI + mise tasks
  (`sim:archive`, `sim:archived`) drive export→verify→purge for
  completed sessions.

## Success Criteria

- **SC-001**: Converting pass on a populated DB preserves all rows;
  steady-state pass is a no-op; fresh-DB pass converges to the same
  schema. `qa:e2e-regression` Δ=0.000% and `qa:storage-budget` pass on
  the partitioned + normalized schema.
- **SC-002**: After a 5-tick run: export → verify → purge leaves zero
  session rows in Postgres, the session's partitions gone, and
  `query_archived_session` returns the same per-table row counts the
  manifest recorded.
- **SC-003**: Fips TEXT keys are NULL in newly-written hex rows;
  `hex_map` holds exactly one row per hydrated hex; trace.csv unchanged.
- **SC-004**: Integration tests cover: partition routing (session rows in
  session partition, stray rows in DEFAULT), idempotent
  ensure/drop_session_partitions, archival roundtrip.
