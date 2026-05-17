# Implementation Plan: QCEW Ownership and NAICS Hierarchy Normalization

**Branch**: `067-qcew-ownership-normalization` | **Date**: 2026-05-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/067-qcew-ownership-normalization/spec.md`

## Summary

`fact_qcew_annual` (8.79 GB SQLite reference table; the source of variable capital `v` and employment_proxy for every downstream simulation consumer) currently holds BOTH the BLS-published rollup rows AND the canonical decomposed rows on two axes (NAICS hierarchy + ownership). Spec-066's e2e audit caught the same double-counting bug three times in three different code paths and patched each one with a defensive `WHERE industry_id = 1 AND ownership_id = 1` filter that selects the BLS-published *rollup* row as a convenient pre-summed denominator. The trap is structural: every new consumer is one missed filter away from a 2×-to-5× wage-and-employment error.

This spec removes the trap at the data layer. The rollup rows (NAICS hierarchy levels 0-5 + the "Total covered" ownership) are **DELETE**'d from `fact_qcew_annual`. Downstream consumers stop selecting the rollup row and instead `SUM` the leaves — `naics_level = 6` × `own_code ∈ {'1', '2', '3', '5'}` — to compute the same total. The rate-of-profit acceptance band tightens from the spec-066 relaxed `[0.05, 0.80]` back to the spec-original `[0.05, 0.50]`. The michigan-e2e baseline regenerates and CI's `qa:e2e-regression` gate continues to pass.

The fix is a one-shot data-layer migration (two DELETE statements), three query rewrites in `hex_hydrator.py` and `county_aggregation.py`, and one test-band tightening. No new code paths, no new dependencies, no schema changes.

## Technical Context

**Language/Version**: Python 3.12+ (per project standard)
**Primary Dependencies**: SQLAlchemy 2.x (`DeclarativeBase` + `Mapped[]` ORM in `src/babylon/reference/schema.py`), `sqlite3` (stdlib, atomic transaction wrapper), Pydantic 2.x (audit-report schema), no new deps
**Storage**: SQLite reference DB at `data/sqlite/marxist-data-3NF.sqlite`; affected tables: `fact_qcew_annual` (DELETE), `dim_industry` (read), `dim_ownership` (read), `dim_time` (read for vintage classification in audit report)
**Testing**: pytest (markers: `@pytest.mark.integration`, `@pytest.mark.slow` for the slow-gate 520-tick verification); doctest for the rollup-predicate helper
**Target Platform**: Linux/macOS dev workstations + CI runners; SQLite is single-file so no infra
**Project Type**: data-layer migration + library refactor (no new long-lived process; one-shot script + 3-file edit)
**Performance Goals**: normalization migration completes in ≤ 5 min wallclock against the current 8.79 GB SQLite (two DELETE queries against indexed FK columns; rollups are ~30 % of rows so net I/O ~3 GB)
**Constraints**: idempotent (re-running produces byte-identical post-state — FR-010 / SC-005); atomic (backup → DELETE → commit, or full rollback on failure); audit report MUST emit before commit; spec-066 `qa:e2e-regression` baseline must pass against the regenerated michigan-e2e.json
**Scale/Scope**: Pre-normalization row count to be captured during T001 pre-flight inspection (rough order-of-magnitude expectation: single-digit millions for the persisted county-level subset; the BLS source CSVs hold ~3.6 M rows per year combining all aggregation levels but only the county-level subset is persisted in `fact_qcew_annual`). Post-normalization will be ~30 % smaller after rollup removal. Per-county audit-delta is computed across 83 Michigan counties × 15 years = 1245 (county, year) pairs.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against Babylon Constitution v2.6.1. Tiered evaluation per III.9 AI Context Budget — P0 mandatory, P1 domain-relevant, P2 awareness-level.

### P0 (Never Drop)

| Principle | Status | Notes |
|---|---|---|
| I.19 Dialectic Primitive | N/A | This is reference data, not a dialectic. |
| I.20 Spatial Substrate as Immutable Ground Truth | **PASS** | `fact_qcew_annual` is reference data feeding the substrate (per III.4 catalog). The DELETE operation removes BLS-published rollup rows, not substrate data. Per-county FIPS geography is untouched. |
| II.9 Morphism Dyadic | N/A | No morphism layer involvement. |
| III.7 Determinism Hash and Replayability | **PASS** | FR-010 (idempotency) + SC-005 (byte-identical re-run) directly encode this principle. The DELETE predicate is purely structural (`naics_level != 6` OR `own_code = '0'`) — no stochasticity, no time-dependent inputs. |
| III.8 Aleksandrov Test (Structural Provenance) | **PASS** | Material relation for the DELETE: BLS publishes rollups as a convenience for human readers (Total = SUM of leaves). They are not independent observations — they are pre-computed sums. Storing them alongside the leaves creates a many-to-one redundancy where any query that mixes both will double-count. The DELETE traces to BLS's QCEW publication methodology, not to an arbitrary choice. |
| V Verb Atomicity | N/A | No player-verb impact. |

### P1 (Load-Bearing — domain-relevant for ingest)

| Principle | Status | Notes |
|---|---|---|
| II.11 Subsystem Table Ownership | **PASS** | `fact_qcew_annual` is owned by the reference-data subsystem (`src/babylon/reference/`). Downstream consumers (`hex_hydrator.py`, `county_aggregation.py`) currently access it directly via raw SQL. This is allowed because the ORM schema (`schema.py`) IS the declared interface — versioned, typed, and explicit. The DELETE migration is exercised THROUGH the schema (SQLAlchemy session), not as an opaque SQLite-CLI script, so the ownership boundary is respected. |
| III.1 No Magic Constants | **PASS** | The predicate values (`naics_level = 6`, `own_code = '0'`) are BLS-published category codes that trace to the QCEW publication specification. They are NOT tuning parameters. The audit report records the exact predicate used per ingest so the chain of derivation is auditable. |
| III.2 Falsifiability Required | **PASS** | Spec SC-001 / SC-007 define the falsifying condition: `SUM(employment)` for any (county × year) disagreeing with the BLS-published total by > 5 %. The test is BLS-publication-grounded, hash-reproducible, and rejects the implementation cleanly on failure. |
| III.4 Data Source Traceability | **PASS** | QCEW is already in the `data-catalog.yaml` Federal Economic category as Runtime data. This spec does not add a new source; it modifies the persistence shape of an existing source. Provenance is preserved (audit report records source CSV paths, NAICS vintage per year, and pre/post row counts). |
| IV Michigan Test Case | **PASS** | SC-007 specifically validates against the 2010-2024 Michigan scope (1245 county-year pairs); the canonical 520-tick Michigan-Canada slow-gate run is the load-bearing acceptance test. |

### P2 (Elaboration — awareness only)

- I.7 Quantitative→Qualitative — relevant: employment / wages are quantities (PASS implicitly; this spec doesn't introduce continuous quality gradients).
- II.4 Quantities vs Coefficients — relevant: the predicate values are categorical codes, not coefficients (PASS).
- VI.1 Material Base First — relevant: reference-data correctness is foundational (PASS).
- VIII.6 Constants Without Data Sources — relevant: see III.1 above (PASS).

### Result

**No constitutional violations. Phase 0 research approved.**

## Project Structure

### Documentation (this feature)

```text
specs/067-qcew-ownership-normalization/
├── plan.md                      # This file
├── spec.md                      # Feature specification (clarified 2026-05-16)
├── research.md                  # Phase 0 — 6 key decisions w/ rationale
├── data-model.md                # Phase 1 — post-067 table shape + audit-report entity
├── contracts/
│   ├── audit_report.schema.json # JSON Schema for normalization audit report
│   ├── post_067_query_contract.md  # Documents the SELECT-leaves-not-rollup contract for downstream
│   └── normalization_migration.sql # The canonical DELETE statements (executable as standalone migration)
├── quickstart.md                # Phase 1 — operator commands + verification recipe
├── checklists/
│   └── requirements.md          # Spec quality checklist (pass, post-clarification)
└── tasks.md                     # Phase 2 output of /speckit.tasks (NOT created here)
```

### Source Code (repository root)

This is a data-layer + library-refactor feature against the existing Babylon monolith. No new top-level packages; modifies four existing files and adds two new ones.

```text
src/babylon/
├── reference/
│   ├── schema.py                # READ-ONLY: existing FactQcewAnnual, DimIndustry, DimOwnership models
│   └── database.py              # READ-ONLY: session factory used by the migration
├── persistence/
│   ├── hex_hydrator.py          # MODIFY: ~30 LOC change — rewrite c/v queries from SELECT(rollup) to SUM(leaves); remove `WHERE industry_id = 1 AND ownership_id = 1` filter pair (lines 463-480 region)
│   └── county_aggregation.py    # MODIFY: ~30 LOC change — rewrite fetch_employment_proxy_for_county_at_tick from SELECT(rollup) to SUM(leaves); remove same filter pair (lines 348-397 region)
└── (no new modules required in src/babylon)

