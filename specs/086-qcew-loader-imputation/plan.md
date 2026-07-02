# Implementation Plan: QCEW Loader Reimplementation with Synthetic Suppression Imputation

**Branch**: `086-qcew-loader-imputation` | **Date**: 2026-07-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/086-qcew-loader-imputation/spec.md` (amended 2026-07-02 with owner decisions)

## Summary

Reimplement the QCEW loader (deleted in spec-037) as new code in the version-controlled babylon-data package, and reconstruct the 67–72 % of 6-digit county cells BLS suppresses so that county employment/wage totals reconcile to BLS-published figures within ±2 % (vs today's silent 10–30 % undercount that biases `v`, exploitation rate, and imperial rent for most counties). Technical approach per research.md: stream each year's staged BLS annual singlefile; keep county leaves (agglvl 78) plus published constraints (agglvl 70/71/74–77); impute suppressed cells top-down through the ownership × NAICS constraint tree, apportioned by establishment counts with largest-remainder integer exactness; write into a staged table rebuilt from the canonical ORM (restoring the lost composite PK) with a row-level `is_imputed` provenance flag; persist published county/ownership constraints in a new `fact_qcew_county_rollup` table; atomic swap + backup per the spec-067 fast-strategy pattern; per-year checkpoints for resume; jsonschema-validated audit report per load. Fully offline, deterministic, idempotent.

## Technical Context

**Language/Version**: Python 3.12 (babylon venv; babylon-data code must avoid >3.12-only syntax it doesn't already use)
**Primary Dependencies**: SQLAlchemy 2.x (canonical ORM `src/babylon/reference/schema.py` + sessions via `babylon.reference.database`), pandas (chunked singlefile streaming, existing pattern), Pydantic 2.x (audit-report models), jsonschema (audit contract validation), stdlib sqlite3/argparse
**Storage**: SQLite reference DB `/media/user/data/babylon-data/sqlite/marxist-data-3NF.sqlite` (canonical, reached via the repo's `data/sqlite` directory symlink — exactly one DB file); source: staged BLS annual singlefile CSVs 2010–2024 at `/media/user/data/babylon-data/qcew/` (8.3 GB, complete)
**Testing**: pytest in babylon's `tests/` (unit fixtures: mini singlefile CSVs + in-memory ORM DBs; integration: tiny end-to-end build + contract validation; live-DB checks skip-gated), `pytest.importorskip("babylon_data...")` for CI where the symlink dangles
**Target Platform**: Linux workstation (operator-run data build; not a runtime service)
**Project Type**: Two-repo change — new loader package code in `/home/user/projects/game/babylon-data` (git) + schema/task/test/docs changes in babylon
**Performance Goals**: Full 15-year load ≤ 90 min wallclock (old suppression-blind load: 46 min; imputation adds ~3,270 × 15 in-memory county-year trees — CPU-trivial vs I/O); per-year resume so interruptions never restart
**Constraints**: No network (FR-011); deterministic byte-identical logical table content across runs (FR-008/SC-008, ordered-SELECT SHA-256); canonical table keeps serving consumers until the staged build validates and swaps; zero consumer code changes (FR-010) beyond dropping the stale `_cache_national_wages_bea` cache
**Scale/Scope**: 15 files × ~3.6 M rows scanned (~54 M); ~15.1 M leaf rows + ~245 K constraint rows written; ~49 K county-year reconciliations; 9 SCs incl. Wayne County MI 2010 → 657,150 ± 2 %

## Constitution Check

*Constitution v2.6.1. Gates evaluated pre-Phase-0 and re-checked post-design (below reflects the post-design state).*

| Gate | Principle(s) | Verdict | Evidence |
|---|---|---|---|
| No magic constants | III.1 | PASS | ±2 %/±1 % tolerances ratified in spec-097 (FINAL) and cited from spec SCs; apportionment weights are BLS-published establishment counts; no invented coefficients. Largest-remainder rounding is a method, not a constant. |
| Falsifiability | III.2 | PASS | Every SC is a computable predicate over the built table (reconciliation within band; Wayne 2010 within ±2 % of 657,150; national identity per research D8). Audit report materializes the residual distribution per load. |
| Structural provenance (Aleksandrov) | III.8 | PASS | Establishments-weighted apportionment: an establishment is a physical workplace — the only cell-size signal BLS publishes under suppression. The constraint tree mirrors BLS's own publication hierarchy (materially: state UI accounting rollups). No ungrounded formalism; no tensor claims. |
| Data source traceability | III.4 / III.4.2 | PASS | QCEW is already a catalogued Federal Economic source; no new source added. The staged 2010–2024 singlefiles are pinned local snapshots consumed by an offline build (reproducible-fixture semantics); the built reference DB remains the runtime artifact. Establishment counts come from the same files. |
| Determinism | III.7 | PASS | Pure integer arithmetic, fixed sibling ordering, no RNG, no wall-clock inputs in data; SC-008 operationalized as ordered-SELECT SHA-256 (contracts/determinism_contract.md). |
| Subsystem table ownership | II.11 | PASS (documented coupling) | `fact_qcew_annual`, new `fact_qcew_county_rollup`, `ingest_checkpoint` are reference-subsystem tables; the loader is that subsystem's build tool. Cross-repo direction is one-way: babylon_data (loader) → babylon (ORM/session); babylon never imports babylon_data at runtime. Documented in research D3; schema ownership across repos deferred to spec-098. |
| No DB I/O during tick | II.6 | PASS | Offline operator tool; never runs inside the engine. Consumers keep reading via existing paths (spec-069 cache unaffected — it reads at hydrate time). |
| Spatial substrate immutability | I.20 | PASS | No county lines redrawn, no dims fabricated (unknown non-pseudo fips = hard error; the old loader's placeholder-county creation is explicitly banned). Identity resolution (46113→46102, CT-2024 as-published) maps source rows onto the existing dim_county substrate and is audit-logged. |
| Michigan test case | IV / IV.2 | PASS | SC-003 is Wayne County 2010; delivery includes michigan-e2e baseline regeneration + structural rate-of-profit invariants re-run (research D12). |
| Scope control | VI.3 | PASS | Traces directly to Michigan/Detroit prediction fidelity: county `v` and employment feed every economic quantity. Out-of-scope items (other loaders, orchestrator, dead throughput/melt adapters, CT crosswalk) explicitly deferred (spec Out of Scope + research Open items). |
| Transition-state protocol | IX.3.4 | PASS | No dependence on I.17/I.18/II.3/II.7 transition-state principles (no hyperedges, no OODA, no morphism-layer work). |

**Pre-Phase-0 evaluation**: no violations; no Complexity Tracking entries required beyond the two-repo shape (justified below).
**Post-design re-check (after Phase 1 artifacts)**: unchanged — PASS on all gates.

## Project Structure

### Documentation (this feature)

```text
specs/086-qcew-loader-imputation/
├── spec.md              # Feature spec (amended 2026-07-02)
├── plan.md              # This file
├── research.md          # Phase 0 — findings R1, decisions D1–D12
├── data-model.md        # Phase 1 — entities, DDL deltas, provenance semantics
├── quickstart.md        # Phase 1 — operator guide (dry-run → apply → validate → rollback)
├── contracts/
│   ├── audit_report.schema.json    # per-load audit artifact contract (extends 067 pattern)
│   ├── cli_contract.md             # python -m babylon_data.qcew + mise data:qcew surface
│   └── determinism_contract.md     # SC-008 logical-hash definition + commands
├── checklists/requirements.md      # (existing)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Repo A: /home/user/projects/game/babylon-data  (loader home — owner decision 2026-07-02)
pyproject.toml                        # NEW — minimal PEP 621 (name, requires-python >=3.12, sqlalchemy+pandas)
src/babylon_data/                     # RENAMED from src/babylon-data (git mv; makes package importable)
├── __init__.py                       # REPLACED — docstring-only; no eager legacy import chain
└── qcew/
    ├── __init__.py                   # TRIMMED — stops importing legacy qcew/schema.py (kills census closure)
    ├── __main__.py                   # NEW — argparse CLI (dry-run/apply/rollback/drop-backup, --years, --restart)
    ├── singlefile.py                 # NEW — chunked 38-col reader, row classifier (agglvl/pseudo-fips), identity resolution (D7)
    ├── hierarchy.py                  # NEW — per-county-year constraint tree (70→71→74..78) from published rows
    ├── imputation.py                 # NEW — top-down estabs-weighted apportionment, largest-remainder (D6); pure, no I/O
    ├── writer.py                     # NEW — staged __new build, per-year txn+checkpoint, atomic swap, cache drop (D9)
    ├── validation.py                 # NEW — reconciliation checks, SC gates, Wayne spot-check
    ├── audit.py                      # NEW — Pydantic report models + write_to_disk (reports/ingest/, jsonschema-validated)
    └── (loader_3nf.py, parser.py, …) # UNTOUCHED — provenance/reference only; not imported by new code

