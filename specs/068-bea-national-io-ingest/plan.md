# Implementation Plan: BEA National Industry I-O Ingest

**Branch**: `068-bea-national-io-ingest` | **Date**: 2026-05-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/068-bea-national-io-ingest/spec.md`

## Summary

Populate the empty `fact_bea_national_industry` and `fact_bea_io_coefficient`
reference tables from BEA Make+Use, Supply-Use, and Total Domestic Requirements
XLSX files already on disk at `data/input-output/`. Wire the
`hex_hydrator` (currently using a hardcoded `_INTERMEDIATE_INPUTS_FRACTION =
0.5` economy-wide average) to compute per-(county, BEA-industry) intermediate-
inputs shares from the new tables, weighted by the county's QCEW employment
mix via the existing `bridge_naics_bea` concordance.

Technical approach (post-Clarifications):

1. **Idempotency**: epsilon-determinism ≤ 10⁻¹² on every float column;
   byte-identical on every integer ID column. Inherits spec-067's amended
   contract proactively. (FR-007, Clarification Q1.)
2. **Vintage tracking**: add `vintage_published_date` column to both fact
   tables; UPSERT replaces older vintages with newer ones; supersessions
   are named in the audit report. (Edge case + Clarification Q2.)
3. **Forward-fill on missing-year I-O**: per-(county, year) lookups for a
   BEA industry with no I-O data for the target year fall back to the most
   recent available year for that industry; logged to audit under
   `stale_share_fallback`. (Clarification Q3.)
4. **Source convention**: `gross_output_millions` comes from BEA Supply-Use
   industry output (producer side), reconciling cleanly with the FR-002
   accounting identity `intermediate_inputs_share + value_added_share = 1`
   within ±1 %. (Clarification Q4.)
5. **Primitives-only storage**: per constitution II.2, the schema stores
   the three BEA primitives (`gross_output_millions`,
   `intermediate_inputs_millions`, `value_added_millions`) — NOT the
   derived shares. Shares are computed lazily by
   `BEAShareLookupService` (new in `src/babylon/reference/bea/`), which
   IS the constitutional interface (II.11) between the BEA subsystem and
   the persistence subsystem.
6. **Existing assets reused**:
   - `bridge_naics_bea` (existing table) IS the spec's hypothesized
     `dim_naics_bea_concordance` — no new table required.
   - `dim_bea_io_table_type` (existing) already has the CHECK
     constraint covering `'USE','MAKE','SUPPLY','TOTAL_REQ','IMPORT_USE'`.
   - Loader stubs at `data/bea/{io_loader.py, loader_national.py,
     loader_concordance.py, loader_county.py}` already document the BEA
     XLSX structure; spec-068 completes them.

## Technical Context

**Language/Version**: Python 3.12+ (existing project standard).
**Primary Dependencies**:

- SQLAlchemy 2.x (ORM writes to `fact_bea_*` and `bridge_naics_bea`)
- Pydantic 2.x (ingest-time row validation, audit-report schema)
- pandas + openpyxl (BEA XLSX reading; both already in `pyproject.toml`
  for existing data loaders)
- pytest 8.x + Hypothesis (unit + property-based tests, inherited from
  spec-053/054/055/056 invariants discipline)

**Storage**:

- SQLite reference DB at `data/sqlite/marxist-data-3NF.sqlite` (WAL +
  2 GiB cache + 12 GB mmap_size — already set per spec-067 PRAGMA
  optimization).
- Source data: read-only from `data/input-output/{make-use, supply-use,
  total-domestic-requirements}/*.xlsx`.
- Concordance source: read-only from
  `data/bea/MAKE-USE-IMPORTS (BEFORE REDEFINITIONS).zip` (BEA's
  official NAICS↔BEA concordance bundle).

**Testing**:

- Unit: `tests/unit/reference/bea/test_loader_national.py`,
  `test_loader_io_coefficient.py`, `test_share_lookup_service.py`,
  `test_audit_report.py`.
- Integration: `tests/integration/reference/bea/test_end_to_end_ingest.py`
  (writes to a transient test DB; gated under `mise run test:int`).
- Property tests (Hypothesis): accounting-identity invariance, column-sum
  identity, idempotency.
- Doctest: in pure formula functions (e.g., `compute_county_share`).

**Target Platform**: Linux dev host; runs as
`poetry run python tools/load_bea_io.py [--rollback] [--years 2010-2024]`
or `mise run data:bea-load`.

**Project Type**: CLI ingestion tool + reference-DB writer + persistence
wiring change. Single-project layout.

**Performance Goals**: SC-007 — full ingest (US1+US2+US3 wiring) under
**15 minutes wallclock** for 2010-2024 scope. Empirically tractable: ~1500
rows in `fact_bea_national_industry` and ~50K-100K rows in
`fact_bea_io_coefficient` (sparse Leontief); bulk INSERT via
SQLAlchemy `Core.execute(insert(...).values(...))` batched at 10K rows.

**Constraints**:

- Idempotency: epsilon-determinism ≤ 10⁻¹² on float cols, byte-identical
  on integer IDs (FR-007 post-clarification).
- BEA accounting identity: `II_share + VA_share = 1 ± 1 %` (FR-002).
- Leontief column-sum identity: `sum_i a_ij ≈ II_share[j] ± 0.1 %` (FR-004).
- Forward-fill fallback: < 1 % of QCEW employment (SC-008).
- Constitutional gate II.11: hex_hydrator MUST consume BEA tables only
  through `BEAShareLookupService`, never via raw SQL.
- Constitutional gate II.2: shares are NOT stored; they are computed.

**Scale/Scope**:

- `fact_bea_national_industry`: ~840-1500 rows (≈70 BEA-summary
  industries × 12-21 years of full data).
- `fact_bea_io_coefficient`: ~50K-100K rows (sparse 70² × 12-21 years).
- `bridge_naics_bea`: ~1100-1500 NAICS-6-digit → 70 BEA-summary mappings.
- hex_hydrator rewiring affects 83 Michigan counties × 11 base years
  (2010-2020 simulation scope per spec-062 cross-scale integration).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### P0 (Never Drop)

| Principle | Status | Notes |
|---|---|---|
| I.19 Dialectic Primitive | N/A | No dialectic mutation; reference-data ingest. |
| I.20 Spatial Substrate | **PASS** | No substrate mutation; consumes county QCEW; writes industry-keyed tables only. |
| II.9 Morphism Dyadic | N/A | No morphism graph changes. |
| III.7 Determinism Hash | **PASS** | FR-007 epsilon-determinism is the operational form of the determinism-hash principle; replayability preserved (same inputs → same outputs within ε). |
| III.8 Aleksandrov Test | **PASS** | Every column traces to a BEA-published material relation: `gross_output_millions` ⇄ Supply-Use industry output, `intermediate_inputs_millions` ⇄ Use-table column sum, `coefficient` ⇄ direct-requirements per dollar of output. |
| V Verb Atomicity | N/A | No player verbs invoked. |

### P1 (Load-Bearing) — domain-relevant

| Principle | Status | Notes |
|---|---|---|
| I.2 Imperial Rent | **PASS** | Per-county c/v heterogeneity (which spec-068 enables) is the precondition for Φ to vary by county — directly serves I.2's measurability. |
| II.2 Primitives vs Derived | **PASS w/ guard** | Schema stores **only** the three BEA primitives; shares are NEVER persisted. `BEAShareLookupService` computes shares from the primitives at read time. Plan and data-model both record this. |
| II.5 AI Observes | N/A | No AI involvement. |
| II.6 State is Data, Engine is Transformation | **PASS** | `fact_bea_*` is reference data (immutable post-load); hex_hydrator is a transformation. |
| II.11 Subsystem Table Ownership | **PASS w/ gate** | The BEA tables belong to the *reference / national-economic-accounts* subsystem. The hex_hydrator (persistence subsystem) consumes them **only** through the new `BEAShareLookupService` interface defined under `contracts/`. Direct SQL on `fact_bea_*` from outside the BEA subsystem is explicitly prohibited by this plan. |
| III.1 No Magic Constants | **PASS** | The 0.5 constant being **removed** IS the spec-068 work; the fallback retention under FR-010 is gated behind an explicit "BEA tables empty" log warning. |
| III.4 Data Catalog | **PASS** (post-remediation) | Pre-remediation: data-catalog.yaml listed only `BEA_GDP`, `BEA_TiVA`, `BEA_EA` — none of which are the I-O tables this spec ingests. Spec-068's /speckit.analyze C1 finding flagged this as a CRITICAL III.4 P1 violation. Resolved by adding four new entries — `BEA_IO_NATIONAL_USE`, `BEA_IO_NATIONAL_SUPPLY`, `BEA_IO_TOTAL_REQ`, `BEA_NAICS_CONCORDANCE` — all classified Federal Economic / Runtime. data-catalog.yaml version bumped 2.6.2 → 2.6.3. |
| IV Michigan Test Case | **PASS** | SC-005 validates against all 83 Michigan counties; SC-006 against Shaikh's empirical bands. |

### P2 (Elaboration)

- I.3 TRPF: per-county c/v heterogeneity is the precondition for TRPF
  observability — without spec-068, every county shares the same r and
  TRPF becomes a single national series.
- III.3 Physics Cosplay: the Leontief column-sum invariance (FR-004) is
  the explicit transformation law that earns the matrix formalism.
- VIII.6 Constants Without Data Sources: the 0.5 hardcode being
  replaced is the canonical instance of this anti-pattern.

### Gate Result

**PASS** — no unjustified violations. Two soft gates require explicit
plan-level handling and have been incorporated above:

1. **II.11 declared interface**: `BEAShareLookupService` Python
   protocol is the contract; defined under `contracts/`. hex_hydrator
   depends on the protocol, not on the SQL tables.
2. **II.2 primitives-only**: shares are computed at read time, not
   stored as columns. Plan, data-model, and contracts all enforce this.

No entries needed in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/068-bea-national-io-ingest/
├── plan.md              # This file (/speckit.plan output)
├── spec.md              # /speckit.specify output (with Clarifications)
├── research.md          # Phase 0 output (this run)
├── data-model.md        # Phase 1 output (this run)
├── quickstart.md        # Phase 1 output (operator runbook)
├── contracts/
│   └── bea_share_lookup_service.md  # II.11 declared interface
├── checklists/
│   └── requirements.md  # /speckit.specify quality checklist
└── tasks.md             # NOT created by /speckit.plan — Phase 2 (/speckit.tasks)
```

### Source Code (repository root)

```text
src/babylon/reference/
└── bea/                              # NEW: BEA subsystem internal API
    ├── __init__.py                   # public exports
    ├── share_lookup_service.py       # BEAShareLookupService (II.11 contract)
    ├── ingest/
    │   ├── __init__.py
    │   ├── national_loader.py        # writes fact_bea_national_industry
    │   ├── io_coefficient_loader.py  # writes fact_bea_io_coefficient
    │   ├── concordance_loader.py     # writes bridge_naics_bea
    │   ├── vintage_resolver.py       # picks latest vintage per (industry, year)
    │   └── audit_report.py           # writes reports/ingest/bea_io_*.{md,json}
    └── tests/                        # contract test scaffolding

src/babylon/persistence/
└── hex_hydrator.py                   # MODIFIED: line ~107 — replace
                                     # _INTERMEDIATE_INPUTS_FRACTION = 0.5 with
                                     # BEAShareLookupService.lookup_county_share()

src/babylon/reference/
└── schema.py                         # MODIFIED: add vintage_published_date
                                     # to FactBEANationalIndustry + FactBEAIOCoefficient

tools/
└── load_bea_io.py                    # NEW: CLI entrypoint with --rollback,
                                     # --years, --dry-run

tests/
├── unit/reference/bea/               # NEW
│   ├── test_share_lookup_service.py
│   ├── test_vintage_resolver.py
│   ├── test_audit_report.py
│   ├── test_accounting_identity.py
│   └── test_column_sum_identity.py
└── integration/reference/bea/        # NEW
    ├── test_end_to_end_ingest.py     # full ingest into transient DB
    ├── test_idempotency.py           # epsilon-determinism across two runs
    ├── test_rollback.py              # --rollback restores empty state
    └── test_hex_hydrator_wired.py    # SC-005 county c/v stddev ≥ 0.2

reports/ingest/                       # MODIFIED: receives new bea_io_*.{md,json}

data/bea/                             # MODIFIED: complete existing stubs
├── io_loader.py                      # complete the Sheet-per-year parsing
├── loader_national.py                # complete the national-aggregate ingest
└── loader_concordance.py             # complete the bridge_naics_bea population

.specify/memory/data-catalog.yaml     # NO change (BEA already registered)
```

**Structure Decision**: Single-project (Option 1). The new BEA subsystem
package lives under `src/babylon/reference/bea/`. The constitutional
II.11 interface lives at `src/babylon/reference/bea/share_lookup_service.py`
and is the only entry point the persistence subsystem may import. The
ingest CLI is one new file at `tools/load_bea_io.py`. Existing legacy
loader stubs under `data/bea/` are completed in-place (they belong to the
legacy `babylon_data` namespace from spec-025; spec-068 reuses them rather
than duplicating).

## Complexity Tracking

> No constitutional violations require justification. This section is
> intentionally empty.
