# Implementation Plan: County-Exposure Loader (BEA I-O imports × QCEW shares)

**Branch**: `100-county-exposure` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/100-county-exposure/spec.md`
**Program**: 09 Full-Game Build, Lane D. Audit-advisory number: spec-100.

## Summary

Build the never-computed `county_exposure_by_external` weight map (named in
`src/babylon/engine/systems/phi_distribution.py`) as a reproducible reference-DB
loader in the **babylon-data** repo, plus a bloc-year bilateral-trade
aggregation. Two new SQLite reference tables, added additively to the canonical
ORM. Mirrors the spec-086 QCEW loader (staged rebuild → validate → atomic swap
with backup; JSON audit contract; `logical_table_hash` determinism). Zero
engine-dynamics change; the consumer wiring is spec-101 (engine lane).

**Technical approach** (all verified against the live reference DB 2026-07-03):
per bloc/year, `weight[C] = raw[C] / Σ raw`, where
`raw[C] = Σ_bea import_coeff[bea] · (county_emp[C,bea] / national_emp[bea])`.
`import_coeff` from `fact_bea_io_coefficient` (source = "Noncomparable imports",
USE table). `county_emp` via the `bridge_naics_bea` concordance (verified
antichain → no double-count) summing QCEW ownerships {1,2,3,5}. Proven on 2024:
weights sum to 1.000000000000 across 3212 counties; top counties (Santa Clara,
LA, Harris, Maricopa) are the import-intensive manufacturing/tech centers.

## Technical Context

**Language/Version**: Python 3.12 (babylon-data must avoid >3.12-only syntax).
**Primary Dependencies**: SQLAlchemy 2.x (canonical ORM `src/babylon/reference/schema.py`
+ sessions via `babylon.reference.database`), stdlib `sqlite3`, Pydantic 2.x
(audit-report models), `jsonschema` (audit contract validation), stdlib
`argparse`/`hashlib`/`subprocess`. **No new dependencies** (all present since
spec-086).
**Storage**: SQLite reference DB `data/sqlite/marxist-data-3NF.sqlite` (symlink to
the trove). Reads: `fact_bea_io_coefficient`, `fact_qcew_annual`,
`bridge_naics_bea`, `dim_bea_industry`, `dim_industry`, `dim_ownership`,
`dim_country`, `dim_county`, `dim_time`, `fact_trade_monthly`. Writes: two NEW
tables only. No existing table mutated.
**Testing**: pytest with in-memory ORM seeding + CSV/dict fixture builders
(spec-086 `tests/fixtures/qcew/` pattern). `@pytest.mark.red_phase` for RED
commits. Tests run in babylon-data via `PYTHONPATH=src`.
**Target Platform**: Local CLI loader (`python -m babylon_data.exposure`, invoked
by `mise run data:exposure`).
**Project Type**: Data loader (babylon-data repo) + additive schema (babylon repo).
**Performance Goals**: Full 2010–2024 build over ~3200 counties × 15 years
completes in minutes; a single streaming pass per year (no N+1 queries).
**Constraints**: Determinism (III.7 `logical_table_hash` reproduces run-to-run);
zero baseline churn; never run canonical sims.
**Scale/Scope**: `fact_county_exposure_by_external` ≈ 8 blocs × ~3200 counties ×
15 years ≈ 385k rows; `fact_bilateral_trade_annual` ≈ 8 blocs × 15 years ≈ 120
rows. Both trivial for SQLite.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Evidence |
|---|-----------|--------|----------|
| **III.8** | Aleksandrov / Structural Provenance (P0) | **PASS** | Every construct traces a material relation: `import_coeff[bea]` = value of imports consumed per unit of industry b's output (BEA USE "Noncomparable imports" row); `county_emp[C,b]/national_emp[b]` = county C's share of national employment in the import-competing industry b; their product = county C's exposure to import competition in b. The map = where imperial-rent Φ lands, weighted by import-competing production concentration. No ungrounded operator. |
| **III.1** | No Magic Constants (P1) | **PASS** | Coefficients come from `fact_bea_io_coefficient` and `fact_qcew_annual` (data, not literals). The two tunable scalars — reconciliation band (±2%, ratified spec-097) and weight-sum tolerance (1e-9, matching the consumer's own check in `phi_distribution`) — are named module constants with cited provenance. Ownership set {1,2,3,5} and USE table-type are data-derived selectors, documented in research.md. |
| **III.7** | Determinism Hash / Frozen Models (P0) | **PASS** | Deterministic insert order (sorted by PK); `logical_table_hash` (spec-086 pattern) over an ordered projection; audit-report Pydantic models are `frozen=True`. SC-003 gate asserts hash reproduces across two runs. |
| **III.4** | Data Catalog (P1) | **PASS** | Sources are catalogued reference tables; the two new tables get docstrings citing their upstreams; `.specify/memory/data-catalog.yaml` noted in research.md (no new external source ingested). |
| **III.2** | Falsifiability (P1) | **PASS** | Reconciliation gate (±2% Σraw vs Σcovered coeff) and per-(bloc,year) sum=1.0 are falsifiable and machine-checked; the audit records both. |
| **II.11** | Subsystem Ownership (P1) | **PASS** | Schema owned by babylon (`src/babylon/reference/schema.py`, additive); loader/audit owned by babylon-data (one-way import of babylon's ORM). No engine system (`src/babylon/engine/**`) or `web/**` touched. |
| **II.6** | State is Data (P1) | **PASS** | Loader is pure transformation reference-DB → reference-DB; no engine state, no graph, no simulation invoked. |
| **IV** | Michigan Test Case (P1) | **PASS** | An integration test (US4 gate) runs the loader against the real reference DB restricted to Michigan tri-county (Wayne 26163, Oakland 26125, Macomb 26099) and asserts weights sum to 1.0 and Wayne's manufacturing weight is nonzero — the canonical daily-gate geography. |

**No violations.** Complexity Tracking table omitted (nothing to justify).

**Data-grounding limitations disclosed (not violations)**: (a) the
`bridge_naics_bea` concordance is goods-biased (covers ~18/66 import-coefficient
industries) — reported as an audit coverage metric, NOT patched by inventing
mappings (III.8 forbids fabrication); (b) the county distribution is currently
bloc-invariant (no bloc×industry resolution in the DB) — disclosed via an audit
`bloc_invariant` flag. Both are honest reporting of the data's real resolution.

## Project Structure

### Documentation (this feature)

```text
specs/100-county-exposure/
├── plan.md              # This file
├── research.md          # Phase 0 — decisions + data-grounding citations
├── data-model.md        # Phase 1 — the two ORM tables + formula
├── quickstart.md        # Phase 1 — how to run + verify
├── contracts/
│   └── exposure_audit.schema.json   # audit-report JSON Schema (086 house pattern)
├── checklists/
│   └── requirements.md  # spec quality checklist (speckit specify)
└── tasks.md             # Phase 2 — /speckit.tasks output
```

### Source Code (two repos)

```text
# babylon repo (worktree d100) — SCHEMA (additive) + mise task + tests
src/babylon/reference/schema.py          # + FactCountyExposureByExternal
                                         # + FactBilateralTradeAnnual  (ADDITIVE)
.mise.toml                               # + [tasks."data:exposure"]
tests/unit/reference/test_exposure_schema.py   # ORM shape/roundtrip (worktree)

# babylon-data repo (branch 100-county-exposure) — LOADER (spec-086 layout)
src/babylon_data/exposure/
├── __init__.py          # empty-imports guard (qcew precedent)
├── compute.py           # the exposure formula (pure, testable)
├── writer.py            # staged build + atomic swap + logical_table_hash
├── validation.py        # sum-to-1.0 + reconciliation gate
├── audit.py             # Pydantic report models + JSON/MD emit
└── __main__.py          # CLI (dry-run/apply/rollback/drop-backup)
src/babylon_data/trade/
├── __init__.py          # NEUTRALIZED (stale babylon.data.* chain; nothing consumes)
└── bilateral.py         # bloc-year trade aggregation (NEW; current imports)
tests/unit/data/exposure/
├── conftest.py          # in-memory ORM engine + fixture seeders
├── test_compute.py      # formula: sum=1.0, antichain, split-weight, coverage
├── test_writer.py       # staged/swap/rollback + logical_table_hash determinism
├── test_validation.py   # reconciliation ±2%, sum-to-1 gate
├── test_audit.py        # schema-valid JSON emit
└── test_bilateral.py    # monthly→annual exact-sum aggregation
tests/integration/data/exposure/
└── test_exposure_real_db.py   # Michigan tri-county against the real DB (IV gate)
```

**Structure Decision**: Two-repo split per the Lane-D collision law (Program 09
§3): babylon owns the ORM schema (additive only); babylon-data owns the loader,
importing babylon's ORM one-way (spec-086 / spec-098 governance). The loader
package mirrors the proven QCEW module boundaries (compute / writer / validation /
audit / CLI).

## Phase 0 — Research (see research.md)

Resolved: import-coefficient source (BEA USE source=Noncomparable-imports);
concordance choice + antichain proof; ownership-slice selection ({1,2,3,5}, own
code 0 absent at detailed NAICS); split-NAICS weighting; year alignment
(2010–2024); reconciliation definition (Σraw vs Σcovered coeff, ±2%); bloc keying
(dim_country is_region) + bloc-invariance disclosure; trade units (USD, feeds
`bilateral_trade_value`); table naming (SQLite `fact_` convention).

## Phase 1 — Design & Contracts

- `data-model.md`: the two ORM tables (columns, PKs, FKs, indexes) + the compute
  formula with materialized types.
- `contracts/exposure_audit.schema.json`: the audit-report JSON Schema (draft
  2020-12), the spec-086 house pattern, validated on every write.
- `quickstart.md`: run/verify recipe + the reconciliation/coverage reading.
- Agent context: no new tech; skip heavy agent-file churn (documented here).

## Complexity Tracking

No Constitution violations — table intentionally empty.
