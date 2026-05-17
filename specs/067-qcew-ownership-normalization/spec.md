# Feature Specification: QCEW Ownership and NAICS Hierarchy Normalization

**Feature Branch**: `067-qcew-ownership-normalization` *(branch name retained for git stability; scope expanded per 2026-05-16 clarification)*
**Created**: 2026-05-16
**Status**: Draft
**Input**: User description: "067 — QCEW Ownership Filter Normalization. Normalize the SQLite ingestion of `fact_qcew_annual` so the canonical un-rolled rows are the only stored representation, removing the need for downstream `WHERE ownership_id = …` filters added as a hotfix in spec-066. Restore the original ±50 % wage band (SC-005 / SC-002 of spec-066, currently relaxed to ±80 %)." *(Clarification 2026-05-16: scope expanded to ALSO normalize NAICS-hierarchy rollups, removing the parallel `WHERE industry_id = 1` defensive filter spec-066 added alongside the ownership filter. Both rollup classes share the same architectural shape and ship together.)*

## Clarifications

### Session 2026-05-16 (clarify pass)

- Q: NAICS-hierarchy rollup scope — should spec-067 cover only ownership rollups (per original draft), or also NAICS rollups (the parallel defensive filter spec-066 added)? → A: **Option A — Expand spec-067 to include NAICS normalization.** Single spec, single delivery, single baseline regeneration. Both rollup classes (ownership AND NAICS-hierarchy) get the canonical-row treatment so FR-003 / SC-004 ("no defensive filters needed") becomes architecturally complete rather than partial. The spec-066 `WHERE industry_id = 1` filter, like its ownership sibling, becomes redundant and is removed from production query strings as part of this delivery.

### Session 2026-05-16 (analyze pass)

Cross-artifact analysis surfaced 7 findings. All resolved by editing the spec/plan/tasks/research without changing semantic scope:

- **AMB-002 (HIGH)**: Corrected factual error in Assumptions ¶3 — pre-067 consumer queries read the BLS "Total Covered" rollup (which INCLUDES government employment), not "private-sector only" as the original draft incorrectly claimed. Post-067 SUM(leaves) over Federal+State+Local+Private is numerically equivalent. Private-sector-only queries must now add an explicit `WHERE o.is_private = TRUE`.
- **AMB-001 (MEDIUM)**: FR-011 reframed — NAICS vintage detection is for audit-report metadata, NOT a load-bearing input to the DELETE predicate. The predicate `naics_level = 6` is vintage-invariant because `DimIndustry.naics_level` harmonizes across NAICS 2007/2012/2017/2022. Missing year-to-vintage mapping (new BLS revision) halts ingest with KeyError.
- **COV-001 (LOW)**: FR-002 tightened — clarifies aggregate-counts-in-report + per-row-preservation-in-backup-table together satisfy "audit can reconstruct what was dropped."
- **INC-001 (LOW)**: FR-009 + SC-003 pinned to the spec-066 test name `test_state_rate_of_profit_in_relaxed_band` for git-history continuity; no rename.
- **INC-003 (MEDIUM)**: tasks.md T001 extended to verify `dim_county.fips_code` + `dim_time.year` column names exist (the SQL contract assumes them).
- **COV-002 (LOW)**: tasks.md T054b added — explicit reproducibility-verification task for SC-006 (byte-identical baseline regeneration at same seed).
- **AMB-003 (LOW)**: plan.md Technical Context Scale/Scope estimate cleaned up — defers to T001 pre-flight for actual row count.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Single-row truth in the reference DB (Priority: P1)

The Babylon simulation engine reads variable capital `v` and employment_proxy from `fact_qcew_annual` via the hex hydrator and county aggregation helpers. Today every consumer must remember to append BOTH `WHERE ownership_id = …` AND `WHERE industry_id = …` to its query, because the table contains the canonical per-ownership and per-NAICS-industry rows AND the BLS-published rollup rows (the "All-ownership Total" rollup AND the NAICS-hierarchy aggregation rows: sector / subsector / industry-group / industry / national-industry, plus the "10 — Total, all industries" supersector). Anyone who forgets either filter multiplies every wage dollar and every job. Spec-067 removes both traps at the source: the table physically holds one canonical row per `(area_fips, industry_code, year, establishment_size_class, ownership_id)` where `industry_code` is at the canonical-decomposition level (6-digit NAICS National Industry per BLS QCEW convention) and `ownership_id` is at the canonical per-ownership level (Federal / State / Local / Private separately), with both ownership-rollup AND NAICS-rollup rows excluded at ingest time.

