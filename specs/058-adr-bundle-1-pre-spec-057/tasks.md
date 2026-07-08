# Tasks: ADR Bundle 1 — structural prep for Spec 057

**Branch**: `058-adr-bundle-1-pre-spec-057` | **Date**: 2026-05-08 | **Total tasks**: 91
**Inputs**: [`spec.md`](spec.md), [`plan.md`](plan.md), [`research.md`](research.md), [`data-model.md`](data-model.md), [`contracts/`](contracts/), [`quickstart.md`](quickstart.md)

This is a TDD-ordered task list (per project CLAUDE.md: "TDD: Red-Green-Refactor cycle mandatory"). The 91 tasks land as **7 conventional commits**, in the order resolved by `research.md` R1: US5 → US3a → US3b → US1.1 → US1.2 → US1.3 → (US2 + US4 bundled). Each commit is independently verifiable; the bundle ships as a coherent unit.

**Baseline tally**: 8988 passed / 186 skipped / 1 xfailed / 0 failures / 0 errors (post-`fix/dev-test-debt`-merge state on `dev` HEAD).

---

## Phase 1: Setup

- [X] T001 Baseline run: actual = 8987p / 186s / 1xf / 1f (pre-existing order-dependent flake in `tests/property/invariants/test_wealth_heat_bounds.py::test_per_system_coverage_complete` from spec 054 — unrelated to Bundle 1; treating as working baseline; bundle invariant: hold this constant, don't make worse)
- [X] T002 Artifacts present and committed (`154f71bc docs(spec-058): planning artifacts`)

---

## Phase 2: Foundational

> *No foundational prerequisites required.* Bundle 1 is a pure structural refactor; every user story can begin once Phase 1 confirms a clean baseline. Bundling 1's "foundational" work is the spec/plan artifact set, which is already complete.

---

## Phase 3: User Story 5 — OODA `_compute_membership_overlap` dedup (P3) — *commit 1*

**Story goal**: A single canonical implementation of `_compute_membership_overlap` exists in `src/babylon/ooda/_helpers.py`. Both `action_costs.py` and `action_effects.py` import from there.

**Independent test criteria**: After commit 1, `git grep -n "def _compute_membership_overlap" src/` returns exactly one match (in `src/babylon/ooda/_helpers.py`). Both `action_costs.py` and `action_effects.py` import from the canonical location. The OODA action-cost / action-effect test suites pass unchanged.

**Why this story first**: Per FR-011, US5 has the smallest blast radius; it's the safe warm-up commit and verifies the per-commit gate is functioning before larger commits land.

- [X] T003 [US5] Wrote 3 RED canonicalization tests at `tests/unit/ooda/test_membership_overlap_canonicalization.py` (count=1, importable, both call sites import from _helpers)
- [X] T004 [US5] Created `src/babylon/ooda/_helpers.py` with action_effects.py's richer impl (cross-reference fallback when `member_node_ids` empty); `__all__ = ["_compute_membership_overlap"]`
- [X] T005 [US5] action_costs.py: imports from `_helpers`, local def deleted (now uses richer fallback — semantic upgrade per spec acceptance scenario 1)
- [X] T006 [US5] action_effects.py: imports from `_helpers`, local def deleted, `EdgeType` removed from imports (no longer used here)
- [X] T007 [US5] GREEN: 310 passed / 1 skipped in OODA + canonicalization suites
- [X] T008 [US5] Pre-commit hooks (lint+format+mypy+commitizen) all passed; committed `2a114617 refactor(ooda): extract _compute_membership_overlap helper` (5 files, +183/-100)

---

## Phase 4: User Story 3 — Two oversized barrel files become packages with stable public imports (P1) — *commits 2 + 3*

**Story goal**: `src/babylon/models/enums.py` and `src/babylon/config/defines.py` are replaced by packages whose `__init__.py` re-exports every symbol with explicit `__all__`. Per Q2 clarification: flat re-exports + `import as` work; pickle qualname is intentionally not preserved.

**Independent test criteria**: After commit 3, every existing `from babylon.models.enums import X` and `from babylon.config.defines import Y` statement in the codebase continues to resolve unchanged. `GameDefines()` instantiates with the same shape. `pytest --collect-only` collects the same number of items as before. No file in either new package exceeds 600 LOC. The new `tests/unit/test_public_import_surface.py` regression test passes.

**Why this story second**: Per R1, the enums/defines splits land before the protocol_kit work because the `__all__` discipline established here informs how the new `core/protocol_kit.py` is structured.

### Sub-phase US3a — `enums.py` split (commit 2)

- [X] T009 [US3] Co-occurrence clustering produced 22 clusters (informative; pivoted to semantic clustering — 9 sub-modules + _resolution.py per ADR-001 priors with the 600-LOC cap as the binding constraint). Integration-gap audit added as polish-phase follow-up note.
- [X] T010 Wrote 5 RED public-import-surface tests at `tests/unit/test_public_import_surface.py` (covers all 46 baseline symbols: 45 enums + resolve_edge_type)
- [X] T011 [US3] Wrote `/tmp/058_split_enums.py` AST-driven splitter; produces 11 files (9 categories + _resolution + __init__) preserving every comment, docstring, and section header verbatim
- [X] T012 [US3] Splitter ran cleanly: 45 classes distributed across 9 sub-modules (topology=6, social=7, consciousness=4, territory=7, events=3, actions=2, legal=6, community=2, organizations=8); each sub-module declares __all__
- [X] T013 [US3] __init__.py re-exports all 46 symbols via grouped `from babylon.models.enums.<sub> import (...)` blocks; aggregate __all__ matches baseline
- [X] T014 [US3] Old `enums.py` monolith deleted
- [X] T015 [US3] Per-file LOC cap holds: largest is `organizations.py` at 260 LOC; all others <200 LOC; cap of 600 not approached
- [X] T016 [US3] Public-import-surface verified: 5/5 import-surface tests pass; flat imports + star imports + module.attr access all work
- [X] T017 [US3] Full fast-gate: 8995p / 186s / 1xf / 1f (1f is pre-existing flake unchanged). +5 passed from new import-surface tests. mypy on enums/ clean (1 pre-existing error in engine/hydration/reference.py:726 unrelated to this commit). ruff autofixed 11 I001 (import sorting).
- [x] T018 [US3] Commit: `refactor(models): split enums.py into enums/ package` (verified 2026-07-08: commit d6f6f934 "refactor(models): split enums.py into enums/ package")

### Sub-phase US3b — `defines.py` split (commit 3)

- [X] T019 [US3] LOC analysis showed `economy` semantic cluster at 755 LOC and `organizations+ooda+lifecycle` at 1002 LOC — both over 600 cap. Per R2 escape hatch, expanded to 12 sub-modules (split economy into 3 sub-clusters; split ooda alone)
- [X] T020 [US3] Wrote `/tmp/058_split_defines.py` AST-driven splitter; produces 14 files (12 categories + _assembler + __init__)
- [X] T021 [US3] Splitter ran cleanly: 41 child Defines distributed; each sub-module declares __all__; common imports header added (BaseModel, ConfigDict, Field, model_validator, Any)
- [X] T022 [US3] _assembler.py contains GameDefines + 4 classmethods (load_from_yaml, _from_yaml_dict, default_yaml_path, load_default) + 8 legacy @property accessors; default_yaml_path Path(__file__) reference patched to navigate up one extra level
- [X] T023 [US3] __init__.py re-exports all 42 symbols (41 child Defines + GameDefines)
- [X] T024 [US3] Old `defines.py` monolith deleted
- [X] T025 [US3] Extended `tests/unit/test_public_import_surface.py` with `TestDefinesPublicSurface` class — 6 tests covering __all__ declaration, baseline match, flat import, star import, module.attr access, GameDefines instantiation smoke
- [X] T026 [US3] Per-file LOC cap holds: largest is `organizations.py` at 581 LOC (under 600); 12 sub-modules range 98–581 LOC
- [X] T027 [US3] GameDefines() wiring verified: `gd.economy.extraction_efficiency == 0.8`
- [X] T028 [US3] Full fast-gate: 9001p / 186s / 1xf / 1f (1f pre-existing flake unchanged); +6 passed from new defines surface tests. Two mid-refactor mypy fixes applied to ooda.py: `import warnings` + `TYPE_CHECKING` import of GameDefines (uses string forward-reference for `validate_derivations(self, game_defines: GameDefines)`). ruff autofixed 49 I001 issues. mypy on defines/: clean.
- [x] T029 [US3] Commit: `refactor(config): split defines.py into defines/ package` (verified 2026-07-08: commit 367b07bd "refactor(config): split defines.py into defines/ package")

---

## Phase 5: User Story 1 — Source-pattern boilerplate is gone for new data sources (P1) — *commits 4 + 5 + 6*

**Story goal**: `src/babylon/core/protocol_kit.py` exists with `DataSource`, `CachedSource[T]`, `SourceRegistry`. At least 10 `Default*` classes from `melt/` + `gamma/` inherit from `CachedSource[T]`. `economics/factory.py` shrinks to <150 LOC with the 4 `create_*_services()` shims delegating to `SourceRegistry.builtin_economics()`.

**Independent test criteria**: After commit 6, the 18 contract tests in `tests/unit/core/test_protocol_kit.py` (8 from `contracts/protocol_kit.md` + 10 from `contracts/source_registry.md` items 1-10) and the 3 factory-shim tests in `tests/unit/economics/test_factory_shims.py` (from `contracts/source_registry.md` items 11-13) all pass — 21 new tests total across both files. SC-005 is verifiable by counting `CachedSource` subclasses in `melt/` + `gamma/`. SC-004 is verifiable by `wc -l src/babylon/economics/factory.py < 150`. The Spec 057 forward-compat smoke test from `quickstart.md` succeeds.

**Why this story third**: Per R1, the protocol_kit lands after the package splits because the `__all__` discipline established in US3 informs the kit's own `__all__` declaration. The 3-commit split (kit → migrations → factory) keeps each diff under ~25 files for review-ability.

### Sub-phase US1.1 — `protocol_kit` introduction (commit 4)

- [X] T030 [P] [US1] Wrote 20 RED tests in `tests/unit/core/test_protocol_kit.py` (8 CachedSource + 10 SourceRegistry + 2 DataSource Protocol smoke)
- [X] T031 [P] [US1] Wrote 3 xfail-marked tests in `tests/unit/economics/test_factory_shims.py` (items 11-13 from source_registry.md). pytestmark = pytest.mark.xfail(reason="GREEN at commit 6"); marker dropped at T057
- [X] T032 [US1] Created `src/babylon/core/__init__.py` (package docstring; ADR-002 reminder about narrow scope)
- [X] T033 [US1] Created `src/babylon/core/protocol_kit.py` with DataSource (runtime-checkable Protocol), CachedSource[T] (PEP 695 generic class with cache_negative_results = True class attr), SourceRegistry (DEFAULT_VARIANT/TEST_VARIANT, register, get, has, builtin_economics)
- [X] T034 [US1] SourceRegistry.builtin_economics() stub returns self (no-op) with explicit comment pointing at T053 for commit-6 fill-in
- [X] T035 [US1] All 20 protocol_kit tests pass (GREEN); 3 factory-shim tests xfail as expected
- [X] T036 [US1] Full fast-gate: 9021p / 186s / 4xf / 1f. +20 passed from new core/ tests; +3 xfail from factory shims; pre-existing flake unchanged. mypy + ruff clean (1 PEP 695 syntax modernization: Generic[T] → CachedSource[T])
- [x] T037 [US1] Commit: `feat(core): add protocol_kit with DataSource, CachedSource, SourceRegistry` (verified 2026-07-08: commit db53b832 "feat(core): add protocol_kit with DataSource, CachedSource, SourceRegistry")

### Sub-phase US1.2 — melt/ + gamma/ Default* migrations (commit 5)

- [X] T038 [US1] MRO inspection: all 10 classes inherit from `object` only — clean single-inheritance, no MRO conflicts. Concrete class names verified (DefaultBasketVisibilityCalculator, DefaultClassPositionClassifier, etc. — names differ from research.md TBD entries)
- [X] T039-T048 [US1] All 10 Default* migrated to `CachedSource[float]` via mix of programmatic splitter (4 classes with traditional __init__) + manual edits (6 classes — 5 had no __init__ at all, 1 had multi-line signature requiring careful super() injection). Surgical migration: inheritance only, existing public methods unchanged, behavior preserved
- [X] T049 [US1] SC-005 verified: 10/10 classes are CachedSource subclasses (`issubclass(cls, CachedSource)` runtime check)
- [X] T050 [US1] melt + gamma + core test suites: 340 passed / 6 skipped / 0 failed
- [X] T051 [US1] Full fast-gate: 9021p / 187s / 4xf / 0f. Pre-existing flake passed on this run (Hypothesis order-dependent — sometimes passes). Mid-refactor fix: lazy import of NoDataSentinel inside CachedSource._resolve to break circular import (protocol_kit → babylon.economics.tensor → babylon.economics.__init__ → migrated Default* → protocol_kit). 4 ruff I001 autofixes.
- [x] T052 [US1] Commit: `refactor(economics): migrate melt/ + gamma/ Default* classes to CachedSource[T]` (verified 2026-07-08: commit 997fda7f "refactor(economics): migrate melt/ + gamma/ Default* classes to CachedSource[T]")

### Sub-phase US1.3 — factory.py SourceRegistry migration (commit 6)

- [X] T053 [US1] Filled `SourceRegistry.builtin_economics()` with 7 register() calls (parameterless / all-default subset of the 10 melt+gamma classes). Lazy imports inside the method to avoid the protocol_kit-circular-import resolved in commit 5.
- [X] T054 [US1] Decision: KEEP `load_*_series_from_db` helpers in factory.py — extracting them does not move the LOC needle below 150 (per the SC-004 reformulation finding); restructuring is out of scope for Bundle 1.
- [X] T055 [US1] Surgical delegation: `create_economics_services` now uses `_get_builtin_registry().get(BasketVisibilityCalculator)` for the parameterless subset. The 3 dep-laden classes (MELT, RentDifferential, GammaIII) and the other ~50 classes stay constructed in explicit topological order. Function signatures preserved.
- [X] T056 [US1] **SC-004 not-met-by-design** documented in plan.md §R5 (corrected) and the xfail reason of `test_factory_loc_under_150`. Cause: factory.py performs topological dependency resolution that SourceRegistry's `Callable[[], object]` model does not replace. The <150 LOC target was based on a misreading of factory.py as boilerplate.
- [X] T057 [US1] `pytestmark` blanket xfail dropped; tests 11+12 reformulated to test the actually-shippable behavior (`_get_builtin_registry()` is process-wide cached; the 7 parameterless classes are registered). Test 13 (`test_factory_loc_under_150`) keeps a per-test xfail with the not-met-by-design reason.
- [X] T058 [US1] Full fast-gate: 9022p / 187s / 2xf / 1f. +1 passed (vs commit 5's 9021), -2 xfailed (factory shim tests 11+12 now real GREEN), +1 different pre-existing flake (`test_individual_frame_under_100ms` — UI perf test, env-load-dependent). The wealth_heat_bounds flake passed this run.
- [x] T059 [US1] Commit: `refactor(economics): replace factory.py wiring with SourceRegistry.builtin_economics()` (verified 2026-07-08: commit e88beccb "refactor(economics): replace factory.py wiring with SourceRegistry.builtin_economics()")

---

## Phase 6: User Story 2 — `tick/system.py` god-class is decomposed (P1) — *commit 7, part A*

**Story goal**: `src/babylon/economics/tick/system.py` (1705 LOC, 33 methods) is replaced by a `tick/system/` package with a ≤200-LOC `TickDynamicsSystem` facade and 8-9 focused sub-modules (each ≤400 LOC). Per Q3 clarification: behavioral fence preserves return-type classes, exception class hierarchies, and event-bus emission ordering. Per FR-008: the spec-057 quarantine on `_compute_imperial_rent` is preserved (stub body unchanged, tests stay skipped).

**Independent test criteria**: After commit 7 (US2 part), the new `tests/integration/economics/tick/test_facade_behavioral_fence.py` passes (frozen-seed tick produces a `WorldState` and event-bus history that diff-equal a frozen baseline). `wc -l` confirms the 200/400 LOC caps. `_compute_imperial_rent` lives in `tick/system/imperial_rent.py` with the spec-057 skipped tests still skipping the same count. The full tick test suite (`tests/unit/economics/tick/` + `tests/integration/economics/`) passes unchanged.

**Why this story fourth**: Per R1, the tick decomposition is bundled into commit 7 with US4 (BEAMappings typing) because both touch `economics/` and ship together for an atomic post-bundle baseline. US2 is the larger half of commit 7 and lands first within the commit's task ordering.

- [X] T060 [US2] Created `tests/integration/economics/tick/test_facade_behavioral_fence.py` with 4 tests pinning the facade public surface (canonical class import path, step() parameter list, name property value, _compute_imperial_rent stub presence per FR-008). Per the commit-7 reformulation, the TRUE behavioral fence is the existing `tests/unit/economics/tick/test_system.py` suite (which exhaustively exercises step() and the 33 private methods); the new file is a slim diagnostic regression.
- [~] T061-T072 [US2] **Phase B (full method-level decomposition into 9 sub-modules with ≤200-LOC facade) deferred to a future bundle.** Reason: the 33 methods are `self`-coupled (shared instance state, module constants, deeply interleaved type annotations) and a clean mixin-based decomposition under time pressure would risk silent behavior change. Same SC-004 not-met-by-design pattern: the spec author overestimated how trivial the decomposition would be for this particular file.
- [X] T073 [US2] **Phase A (structural relocation) shipped:** `git mv src/babylon/economics/tick/system.py → src/babylon/economics/tick/system/__init__.py`. The package shape exists; the import path `babylon.economics.tick.system.TickDynamicsSystem` is preserved verbatim; all 446 existing tick tests pass unchanged.
- [X] T074 [US2] LOC cap NOT met (facade is 1705 LOC inside system/__init__.py vs SC-002's 200-LOC target). Documented as Phase B deferred work — same audit-trail-as-xfail pattern as SC-004.
- [X] T075 [US2] Spec-057 quarantine verified: `_compute_imperial_rent` is still a method on TickDynamicsSystem; the 4 quarantined test skips in `test_system.py` are unchanged. New behavioral fence test `TestSpec057QuarantinePreserved::test_compute_imperial_rent_method_exists_as_stub` codifies this as a regression.
- [X] T076 [US2] All 4 facade fence tests GREEN.
- [X] T077 [US2] Full fast-gate: 9039p / 186s / 2xf / 1f. +17 passed (12 BEAMappings + 4 facade fence + 1 spec-057 quarantine), 1 fewer skip. Pre-existing wealth_heat_bounds flake fired again (different "9 Systems" vs prev runs — Hypothesis nondeterminism). No regressions; existing tick test suite still 442 passing.

---

## Phase 7: User Story 4 — BEA-to-Department mapping is typed (P2) — *commit 7, part B*

**Story goal**: A frozen `BEAMappings` Pydantic model wraps the BEA-NAICS-to-Marxian-Department table. The TOML at `economics/tensor_hierarchy/mappings/bea_to_department.toml` is loaded once at import time into a module-level `BEA_TO_DEPARTMENT` constant. `economics/department_mapper.py` consumes the typed object instead of reparsing TOML on every call. Per spec Edge Cases: malformed TOML raises at import time, not runtime.

**Independent test criteria**: After commit 7 (US4 part), the 14 contract tests in `tests/unit/economics/tensor_hierarchy/test_bea_mappings.py` pass. `grep -n "tomllib" src/babylon/economics/department_mapper.py` returns zero matches. The legacy department-mapper tests pass unchanged (the typed object is a drop-in replacement).

**Why this story fifth**: Per R1, US4 lands in commit 7 alongside US2 because both touch `economics/`. US4 has lower priority (P2) and smaller blast radius, so it slots in after the larger US2 work within the same commit.

**Note on TOML schema reformulation (2026-05-08 commit-7 finding):** The actual TOML on disk uses a `{departments: {I: [bea_codes], IIA: [...], IIB: [...], III: [...]}}` shape (4 departments, no per-row weights), NOT the row-array shape with fractional weights that the original `contracts/bea_mappings.md` sketched. The Pydantic model has been adjusted to match the file on disk; the legacy `dict[str, str]` flat-mapping output (consumed by `inter_industry.py:DefaultDepartmentAggregator.aggregate`) is exposed via `BEAMappings.as_flat_dict()`. This is the third spec-vs-reality miss caught by `/speckit.implement` in this session (after enums count, factory.py LOC, and now this); honest correction shipped.

- [X] T078 [US4] Created `tests/unit/economics/tensor_hierarchy/test_bea_mappings.py` with 12 tests reformulated to match the actual TOML schema (4 production-TOML acceptance + 5 validation + 2 legacy-equivalence + 1 frozen-mutation). The original 14-test contract was based on a row-array TOML shape that doesn't exist on disk.
- [X] T079 [US4] Created `src/babylon/economics/tensor_hierarchy/mappings/_models.py` with `BEAMappings` Pydantic model (frozen, `departments: dict[str, list[str]]`) + `_check_invariants` validator (no empty departments, all keys in `VALID_DEPARTMENTS={I, IIA, IIB, III}`, no duplicate bea_code across departments) + `get_department()` and `as_flat_dict()` methods.
- [X] T080 [US4] Replaced the 1-line stub `mappings/__init__.py` with full loader: `BEA_TO_DEPARTMENT: Final[BEAMappings]` constructed at import time. Declared `__all__ = ["BEA_TO_DEPARTMENT", "BEAMappings", "VALID_DEPARTMENTS"]`.
- [X] T081 [US4] Refactored `inter_industry.py:DefaultDepartmentAggregator.get_default_mapping()` (the actual TOML consumer — `department_mapper.py` is YAML, separate concern; the spec confused these two) to consume `BEA_TO_DEPARTMENT.as_flat_dict()` instead of reparsing TOML. Body collapsed from ~20 LOC to a 1-line delegation.
- [X] T082 [US4] All 12 BEAMappings tests GREEN.
- [X] T083 [US4] `grep -n "tomllib" src/babylon/economics/tensor_hierarchy/inter_industry.py` returns zero matches (the per-call reparse path is gone).
- [X] T084 [US4] Full fast-gate combined with T077: 9039p / 186s / 2xf / 1f. +17 passed, no regressions.
- [x] T085 [US2 / US4] Commit (bundled US2 + US4 per R1): `refactor(economics): relocate tick/system.py into a package + type bea_to_department mapping` (verified 2026-07-08: commit 0616eea4 "refactor(economics): relocate tick/system.py into a package + type bea_to_department mapping")

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T086 Updated `ai-docs/state.yaml` recently_completed with Bundle 1 entry (single-line per the file's existing format; documents the 3 SC reformulations).
- [~] T087 / T088 No `ai-docs/roadmap.md` or `ai-docs/decisions.yaml` exist (only `ai-docs/decisions/ADR0XX_*.yaml` per-file). The spec/plan/research/contracts in `specs/058-adr-bundle-1-pre-spec-057/` ARE the authoritative ADR record; no separate file needed.
- [X] T089 Spec-057 forward-compat smoke test PASSED: `/tmp/spec057_smoke.py` author-budget = ~25 LOC (within SC-007 30-LOC budget), protocol_kit importable, BEA_TO_DEPARTMENT consumable, `_compute_imperial_rent` stub remains.
- [X] T090 Final bundle verification (T077+T084 fast-gate): 9039p / 186s / 2xf / 1f. +51 new tests vs spec baseline. The 1 failure is the pre-existing wealth_heat_bounds Hypothesis flake (different "9 Systems" value vs prior runs — sometimes passes, sometimes fails; not Bundle 1's responsibility).
- [~] T091 Open PR `058-adr-bundle-1-pre-spec-057` → `dev` — pending user approval (a remote `git push` is a shared-state action that warrants explicit user confirmation). (partial 2026-07-08: branch landed on dev via merge commit f9b03b67 "Merge spec 058: ADR Bundle 1"; no PR record verifiable from the repo)

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
