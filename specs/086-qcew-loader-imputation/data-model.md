# Data Model: QCEW Loader with Suppression Imputation

**Spec**: spec-086 | **Date**: 2026-07-02 | **Source decisions**: research.md D4–D9

## 1. Modified entity: `FactQcewAnnual` (`src/babylon/reference/schema.py:1270`)

Grain unchanged: one row per **county × 6-digit NAICS × ownership × year** (agglvl-78 leaves only; spec-067 no-rollup invariant preserved).

| Column | Type | Change | Semantics |
|---|---|---|---|
| county_id, industry_id, ownership_id, time_id | INT FK, composite PK | **PK now physically enforced** (rebuild from ORM DDL — the live table lost it) | Identity |
| establishments | INT | unchanged | Always observed (BLS publishes under suppression) |
| employment | INT | unchanged type; **new semantics** | Disclosed: verbatim (incl. true 0). Suppressed: **imputed positive-or-zero value** (never a masking 0) |
| total_wages_usd | NUMERIC(15,2) | unchanged type; **new semantics** | Same rule as employment |
| avg_weekly_wage_usd, avg_annual_pay_usd | INT | unchanged type | Disclosed: verbatim. Imputed rows: **NULL** (never fabricated) |
| lq_employment, lq_annual_pay | NUMERIC(10,4) | unchanged type | Imputed rows: **NULL** |
| disclosure_code | VARCHAR(5) | unchanged | Raw BLS flag: `'N'` = BLS withheld; NULL = disclosed. Preserved verbatim |
| **is_imputed** | **BOOLEAN NOT NULL, server default 0** | **NEW** | 1 ⇔ employment/total_wages_usd were reconstructed by the imputation pass (FR-005). Note `is_imputed=1 ⇒ disclosure_code='N'`, but not conversely only in the degenerate case where a suppressed cell is exactly recovered — exact recovery is still reconstruction ⇒ flagged 1 |

**Validation rules**: employment ≥ 0; total_wages_usd ≥ 0; `is_imputed=1` ⇒ avg/lq columns NULL; every (county_id, time_id) group non-empty for covered county-years; per-year insert order = (county_id, ownership_id, industry_id) for deterministic rowids.

**Invariant (FR-002/FR-003, per county-year)**: `Σ employment over leaves` = county Total-Covered constraint (exactly, by construction of D6) whenever the agglvl-70 row was published; within documented fallback semantics otherwise. Same for wages. SC bands (±2 %) absorb source-data self-inconsistency (BLS rounding), not algorithmic slack.

## 2. New entity: `FactQcewCountyRollup` (`fact_qcew_county_rollup`)

BLS-published reconciliation constraints made durable (spec Key Entity "Published Aggregate (Constraint)"; research D5).

| Column | Type | Semantics |
|---|---|---|
| county_id | INT FK dim_county, PK part | County |
| time_id | INT FK dim_time, PK part | Year (annual rows) |
| ownership_id | INT FK dim_ownership, PK part | own_code '0' row = county Total Covered (agglvl 70); own 1/2/3/5 = per-ownership totals (agglvl 71) |
| establishments | INT | As published |
| employment | INT | As published; if the rollup itself was suppressed: the D6 fallback value, `is_imputed=1` |
| total_wages_usd | NUMERIC(15,2) | Same rule |
| disclosure_code | VARCHAR(5) | Raw BLS flag on the rollup row |
| is_imputed | BOOLEAN NOT NULL default 0 | 1 ⇔ this constraint was reconstructed via fallback (low-confidence county-year) |

Scale: ~3,270 counties × ≤5 ownership rows × 15 years ≈ 245 K rows. Index: PK only (covers the county-year lookup).

**Role**: SC-001/002/004 validation queries; `qa:data`-style gates re-checkable forever without the 8.3 GB source; future correct data source for the (already dead since 067) throughput/melt total-lookups.

## 3. Checkpoint usage: `ingest_checkpoint` (existing table, corrected semantics)

