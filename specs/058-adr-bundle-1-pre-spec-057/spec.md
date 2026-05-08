# Feature Specification: ADR Bundle 1 — structural prep for Spec 057

**Feature Branch**: `058-adr-bundle-1-pre-spec-057`
**Created**: 2026-05-08
**Status**: Draft
**Input**: User description: "Bundle 1: Implement ADR-001 (mechanical splits of `defines.py` + `enums.py` + OODA helper dedup), ADR-002 (`protocol_kit` + `SourceRegistry`), ADR-006 item 6.3 (decompose `tick/system.py` god-class), and ADR-006 item 6.5 (type the BEA-to-Department TOML mapping via Pydantic). The bundle's purpose is to land the structural refactors that spec 057-leontief-rent-integration would otherwise have to refactor around."

## Background and Motivation

The spec 057 work (End-to-End Leontief Imperial Rent Integration) will:

1. Add new injectable data sources (`PeripheryLaborCoefficientsSource`, `FinalDemandSource`, `IndustryToCountyAllocator`) to the existing `Protocol + Default*` pattern.
2. Replace the no-op stub `_compute_imperial_rent` inside `src/babylon/economics/tick/system.py` with a real Leontief pipeline.
3. Likely add a `LeontiefRentDefines` category to `src/babylon/config/defines.py` for calibration coefficients.
4. Consume the existing BEA-to-Department mapping in `economics/tensor_hierarchy/mappings/bea_to_department.toml` for the `dept_mapping` argument to `ProductionChainRentCalculator.calculate(...)`.

Each of those four touch points lands cleanly only if four corresponding architectural changes — captured in `docs/agents/adrs/` as ADR-001, ADR-002, ADR-006 item 6.3, and ADR-006 item 6.5 — are in place first. Without them, spec 057 would have to:

- Add `LeontiefRentDefines` into the existing 4157-line `defines.py` monolith, and a follow-up ADR-001 would then need to extract the new class into the package shape.
- Hand-roll the cache and factory wiring for `PeripheryLaborCoefficientsSource` and `FinalDemandSource`, and a follow-up ADR-002 would then need to migrate them to `CachedSource[T]` + `SourceRegistry`.
- Modify a function inside the 1705-line `tick/system.py` god-class, and a follow-up ADR-006.3 would then need to extract the modified code along with its 32 siblings.
- Pass the BEA-to-Department mapping as a raw `dict[str, str]` reparsed from TOML on every call, and a follow-up ADR-006.5 would then need to type and cache it.

Bundling these four refactors into one feature, ahead of spec 057, eliminates that re-work cost and lets spec 057 land in a clean target.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Source-pattern boilerplate is gone for new data sources (Priority: P1)

When a contributor (the spec 057 implementer in particular, but anyone authoring a new economic data source after this bundle lands) writes a new `Protocol + Default*` data source, they inherit the cache and the registry plumbing instead of hand-rolling them. The new source registers itself in one line; tests can substitute mocks via the same registry without monkey-patching.

**Why this priority**: This is the highest-leverage change in the bundle. Spec 057 introduces two new sources and one new allocator; without the kit, each one carries ~30 lines of cache + factory boilerplate that would land in spec 057's diff and then need to be removed by a follow-up ADR-002 pass. With the kit, spec 057's new sources are 5–10 lines each and inherit consistent caching semantics (LRU, `NoDataSentinel` for missing-data, year-keyed lookups).

**Independent Test**: A trivial new data source can be authored and registered without modifying `economics/factory.py`. The author writes one Protocol class, one `Default*` subclass that inherits from `CachedSource[T]` and implements only `_fetch(...)`, and one registry line. The new source then participates in the existing dependency injection flow with no other glue code.

**Acceptance Scenarios**:

1. **Given** `babylon.core.protocol_kit` exists with `CachedSource`, `SourceRegistry`, and `DataSource`, **When** a contributor writes a new `Default*` class that inherits from `CachedSource[float]`, **Then** the class needs no `__init__`, no manual cache management, and no `economics/factory.py` edit beyond a single registration line.
2. **Given** a `SourceRegistry` populated with the project's builtin economics implementations, **When** a test substitutes a mock for one Protocol with `registry.register(Foo, MockFoo, variant="test")`, **Then** the mock is used by callers that retrieve the source via the registry, and the real implementation is restored when the test finishes (test isolation preserved).
3. **Given** `economics/factory.py` after migration, **When** the file is opened, **Then** it is under 150 lines (down from 662), with the existing `create_*_services()` functions kept only as thin shims around `SourceRegistry.builtin_economics()`.

