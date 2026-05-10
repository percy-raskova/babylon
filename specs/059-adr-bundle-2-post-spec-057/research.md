# Phase 0 Research: ADR Bundle 2 — post-Spec-057 architectural cleanup

**Feature**: 059-adr-bundle-2-post-spec-057
**Date**: 2026-05-09
**Spec**: [spec.md](spec.md)
**Status**: Phase 0 complete

This document resolves the NEEDS-CLARIFICATION items implicit in spec.md and
records the canonical patterns each ADR will follow. Decisions here override
stale numbers in spec.md and `docs/agents/adrs/ADR-00{3,4,5,6}-*.md` where the
two disagree, until those documents are reconciled in their respective rollout
commits.

## D1 — System count: 22 (not 23)

**Decision**: Bundle 2 migrates **22** System implementations to `SystemBase`,
not 23 as stated in ADR-003 and inherited by spec.md FR-009 / SC-005 / US3.

**Rationale**: A direct enumeration of `^class.*System[^a-zA-Z]:` in
`src/babylon/` on the current branch yields:

| Location | Count | Names |
|---|---:|---|
| `src/babylon/engine/systems/` | 21 | SurvivalSystem, TerritorySystem, VitalitySystem, DispossessionEventSystem, OODASystem, ProductionSystem, DecompositionSystem, EventTemplateSystem, ReserveArmySystem, CommunitySystem, LifecycleSystem, ControlRatioSystem, ContradictionFieldSystem, MetabolismSystem, ImperialRentSystem, SolidaritySystem, StruggleSystem, EdgeTransitionSystem, ContradictionSystem, ConsciousnessSystem, FieldDerivativeSystem |
| `src/babylon/economics/tick/system/` | 1 | TickDynamicsSystem (Bundle 1 / Spec 057 deliverable) |
| **Total** | **22** | — |

ADR-003 was authored on 2026-05-05 with "23 System implementations". The
current branch has 22; either ADR-003 mis-counted, or one System has been
consolidated since. Either way, the implementing tasks must reconcile to the
authoritative live count at task time.

**Alternatives considered**:
- *Keep ADR-003's "23" wording* — rejected: introduces a false acceptance
  criterion (`SC-005` would fail because no 23rd System exists to inherit
  from `SystemBase`).
- *Re-derive the count via `git grep` at every commit* — rejected: brittle.
  The plan locks in 22 and `tasks.md` will list each System by name.

**Consequences for spec.md**: FR-009, FR-011, US3 acceptance, SC-005, and the
edge-case bullet referring to "23 System implementations" all read "22" or
"all System implementations" instead.

## D2 — Event leaf-variant count: 19 (not 22)

**Decision**: Bundle 2 introduces a `kind: Literal[...]` discriminator on **19
leaf Event variants**, not 22 as stated in ADR-004 and FR-004.

**Rationale**: `models/events.py` currently contains 25 `class …Event…:`
declarations, structured as:

| Layer | Count | Classes |
|---|---:|---|
| Root | 1 | `SimulationEvent` |
| Intermediate bases | 5 | `EconomicEvent`, `ConsciousnessEvent`, `StruggleEvent`, `ContradictionEvent`, `TopologyEvent` |
| **Leaf variants** | **19** | `ExtractionEvent`, `SubsidyEvent`, `CrisisEvent`, `SuperwageCrisisEvent`, `ClassDecompositionEvent`, `ControlRatioCrisisEvent`, `TerminalDecisionEvent`, `TransmissionEvent`, `MassAwakeningEvent`, `SparkEvent`, `UprisingEvent`, `SolidaritySpikeEvent`, `RuptureEvent`, `PhaseTransitionEvent`, `BifurcationTendencyEvent`, `EndgameEvent`, `AxiomViolationEvent`, `QcewCarryForwardEvent`, `PhiHourOutlierEvent` |

Pydantic 2 discriminated unions discriminate over **leaf** variants — the 5
intermediate bases (`EconomicEvent` etc.) are abstract namespaces and do not
themselves get a `kind` field. Only the 19 leaves do.

ADR-004's "22 Event subclasses" likely counted abstract bases as variants or
predates the addition of `QcewCarryForwardEvent` and `PhiHourOutlierEvent`
(both added in Spec 057's calibration-warning family per project memory
S2713 / S35888).

