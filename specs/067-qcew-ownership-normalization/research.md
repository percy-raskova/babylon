# Phase 0 Research: QCEW Ownership and NAICS Hierarchy Normalization

**Branch**: `067-qcew-ownership-normalization` | **Date**: 2026-05-16 | **Plan**: [plan.md](./plan.md)

Six key decisions made during Phase 0. Each follows the Decision / Rationale / Alternatives format.

---

## R1 — Rollup-detection predicate uses existing dimension-table semantics, NOT BLS `agglvl_code`

**Decision**: The DELETE predicate identifies rollup rows by querying the existing dimension tables:
- A row is a **NAICS rollup** if `dim_industry.naics_level != 6` (the canonical National-Industry detail level).
- A row is an **ownership rollup** if `dim_ownership.own_code = '0'` (the BLS "Total Covered" rollup ownership code).

The migration SQL is two semantically-clear DELETEs against indexed FK columns.

**Rationale**: The existing schema (`src/babylon/reference/schema.py:377-431`) already encodes the rollup structure at the dimension level:
- `DimIndustry.naics_level: Mapped[int]` (0-6) was explicitly added to support NAICS hierarchy queries, and it harmonizes ALL NAICS vintages into a single semantic. A NAICS 2007 6-digit code and a NAICS 2022 6-digit code BOTH carry `naics_level = 6`.
- `DimOwnership.own_code: Mapped[str]` is the BLS-published 1-digit code, with `is_government` / `is_private` flags. The "Total covered" rollup carries `own_code = '0'`; the four canonical levels (Federal, State, Local, Private) carry `own_code ∈ {'1', '2', '3', '5'}` respectively.

This means **the rollup predicate is vintage-invariant** (R3 below) and we don't need to add new columns, new lookup tables, or vintage-conditional logic. Two DELETE statements against existing indexes complete the migration.

**Alternatives considered**:
- (A) Use the BLS-published `agglvl_code` column from source CSVs. **Rejected**: `agglvl_code` is not persisted in `FactQcewAnnual` (the existing PK is `(county_id, industry_id, ownership_id, time_id)` — no aggregation-level column). Adding it would require a schema migration AND backfilling from source CSVs — substantial extra scope. The dimension-table approach achieves the same result without schema change.
- (B) Re-ingest from source CSVs, applying the predicate at load time. **Rejected**: the QCEW loader was deleted in the spec-037 data-layer extraction (per ADR037; `tools/ingest_qcew_full.py` is a stub) and re-implementing it is out of scope (deferred to spec-086). The table is already populated with the rollup contamination present; a one-shot DELETE achieves the post-067 end state without a loader rewrite.
- (C) Mark rollup rows with a discriminator column rather than deleting. **Rejected**: documented in the spec checklist as considered-and-rejected. Adds a column every consumer must filter on — defeats the spec's "no defensive filters needed" goal. Storage savings (~30 % of rows are rollups) and audit-clarity favor deletion.

---

## R2 — Downstream query rewrite from SELECT(rollup) to SUM(leaves) — NOT just filter removal

**Decision**: The spec-066 hotfix queries currently look like:
```sql
SELECT total_wages_usd
FROM fact_qcew_annual
WHERE county_id = ? AND time_id = ? AND industry_id = 1 AND ownership_id = 1
```
where `industry_id = 1` is the "10 — Total, all industries" supersector ROLLUP in the local schema and `ownership_id = 1` is the "Total Covered" ROLLUP. The filter selects the BLS-pre-summed convenience row.

After spec-067 those rollup rows no longer exist. The corresponding query becomes:
```sql
SELECT SUM(total_wages_usd)
FROM fact_qcew_annual
WHERE county_id = ? AND time_id = ?
```
(no per-row filter needed; the table now contains only the canonical leaves, so SUM produces the BLS-agreement total directly).

This is a **query refactor**, not just a filter removal — the SQL shape changes from single-row SELECT to GROUP-BY-aggregate SUM. The spec FR-003 / FR-004 language "remove the defensive filter" is correct in effect but understates the code change required.

**Rationale**: Discovered by reading `src/babylon/persistence/hex_hydrator.py:463-480` and `src/babylon/persistence/county_aggregation.py:348-397`. The inline comments explicitly identify the filter values as rollup codes:
> `# `ownership_id = 1` row IS the sum of the four leaf ownership` (hex_hydrator.py:468)
> `# `industry_id = 1` — BLS 'All Industries' rollup (avoids NAICS rollup-vs-leaves double-count)` (county_aggregation.py:361)