**Why this priority**: Without this, every new consumer of QCEW data in the codebase is one missed `WHERE` clause away from a 2×, 3×, or higher-multiplier employment-and-wage error. Spec-066's e2e audit caught the same bug three times in three different code paths (hex hydrator wages, hex hydrator c calculation, county aggregation employment proxy) and required TWO parallel defensive filters at every call site. The architectural fix prevents recurrence on both axes.

**Independent Test**: Re-run `tools/ingest_qcew_full.py` against the existing raw QCEW CSVs at `/media/user/data/babylon-data/qcew/`. Inspect `fact_qcew_annual` row counts before and after. Verify a `SELECT SUM(employment) FROM fact_qcew_annual WHERE area_fips = '26163' AND year = 2010` (Wayne County) — with no ownership filter AND no industry filter — returns the BLS-published ~660 K, not the higher multiplier-inflated figure.

**Acceptance Scenarios**:

1. **Given** the post-ingest `fact_qcew_annual` table, **When** a query sums `employment` for Wayne County (FIPS 26163) for year 2010 without any `WHERE ownership_id` filter AND without any `WHERE industry_id` filter, **Then** the result equals the BLS publication for Wayne County 2010 within ±5 %.
2. **Given** an existing query in `hex_hydrator.py` or `county_aggregation.py` that explicitly filters BOTH `ownership_id = 1` AND `industry_id = 1`, **When** both filters are removed, **Then** the query result is byte-identical to the pre-removal result (both filters became redundant — the rows they were excluding no longer exist).
3. **Given** any BLS-published rollup row encountered during ingestion (the "All-ownership Total" ownership rollup OR any NAICS-hierarchy aggregation row above the National-Industry level), **When** that row is encountered, **Then** ingestion logs a normalization decision and excludes it from the persisted table so it does not contaminate `SUM()` queries.

---

### User Story 2 — Tightened rate-of-profit acceptance band (Priority: P1)

Spec-066 had to relax the rate-of-profit acceptance band from `[0.05, 0.50]` to `[0.05, 0.80]` (`tests/test_state_rate_of_profit_in_relaxed_band`) because the per-query ownership hotfix changed the variable-capital denominator at one site but not another, producing an internally-inconsistent `s/v` ratio that drifted outside the original band. Once `fact_qcew_annual` is normalized at the source, every consumer reads the same `v` definition, and the rate of profit returns to its theoretically-justified narrow band.

**Why this priority**: The rate of profit `s/v` is the load-bearing economic invariant of the simulation. A band of `[0.05, 0.80]` is wide enough to hide real regressions. Restoring `[0.05, 0.50]` (the Shaikh-tractable band documented in spec-066 FR-021) restores meaningful regression coverage on every downstream change.

**Independent Test**: After spec-067 ingestion lands and downstream code has its per-query `WHERE ownership_id` filters removed, change the band in `tests/test_state_rate_of_profit_in_relaxed_band` (or its successor) back to `[0.05, 0.50]` and re-run the 520-tick Michigan-Canada slow gate. The test passes.

**Acceptance Scenarios**:

1. **Given** the spec-067-normalized `fact_qcew_annual` table and downstream code with per-query ownership filters removed, **When** the canonical 520-tick Michigan-Canada simulation runs, **Then** the per-county `s/v` rate of profit falls within `[0.05, 0.50]` for every county-tick row.
2. **Given** the test `test_state_rate_of_profit_in_relaxed_band`, **When** its band parameter is tightened from `[0.05, 0.80]` back to `[0.05, 0.50]`, **Then** the test passes against the post-067 baseline.

---

### User Story 3 — Removal of per-query rollup filters from consumer code (Priority: P2)

