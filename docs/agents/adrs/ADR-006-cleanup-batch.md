# ADR-006: Scenario ABC + remaining splits + orphan schemas

**Status**: Proposed
**Date**: 2026-05-05
**Phase**: 6 of 6
**Tier**: T3 (mostly cleanup)
**Estimated effort**: 3 days
**Risk**: Low

## Context

Once ADRs 001–005 land, the architectural shape is in place. This ADR collects the remaining cleanup work that would otherwise drift into "we'll get to it" territory. Each item is small enough to be a single commit; together they finish the leasing-up pass.

Inventory:

| #   | Target                                                                                             | Why                                                                                 | Lines / impact |
| --- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | -------------- |
| 6.1 | `engine/scenarios.py` + `scenarios_wayne_county.py`                                                | Free functions with no shared base; new scenarios will keep duplicating boilerplate | 970 + 569      |
| 6.2 | `economics/circulation/types.py`                                                                   | 1354 LOC, 19 Pydantic types covering 3 distinct concepts                            | 1354           |
| 6.3 | `economics/tick/system.py`                                                                         | 1705 LOC, 33 methods on one class — same god-class shape as ADR-005                 | 1705           |
| 6.4 | `engine/systems/edge_transition.py`                                                                | 853 LOC mixing Pydantic predicate models with the System class                      | 853            |
| 6.5 | `economics/tensor_hierarchy/mappings/bea_to_department.toml`                                       | Untyped TOML loaded at runtime; should be a frozen Pydantic model                   | 151            |
| 6.6 | 8 orphan schemas (culture, ideology, institution, persona, sentiment, slice-spec, narrative_frame) | Flagged as orphans in graph validation — no `$ref` cross-references                 | —              |

## Decision

Six independent commits, all using patterns established in earlier ADRs.

### 6.1 Scenario ABC

Introduce `engine/scenarios/base.py`:

```python
from abc import ABC, abstractmethod
from typing import ClassVar

class Scenario(ABC):
    """Base class for scenario builders. Subclasses register themselves at import."""

    name: ClassVar[str]
    description: ClassVar[str]

    @abstractmethod
    def build_territories(self) -> dict[str, Territory]: ...
    @abstractmethod
    def build_classes(self) -> dict[str, SocialClass]: ...
    @abstractmethod
    def build_relationships(self) -> dict[str, Relationship]: ...

    def build(self) -> tuple[WorldState, SimulationConfig, GameDefines]:
        """Default composition. Override only when a scenario needs custom assembly."""
        territories = self.build_territories()
        classes = self.build_classes()
        relationships = self.build_relationships()
        # ... shared assembly logic that used to be duplicated across scenario fns
        return state, config, defines

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        _SCENARIO_REGISTRY[cls.name] = cls
```

Convert the 9 free functions in `scenarios.py` and `scenarios_wayne_county.py` to subclasses:

```
src/babylon/engine/scenarios/
├── __init__.py             # Registry + get_multiverse_scenarios()
├── base.py                 # Scenario ABC
├── two_node.py             # TwoNodeScenario
├── high_tension.py         # HighTensionScenario
├── labor_aristocracy.py    # LaborAristocracyScenario
├── imperial_circuit.py     # ImperialCircuitScenario
├── us.py                   # USScenario
└── wayne_county.py         # WayneCountyScenario
```

Existing free-function imports kept as thin shims:

```python
def create_two_node_scenario(*args, **kwargs):
    return TwoNodeScenario(*args, **kwargs).build()
```

### 6.2 Split `economics/circulation/types.py`

Group its 19 Pydantic types into three thematic files, mirroring ADR-001:

```
src/babylon/economics/circulation/types/
├── __init__.py             # Re-exports
├── flow.py                 # CircuitState, TurnoverProfile, AnnualSurplusValue, ReproductionBalance, ReproductionAnalysis
├── fixed_capital.py        # FixedCapitalItem, DepreciationFundState, MoralDepreciation, InventoryState
├── crisis.py               # RealizationCrisis, DisproportionalityCrisis, CirculationCrisisAssessment, CirculationCrisisState
└── _enums.py               # CapitalForm, ReplacementCyclePosition, InventoryDiagnosis, CrisisSeverity (4 StrEnums)
```

### 6.3 Decompose `economics/tick/system.py`

Same god-class playbook as ADR-005 Part B (`Simulation`):

```
src/babylon/economics/tick/system/
├── __init__.py             # TickDynamicsSystem facade
├── national_parameters.py  # NationalTickParameters computation
├── county_distribution.py  # CountyEconomicState updates
├── crisis_detection.py     # CrisisDetector logic
├── smoothing.py            # already exists at tick/smoothing.py — wire in
└── derived_rates.py        # already exists at tick/derived_rates.py — wire in
```

`TickDynamicsSystem` becomes a ~200-LOC facade composing the above.

### 6.4 Split `engine/systems/edge_transition.py`

```
src/babylon/engine/systems/edge_transition/
├── __init__.py             # EdgeTransitionSystem (re-export)
├── predicates.py           # PredicateCondition, CompoundPredicate, EdgeModeTransition (Pydantic models)
└── system.py               # EdgeTransitionSystem class (uses ADR-003 SystemBase)
```

### 6.5 Type the BEA → Department mapping

Replace runtime TOML parsing in `economics/department_mapper.py` with a typed Pydantic model:

