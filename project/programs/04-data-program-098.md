# 04 — Data Program: spec-098 Reference-DB Build Pipeline

Interleave this with catalog work per the ratified sequencing. Owner
decisions (2026-07-02): loaders live in the **babylon-data repo**
(`/home/user/projects/game/babylon-data`); the trove DB is canonical; the
in-repo `data/sqlite` directory symlink is how code reaches it.

## Context (why this program exists)

The 3NF reference DB (`marxist-data-3NF.sqlite`, ~5 GB) was originally built
by ~25 loaders that were **deleted from the babylon repo in spec-037**
(commit `4ce7c96a` "remove data layer"). The DB itself survived, but the
pipeline to rebuild it did not. Spec-086 rebuilt the QCEW slice properly and
established every pattern the remaining loaders need. Spec-098 generalizes:
recover/rewrite the remaining loaders into babylon-data, so the whole DB is
reproducible from staged sources.

## What spec-086 already proved (reuse these patterns)

All in `/home/user/projects/game/babylon-data/src/babylon_data/qcew/`:

- **Streaming ingest**: pandas chunked reads of multi-GB CSVs
  (`singlefile.py` — header pinning, row classification with explicit
  exclusion classes, halt-on-unknown).
- **Staged rebuild + atomic swap** (`writer.py`): build `__new` tables from
  the canonical ORM DDL (`src/babylon/reference/schema.py` — babylon owns the
  schema, babylon-data imports it one-way), swap with `__pre_<spec>` backup,
  rollback + drop-backup commands.
- **Resumable checkpoints**: `ingest_checkpoint` rows
  (source/year/state_fips/table_id), `pending_years`, purge-legacy.
- **Determinism**: `logical_table_hash` = SHA-256 over an ordered projection,
  tolerant of physical-schema drift (introspects ORM∩physical columns).
- **Audit contract**: Pydantic report models mirroring a JSON Schema
  (`specs/086-qcew-loader-imputation/contracts/audit_report.schema.json`),
  jsonschema-validated on write, plus human Markdown rendering.
- **CLI shape**: `python -m babylon_data.qcew` via `mise run data:qcew --`
  (argparse; exit 0/1/2/130; `--years`, `--dry-run`, `--drop-backup`, …).
- **Test fixture pattern**: verbatim-header synthetic CSV builders +
  in-memory ORM engine seeding (`tests/fixtures/qcew/`).

## The work

1. **Inventory** the deleted loaders: `git show 4ce7c96a^ --stat` and the
   `mutants/` directory history list them (~24 remaining: BEA I-O, BEA REIS,
   LODES OD, TIGER, FCC broadband, FRED, Census, ATUS, Z.1, Hickel/Ricci,
   FAF freight, Natural Earth, …). Cross-check against tables actually
   present: `sqlite3 data/sqlite/marxist-data-3NF.sqlite ".tables"`.
1. **Prioritize by consumer**: tables read by the engine/hydrators first
   (`ReferenceDataCache.hydrate` sources — bea_io, melt_tau, basket_gamma,
   erdi, hickel_drain, ricci_unequal, faf_freight, qcew ✅, bea_reis_rent,
   fred_rates — the hydrator log names them), then analysis-only tables.
1. Per loader: source staging location under `/media/user/data/babylon-data/`,
   module in babylon-data mirroring the qcew package layout, checkpoints,
   audit report, `mise run data:<name>` task, gated integration tests, and a
   reconciliation gate against published totals where the source publishes
   any (the SC-001-style ±2% pattern; spec-097 documents the imputation
   re-basing precedent).
1. **Packaging/CI** (deferred from 086): babylon-data gets its own
   pyproject (exists, minimal PEP 621), a real test workflow, and eventually
   a pinned release the babylon repo consumes instead of the dev symlink.
   Keep the one-way dependency: babylon-data imports babylon's ORM, never
   the reverse.
1. **Schema ownership**: additions to `src/babylon/reference/schema.py`
   happen in the babylon repo (like 086's `is_imputed` + rollup table), with
   migration/backfill scripts in babylon-data.

## Traps

- The `data/sqlite` symlink is NOT in git — fresh clones/worktrees must
  recreate it (`ln -sfn /media/user/data/babylon-data/sqlite data/sqlite`).
- SQLite writes on the live DB while a canonical run reads it: don't. Stage,
  then swap.
- `VACUUM INTO` is the safe way to copy the 5 GB DB for experiments (~60 s).
- Suppression (`disclosure_code`) exists in other BLS/BEA products too —
  audit each source for the QCEW-style silent-zero trap before trusting
  totals (this is the class of bug that motivated 086: 67–72% of county
  6-digit QCEW cells were suppressed zeros).
