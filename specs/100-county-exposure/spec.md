# Feature Specification: County-Exposure Loader (BEA I-O imports × QCEW shares)

**Feature Branch**: `100-county-exposure`
**Created**: 2026-07-03
**Status**: Draft
**Program**: 09 Full-Game Build, Lane D (data). Audit-advisory number: spec-100.
**Input**: Program 09 §2 spec-100 entry + `src/babylon/engine/systems/phi_distribution.py` docstring.

## Overview

The imperial-rent Φ-distribution system (`phi_distribution.distribute_phi_week_to_counties`)
splits each external bloc's weekly Φ inflow across US counties using a
`county_exposure: {county_fips: weight}` map whose weights **MUST sum to 1.0**
(the function raises rather than silently renormalize). That map has never been
computed — the MVP passes it in by hand. Its docstring names the exact source:
"BEA I-O imports × QCEW industry shares."

This feature builds that map as a reproducible reference-data loader in the
**babylon-data** repo, following the spec-086 QCEW pattern (staged rebuild,
atomic swap, JSON audit contract, `logical_table_hash`). It also aggregates the
monthly bilateral-trade fact table to bloc-year totals. Two **new** SQLite
reference tables are added; no existing table is mutated; **zero engine-dynamics
change** (the consumer wiring is spec-101, a separate engine-lane spec).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compute & persist the county import-exposure map (Priority: P1)

A maintainer runs `mise run data:exposure -- --apply`. The loader reads the BEA
I-O import coefficients, the QCEW county employment, and the NAICS↔BEA
concordance already present in the reference DB; computes, for each external
bloc and year, a per-county import-exposure weight that sums to 1.0; and
persists it to `fact_county_exposure_by_external` via a staged build + atomic
swap. A JSON+Markdown audit artifact is written.

**Why this priority**: This is the deliverable spec-101 blocks on (sync point
S1). Without it the Φ-distribution circuit cannot go live.

**Independent Test**: Seed a small in-memory reference DB (fixture counties,
NAICS, BEA industries, concordance, import coefficients, QCEW rows), run the
loader in dry-run, and assert per-(bloc, year) weights sum to 1.0 and the
top-weighted counties match the seeded import-intensive industries.

**Acceptance Scenarios**:

1. **Given** a reference DB with BEA import coefficients, QCEW employment, and
   the NAICS↔BEA concordance for one year, **When** the loader runs in dry-run,
   **Then** for that year the emitted per-bloc county weights sum to 1.0 within
   1e-9 and every weight is in [0, 1].
2. **Given** the same DB, **When** the loader runs twice with `--apply`, **Then**
   the `logical_table_hash` of `fact_county_exposure_by_external` is identical
   across the two runs (determinism, III.7).
3. **Given** a county with employment only in an industry that has no import
   coefficient, **When** the loader runs, **Then** that county receives weight
   0.0 (it appears with no exposure, not an error).
4. **Given** the `--apply` path completes, **When** the swap runs, **Then** the
   canonical table is promoted and a `__pre_100` backup is retained (or, on a
   first-ever build, no backup is required and the swap still succeeds).

### User Story 2 - Aggregate bilateral trade to bloc-year totals (Priority: P2)

The same loader run aggregates the monthly bilateral-trade fact table to
bloc-year totals in `fact_bilateral_trade_annual`, so a downstream engine spec
can populate external-node trade magnitudes.

**Why this priority**: Needed by spec-101 for external-node trade fields, but
the Φ-distribution map (US1) is the harder, gating deliverable.

**Independent Test**: Seed monthly trade rows for two blocs across two years,
run the aggregation, and assert each bloc-year total equals the exact sum of its
months for imports, exports, and total.

**Acceptance Scenarios**:

1. **Given** monthly import/export rows for a bloc-year, **When** the loader
   aggregates, **Then** the annual row equals the exact sum of the present
   months (missing months contribute nothing; they are not treated as zero
   unless the source row is absent).
2. **Given** two identical runs, **When** aggregation completes, **Then** the
   `logical_table_hash` of `fact_bilateral_trade_annual` reproduces.

### User Story 3 - Audit artifact with reconciliation & coverage (Priority: P2)

Every run emits a schema-validated JSON audit report plus a human Markdown
render, recording per-year reconciliation, concordance coverage, table hashes,
and git provenance — the spec-086 audit-contract house pattern.

**Why this priority**: The audit is the verifiable-claim record (III.8) and the
gate evidence; it must ship with the loader, not after.

**Independent Test**: Run the loader against the fixture DB and assert the
emitted JSON validates against the contract schema and that the reconciliation
gate field reflects the ±2% band.