New loader writes: `source_code='qcew'`, `year=<real year>`, `state_fips='US'` (2 chars, no more hash abuse), `table_id='annual_v086'`, `race_code='T'`, `row_count=<leaf rows inserted>`. UNIQUE constraint gives per-year upsert. Resume = skip years whose checkpoint exists AND whose rows are present in the staging table; `--restart` deletes v086 checkpoints + staging. Swap-time cleanup deletes the old loader's malformed rows (`source_code='qcew' AND table_id='file'`).

## 4. In-memory entities (loader-internal, not persisted)

- **CountyYearTree** (`hierarchy.py`): per (county_id, year): county node (70) → ownership nodes (71) → NAICS prefix tree from published 74→75→76→77→78 rows of that ownership. Node: `{code, level, estabs, employment|None, wages|None, disclosed: bool, children[]}`. Built solely from the year's singlefile rows after classification.
- **ImputationResult** (`imputation.py`): per node: assigned employment/wages (int), method ∈ {`observed`, `exact_recovery`, `estabs_apportioned`, `equal_split`, `zero_negative_remainder`}, anomalies. Pure function of the tree — no I/O, unit-testable.
- **RowClassification** (`singlefile.py`): per CSV row → {LEAF, CONSTRAINT_70, CONSTRAINT_71, CONSTRAINT_NAICS, EXCLUDED(class ∈ us|msa|statewide|ss999|unknown_fips|non_county_vi), IDENTITY_MAPPED(46113→46102), DROPPED_DUPLICATE(2015 Shannon)}.

## 5. Audit report (persisted artifact, `reports/ingest/qcew_impute_<UTC>.{json,md}`)

Pydantic models in `audit.py`, JSON validated against `contracts/audit_report.schema.json` before writing (067 pattern). Top-level: `schema_version`, `run_metadata` (mode, years, db sha256 pre/post, **git branch+sha of BOTH repos**, duration, source-file sha256 per year), `per_year[]` (rows_scanned, leaf_rows, constraint_rows, excluded per class, suppression {cells, rate, exact_recovery, estabs_apportioned, equal_split, negative_remainder}, reconciliation {counties, within_2pct_employment/wages counts+pct, residual p50/p90/p99/max, outliers[], low_confidence_county_years[]}, national_check {sum_counties, excluded_pseudo_mass, bls_us000, delta_pct, pass}), `identity_resolutions`, `sc_gates` (booleans SC-001…SC-009 where computable at load time).

## 6. State transitions (load lifecycle)

```
EMPTY/STALE ──apply──► STAGING (fact_qcew_annual__new + rollup__new; per-year txns; checkpoints)
STAGING ──all years + validation pass──► SWAPPED (canonical ← __new; old ← __pre_086 backup; indexes recreated;
                                                  _cache_national_wages_bea dropped; old file-checkpoints purged)
SWAPPED ──rollback-from-backup──► PRE-086 state (backup → canonical)
SWAPPED ──drop-backup──► FINAL (backup removed)
interrupted STAGING ──re-run apply──► resumes at first un-checkpointed year (FR-012)
```

## 7. Consumer compatibility matrix (FR-010 — verified in research R1)

| Consumer | Query shape | Post-086 behavior |
|---|---|---|
| hex_hydrator (v), county_aggregation (employment), reference_data_cache, postgres preflight | SUM at county-year grain, no column filters | Correct totals automatically; no change |
| share_lookup_service, leontief allocator, hydration/reference | per-industry, skip NULL | Imputed rows carry values → included (intended) |
| sqlite_hydrator `_copy_qcew`, economics/adapters | filter `IS NOT NULL` / `> 0` | Imputed rows non-NULL → included |
| economics/adapters `_cache_national_wages_bea` | persisted cache | **Dropped at swap**; lazily rebuilt correct |
| throughput/melt rollup adapters | own '0' / naics '10' rows | Already dead since 067; unchanged (out of scope; rollup table is their future fix) |