```python
# economics/tensor_hierarchy/mappings/_models.py
class DepartmentMapping(BaseModel):
    model_config = ConfigDict(frozen=True)
    bea_code: str
    department: Literal["I", "II", "III"]
    weight: float = Field(ge=0.0, le=1.0)

class BEAMappings(BaseModel):
    model_config = ConfigDict(frozen=True)
    mappings: list[DepartmentMapping]

# economics/tensor_hierarchy/mappings/__init__.py
import tomllib
from pathlib import Path
_path = Path(__file__).parent / "bea_to_department.toml"
BEA_TO_DEPARTMENT = BEAMappings.model_validate(tomllib.loads(_path.read_text()))
```

`get_default_mapper()` consumes the typed object instead of reparsing TOML on every call.

### 6.6 Orphan schemas

8 schemas have no incoming or outgoing edges in the knowledge graph (per Phase 6 validation warnings):

- `schemas/entities/culture.schema.json`
- `schemas/entities/ideology.schema.json`
- `schemas/entities/institution.schema.json`
- `schemas/entities/persona.schema.json`
- `schemas/entities/sentiment.schema.json`
- `schemas/slice-spec.schema.json`
- `schemas/narrative/narrative_frame.schema.json`

For each, verify:

1. **Used at runtime?** Does any code load it via `jsonschema` or reference its `$id`? If not, candidate for deletion.
1. **Reachable Pydantic counterpart?** If `models/entities/culture.py` exists and is current, the schema may be redundant or out-of-sync.
1. **Listed in CLAUDE.md as one of the "17 JSON entity collections"?** If yes, keep and document why it has no `$ref` (it's standalone).

Action per schema:

- Add a top-level `description` field clarifying its role.
- If unused and superseded by a Pydantic model, delete it (with an entry in `ai-docs/decisions.yaml`).
- If standalone-by-design, add a `# standalone schema, no $ref` comment to its `models/entities/*.py` counterpart.

## Consequences

### Positive

- New scenarios drop in as one class, not three free functions in two files.
- `circulation/types/` and `edge_transition/` follow the same package shape as enums/defines/events.
- TOML mapping becomes typecheck-aware.
- Orphan schemas either earn their place or stop adding noise.

### Negative / tradeoffs

- This ADR is broad — six small decisions in one document. Defensible because they're independent and trivially small. Each ships as its own commit.
- Scenario ABC's `__init_subclass__` registry pattern is mildly magic; could be replaced with explicit registration if preferred. We choose the simpler pattern; the magic is contained.

## Acceptance criteria

- [ ] `Scenario` ABC exists; all 9 existing scenario builders ported as subclasses; old free-function names kept as shims.
- [ ] `economics/circulation/types.py` no longer >300 LOC (or replaced by `economics/circulation/types/` package).
- [ ] `economics/tick/system.py` decomposed; facade ≤200 LOC; no constituent file >400 LOC.
- [ ] `engine/systems/edge_transition.py` split with predicates and System in separate files.
- [ ] `BEAMappings` Pydantic model defined and consumed by `department_mapper.py` instead of raw TOML parsing.
- [ ] Each of the 8 orphan schemas has been audited; each has either: (a) a documented standalone status, (b) a `defines_schema` edge to a Pydantic counterpart, or (c) been deleted with rationale in `ai-docs/decisions.yaml`.
- [ ] `mise run check` passes; `mise run test:all` passes.

## Rollout

Six independent commits. Order is flexible; suggested:

1. **`refactor(engine): introduce Scenario ABC and migrate scenario builders`** (1 day)
1. **`refactor(economics): split circulation/types.py into package`** (½ day)
1. **`refactor(engine): split edge_transition.py into predicates + system`** (½ day)
1. **`refactor(economics): decompose tick/system.py into focused subcomponents`** (1 day)
1. **`refactor(economics): type bea_to_department mapping via Pydantic`** (¼ day)
1. **`docs(schemas): audit and document orphan schemas`** (¼ day)

Items 1, 2, 3, 5, 6 can happen in parallel (different packages, no overlap). Item 4 stands on its own.

## Test strategy

- After each commit: `mise run check`.
- Specific:
  - **6.1** `tests/integration/test_scenario_*.py` and `mise run sim:run --scenario X` for each migrated scenario should produce identical baseline output (use `mise run qa:regression-generate` pre-flight).
  - **6.2/6.3/6.4** Same package-shape pattern as ADR-001; verify import equivalence with `git grep`.
  - **6.5** `pytest tests/ -k "department_mapper"` should pass; add a new test that constructs `BEAMappings` from inline data and validates fields.
  - **6.6** No automated test; require explicit human sign-off on each schema decision in the commit message.

## References

- Knowledge graph nodes:
  - `file:src/babylon/engine/scenarios.py` (970 LOC, 9 free functions)
  - `file:src/babylon/engine/scenarios_wayne_county.py` (569 LOC)
  - `file:src/babylon/economics/circulation/types.py` (1354 LOC, 19 Pydantic types)
  - `file:src/babylon/economics/tick/system.py` (1705 LOC, 33 methods)
  - `file:src/babylon/engine/systems/edge_transition.py` (853 LOC)
  - 8 orphan schema nodes (validation warnings from Phase 6 of the `/understand` build)
- Related ADRs: ADR-001 (package-split shape), ADR-003 (`SystemBase` helpers used in 6.4), ADR-005 (god-class decomposition shape used in 6.3).
- CLAUDE.md sections: "Pydantic First", "Coding Standards" (no function over ~100 lines), "Common Gotchas" (Mypy Misses Pydantic Attribute Errors — relevant to 6.5).