**Acceptance Scenarios**:

1. **Given** a completed run, **When** the audit is written, **Then** the JSON
   validates against `contracts/exposure_audit.schema.json`.
2. **Given** a completed year, **When** the reconciliation is computed, **Then**
   the report records `Σ county raw-exposure` vs `Σ covered BEA import
   coefficients` and whether it is within ±2%.

### Edge Cases

- **Non-unit weight sum**: if any per-(bloc, year) weight vector does not sum to
  1.0 within tolerance, the run FAILS the validation gate and the canonical
  table is left untouched (the consumer rejects non-unit sums; the loader must
  guarantee the invariant it feeds).
- **County/NAICS/BEA code absent from a dimension**: HALT with an explicit
  unknown-dimension error (spec-086 FR-013 halt-on-unknown; no silent skip).
- **A year present in one source but not another** (e.g., BEA I-O missing a
  year QCEW has): that year is skipped for exposure with a recorded reason; it is
  never fabricated.
- **Industry with import coefficient but zero national employment** (uncovered
  by the concordance): excluded from both numerator and the reconciliation
  denominator; counted in the reported coverage metric.
- **First-ever build** (no canonical table to back up): swap succeeds without a
  `__pre_100` backup; `logical_table_hash` of the absent prior table is the
  documented `absent:<name>` sentinel.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The loader MUST compute, for each external bloc and each covered
  year, a per-county weight `weight[C] = raw[C] / Σ raw`, where
  `raw[C] = Σ_bea import_coeff[bea] · (county_emp[C,bea] / national_emp[bea])`,
  over BEA industries that have an import coefficient AND nonzero national
  employment.
- **FR-002**: `import_coeff[bea]` MUST be sourced from `fact_bea_io_coefficient`
  rows with `source_industry_id` = the "Noncomparable imports and
  rest-of-the-world adjustment" BEA industry, `table_type_id` = the USE table,
  for the target year's annual `time_id`.
- **FR-003**: `county_emp[C,bea]` MUST be computed by joining QCEW county
  employment to BEA industries through the `bridge_naics_bea` concordance,
  summing QCEW ownership slices {federal, state, local, private} (own_codes
  1/2/3/5), and apportioning split-mapped NAICS by the concordance weight
  (defaulting an absent weight to `1 / split_count`).
- **FR-004**: The per-(bloc, year) weight vector MUST sum to 1.0 within 1e-9 and
  every weight MUST lie in [0, 1]; a violation FAILS the run (no
  renormalization band).
- **FR-005**: The loader MUST persist the map to a new reference table
  `fact_county_exposure_by_external` keyed by (annual `time_id`, external bloc,
  county), and the bloc-year trade aggregation to `fact_bilateral_trade_annual`
  keyed by (annual `time_id`, country).
- **FR-006**: Both tables' ORM definitions MUST be added additively to
  `src/babylon/reference/schema.py` (babylon owns the schema; babylon-data
  imports it one-way). No existing table is altered.
- **FR-007**: Persistence MUST use a staged `__new` build, per-year transactional
  writes, and an atomic swap that retains a `__pre_100` backup, with
  rollback-from-backup and drop-backup operations (spec-086 lifecycle).
- **FR-008**: Row insertion order MUST be deterministic so `logical_table_hash`
  (SHA-256 over an ordered projection, tolerant of physical-schema drift)
  reproduces run-to-run.
- **FR-009**: The bilateral-trade aggregation MUST sum monthly `imports` and
  `exports` (USD millions) to bloc-year totals plus a derived total; a month
  absent in the source contributes nothing (not a fabricated zero).
- **FR-010**: Every run (dry-run and apply) MUST emit a JSON audit report that
  validates against `contracts/exposure_audit.schema.json`, plus a Markdown
  render, recording: mode, years, DB path, DB sha256 pre/post, duration, git
  provenance for both repos, per-table `logical_table_hash`, per-year
  reconciliation, and concordance coverage.
- **FR-011**: The reconciliation gate MUST compare `Σ_C raw_exposure[C]` against
  `Σ_bea import_coeff[bea]` over the covered industries (sourced from the DB's
  own BEA import rows) and record whether the residual is within ±2%.
- **FR-012**: The audit MUST record `concordance_coverage` = (Σ covered import
  coefficient) / (Σ all import coefficient) as a first-class data-quality metric,
  and MUST record `bloc_invariant = true` while the county distribution is the
  same across blocs (see Assumptions).
