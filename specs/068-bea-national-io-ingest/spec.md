# Feature Specification: BEA National Industry I-O Ingest

**Feature Branch**: `068-bea-national-io-ingest`
**Created**: 2026-05-17
**Status**: Draft
**Input**: "068 BEA national industry I-O ingest"

## Clarifications

### Session 2026-05-17

- Q: Should FR-007 hold to "byte-identical" idempotency or match spec-067's amended epsilon-determinism contract? → A: **Epsilon-determinism ≤ 10⁻¹² on every float column; integer ID columns remain byte-identical.** Float64 weighted sums won't bit-match across runs (Python hash randomization, BLAS threading); this is the same failure mode that forced spec-067 to amend its idempotency SC mid-implementation. Inheriting that precedent up-front rather than re-discovering it.
- Q: How should multi-vintage BEA tables be stored (e.g., 2019 Use table published 2021, revised 2023)? → A: **Latest-vintage-only with a `vintage_published_date` audit column on `fact_bea_national_industry` and `fact_bea_io_coefficient`.** When BEA re-publishes, the new vintage replaces the prior row and the audit report names the supersession. Matches BEA's "use most recent vintage" recommendation; avoids per-vintage row-count bloat.
- Q: When a BEA industry has no I-O data for a year in scope (latest year not yet published), what does the per-(county, year) lookup return? → A: **Forward-fill from the most-recent-available year for that BEA industry, logged to the audit report under a `stale_share_fallback` category and counted against SC-008's <1 % uncovered threshold.** Matches BEA's own forward-fill convention.
- Q: Where does `fact_bea_national_industry.gross_output` come from — BEA Use table column total (consumer side) or Supply-Use industry output (producer side)? → A: **Supply-Use industry output (producer side).** Matches BEA's published industry-GDP figure exactly and reconciles cleanly with the FR-002 accounting identity (`intermediate_inputs_share + value_added_share = 1`).
- Q: Is the SC-005 stddev threshold (0.2) empirical or a placeholder? → A: **Directional threshold, not empirical.** Post-spec-067 baseline is exactly 0.0 (every county got the same hardcoded `0.5`), so any sub-uniform distribution proves the wiring works. The exact threshold may be re-tuned during the implementation plan after the first post-068 Michigan-83 baseline run measures the actual magnitude.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Populate the BEA national industry table (Priority: P1)

A simulation engineer wants the BEA national-industry I-O accounting tables
(`fact_bea_national_industry`, `fact_bea_io_coefficient`,
`dim_bea_io_table_type`) — currently defined in the schema but containing
**zero rows** — populated from the BEA Make+Use, Supply-Use, and
Total-Domestic-Requirements source CSVs already on disk under
`data/input-output/`. After ingest, the per-industry intermediate-inputs
ratio for each BEA industry × year is queryable from the reference DB.

**Why this matters**: spec-066, spec-067, and the hex_hydrator
documentation all reference the BEA national I-O table as the canonical
source of the "intermediate-inputs fraction" (currently hardcoded as
`0.5` in `src/babylon/persistence/hex_hydrator.py:107` as the
Shaikh-tractable economy-wide average). Without it, every county /
every industry uses the same `c/v` ratio, collapsing the real economic
heterogeneity between (e.g.) financial services (`c/v ≈ 0.3`) and
manufacturing (`c/v ≈ 2.0`).

**Independent test**: After ingest, `SELECT COUNT(*) FROM
fact_bea_national_industry` returns a row count proportional to
**BEA-industries × years-in-scope** (rough order: 70-100 industries × 15
years = ~1,000-1,500 rows). All rows have non-null
`intermediate_inputs_share` ∈ [0, 1] and the sum of per-industry
intermediate-inputs share weighted by industry GDP matches BEA's
published national-aggregate intermediate-inputs share within ±1 %.

---

### User Story 2 — Populate the full BEA I-O coefficient matrix (Priority: P2)

