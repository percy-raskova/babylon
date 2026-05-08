# Feature Specification: ADR Bundle 2 — post-Spec-057 architectural cleanup

**Feature Branch**: `059-adr-bundle-2-post-spec-057`
**Created**: 2026-05-08
**Status**: Draft
**Input**: User description: "Bundle 2: implement the remaining ADRs after spec 057 lands. Covers ADR-003 (lift `engine/systems/protocol.py:System` Protocol into a `SystemBase` ABC with shared `_read`/`_write`/`_publish` helpers, migrate all 23 System implementations), ADR-004 (replace the 22-variant `Event` hierarchy with a Pydantic discriminated `TickEvent` union keyed on a `kind` Literal, split `models/events.py` into a package, delete `deserialize_event`), ADR-005 (decompose `persistence/postgres_runtime.py` at 1955 LOC and `engine/simulation.py` at 1048 LOC into focused IO/sub-component packages), and ADR-006 items 6.1 (Scenario ABC + migrate 9 free-function scenario builders), 6.2 (split `economics/circulation/types.py` at 1354 LOC), 6.4 (split `engine/systems/edge_transition.py` at 853 LOC into predicates + system), 6.6 (audit the 8 orphan JSON schemas)."

## Background and Motivation

ADR Bundle 1 (spec 058) lands the four refactors that spec 057 (End-to-End Leontief Imperial Rent Integration) would otherwise have to refactor around: package splits for `defines.py` and `enums.py`, the `protocol_kit` + `SourceRegistry` pattern, decomposition of `tick/system.py`, and typing of the BEA-to-Department mapping. Spec 057 then implements the Leontief integration on top of that clean target.

Bundle 2 collects the remaining ADRs from `docs/agents/adrs/` that did not need to ship before spec 057. They are independent enough to land in any order relative to each other (and relative to spec 057), but they share a common purpose: **finishing the architectural cleanup pass that the ADR set was designed to deliver, so the codebase reaches the steady-state shape that ADR-001 through ADR-006 collectively describe.**

The four ADRs in this bundle:

| ADR | Title | Estimated effort | Risk |
|---|---|---|---|
| **ADR-003** | Lift `System` Protocol into a true ABC with shared scaffolding | 1 d | Low |
| **ADR-004** | Discriminated `TickEvent` union replaces `deserialize_event` | 2 d | Medium |
| **ADR-005** | Decompose `postgres_runtime.py` and `engine/simulation.py` | 5 d | Medium |
| **ADR-006** items 6.1, 6.2, 6.4, 6.6 | Scenario ABC + remaining splits + orphan schemas | 3 d | Low |

Each ADR ships its own commits per the rollout sequence in its respective `docs/agents/adrs/ADR-NNN-*.md` document. This spec defines the bundle's shape, ordering, and what "Bundle 2 complete" looks like.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - God-class decomposition lifts the merge-conflict ceiling on persistence and orchestration (Priority: P1)

When two contributors edit different concerns of the persistence layer (one touches per-tick I/O, the other touches archival), they edit different files instead of colliding inside `postgres_runtime.py`. Same for the simulation orchestrator: lifecycle changes, observer-dispatch changes, and recovery changes each land in their own focused sub-module.

**Why this priority**: `postgres_runtime.py` (1955 LOC, 53 methods on one class) and `engine/simulation.py` (1048 LOC, 35 methods on one class) are the two largest god-classes left in the codebase. They concentrate critical-path responsibility (persistence + tick orchestration) into single-file edit bottlenecks. The decomposition is the highest-leverage change in Bundle 2 because it both unblocks parallel work and makes targeted unit testing tractable (stubbing one IO sub-component instead of instantiating the whole runtime).

**Independent Test**: After the decomposition, `from babylon.persistence import PostgresRuntime` and `from babylon.engine import Simulation` continue to resolve and produce instances with the same public method surface. The 150 unit + 10 contract persistence tests and the integration tests in `tests/integration/` pass unchanged. No file in either new package exceeds 400 LOC, and the facade files for both `PostgresRuntime` and `Simulation` are under 200 LOC.

**Acceptance Scenarios**:

