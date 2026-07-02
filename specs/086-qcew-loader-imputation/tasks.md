# Tasks: QCEW Loader Reimplementation with Synthetic Suppression Imputation

**Input**: Design documents from `/specs/086-qcew-loader-imputation/`
**Prerequisites**: plan.md, spec.md, research.md (D1–D12), data-model.md, contracts/, quickstart.md — all committed (`0313a1b1`)

**Tests**: INCLUDED — TDD is mandatory per house rules (Red-Green-Refactor, `@pytest.mark.red_phase` until green).

**Two-repo convention**: `REPO-A` = `/home/user/projects/game/babylon-data` (loader home; has its own git — commit there with conventional messages). `REPO-B` = `/home/user/projects/game/babylon` (schema, symlink, mise task, tests, docs). All `babylon_data.qcew` test modules guard with `pytest.importorskip("babylon_data.qcew", reason="babylon-data symlink not resolved (CI)")` so CI skips exactly like existing data-dependent tests.

**Organization**: Grouped by user story (spec.md): US1 (P1) accurate county totals, US2 (P2) rebuildable/idempotent/resumable, US3 (P3) auditable provenance.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (babylon-data minimal packaging + import wiring — research D2)

**Purpose**: Make the loader package importable and version-controlled before any feature code.

- [x] T001 In REPO-A: `git mv src/babylon-data src/babylon_data` and commit (`refactor: rename package dir to importable babylon_data`)
- [x] T002 In REPO-A: add minimal `pyproject.toml` at repo root (PEP 621: name `babylon-data`, `requires-python = ">=3.12"`, dependencies `sqlalchemy>=2`, `pandas>=2`; no build/publish extras) and commit
- [x] T003 In REPO-A: replace `src/babylon_data/__init__.py` with docstring-only module (no eager `loader_base` import chain) and trim `src/babylon_data/qcew/__init__.py` to stop importing legacy `qcew/schema.py` (kills the broken census import closure — research R1); commit
- [x] T004 In REPO-B: repoint symlink `src/babylon_data` → `/home/user/projects/game/babylon-data/src/babylon_data` (`ln -sfn`); verify `poetry run python -c "import babylon_data, babylon_data.qcew"` succeeds; commit the symlink change
- [x] T005 In REPO-B: verify `poetry run pytest tests/integration/economics/test_tensor_hierarchy.py --collect-only -q` and a run of its babylon_data-dependent tests SKIP (not error) now that trove `bea/` modules left the import path; if they error, add `pytest.importorskip` guards in that file (research D2 consequence)

**Checkpoint**: `import babylon_data.qcew` works in REPO-B's venv; loader home is version-controlled.

---

## Phase 2: Foundational (canonical schema delta — blocks all stories)

**Purpose**: The ORM columns/tables every story writes to (data-model.md §1–§2).

- [x] T006 [P] In REPO-B: RED — write `tests/unit/reference/qcew/{__init__.py,conftest.py,test_schema_086.py}`: in-memory `create_all` from ORM subset asserts `FactQcewAnnual.is_imputed` exists (BOOLEAN NOT NULL, server default 0) and `FactQcewCountyRollup` exists with PK `(county_id, time_id, ownership_id)` and columns per data-model.md §2; mark `@pytest.mark.red_phase`
- [x] T007 In REPO-B: GREEN — implement in `src/babylon/reference/schema.py`: add `is_imputed` to `FactQcewAnnual` (Boolean, nullable=False, server_default="0") and new `FactQcewCountyRollup` class (`fact_qcew_county_rollup`); remove red_phase marker from T006 tests; `mise run typecheck` clean
- [x] T008 [P] In REPO-B: shared fixtures in `tests/unit/reference/qcew/conftest.py` + `tests/fixtures/qcew/`: (a) `mini_singlefile(rows) -> Path` builder emitting the exact 38-column header (research R1) with helper row-constructors for agglvl 70/71/74–78 and `disclosure_code='N'` cells; (b) `qcew_orm_db` in-memory engine seeded with dim_county (incl. 26163, 46102, 46113, a `SS999`, one CT planning region), dim_ownership (own 0,1,2,3,5), dim_industry (small NAICS chain incl. a range-sector like 31-33), dim_time (2010, 2015, 2024)