A simulation engineer wants the full Leontief intermediate-input
coefficient matrix populated (`fact_bea_io_coefficient`) so that the
per-(source-industry, target-industry) coefficient `a_ij` (dollar of
input industry `i` required per dollar of output industry `j`) is
queryable. This is the input to the per-county Leontief multiplier
calculation that derives `c` and circulating-capital flows in the
hex_hydrator and (eventually) the spec-023 (Capital Vol. II) circulation
system.

**Why this matters**: US1 alone gives a per-industry aggregate share
(`sum_i a_ij` per `j`). US2 gives the full I-O matrix so consumers can
distinguish "this industry needs steel" from "that industry needs
software," which is required for the spec-024 Capital Vol. III
average-rate-of-profit transformation procedure.

**Independent test**: `SELECT COUNT(*) FROM fact_bea_io_coefficient`
returns ~N² rows per year × years where N is the BEA-industry count
(~5,000 - 10,000 rows per year for the BEA-summary I-O level). Each row's
`coefficient_value` ∈ [0, 1] when normalized. The row-sum identity
holds: for every target industry `j`, the column-sum of input
coefficients matches the per-industry aggregate share from US1 within
±0.1 %.

---

### User Story 3 — Wire downstream consumers (hex_hydrator + future Vol-II/III) (Priority: P2)

After US1 + US2 land, the production code paths currently using the
hardcoded `_INTERMEDIATE_INPUTS_FRACTION = 0.5` switch to per-(county,
BEA-industry) lookups against the BEA tables via the NAICS→BEA
concordance that already exists at `data/bea/loader_concordance.py`.

**Why this matters**: This is the production-payoff user story — the
actual simulation behavior changes after wiring. Per-county `c` / `s` /
`s/(c+v)` values become heterogeneous in a way that reflects the real
industrial composition of each county.

**Independent test**: After wiring, `mise run sim:e2e-michigan`
produces a baseline trace where the standard deviation of `c/v` across
the 83 Michigan counties at terminal tick is at least 0.2 (vs the
post-spec-067 baseline where it is 0.0 — every county had the same `c/v`
because every county got the same intermediate-inputs fraction).

---

### User Story 4 — Validation against Shaikh's empirical magnitudes (Priority: P3)

After US3, the per-county `c/v` distribution is validated against Shaikh
(2016) *Capitalism: Competition, Conflict, Crises* empirical bands for
modern US capitalism. Per-industry `c/v` values are expected to land in
ranges consistent with Shaikh's 2000-2020 broad-measure observations:
manufacturing in `[1.5, 3.0]`, services in `[0.3, 1.0]`, retail in
`[0.5, 1.2]`, agriculture in `[2.0, 5.0]`.

**Why this matters**: The Shaikh empirical bands are the standard
modern-Marxian calibration target. Without this validation, the
spec-068 wiring could be technically correct but produce per-industry
`c/v` magnitudes inconsistent with real US capitalism.

**Independent test**: A new audit script
`tools/validate_bea_io_against_shaikh.py` reads the post-US3 per-county
`c/v` distribution from a canonical e2e run, groups by dominant
BEA-industry, and asserts each group's mean `c/v` falls inside Shaikh's
documented band (with a documented tolerance ≥ 50 % reflecting the
between-county heterogeneity within a single industry).

---

### Edge Cases

- **Multi-vintage I-O tables**: BEA publishes I-O tables on different
  schedules (Make+Use yearly, Supply-Use yearly, Total Domestic
  Requirements with a 2-3 year lag) and revises prior years on later
  publications. Storage policy: **latest-vintage-only**, with a
  `vintage_published_date` column on `fact_bea_national_industry` and
  `fact_bea_io_coefficient` that records when BEA published the
  vintage actually loaded. When BEA re-publishes a year, the new
  vintage replaces the prior row and the audit report names every
  supersession. Older vintages are not retained in the reference DB;
  if historical-vintage analysis is needed, archive snapshots via
  the spec-037 Parquet archival pipeline.
