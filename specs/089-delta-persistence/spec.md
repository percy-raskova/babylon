# Feature Specification: Delta Persistence with Checkpoint Frames + tick_commit Hash Chain

**Feature Branch**: `feature/087-storage-foundations` (program branch)
**Created**: 2026-07-03
**Status**: Draft
**Parent program**: Storage & Database Scaling Program, Sprints 3–4 (unit S1 — THE lever). Prior: spec-087 (compose+observability), spec-088 (partitioning+normalization+archival).

## Why

`WorldStateBridge.persist_tick` re-emits the tick-0 hex template every tick
(`bridge.py`: "re-emit cached templates with the current tick") — measured:
**zero of 1,045 hex rows change any value across consecutive ticks**; hex
economics are static-per-year by design (`project/02`). That is 48,827
duplicate rows/tick statewide (~7 GB/run) and ~450 GB/run at national res-7.
ADR031 explicitly deferred diff-based storage "until needed"; the national
ceiling makes it needed.

## Functional Requirements

### S1a — tick_commit (the commit marker + hash chain)

- **FR-001**: New partitioned table `tick_commit(session_id, tick,
  determinism_hash, hex_rows_written, is_checkpoint, created_at_utc)`
  (migration 0029), appended in the SAME transaction as the envelope by
  `persist_tick_atomic`. It is simultaneously: the per-tick commit marker
  (a tick with zero changed hexes still commits a row), the queryable
  Constitution-III.7 hash chain, and the dense tick spine for the as-of
  views. Trackability strictly improves.
- **FR-002**: `get_last_committed_tick` reads `MAX(tick) FROM tick_commit`,
  falling back to `dynamic_hex_state` for pre-0029 sessions ("every
  committed envelope writes at least one hex row" no longer holds).
- **FR-003**: The hex hydrator's tick-0 envelope does NOT write a marker
  (its placeholder hash is all-zeros); the bridge's tick-0 re-delivery
  writes the real one. `persist_tick_atomic` gains
  `write_commit_marker: bool = True`.

### S1b — Delta emission in the bridge

- **FR-004**: `persist_tick` builds the full candidate frame (auditor and
  determinism inputs are frame-level and MUST keep seeing it), then
  enqueues into the envelope only rows whose **value tuple** (c, v, s, k,
  3 substrate stocks, internet, surveillance — spatial keys excluded)
  differs from the last-emitted tuple for that hex.
- **FR-005**: Every `CHECKPOINT_EVERY_TICKS = 52` ticks (tick 0, 52, …)
  the full frame is emitted regardless, bounding reconstruction depth to
  one year of deltas (changes cluster at year boundaries anyway).
- **FR-006**: Emission is deterministic and idempotent: re-running a tick
  re-emits the same rows; `ON CONFLICT DO NOTHING` + tick_commit keep
  re-delivery a no-op (spec-056 monotonicity preserved).
- **FR-007**: External-node rows (9/tick) and the county trio stay dense —
  they are the cheap tick spine for LEFT JOINs and cost nothing.

### S1c — As-of reconstruction (read side)

- **FR-008**: The 0028 canonical views are rewritten fill-forward so every
  `(session, tick, county)` still yields a row over sparse hex data:
  county aggregates computed at hex-change ticks (interval join), then
  filled across the dense spine (`tick_commit` ∪ hex-row ticks, so
  pre-S1 sessions keep working). `_query_trace`,
  `_query_terminal_aggregates`, `_county_terminal_snapshot` read the view
  and need no changes.
- **FR-009**: A full-resolution reconstruction view `v_hex_state_asof`
  (session, tick, h3, values) is the declared hex-level history read
  interface (FR-019-compliant: on-read, hex remains source of truth).
- **FR-010**: `sim:status` sources tick/520 and bytes-per-tick from
  `tick_commit` (hex-table fallback).

## Success Criteria

- **SC-001**: 5-tick tri-county run writes 1,045 hex rows total (tick-0
  checkpoint) instead of 5,225 — and `trace.csv` is **byte-identical**
  (sha256 vs the pre-S1 bundle; county sums are order-independent because
  hydrated hex values are uniform within a county — any future ULP drift
  from heterogeneous engine mutations goes through the Amendment-L
  written-proof + baseline-regeneration path).
- **SC-002**: `qa:e2e-regression` Δ=0.000%; `qa:storage-budget` passes
  (under budget); canonical Michigan projection drops from ~25.4M to
  ~0.6M hex rows (10 checkpoints + deltas).
- **SC-003**: Property test: for a randomized sparse write history,
  `v_hex_state_asof` at every tick ≡ the dense frame that produced it.
- **SC-004**: Re-delivering an already-persisted tick changes nothing
  (idempotency test); a tick with zero changed hexes still advances
  `get_last_committed_tick`.

## Out of scope

`boundary_flow_register` delta treatment (flows are real per-tick
information; Sprint 5 assesses), archived-Parquet as-of helper for DuckDB
(archive stores deltas+checkpoints = complete information), h3 BIGINT.