Spec-066 added defensive `WHERE ownership_id = …` AND `WHERE industry_id = …` filters to two production query paths (`hex_hydrator._fetch_per_county_*` and `babylon.persistence.county_aggregation.fetch_employment_proxy_for_county_at_tick`) plus one cascade fix in the hex hydrator wages query. After spec-067 both filter families become *correct but redundant*. Removing them simplifies the call sites, prevents future authors from copying the redundant filters into new code, and aligns the schema with the spec-066 quickstart promise that downstream consumers should not need to know about rollup codes.

**Why this priority**: Code hygiene, not correctness. The system works the same way with or without the filters once spec-067 lands. But leaving them in the codebase teaches future contributors a defensive pattern that is no longer needed and obscures the architectural fix.

**Independent Test**: Diff `hex_hydrator.py` and `county_aggregation.py` before and after spec-067 cleanup. Confirm both the `WHERE ownership_id = N` AND the `WHERE industry_id = N` clauses are gone. Re-run all unit + integration + slow-gate tests; they pass unchanged.

**Acceptance Scenarios**:

1. **Given** the codebase post-067, **When** `rg "WHERE ownership_id = " src/babylon/` AND `rg "WHERE industry_id = " src/babylon/` are run, **Then** zero hits remain in production code paths (test fixtures and migration scripts may still reference the columns).
2. **Given** any production query in `hex_hydrator.py` or `county_aggregation.py`, **When** that query runs against the spec-067-normalized table, **Then** the result is identical to the spec-066 result that did include both filters.

---

### User Story 4 — Audit trail for the normalization decision (Priority: P3)

Re-running ingestion materially changes the contents of `fact_qcew_annual`. Operators and CI need a clear record of how many rows were dropped, why, and how the totals shifted, so the change is auditable and reversible without re-deriving the rationale from git history.

**Why this priority**: The ingestion change is itself a one-shot event, but the audit trail prevents future confusion ("why does our QCEW table have N rows instead of N+M?"). Goes in the data-pipeline report (`reports/data_freshness.md` per the proposed spec-086 plan, or a standalone report file in `reports/ingest/`).

**Independent Test**: Run the ingestion against a known fixture county-year set with deliberately-included rollup rows. Verify the post-ingest log/report records: (a) total rollup rows seen, (b) total rollup rows excluded, (c) per-county delta in summed employment and wages before vs after normalization, (d) the BLS-publication comparison delta per county-year.

**Acceptance Scenarios**:

1. **Given** an ingestion run, **When** the run completes, **Then** a normalization report is written to a known location (e.g., `reports/ingest/qcew_normalization_YYYYMMDD.md`) listing the per-county pre/post totals.
2. **Given** the normalization report, **When** an operator inspects it, **Then** they can determine whether any county-year pair shifted by more than ±10 % from its pre-067 value (indicating either a rollup row was correctly removed OR an under-the-radar coding anomaly was surfaced).

---

### Edge Cases