---

### User Story 2 - The `tick/system.py` god-class is decomposed into focused sub-components (Priority: P1)

When spec 057 modifies `_compute_imperial_rent`, the change lands inside a focused sub-module (`tick/system/imperial_rent.py` or similar) rather than inside a 1705-line monolith with 33 unrelated methods. Other contributors editing other concerns of the same tick-level system (national parameters, county distribution, crisis detection, smoothing, derived rates) work in their own sub-modules without merge collisions.

**Why this priority**: This is the second-highest-leverage change because spec 057's main code site is exactly inside this file. Every line spec 057 adds, removes, or modifies in `_compute_imperial_rent` is a line that ADR-006.3 would then need to migrate to the new package shape. Doing the decomposition first means spec 057 lands in the right module from day one.

**Independent Test**: After the decomposition, the public class `TickDynamicsSystem` is a facade of ~200 lines that composes named sub-components. Each sub-component lives in its own file under 400 lines. The full unit and integration test suites for tick dynamics pass unchanged; importing `TickDynamicsSystem` from its current import path still works.

**Acceptance Scenarios**:

1. **Given** `src/babylon/economics/tick/system.py` (1705 LOC, 33 methods on one class) and the existing tick test suite, **When** the file is replaced by a `tick/system/` package and the public facade is reassembled, **Then** every test in `tests/unit/economics/tick/` and `tests/integration/economics/` (the subset currently passing — the spec-057-quarantined tests stay quarantined) passes unchanged.
2. **Given** the new package, **When** the facade file is inspected, **Then** it is under 200 lines and consists primarily of construction (composing the sub-components) and pass-through methods.
3. **Given** the new package, **When** any single sub-component file is inspected, **Then** it is under 400 lines.
4. **Given** a contributor opens `_compute_imperial_rent` to modify it (as spec 057 will), **When** they navigate to the implementation, **Then** the method lives in a focused sub-module that contains only the imperial-rent step (and its private helpers), not the entire tick pipeline.

---

### User Story 3 - The two oversized barrel files are packages with stable public imports (Priority: P1)

When a contributor edits a single `*Defines` class or a single enum, the change touches only the relevant sub-module. Tests and consumers continue to import via the historical paths (`from babylon.config.defines import GameDefines`, `from babylon.models.enums import EdgeType`) without modification.

**Why this priority**: `defines.py` (4157 lines, 65 importers) and `enums.py` (1298 lines, 90 importers) are the #1 and #2 most-imported files in the project. Edits to either invalidate the bytecode cache for dozens of importers and slow `mypy --strict`. Spec 057 will likely add a new `LeontiefRentDefines` category; landing it inside the post-split package shape avoids growing the monolith further.

**Independent Test**: Every existing import path for symbols in `defines.py` and `enums.py` continues to resolve. `git grep -n "from babylon.models.enums import"` and `git grep -n "from babylon.config.defines import"` produce identical output before and after. `python -c "from babylon.config.defines import GameDefines; GameDefines()"` succeeds. No file in either new package exceeds 600 lines.

**Acceptance Scenarios**:

1. **Given** `src/babylon/models/enums.py` (1298 LOC, 25 enums), **When** the file is replaced by `src/babylon/models/enums/` package with category sub-files plus an `__init__.py` re-export, **Then** all existing `from babylon.models.enums import …` statements across the project continue to resolve and the full test suite passes unchanged.
2. **Given** `src/babylon/config/defines.py` (4157 LOC, 42 `*Defines` classes), **When** the file is replaced by `src/babylon/config/defines/` package with one file per category-cluster plus an `__init__.py` re-export, **Then** all existing `from babylon.config.defines import …` statements continue to resolve, `GameDefines()` instantiates with the same shape, and `pyproject.toml [tool.babylon]` loading still produces an identical `GameDefines` instance.
3. **Given** the two new packages, **When** any single category file is inspected, **Then** it is under 600 lines.

---

### User Story 4 - The BEA-to-Department mapping is typed (Priority: P2)

