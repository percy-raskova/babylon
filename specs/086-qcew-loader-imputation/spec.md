# Feature Specification: QCEW Loader Reimplementation with Synthetic Suppression Imputation

**Feature Branch**: `086-qcew-loader-imputation`
**Created**: 2026-05-27
**Status**: Draft (amended 2026-07-02 — owner decisions on loader home and write target; see Assumptions)
**Input**: User description: "Reimplement the QCEW loader deleted in spec-037 and reconstruct BLS-suppressed county employment/wage cells so the reference database's county totals match the figures BLS actually publishes. Supersedes spec-067's lossy normalization and resolves the spec-097 suppression placeholder."

## Overview

The simulation derives each county's variable capital (wages paid to labor) and employment from the `fact_qcew_annual` table of the reference database. After spec-067 reduced that table to 6-digit-industry detail rows, those county totals became systematically understated, because the U.S. Bureau of Labor Statistics (BLS) **suppresses** roughly half of all 6-digit county cells to protect employer confidentiality. Summing only the surviving (disclosed) detail therefore undercounts true county employment and wages by 10–30%+ (one observed county-year was low by ~61%). The loader that originally built this table was also deleted, so the database can no longer be rebuilt from source.

This feature restores a QCEW loader that builds the table from the staged BLS source files **and reconstructs the suppressed cells** so that each county's totals reconcile to the figures BLS publishes — while clearly marking which values were observed versus reconstructed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Simulation consumes accurate county labor totals (Priority: P1)

As the simulation engine, when I hydrate a county for a given year, the employment and wage totals I read from the reference database match the totals BLS actually published for that county — not an undercount caused by withheld detail cells. This makes derived variable capital, employment, and population-fallback figures trustworthy for every county in the country.

**Why this priority**: This is the entire reason for the feature. Biased labor inputs silently corrupt the model's core economic quantities for the majority of counties. Without this, every downstream calculation that depends on QCEW (rate of exploitation, imperial rent, class composition) is wrong by an unknown, county-varying margin.

**Independent Test**: Hydrate one county-year (e.g., the historically-failing Wayne County, MI, 2010), sum the reconstructed detail rows, and confirm the result reconciles to the BLS-published county total within the agreed tolerance — where the prior approach was off by −14.6%.

**Acceptance Scenarios**:

1. **Given** a county-year whose detail is partially suppressed by BLS, **When** the simulation reads county employment and wages, **Then** the summed detail reconciles to the BLS-published county Total-Covered figure within ±2%.
2. **Given** Wayne County, MI, 2010 (the spec-067 spot-check that previously failed at −14.6%), **When** county-total employment is computed from the table, **Then** it is within ±2% of the BLS-published rollup.
3. **Given** any county-year, **When** per-ownership totals (Federal, State, Local, Private) are summed, **Then** each reconciles to the BLS-published by-ownership total within ±2%.

---

### User Story 2 - Reference database is rebuildable from staged source (Priority: P2)

As a maintainer, I can rebuild the QCEW portion of the reference database from the BLS source files already staged on disk, for every year 2010–2024, with a single documented operation and no network access — restoring the reproducibility that was lost when the loader was deleted.

**Why this priority**: "Up to standard once and for all" requires the database to be reproducible, not a frozen artifact. This story re-establishes that for QCEW (the largest fact table) and sets the pattern the broader build-pipeline effort (spec-098) generalizes.

**Independent Test**: From a database with an empty `fact_qcew_annual`, run the loader against the staged source files and confirm the table is populated for all 15 years with sane per-year row counts and full county coverage.

**Acceptance Scenarios**:

1. **Given** the staged BLS source files for 2010–2024 and an empty target table, **When** the loader runs, **Then** the table is populated for all 15 years covering all U.S. counties plus DC and Puerto Rico.
2. **Given** a completed load, **When** the loader is run again, **Then** it produces an identical table (idempotent) and identical reconstructed values (deterministic).
3. **Given** an interrupted load, **When** the loader is re-run, **Then** it resumes from the last completed year rather than restarting.

---

### User Story 3 - Reconstructed values are distinguishable and auditable (Priority: P3)

As an analyst or auditor, I can tell which stored values are observed (BLS-disclosed) versus reconstructed (imputed), and I can review a per-load report quantifying how much of each county-year was suppressed and reconstructed, so the provenance and quality of the data are transparent.