**Checkpoint**: Schema delta merged; fixtures available — user stories can begin.

---

## Phase 3: User Story 1 — Simulation consumes accurate county labor totals (Priority: P1) 🎯

**Goal**: Parse → classify → build constraint tree → impute suppressed cells → write leaves + constraints so summed detail reconciles to BLS-published county totals (±2 %; exact when agglvl-70 is published).

**Independent Test** (spec US1): build a fixture county-year with suppressed cells, run the pipeline, confirm `SUM(leaves)` reconciles to the agglvl-70 constraint; Wayne-shaped fixture reproduces the −14.6 %→0 correction.

### Tests for User Story 1 (RED first — must fail before implementation)

- [x] T009 [P] [US1] RED — row classification tests in REPO-B `tests/unit/reference/qcew/test_singlefile_classify.py`: LEAF (78, own 1/2/3/5) / CONSTRAINT_70 / CONSTRAINT_71 / CONSTRAINT_NAICS (74–77) routing; exclusions with per-class counts (`US000/USCMS/USMSA/USNMS`, `C####` MSA, `SS000`, `SS999`, fips-not-in-dim_county e.g. 78010); identity mapping 46113→46102 all years + 2015 both-published dedupe (keep 46102, count drops); unknown non-pseudo fips → hard error listing codes; 38-column header mismatch → hard error
- [x] T010 [P] [US1] RED — hierarchy tests in `tests/unit/reference/qcew/test_hierarchy.py`: CountyYearTree from published rows only (70→71→NAICS prefix chain 2→3→4→5→6 incl. range sectors "31-33"); suppressed intermediate nodes marked undisclosed but structurally present; missing agglvl-70 flags the tree low-confidence with fallback constraint per D6
- [x] T011 [P] [US1] RED — imputation tests in `tests/unit/reference/qcew/test_imputation.py`: single suppressed sibling = exact recovery `P − Σdisclosed` (method `exact_recovery`); multi-sibling estabs-proportional apportionment; zero-estabs group → `equal_split`; `R < 0` → suppressed siblings 0 + `zero_negative_remainder` anomaly; suppressed 71 apportioned from 70 then constrains its subtree; suppressed 70 → fallback chain (Σdisclosed 71 → Σdisclosed leaves) + low-confidence; largest-remainder: children sum EXACTLY to remainder in every group (property-style over several group shapes); observed values never mutated; wages and employment reconciled independently
- [x] T012 [P] [US1] RED — algorithm determinism tests in `tests/unit/reference/qcew/test_imputation_determinism.py`: permuted input row order ⇒ identical outputs; repeated runs ⇒ identical outputs; tie-break rule (equal remainders → lower industry_code first) pinned
- [x] T013 [P] [US1] RED — fixture e2e in REPO-B `tests/integration/test_qcew_impute_e2e.py`: 2 counties × 1 year mini singlefile → pipeline → tmp ORM SQLite: leaves sum exactly to 70 (both metrics); `is_imputed` set on suppressed cells only; imputed rows have `disclosure_code='N'`, NULL avg/lq; `fact_qcew_county_rollup` holds 70+71 rows; true-zero disclosed cells stay 0 with `is_imputed=0`

### Implementation for User Story 1 (in REPO-A `src/babylon_data/qcew/`, commit per module)