**Alternatives considered**:
- *Discriminate over all 24 non-root classes* — rejected: violates Pydantic's
  discriminator contract (a non-leaf would create a recursive discriminator
  ambiguity).
- *Flatten the intermediate bases into the leaf classes* — rejected: the
  intermediate bases carry shared fields (`tick`, `actors`, etc.) and removing
  them is a larger refactor than ADR-004 envisioned.

**Consequences for spec.md**: FR-004 and SC-010 reference "all Event variants"
or "every leaf variant" (number elided) instead of "22". Tasks.md will list
each of the 19 leaves by name.

## D3 — Scenario builder count: 6 (not 9)

**Decision**: Bundle 2 ports **6 scenario builders** to `Scenario` subclasses,
not 9 as stated in ADR-006 and FR-012.

**Rationale**: A direct enumeration of public `def create_*_scenario` and
`def *_scenario` functions in `engine/scenarios.py` and
`engine/scenarios_wayne_county.py`:

| File | Builders |
|---|---|
| `engine/scenarios.py` | `create_two_node_scenario`, `create_high_tension_scenario`, `create_labor_aristocracy_scenario`, `create_imperial_circuit_scenario`, `create_us_scenario` |
| `engine/scenarios_wayne_county.py` | `create_wayne_county_scenario` |
| **Total** | **6 builders** |

`engine/scenarios.py` also contains:
- 2 utilities — `get_multiverse_scenarios` (returns a list of `ScenarioConfig`s,
  not a builder), `apply_scenario` (mutates a config; not a builder)
- 5 private helpers — `_get_region_name`, `_compute_metro_influence`,
  `_classify_hex`, `_create_us_territories`, `_assign_tenancy_edges`

ADR-006.1's "9 free functions" appears to have counted utilities or private
helpers as builders.

**Alternatives considered**:
- *Port the utilities (`get_multiverse_scenarios`, `apply_scenario`) as
  `Scenario` subclass methods* — rejected: they operate on multiple scenarios
  or on configs, not on building one scenario. They belong on the registry, not
  on the ABC.
- *Decompose `create_us_scenario` into per-region sub-scenarios* — out of
  scope (ADR-006.1 explicitly says "port the existing builders unchanged").

**Consequences for spec.md**: FR-012 and US4 acceptance reference "the
existing scenario builders" (number elided) instead of "9". Tasks.md will list
the 6 builders by name.

## D4 — ADR-006.3 and ADR-006.5 are out of Bundle 2 scope

**Decision**: Bundle 2 implements ADR-006 items **6.1 (Scenario ABC), 6.2
(circulation/types split), 6.4 (edge_transition split), and 6.6 (orphan
schemas)** only. Items 6.3 (decompose `economics/tick/system.py`) and 6.5
(type the BEA → Department mapping) are **already shipped** by Bundle 1
(Spec 058) and require no further work in Bundle 2.

**Rationale**: Direct verification on the current branch:

- **ADR-006.3 — already shipped**: `src/babylon/economics/tick/` is a package
  containing `crisis_detector.py`, `derived_rates.py`, `graph_bridge.py`,
  `initializer.py`, `precarity.py`. The sub-`tick/system/` package contains
  `imperial_rent.py` (Spec 057) and `__init__.py` (TickDynamicsSystem facade).
  The original 1705-LOC monolith no longer exists.
- **ADR-006.5 — already shipped**:
  `src/babylon/economics/tensor_hierarchy/mappings/_models.py` defines the
  `BEAMappings` Pydantic model; `mappings/__init__.py` parses
  `bea_to_department.toml` once into a `BEA_TO_DEPARTMENT` singleton via
  `BEAMappings.model_validate(...)`.

**Alternatives considered**:
- *Re-verify and tighten 6.3 / 6.5 in Bundle 2* — rejected: it would either
  duplicate Bundle 1's commits or open a re-litigation that risks regressing
  Spec 057's calibration code that depends on these surfaces.

**Consequences for spec.md**: spec.md's input bullet (line 6) and "ADR-006
items 6.1, 6.2, 6.4, 6.6" wording is correct; nothing to change.

## D5 — ADR-003 → ADR-006.4 is a hard ordering, not parallel

**Decision**: ADR-003 (SystemBase ABC) **must merge before** ADR-006.4
(edge_transition split). The plan documents this as a hard task-level
dependency in `tasks.md`, not as a soft note in Assumptions.