1. **Given** the existing public API surface of `PostgresRuntime` (53 methods covering both `RuntimePersistence` and `PostgresRuntimeExtensions` Protocols), **When** the file is replaced by a `persistence/postgres_runtime/` package with a thin facade composing focused IO sub-components, **Then** `isinstance(PostgresRuntime(...), RuntimePersistence)` and `isinstance(..., PostgresRuntimeExtensions)` both still return `True`, and every existing call site continues to work without modification.
2. **Given** the existing public API of `Simulation` (35 methods covering tick pipeline, observer dispatch, history, error recovery, lifecycle), **When** the file is replaced by an `engine/simulation/` package with a thin facade, **Then** `mise run sim:run` and `mise run sim:trace` both succeed end-to-end and produce byte-identical output to a pre-decomposition baseline (deterministic seeds).
3. **Given** the new packages, **When** any single sub-component file is inspected, **Then** it is under 400 LOC; **When** either facade file is inspected, **Then** it is under 200 LOC.
4. **Given** a contributor wants to test the per-tick IO logic in isolation, **When** they author a new test, **Then** they can stub `PostgresTickIO` directly without instantiating the full `PostgresRuntime` (the sub-components are independently constructable and testable).

---

### User Story 2 - Mypy catches event-handling bugs at typecheck time (Priority: P1)

When a contributor adds a new `TickEvent` variant or removes an existing one, every observer's `match event:` statement is forced (by `assert_never` exhaustiveness) to acknowledge the change at typecheck time, not at runtime. The hand-rolled `deserialize_event` switch — which currently silently drops unknown variants and which CLAUDE.md flags as a gotcha — is replaced by Pydantic's built-in discriminated-union dispatch.

**Why this priority**: P1 because event handling is one of the two biggest known correctness gaps in the project (the other being the imperial-rent stub, which spec 057 fixes). CLAUDE.md "Common Gotchas" calls out two event-related issues: `WorldState.events` is per-tick (not cumulative — already fixed) and `mypy` misses Pydantic attribute errors (this is what ADR-004 addresses). The discriminated union is the canonical Pydantic 2 pattern for sum types and gets the typechecker to do the work currently delegated to runtime hope.

**Independent Test**: All 22 Event subclasses carry a unique `kind: Literal["..."]` field. `TickEvent = Annotated[Union[...], Field(discriminator="kind")]` is defined. `WorldState.events: list[TickEvent]` validates correctly: passing a mismatched dict raises `ValidationError`. `git grep deserialize_event` returns zero results after the final commit. Every observer's `match event:` statement type-checks with exhaustiveness verified.

**Acceptance Scenarios**:

1. **Given** all 22 Event subclasses, **When** they are inspected, **Then** each carries a unique `kind: Literal["..."]` field and shares a common frozen `_EventBase`.
2. **Given** the discriminated union, **When** an event dict with a missing or mismatched `kind` field is passed to `TypeAdapter(TickEvent).validate_python(...)`, **Then** Pydantic raises `ValidationError` with a clear discriminator-mismatch message.
3. **Given** an observer that uses `match event:` over the union, **When** a hypothetical new variant is added without updating the observer, **Then** mypy flags the missing `case` (via the `assert_never` exhaustiveness pattern) at typecheck time, not at runtime.
4. **Given** an integration test that round-trips events through `to_graph()` / `from_graph()`, **When** the test runs after the refactor, **Then** the events deserialize via Pydantic's `TypeAdapter` (no `deserialize_event` shim) and reconstitute as the correct subclasses.

---

### User Story 3 - All 23 System implementations share scaffolding and the schema-bug-masking pattern is gone (Priority: P2)

When a contributor authors a new System (or modifies an existing one), they inherit a `SystemBase` ABC that supplies the `_read(graph, node_id, key, required=True)` helper. Required attributes that are missing on a graph node raise `KeyError` at the read site instead of being silently coerced to a default value (the `data.get("field", 0.0)` pattern that CLAUDE.md "Common Gotchas" explicitly warns about).

**Why this priority**: P2 because this is mostly mechanical (23 files migrated; minimal blast radius) and doesn't unblock any specific feature. The wins are real but indirect: surfacing schema bugs at the read site (instead of producing wrong numbers downstream) and reducing per-System boilerplate. The change is low-risk because the existing 23 Systems already conform to the `System` Protocol; the ABC is a strict superset.