- **FR-013**: The CLI MUST expose `--dry-run`, `--apply`, `--rollback-from-backup`,
  `--drop-backup`, `--years`, `--db`, and `--report-dir`, with exit codes
  0 (success) / 1 (validation failure, canonical untouched) / 2 (pre-flight or
  usage failure) / 130 (interrupted), reachable via `mise run data:exposure`.
- **FR-014**: On any unknown county FIPS / NAICS code / BEA code / ownership
  code / annual year with no dimension row, the loader MUST HALT with an explicit
  error naming the missing key (no silent skip).

### Key Entities

- **County import-exposure weight**: one (year, external bloc, county) → weight in
  [0,1]; per-(bloc, year) vector sums to 1.0; the materialized
  `county_exposure_by_external` the Φ-distribution consumes.
- **Bilateral trade annual**: one (year, country) → imports/exports/total in USD
  millions, aggregated from the monthly source.
- **External bloc**: a `dim_country` row with `is_region = 1` (the 8 loaded
  Census FT900 exhibit regions).
- **Import coefficient**: BEA USE-table coefficient from the "Noncomparable
  imports" source industry to a consuming industry — the import intensity of that
  industry's production.
- **NAICS↔BEA concordance**: `bridge_naics_bea`, the reference DB's grounded map
  from QCEW NAICS industries to BEA industries.
- **Audit report**: per-run JSON/Markdown provenance + reconciliation + coverage
  + table hashes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `mise run data:exposure -- --apply` completes with exit code 0 and
  writes a schema-valid audit artifact for the full 2010–2024 range.
- **SC-002**: For every (bloc, year), the county weights sum to 1.0 within 1e-9.
- **SC-003**: Running the loader twice yields identical `logical_table_hash`
  values for both tables (determinism).
- **SC-004**: For every covered year, the reconciliation residual
  (`Σ raw-exposure` vs `Σ covered import coefficients`) is within ±2%.
- **SC-005**: The bilateral-trade annual total for each seeded bloc-year equals
  the exact sum of its monthly source rows.
- **SC-006**: The audit reports a `concordance_coverage` value and the
  `bloc_invariant` flag; no existing reference table's row count or schema
  changes.

## Assumptions

- **Concordance is the DB's grounded `bridge_naics_bea`** (462 exact mappings,
  verified an antichain so summing does not double-count). It is goods-biased:
  it covers ~18 of the ~66 import-coefficient BEA industries with QCEW
  employment (the durable/nondurable manufacturing core, plus a few services).
  This is **theoretically apt** — unequal-exchange imperial rent is a
  tradeable-commodity phenomenon (Amin, Cope), so the map is a
  manufacturing/tradeable-goods import-exposure map. The concordance is **not
  extended** in this spec (that would fabricate mappings; III.8) — coverage is
  reported instead, and extending it to full service coverage is a future spec.
- **The county distribution is currently bloc-invariant.** The reference DB has
  no bloc×industry trade resolution (`fact_trade_monthly` is bloc-level total
  USD; one "bloc" is the product category "Advanced Technology Products"; the
  blocs geographically overlap). So the same import-exposure distribution
  applies to every bloc. This is disclosed via the audit `bloc_invariant` flag
  and stored per-bloc to match the consumer contract and to allow a future
  bloc×industry spec to differentiate without a schema migration.
- **`world_system_tier` is NULL for all 8 blocs** by original-loader design
  (the trade loader only classifies `is_region = 0` countries). The Program 09
  §2 note "(+ world_system_tier core/semi_periphery/periphery)" does not hold for
  these region rows; this spec does not populate the tier.
- **`fact_trade_monthly` is USD millions, not tons.** The aggregation therefore
  feeds the engine's `bilateral_trade_value` (USD) field; the distinct
  `bilateral_trade_tons` field needs FAF freight tonnage and is out of scope
  (a future 098-family slice). This unit reconciliation is a note for spec-101.
- **The engine's 8 external node ids** (`canada, china, eu, india,
  sub_saharan_africa, latin_america, russia_csi, southeast_asia`) differ from
  the 8 `dim_country` `is_region` blocs (EU, Advanced Technology Products, North
  America, Europe, Africa, Pacific Rim, Asia, Australia & Oceania). This spec
  keys on the `dim_country` blocs (its named source) and does **not** force a
  lossy crosswalk to the engine nodes; reconciling the two 8-sets is a spec-101
  (engine-lane) concern, eased by the bloc-invariance above.
- **Years 2010–2024** are the covered range (BEA I-O, QCEW annual, and trade
  monthly all cover it). Reads are against the canonical reference DB via the
  `data/sqlite` symlink; the trove DB is authoritative.
- **USGS minerals** ("regions with resources") is a flagged stretch (Program 09
  §6.5) and is **out of scope**.