# Repo B: /home/user/projects/game/babylon
src/babylon_data                      # SYMLINK REPOINTED → /home/user/projects/game/babylon-data/src/babylon_data
src/babylon/reference/schema.py       # +FactQcewAnnual.is_imputed; +FactQcewCountyRollup (D4, D5)
.mise.toml                            # +[tasks."data:qcew"] (data:bea-load pattern)
tools/ingest_qcew_full.py             # tombstone message → real command
tests/unit/reference/qcew/            # NEW — imputation math, classifier, identity, rounding (fixture CSVs; importorskip)
tests/integration/
├── test_qcew_impute_e2e.py           # NEW — tiny end-to-end build → SCs on fixture; audit JSON vs contract schema
└── test_qcew_live_reconciliation.py  # NEW — live-DB gated: Wayne 2010 ≈ 657,150 ± 2 % via consumer paths (SC-003)
tests/baselines/michigan-e2e.json     # REGENERATED post-reload (D12)
```

**Structure Decision**: Two-repo change per owner decision 2026-07-02 (loader home = babylon-data, minimal viable packaging). All *new* loader code is additive modules beside the untouched legacy files; babylon-side changes are the ORM delta, the symlink repoint, the mise task, and tests. The trove (`/media/user/data/babylon-data`) remains the data home (raw CSVs + the one canonical SQLite DB) and stops being an import target.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Loader code outside the main repo (second repo in the change) | Owner decision 2026-07-02: babylon-data is the loaders' permanent home; 086 establishes the pattern spec-098 generalizes | In-repo `src/babylon/reference/qcew/` (single-repo, CI-covered) was the spec's original wording — rejected by owner; would force a second migration in 098 |
| New `fact_qcew_county_rollup` table (schema surface grows) | SC validation + qa:data gate need published BLS targets queryable without re-reading 8.3 GB of CSVs; spec's "Published Aggregate (Constraint)" entity | Audit-JSON-only persistence — rejected: 49 K county-year residuals bloat every report and the targets are unqueryable afterward (research D5) |