- [x] T014 [US1] `singlefile.py`: chunked pandas reader (100k rows) with exact-header validation, `RowClassification` classifier, identity resolution (46113→46102 + 2015 dedupe, CT-2024 pass-through), per-class exclusion counters; pure row-level logic independent of chunk boundaries → GREEN T009
- [x] T015 [US1] `hierarchy.py`: `CountyYearTree` assembly from classified rows (data-model.md §4) → GREEN T010
- [x] T016 [US1] `imputation.py`: pure top-down apportionment (D6) — int arithmetic, fixed sibling order `(own_code, industry_code)`, largest-remainder with pinned tie-break, `ImputationResult` with method labels + anomalies; no I/O → GREEN T011 + T012
- [x] T017 [US1] `writer.py` (minimal): leaf-row assembly (is_imputed / NULL-avg-lq rules), rollup-row assembly, staging DDL created from `babylon.reference.schema` metadata (restores composite PK), deterministic insert order `(county_id, ownership_id, industry_id)`, `write_year(session, year_result)` → with T018, GREEN T013
- [x] T018 [US1] `validation.py`: per-county-year reconciliation calculator (residual %, band check ±2 %, exactness assertion when 70 published), year-level rollups of results → GREEN T013 fully
- [x] T019 [US1] Checkpoint: full US1 test set green without red_phase markers; `mise run check` clean in REPO-B; commit both repos

**Checkpoint**: Imputation core proven at fixture scale — US1 independently demonstrable.

---

## Phase 4: User Story 2 — Reference database is rebuildable from staged source (Priority: P2)

**Goal**: One documented offline operation rebuilds 2010–2024: per-year transactions + checkpoints (resume), staged build + atomic swap with backup, idempotent + deterministic, CLI + mise task.

**Independent Test** (spec US2): from empty staging, run the loader over fixture files for ≥2 "years"; interrupt after year 1 → re-run resumes; re-run after completion → identical logical hashes; swap/rollback verified.

### Tests for User Story 2 (RED first)

- [x] T020 [P] [US2] RED — checkpoint tests in REPO-B `tests/unit/reference/qcew/test_checkpoints.py`: v086 rows written as `(source='qcew', year=<real>, state_fips='US', table_id='annual_v086', race_code='T', row_count)`; resume skips checkpointed-AND-populated years; `--restart` drops staging + v086 checkpoints only; swap-time purge deletes ONLY legacy `(source='qcew', table_id='file')` rows
- [x] T021 [P] [US2] RED — resume/idempotency e2e in REPO-B `tests/integration/test_qcew_resume_idempotency.py`: simulated interrupt after year 1 of 2 → staging + checkpoint persist → re-run completes only year 2; second full run reproduces both logical table hashes (ordered-SELECT sha256 per contracts/determinism_contract.md); composite PK rejects duplicate insertion
- [x] T022 [P] [US2] RED — swap lifecycle e2e in REPO-B `tests/integration/test_qcew_swap.py`: swap renames canonical→`__pre_086`, staging→canonical, recreates the 3 indexes (PRAGMA index_list), drops `_cache_national_wages_bea` if present; `--rollback-from-backup` restores; `--drop-backup` removes; swap is REFUSED when validation gates fail (canonical untouched, exit 1)
- [x] T023 [P] [US2] RED — CLI contract tests in REPO-B `tests/unit/reference/qcew/test_cli.py` per contracts/cli_contract.md: modes mutually exclusive + exactly one required; `--years` parses `2010-2024` and `2010,2012`; missing singlefile → exit 2 pre-flight; header mismatch → exit 2; validation failure → exit 1; defaults (source-dir, report-dir) wired

### Implementation for User Story 2

- [x] T024 [US2] `writer.py` (full): staging-build orchestration (per-year txn: DELETE-year → insert → checkpoint upsert → COMMIT), atomic swap + backup + index recreation, cache-table drop, legacy checkpoint purge, rollback/drop-backup operations, logical-hash computation for both tables → GREEN T020–T022
- [x] T025 [US2] `__main__.py`: argparse CLI (modes, `--years`, `--source-dir`, `--db`, `--restart`, `--report-dir`, `--quiet`), pre-flight assertions (per-year file presence + header check, dims populated, ORM `is_imputed` present, own_codes resolvable), exit-code mapping (0/1/2/130), flush-printed progress → GREEN T023
- [x] T026 [P] [US2] In REPO-B `.mise.toml`: add `[tasks."data:qcew"]` (usage-crate pattern from `data:bea-load`; args `[years]` default `2010-2024`, flags `--dry-run/--apply/--restart/--rollback-from-backup/--drop-backup`); update `tools/ingest_qcew_full.py` tombstone to name `mise run data:qcew` / `python -m babylon_data.qcew`
- [x] T027 [US2] Checkpoint: US1+US2 suites green; `mise run check` clean; commit both repos