**Rationale**: `docs/agents/adrs/ADR-006-cleanup-batch.md:119` explicitly
specifies the post-split `system.py` as `EdgeTransitionSystem class (uses
ADR-003 SystemBase)`. Same document line 226 lists ADR-003 in its References as
"`SystemBase` helpers used in 6.4". The split therefore requires the
`SystemBase` symbol to exist; absent that, 6.4 either has to land a
duplicate-and-revert or block.

The other ADRs are unaffected:
- ADR-004 (TickEvent union) — independent (touches `models/events.py` only)
- ADR-005 (god-class decomposition) — independent (touches
  `persistence/postgres_runtime.py` and `engine/simulation.py`)
- ADR-006.1 (Scenario ABC) — independent (touches `engine/scenarios.py` only)
- ADR-006.2 (circulation/types split) — independent
- ADR-006.6 (orphan schema audit) — independent (docs only)

**Alternatives considered**:
- *Allow ADR-006.4 to inherit from `System` Protocol initially, then refactor
  to `SystemBase` later* — rejected: produces an extra commit per System,
  doubles the test churn, and contradicts ADR-006.4's stated design.

**Consequences for spec.md**: FR-017 still permits parallel work across the
remaining six items; only the ADR-003 → ADR-006.4 edge is locked. The
suggested order in spec.md ("ADR-005 first … ADR-006 items last") is
compatible — ADR-006.4 lands after ADR-003 by that order.

## D6 — Orphan schema disambiguation

**Decision**: The FR-015 audit for the 8 orphan schemas distinguishes
**graph-orphan** (no incoming `$ref`) from **runtime-unused** (no Python loader
references the file). Each schema receives a disposition based on which type
of orphan it is:

| Schema | Graph-orphan | Runtime-loaded? | Recommended disposition |
|---|---|---|---|
| `entities/culture.schema.json` | yes | no | (b) delete or (c) annotate |
| `entities/ideology.schema.json` | yes | partial — referenced from `models/entities/` Pydantic counterparts | (a) standalone-by-design |
| `entities/institution.schema.json` | yes | partial — same | (a) standalone-by-design |
| `entities/persona.schema.json` | yes | yes — loaded by `ai/persona_loader.py` | (a) standalone-by-design + add `description` field |
| `entities/sentiment.schema.json` | yes | no | (b) delete or (c) annotate |
| `slice-spec.schema.json` | yes | unclear — needs single-call grep | TBD at audit |
| `narrative/narrative_frame.schema.json` | yes | **yes — loaded at runtime** by `engine/observers/schema_validator.py:36` | **(a) standalone-by-design + add `description` field** |
| (8th — TBD by knowledge-graph rebuild) | — | — | TBD |

**Rationale**: ADR-006.6 conflates the two orphan types under a single
"orphan" label. Acting on a graph-orphan as if it were runtime-unused would
delete `narrative_frame.schema.json`, which is loaded by the schema validator
observer — a regression. The plan splits the audit into two passes: first a
runtime-load grep (`git grep` for `.schema.json` in `src/`, `tests/`,
`tools/`), then a graph-orphan audit (the knowledge graph) — and dispositions
are assigned only after both passes complete.

**Pre-flight requirement**: `.understand-anything/knowledge-graph.json` on
disk is a 132-byte git-lfs pointer file. Either run `git lfs pull` or rebuild
via `/understand-anything:understand` before US6 begins, to confirm the orphan
list is still 8 (and to identify any new orphans introduced since 2026-05-06).

**Alternatives considered**:
- *Trust ADR-006.6's flat list without runtime-grep* — rejected: would
  delete a runtime-loaded schema (`narrative_frame`).

**Consequences for spec.md**: FR-015 grows a clarification — "the audit
distinguishes graph-orphans (no `$ref`) from runtime-unused schemas (no Python
loader). Dispositions account for both: a graph-orphan that is loaded at
runtime is annotated with `description`, never deleted." US6 acceptance and
SC-008 follow.

## D7 — FR-008 introduces `match event:` exhaustiveness; observers don't currently use it

**Decision**: FR-008's exhaustiveness migration **introduces** `match event:`
or `if isinstance(...)` chains with `assert_never` in observers; it does not
just add `case _:` to existing match statements.