When code reads the BEA-NAICS to Marxian Department mapping, it consumes a typed Pydantic model rather than a raw dict reparsed from TOML on every call. Spec 057's pipeline (which feeds the BEA Use Table through the Leontief calculator and benefits from a typed `dept_mapping` argument) gets static-analysis safety on the mapping contents.

**Why this priority**: P2 because the current `dict[str, str]` representation works; this is a polish refactor that pairs naturally with spec 057's new use of the mapping. Lower priority than US1–3 because spec 057 can technically work with the untyped mapping; the typed mapping is a smaller follow-up benefit.

**Independent Test**: A new `BEAMappings` Pydantic model exists. `economics/department_mapper.py` consumes the typed object instead of reparsing TOML. The runtime behavior of `get_default_mapper()` is unchanged (same mappings produced); the type contract is now documented in code.

**Acceptance Scenarios**:

1. **Given** a typed `BEAMappings` model with `mappings: list[DepartmentMapping]` and per-entry constraints (`bea_code: str`, `department: Literal["I", "II", "III"]`, `weight: float ∈ [0,1]`), **When** the TOML file at `economics/tensor_hierarchy/mappings/bea_to_department.toml` is loaded once at import time, **Then** every existing call to `get_default_mapper()` produces the same `DepartmentMapper` instance (verified by structural equality on its mapping table).
2. **Given** a deliberately malformed TOML test fixture (e.g., `weight: 1.5`), **When** the loader is invoked, **Then** Pydantic raises `ValidationError` at import time rather than silently producing wrong numbers later.

---

### User Story 5 - The duplicated OODA helper exists in exactly one place (Priority: P3)

When a contributor needs `_compute_membership_overlap` (currently duplicated between `src/babylon/ooda/action_costs.py` and `action_effects.py`), they import from a single canonical location. No drift risk, no possibility of one copy being updated without the other.

**Why this priority**: P3 because this is independent of spec 057. The dedup is a small, low-risk cleanup that the file analyzer flagged with the `duplication` tag during knowledge-graph build. It belongs to the same spirit (Bundle 1 establishes good architectural hygiene) and is cheap enough to ship together.

**Independent Test**: After the change, exactly one definition of `_compute_membership_overlap` exists in the source tree (verified by `git grep -n "def _compute_membership_overlap" src/`). Both `action_costs.py` and `action_effects.py` import from the canonical location. Both modules continue to behave identically to their pre-refactor versions on the OODA action cost / effect test suites.

**Acceptance Scenarios**:

1. **Given** the OODA package, **When** `git grep -n "def _compute_membership_overlap" src/` is run, **Then** it returns exactly one match (in `src/babylon/ooda/_helpers.py`).
2. **Given** the OODA action-cost and action-effect tests, **When** they run after the dedup, **Then** they pass unchanged.

---

### Edge Cases