**Independent Test**: All 23 System classes inherit from `SystemBase` and use `self._read` / `self._write` / `self._publish` instead of direct `graph.nodes[id][key] = ...`. `engine/systems/protocol.py` either re-exports from the new `base.py` or is removed without breaking imports. The full test suite passes unchanged. At least 5 instances of `data.get("X", default)` masking are converted to `_read(..., required=True)`; the resulting `KeyError`s either fail loudly (revealing real bugs that were previously hidden) or trigger explicit data-shape fixes documented in the migrating commit.

**Acceptance Scenarios**:

1. **Given** the historical `engine/systems/protocol.py:System` Protocol, **When** the new `engine/systems/base.py:SystemBase` ABC is introduced and `System` is re-exported alongside it, **Then** `isinstance(StubSystem(), System)` continues to return `True` (Protocol structural typing preserved for tests/mocks) and `isinstance(StruggleSystem(...), SystemBase)` returns `True` (post-migration).
2. **Given** a graph node that legitimately requires a `wealth` attribute, **When** a System reads it via `self._read(graph, node_id, "wealth", required=True)` and the attribute is missing, **Then** the System raises `KeyError` with a diagnostic naming both the attribute and the node, instead of silently substituting `0.0`.
3. **Given** all 23 migrated Systems, **When** the existing System unit tests run, **Then** they pass unchanged, except for any test that was implicitly relying on silent default coercion — those tests are updated to provide the required attribute, and the change is documented in the migrating commit message.

---

### User Story 4 - New scenarios drop in as one class, not three free functions in two files (Priority: P2)

When a contributor authors a new simulation scenario (e.g., a new geographic baseline or a new contradiction tree), they subclass a `Scenario` ABC and implement three abstract methods. The subclass auto-registers itself via `__init_subclass__`, and `mise run sim:run --scenario <name>` discovers it without any registry edit.

**Why this priority**: P2. The existing 9 free-function scenario builders work; this is a quality-of-life improvement for future scenario authoring. Becomes more valuable once spec 057 lands and stakeholders start authoring more scenarios to explore Leontief calibration.

**Independent Test**: All 9 historical scenario builders (currently free functions in `engine/scenarios.py` and `engine/scenarios_wayne_county.py`) are ported as `Scenario` subclasses with their old free-function names retained as thin shims. `mise run sim:run --scenario <existing_scenario_name>` produces byte-identical baseline output to a pre-refactor run for at least one named scenario.

**Acceptance Scenarios**:

1. **Given** the existing 9 free-function scenario builders, **When** they are converted to `Scenario` subclasses with `build_territories`, `build_classes`, `build_relationships` abstract methods implemented, **Then** the existing free-function names continue to work (kept as shims that wrap the subclass `.build()` call).
2. **Given** a contributor wants to add a new scenario, **When** they author a new `Scenario` subclass, **Then** the subclass auto-registers via `__init_subclass__` and is discoverable by `mise run sim:run --scenario <new_name>` without manual registry edits.
3. **Given** the migrated scenarios, **When** `mise run sim:trace 100` runs against a deterministic-seed baseline before and after, **Then** the trace CSV is byte-identical.

---

### User Story 5 - Two more oversized files become packages (Priority: P3)

`economics/circulation/types.py` (1354 LOC, 19 Pydantic types covering 3 distinct concepts) and `engine/systems/edge_transition.py` (853 LOC mixing Pydantic predicate models with the System class) follow the package-split pattern established by Bundle 1 for `enums/` and `defines/`. Each becomes a package with thematic sub-files and a re-exporting `__init__.py`.

**Why this priority**: P3. These are the two remaining oversized files identified in the knowledge graph that didn't make Bundle 1's cut. The split is purely mechanical, follows an established pattern, and the existing tests should pass unchanged. The win is per-category test isolation and faster mypy.

**Independent Test**: Every existing import of a symbol from either file continues to resolve (verified by `git grep` byte-equality before/after). No file in either new package exceeds 400 LOC.

**Acceptance Scenarios**:

1. **Given** `economics/circulation/types.py` (1354 LOC, 19 types), **When** it is replaced by `economics/circulation/types/` package with `flow.py` / `fixed_capital.py` / `crisis.py` / `_enums.py` sub-files, **Then** every existing `from babylon.economics.circulation.types import X` resolves unchanged.
2. **Given** `engine/systems/edge_transition.py` (853 LOC), **When** it is replaced by `engine/systems/edge_transition/` package with `predicates.py` (Pydantic models) and `system.py` (the System class), **Then** the System class continues to be importable from `engine/systems/edge_transition` and the predicate models are accessible via `engine/systems/edge_transition.predicates`.