**Rationale**: A grep across `src/babylon/engine/observers/` returns **zero**
matches for `match event:` and zero `isinstance(.*Event)` chains over the
`Event` hierarchy. Observers currently use other dispatch mechanisms
(method-per-event, hash maps, or Pydantic discriminator inspection).

This is a meaningful scope adjustment for ADR-004 step 3 (`refactor(engine):
consume TickEvent union in WorldState and observers`). The work is not "patch
existing match statements" but "introduce a typed dispatch surface to each
observer that has variant-specific behavior". For observers that emit telemetry
without branching by variant (e.g., `metrics.py` counting all events
uniformly), no match is required and `assert_never` does not apply.

**Alternatives considered**:
- *Defer the observer migration to a follow-up spec* — rejected: it is
  the load-bearing change that turns FR-004's discriminated union into a
  typecheck-time win. Without observer dispatch, the new union's `mypy`
  benefit is invisible.
- *Add `match event:` only to causal/endgame observers, leave others
  Pydantic-typed* — accepted as a tactical refinement. The task list will
  enumerate which observers acquire `match` statements and which keep their
  current dispatch (with a typecheck on the union covering all variants).

**Consequences for spec.md**: FR-008 reads "every observer that consumes the
`TickEvent` union variant-specifically must include an `assert_never(event)`
exhaustiveness check; observers that consume events uniformly (e.g.,
telemetry counters) need only type their input as `TickEvent` to gain
discriminator-validation".

## D8 — Byte-determinism verified for the workhorse scenario

**Decision**: SC-007's byte-equality check is achievable as written for at
least the `imperial_circuit` scenario.

**Rationale**: `tools/parameter_analysis.py trace --ticks 50` was run twice
with no parameter overrides; both CSVs are byte-identical (`cmp -s` returns 0).
The default scenario in `parameter_analysis.py` is
`create_imperial_circuit_scenario`, which is also the primary scenario
exercised by `vertical_slice.py`, `audit_simulation.py`, `necropolis_viewer.py`,
and `regression_test.py`.

50 ticks is shorter than `sim:trace`'s 200-tick default, but if the simulation
is byte-deterministic at 50, it remains so at 200 unless something
seed-dependent enters the path later (no such code path exists; no `time.time`
or `random` without explicit seed in the tick path).

**Alternatives considered**:
- *Verify all 6 scenarios pre-flight* — partially adopted. The plan's
  pre-flight checklist (in `quickstart.md`) runs `sim:trace 50` twice for
  each of the 6 scenarios before US4 begins. If any scenario fails the byte
  check, that scenario's SC-007 is relaxed to numeric-tolerance with a
  documented epsilon.

**Consequences for spec.md**: SC-007 wording stands. The pre-flight check is
in `quickstart.md`, not the spec.

## D9 — Updated load-bearing LOC counts

**Decision**: spec.md's LOC numbers are updated to current-branch reality:

| File | spec.md | current | delta |
|---|---:|---:|---:|
| `persistence/postgres_runtime.py` | 1955 | **2094** | +139 |
| `engine/simulation.py` | 1048 | **1048** | 0 |
| `models/events.py` | 1011 | **1119** | +108 |
| `economics/circulation/types.py` | 1354 | **1354** | 0 |
| `engine/systems/edge_transition.py` | 853 | **856** | +3 |
| `engine/scenarios.py` | 970 | **970** | 0 |
| `engine/scenarios_wayne_county.py` | 569 | **569** | 0 |
| `engine/systems/protocol.py` | 41 | **41** | 0 |

The +139 LOC on `postgres_runtime.py` and +108 on `events.py` are likely Spec
057 contributions (PostgresTickIO `phi_hour` extensions and the
`CalibrationWarning` event family per memory S35888). They do not change
ADR-005 / ADR-004's decomposition shape, but the per-file LOC budgets in
FR-001 (≤400 LOC per sub-component) and FR-007 (≤300 LOC per `events/`
sub-file) remain the correct constraint.

**Alternatives considered**:
- *Reset the budgets relative to new totals* — rejected: 400 LOC per
  sub-component is a quality target, not a proportional one.

**Consequences for spec.md**: FR-001, FR-007, US1's Independent Test, US5's
Independent Test, and SC-002 all refer to the constraint (≤400 LOC,
≤200 LOC for facades, ≤300 LOC for events sub-files), not to the source
file's pre-decomposition size.