- A consumer that was importing from a sub-path that did not previously exist (e.g., `from babylon.config.defines.economy import EconomyDefines` for a sub-module that the old monolith didn't export through that path) → the new package may make that import work where it didn't before, which is harmless and intended.
- A `Default*` class that already inherits from a non-`object` base (multiple inheritance with `CachedSource[T]`) → MRO must be checked per class; classes that conflict get explicitly excluded from the bundle's migration scope (with their migration deferred to a follow-up).
- A test that monkey-patches a `Default*` constructor (passing `db_path=` directly) → after migration, the test must use `SourceRegistry.register(..., variant="test")` instead of constructor monkey-patching. Such tests are identified during migration and updated alongside the production change.
- The TOML file is missing or unreadable at import time → `BEAMappings` raises `FileNotFoundError` (or `tomllib.TOMLDecodeError`) at import, which is louder and more diagnostic than today's runtime failure.
- The `tick/system.py` decomposition relies on the spec-057 quarantine commit (`e2bf4c60`) being already in place — `_compute_imperial_rent` is currently a stub but its tests are skipped via `pytest.mark.skip("Blocked on spec 057-leontief-rent-integration; …")`. The decomposition preserves that skip and the stub.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST split `src/babylon/models/enums.py` into a `src/babylon/models/enums/` package with category sub-files and a re-exporting `__init__.py`, such that every existing `from babylon.models.enums import X` statement across the project continues to resolve unchanged.
- **FR-002**: System MUST split `src/babylon/config/defines.py` into a `src/babylon/config/defines/` package with category sub-files and a re-exporting `__init__.py`, such that every existing `from babylon.config.defines import X` statement continues to resolve unchanged and `GameDefines()` instantiates with the same shape.
- **FR-003**: System MUST consolidate `_compute_membership_overlap` into a single canonical implementation in `src/babylon/ooda/_helpers.py`, with both `action_costs.py` and `action_effects.py` importing from there.
- **FR-004**: System MUST introduce a new `src/babylon/core/protocol_kit.py` module exposing `DataSource` (Protocol marker), `CachedSource` (LRU + `NoDataSentinel` mixin/ABC), and `SourceRegistry` (type-keyed registry with optional `variant` discrimination).
- **FR-005**: System MUST migrate at least the data sources in `economics/melt/` and `economics/gamma/` to inherit from `CachedSource[T]`, dropping their hand-rolled `__init__` boilerplate.
- **FR-006**: System MUST replace the per-package `create_*_services()` factory functions in `economics/factory.py` with a single `SourceRegistry.builtin_economics()` registration entry-point, retaining the old function names as thin shims for one release cycle.
- **FR-007**: System MUST decompose `src/babylon/economics/tick/system.py` (1705 LOC, 33 methods) into a `src/babylon/economics/tick/system/` package containing a facade (≤200 lines) and focused sub-modules (each ≤400 lines), preserving the public class name `TickDynamicsSystem` and its public method signatures.
- **FR-008**: System MUST preserve the spec-057 quarantine on `_compute_imperial_rent`'s tests (the `pytest.mark.skip` markers committed in `e2bf4c60`) — the decomposition moves the stubbed method into a sub-module, but does not change its body and does not unskip its tests.
- **FR-009**: System MUST replace runtime TOML reparsing in `economics/department_mapper.py` with a typed `BEAMappings` Pydantic model loaded once at import time from `economics/tensor_hierarchy/mappings/bea_to_department.toml`.
- **FR-010**: System MUST verify that the full non-AI test suite (`mise run test:unit` plus `mise run test:int`) passes with the same final tally as the current `fix/dev-test-debt` baseline (8988 passed, 186 skipped, 1 xfailed) at every commit boundary in the bundle.
- **FR-011**: System MUST land each of the five user stories as one or more conventional commits, in the order: US5 (OODA dedup, smallest) → US3 (enums + defines splits) → US1 (protocol_kit + economics migration) → US2 (tick/system decomposition) → US4 (BEA mapping typing). This ordering minimizes inter-commit conflict by landing the lowest-blast-radius change first.
- **FR-012**: System MUST commit each user story under a feature branch (`058-adr-bundle-1-pre-spec-057`) and merge to `dev` only after the entire bundle is green, so the bundle ships as a coherent unit and Spec 057 can branch from a known-clean `dev` state.

### Key Entities

- **`enums/` package (replacing `enums.py`)**: A Python package holding the same 25 enum types as the historical monolith, organised into themed sub-modules (topology, social, consciousness, territory, events, legal, community), with an `__init__.py` that re-exports every symbol so historical import paths continue to resolve.
- **`defines/` package (replacing `defines.py`)**: A Python package holding the same 42 `*Defines` Pydantic models, with `GameDefines` as the assembler facade in `__init__.py` and category-clustered sub-modules (crisis, economy, consciousness, struggle, territory, ooda, state_apparatus, etc.).
- **`core/protocol_kit.py` (new)**: A small module exposing the `DataSource` marker Protocol, the `CachedSource[T]` cache mixin (LRU with FIFO eviction at `max_entries`, `NoDataSentinel` for missing-data results), and the `SourceRegistry` (type-keyed registry with `variant` discrimination for test substitution).
- **`SourceRegistry.builtin_economics()` (new method on the registry)**: A single entry-point that registers every existing `Default*` implementation in `economics/`. Replaces the seven `create_*_services()` functions in `economics/factory.py`.
- **`tick/system/` package (replacing `tick/system.py`)**: A package with a `TickDynamicsSystem` facade (≤200 LOC) and focused sub-modules — `national_parameters.py`, `county_distribution.py`, `crisis_detection.py`, `imperial_rent.py` (housing the current stub `_compute_imperial_rent`), and wired-in references to the existing `tick/smoothing.py` and `tick/derived_rates.py`.
- **`BEAMappings` (new Pydantic model)**: A frozen Pydantic model wrapping the BEA-to-Department mapping. Each entry is a `DepartmentMapping(bea_code: str, department: Literal["I", "II", "III"], weight: float ∈ [0,1])`. Loaded once at import time from `economics/tensor_hierarchy/mappings/bea_to_department.toml` and consumed by `department_mapper.py`.
- **`ooda/_helpers.py` (new module)**: The canonical home for `_compute_membership_overlap` and any future cross-OODA helpers that genuinely need to be shared between `action_costs.py` and `action_effects.py`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After the bundle lands, `mise run test:unit` and `mise run test:int` produce the same pass/skip/xfail counts as the current `fix/dev-test-debt` baseline (8988 passed, 186 skipped, 1 xfailed) — zero new failures and zero new skips beyond the spec-057 quarantine.
- **SC-002**: After the bundle lands, no file in `src/babylon/models/enums/` or `src/babylon/config/defines/` exceeds 600 lines, and no file in `src/babylon/economics/tick/system/` exceeds 400 lines (down from monoliths of 1298, 4157, and 1705 lines respectively).
- **SC-003**: After the bundle lands, `git grep -n "def _compute_membership_overlap" src/` returns exactly one match (down from two).
- **SC-004**: After the bundle lands, `src/babylon/economics/factory.py` is under 150 lines (down from 662), and the public `create_*_services()` function names are kept only as thin shims around `SourceRegistry.builtin_economics()`.
- **SC-005**: After the bundle lands, at least 10 `Default*` classes (drawn from `economics/melt/` and `economics/gamma/`) inherit from `CachedSource[T]` and have no hand-rolled `__init__` for cache management.
- **SC-006**: After the bundle lands, every historical import statement that exercised a symbol from `enums.py` or `defines.py` continues to resolve (verified by running `pytest --collect-only` and confirming the same number of test items collect as before, plus by `git grep` byte-equality comparisons of the old and new import lines).
- **SC-007**: After the bundle lands, a contributor implementing spec 057 can author the new `PeripheryLaborCoefficientsSource`, `FinalDemandSource`, and `IndustryToCountyAllocator` as ≤30-line files (each consisting of a one-line `class Default…(CachedSource[T])`, a `_fetch(...)` method, and a one-line `SourceRegistry` registration), with no manual cache management and no factory edits.
- **SC-008**: After the bundle lands, `mise run check` (the fast CI gate: lint + format + typecheck + test:unit) passes with zero new mypy/ruff findings introduced by the bundle's diff.
- **SC-009**: After the bundle lands, `BEAMappings.model_validate(...)` accepts every entry in the production TOML and rejects synthetic malformed fixtures (verified by a new unit test that constructs both kinds of fixture inline).

## Assumptions

- The `fix/dev-test-debt` branch (carrying the β fix, spec-057 quarantine, data-file restorations, Spec 052 contract alignment, and the C8c bifurcation routing fix) is already merged to `dev` before this bundle starts. Bundle 1's expected baseline tally (8988 passed, 186 skipped, 1 xfailed) is the post-merge state.
- Spec 057's `/speckit.specify` artifact at `specs/057-leontief-rent-integration/spec.md` is treated as the authoritative description of what spec 057 will need; FRs in this bundle are sized to make that spec's implementation cleanly fit into the post-bundle codebase.
- The four ADRs being implemented (`docs/agents/adrs/ADR-001`, `ADR-002`, `ADR-006` items 6.3 and 6.5) are the canonical decision records; this spec defers to those ADRs for the detailed technical shape (directory layouts, class signatures, code sketches) and limits itself to defining what success looks like and how this bundle must hold together as a coherent unit.
- ADR-003 (`System` ABC) and ADR-005 (`postgres_runtime` + `Simulation` decomposition) and ADR-006 items 6.1, 6.2, 6.4, 6.6 are explicitly out of scope for Bundle 1 — they are deferred to a follow-up Bundle 3 because they don't directly conflict with spec 057.
- ADR-004 (discriminated `TickEvent` union) is out of scope for Bundle 1 because it is independent of spec 057; it can ship before, after, or in parallel with this bundle.
- The 186 skipped tests after this bundle are the same 186 skipped tests after the `fix/dev-test-debt` merge — almost all are spec-057 quarantines that this bundle does not unskip. The bundle does not introduce new skips and does not unskip existing ones.

## Dependencies

- Existing module: `src/babylon/economics/tensor.py` — provides `NoDataSentinel`, used unchanged inside `CachedSource._resolve` to represent missing-data results.
- Existing module: `src/babylon/economics/factory.py` — its public `create_*_services()` function names are kept as thin shims; its body is replaced by a `SourceRegistry.builtin_economics()` call.
- Existing module: `src/babylon/economics/department_mapper.py` — consumes the new `BEAMappings` typed model in place of raw TOML.
- Existing TOML data file: `src/babylon/economics/tensor_hierarchy/mappings/bea_to_department.toml` — content unchanged; loader replaced.
- Existing test fixture infrastructure: `tests/conftest.py` and per-package conftests — unchanged.
- Existing CI gate: `mise run check` — must pass at every commit boundary.

## Out of Scope

- ADR-003: lifting `engine/systems/protocol.py:System` to a true ABC. Deferred to Bundle 3.
- ADR-004: discriminated `TickEvent` union and `models/events.py` split. Independent of spec 057; can ship separately at any time.
- ADR-005: decomposing `src/babylon/persistence/postgres_runtime.py` and `src/babylon/engine/simulation.py`. Both are large refactors that don't directly conflict with spec 057. Deferred to Bundle 3.
- ADR-006 item 6.1: `Scenario` ABC and migration of free-function scenario builders. Deferred to Bundle 3.
- ADR-006 item 6.2: splitting `economics/circulation/types.py` into a `types/` package. Deferred to Bundle 3.
- ADR-006 item 6.4: splitting `engine/systems/edge_transition.py` into `predicates.py` + `system.py`. Deferred to Bundle 3.
- ADR-006 item 6.6: auditing the 8 orphan schemas. Deferred to Bundle 3 (or a separate small docs spec).
- Migrating `economics/substrate/`, `economics/lifecycle/`, `economics/dynamics/`, `economics/credit/`, `economics/throughput/`, `economics/rent/`, `economics/working_day/`, `economics/tick/`, `economics/reserve_army/`, `economics/monetary/`, and `infrastructure/` `Default*` classes to `CachedSource[T]`. These are listed as opportunistic follow-up work in ADR-002's rollout. The bundle migrates only `melt/` and `gamma/` (the highest-leverage starting set, ~10 classes total).
- Implementing spec 057 itself. Bundle 1 prepares the ground; spec 057 lands on top of it.
- Performance benchmarking the new `CachedSource` cache against the previous hand-rolled implementations. The pattern is well-established and any micro-regression would be lost in noise; calibration is out of scope.

## Risks

- **Import-cycle risk during package splits**: Splitting `enums.py` and `defines.py` into packages can introduce circular imports if any module imports a category that itself imports another category at the top level. Mitigation: Each category sub-module imports only from `typing`, `pydantic`, and the project's own `models/types.py` (constrained types). Cross-category references (rare) are deferred via `TYPE_CHECKING` guards.
- **MRO conflict for `CachedSource` mixin**: A `Default*` class that already inherits from a non-`object` base may MRO-conflict with `CachedSource[T]`. Mitigation: Per-class inspection during migration; classes that conflict are explicitly excluded from this bundle's migration scope (left to a follow-up ADR).
- **`tick/system.py` decomposition breaking subtle internal couplings**: 33 methods on one class often share private state via `self._foo`. Mitigation: Extract sub-components incrementally (one or two at a time per commit), running the full tick test suite between each commit. The post-Bundle-1 expected baseline (8988 passed, 186 skipped, 1 xfailed) is the regression net.
- **Backward-compat shim drift in `economics/factory.py`**: Keeping the old `create_*_services()` function names as shims around `SourceRegistry.builtin_economics()` introduces a small temporary surface that may rot. Mitigation: A follow-up Bundle 3 task removes the shims once all callers (including spec 057) consume the registry directly.
- **Scope creep**: ADR-006 lists six items; this bundle picks two (6.3 and 6.5) and defers four. The temptation to "land all of 006 while we're touching it" should be resisted because 6.1 (Scenario ABC) and 6.2 (circulation/types split) and 6.4 (edge_transition split) and 6.6 (orphan schemas) don't unblock spec 057 and would inflate the bundle past a reviewable size.
