# Research: QCEW Loader Reimplementation with Synthetic Suppression Imputation

**Spec**: `specs/086-qcew-loader-imputation/spec.md` (amended 2026-07-02)
**Date**: 2026-07-02
**Method**: Three parallel read-only investigations — (R1) recoverable loader archaeology in the babylon-data repo, (R2) staged BLS source files + live reference DB, (R3) consumer contracts + spec-067/068 house patterns.

---

## R1. Empirical findings (verified, not assumed)

### Source files (staged, complete)

- `/media/user/data/babylon-data/qcew/` holds all 15 years 2010–2024 as BLS **annual-averages singlefile** CSVs (`YYYY.annual.singlefile.csv`, ~506–532 MB, 3.60–3.65 M rows each) plus the original ZIPs. Downloaded 2026-01-30. FR-011 (no network) is satisfiable as-is.
- 38-column layout is **byte-identical across 2010 and 2023 headers**: `area_fips, own_code, industry_code, agglvl_code, size_code, year, qtr, disclosure_code, annual_avg_estabs, annual_avg_emplvl, total_annual_wages, taxable_annual_wages, annual_contributions, annual_avg_wkly_wage, avg_annual_pay`, then `lq_*` (8) and `oty_*` (15) blocks. `qtr="A"`, `size_code="0"` on every county row.
- County agglvl codes present: **70** (county total, own_code 0 / industry "10"), **71** (county × ownership, own 1/2/3/5), 72–73 (domain/supersector), **74–78** (NAICS 2- through 6-digit). At agglvl 78 only own codes {1,2,3,5} appear.
- **Suppression semantics confirmed**: `disclosure_code="N"` ⇒ `annual_avg_emplvl`, `total_annual_wages`, and all wage/pay fields are **literal 0** (not blank), while `annual_avg_estabs` **remains populated**. Non-suppressed rows carry `disclosure_code=""`. Example (Wayne 26163, 2010, agglvl 78): `"26163","2","541511","78","0","2010","A","N",7,0,0,...`.
- **Suppression magnitude (full-file scans)**: agglvl-78 rows with `disclosure_code='N'` = **72.19 % in 2010** (730,390 / 1,011,704) and **67.24 % in 2023**. This is the fraction of *cells*; the employment *mass* withheld is the 10–30 % county-total gap spec-067 measured.
- **Wayne County ground truth confirmed**: agglvl-70 row for 26163/2010 shows `annual_avg_emplvl = 657,150` exactly (vs post-067 leaf sum 561,173 = −14.6 %).

### Live reference DB (`/media/user/data/babylon-data/sqlite/marxist-data-3NF.sqlite`, via the repo's `data/sqlite` directory symlink)