- **Missing-year I-O data**: If a BEA industry has no I-O data for a
  year in simulation scope (e.g., latest year is unpublished by BEA),
  the per-(county, year) lookup **forward-fills** from the most-recent
  available year for that BEA industry. Every forward-fill is logged
  to the audit report under a `stale_share_fallback` category and
  counted against SC-008's < 1 % uncovered threshold.
- **NAICS→BEA concordance gaps**: The BEA Summary-level I-O has
  ~70 industries; QCEW has 6-digit NAICS detail (~1100 industries).
  Many-to-one mapping is the default; QCEW NAICS codes lacking a BEA
  concordance entry fall back to an industry's parent NAICS-2-digit
  sector for I-O coefficient lookup.
- **BEA Detailed vs Summary tables**: BEA publishes I-O at multiple
  aggregation levels (Sector ~15 industries, Summary ~70, Detail ~400).
  Spec-068 ships at the Summary level (~70 industries) as a deliberate
  Shaikh-tractable choice; Detail-level ingestion is deferred to a
  follow-up spec.
- **Total Domestic Requirements vs Make+Use**: Make+Use are direct
  coefficients (input cost per dollar of output). Total Domestic
  Requirements are the Leontief inverse (direct + indirect; total
  domestic supply-chain demand per dollar of final demand). Spec-068
  ships Make+Use as the canonical input; Total Domestic Requirements
  is loaded for cross-validation and future Vol-III TRPF analysis.
- **Years before BEA-NAICS reconciliation (pre-1997)**: BEA's
  NAICS-based I-O tables don't cover years before 1997. Spec-068's
  2010-2024 simulation scope is well after this, so no
  historical-vintage handling is required.
- **Empty source CSVs**: If `data/input-output/make-use/` is missing
  expected files for a year in scope, the ingest halts with a clear
  error rather than silently producing partial data.

## Functional Requirements *(mandatory)*

- **FR-001**: The ingest tool MUST populate `fact_bea_national_industry`
  with one row per (BEA-industry × year) in the simulation scope
  (2010-2024), reading from `data/input-output/make-use/` and
  `data/input-output/supply-use/`.
- **FR-002**: Each `fact_bea_national_industry` row MUST include:
  `gross_output` (sourced from BEA **Supply-Use industry output** —
  producer side, matching BEA's published industry-GDP figure;
  **not** the Use-table column total, which is the consumer side),
  intermediate-inputs total, intermediate-inputs share
  (= intermediate_inputs / gross_output), and value-added share. The
  shares are constrained to `[0, 1]` and the sum
  `intermediate_inputs_share + value_added_share ≈ 1` within ±1 %
  (per BEA accounting identity).
- **FR-003**: The ingest tool MUST populate `fact_bea_io_coefficient`
  with the full direct-requirements matrix `a_ij` from the BEA Use
  table, normalized to "dollar of input industry `i` per dollar of
  output industry `j`."
- **FR-004**: An accounting validation MUST verify the column-sum
  identity:
  `sum_i a_ij ≈ fact_bea_national_industry.intermediate_inputs_share[j]`
  within ±0.1 % for every (target-industry, year) pair.
- **FR-005**: `src/babylon/persistence/hex_hydrator.py` MUST be
  refactored to replace the hardcoded `_INTERMEDIATE_INPUTS_FRACTION
  = 0.5` with a per-(county, industry-mix) computation that derives
  the intermediate-inputs share from `fact_bea_national_industry`
  weighted by the county's QCEW industry employment shares.
- **FR-006**: The NAICS→BEA-summary concordance MUST be loaded into a
  reference table (likely `dim_naics_bea_concordance`) from
  `data/bea/loader_concordance.py` source data. Concordance gaps fall
  back to NAICS-2-digit sector aggregation.