**Why this priority**: Reconstructed economic data must never masquerade as observed data. Provenance protects scientific integrity and lets downstream consumers weight or exclude imputed values if they choose.

**Independent Test**: Query the table and confirm every value carries an observed/imputed marker; open the load's audit report and confirm it states the suppression rate and imputed share per year.

**Acceptance Scenarios**:

1. **Given** a loaded table, **When** any row is inspected, **Then** it indicates whether its employment/wage magnitudes were observed or reconstructed.
2. **Given** a completed load, **When** the audit report is opened, **Then** it lists, per year, the share of cells suppressed, the share reconstructed, and the distribution of per-county reconciliation residuals.

---

### Edge Cases

- **County total itself suppressed**: When even the county Total-Covered constraint is withheld, the system MUST fall back to the highest available published subtotal (or sum of disclosed lower levels) and flag the county-year as lower-confidence in the audit report, rather than silently undercounting.
- **Apportionment basis missing**: When a suppressed cell has no published establishment count to apportion by, the system MUST apply a documented fallback (e.g., the national average employment-per-establishment for that industry, else an equal split) so totals still reconcile.
- **NAICS revisions across years** (2012, 2017 vintages): The system MUST keep industry identity consistent so a county-year reconciles internally regardless of the source year's classification vintage.
- **County boundary/FIPS changes over time** (e.g., Shannon→Oglala Lakota SD 46102; independent-city merges): The system MUST resolve county identity per year so coverage is correct.
- **Non-county / statewide / overseas pseudo-areas** in the source (e.g., "Unknown Or Undefined", US-wide, overseas codes): The system MUST exclude these from county-grain output (or map them deliberately), never letting them pollute county totals.
- **Integer reconciliation**: Reconstructed employment counts MUST be rounded so the children sum exactly to the (real-valued) parent constraint without drift.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST populate the canonical `fact_qcew_annual` table from the staged BLS annual source files for years 2010–2024, at the established grain (county × 6-digit industry × ownership × year).
- **FR-002**: The system MUST reconstruct magnitudes for cells BLS suppresses, so that, per county-year, the summed detail reconciles to the BLS-published county Total-Covered figure within the agreed tolerance.
- **FR-003**: Reconstruction MUST be constrained by the BLS-published higher-aggregation totals present in the same source (county total, county-by-ownership, and the NAICS sector / 3- / 4- / 5-digit subtotals).
- **FR-004**: Reconstruction MUST apportion each constraint's unobserved remainder across its suppressed children using establishment counts (which BLS publishes even when employment and wages are withheld) as the basis.
- **FR-005**: Every stored magnitude MUST carry a provenance marker indicating whether it was observed (BLS-disclosed) or reconstructed (imputed).
- **FR-006**: Per-ownership county totals (Federal, State, Local, Private) MUST reconcile to the BLS-published by-ownership totals within the agreed tolerance.
- **FR-007**: The load MUST be idempotent: re-running over the same source yields an identical table.
- **FR-008**: Reconstruction MUST be deterministic: identical inputs yield identical reconstructed values across runs and machines.
- **FR-009**: The system MUST emit a per-load audit report summarizing, per year, county coverage, suppression rate, reconstructed share, and the distribution of per-county reconciliation residuals.
- **FR-010**: The existing simulation consumers of QCEW data MUST obtain accurate totals with no further changes beyond those spec-067 already made.
- **FR-011**: The load MUST NOT require network access; it reads only the locally-staged source files.
- **FR-012**: The load MUST be checkpointed per year so an interrupted run resumes rather than restarts.
- **FR-013**: The system MUST resolve county identity correctly for each year despite NAICS-vintage and county-boundary/FIPS changes over the 2010–2024 span.
- **FR-014**: The system MUST exclude non-county and statewide/overseas pseudo-areas from county-grain output so they do not distort county totals.
- **FR-015**: When a required published constraint is itself unavailable, the system MUST apply and record a documented fallback rather than emit a silent undercount.

### Key Entities *(include if feature involves data)*