---

### User Story 6 - Orphan schemas earn their place or stop adding noise (Priority: P3)

The 8 JSON schemas in `src/babylon/schemas/` that have no `$ref` cross-references in the knowledge graph (`culture`, `ideology`, `institution`, `persona`, `sentiment`, `slice-spec`, `narrative_frame`, plus one more from the validation warnings) are audited. Each is either: (a) documented as standalone-by-design with a clarifying comment in the corresponding Pydantic model, (b) confirmed unused at runtime and deleted with a rationale entry in `ai-docs/decisions.yaml`, or (c) updated with a `description` field clarifying its role.

**Why this priority**: P3. Pure documentation cleanup. No runtime impact unless one of the schemas turns out to actually be used at runtime (in which case the audit reveals that and the schema gets a corresponding `defines_schema` edge added to the knowledge graph).

**Independent Test**: After the audit, every orphan schema either has a documented standalone status, a `defines_schema` edge to a Pydantic counterpart, or has been deleted with rationale. The next `/understand-anything:understand` knowledge-graph rebuild produces zero new orphan-schema validation warnings.

**Acceptance Scenarios**:

1. **Given** the 8 orphan schemas, **When** each is audited, **Then** for each schema there exists exactly one of: (a) a `# standalone schema, no $ref` comment in the Pydantic counterpart at `models/entities/<name>.py`, (b) a deletion commit with rationale in `ai-docs/decisions.yaml`, or (c) a `description` field added to the schema and the corresponding Pydantic model.
2. **Given** the post-audit state, **When** the knowledge graph is rebuilt, **Then** no new orphan-schema validation warnings appear.

---

### Edge Cases

