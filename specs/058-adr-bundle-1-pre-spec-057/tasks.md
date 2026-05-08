# Tasks: ADR Bundle 1 — structural prep for Spec 057

**Branch**: `058-adr-bundle-1-pre-spec-057` | **Date**: 2026-05-08 | **Total tasks**: 91
**Inputs**: [`spec.md`](spec.md), [`plan.md`](plan.md), [`research.md`](research.md), [`data-model.md`](data-model.md), [`contracts/`](contracts/), [`quickstart.md`](quickstart.md)

This is a TDD-ordered task list (per project CLAUDE.md: "TDD: Red-Green-Refactor cycle mandatory"). The 91 tasks land as **7 conventional commits**, in the order resolved by `research.md` R1: US5 → US3a → US3b → US1.1 → US1.2 → US1.3 → (US2 + US4 bundled). Each commit is independently verifiable; the bundle ships as a coherent unit.

**Baseline tally**: 8988 passed / 186 skipped / 1 xfailed / 0 failures / 0 errors (post-`fix/dev-test-debt`-merge state on `dev` HEAD).

---

## Phase 1: Setup

- [ ] T001 Confirm baseline tests pass on branch `058-adr-bundle-1-pre-spec-057`: run `mise run check && mise run test:int`; verify tally matches 8988p / 186s / 1xf / 0f / 0e
- [ ] T002 Verify all spec/plan artifacts present: `ls specs/058-adr-bundle-1-pre-spec-057/` shows `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `checklists/`

---

## Phase 2: Foundational

> *No foundational prerequisites required.* Bundle 1 is a pure structural refactor; every user story can begin once Phase 1 confirms a clean baseline. Bundling 1's "foundational" work is the spec/plan artifact set, which is already complete.

---

## Phase 3: User Story 5 — OODA `_compute_membership_overlap` dedup (P3) — *commit 1*

**Story goal**: A single canonical implementation of `_compute_membership_overlap` exists in `src/babylon/ooda/_helpers.py`. Both `action_costs.py` and `action_effects.py` import from there.

**Independent test criteria**: After commit 1, `git grep -n "def _compute_membership_overlap" src/` returns exactly one match (in `src/babylon/ooda/_helpers.py`). Both `action_costs.py` and `action_effects.py` import from the canonical location. The OODA action-cost / action-effect test suites pass unchanged.

**Why this story first**: Per FR-011, US5 has the smallest blast radius; it's the safe warm-up commit and verifies the per-commit gate is functioning before larger commits land.

- [ ] T003 [US5] Write failing test in `tests/unit/ooda/test_membership_overlap_canonicalization.py` that asserts `git grep -c "def _compute_membership_overlap" src/` returns 1 (currently returns 2 — RED)
- [ ] T004 [US5] Create `src/babylon/ooda/_helpers.py` with the canonical `_compute_membership_overlap` function, extracted verbatim from `src/babylon/ooda/action_effects.py:249` (the longer of the two duplicates per ADR-001 references); declare `__all__ = ["_compute_membership_overlap"]`
- [ ] T005 [US5] Update `src/babylon/ooda/action_costs.py` to `from babylon.ooda._helpers import _compute_membership_overlap`; delete the local definition at line 85
- [ ] T006 [US5] Update `src/babylon/ooda/action_effects.py` to `from babylon.ooda._helpers import _compute_membership_overlap`; delete the local definition at line 249
- [ ] T007 [US5] Verify T003's test now passes (GREEN); run `poetry run pytest tests/unit/ooda/ tests/integration/test_ooda_*.py`; full OODA suite green
- [ ] T008 [US5] Run `mise run check`; commit: `refactor(ooda): extract _compute_membership_overlap helper`

---

## Phase 4: User Story 3 — Two oversized barrel files become packages with stable public imports (P1) — *commits 2 + 3*

**Story goal**: `src/babylon/models/enums.py` and `src/babylon/config/defines.py` are replaced by packages whose `__init__.py` re-exports every symbol with explicit `__all__`. Per Q2 clarification: flat re-exports + `import as` work; pickle qualname is intentionally not preserved.

**Independent test criteria**: After commit 3, every existing `from babylon.models.enums import X` and `from babylon.config.defines import Y` statement in the codebase continues to resolve unchanged. `GameDefines()` instantiates with the same shape. `pytest --collect-only` collects the same number of items as before. No file in either new package exceeds 600 LOC. The new `tests/unit/test_public_import_surface.py` regression test passes.

**Why this story second**: Per R1, the enums/defines splits land before the protocol_kit work because the `__all__` discipline established here informs how the new `core/protocol_kit.py` is structured.

### Sub-phase US3a — `enums.py` split (commit 2)

- [ ] T009 [US3] Run import-graph clustering analysis on `enums.py` per R2: `git grep -E "from babylon.models.enums import" src/ tests/ > /tmp/058_enums_imports.txt`; build co-occurrence matrix in a one-off Python script; output proposed clustering to `/tmp/058_enums_clustering.json` (planning artifact, not committed)
- [ ] T010 Create `tests/unit/test_public_import_surface.py` per SC-006: assert `set(babylon.models.enums.__all__)` matches the pre-split symbol set (extract baseline via `python -c "from babylon.models import enums; print(sorted(n for n in dir(enums) if not n.startswith('_')))"`); initially RED until commit 2 declares `__all__`
- [ ] T011 [US3] Create `src/babylon/models/enums/` package skeleton: empty `__init__.py` and one `*.py` file per cluster from T009 (~7-9 files); each sub-module starts as an empty stub
- [ ] T012 [US3] Move enum classes from the old `enums.py` into their cluster sub-modules per T009's mapping; declare `__all__` in each sub-module enumerating its public classes
- [ ] T013 [US3] Wire `src/babylon/models/enums/__init__.py` to re-export every symbol via `from .topology import *`-style imports; declare aggregate `__all__` matching the pre-split symbol set baseline from T010
- [ ] T014 [US3] Delete `src/babylon/models/enums.py` (the old monolith)
- [ ] T015 [US3] Verify per-file LOC cap: `find src/babylon/models/enums -name "*.py" -exec wc -l {} \;` reports no file over 600 LOC (SC-002); if any over, split further into nested sub-packages per R2 escape hatch
- [ ] T016 [US3] Verify `git grep` byte-equality: `git grep -hn "from babylon.models.enums import" src/ tests/ | sort | uniq -c | sort -rn > /tmp/058_enums_imports_after.txt`; compare with pre-split snapshot from T009 — same line count and same import sets
- [ ] T017 [US3] Verify T010's regression test now passes (GREEN); run `mise run check && mise run test:unit`; baseline tally preserved
- [ ] T018 [US3] Commit: `refactor(models): split enums.py into enums/ package`

### Sub-phase US3b — `defines.py` split (commit 3)

- [ ] T019 [US3] Run import-graph clustering analysis on `defines.py` per R2: same algorithm as T009 but `git grep -E "from babylon.config.defines import" src/ tests/`; output to `/tmp/058_defines_clustering.json`
- [ ] T020 [US3] Create `src/babylon/config/defines/` package skeleton: empty `__init__.py`, `_assembler.py`, and one `*.py` file per cluster from T019 (~7-10 files); each sub-module starts as an empty stub
- [ ] T021 [US3] Move `*Defines` Pydantic classes from the old `defines.py` into their cluster sub-modules per T019's mapping; declare `__all__` in each sub-module
- [ ] T022 [US3] Move `GameDefines` assembler logic from the old `defines.py` into `src/babylon/config/defines/_assembler.py` (composition + `pyproject.toml [tool.babylon]` loading)
- [ ] T023 [US3] Wire `src/babylon/config/defines/__init__.py` to re-export `GameDefines` + every `*Defines` class; declare aggregate `__all__` matching the pre-split symbol set
- [ ] T024 [US3] Delete `src/babylon/config/defines.py` (the old monolith)
- [ ] T025 [US3] Update `tests/unit/test_public_import_surface.py` to add `babylon.config.defines.__all__` assertions (parallel to the enums assertions added in T010)
- [ ] T026 [US3] Verify per-file LOC cap: `find src/babylon/config/defines -name "*.py" -exec wc -l {} \;` reports no file over 600 LOC; if any over (likely candidates per ADR-001: `OODADefines` at 441 LOC and `StateApparatusAIDefines` at 480 LOC, both well under cap when alone in a file), split per R2 escape hatch
- [ ] T027 [US3] Verify GameDefines wiring intact: `python -c "from babylon.config.defines import GameDefines; gd = GameDefines(); print(gd.economy.extraction_efficiency)"` returns `0.8`
- [ ] T028 [US3] Verify import equivalence and run `mise run check && mise run test:unit`; baseline tally preserved
- [ ] T029 [US3] Commit: `refactor(config): split defines.py into defines/ package`

---

## Phase 5: User Story 1 — Source-pattern boilerplate is gone for new data sources (P1) — *commits 4 + 5 + 6*

**Story goal**: `src/babylon/core/protocol_kit.py` exists with `DataSource`, `CachedSource[T]`, `SourceRegistry`. At least 10 `Default*` classes from `melt/` + `gamma/` inherit from `CachedSource[T]`. `economics/factory.py` shrinks to <150 LOC with the 4 `create_*_services()` shims delegating to `SourceRegistry.builtin_economics()`.

**Independent test criteria**: After commit 6, the 18 contract tests in `tests/unit/core/test_protocol_kit.py` (8 from `contracts/protocol_kit.md` + 10 from `contracts/source_registry.md` items 1-10) and the 3 factory-shim tests in `tests/unit/economics/test_factory_shims.py` (from `contracts/source_registry.md` items 11-13) all pass — 21 new tests total across both files. SC-005 is verifiable by counting `CachedSource` subclasses in `melt/` + `gamma/`. SC-004 is verifiable by `wc -l src/babylon/economics/factory.py < 150`. The Spec 057 forward-compat smoke test from `quickstart.md` succeeds.

**Why this story third**: Per R1, the protocol_kit lands after the package splits because the `__all__` discipline established in US3 informs the kit's own `__all__` declaration. The 3-commit split (kit → migrations → factory) keeps each diff under ~25 files for review-ability.

### Sub-phase US1.1 — `protocol_kit` introduction (commit 4)

- [ ] T030 [P] [US1] Create `tests/unit/core/test_protocol_kit.py` with the 8 `CachedSource` tests from `contracts/protocol_kit.md` "Test contract" section + the 10 `SourceRegistry` tests from `contracts/source_registry.md` "Test contract" **items 1-10** (18 tests total in this file; **items 11-13 belong in `test_factory_shims.py` per T031 — do NOT duplicate them here**); initially RED — module doesn't exist yet
- [ ] T031 [P] [US1] Create `tests/unit/economics/test_factory_shims.py` with the 3 shim-acceptance tests from `contracts/source_registry.md` "Test contract" items 11-13; initially RED — will pass after commit 6 (T057)
- [ ] T032 [US1] Create `src/babylon/core/__init__.py` as an empty package marker
- [ ] T033 [US1] Create `src/babylon/core/protocol_kit.py` with `DataSource` (Protocol marker), `CachedSource[T]` (Generic ABC with `cache_negative_results: bool = True` class attribute, `__init__`, `_resolve`, `invalidate`, `clear`), and `SourceRegistry` (concrete class with `register`, `get`, `has`, stub `builtin_economics`) per `data-model.md` §2-§4 and `contracts/protocol_kit.md` + `contracts/source_registry.md`
- [ ] T034 [US1] Stub `SourceRegistry.builtin_economics()` body to `return self  # filled in commit 6 — see T053`; this leaves no integration broken at commit 4 boundary
- [ ] T035 [US1] Verify T030's 18 contract tests pass (GREEN); the 3 factory-shim tests in T031 stay RED until commit 6
- [ ] T036 [US1] Run `mise run check && mise run test:unit`; baseline tally + 21 new tests passing; the 3 factory-shim RED tests are *expected* to still RED (mark with `@pytest.mark.xfail(reason="GREEN at commit 6")` to keep CI green between commit 4 and commit 6)
- [ ] T037 [US1] Commit: `feat(core): add protocol_kit with DataSource, CachedSource, SourceRegistry`