**Checkpoint**: Full rebuild operation exists end-to-end at fixture scale — US2 independently demonstrable.

---

## Phase 5: User Story 3 — Reconstructed values are distinguishable and auditable (Priority: P3)

**Goal**: Every magnitude carries observed/imputed provenance; each load emits a jsonschema-validated audit report (JSON+md) quantifying suppression, reconstruction methods, residual distributions, identity resolutions, and SC gates.

**Independent Test** (spec US3): query the fixture-built table → every row's provenance is determinate; open the emitted report → per-year suppression rate, reconstructed share, residual distribution present and schema-valid.

### Tests for User Story 3 (RED first)

- [x] T028 [P] [US3] RED — audit contract test in REPO-B `tests/contract/qcew/test_audit_report_contract.py`: fixture e2e emission validates against `specs/086-qcew-loader-imputation/contracts/audit_report.schema.json` (jsonschema, Draft 2020-12); md sidecar written next to JSON; report filenames `qcew_impute_<UTC>.{json,md}`
- [x] T029 [P] [US3] RED — audit model tests in REPO-B `tests/unit/reference/qcew/test_audit_models.py`: Pydantic round-trip (to_json/from_json); suppression method counts sum to suppressed_cells; per-class excluded counts; identity_resolutions counters; national_check math per D8 (`sum_counties + excluded_pseudo_mass` vs US000, ±1 % gate); sc_gates booleans populated (null when not computable for subset years)
- [x] T030 [P] [US3] RED — provenance queryability e2e in REPO-B `tests/integration/test_qcew_provenance.py` (extends fixture e2e): 100 % of rows have `is_imputed ∈ {0,1}` (SC-006); `is_imputed=1 ⇒ disclosure_code='N' AND avg/lq NULL`; suppressed-70 fixture county-year appears in `low_confidence_county_years` with reason `county_total_suppressed`; rollup rows built by fallback carry `is_imputed=1`

### Implementation for User Story 3

- [x] T031 [US3] `audit.py`: Pydantic report models mirroring the contract schema, per-stage collectors, `write_to_disk(report_dir)` with pre-write jsonschema validation, run metadata (mode/years/db sha256 pre-post/duration/git branch+sha of BOTH repos/source-file sha256/table hashes) → GREEN T028 + T029
- [x] T032 [US3] Wire collectors through `singlefile.py` (exclusion + identity counters), `imputation.py` (method + anomaly counts), `validation.py` (reconciliation distributions + low-confidence), `writer.py` (row counts + hashes), `__main__.py` (US000 national-check rows routed to audit, never to county tables; sc_gates assembly; report emission in every mode) → GREEN T030 and re-green e2e suites
- [x] T033 [US3] Checkpoint: all three story suites green; `mise run check` clean; commit both repos

**Checkpoint**: All user stories independently functional at fixture scale.

---

## Phase 6: Live delivery, verification & cross-cutting polish

**Purpose**: Run against the real staged source + canonical DB, prove the SCs, re-baseline downstream, close the docs loop.