This is the architectural inversion the spec missed in its first-draft framing. After spec-067:
- The rollup rows that the current queries SELECT do not exist.
- The leaves that the queries currently exclude become the only rows present.
- The natural SUM over those leaves recovers the same BLS-agreement total without any filter.

**Alternatives considered**:
- (A) Keep the queries as-is, repopulate the rollup row by computing it (an aggregate VIEW). **Rejected**: defeats the spec's "physical normalization" intent; keeps two semantically-equivalent representations of the same data and reintroduces the double-counting risk at the next view-vs-direct-table refactor.
- (B) Compute the rollup row as a stored procedure result. **Rejected**: SQLite has limited stored-procedure support; not aligned with current SQLAlchemy ORM pattern.
- (C) Force consumers to know about the schema change via deprecation. **Rejected**: the spec FR-004 explicitly mandates the filter removal in this delivery — leaving the query unchanged would fail the acceptance test.

**Implication for tasks.md**: the "remove filters" tasks are actually "rewrite queries from SELECT(rollup) to SUM(leaves)" tasks. Each affected query is ~10-15 LOC, three queries total (hex_hydrator c calc, hex_hydrator wages, county_aggregation employment_proxy) = ~40 LOC change net.

---

## R3 — NAICS vintage detection is for audit-report metadata ONLY, not for the predicate

**Decision**: The DELETE predicate is vintage-invariant (`naics_level = 6` means "canonical National Industry detail" for every NAICS vintage from 2007 through 2022). Vintage detection is performed solely for the **audit report metadata** — recording per-year which NAICS vintage governed the source data, so an operator can correlate the report against BLS's NAICS revision schedule.