### Sub-phase US1.2 — melt/ + gamma/ Default* migrations (commit 5)

- [ ] T038 [US1] MRO inspection for all 10 melt+gamma `Default*` classes per R3 — concrete targets (one `Default*` class per file, see T039-T048 for the per-file mapping): `melt/melt_calculator.py` (`DefaultMELTCalculator`), `melt/basket_visibility.py`, `melt/class_position.py`, `melt/rent_differential.py`, `melt/wealth_proxy.py`, `melt/unified_classifier.py` (`DefaultUnifiedClassifier`), `gamma/gamma_iii.py`, `gamma/gamma_basket.py`, `gamma/gamma_import.py`, `gamma/shadow_subsidy.py`. For each, run `python -c "from babylon.economics.<pkg>.<module> import <DefaultClass>; print(<DefaultClass>.__mro__)"` and confirm single-inheritance from `object` (the precondition for clean `CachedSource[T]` mixin). If any conflict with `CachedSource[T]`, swap per spec Risks (substitute another `Default*` from `economics/credit/`, `economics/throughput/`, `economics/rent/`, etc.) and document the swap in commit 5's message
- [ ] T039 [P] [US1] Migrate `DefaultMELTCalculator` in `src/babylon/economics/melt/melt_calculator.py` to inherit from `CachedSource[T]`; replace hand-rolled `__init__` cache management with `_resolve(key, fetch)` calls in lookup methods; verify melt unit tests still pass (`poetry run pytest tests/unit/economics/melt/test_melt_calculator.py`)
- [ ] T040 [P] [US1] Migrate the `Default*` class in `src/babylon/economics/melt/basket_visibility.py` to `CachedSource[T]`; verify `poetry run pytest tests/unit/economics/melt/test_basket_visibility.py`
- [ ] T041 [P] [US1] Migrate the `Default*` class in `src/babylon/economics/melt/class_position.py` to `CachedSource[T]`; verify `poetry run pytest tests/unit/economics/melt/test_class_position.py`
- [ ] T042 [P] [US1] Migrate the `Default*` class in `src/babylon/economics/melt/rent_differential.py` to `CachedSource[T]`; verify `poetry run pytest tests/unit/economics/melt/test_rent_differential.py` (or per-file equivalent)
- [ ] T043 [P] [US1] Migrate the `Default*` class in `src/babylon/economics/melt/wealth_proxy.py` to `CachedSource[T]`; verify `poetry run pytest tests/unit/economics/melt/test_wealth_proxy.py`
- [ ] T044 [P] [US1] Migrate `DefaultUnifiedClassifier` in `src/babylon/economics/melt/unified_classifier.py` to `CachedSource[T]`; verify `poetry run pytest tests/unit/economics/melt/test_unified_classifier.py`
- [ ] T045 [P] [US1] Migrate the `Default*` class in `src/babylon/economics/gamma/gamma_iii.py` to `CachedSource[T]`; verify `poetry run pytest tests/unit/economics/gamma/test_gamma_iii.py`
- [ ] T046 [P] [US1] Migrate the `Default*` class in `src/babylon/economics/gamma/gamma_basket.py` to `CachedSource[T]`; verify `poetry run pytest tests/unit/economics/gamma/test_gamma_basket.py`
- [ ] T047 [P] [US1] Migrate the `Default*` class in `src/babylon/economics/gamma/gamma_import.py` to `CachedSource[T]`; verify `poetry run pytest tests/unit/economics/gamma/test_gamma_import.py`
- [ ] T048 [P] [US1] Migrate the `Default*` class in `src/babylon/economics/gamma/shadow_subsidy.py` to `CachedSource[T]`; verify `poetry run pytest tests/unit/economics/gamma/test_shadow_subsidy.py`
- [ ] T049 [US1] Verify migration count via the SC-005 check from `quickstart.md` commit 5 verification recipe: `find src/babylon/economics/{melt,gamma} -name "*.py" -exec grep -l "CachedSource" {} \; | xargs grep -c "^class Default"` reports total ≥10
- [ ] T050 [US1] Run `poetry run pytest tests/unit/economics/melt/ tests/unit/economics/gamma/`; all melt + gamma unit tests pass
- [ ] T051 [US1] Run `mise run check`; full fast gate passes; baseline tally preserved
- [ ] T052 [US1] Commit: `refactor(economics): migrate melt/ + gamma/ Default* classes to CachedSource[T]`