- A System that already inherits from a non-`object` base (multiple inheritance with `SystemBase`) → MRO must be checked per System; if any conflict, that System keeps its existing `__init__` and explicitly calls `super().__init__(defines)` first; the migration commit notes the pattern.
- A `Default*` class that already inherits from `CachedSource[T]` (post-Bundle-1) and now needs migration to `SystemBase` is not in scope — Systems and Sources are different abstractions; this confusion would be a design error, not an edge case.
- An Event subclass currently constructed via `Event(event_type="X", ...)` rather than the specific variant — those call sites must change to construct the variant directly. Audited during step 1 of ADR-004's rollout; identified call sites are listed in the rollout commit.
- An observer using `match event:` over the discriminated union without a `case _: assert_never(event)` clause → mypy will not catch a missing variant. The migration must add the `assert_never` to every existing match statement in `observers/`.
- The `archival` IO sub-component of `PostgresRuntime` is currently stubbed (per project memory: "Archival pipeline (Phase 8) is stub-only — `NotImplementedError` for all 4 functions"). The decomposition extracts the stub into `archival_io.py` without changing its body or unstubbing it.
- The `_session_action_history` and `_session_trap_state` module-level state in `web/game/engine_bridge.py` is not part of `engine/simulation.py` — `Simulation` decomposition does not affect it.
- One or more orphan schemas may be required by an ETL or scenario file that lives outside `src/babylon/` (e.g., in `tools/` or `scripts/`). The audit must check `git grep` across the whole repo, not just `src/`.
- Spec 057 is assumed to have landed before Bundle 2 starts — the spec-057 quarantine markers in tests are still in place, but the orphaned imperial-rent tests have been replaced with new tests that use the Leontief pipeline. If spec 057 has not yet shipped when Bundle 2 starts, ADR-005's `Simulation` decomposition still runs cleanly because the snapshot bridge in `simulation.py` reads `phi_hour` either way (a `0.0` stub or a real Leontief value).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST replace `src/babylon/persistence/postgres_runtime.py` (1955 LOC, 53 methods) with a `src/babylon/persistence/postgres_runtime/` package containing a `PostgresRuntime` facade (≤200 LOC) and focused IO sub-modules — at minimum `_pool.py`, `tick_io.py`, `archival_io.py`, `spatial_io.py`, `community_io.py`, `trace_io.py` — each ≤400 LOC.
- **FR-002**: System MUST replace `src/babylon/engine/simulation.py` (1048 LOC, 35 methods) with a `src/babylon/engine/simulation/` package containing a `Simulation` facade (≤200 LOC) and focused sub-modules — at minimum `orchestrator.py`, `observer_dispatch.py`, `lifecycle.py`, `error_recovery.py` — each ≤400 LOC.
- **FR-003**: System MUST preserve the public import paths `from babylon.persistence import PostgresRuntime` and `from babylon.engine import Simulation` (and every other historical import path that exercised symbols in either file) without modification.
- **FR-004**: System MUST add a unique `kind: Literal["..."]` field to every Event subclass and define `TickEvent = Annotated[Union[...], Field(discriminator="kind")]` covering all variants.
- **FR-005**: System MUST update `WorldState.events` to type-check as `list[TickEvent]`, with Pydantic validating discriminator dispatch on every assignment.
- **FR-006**: System MUST replace the hand-rolled `deserialize_event` switch with a `TypeAdapter(TickEvent).validate_python(...)` call (or delete `deserialize_event` entirely once no caller remains, replacing each call site with the `TypeAdapter` directly).
- **FR-007**: System MUST split `src/babylon/models/events.py` (1011 LOC) into a `src/babylon/models/events/` package mirroring the package shape established by Bundle 1, with no file >300 LOC and a re-exporting `__init__.py`.
- **FR-008**: System MUST update every observer that uses `match event:` over the union to include a `case _: assert_never(event)` exhaustiveness clause; observers using `if isinstance(...)` chains MUST cover every variant explicitly.
- **FR-009**: System MUST introduce a `src/babylon/engine/systems/base.py:SystemBase` ABC with abstract `step(graph, services, context)` and shared `_read(graph, node_id, key, *, required=False)` / `_write(graph, node_id, key, value)` / `_publish(services, event)` helpers, and migrate all 23 System implementations to inherit from it.
- **FR-010**: System MUST preserve the `engine/systems/protocol.py:System` Protocol for structural typing (tests, mocks) — either re-exported from `base.py` or maintained alongside the ABC. `isinstance(obj, System)` MUST continue to return `True` for any object that satisfies the Protocol shape.
- **FR-011**: System MUST audit every `data.get("X", default)` pattern in `src/babylon/engine/systems/` and convert at least 5 instances to `self._read(..., required=True)` where the field is meant to always be present, documenting the conversions in the migrating commit message.
- **FR-012**: System MUST introduce a `src/babylon/engine/scenarios/base.py:Scenario` ABC and port the 9 historical scenario builders (currently free functions in `scenarios.py` and `scenarios_wayne_county.py`) as subclasses, retaining the historical free-function names as thin shims.
- **FR-013**: System MUST replace `src/babylon/economics/circulation/types.py` (1354 LOC, 19 types) with an `economics/circulation/types/` package, no file >400 LOC.
- **FR-014**: System MUST replace `src/babylon/engine/systems/edge_transition.py` (853 LOC) with an `engine/systems/edge_transition/` package containing `predicates.py` (Pydantic models) and `system.py` (the System class, inheriting from `SystemBase` per FR-009).
- **FR-015**: System MUST audit each of the 8 orphan JSON schemas (`schemas/entities/{culture,ideology,institution,persona,sentiment}.schema.json`, `schemas/slice-spec.schema.json`, `schemas/narrative/narrative_frame.schema.json`, plus any others flagged by the next knowledge-graph rebuild) and resolve each to one of: documented standalone status, deletion with rationale in `ai-docs/decisions.yaml`, or addition of a `description` field clarifying its role.
- **FR-016**: System MUST verify that the full non-AI test suite (`mise run test:unit` + `mise run test:int`) passes with the same final tally as the post-Spec-057 baseline at every commit boundary in the bundle, allowing tally changes only when explicitly justified by a new test added by spec 057 or by this bundle.
- **FR-017**: System MUST land each ADR (or each ADR-006 sub-item) as one or more conventional commits, in any order that the implementer judges minimizes inter-ADR conflict — the four ADRs are mutually independent in their file scopes (postgres_runtime ≠ events ≠ systems ≠ scenarios ≠ circulation/types ≠ edge_transition ≠ orphan schemas), so parallel work is permitted.

### Key Entities