- `fact_qcew_annual` physical DDL **diverges from the ORM**: the physical table is a plain rowid table with **no primary key and no unique index** (only 3 non-unique indexes), while `FactQcewAnnual` (schema.py:1270) declares composite PK `(county_id, industry_id, ownership_id, time_id)`. Re-running any loader today would silently duplicate rows.
- **No provenance column exists**; `disclosure_code` is the only marker, stored as `'N'` (suppressed) vs `NULL` (disclosed). Suppressed rows store employment/wages as **literal 0** — poisoning every SUM (the spec's core defect).
- Contents: 15,097,464 rows, **agglvl-78 leaves only**, own codes {1,2,3,5}, all 15 years (per-year ≈ 0.99–1.04 M). Exact reconciliation for 2010: file agglvl-78 (1,011,704) − 914 US Virgin Islands rows (78xxx fips absent from dim_county) = 1,010,790 = DB count.
- `ingest_checkpoint` exists with `UNIQUE(source_code, year, state_fips, table_id, race_code)`; the old loader's qcew rows abuse it: `year=0`, `table_id='file'`, and a **16-hex path hash stored in `state_fips VARCHAR(2)`**; only 14 rows for 15 loaded years.
- Dims: `dim_industry` has `naics_level` with 1,382 level-6 codes (superset of any single year's ~1,193 — vintage-union already seeded); `dim_ownership` has 7 rows (own 0,1,2,3,5,8,9 — titles are placeholders); `dim_time` keys years (annual rows: `is_annual=1`, month/quarter NULL); `dim_county` 3,285 rows keyed by 5-char fips.
- **County-identity defects in current data**: (a) Shannon→Oglala Lakota: 2015 file publishes BOTH 46113 and 46102 with near-duplicate data, and the DB loaded **both** (2015 double-count; history split across two county_ids); (b) the 2024 file switches Connecticut from legacy counties 09001–09015 to planning regions 09110–09190 and the DB loaded the new codes (split identity); (c) US Virgin Islands rows silently dropped; (d) **`SS999` "unknown/undefined county" pseudo-areas were loaded** (~25,638 agglvl-78 rows in 2010 alone) under auto-created dim_county rows named "County 09999".
- Pseudo-FIPS inventory per file: `US000/USCMS/USMSA/USNMS`, 1,070 `C####` MSA codes, 53 `SS000` statewide, 49 `SS999` — none belong in county grain (FR-014).

### Recoverable loader (babylon-data repo)

- `/home/user/projects/game/babylon-data` = single-commit git repo (`f57c987`, 2026-03-01), content **byte-identical** to monorepo `4ce7c96a^:src/babylon/data/` and to `mutants/src/babylon/data/` — no divergence; provenance settled. **Zero packaging** (no pyproject/README/lockfile), package dir hyphenated (`src/babylon-data/`).
- `qcew/loader_3nf.py` (1,562 lines, `QcewLoader(ApiLoaderBase)`): pandas-chunked singlefile path (100k chunks, bulk `insert()`, flush every 5 chunks); routes agglvl 70–78→county, 20–28→state, 30–58→metro fact tables; **loads every agglvl and every own_code** (the DB's leaves-only state is spec-067's post-hoc DELETE, not loader filtering); national 10–18 silently dropped.
- **Suppression handling: none** (`rg -i 'suppress|imput'` = zero hits). `disclosure_code` copied verbatim; zeros pass through `safe_int(0)→0`. The per-field `lq_disclosure_code`/`oty_disclosure_code` flags are discarded.
- Known defects: **reset+file-mode checkpoint bug** (reset clears per-year checkpoints but file checkpoints live under `year=0` → after reset, all files are skipped as "completed" → empty tables); path-hash (not content-hash) checkpoints; `_get_or_create_county` fabricates placeholder counties (source of the SS999/dim pollution); `downloader.get_csv_path()` filename mismatch; file mode parses **every** CSV in the directory regardless of requested years.
- Import closure: all intra-repo imports use absolute `babylon.data.*` (broken until re-homed); 3 external modules missing for the minimal QCEW cut (`babylon.exceptions`, `babylon.utils.exceptions`, `babylon.utils.log`) — all tiny and vendorable. `qcew/__init__` imports legacy `qcew/schema.py` (dead denormalized tables) which drags in the entire census subpackage; severing that one import collapses the closure.
- Load path essentially untested (only `_handle_api_error` has a unit test).

### Import mechanism + consumers (babylon repo)

- **`babylon_data` already imports today**: pyproject `packages = [{include = "babylon_data", from = "src"}]` + a **committed symlink `src/babylon_data → /media/user/data/babylon-data`** (the trove). The trove copy has `loader_base.py`, `bea/`, `atus/`, `reference/` — **no qcew loader, no cli** (the `tools/ingest_qcew_full.py` tombstone advertises a `babylon_data.cli` that does not exist). Imports resolve via `PYTHONPATH=src` (mise env); mypy excludes `src/babylon_data/`.
- Runtime consumers of `babylon_data` inside babylon: **none in src/** (docstring mentions only). Tests: `tests/integration/economics/test_tensor_hierarchy.py:84-85` imports `babylon_data.bea.{io_loader,loader_national}` (skip-guarded, `# type: ignore[import-not-found]`).
- `fact_qcew_annual` consumers (FR-010 analysis): every production consumer **SUMs at county-year grain with no `SELECT *`, no disclosure_code filter, no column filters** — `hex_hydrator.py:470-481` (wages→v), `county_aggregation.py:320-397` (employment_proxy + population fallback), `reference_data_cache.py:194-201` (batched), `postgres_initialization.py:139-142` (year-window preflight), `share_lookup_service.py:269-287` (per-industry employment, skips NULL). Finer-grain consumers filter `IS NOT NULL`/`> 0` — imputed rows carry non-NULL values so they flow through.
- **Stale-cache hazard**: `economics/adapters.py` persists `_cache_national_wages_bea` (`_CACHE_TABLE_VERSION = 2`) inside the reference DB — this is the DB's one un-mapped table. After imputation rewrites wages, this cache is wrong until dropped or version-bumped.
- Pre-existing breakage (out of 086 scope, flag only): `economics/throughput/adapters.py` and `economics/melt/adapters.py` still query the own_code='0' / naics "10" rollup rows spec-067 deleted → return None/empty today. `throughput/data_sources.py` docstring cites a non-existent `mise run data:qcew` task (086 creates it).
- House patterns to reuse: spec-067 `tools/normalize_qcew_rollups.py` (preflight assertions → own-transaction backup → explicit BEGIN/COMMIT with row-count integrity check → post-validation + Wayne spot-check; **fast strategy**: build `__new` table → drop indexes → double RENAME → recreate indexes; jsonschema-validated JSON+md audit reports to `reports/ingest/`); spec-068 `src/babylon/reference/bea/ingest/` module split (parser / writer with `WriterStats` + vintage supersession / validators / audit_report with `write_to_disk` / `schema_migration.ensure_*_columns` idempotent ALTERs) and `tools/load_bea_io.py` CLI shape (`--years START-END`, `--dry-run`, `--rollback`, stage functions setting SC-gate booleans on the audit report).
- Test conventions: unit fixtures build in-memory SQLite from ORM metadata subsets (`NormalizedBase.metadata.create_all(engine, tables=[...])`); integration `tiny_qcew_fixture` hand-written DDL + 6 seeded rows; live-DB tests skip at collection when the reference DB is absent; contract tests validate emitted audit JSON against the schema.
- mise task registration pattern: `[tasks."data:bea-load"]` with usage-crate args and `${usage_x:+--flag}` conditional expansion. No `data:qcew` exists yet.

---

## R2. Decisions

### D1. Rewrite the load path; do not restore `QcewLoader`

**Decision**: Write a new, purpose-built loader (parse → filter → impute → write) in the babylon-data package. The old `loader_3nf.py`/`parser.py` remain in place untouched as provenance/reference; the new code does not import them.
**Rationale**: The old loader's value was its pandas singlefile streaming pattern — trivially re-derived. Its behavior is wrong for 086 on every axis that matters: loads all agglvls/ownerships (067 then deleted 65 % of rows post-hoc), no suppression handling, fabricates dim_county placeholder rows (the SS999 pollution), reset+checkpoint bug, path-hash checkpoints abusing `state_fips`, untested load path, and a legacy-schema import that drags in the census subpackage.
**Alternatives considered**: (a) Patch `QcewLoader` in place — rejected: the fixes touch every method; the imputation stage has no home in its architecture; its test coverage is ~zero so "patch" is a rewrite with worse ergonomics. (b) Restore into `src/babylon/reference/` — rejected by owner decision 2026-07-02 (loader home = babylon-data).

### D2. Minimal viable packaging = rename + pyproject + trimmed root `__init__`; babylon consumes via the existing symlink mechanism, repointed

**Decision**: In `/home/user/projects/game/babylon-data`: `git mv src/babylon-data src/babylon_data`; add a minimal `pyproject.toml` (PEP 621, `requires-python >= 3.12`, deps: sqlalchemy, pandas; no publish config); replace the package root `__init__.py` with a docstring-only module (no eager `loader_base` import chain, so `import babylon_data.qcew.<new module>` never touches legacy broken imports). In babylon: repoint the committed symlink `src/babylon_data` from the trove to `/home/user/projects/game/babylon-data/src/babylon_data`. No pyproject changes in babylon.
**Rationale**: The symlink + `PYTHONPATH=src` + `packages` include is the mechanism that already works (restored per ADR-037) and is CI-neutral: in CI the symlink dangles exactly as it does today, and babylon_data-dependent tests skip via the established data-dependent-precondition pattern. Repointing moves the import target from an **un-version-controlled trove** to the **git repo** — code under version control is non-negotiable (the spec exists because un-versioned deletion lost the loaders once already). A poetry path-dependency was considered as the literal reading of the spec's "path dependency" wording — rejected for 086 because it breaks `poetry install` wherever `../babylon-data` is absent (CI, fresh clones) and buys nothing the symlink doesn't already provide; spec-098 (remote + CI for babylon-data) is the right time for a real dependency declaration.
**Consequences**: trove modules (`babylon_data.bea`, `babylon_data.atus`) leave the import path. Verified consumers: only `tests/integration/economics/test_tensor_hierarchy.py:84-85` (skip-guarded). A verification task will confirm those tests skip (not error) post-repoint; the code repo's own `bea/` copies raise ImportError on their broken `babylon.data.*` imports, which the skip guard treats identically to "not installed".

### D3. The new loader imports babylon's canonical ORM; no schema copy

**Decision**: New loader modules import `babylon.reference.schema` (FactQcewAnnual, dims, IngestCheckpoint) and `babylon.reference.database` for sessions. The babylon-data repo's stale `reference/schema.py` copy is not used and not fixed in 086.
**Rationale**: Owner decision + spec Assumption name `src/babylon/reference/schema.py` (95 tables) as the canonical build target; duplicating DDL in the loader (raw SQL or a second ORM) recreates the exact drift this program exists to eliminate (the physical table already drifted from the ORM once — no PK). Dependency direction is one-way (babylon_data → babylon) inside babylon's venv where the loader runs; babylon has no runtime import of babylon_data, so no cycle. Schema ownership across the two repos is a spec-098 question and is explicitly deferred.

### D4. Provenance = row-level `is_imputed` flag; suppressed magnitudes become imputed values, never zeros

**Decision**: Add `is_imputed BOOLEAN NOT NULL DEFAULT 0` (server default `0`) to `FactQcewAnnual`. Disclosed rows: stored verbatim (including true zeros), `is_imputed=0`. Suppressed rows (`disclosure_code='N'`): `establishments` observed (BLS publishes it), `employment`/`total_wages_usd` **imputed**, `avg_weekly_wage_usd`/`avg_annual_pay_usd`/`lq_*` set NULL (never fabricated), `disclosure_code` kept `'N'`, `is_imputed=1`.
**Rationale**: BLS suppression withholds employment+wages jointly at cell level, so one row-level flag captures FR-005 exactly; per-magnitude flags add width without information. `disclosure_code` alone is insufficient — it marks *what BLS withheld*, not *what we reconstructed* (the FR-015 fallback can also impute cells whose constraint was withheld). Derived per-worker fields on imputed rows would be pseudo-precision; NULL is honest and every consumer already tolerates NULL there (R1).
**Alternatives**: separate `employment_imputed`/`wages_imputed` flags (rejected: suppression is cell-joint); sentinel values (rejected: sentinel-in-band is the current bug).

### D5. Persist BLS-published county constraints in a new `fact_qcew_county_rollup` table

**Decision**: New ORM table `fact_qcew_county_rollup` — PK `(county_id, time_id, ownership_id)`; columns `establishments, employment, total_wages_usd, disclosure_code, is_imputed`; rows = agglvl 70 (as ownership_id of own_code '0') + agglvl 71 (own 1/2/3/5) per county-year (~3,270 × 5 × 15 ≈ 245 K rows).
**Rationale**: (a) SC-001/002/004 and the future `qa:data` gate need the published targets queryable forever, not buried in 500 MB source CSVs; (b) the audit report's residual distribution (FR-009) is recomputable at any time; (c) spec-067's "no rollup rows" invariant is preserved — that trap was *mixed grains in one table*; a separate constraints table with its own grain is the spec's own "Published Aggregate (Constraint)" entity made durable; (d) it gives the already-broken throughput/melt total-lookups a correct future home (out of 086 scope, noted for their eventual fix).
**Alternatives**: audit-report-only persistence (rejected: 49 K county-year residuals per load make reports huge and the targets unqueryable); re-reading source CSVs at validation time (rejected: couples validation to 8.3 GB of staged files).

### D6. Imputation algorithm: top-down hierarchical apportionment, establishments-weighted, integer-exact, pure-integer arithmetic

**Decision**: Per (county, year), build the constraint hierarchy from the same singlefile: county total (70) → per-ownership totals (71) → within each ownership a NAICS prefix tree from the published 74→75→76→77→78 rows. Then top-down: at each node with a *known* value `P` (published, or already imputed one level up), compute remainder `R = P − Σ(disclosed children)`; distribute `max(R, 0)` across the suppressed children proportional to `annual_avg_estabs`; when no child has establishments, split equally (documented FR-015 fallback, counted in the audit). Suppressed intermediate nodes are "transparent": their value is the share assigned from above, and they constrain their own children in turn. Rounding: employment and wages are integers; use largest-remainder rounding within each sibling group so children sum **exactly** to the assigned remainder. All arithmetic on ints (wages fit int64 nationally); sibling ordering fixed by `(own_code, industry_code)`.
**Edge rules**: `R < 0` (disclosed children exceed parent — BLS rounding/quirk): imputed siblings get 0, anomaly logged with magnitude. County total (70) itself suppressed: fall back to `Σ(disclosed 71)` plus estabs-apportioned remainder if any 71 is disclosed, else `Σ(disclosed leaves)`; county-year flagged low-confidence in the audit (spec Edge Case 1). Single suppressed sibling: value is `P − Σ(disclosed)` exactly — not an estimate; counted separately in the audit ("exactly recovered").
**Rationale**: This is IPF/RAS degenerate-cased to a tree (each cell has one parent per axis level), so a single top-down pass reconciles exactly — no iteration, no convergence tolerance, trivially deterministic (FR-008). Establishment counts are the only within-cell size signal BLS publishes under suppression and are materially grounded (III.8: an establishment is a workplace; more workplaces ⇒ more employment, all else equal).
**Alternatives**: full iterative RAS over a county×industry matrix (rejected: the constraint structure is a tree per ownership, not a two-margin matrix; iteration adds nondeterminism risk for zero gain); national industry emp-per-estab priors as apportionment basis (rejected for the default: adds a cross-county data dependency and drifts from the local constraint; retained implicitly as nothing — equal split is the simpler documented fallback the spec allows); float arithmetic + final rounding (rejected: FR-008 byte-identical determinism is cheapest with ints end-to-end).

### D7. County identity resolution (FR-013/FR-014)

**Decision**, applied at parse time, all recorded in the audit report:
1. **46113 → 46102** (Shannon → Oglala Lakota, SD): all years' 46113 rows load under 46102's county identity. For 2015 (BLS published both), keep **46102** rows and drop 46113 duplicates.
2. **Connecticut 2024** (planning regions 09110–09190): load as published. dim_county already contains the planning regions; a proper region↔county crosswalk is not county-grain-preserving (regions do not nest in legacy counties) and inventing one would violate substrate fidelity (I.20). The identity discontinuity is flagged prominently in the audit report; the canonical Michigan scope (Constitution IV) is unaffected.
3. **Exclusions** (never enter county tables, counted per class in the audit): `US000/USCMS/USMSA/USNMS`, `C####` MSA codes, `SS000` statewide, **`SS999` unknown-county**, and fips absent from dim_county (US Virgin Islands 78xxx — today's silent drop becomes a logged exclusion).
4. **No dim_county creation**: unknown non-pseudo fips is a hard error listing the codes (the old loader's placeholder-county fabrication is the anti-pattern). Existing orphan "County SS999" dim rows are left untouched (removing dims is out of scope; they simply have no facts).
**Consequence**: current-DB SS999 leaf rows (~25 K/year) disappear from `fact_qcew_annual`. They are not counties; no consumer hydrates them (hydration keys on real county fips). SC-005's national check accounts for the excluded mass explicitly (D8).

### D8. National sanity check (SC-005) definition

**Decision**: Per year, the audit computes `Σ(county leaf employment, post-imputation) + Σ(published totals of excluded pseudo-areas: SS999 per state + US VI)` and compares to the BLS **US000 Total Covered** row from the same file; pass at ±1 %. Both terms reported separately.
**Rationale**: BLS's national total includes unknown-county and VI mass that county grain rightly excludes (D7); adding the published excluded mass back makes the identity exact rather than "close, minus stuff we dropped".

### D9. Write path: staged rebuild + atomic swap; per-year checkpoints; content-keyed resume

**Decision**: Build into `fact_qcew_annual__new` (DDL from the ORM — restoring the composite PK the physical table lost) with one transaction per year: `DELETE` that year's rows from `__new` → insert (deterministic order) → upsert checkpoint → `COMMIT`. Checkpoint rows: `source_code='qcew'`, real `year`, `state_fips='US'`, `table_id='annual_v086'`, `race_code='T'`, `row_count=inserted`. After all years pass in-load validation: single atomic swap (old → `fact_qcew_annual__pre_086` backup, `__new` → canonical, recreate the 3 indexes), same for the rollup table, then `DROP TABLE IF EXISTS _cache_national_wages_bea` and delete the old loader's malformed qcew checkpoints (`year=0`/`table_id='file'`). `--rollback-from-backup` and `--drop-backup` modes mirror the 067 tool.
**Rationale**: 067's fast-strategy swap is the proven pattern at this scale (43 M rows, ~10× faster than in-place DELETE); staging keeps the canonical table serving consumers until the new build validates; per-year transactions give FR-012 resume for free (interrupted run: `__new` + checkpoints persist; completed years skip). Rebuilding from ORM DDL closes the ORM↔physical PK divergence as a side effect and makes FR-007 idempotency structural (PK) rather than procedural.
**SC-008 operationalization**: "byte-identical table" = equal SHA-256 over `SELECT * FROM <table> ORDER BY <full PK>` for both tables (documented in `contracts/determinism_contract.md`); the DB *file* is not byte-comparable (WAL/freelist noise), the table contents are.

### D10. CLI surface + mise task

**Decision**: `python -m babylon_data.qcew` (argparse, 067/068 house style): required mode `--dry-run | --apply | --rollback-from-backup | --drop-backup`; `--years 2010-2024` (default full range); `--source-dir` (default `/media/user/data/babylon-data/qcew`); `--db` (default resolves via babylon's reference database module); `--restart` (drop `__new` + v086 checkpoints). Registered as `mise run data:qcew` following the `data:bea-load` usage-crate pattern. `tools/ingest_qcew_full.py` tombstone message updated to the real command.
**Rationale**: `__main__.py` avoids resurrecting the 83.5 KB typer `cli.py` (whose import closure needs four missing modules); argparse matches 067/068. A `babylon_data/cli.py` shim can trivially delegate later (098) — the tombstone's promised interface is a follow-up alias, not a 086 requirement.

### D11. Tests live in babylon; imputation math is fixture-tested; live-DB checks are gated

**Decision**: Unit + integration tests in babylon's `tests/` (the venv, factories, and CI live there), importing `babylon_data.qcew.*` under `pytest.importorskip` so CI (dangling symlink) skips exactly like the existing data-dependent-precondition tests. Unit fixtures: hand-built mini singlefile CSVs + in-memory ORM DBs covering: exact single-suppressed-sibling recovery; multi-sibling estabs apportionment; equal-split fallback; negative remainder; suppressed 71; suppressed 70 fallback; largest-remainder exactness; SS999/US/MSA/state exclusion; 46113→46102 (incl. 2015 dedupe); resume-after-interrupt; re-run idempotency (logical hash); determinism (two runs, equal hash). Integration: tiny end-to-end build + audit-JSON contract validation; live-DB Wayne-2010 ±2 % check (SC-003) reusing the `test_post_067_consumer_queries` skip-gating.
**Rationale**: The pure imputation algorithm must be CI-covered — so it is implemented in modules importable without the DB or source files present... but with the symlink dangling in CI, *no* babylon_data module imports. Accepted for 086 (documented limitation, consistent with every existing babylon_data-precondition test); spec-098's babylon-data CI closes it. Local `mise run check` runs everything.

### D12. Downstream re-baselining is in scope as a delivery step

**Decision**: After the live reload, regenerate `tests/baselines/michigan-e2e.json` (the 067 FR-008 pattern) and re-run `qa:e2e-regression` + the structural rate-of-profit invariants (s > 0, p′ finite — band-free per 067 SC-002 amendment). Wayne-2010 spot-check asserts ≈ 657,150 ± 2 %.
**Rationale**: county `v` rises 10–30 %+ by design; the e2e baseline necessarily shifts. Shipping the reload without the baseline regen would leave `qa:e2e-regression` red and misattribute the shift to a regression.

---

## R3. Resolved spec edge cases → mechanism map

| Spec edge case | Mechanism (decision) |
|---|---|
| County total itself suppressed | D6 fallback chain (Σ disclosed 71 → Σ disclosed leaves) + low-confidence flag (audit) |
| Apportionment basis missing | D6 equal split, counted in audit |
| NAICS revisions across years | Tree built from each year's own published rows; dim_industry lookup by code (vintage-union already seeded, 1,382 level-6 codes); unknown code = hard error naming codes |
| County boundary/FIPS changes | D7 (46113→46102 incl. 2015 dedupe; CT-2024 as published + audit flag) |
| Non-county pseudo-areas | D7 exclusions, per-class counts in audit; SS999 no longer loaded |
| Integer reconciliation | D6 largest-remainder, exact sums by construction |

## Open items deliberately deferred

- babylon-data full packaging, remote, CI, and the other ~24 loaders → **spec-098**.
- Fixing throughput/melt rollup adapters (dead since 067) → future spec; D5's rollup table is their natural data source.
- dim_ownership placeholder titles, orphan SS999 dim_county rows → hygiene, 098.
- Schema ownership between the two repos → 098.