- **County Industry Record**: One county's value for a specific 6-digit industry, ownership sector, and year — establishments, employment, and total wages — plus a marker of whether each magnitude was observed or reconstructed. The grain consumed by the simulation.
- **Published Aggregate (Constraint)**: A BLS-published subtotal (county total, county-by-ownership, or an intermediate NAICS rollup) used as a reconciliation target that reconstructed children must sum to.
- **Suppression Indicator**: The BLS confidentiality flag distinguishing disclosed from withheld cells in the source.
- **Reconciliation / Audit Report**: A per-load artifact recording coverage, suppression and reconstruction rates, and per-county residuals against the published totals.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For ≥99% of county-years (2010–2024), summed county employment reconciles to the BLS-published county total within ±2%.
- **SC-002**: For ≥99% of county-years, summed county wages reconcile to the BLS-published county total within ±2%.
- **SC-003**: Wayne County, MI, 2010 county-total employment reconciles within ±2% (versus the prior −14.6% undercount).
- **SC-004**: For ≥95% of county-ownership-years, per-ownership totals reconcile within ±2%.
- **SC-005**: For each year, reconstructed national employment is within ±1% of the BLS-published national Total-Covered figure (top-of-hierarchy sanity check).
- **SC-006**: 100% of stored magnitudes carry an observed/reconstructed provenance marker.
- **SC-007**: The full 2010–2024 table is reproducible from staged source in a single documented operation with no network access.
- **SC-008**: Re-running the load yields a byte-identical table (idempotent and deterministic).
- **SC-009**: A per-load audit report is produced that quantifies suppression rate and reconstructed share per year and the residual distribution.

## Assumptions

- **Tolerance**: ±2% is adopted as the working reconciliation target; spec-097 ratifies the final figure. (This re-bases spec-067's acceptance criteria, which were infeasible because they expected raw suppressed leaves to match published totals.)
- **Establishment counts survive suppression**: Verified in the 2023 source (suppressed cells publish establishment counts while employment/wages are blank); assumed to hold across 2010–2024.
- **Published constraints are largely disclosed**: County and intermediate rollups are mostly non-suppressed and serve as reliable reconciliation targets.
- **Target schema**: The canonical reference schema in this repository (`src/babylon/reference/schema.py`) is the build target; the stale schema copy in the external data trove is not used.
- **Write target** *(owner decision 2026-07-02)*: The canonical reference database lives in the data trove at `/media/user/data/babylon-data/sqlite/marxist-data-3NF.sqlite`, reached from this repository via the `data/sqlite` directory symlink. The loader writes there; there is exactly one database file.
- **Staged source**: BLS annual source files for 2010–2024 are present locally; no download is required.
- **Loader home** *(owner decision 2026-07-02, supersedes the original "re-homed into the reference package" wording)*: The reimplemented loader lives in the external `babylon-data` package (`/home/user/projects/game/babylon-data`). This spec includes only the **minimal viable packaging** needed to run it: rename the package directory to an importable `babylon_data`, add a `pyproject.toml`, fix the QCEW subtree's imports (they still reference the deleted `babylon.data.*` paths), and consume it from this repository as a path dependency. Full packaging of the remaining ~24 loaders (remote, CI, versioned release) belongs to spec-098.
- **Recovery reference**: The deleted loader is available in version-control history (`4ce7c96a^`, mirrored in `mutants/` and the babylon-data repo) as a starting reference, but is corrected in place (it never handled suppression).

## Dependencies & Relationships

- **Supersedes spec-067 (QCEW ownership/NAICS normalization)**: Replaces the lossy post-load deletion approach with correct construction at load time. The canonical grain and the rate-of-profit band changes from spec-067 are retained.
- **Resolves spec-097 (QCEW suppression amendment)**: Records "synthetic imputed totals" as the chosen mitigation and re-bases the acceptance criteria. Spec-097 is finalized as the decision record.
- **First leg of spec-098 (reference-DB reproducible build pipeline)**: Establishes the loader-restoration pattern (recover from history → re-home into the reference package → wire a build task) that spec-098 generalizes to the remaining sources, plus the validation gate and hygiene work.
- **Consumers**: The county hydration and aggregation paths that read QCEW employment and wages benefit automatically (FR-010).

## Out of Scope

- The other ~24 deleted source loaders, the end-to-end build orchestrator, and the database validation gate — these belong to spec-098.
- Re-downloading or extending QCEW beyond 2024, and quarterly (sub-annual) QCEW data.
- State- and metro-grain QCEW tables beyond what current consumers require (this spec targets the county-grain `fact_qcew_annual`).
- Changes to downstream economic formulas; only the accuracy and provenance of the QCEW data change.