### Sub-phase US1.3 — factory.py SourceRegistry migration (commit 6)

- [ ] T053 [US1] Fill `SourceRegistry.builtin_economics()` body in `src/babylon/core/protocol_kit.py` with the 10 `register()` calls for melt+gamma `(Protocol, Default)` pairs per `contracts/source_registry.md` and `data-model.md` §4
- [ ] T054 [US1] Decide R5 disposition for the 3 `load_*_series_from_db` helpers in `factory.py`: (a) move to a new `src/babylon/economics/_db_helpers.py` module, OR (b) inline into `Default*._fetch` bodies now that those classes use `CachedSource[T]`; document the choice in commit 6's message
- [ ] T055 [US1] Refactor `src/babylon/economics/factory.py`: replace each of the 4 `create_*_services()` function bodies (`create_economics_services`, `create_financial_services`, `create_circulation_services`, `create_vol1_services`) with a 3-line shim per `contracts/source_registry.md` "Migration shims" section; preserve public function signatures
- [ ] T056 [US1] Verify factory.py LOC cap (SC-004): `wc -l src/babylon/economics/factory.py` reports < 150
- [ ] T057 [US1] Remove the `xfail` marker from T031's 3 factory-shim tests; verify they now pass (GREEN)
- [ ] T058 [US1] Run `mise run check && mise run test:int`; baseline tally preserved (within ±3 tests for the new test files)
- [ ] T059 [US1] Commit: `refactor(economics): replace factory.py wiring with SourceRegistry.builtin_economics()`