- **Counties with only one ownership level reported**: some small counties have only the canonical row, no rollup. Ingestion MUST handle these without false positives (don't drop the only row).
- **Year-over-year ownership code changes**: BLS occasionally re-codes ownership classifications. Ingestion MUST be stable across the 2010-2024 year range in scope. If a year uses a different code set, the ingestion logs a warning and preserves the canonical rows by the year's own convention.
- **NAICS hierarchy revisions**: NAICS gets revised every 5 years (NAICS 2007 → 2012 → 2017 → 2022) and BLS-published industry codes shift accordingly. Ingestion MUST detect the NAICS vintage per source CSV and preserve the canonical-level (National-Industry / 6-digit) rows in whichever vintage the year was published. Cross-year industry-code matching becomes a downstream concern, not an ingest concern.
- **Counties with only sector-level (2-digit) NAICS rows reported**: BLS suppresses lower-level industry rows for confidentiality when establishment counts are small. If a county-year has ONLY rolled-up rows and NO canonical National-Industry rows, that county-year is "BLS-suppressed" and ingestion MUST preserve the highest-resolution rows available (lowest-aggregation rollup) while still flagging the county-year so downstream consumers know the granularity is degraded. The audit report MUST list these counties.
- **Public-sector queries (future)**: spec-066 only used private-sector totals. If a future spec needs Federal / State / Local government employment as a distinct slice, the canonical table after 067 still preserves those rows separately — only the summary "All-ownership Total" rollup is excluded.
- **Test fixtures with hand-written rollup rows**: existing tests that synthesized rollup rows for the *old* hotfixes to defend against (e.g., to assert the hotfix filters worked) must be updated or removed; they are now testing a non-existent state.
- **The spec-066 baseline `tests/baselines/michigan-e2e.json`**: a normalized `fact_qcew_annual` will produce different trace values. The baseline MUST be regenerated as part of spec-067 delivery; CI's `qa:e2e-regression` gate will compare against the post-067 baseline.
- **Backward-compat for queries that DO filter `ownership_id` or `industry_id`**: filters using `ownership_id = 1` or `industry_id = 1` (the spec-066 hotfix values for canonical-private / canonical-National-Industry) against the normalized table should continue to work and return the same rows. Filters targeting *rollup* values (`ownership_id = 0` Total, or any `industry_id` corresponding to a 2/3/4/5-digit aggregation or the "10 — Total, all industries" supersector) should now return zero rows, and a deprecation warning should fire in code paths that try.
- **Concurrent ingest of multi-resolution data**: per the proposed spec-086 plan, ingestion runs are wrapped in atomic backup-truncate-load. Spec-067 inherits this discipline; the normalization step happens *during* the load phase, after backup and before commit.
- **What if BLS revises a historical year's data**: BLS routinely revises older QCEW data. Ingestion is a re-runnable, idempotent operation — each run produces the same normalized table from the same input CSVs. Re-ingest after BLS revision is expected and supported.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The QCEW ingestion process MUST produce exactly one canonical row per `(area_fips, industry_code, year, establishment_size_class, ownership_id)` for private-sector employment in `fact_qcew_annual`, where `industry_code` is at the National-Industry (6-digit) granularity per the source year's NAICS vintage and `ownership_id` is at the canonical per-ownership level (Federal / State / Local / Private separately). The "All-ownership Total" ownership rollup AND all NAICS-hierarchy rollup rows (sector / subsector / industry-group / industry / and the "10 — Total, all industries" supersector) published by BLS MUST be excluded from the persisted table.
- **FR-002**: The ingestion process MUST log aggregate excluded-row counts broken down by rollup class (NAICS-only / ownership-only / both-axes) in the audit report, AND retain a recoverable backup of the pre-migration `fact_qcew_annual` table (`fact_qcew_annual__pre_067`) so that any individual excluded row is reconstructible without re-reading the source CSV. The audit report's aggregate counts plus the backup table together satisfy the audit-reconstruction requirement.
- **FR-003**: Downstream production code in `src/babylon/persistence/hex_hydrator.py` and `src/babylon/persistence/county_aggregation.py` MUST NOT require explicit `WHERE ownership_id = …` OR `WHERE industry_id = …` filters to return correct employment and wage totals after this spec lands.
- **FR-004**: Both the `WHERE ownership_id = 1` AND `WHERE industry_id = 1` defensive filters added in spec-066 to those two files MUST be removed from production query strings as part of this spec's delivery.
- **FR-005**: The post-ingest table MUST preserve the per-ownership distinction (Federal / State / Local / Private) as separate rows so future specs can query them individually; only the "All-ownership Total" rollup is dropped. Similarly, the post-ingest table MUST preserve the per-National-Industry (6-digit NAICS) granularity so future specs can query individual industries; only the higher-aggregation rollup rows are dropped.
- **FR-006**: Per-county employment and wage values summed from `fact_qcew_annual` MUST agree with BLS publication for the same `(area_fips, year)` within ±5 % for every county-year in the 2010-2024 range covered by the canonical Michigan-Canada test scope.
- **FR-007**: The ingestion process MUST emit a normalization audit report to a known location (e.g., `reports/ingest/qcew_normalization_YYYYMMDD.md`) summarizing rows seen, rows excluded (broken down by rollup class: ownership / NAICS / both), and per-county delta from any prior table state. The report MUST also list all BLS-suppressed county-years where only rolled-up rows are available (per Edge Cases).
- **FR-008**: The spec-066 canonical baseline at `tests/baselines/michigan-e2e.json` MUST be regenerated against the post-067 normalized table before spec-067 ships, and the regenerated baseline MUST be committed in the spec-067 delivery so the `qa:e2e-regression` gate continues to pass.
- **FR-009**: The rate-of-profit acceptance band in `test_state_rate_of_profit_in_relaxed_band` (the spec-066 test, located in whichever `tests/` subdirectory it currently lives) MUST be tightened from the spec-066 relaxed `[0.05, 0.80]` back to the spec-original `[0.05, 0.50]`. The test name and file location are preserved for git-history continuity; only the band parameter and docstring change. The test MUST pass against the post-067 baseline.
- **FR-010**: The ingestion process MUST be idempotent — running it twice in succession against the same source CSVs produces a byte-identical `fact_qcew_annual` table.
- **FR-011**: The ingestion process MUST classify each source year's NAICS vintage (2007 / 2012 / 2017 / 2022) and record the classification in the audit-report metadata. The DELETE predicate itself is vintage-invariant (the dimension table's `naics_level = 6` semantic harmonizes across all NAICS revisions), so vintage information is required for audit traceability and operator review against BLS's NAICS revision schedule, NOT for branching the predicate. A missing year-to-vintage mapping (e.g., when a new BLS NAICS revision is adopted) MUST halt ingest with a clear error rather than silently classifying as unknown.