tools/
├── normalize_qcew_rollups.py   # NEW: one-shot migration script (~150 LOC); backup → DELETE rollups → audit report → commit
└── ingest_qcew_full.py          # READ-ONLY: existing stub; loader rewrite is out of scope (deferred to spec-086)

tests/
├── integration/
│   ├── test_normalize_qcew_rollups.py    # NEW: idempotency, atomicity, audit-report integrity, schema unchanged
│   ├── test_post_067_consumer_queries.py # NEW: hex_hydrator + county_aggregation produce BLS-agreement totals via SUM(leaves)
│   └── test_audit_report_validation.py   # NEW: enforces contracts/audit_report.schema.json (US4 contract harness)
├── <slow_or_integration>/
│   └── test_state_rate_of_profit_in_relaxed_band.py  # MODIFY (name + location preserved from spec-066 for git continuity): tighten band [0.05, 0.80] → [0.05, 0.50]; only the band parameter and docstring change
└── baselines/
    └── michigan-e2e.json        # REGENERATE post-067 (~50KB→~1.2MB; the spec-066 commit 3423dd20 already shipped the 520-tick shape; this is a value refresh)

reports/
└── ingest/
    └── qcew_normalization_YYYYMMDD.md  # NEW: emitted by the migration script on each run (audit trail per FR-007)
```

**Structure Decision**: Existing monolith layout — `src/babylon/persistence/` owns the downstream query layer, `src/babylon/reference/` owns the schema, `tools/` owns one-shot operator scripts. No new package boundaries needed. The migration is one new tool + two file edits + one test-band tightening + one baseline regeneration. Per Constitution II.11 the subsystem-ownership boundary is respected: the migration writes only to reference-data tables it owns; downstream consumers continue reading via the same SQLAlchemy session pattern they already use.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitutional violations. No complexity justifications required.

## Post-Phase-1 Re-Check

*Performed after Phase 1 artifacts generated. See research.md, data-model.md, contracts/, quickstart.md.*

**Re-check result**: All P0 / P1 / P2 principles remain PASS. Phase 1 artifacts add no new dependencies, no new tables, no new long-lived processes. The migration script (`tools/normalize_qcew_rollups.py`) uses the existing reference-data SQLAlchemy session pattern; the audit-report JSON schema introduces no new persistence; the contracts/ folder documents existing-source invariants rather than introducing new boundaries.

Ready to proceed to `/speckit.tasks`.