- **`postgres_runtime/` package (replacing `postgres_runtime.py`)**: A package holding the same public class `PostgresRuntime` as a facade, composed of focused IO sub-components — `PostgresTickIO`, `PostgresArchivalIO`, `PostgresSpatialIO`, `PostgresCommunityIO`, `PostgresTraceIO` — each in its own file under 400 LOC. Both `RuntimePersistence` and `PostgresRuntimeExtensions` Protocols continue to be satisfied by the facade.
- **`simulation/` package (replacing `simulation.py`)**: A package holding the same public class `Simulation` as a facade, composed of focused sub-components — `SimulationOrchestrator`, `ObserverDispatcher`, `SimulationLifecycle`, `SimulationRecovery` — each in its own file under 400 LOC. Public API for embedders (UI, web backend, tests) is preserved.
- **`SystemBase` (new ABC)**: An abstract base class for all 23 simulation Systems, providing shared read/write/publish helpers. The companion `runtime_checkable Protocol System` is retained for structural typing in tests and mocks.
- **`TickEvent` (new discriminated union)**: A Pydantic discriminated `Annotated[Union[...], Field(discriminator="kind")]` covering every Event subclass, keyed on a unique `kind: Literal["..."]` field per variant. Replaces the implicit dispatch in the deleted `deserialize_event` function.
- **`events/` package (replacing `events.py`)**: A package holding the 22 Event subclasses organised into themed sub-modules (`economic.py`, `consciousness.py`, `territory.py`, `system.py`) plus a `_base.py` with `_EventBase` and the `TickEvent` union assembly.
- **`Scenario` (new ABC)**: An abstract base class for scenario builders, with abstract `build_territories`, `build_classes`, `build_relationships` methods and a default `build()` composition. Subclasses auto-register via `__init_subclass__`.
- **`circulation/types/` package**: Holds the 19 Pydantic types previously in the 1354-line monolith, organised by concept: `flow.py` (CircuitState, TurnoverProfile, AnnualSurplusValue, ReproductionBalance, ReproductionAnalysis), `fixed_capital.py` (FixedCapitalItem, DepreciationFundState, MoralDepreciation, InventoryState), `crisis.py` (RealizationCrisis, DisproportionalityCrisis, CirculationCrisisAssessment, CirculationCrisisState), `_enums.py` (CapitalForm, ReplacementCyclePosition, InventoryDiagnosis, CrisisSeverity).
- **`edge_transition/` package**: Holds the predicate Pydantic models (`PredicateCondition`, `CompoundPredicate`, `EdgeModeTransition`) in `predicates.py`, and the `EdgeTransitionSystem` class (inheriting from `SystemBase` per FR-009) in `system.py`.
- **Orphan schema audit ledger**: A new section in `ai-docs/decisions.yaml` (or an entry per schema in the existing decisions ledger) recording, for each of the 8 orphan schemas, the disposition (kept-standalone / deleted / annotated) and the rationale.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After the bundle lands, `mise run test:unit` and `mise run test:int` produce a pass/skip/xfail tally that differs from the pre-Bundle-2 baseline only by tests intentionally added by this bundle (e.g., new `SystemBase._read(required=True)` failure tests) or by spec 057 (new Leontief tests). Zero unintended new failures.
- **SC-002**: After the bundle lands, no file in `src/babylon/persistence/postgres_runtime/`, `src/babylon/engine/simulation/`, `src/babylon/economics/circulation/types/`, or `src/babylon/engine/systems/edge_transition/` exceeds 400 LOC, and both `PostgresRuntime` and `Simulation` facade files are under 200 LOC.
- **SC-003**: After the bundle lands, `git grep -n "def deserialize_event" src/` returns zero matches.
- **SC-004**: After the bundle lands, every observer's `match event:` statement includes an `assert_never(event)` exhaustiveness check, verified by mypy passing under `--strict` on the affected files.
- **SC-005**: After the bundle lands, all 23 System classes inherit from `SystemBase`, verified by `python -c "from babylon.engine.systems import …; assert issubclass(…, SystemBase)"` for each.
- **SC-006**: After the bundle lands, at least 5 previously-silent `data.get("X", default)` patterns are converted to `_read(..., required=True)`. The conversion either fixes a previously-hidden bug (revealed when the field was actually missing in some scenario) or is documented as a defensive read of a field that should always be present.
- **SC-007**: After the bundle lands, `mise run sim:run` against any of the 9 ported scenarios produces byte-identical output to a pre-Bundle-2 baseline run with the same seed, for at least one named scenario verified at full length.
- **SC-008**: After the bundle lands, every orphan schema flagged by the latest knowledge-graph rebuild is resolved (none remain as orphans without a documented disposition).
- **SC-009**: After the bundle lands, `mise run check` passes with zero new mypy/ruff findings introduced by the bundle's diff.
- **SC-010**: After the bundle lands, a contributor authoring a new Event variant adds three things — the subclass with its `kind: Literal["..."]` field, an entry in `models/events/<category>.py`, and a re-export from `models/events/__init__.py` — and is forced by mypy `assert_never` exhaustiveness to update every `match event:` in observers; the typecheck-time enforcement is verifiable by intentionally adding a stub variant and confirming mypy errors before any observer is updated.