- [x] T034 Operator: single-year live dry-run `mise run data:qcew -- --dry-run --years 2010`; review audit vs research expectations (≈72 % cell suppression 2010; Wayne 2010 gate true; exclusions ≈914 VI rows + ~25.6 K SS999 rows)
- [x] T035 Operator: full live dry-run then `--apply --years 2010-2024` (≤90 min budget; resume on interrupt); confirm swap + `__pre_086` backups + `_cache_national_wages_bea` dropped
- [x] T036 SC-008: re-run recompute and compare both table digests to the audit's `table_hashes` per contracts/determinism_contract.md (must match exactly)
- [x] T037 Live-DB gated integration test in REPO-B `tests/integration/test_qcew_live_reconciliation.py` (collection-skip when reference DB absent, pattern of `test_post_067_consumer_queries.py`): Wayne 2010 within ±2 % of 657,150 **via the real consumer paths** (`hex_hydrator` wages query + `county_aggregation.fetch_employment_proxy`) [SC-003, FR-010]; ≥99 % of county-years within ±2 % for employment AND wages via rollup-table join [SC-001/SC-002]; ≥95 % of county-ownership-years within ±2 % [SC-004]; national ±1 % per year [SC-005]
- [ ] T038 Operator: regenerate `tests/baselines/michigan-e2e.json` (`mise run sim:e2e-michigan`, ~45 min), then `mise run qa:e2e-regression` green + structural rate-of-profit invariants (s > 0, p′ finite) green; commit regenerated baseline citing the audit report (research D12)
- [x] T039 [P] REPO-B docs: `ai-docs/state.yaml` spec-086 sprint summary (SC outcomes, row counts, suppression stats); new ADR050 (QCEW synthetic-imputation architecture — records the spec-097 decision as implemented) in `ai-docs/decisions/` + append to `decisions/index.yaml`
- [ ] T040 [P] REPO-B: mark completed checkboxes in `specs/086-qcew-loader-imputation/{tasks.md,checklists/requirements.md}` as work lands (do NOT repeat spec-070's stale-checkbox trap)
- [ ] T041 Final gate: `mise run check` + `mise run test:all` green (unit/int/contract; live-gated tests run locally); final commits in both repos; update session memory (loader shipped, DB rebuilt, baselines regenerated)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none — start immediately. T001→T002→T003 sequential (same repo surgery); T004 after T003; T005 after T004
- **Foundational (Phase 2)**: after Phase 1 (fixtures import babylon_data.qcew). T006→T007; T008 parallel with T006/T007
- **US1 (Phase 3)**: after Phase 2. BLOCKS US2/US3 implementation (they orchestrate/report over US1's pipeline) — but their RED tests (T020–T023, T028–T030) can be written in parallel with US1 implementation
- **US2 (Phase 4)**: T024 depends on T017; T025 depends on T024; T026 parallel; T027 last
- **US3 (Phase 5)**: T031 depends on audit contract only (parallel-safe with US2 impl); T032 depends on T014–T018 + T024/T025 (touches all pipeline modules — do after US2 implementation to avoid same-file conflicts)
- **Phase 6**: after all stories; T034→T035→T036 sequential operator chain; T037 after T035; T038 after T035; T039/T040 parallel anytime after T035; T041 last

### Within-story rule

RED tests first and observed failing (`red_phase` marker) → implement → remove marker → checkpoint commit. Never commit red and green for the same behavior in one change-set unless it is the same unit of work (house rules).

## Parallel Example: User Story 1

```bash
# All US1 RED tests in parallel (different files):
T009 test_singlefile_classify.py | T010 test_hierarchy.py | T011 test_imputation.py \
| T012 test_imputation_determinism.py | T013 test_qcew_impute_e2e.py
# Then implementation mostly sequential (pipeline modules feed each other):
T014 singlefile.py → T015 hierarchy.py → T016 imputation.py → T017 writer.py → T018 validation.py
```

## Implementation Strategy

Incremental delivery in priority order — US1 (the correctness core) first, validated at fixture scale before any orchestration; US2 makes it operational; US3 makes it auditable; Phase 6 proves it against the real 8.3 GB source and re-baselines downstream. Note: this is execution sequencing within the full spec scope — all three stories + live delivery are in scope for 086 (no scope reduction; per project rule the full spec is the minimum).

**Total**: 41 tasks — Setup 5, Foundational 3, US1 11 (5 test + 6 impl), US2 8 (4 test + 4 impl), US3 6 (3 test + 3 impl), Delivery/Polish 8.