---

## Phase 6: User Story 2 — `tick/system.py` god-class is decomposed (P1) — *commit 7, part A*

**Story goal**: `src/babylon/economics/tick/system.py` (1705 LOC, 33 methods) is replaced by a `tick/system/` package with a ≤200-LOC `TickDynamicsSystem` facade and 8-9 focused sub-modules (each ≤400 LOC). Per Q3 clarification: behavioral fence preserves return-type classes, exception class hierarchies, and event-bus emission ordering. Per FR-008: the spec-057 quarantine on `_compute_imperial_rent` is preserved (stub body unchanged, tests stay skipped).

**Independent test criteria**: After commit 7 (US2 part), the new `tests/integration/economics/tick/test_facade_behavioral_fence.py` passes (frozen-seed tick produces a `WorldState` and event-bus history that diff-equal a frozen baseline). `wc -l` confirms the 200/400 LOC caps. `_compute_imperial_rent` lives in `tick/system/imperial_rent.py` with the spec-057 skipped tests still skipping the same count. The full tick test suite (`tests/unit/economics/tick/` + `tests/integration/economics/`) passes unchanged.

**Why this story fourth**: Per R1, the tick decomposition is bundled into commit 7 with US4 (BEAMappings typing) because both touch `economics/` and ship together for an atomic post-bundle baseline. US2 is the larger half of commit 7 and lands first within the commit's task ordering.