### Key Entities

- **`fact_qcew_annual` table**: SQLite reference-data table holding QCEW employment and wage rows per `(area_fips, industry_code, year, establishment_size_class, ownership_id)`. Source of variable capital `v` and employment_proxy for every downstream consumer. After spec-067, contains canonical un-rolled rows only — National-Industry (6-digit NAICS) granularity on the industry axis AND per-ownership-level granularity on the ownership axis, with no rollup rows on either axis.
- **QCEW Ownership Dimension**: Discrete BLS-published ownership categories (Federal / State / Local / Private + the Total rollup). Spec-067 keeps the four canonical categories as separate rows and drops the Total rollup.
- **QCEW NAICS Hierarchy Dimension**: The NAICS hierarchy as published by BLS — sector (2-digit) → subsector (3-digit) → industry-group (4-digit) → industry (5-digit) → National-Industry (6-digit), plus the "10 — Total, all industries" supersector and various intermediate supersector codes. Spec-067 keeps only the National-Industry (6-digit) rows and drops all aggregation rollup rows.
- **NAICS Vintage**: The NAICS revision year (2007 / 2012 / 2017 / 2022) governing the industry codes for a given source-data year. Spec-067 detects vintage per source CSV and applies the correct rollup predicate per vintage.
- **QCEW Ingestion Script**: The tool (currently `tools/ingest_qcew_full.py`) that reads raw CSVs from `/media/user/data/babylon-data/qcew/` and writes `fact_qcew_annual`. Spec-067 adds the normalization step (both axes) to this script.
- **Normalization Audit Report**: A Markdown report emitted per ingest run summarizing per-county pre/post deltas, excluded-row counts broken down by rollup class (ownership / NAICS / both), NAICS vintage detected per year, and the list of BLS-suppressed county-years where only rolled-up rows are available.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After spec-067 ingestion, `SELECT SUM(employment) FROM fact_qcew_annual WHERE area_fips = '26163' AND year = 2010` (Wayne County) — with no ownership filter AND no industry filter applied — returns a value within ±5 % of the BLS publication for Wayne County 2010 (~660 K).
- **SC-002**: After spec-067 ingestion AND both the `WHERE ownership_id = 1` and `WHERE industry_id = 1` filters are removed from `hex_hydrator.py` and `county_aggregation.py`, the canonical 520-tick Michigan-Canada simulation produces a trace whose per-county `s/v` rate of profit falls within `[0.05, 0.50]` for every county-tick row.
- **SC-003**: The test `test_state_rate_of_profit_in_relaxed_band` (the spec-066-named test, with its band tightened back to `[0.05, 0.50]`) passes against the post-067 baseline.
- **SC-004**: `rg "WHERE ownership_id = " src/babylon/persistence/hex_hydrator.py src/babylon/persistence/county_aggregation.py` AND `rg "WHERE industry_id = " src/babylon/persistence/hex_hydrator.py src/babylon/persistence/county_aggregation.py` both return zero matches.
- **SC-005**: Running the QCEW ingestion script twice in succession produces a byte-identical `fact_qcew_annual` table on both runs (idempotency).
- **SC-006**: The post-067 michigan-e2e baseline regeneration is reproducible — running the canonical Michigan-Canada simulation twice with the same seed produces byte-identical trace.csv content.
- **SC-007**: Per-county employment totals summed from `fact_qcew_annual` agree with BLS publication within ±5 % for ≥ 95 % of (county × year) pairs in the 2010-2024 Michigan scope.
- **SC-008**: The normalization audit report correctly classifies every excluded row by rollup class (ownership-only / NAICS-only / both), and the per-class excluded-row counts sum to the total excluded-row count (no row miscounted, no row counted twice).