## Assumptions

- Bundle 1 (spec 058) is merged to `dev` before Bundle 2 starts. Bundle 2's expected pass/skip baseline is the post-Bundle-1 (post-Spec-057) state.
- Spec 057 is also merged to `dev` before Bundle 2 starts. The Leontief pipeline is in place and the orphaned imperial-rent tests have been replaced by Leontief-pipeline tests; the spec-057 quarantine markers may or may not still be present (spec 057 implementer's choice per FR-009 of that spec).
- The four ADRs in this bundle (`docs/agents/adrs/ADR-003`, `ADR-004`, `ADR-005`, `ADR-006` items 6.1, 6.2, 6.4, 6.6) are the canonical decision records; this spec defers to them for the detailed technical shape and limits itself to defining the bundle's shape and ordering.
- The four ADRs are mutually independent in file scope (no two ADRs touch the same source file). They can be implemented in any order or in parallel by separate contributors. The ordering specified in this spec is a *suggestion* (ADR-005 first because it's the largest, ADR-004 second, ADR-003 third, ADR-006 items last) but not a hard ordering.
- The `archival` IO sub-component of `PostgresRuntime` remains stubbed (per project memory: "Archival pipeline (Phase 8) is stub-only"). Bundle 2 extracts the stub into its own file but does not unstub it; that is a separate feature spec.
- The Pydantic 2 discriminated-union pattern (`Annotated[Union[...], Field(discriminator="...")]`) is the canonical idiom and is well-supported in the project's Pydantic version (2.x already in use per `pyproject.toml`).
- `engine/systems/edge_transition.py`'s split into `predicates.py` + `system.py` follows the same shape as ADR-001's package splits and inherits from `SystemBase` per FR-009; this means ADR-006.4 implicitly depends on ADR-003 having landed first (or being in the same commit chain).
- The 9 scenario builders currently in `engine/scenarios.py` and `engine/scenarios_wayne_county.py` produce deterministic baselines that can be byte-compared. If any scenario is non-deterministic at the per-byte level, the SC-007 byte-equality check is relaxed to numeric-equality with a documented tolerance.
- The 8 orphan schemas listed in this spec are the same 8 listed in ADR-006 item 6.6. If a knowledge-graph rebuild between Bundle 1 and Bundle 2 reveals additional orphans, those are added to the audit scope.

## Dependencies

- Spec 058 (ADR Bundle 1) — merged to `dev` before Bundle 2 starts.
- Spec 057 (Leontief Imperial Rent Integration) — merged to `dev` before Bundle 2 starts.
- ADR documents at `docs/agents/adrs/ADR-003-system-abc.md`, `ADR-004-discriminated-event-union.md`, `ADR-005-god-class-decomposition.md`, `ADR-006-cleanup-batch.md` — the technical contracts for each ADR.
- Existing 150 unit + 10 contract persistence tests — the regression net for ADR-005 Part A.
- Existing integration tests in `tests/integration/` — the regression net for ADR-005 Part B.
- Existing observer tests in `tests/unit/engine/observers/` — must be updated for ADR-004's `assert_never` exhaustiveness.
- Existing scenario tests in `tests/integration/test_scenario_*.py` — the regression net for ADR-006.1.
- The knowledge graph at `.understand-anything/knowledge-graph.json` — the source of orphan-schema flags for ADR-006.6.

## Out of Scope

- Implementing additional ADRs not in this bundle's scope — there are no further proposed ADRs in `docs/agents/adrs/` after Bundles 1 and 2 land. Future ADRs would be authored separately.
- Unstubbing the `PostgresArchivalIO` Phase 8 pipeline (Parquet export, R2 upload). Bundle 2 only extracts the stub into its own file; the archival feature itself is a separate spec.
- Removing the `engine/systems/protocol.py:System` Protocol entirely. Bundle 2 keeps it alongside `SystemBase` to preserve structural typing for tests/mocks.
- Migrating `Default*` classes that did not migrate in Bundle 1 (the `economics/substrate/`, `lifecycle/`, `dynamics/`, `credit/`, `throughput/`, `rent/`, `working_day/`, `tick/`, `reserve_army/`, `monetary/`, and `infrastructure/` packages) to `CachedSource[T]`. Those are listed as opportunistic follow-up work in ADR-002's rollout and are not part of Bundle 2.
- Refactoring `web/game/engine_bridge.py` (which holds module-level `_session_action_history` and `_session_trap_state`). Bundle 2 does not touch the web layer.
- Performance benchmarking the post-decomposition runtime against pre-decomposition baselines beyond the byte-equality check in SC-007. Composition adds one extra method dispatch per call; that is negligible at simulation tick frequency and not worth a benchmark.
- Updating `ai-docs/decisions.yaml` with full ADR records for Bundles 1 and 2 (per the README convention "Once implemented, each ADR's outcome is summarized into a YAML entry in `ai-docs/decisions.yaml`"). That documentation work is a separate small commit at the end of each bundle.

## Risks

- **Critical-path churn for ADR-005**: Persistence and orchestration are core. Any test gap during decomposition risks production bugs. Mitigation: tag the pre-Bundle-2 commit as `pre-bundle-2-baseline`, snapshot baseline metrics with `mise run qa:regression-generate`, run the full integration suite after every ADR-005 commit, and compare a small-scale `sim:trace` run byte-for-byte before merging.
- **Discriminator-field migration risk for ADR-004**: Variants that historically built their `event_type` field dynamically (rather than as a hardcoded `Literal[...]`) need the literal added. Mitigation: a pre-flight audit identifies dynamic `event_type` constructions; each is converted to construct the specific variant directly, and the audit's findings ship in the rollout commit message.
- **MRO conflict for `SystemBase` (ADR-003)**: Any System that already inherits from a non-`object` base may conflict. Mitigation: per-System inspection during migration; conflicting Systems keep their existing `__init__` and explicitly call `super().__init__(defines)`.
- **Hidden bug surfacing on `_read(required=True)` migration (ADR-003 + FR-011)**: Converting a `data.get("field", 0.0)` to `_read("field", required=True)` may reveal a real bug where the field was actually missing in some scenarios. Mitigation: this is the *intended* outcome — the bug surfaces, gets fixed in the same commit, and the test suite gains a regression check for that scenario. Document each such fix in the migrating commit message.
- **Scenario subclass auto-registration via `__init_subclass__` is mildly magic (ADR-006.1)**: Some teams prefer explicit registration. Mitigation: the magic is contained to the `Scenario` base class; the alternative (an explicit `register_scenario(...)` call per subclass) can be substituted if reviewers push back, with no downstream impact.
- **Orphan-schema audit may surface a runtime usage that the knowledge graph missed (ADR-006.6)**: A schema flagged as orphan may turn out to be loaded at runtime by an ETL or scenario file outside `src/`. Mitigation: each schema disposition is verified by `git grep` across the *entire* repository (not just `src/`), and the audit commit lists the search commands used.
- **Bundle 2 ships post-Spec-057, so any Spec-057-era code introduced in `tick/system/imperial_rent.py` may need light adjustment if ADR-003's `SystemBase` migration affects the parent `TickDynamicsSystem`**: Mitigation: Spec 057 already inherits from the Bundle-1 facade pattern; the ADR-003 migration only changes the System base class scaffolding and does not affect the sub-component classes inside `tick/system/`.
- **Scope drift (with so many ADRs in one bundle)**: The bundle is large (~11 days). Resist the temptation to also tackle items deferred to later (e.g., the remaining `Default*` migrations). If during implementation a new ADR-worthy refactor is discovered, file it as a new ADR for a future bundle rather than absorbing it into Bundle 2.