- [ ] T060 [US2] Create `tests/integration/economics/tick/test_facade_behavioral_fence.py` per Q3 clarification: instantiate `TickDynamicsSystem` from a frozen seed (`SimulationConfig` with deterministic random_seed), run one full tick, snapshot the returned `WorldState` JSON dump + the event-bus `get_history()` list to fixture; the test asserts both diff-equal a saved baseline JSON
- [ ] T061 [US2] Capture the pre-decomposition behavioral baseline: run the new test against the current monolithic `tick/system.py`, save the snapshot to `tests/integration/economics/tick/_facade_baseline.json` (commit this file as the frozen baseline)
- [ ] T062 [US2] Create `src/babylon/economics/tick/system/` package skeleton with empty `__init__.py` and 9 sub-module files per R4: `initialization.py`, `national_parameters.py`, `county_distribution.py`, `imperial_rent.py`, `crisis.py`, `volume_layers.py`, `tensor_helpers.py`, `bifurcation.py`, `transitions.py`
- [ ] T063 [US2] Extract `_determine_year`, `_get_territory_fips`, `_bootstrap_county_states` (3 methods) from the old `tick/system.py` into `src/babylon/economics/tick/system/initialization.py`; preserve method signatures exactly per Q3 behavioral fence
- [ ] T064 [P] [US2] Extract `_compute_national_params`, `_update_coefficients` (2 methods) into `src/babylon/economics/tick/system/national_parameters.py`
- [ ] T065 [P] [US2] Extract `_compute_county_states`, `_derive_precarity`, `_write_hex_substrate` (3 methods) into `src/babylon/economics/tick/system/county_distribution.py`
- [ ] T066 [P] [US2] Extract `_compute_imperial_rent` (1 method, the spec-057 stub) into `src/babylon/economics/tick/system/imperial_rent.py`; FR-008 — body unchanged, the existing `pytest.mark.skip` markers in the quarantined test files are NOT touched
- [ ] T067 [P] [US2] Extract `_check_crisis_triggers`, `_emit_crisis_event`, `_check_dispossession_cascade`, `_get_profit_rate` (4 methods) into `src/babylon/economics/tick/system/crisis.py`; if `wc -l` reports >400 LOC, split into `crisis.py` (triggers + emit) and `dispossession.py` (cascade + profit_rate) per R4 mitigation
- [ ] T068 [P] [US2] Extract `_compute_vol1_layer`, `_compute_vol1_county_state`, `_compute_circulation_layer`, `_compute_national_circulation_state`, `_compute_county_circulation_state`, `_compute_financial_layer`, `_compute_national_financial_state`, `_compute_county_financial_state`, `_assess_county_financial_crisis` (9 methods) into `src/babylon/economics/tick/system/volume_layers.py`; if >400 LOC, split into nested `volume_layers/{vol1,circulation,financial}.py` sub-package per R4 escape hatch
- [ ] T069 [P] [US2] Extract `_get_best_tensor_year`, `_get_county_profit_rate`, `_get_county_surplus` (3 methods) into `src/babylon/economics/tick/system/tensor_helpers.py`
- [ ] T070 [P] [US2] Extract `_compute_bifurcation_risk`, `_emit_bifurcation_event` (2 methods) into `src/babylon/economics/tick/system/bifurcation.py` (Constitution I.4 — George Jackson Bifurcation, preserve emission order per Q3)
- [ ] T071 [P] [US2] Extract `_simulate_transitions`, `_validate_distributions`, `_compute_tick_summary` (3 methods) into `src/babylon/economics/tick/system/transitions.py`
- [ ] T072 [US2] Build the `TickDynamicsSystem` facade in `src/babylon/economics/tick/system/__init__.py`: `__init__` (composition: instantiates the 9 sub-modules), `name` (returns `"TickDynamicsSystem"`), `step(graph, services, context) -> tuple[graph, events]` (orchestrates sub-module calls in the same order as the old monolith); MUST be ≤200 LOC per SC-002
- [ ] T073 [US2] Delete `src/babylon/economics/tick/system.py` (the old monolith)
- [ ] T074 [US2] Verify LOC caps: facade ≤200 LOC (`wc -l src/babylon/economics/tick/system/__init__.py`); per-sub-module ≤400 LOC (`find src/babylon/economics/tick/system -name "*.py" -exec wc -l {} \;`)
- [ ] T075 [US2] Verify spec-057 quarantine preserved (FR-008): `grep -n "_compute_imperial_rent" src/babylon/economics/tick/system/imperial_rent.py` shows the stub function exists; `pytest tests/ -k "imperial_rent" --collect-only 2>&1 | grep -c "skipped"` reports the same skipped count as the pre-decomposition baseline
- [ ] T076 [US2] Verify behavioral fence test passes (T060 GREEN); `poetry run pytest tests/integration/economics/tick/test_facade_behavioral_fence.py -v`
- [ ] T077 [US2] Run `mise run check && mise run test:int`; baseline tally preserved within ±3 tests for the new behavioral fence test