## Pattern decisions

### P1 — Pydantic 2 discriminated union

**Pattern**: `TickEvent = Annotated[Union[V1, V2, …], Field(discriminator="kind")]`
where each `Vi` carries a unique `kind: Literal["..."]`.

**Source**: ADR-004; canonical Pydantic 2 idiom for sum types
([Pydantic Discriminated Unions](https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions)).

**Rationale**: Pydantic auto-dispatches on the discriminator, validates the
literal at class definition, and (with `assert_never` in match statements)
forces observers to acknowledge new variants at typecheck time.

**Open question**: Whether the 5 intermediate bases (`EconomicEvent` etc.)
remain as Pydantic models or collapse to `TypeAlias` namespaces. The plan
keeps them as Pydantic models for shared field inheritance; only the 19 leaves
get `kind`.

### P2 — ABC + runtime_checkable Protocol coexistence

**Pattern**: `engine/systems/base.py` defines both:
```python
class SystemBase(ABC):
    name: ClassVar[str]
    @abstractmethod
    def step(self, graph, services, context) -> None: ...
    def _read(...): ...
    def _write(...): ...
    def _publish(...): ...

@runtime_checkable
class System(Protocol):
    name: str
    def step(self, graph, services, context) -> None: ...
```

**Source**: ADR-003.

**Rationale**: ABCs lift shared scaffolding for production code; the
`runtime_checkable Protocol` preserves duck-typed mocks in tests
(`isinstance(stub, System)` still works without inheriting from `SystemBase`).
PEP 544 explicitly supports this dual-export pattern.

### P3 — Facade composition over monolith

**Pattern**: A god-class file becomes a package whose `__init__.py` exports
a thin facade (≤200 LOC) that composes focused IO/orchestration sub-components
(each ≤400 LOC).

**Source**: ADR-005.

**Rationale**: The facade preserves the public Protocol surface
(`RuntimePersistence`, `PostgresRuntimeExtensions` for `PostgresRuntime`;
the embedder-facing `tick()`, `run_to_completion()`, etc. for `Simulation`)
while sub-components become independently constructable and testable. Per-call
overhead is one extra method dispatch — negligible at simulation tick
frequency.

### P4 — `__init_subclass__` registry for Scenario ABC

**Pattern**:
```python
class Scenario(ABC):
    name: ClassVar[str]
    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        _SCENARIO_REGISTRY[cls.name] = cls
```

**Source**: ADR-006.1.

**Rationale**: Subclasses register themselves at import time without an
explicit `register_scenario(...)` call site. New scenarios drop in by adding
one file and importing it from `engine/scenarios/__init__.py`.

**Tradeoff**: The auto-registration is "mildly magic" (per ADR-006.1's own
note). If reviewers push back, the alternative is an explicit
`register_scenario(name)(cls)` decorator with no behavior change. The plan
defaults to `__init_subclass__` and notes the fallback.

## Open items deferred to `tasks.md`

- The 5–7 specific `data.get("X", default)` masking patterns to convert to
  `_read(..., required=True)` per FR-011. Identified via `git grep
  'data.get("' src/babylon/engine/systems/` at task-decomposition time.
- The exact list of observers that acquire `match event:` statements vs.
  those that retain their current dispatch (per D7).
- The 8th orphan schema's identity (per D6). The current count of 7 plus
  one TBD will be resolved by the pre-flight knowledge-graph rebuild.

## Constitutional tier check

This refactor touches no theoretical primitives:

- **P0 (Never Drop)**: Untouched. I.19 Dialectic, I.20 Spatial Substrate,
  II.9 Morphism, III.7 Determinism Hash, III.8 Aleksandrov Test, V Verb
  Atomicity all retain their current implementations.
- **P1 (Load-Bearing)**: Bundle 2 preserves I.16 (Organization vs Institution)
  by preserving the Systems that act on Organizations; II.6 (State is Data,
  Engine is Transformation) by keeping the engine's pure-transformation shape
  (Systems mutate the graph in place, but the ABC supplies the read/write
  primitives, not new behavior); II.11 (Subsystem Table Ownership) by leaving
  postgres_runtime's per-table ownership unchanged across the decomposition.
- **P2 (Elaboration)**: Untouched.

No constitutional gate is at risk. The Constitution Check in plan.md confirms
this.