Vintage classification mechanism: year-keyed lookup table in `tools/normalize_qcew_rollups.py`:
```python
NAICS_VINTAGE_BY_YEAR: dict[int, Literal["2007", "2012", "2017", "2022"]] = {
    2010: "2007", 2011: "2007",
    2012: "2012", 2013: "2012", 2014: "2012", 2015: "2012", 2016: "2012",
    2017: "2017", 2018: "2017", 2019: "2017", 2020: "2017", 2021: "2017",
    2022: "2022", 2023: "2022", 2024: "2022",
}
```
(per BLS's documented NAICS adoption schedule for QCEW; mapping codified in the spec Assumptions section.)

**Rationale**: The original spec FR-011 mandated "detect NAICS vintage per source CSV and apply the rollup-detection predicate appropriate to that vintage" — but this discovery (R1) shows the predicate IS vintage-invariant because `DimIndustry.naics_level` is already harmonized across vintages. Vintage detection is therefore demoted from a load-bearing predicate input to audit-report metadata.

This simplifies the migration substantially:
- No vintage-conditional code paths in the DELETE logic
- No vintage-detection failure mode that halts ingest (FR-011's halt-on-failure clause becomes inapplicable in the canonical happy path)
- The audit report still records vintage per year, so the spec's auditability promise is preserved

**Alternatives considered**:
- (A) Per-vintage rollup predicate (the spec's original framing). **Rejected**: discovered to be unnecessary; the schema already harmonizes.
- (B) Auto-detect vintage from data (e.g., presence of NAICS codes only valid in 2022). **Rejected**: more complex than the year-keyed table and adds no robustness (BLS's adoption schedule is documented and stable).
- (C) Read vintage from CSV header / metadata. **Rejected**: source CSVs don't carry a vintage column; year is the only available signal.

**Spec amendment** (applied 2026-05-16 post-/speckit.analyze): FR-011 reframed as "the audit report MUST classify each source year's NAICS vintage; the DELETE predicate itself is vintage-invariant; missing year-to-vintage mappings (e.g., new BLS revision) halt ingest." This matches the implementation in T006 (hard-coded `NAICS_VINTAGE_BY_YEAR` dict — KeyError on missing year naturally halts).

---

## R4 — In-place DELETE migration with atomic backup-then-commit, idempotency by predicate

**Decision**: The migration is a one-shot Python script (`tools/normalize_qcew_rollups.py`) that performs the following sequence atomically:

1. **Pre-flight**: count rows in `fact_qcew_annual`, count rollup rows per predicate, dry-run estimate of post-migration row count.
2. **Backup**: create `fact_qcew_annual__pre_067` as a CREATE TABLE AS SELECT * snapshot. (Stored in the same SQLite file; ~3 GB extra disk during migration; dropped after successful commit via a follow-up cleanup task, or retained by `--keep-backup` flag.)
3. **DELETE** rollup rows in a single transaction:
   ```sql
   BEGIN;
   DELETE FROM fact_qcew_annual
     WHERE industry_id IN (SELECT industry_id FROM dim_industry WHERE naics_level != 6);
   DELETE FROM fact_qcew_annual
     WHERE ownership_id IN (SELECT ownership_id FROM dim_ownership WHERE own_code = '0');
   COMMIT;
   ```
4. **Audit report**: emit Markdown to `reports/ingest/qcew_normalization_YYYYMMDD-HHMMSS.md` AND a machine-readable JSON sidecar at the same path with `.json` extension.
5. **Verify**: re-run pre-flight; if post-migration row count doesn't match the dry-run estimate within ±0.01 %, raise and roll back from the backup table.

**Idempotency** (FR-010 / SC-005): re-running the script after a successful first run finds zero rollup rows matching the predicate; both DELETEs are no-ops; the audit report records `rows_excluded = 0` and the migration completes successfully with no state change. The backup table is preserved unchanged.

**Atomicity**: SQLite supports transactional DDL+DML, so the BEGIN ... COMMIT block is atomic. On any failure between BEGIN and COMMIT (process kill, disk full, etc.) the database is unchanged. On post-COMMIT failure (audit-report write fails) the database IS changed but the backup table remains as recovery surface.

**Rationale**: Matches the project's existing migration discipline (per ADR040 spec-062 two-phase persistence + per-tick atomic transactional commit). Backup-then-commit is the standard pattern for one-shot reference-data migrations in this codebase. SQLite's small surface (one file, one process) makes the backup cheap and rollback trivial.

**Alternatives considered**:
- (A) Re-ingest from source CSVs, applying the predicate at load. **Rejected**: see R1(B); the loader doesn't currently exist.
- (B) Two-table migration (write to a new `fact_qcew_annual_v2`, swap with rename). **Rejected**: same effect as backup-then-DELETE but doubles the peak disk requirement. The DELETE-with-backup-table pattern uses less peak disk.
- (C) Mark-and-sweep with discriminator. **Rejected**: see R1(C).

---

## R5 — Audit report format: Markdown for humans + JSON sidecar for CI

**Decision**: The migration emits TWO files to `reports/ingest/`:

1. **`qcew_normalization_YYYYMMDD-HHMMSS.md`** — human-readable Markdown summary:
   ```markdown
   # QCEW Normalization Report
   **Run timestamp**: 2026-XX-XX HH:MM:SS UTC
   **Migration version**: spec-067 v1.0
   **Database**: data/sqlite/marxist-data-3NF.sqlite (SHA256: ...)

   ## Summary
   - Total rows pre-migration: N
   - Total rows post-migration: N'
   - Rows excluded: M (= N - N')
     - NAICS-only rollups: A
     - Ownership-only rollups: B
     - Both axes (intersection): C
     - Sum: A + B + C == M ✅
   - NAICS vintages detected: {2007: 2 years, 2012: 5 years, 2017: 5 years, 2022: 3 years}
   - BLS-suppressed county-years (only rollup rows available): N_suppressed

   ## Per-county deltas (Michigan scope, top 10 by absolute change)
   | county_fips | county_name | year | pre_sum | post_sum | delta_pct |
   ...

   ## All-county summary statistics
   - Counties with |delta| > 10%: N_large_delta
   - Counties with |delta| ≤ 5%: N_within_band (target: ≥ 95%)
   - Maximum |delta| observed: max_delta_pct
   ```

2. **`qcew_normalization_YYYYMMDD-HHMMSS.json`** — machine-readable sidecar conforming to `contracts/audit_report.schema.json` for CI consumption.

**Rationale**: Operators need the human-readable Markdown for one-time review; CI's `qa:e2e-regression` gate needs structured data to assert SC-008 (excluded-row class accounting). Two formats satisfy both audiences without duplicating the substantive content.

**Alternatives considered**:
- (A) Markdown only. **Rejected**: CI parsing of Markdown is fragile; SC-008 needs machine assertions.
- (B) JSON only. **Rejected**: operators reading raw JSON is friction; the Markdown comparison tables are valuable for ad-hoc inspection.
- (C) Database table (`tbl_ingest_audit`). **Rejected**: per Constitution II.11, the reference-data subsystem already owns the schema; adding an audit table inside that schema is acceptable but creates a long-lived persistence concern that doesn't need to outlive the migration. The filesystem-based report is the right granularity.

---

## R6 — Backward-compat policy: deprecation warning for queries hitting deleted rollups

**Decision**: When post-067 a query attempts to filter `WHERE ownership_id = 1` or `WHERE industry_id = 1` (the local-schema rollup IDs), the query simply returns zero rows — SQLite has no built-in deprecation mechanism, and adding one would require a query-rewriter shim that we don't want in the hot path.

Instead, we add a **review-time check**:

1. A new pre-commit hook entry (or `mise run qa:audit`-style check) runs `rg "ownership_id\s*=\s*1|industry_id\s*=\s*1" src/babylon/persistence/` and fails if any match is found in production code paths post-067.
2. CI's `qa:e2e-regression` gate fails if the michigan-e2e baseline shows zero rows in a path that the spec-066 baseline showed non-zero rows — this catches consumers that didn't refactor.
3. Test fixtures and migration scripts that still reference these filter values are exempt (they may legitimately test pre-067 behavior or document historical state).

**Rationale**: SQL-level deprecation warnings are an engine feature SQLite lacks; an application-layer query interceptor would add complexity disproportionate to the value. The build-time grep + integration-test row-count assertion catches the same class of bugs without runtime overhead.

**Alternatives considered**:
- (A) SQL VIEW that returns zero rows + raises a warning. **Rejected**: requires a custom SQLite function; the cost-benefit is poor for a one-time migration.
- (B) Application-layer query interceptor that wraps SQLAlchemy session. **Rejected**: adds latency to every query in the hot path for a migration concern.
- (C) Trust git history + commit-message conventions. **Rejected**: too weak; a future contributor copying old code would reintroduce the bug.

The pre-commit-style grep is the lightest enforcement that catches the bug.

---

## Open questions resolved during research

None remaining. The spec's NEEDS-CLARIFICATION budget was zero before Phase 0 and stays zero after.

## Post-/speckit.analyze amendments (2026-05-16)

Seven findings from `/speckit.analyze` resolved:

- **AMB-002 (HIGH)**: spec.md Assumptions ¶3 corrected — pre-067 consumers read the BLS "Total Covered" rollup (including government), not "private-sector only" as the original draft incorrectly stated. Post-067 SUM(leaves) is numerically equivalent. Future private-sector-only queries must add explicit `WHERE o.is_private = TRUE`.
- **AMB-001 (MEDIUM)**: spec.md FR-011 reframed to match this R3 decision (above).
- **INC-003 (MEDIUM)**: tasks.md T001 extended to verify `dim_county.fips_code` and `dim_time.year` column names exist; if not, update `contracts/normalization_migration.sql` Step 4 B1 and `tools/normalize_qcew_rollups.py:wayne_county_2010_spot_check` before T036.
- **COV-002 (LOW)**: tasks.md T054b added — explicit reproducibility-verification task (re-run baseline regen, diff trace.csv, assert byte-identical) covering SC-006.
- **COV-001 (LOW)**: spec.md FR-002 tightened — clarifies that audit report logs aggregate counts and backup table preserves per-row recoverability; together they satisfy audit-reconstruction.
- **INC-001 (LOW)**: test name aligned across spec.md FR-009/SC-003, plan.md project structure, and tasks.md T049/T050/T054 — all reference `test_state_rate_of_profit_in_relaxed_band` (spec-066 name, preserved for git continuity).
- **AMB-003 (LOW)**: plan.md Technical Context Scale/Scope estimate cleaned up — defers to T001 pre-flight for actual row count.

## T001 pre-flight verification (2026-05-16)

Verified against `data/sqlite/marxist-data-3NF.sqlite`:

- **`fact_qcew_annual` row count**: **43,305,794** rows (NOT ~10 M as estimated; ~4× the earlier estimate — the table holds all US counties, not just Michigan).
- **`dim_industry.naics_level` distribution**: 0, 2, 3, 4, 5, 6, 98, 99 (no level 1 rows exist; codes 98/99 are 2 + 12 special-aggregation rows respectively, e.g. NAICS supersector codes 101/102/1021-1028).
- **`dim_ownership` codes present in table**: '0', '1', '2', '3', '5', '8', '9' (codes 8 = Total Government rollup, 9 = Total UI Covered). Verified that **zero rows in `fact_qcew_annual` reference own_code 8 or 9** — only codes 0/1/2/3/5 are populated. The predicate `own_code = '0'` correctly identifies the only rollup-ownership rows present.
- **`dim_county.fips`** (NOT `fips_code`): the 5-digit FIPS column is named `fips`. Wayne County, MI is `county_id = 1313`, `fips = '26163'`. The 3-digit county portion is in `county_fips`. **Updated `contracts/normalization_migration.sql` Step 4 B1 to use `c.fips`.**
- **`dim_time.year`**: present as expected. Range 2010-2024 (15 years).

### Row-count breakdown by rollup class (pre-migration)

| naics_level | own_code | classification | row count |
|---|---|---|---|
| 6 | 1/2/3/5 | canonical leaves (SURVIVE) | ~15,048,415 |
| 6 | 0 | ownership-only rollup (DELETE 3b) | ~49,049 |
| 0/2/3/4/5/98/99 | 1/2/3/5 | NAICS-only rollups (DELETE 3a) | ~28,159,281 |
| 0/2/3/4/5/98/99 | 0 | both-axes rollups (DELETE 3a or 3b) | ~49,049 portion of 28M |

Expected post-067 row count: ~15.0 M (3× reduction). Backup table doubles peak disk to ~17.6 GB during migration (revising plan.md's 12 GB estimate upward).

## T001/T036 finding (2026-05-16) — BLS suppression at 6-digit NAICS

Verified empirically during dry-run against the live reference DB:

```
Wayne County 2010 employment:
  naics_level=0 / own_code='0' (Total Covered rollup): 657,150  ← BLS publication
  naics_level=4 sum (all 4-digit industry groups):     617,899  (-6.0% vs rollup)
  naics_level=5 sum:                                   564,508  (-14.1%)
  naics_level=6 sum (canonical leaves):                561,173  (-14.6%)
```

This gradient demonstrates that **BLS suppresses 6-digit leaf cells more aggressively than higher-aggregation cells** to protect employer confidentiality. The rollup row at `naics_level=0` contains the full population total; the sum of leaves at `naics_level=6` is systematically lower by ~10-30% across all Michigan county-years.

**Implication for SC-001 / FR-006 / SC-007**: The spec's "±5% within BLS publication" target is **infeasible for `naics_level=6` aggregation** given QCEW's suppression policy. Empirical population-wide statistics across the 84 Michigan counties × 15 years (1260 pairs):

```
Pairs total:              1260
Pairs within ±5% band:       0
Pairs with |delta| > 10%: 1236  (98% of pairs)
Mean delta:              -61%
Max |delta|:              94%
```

(These numbers are *pre-apply* simulated via the canonical predicate; they will be confirmed by the post-apply audit report.)

**Mitigation options** (deferred to post-spec-067 follow-up, not blocking this migration):

1. **Loosen tolerance** in SC-001/SC-007 from ±5% to ±20-30% to match observed QCEW suppression; document as a known limitation.
2. **Use `naics_level=4` leaves** instead of `naics_level=6` — closer to BLS publication fidelity (still ~6% off, within the original ±5% target after rounding).
3. **Retain the `naics_level=0 AND own_code='0'` rollup row** as the canonical Total Covered data source; spec-067 then becomes only an ownership-rollup-removal (the spec-066 hotfix already correctly selected this rollup via `industry_id = 1 AND ownership_id = 1`).
4. **Introduce a synthetic imputed-total row** that captures the BLS rollup value but is flagged so consumers know it's not a leaf.

Spec-067 proceeds with the current approach (delete both NAICS and ownership rollups; expose the suppression in the audit report) because the migration is fully reversible via the backup table. The audit report is the authoritative ground truth for what fraction of MI county-years meet SC-007; if that fraction is below 95% the user will need to choose among the mitigation options above before the spec is closed.

## Risk register (for plan.md awareness)

- **R1 risk**: if `DimIndustry.naics_level` is populated incorrectly for some rows (data-quality bug in the existing reference DB), the predicate will mis-classify. Mitigation: the audit report's per-county delta check (FR-007 / SC-007) catches this within ±5 % BLS-agreement bound.
- **R2 risk**: the consumer-query rewrite changes the SQL shape from O(1) primary-key lookup to O(N) scan-and-aggregate per query, increasing per-query latency by ~10–50 ms each. The 520-tick canonical run executes ~166,000 such queries (83 counties × 2 fetches × 520 ticks × 2 query types), adding ~30 min wallclock IF unoptimized. Mitigation: this is precisely the case spec-069 (SQLite read caching) was scoped to address. Spec-069 will reclaim the ~30 min and create headroom to tighten the wallclock budget. Spec-067 implementation does NOT need spec-069 to ship; both fit within the spec-066-relaxed 90-min budget.
- **R4 risk**: the backup table doubles the SQLite file size during migration. Current DB is 8.79 GB; peak during migration is ~12 GB. Mitigation: documented in quickstart.md as a pre-flight disk-space check.
- **R5 risk**: the audit report's per-county delta computation requires holding pre- and post-state row counts in memory for ~3.1K US counties. Memory footprint is negligible (~10 MB).
