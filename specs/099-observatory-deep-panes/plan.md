# Implementation Plan: Observatory Deep Panes

**Branch**: `099-observatory-deep-panes` | **Date**: 2026-07-04 | **Spec**: [spec.md](./spec.md)
**Stacks on**: spec-096 (branches off `38adfa03`). Provisional program number 099.

## Summary

Add five deep diagnostic panes to the Observatory and a `source=live|archive`
selector on every read. `live` keeps 096's read-only `sim` Postgres alias;
`archive` reads a session's exported Parquet under `BABYLON_ARCHIVE_ROOT` via
DuckDB (already in pyproject), read-only. New endpoints: boundary-flow explorer,
hash-chain verification, conservation-audit browser, two-session diff. Zero new
tables, zero dynamics change, no new deps.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.7 (frontend).
**Primary Dependencies**: Django + DRF; **DuckDB** (^1.4.4, already present) for
archive reads; React 19 + Recharts (frontend). No new deps.
**Storage (read-only)**: `live` = Postgres `sim` alias (spec-062 `dynamic_*` +
087–089); `archive` = Parquet under `BABYLON_ARCHIVE_ROOT`
(`/media/user/data/babylon-archives`), one dir/session (layout per
`tools/archive_sessions.py`; reader `babylon.persistence.archival.
query_archived_session`).
**Testing**: pytest (`tests/unit/observatory/` fast; `tests/integration/
observatory/` Postgres + a real archived session `edf07b2e-…`), Vitest + MSW.
**Project Type**: Web application (Django + React).
**Constraints**: STRICT read-only both sources; ownership law (Lane O writes only
`web/observatory/**`, `web/frontend/src/observatory/**`, settings, one App.tsx
line, `web/HOW-TO-LOCAL-DEV.md`); `src/babylon/**` is READ-only (import
`query_archived_session`, never edit it); no engine/`web/game` edits.
**Scale/Scope**: 4 new endpoints + `source` param on 096's; 4 new React panes +
a source selector; archive reader module; docs.

## Constitution Check (v2.7.0)

Read-only observer; changes no dynamics, adds no persistence. Same disposition
as 096.

| Article | Binds? | Disposition |
|---|---|---|
| **II.11 Subsystem Table Ownership** (P1) | YES — central | Reads the runner-owned schema through declared interfaces only (the views + `tick_commit` + the append-only `boundary_flow_register` / `conservation_audit_log` registers). Archive reads go through the sanctioned `query_archived_session` DuckDB path over exported Parquet. No direct mutation; read-only both sources. **PASS**. |
| **III.7 Determinism Hash** (P0) | Reads/verifies | The verification pane READS and structurally validates the `tick_commit` III.7 chain; it computes no new hash and changes no dynamics. Per-tick hashes returned equal the persisted ones (live≡archive). **PASS**. |
| **VII Visual Design** (P2) | YES — UI | Panes reuse Recharts + Tufte-minimal + palette tokens; severity uses semantic color (crimson=alarm, amber=warn). No chartjunk. **PASS**. |
| **III.1 No Magic Constants** (P1) | Minor | Checkpoint cadence (52) is imported from `babylon.persistence.delta.CHECKPOINT_EVERY_TICKS` (read-only import), not hardcoded; archive root from env. **PASS**. |
| **III.8 Data Grounding** (P0) | Read-only | Every value traces to a persisted row (Postgres or Parquet). **PASS**. |
| **X Deployment** | Archive | Local-only archives (spec-088 ruling); DuckDB over local Parquet, no R2. **PASS**. |
| Amendments K/L, I.20, II.12 | No | Engine-only; N/A. |

**Read-only guarantee (load-bearing)**: `live` via the `default_transaction_
read_only=on` alias + `SimDatabaseRouter` (096); `archive` via DuckDB
`SELECT`-only over Parquet (`query_archived_session` opens a fresh in-memory
DuckDB, creates views over `read_parquet(...)`, never writes files). No new
tables; `makemigrations observatory --check` stays clean (still zero models).

## Project Structure (Lane O ownership only)

```text
web/observatory/
├── sources.py        # NEW: Source abstraction — live (sim cursor) | archive (DuckDB)
├── deep_queries.py   # NEW: boundary / verify / conservation / diff query builders
├── deep_views.py     # NEW: the 4 deep-pane endpoints (+ source param)
├── views.py          # EXTEND: add source= to 096's endpoints via sources.py
├── urls.py           # EXTEND: register deep-pane routes
└── (db.py/router.py/queries.py unchanged except source wiring)

web/frontend/src/observatory/
├── deepApi.ts        # NEW: typed client for deep-pane endpoints + source param
├── panes/            # NEW: VerificationPane, BoundaryPane, ConservationPane, DiffPane
├── SourceSelector.tsx
├── ObservatoryPage.tsx  # EXTEND: tabbed panes + source selector
└── __tests__/        # MSW contracts for the deep endpoints

tests/unit/observatory/         # source resolution, verify logic, gating
tests/integration/observatory/  # + archive read against edf07b2e-…
web/HOW-TO-LOCAL-DEV.md         # + source=live|archive doc
```

**Structure Decision**: A `sources.py` abstraction returns a uniform read
interface for either backend; `live` runs the Postgres-view SQL (096), `archive`
runs DuckDB reconstruction SQL over the raw Parquet. The 4 deep panes and the
`source` param on 096's endpoints both go through it. Keeps the read-only
boundary in one place per source.

## Key Design Decisions

1. **Archive reader** = `babylon.persistence.archival.query_archived_session`
   (imported read-only) — opens in-memory DuckDB, `CREATE VIEW <table> AS SELECT
   * FROM read_parquet(...)` per file, runs SQL. Archive dir resolved as
   `<BABYLON_ARCHIVE_ROOT>/<session_id>/`.
2. **Archive series/verify** reconstruct over raw `dynamic_hex_state` +
   `tick_commit` Parquet with the same as-of window logic (national scope only —
   archive lacks `hex_spatial_map`; documented). Commit chain / boundary / audit
   read their raw tables directly.
3. **`source` param**: `?source=live|archive`; invalid → 400; `archive` for a
   missing session dir → empty result.
4. **Verification** = structural chain integrity (contiguity, checkpoint cadence
   via `CHECKPOINT_EVERY_TICKS`, hash length, gaps/dups) — no engine re-run.
5. **Frontend**: deep panes as tabs in the existing lazy Observatory chunk; a
   source selector at the shell level threads `source` into every fetch.

## Testing Strategy (TDD, red-first)

- **Unit (no DB)**: source-selector parsing/validation; archive-dir resolution;
  chain-verification pure logic (well-formed vs gap vs bad-cadence fixtures);
  deep endpoint gating (404-off / 403-unauth); deep query SQL sweeps.
- **Integration (Postgres + archive)**: `source=live` deep endpoints over a
  seeded session (boundary empty-state, audit rows, verify ok, diff); **archive**
  read of the real `edf07b2e-…` session — commit chain 520 ticks + verification
  valid + national series, all read-only.
- **Frontend (Vitest + MSW)**: contract test per deep endpoint + source selector;
  empty-state renders; verification verdict renders.

## Complexity Tracking

No constitutional violations. The one genuinely new mechanism (DuckDB archive
reads) reuses the existing sanctioned `query_archived_session`; the source
abstraction is the minimum needed to serve two backends from one endpoint set.