## Assumptions

- The raw QCEW CSV source data already on disk at `/media/user/data/babylon-data/qcew/` (loaded prior to this spec) contains BOTH the canonical per-ownership and per-National-Industry rows AND the BLS-published rollup rows on both axes (the "All-ownership Total" ownership rollup AND the NAICS-hierarchy aggregation rows at each level above National-Industry, plus the "10 — Total, all industries" supersector), per BLS's standard publication format. Spec-067 does not re-download from BLS — it re-ingests from the existing local CSVs.
- BLS publication values for `(county × year)` employment and wages are the ground truth for verification. No additional cross-source verification is required.
- All current production consumers of `fact_qcew_annual` (`hex_hydrator.py`, `county_aggregation.py`) read the BLS "Total Covered" rollup row (local `ownership_id = 1` corresponding to BLS `own_code = '0'`) combined with the "All Industries" NAICS rollup (local `industry_id = 1` corresponding to BLS supersector "10"). This rollup row is the sum across all four canonical ownership levels (Federal + State + Local + Private) and across all NAICS detail levels — NOT private-sector only. Post-067 SUM(leaves) over the canonical-only rows is numerically equivalent to the pre-067 rollup-row selection without requiring rollup-row storage. Future consumers that need private-sector-only totals MUST add an explicit `WHERE o.is_private = TRUE` join filter per `contracts/post_067_query_contract.md` "Variant: private-sector-only totals."
- Industry-NAICS-hierarchy rollups are now in scope for spec-067 (clarified 2026-05-16 — the previously-out-of-scope NAICS work is integrated into this spec rather than deferred to a sibling).
- Establishment-size-class rollups are present in the source data but follow a different aggregation rule and are out of scope for spec-067.
- The canonical Michigan-Canada baseline (`tests/baselines/michigan-e2e.json`) will be regenerated as part of spec-067 delivery; this is expected and budgeted, not a regression.
- The spec-069 SQLite read-cache optimization is independent of spec-067 and can land before, after, or in parallel; the two specs do not share any code paths.
- Spec-068 (BEA national industry I-O ingestion) is independent of spec-067; the c (constant capital) calculation will continue to use the 0.5 hardcoded intermediate-inputs-fraction until spec-068 lands.
- NAICS vintages relevant to the 2010-2024 scope are NAICS 2007 (used 2010-2011), NAICS 2012 (used 2012-2016), NAICS 2017 (used 2017-2021), and NAICS 2022 (used 2022-2024). Cross-vintage industry-code mapping for time-series analysis is OUT of scope for spec-067 and remains a downstream concern.

## Dependencies

- Spec-037 (Postgres Runtime DB) — already shipped; provides the persistence boundary.
- Spec-062 (Cross-Scale Integration) — already shipped; defines two-phase persistence and the immutable-reference-lookup pattern that the normalized table feeds into.
- Spec-066 (Marx Coherence Fixes) — already shipped; introduced the per-query ownership filters that spec-067 makes redundant, and the relaxed `[0.05, 0.80]` band that spec-067 tightens.
- Existing ingestion tooling at `tools/ingest_qcew_full.py` (or equivalent) — modified, not replaced.
- ADR042 lines 130-131 (deferral note) and ADR044 line 100 (follow-up reference) — provide the architectural commitment to this work.