- **FR-007**: The ingest MUST be idempotent under epsilon-determinism
  semantics (inherited from spec-067's amended idempotency contract).
  Running it twice in succession produces:
  - **Byte-identical** integer/categorical columns
    (`bea_industry_id`, `source_industry_id`, `target_industry_id`,
    `time_id`, `table_type_id`, `vintage_published_date`).
  - **Float-equal within ≤ 10⁻¹² relative error** on every numeric
    column (`gross_output`, `intermediate_inputs`, `value_added`,
    `intermediate_inputs_share`, `value_added_share`,
    `coefficient_value`).
  Byte-identical idempotency on floats is not enforceable on this stack
  (Python hash randomization + BLAS threading + accumulated float64
  rounding), which is the failure mode spec-067 hit in its T054b
  byte-identical regen test.
- **FR-008**: An audit report (`reports/ingest/bea_io_ingest_<timestamp>.{md,json}`)
  MUST summarize: per-year row counts, accounting-identity violations
  (FR-002 and FR-004), per-industry intermediate-inputs share top-10
  and bottom-10, NAICS→BEA concordance coverage percentage.
- **FR-009**: A `--rollback` mode MUST restore `fact_bea_national_industry`
  and `fact_bea_io_coefficient` to their empty pre-spec-068 state in
  case the post-ingest validation flags critical mismatches.
- **FR-010**: The pre-spec-068 fallback (`_INTERMEDIATE_INPUTS_FRACTION
  = 0.5`) MUST remain as a documented fallback when the BEA tables are
  empty, with a clear log warning that the fallback is being used. This
  preserves the spec-066 / spec-067 baseline behavior for operators who
  haven't yet run the spec-068 ingest.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `SELECT COUNT(*) FROM fact_bea_national_industry` returns
  ≥ 800 rows after spec-068 ingest (rough order: 70 BEA-summary
  industries × 12 years of full data = 840 minimum; allow some years
  to lag).
- **SC-002**: `SELECT COUNT(*) FROM fact_bea_io_coefficient` returns
  ≥ 50,000 rows after ingest (70² × 12 years ≈ 58,800; allow
  zero-coefficient cells to be omitted).
- **SC-003**: 100 % of `fact_bea_national_industry` rows satisfy
  `intermediate_inputs_share + value_added_share = 1 ± 0.01` (the
  BEA accounting identity).
- **SC-004**: 100 % of (target-industry, year) pairs satisfy the
  Leontief column-sum identity from FR-004 within ±0.1 %.
- **SC-005**: Post-US3 wiring, the `mise run sim:e2e-michigan` baseline
  shows per-county `c/v` standard deviation across the 83 Michigan
  counties of at least 0.2 (vs the post-067 baseline where every county
  had identical `c/v` because every county got the same 0.5 hardcoded
  fraction). The 0.2 figure is a **directional threshold** — the
  post-067 baseline is exactly 0.0, so any sub-uniform distribution
  proves the wiring works. The exact threshold may be re-tuned during
  the implementation plan after the first post-068 Michigan-83 baseline
  measures the real magnitude.
- **SC-006**: For each BEA-summary industry, the population-weighted
  mean per-county `c/v` falls within ±50 % of Shaikh's documented
  empirical band for that industry, as validated by
  `tools/validate_bea_io_against_shaikh.py`.
- **SC-007**: The full BEA-ingest workflow (US1 + US2 + US3) executes
  in under 15 minutes wallclock for the 2010-2024 scope, end-to-end.
- **SC-008**: The audit report classifies every (county, year) row by
  concordance-coverage status: full match, NAICS-2-digit fallback, or
  uncovered (must be < 1 % of QCEW employment to pass).

## Assumptions

- The BEA Make+Use, Supply-Use, and Total Domestic Requirements source
  CSVs are already on disk at `data/input-output/{make-use, supply-use,
  total-domestic-requirements}/` (verified 2026-05-17). Spec-068 does
  NOT re-download from BEA; it ingests from the existing local copies.
- The schema tables `fact_bea_national_industry`,
  `fact_bea_io_coefficient`, and `dim_bea_io_table_type` already exist
  in `src/babylon/reference/schema.py` (verified 2026-05-17). Spec-068
  populates them; no schema migration is required.
- Loader stubs at `data/bea/{io_loader.py, loader_national.py,
  loader_county.py, loader_concordance.py}` exist as Python skeletons
  (verified 2026-05-17). Spec-068 fills them in; the stubs' function
  signatures may be revised.
- The simulation operates on the **BEA Summary level (~70 industries)**,
  not the Detail level (~400 industries). The Summary level is
  Shaikh-tractable and avoids the Detail level's per-cell sparsity
  problems. Detail-level ingestion is deferred to a future follow-up.
- Spec-068 ships BEFORE spec-070's BLS-suppression amendment is
  resolved. The spec-068 wiring works regardless of which spec-070
  mitigation is chosen; the per-industry intermediate-inputs share is
  orthogonal to the BLS-suppression issue (which affects `v`, not the
  composition of `c`).
- The QCEW employment shares (from `fact_qcew_annual` post-spec-067)
  are the per-county industry-mix weights. Counties' "industry mix" is
  derived from county-level NAICS employment counts.
- Spec-068 does NOT touch the spec-066 ownership filter or the spec-067
  rollup-row removal. Spec-068's only fact-table writes are to
  `fact_bea_national_industry` and `fact_bea_io_coefficient` (both
  currently empty); no spec-067 contracts are renegotiated.

## Dependencies

- **Spec-037** (Postgres Runtime DB) — already shipped; provides the
  persistence boundary.
- **Spec-062** (Cross-Scale Integration) — already shipped; defines
  the immutable-reference-lookup pattern that the BEA tables will
  participate in.
- **Spec-066** (Marx Coherence Fixes) — already shipped; established
  the hex_hydrator's `_INTERMEDIATE_INPUTS_FRACTION = 0.5` as the
  Shaikh-tractable interim with explicit "deferred to spec-068" markers.
- **Spec-067** (QCEW Ownership and NAICS Hierarchy Normalization) —
  already shipped; provides the per-(county, year) industry employment
  base that spec-068's wiring uses to compute the county-specific
  industry mix.
- **BEA source data** — already on disk at `data/input-output/`. No
  external API calls required during ingest.
- **NAICS→BEA concordance** — source file referenced by
  `data/bea/loader_concordance.py`; spec-068 will load it as part of
  US1.

## Key Entities

- **fact_bea_national_industry** (existing schema, currently empty):
  Per-(BEA-industry, year) aggregate I-O metrics. Columns expected:
  `bea_industry_id`, `time_id`, `gross_output`, `intermediate_inputs`,
  `value_added`, `intermediate_inputs_share`, `value_added_share`,
  `vintage_published_date` (audit column tracking which BEA publication
  vintage the row was sourced from; latest-only policy per Clarifications Q2).
- **fact_bea_io_coefficient** (existing schema, currently empty):
  Per-(source-industry, target-industry, table-type, year) direct
  coefficient `a_ij`. Columns: `source_industry_id`,
  `target_industry_id`, `table_type_id`, `time_id`,
  `coefficient_value`, `vintage_published_date` (same audit
  semantics as `fact_bea_national_industry`).
- **dim_bea_io_table_type** (existing schema): Discriminator for the
  three BEA table families (Make+Use, Supply-Use, Total Domestic
  Requirements). Already has its check-constraint defined.
- **dim_naics_bea_concordance** (new or existing): Per-(NAICS-6-digit,
  BEA-summary-industry) many-to-one mapping. Populated from BEA's
  published NAICS-to-BEA concordance file.
- **fact_qcew_annual** (post-spec-067 canonical leaves): The per-
  (county, NAICS-6-digit, ownership, year) employment + wages base
  that drives the county industry-mix weights used in US3.