---

## Phase 7: User Story 4 — BEA-to-Department mapping is typed (P2) — *commit 7, part B*

**Story goal**: A frozen `BEAMappings` Pydantic model wraps the BEA-NAICS-to-Marxian-Department table. The TOML at `economics/tensor_hierarchy/mappings/bea_to_department.toml` is loaded once at import time into a module-level `BEA_TO_DEPARTMENT` constant. `economics/department_mapper.py` consumes the typed object instead of reparsing TOML on every call. Per spec Edge Cases: malformed TOML raises at import time, not runtime.

**Independent test criteria**: After commit 7 (US4 part), the 14 contract tests in `tests/unit/economics/tensor_hierarchy/test_bea_mappings.py` pass. `grep -n "tomllib" src/babylon/economics/department_mapper.py` returns zero matches. The legacy department-mapper tests pass unchanged (the typed object is a drop-in replacement).

**Why this story fifth**: Per R1, US4 lands in commit 7 alongside US2 because both touch `economics/`. US4 has lower priority (P2) and smaller blast radius, so it slots in after the larger US2 work within the same commit.

- [ ] T078 [US4] Create `tests/unit/economics/tensor_hierarchy/test_bea_mappings.py` with the 14 contract tests from `contracts/bea_mappings.md` "Test contract" section (production TOML acceptance tests #1-5; synthetic malformed-fixture rejection tests #6-13; equivalence-with-legacy test #14); initially RED — `BEAMappings` doesn't exist yet
- [ ] T079 [US4] Create `src/babylon/economics/tensor_hierarchy/mappings/_models.py` with `DepartmentMapping` (frozen Pydantic, `bea_code: str`, `department: Literal["I", "II", "III"]`, `weight: float ∈ [0,1]`) and `BEAMappings` (frozen Pydantic, `mappings: list[DepartmentMapping]` with `min_length=1`, model-level `_check_invariants` validator enforcing per-bea_code uniqueness and weight-sum-equals-1.0-within-1e-9, `get_departments(bea_code) -> Mapping[str, float]` method) per `data-model.md` §1
- [ ] T080 [US4] Create `src/babylon/economics/tensor_hierarchy/mappings/__init__.py` with module-level `BEA_TO_DEPARTMENT: Final[BEAMappings]` loaded once via `BEAMappings.model_validate(tomllib.loads(_TOML_PATH.read_text()))`; declare `__all__ = ["BEAMappings", "BEA_TO_DEPARTMENT", "DepartmentMapping"]` per `data-model.md` §5
- [ ] T081 [US4] Refactor `src/babylon/economics/department_mapper.py` to consume `BEA_TO_DEPARTMENT` instead of reparsing TOML on every call: delete `import tomllib`, delete the `_reparse_and_lookup` helper (or whatever the current per-call reparse function is named), update `get_default_mapper()` to construct `DepartmentMapper(mapping=BEA_TO_DEPARTMENT)`
- [ ] T082 [US4] Verify T078's 14 BEAMappings tests pass (GREEN); `poetry run pytest tests/unit/economics/tensor_hierarchy/test_bea_mappings.py -v`
- [ ] T083 [US4] Verify the runtime-reparse pattern is gone: `grep -n "tomllib" src/babylon/economics/department_mapper.py` returns zero matches
- [ ] T084 [US4] Run `mise run check && mise run test:int`; baseline tally preserved within ±5 tests for the new behavioral-fence + BEAMappings test files
- [ ] T085 [US2] Commit (bundled US2 + US4 per R1 — also closes US4): `refactor(economics): decompose tick/system.py into focused subcomponents + type bea_to_department mapping`

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T086 [P] Update `ai-docs/state.yaml`: bump test-count entries to reflect post-bundle tally (8988p + N new tests / 186s / 1xf); mark Bundle 1 as complete; add ADR-001/002/006.3/006.5 references
- [ ] T087 [P] Update `ai-docs/roadmap.md`: mark Bundle 1 (spec 058) complete; note Spec 057 is unblocked; flag Bundle 3 (deferred per spec Out of Scope: ADR-003, ADR-004, ADR-005, ADR-006 items 6.1/6.2/6.4/6.6) as next-after-057 work
- [ ] T088 [P] Add ADR entry to `ai-docs/decisions.yaml` referencing Bundle 1 and pointing at the canonical ADRs (`docs/agents/adrs/ADR-001`, `ADR-002`, `ADR-006` items 6.3 and 6.5); record the four Q1-Q4 clarifications from Spec 058 as part of the decision record
- [ ] T089 Run the Spec 057 forward-compat smoke test from `quickstart.md` "Spec 057 forward-compat sanity check" section: (a) write the 30-line `DefaultPeripheryLaborCoefficientsSource` template to `/tmp/spec057_smoke.py`, (b) verify it imports and runs, (c) confirm `tick/system/imperial_rent.py` exists and is the spec-057 landing pad, (d) confirm `BEA_TO_DEPARTMENT` is consumable as a `dept_mapping` argument
- [ ] T090 Final bundle verification: run `mise run check && mise run test:int && mise run test:scenario` (full pre-PR gate); tally matches baseline 8988p / 186s / 1xf within ±5 tests for the new test files added by commits 4 (T030 → 18 tests, T031 → 3 tests), 5 (none), 7 (T060 → 1 test, T078 → 14 tests, T010+T025 → 1-2 tests = ~37 new tests total); no unexpected skips, no new xfails
- [ ] T091 Open PR `058-adr-bundle-1-pre-spec-057` → `dev`; PR description references `spec.md`, `plan.md`, `research.md`, the four ADRs, the four Q1-Q4 clarifications, and the 7-commit changelog; tag PR for review

---

## Dependencies & Parallelization

### Phase ordering (sequential)

```
Phase 1 (Setup)  →  Phase 3 (US5)  →  Phase 4 (US3a → US3b)  →  Phase 5 (US1.1 → US1.2 → US1.3)  →  Phase 6 (US2)  →  Phase 7 (US4)  →  Phase 8 (Polish)
```

Phase 2 (Foundational) is empty for this bundle. Phase 6 and Phase 7 share commit 7 and ship together (T085 is the joint commit). Phase 8 does not require any commits — it is documentation + verification only, except for T086-T088 which may be a single small `docs:` commit.

### Within-story parallelization opportunities

| Phase | Parallel band | Tasks | Why parallel |
|-------|---------------|-------|--------------|
| Phase 5 (US1.1) | TDD setup | T030, T031 | Different test files, no inter-dependencies |
| Phase 5 (US1.2) | Migrations | T039 → T048 (10 tasks) | Different `Default*` classes in different files; each migration is mechanical and self-contained |
| Phase 6 (US2) | Sub-module extractions | T064 → T071 (8 tasks; T063 must finish first) | After `initialization.py` is extracted (T063 sequential), the remaining 8 sub-modules each take a different cluster of methods and can extract in parallel |
| Phase 8 (Polish) | Doc updates | T086, T087, T088 | Different ai-docs files; no shared state |

### Commit-boundary verification gates

After each commit, run the per-commit verification recipe from `quickstart.md`:

| Commit | After tasks | Verification |
|--------|-------------|--------------|
| 1 | T008 | `git grep -c "def _compute_membership_overlap" src/` = 1 |
| 2 | T018 | `__all__` declared; per-file LOC ≤600; baseline tally preserved |
| 3 | T029 | `GameDefines()` works; per-file LOC ≤600; baseline tally preserved |
| 4 | T037 | 21 protocol_kit contract tests pass; 3 factory-shim tests are xfail |
| 5 | T052 | ≥10 `Default*` classes inherit from `CachedSource[T]`; melt/gamma tests pass |
| 6 | T059 | factory.py < 150 LOC; 3 factory-shim tests now pass; baseline tally preserved |
| 7 | T085 | facade ≤200 LOC; sub-modules ≤400 LOC; behavioral fence test passes; 14 BEAMappings tests pass; spec-057 quarantine preserved |

### Story-level dependencies (which user stories block which)

- **US5** has no dependencies; ships first
- **US3** depends on US5 only for clean baseline (no code dependency)
- **US1** depends on US3 (the new `__all__` discipline informs `core/protocol_kit.py`); ships in 3 commits
- **US2** depends on US1 indirectly (the post-US1 `mise run check` baseline is the regression net for the behavioral fence); ships in commit 7
- **US4** depends on US2 only because they share commit 7 (the typed `BEAMappings` itself does not depend on US2's tick decomposition)

---

## Implementation Strategy

### MVP scope

For Bundle 1, the MVP is the *full bundle* — splitting into a partial-MVP doesn't make sense because the bundle's purpose is to land all four pre-Spec-057 refactors atomically. Spec 057 wants to branch from a clean post-bundle `dev`, not a half-bundled intermediate state.

**Smallest verifiable increment**: commit 1 alone (US5 OODA dedup, ~6 tasks, ~30 LOC of code change, ~50 LOC of test). After commit 1 passes verification, the per-commit gate is proven; the rest of the bundle can proceed with confidence.

### Incremental delivery

Each commit is independently revertible (per `quickstart.md` "Rollback procedure"). If any commit fails the gate, `git revert HEAD` produces a clean revert without affecting prior commits. This allows the bundle to be paused mid-roll at any commit boundary if a real-world interruption occurs (e.g., a CI infrastructure outage).

### Suggested working order

1. **Day 1 morning**: Phase 1 (T001-T002) + Phase 3 US5 (T003-T008) + start Phase 4 US3a (T009-T018)
2. **Day 1 afternoon**: Finish Phase 4 US3a; start US3b (T019-T029)
3. **Day 2 morning**: Finish Phase 4 US3b; Phase 5 US1.1 (T030-T037)
4. **Day 2 afternoon**: Phase 5 US1.2 (T038-T052) — 10 parallel migrations
5. **Day 3 morning**: Phase 5 US1.3 (T053-T059)
6. **Day 3 afternoon + Day 4 morning**: Phase 6 US2 (T060-T077) — the largest single commit
7. **Day 4 afternoon**: Phase 7 US4 (T078-T084) + commit 7 (T085)
8. **Day 5 morning**: Phase 8 Polish (T086-T091); open PR

Estimated total: **5 working days** for a single contributor; 3 working days with the parallelization opportunities flagged above.

---

## Format Validation

All 91 tasks follow the required checklist format: `- [ ] T### [P?] [Story?] Description with file path`.

- ✅ Every task starts with `- [ ]` (markdown checkbox)
- ✅ Every task has a sequential T### ID
- ✅ User-story tasks (T003-T085) have the correct [USX] label
- ✅ Setup (T001-T002) and Polish (T086-T091) tasks have NO story label
- ✅ Foundational phase has no tasks (correctly empty)
- ✅ [P] markers applied only to tasks with no incomplete dependencies and different file targets
- ✅ Every task description references the exact file path being created/modified
- ✅ TDD ordering preserved: tests precede implementations within each user story phase

**Total tasks**: 91 (T001 → T091)
**Tasks per user story**:
- Setup: 2 (T001, T002)
- US5 (P3): 6 (T003-T008)
- US3 (P1): 21 (T009-T029, split as US3a 10 + US3b 11)
- US1 (P1): 30 (T030-T059, split as US1.1 8 + US1.2 15 + US1.3 7)
- US2 (P1): 18 (T060-T077)
- US4 (P2): 7 (T078-T084) + 1 shared commit task (T085)
- Polish: 6 (T086-T091)
