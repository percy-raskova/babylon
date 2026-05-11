# Contract: Public Import Equivalence

**Bundle**: 059-adr-bundle-2-post-spec-057 · **Phase**: 1
**Reference**: spec.md FR-003, FR-007, FR-010, FR-012; data-model.md §2

Bundle 2 is a structural refactor. **No public import path may break.**
Every symbol importable on the pre-Bundle-2 baseline must continue to resolve
on the post-Bundle-2 branch, with the same identity (a class is the same
class; a function is the same function — modulo the `Scenario` shim wrappers).

This contract is verified by `git grep` byte-equality between the
pre-bundle-2-baseline tag and the post-merge `dev` branch.

## C1 — `persistence/postgres_runtime` (ADR-005 Part A)

Every existing import that resolved a symbol from the 2094-LOC monolith MUST
continue to resolve from the new package.

```python
# MUST keep working post-decomposition
from babylon.persistence import PostgresRuntime
from babylon.persistence.postgres_runtime import PostgresRuntime
```

**New paths permitted (do not break the contract)**:
```python
# These become accessible alongside the facade — additive, not replacement
from babylon.persistence.postgres_runtime.tick_io import PostgresTickIO
from babylon.persistence.postgres_runtime.archival_io import PostgresArchivalIO
from babylon.persistence.postgres_runtime.spatial_io import PostgresSpatialIO
from babylon.persistence.postgres_runtime.community_io import PostgresCommunityIO
from babylon.persistence.postgres_runtime.trace_io import PostgresTraceIO
```

**Verification**:
```bash
# Pre-bundle-2 baseline
git checkout pre-bundle-2-baseline
git grep -l "from babylon.persistence" -- 'src/' 'tests/' 'tools/' \
  | xargs grep -h "from babylon.persistence" | sort -u > /tmp/persistence-imports-before.txt

# Post-bundle-2 branch
git checkout 059-adr-bundle-2-post-spec-057
git grep -l "from babylon.persistence" -- 'src/' 'tests/' 'tools/' \
  | xargs grep -h "from babylon.persistence" | sort -u > /tmp/persistence-imports-after.txt

# Every "before" import must still appear in the "after" set
diff /tmp/persistence-imports-before.txt /tmp/persistence-imports-after.txt \
  | grep "^<" \
  | grep -v "^---"
# Expected output: empty (no removed import lines)
```

## C2 — `engine.Simulation` (ADR-005 Part B)

```python
# MUST keep working post-decomposition
from babylon.engine import Simulation
from babylon.engine.simulation import Simulation
```

**Public method surface** — every method on the pre-Bundle-2 `Simulation`
class MUST resolve on the post-Bundle-2 facade. The facade delegates to
sub-components but the call sites do not change.

**Verification** (smoke):
```python
import inspect
from babylon.engine import Simulation
methods_after = {name for name, _ in inspect.getmembers(Simulation, predicate=inspect.isfunction)
                 if not name.startswith("_")}
# Expected: methods_after >= methods_before (where methods_before is the
# pre-Bundle-2 snapshot, captured by tasks.md step 1).
```

## C3 — `models.events` (ADR-004)

```python
# MUST keep working post-package-split (FR-007)
from babylon.models.events import (
    SimulationEvent,                    # root base
    EconomicEvent, ConsciousnessEvent,  # intermediate bases
    StruggleEvent, ContradictionEvent, TopologyEvent,
    # all 19 leaf variants:
    ExtractionEvent, SubsidyEvent, CrisisEvent, SuperwageCrisisEvent,
    ClassDecompositionEvent, ControlRatioCrisisEvent, TerminalDecisionEvent,
    TransmissionEvent, MassAwakeningEvent,
    SparkEvent, UprisingEvent, SolidaritySpikeEvent,
    RuptureEvent,
    PhaseTransitionEvent, BifurcationTendencyEvent,
    EndgameEvent, AxiomViolationEvent,
    QcewCarryForwardEvent, PhiHourOutlierEvent,
    # plus the new union type:
    TickEvent,
)
```

**New imports permitted (additive)**:
```python
# Per-category sub-modules become accessible
from babylon.models.events.economic import ExtractionEvent
from babylon.models.events.consciousness import TransmissionEvent
# … etc.
```

## C4 — `engine.systems.System` Protocol (ADR-003)

```python
# MUST keep working — preserves duck-typed mocks in tests (FR-010)
from babylon.engine.systems.protocol import System

# AND the new ABC must become accessible:
from babylon.engine.systems.base import SystemBase
```

If `engine/systems/protocol.py` is collapsed into `base.py`, the old import
path MUST still resolve (either via re-export from `base.py` or by leaving
`protocol.py` as a 1-line shim `from .base import System`).

## C5 — `engine.scenarios` shims (ADR-006.1)

```python
# MUST keep working as backward-compat shims (FR-012)
from babylon.engine.scenarios import (
    create_two_node_scenario,
    create_high_tension_scenario,
    create_labor_aristocracy_scenario,
    create_imperial_circuit_scenario,
    create_us_scenario,
    get_multiverse_scenarios,
    apply_scenario,
)
from babylon.engine.scenarios_wayne_county import create_wayne_county_scenario
```

**New paths permitted (additive)**:
```python
from babylon.engine.scenarios.base import Scenario
from babylon.engine.scenarios.imperial_circuit import ImperialCircuitScenario
# … etc.
```

**Note**: `engine.scenarios_wayne_county` is preserved as a 1-line shim
re-exporting `create_wayne_county_scenario` from the new package
(`engine.scenarios.wayne_county`). This is the only file outside
`engine/scenarios/` that must remain importable.

## C6 — `economics.circulation.types` (ADR-006.2)

```python
# MUST keep working post-split (FR-013)
from babylon.economics.circulation.types import (
    CircuitState, TurnoverProfile, AnnualSurplusValue,
    ReproductionBalance, ReproductionAnalysis,
    FixedCapitalItem, DepreciationFundState, MoralDepreciation, InventoryState,
    RealizationCrisis, DisproportionalityCrisis,
    CirculationCrisisAssessment, CirculationCrisisState,
    CapitalForm, ReplacementCyclePosition, InventoryDiagnosis, CrisisSeverity,
)
```

**New paths permitted (additive)**:
```python
from babylon.economics.circulation.types.flow import CircuitState
from babylon.economics.circulation.types.crisis import RealizationCrisis
# … etc.
```

## C7 — `engine.systems.edge_transition` (ADR-006.4)

```python
# MUST keep working post-split (FR-014)
from babylon.engine.systems.edge_transition import EdgeTransitionSystem
```

**New paths permitted (additive)**:
```python
from babylon.engine.systems.edge_transition.predicates import (
    PredicateCondition, CompoundPredicate, EdgeModeTransition,
)
from babylon.engine.systems.edge_transition.system import EdgeTransitionSystem
```

## Acceptance gate

This contract is satisfied when:

1. The "before" set of import lines (captured at the `pre-bundle-2-baseline`
   tag) is a subset of the "after" set on the merge commit.
2. `mise run test:unit` and `mise run test:int` produce identical pass/skip/
   xfail tallies (modulo intentionally-added Bundle 2 tests, per FR-016).
3. `python -c "from babylon.persistence import PostgresRuntime; from
   babylon.engine import Simulation; from babylon.models.events import
   TickEvent; from babylon.engine.systems.base import SystemBase; from
   babylon.engine.scenarios.base import Scenario"` exits 0.
