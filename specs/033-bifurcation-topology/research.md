# Research: Bifurcation Topology Analysis

## R1: Community Consciousness Access from TopologyMonitor

**Problem**: TopologyMonitor receives `WorldState` via `on_tick(prev, new)` and calls `state.to_graph()` internally. Community consciousness (`collective_identity`) lives in `CommunityState` objects stored in `services.community_hypergraph["community_states"]` — NOT in WorldState. The XGI hypergraph is ephemeral (built and discarded within `CommunitySystem.step()` each tick). TopologyMonitor has no access to `services`.

**Decision**: Protocol-based `CommunityStateStore` with in-memory + JSON default implementation, designed for future PostgreSQL swap.

**Rationale**: A `CommunityStateStore` Protocol defines a minimal read interface (`get_all() -> dict[CommunityType, CommunityState]`). The default implementation wraps the existing in-memory `community_states` dict and optionally serializes to JSON for persistence across sessions. BifurcationMonitor receives the store via constructor injection (dependency injection per CLAUDE.md). This design:
- Requires no WorldState schema changes
- Keeps BifurcationMonitor decoupled from storage details
- Enables a future PostgreSQL adapter implementing the same protocol
- Allows the in-memory dict to remain the runtime source of truth (CommunitySystem updates it in-place; observers run AFTER systems, so data is always current)

**Implementation**:
```python
class CommunityStateStore(Protocol):
    """Read interface for community consciousness data."""
    def get_all(self) -> dict[CommunityType, CommunityState]: ...

class InMemoryCommunityStateStore:
    """Default: wraps existing in-memory dict, optional JSON snapshot."""
    def __init__(self, states: dict[CommunityType, CommunityState]) -> None:
        self._states = states

    def get_all(self) -> dict[CommunityType, CommunityState]:
        return self._states

class BifurcationMonitor(TopologyMonitor):
    def __init__(
        self,
        community_state_store: CommunityStateStore | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._community_state_store = community_state_store
```

The `Simulation` facade wires this when `services.community_hypergraph` is available by wrapping the existing dict in `InMemoryCommunityStateStore`. If no store is given, bifurcation analysis degrades to unweighted (logs warning). Future PostgreSQL adapter implements the same `CommunityStateStore` protocol.

**Alternatives considered**:
- Raw callback injection (`Callable[[], dict]`): Works but obscures intent; a Protocol is more explicit and testable.
- Add `community_states` to WorldState: Proper long-term fix but cross-cutting schema change; out of scope for this feature.
- Store XGI hypergraph as graph-level attribute: Doesn't survive WorldState round-trip (`to_graph()` → `from_graph()`).
- Extend SimulationObserver protocol: Breaking change to all existing observers.

## R2: Sigmoid Transform for Consciousness Weighting

**Problem**: Consciousness weighting must be a qualitative filter with a breakage cliff (FR-013, Clarification Q5), not a simple scalar multiplication. Need a nonlinear transform where low collective_identity produces near-zero output and high collective_identity produces near-full output, with a sharp transition.

**Decision**: Logistic sigmoid with configurable midpoint and steepness, following existing codebase pattern.

**Rationale**: Three existing sigmoid implementations in the codebase all use `1.0 / (1.0 + math.exp(-k * (x - x0)))` with `math.exp` and overflow clamping. This is the established pattern. The midpoint (`x0`) and steepness (`k`) go in `BifurcationDefines`.

**Implementation**:
```python
def consciousness_sigmoid(collective_identity: float, midpoint: float, steepness: float) -> float:
    """Nonlinear transform creating a breakage cliff for consciousness weighting."""
    exponent = -steepness * (collective_identity - midpoint)
    exponent = max(-500.0, min(500.0, exponent))
    return 1.0 / (1.0 + math.exp(exponent))
```

With default `midpoint=0.4` and `steepness=10.0`:
- `collective_identity=0.1` → sigmoid ≈ 0.047 (near-zero, breaks under stress)
- `collective_identity=0.3` → sigmoid ≈ 0.269 (transition zone)
- `collective_identity=0.5` → sigmoid ≈ 0.731 (holds)
- `collective_identity=0.8` → sigmoid ≈ 0.982 (near-full, revolutionary potential)

The full consciousness-weighted solidarity formula:
```python
weighted = edge_resilience * consciousness_sigmoid(min(source_ci, target_ci), midpoint, steepness)
```

**Alternatives considered**:
- Linear `min()` multiplication: Fails FR-013 — no breakage cliff, assimilated solidarity at 0.2 still gives 20% weight.
- Step function (threshold cutoff): Too abrupt; no gradient for the optimizer to find.
- Exponential decay: Asymmetric — no natural saturation at high values.

## R3: Antagonism Edge Classification

**Problem**: FR-003 requires computing "lateral antagonism" per contradiction axis, but there is no `ANTAGONISTIC` EdgeType. The spec assumption says "EXPLOITATION, REPRESSION, or COMPETITION between agents on the same side" plus any `ANTAGONISTIC`-mode edges.

**Decision**: Antagonism identified by EdgeType + EdgeMode combination.

**Rationale**: `EdgeType` describes mechanical nature (EXPLOITATION, REPRESSION, COMPETITION). `EdgeMode` describes qualitative character (ANTAGONISTIC). Both are relevant:
- An EXPLOITATION edge between two workers on the same side of an axis = lateral antagonism (mechanical extraction within the group)
- An ANTAGONISTIC-mode edge of any type = open conflict

For the bifurcation analysis, "lateral antagonism" along an axis means: edges where both source and target are on the same side (both hegemonic or both marginalized for that axis) AND the edge type is EXPLOITATION, REPRESSION, or COMPETITION, OR the edge has `edge_mode=EdgeMode.ANTAGONISTIC`.

"Upward antagonism" means: edges from marginalized-side agents directed at hegemonic-side agents (class struggle directed upward).

**Alternatives considered**:
- Only EdgeType-based: Misses edges that are mechanically neutral but dialectically antagonistic.
- Only EdgeMode-based: Misses exploitative edges that don't have an explicit mode set.
- Add new ANTAGONISM EdgeType: Unnecessary; the combination of existing types covers the concept.

## R4: Betti Number Computation

**Problem**: FR-005 requires beta_0 and beta_1 on the solidarity subgraph using standard graph algorithms, not persistent homology libraries.

**Decision**: Use cycle rank formula for beta_1.

**Rationale**:
- `beta_0` = number of connected components = `len(list(nx.connected_components(G)))` (already computed by `calculate_component_metrics`)
- `beta_1` = cycle rank = `|E| - |V| + beta_0` (from graph theory: independent cycles in the cycle space)
- This is exact for graphs (1-dimensional simplicial complexes) without needing homology computation.
- `beta_2` excluded per spec constraints.

Both raw and consciousness-filtered subgraphs need Betti numbers (two-pass, per Clarification Q3).

**Alternatives considered**:
- giotto-tda persistent homology: Adds heavy dependency for a result that graph theory gives exactly.
- scipy sparse matrix null space: Over-engineered for 1D complexes.

## R5: BifurcationMonitor Architecture

**Problem**: Spec says "extension of existing TopologyMonitor." How exactly?

**Decision**: BifurcationMonitor inherits TopologyMonitor and extends `_record_snapshot`.

**Rationale**: BifurcationMonitor subclasses TopologyMonitor, overriding `_record_snapshot()` to call `super()._record_snapshot()` (preserving all existing topology metrics) then computing bifurcation analysis. This follows Open-Closed Principle — existing TopologyMonitor code untouched.

Users register `BifurcationMonitor` instead of `TopologyMonitor` to get bifurcation analysis. If they register plain `TopologyMonitor`, everything works as before.

**Implementation**:
```python
class BifurcationMonitor(TopologyMonitor):
    def _record_snapshot(self, state: WorldState, is_start: bool = False) -> None:
        super()._record_snapshot(state, is_start)
        self._record_bifurcation(state)
```

BifurcationMonitor has its own `_bifurcation_history: list[BifurcationSnapshot]` and `_previous_tendency: str | None` for event emission.

**Alternatives considered**:
- Composition (wraps TopologyMonitor): Duplicates observer registration; two separate observers complicates wiring.
- Modify TopologyMonitor directly: Violates OCP; adds complexity to all users who don't need bifurcation.
- Separate observer: Doesn't satisfy "extension of existing TopologyMonitor" (Clarification Q1).

## R6: Hypergraph Reconstruction in Observer

**Problem**: BifurcationMonitor needs an XGI hypergraph for bridge detection and axis analysis, but the hypergraph is ephemeral.

**Decision**: Rebuild the hypergraph within BifurcationMonitor using existing `build_community_hypergraph()`.

**Rationale**: `build_community_hypergraph()` is a pure function taking `memberships` and `community_states`. BifurcationMonitor can collect memberships from graph node attributes (they survive the WorldState round-trip) and get community_states from the injected provider. The hypergraph construction is lightweight (linear in number of memberships).

This follows the same pattern as CommunitySystem: build hypergraph when needed, use it, let it go.

**Alternatives considered**:
- Cache hypergraph across ticks: Stale data risk; community memberships change.
- Pass hypergraph through event bus: Architectural misuse of the event system.

## R7: Event Type for Bifurcation Tendency Change

**Problem**: FR-016 requires emitting an event when overall tendency changes between ticks. Need a new EventType.

**Decision**: Add `BIFURCATION_TENDENCY_CHANGE` to `EventType` enum and create `BifurcationTendencyEvent` model.

**Rationale**: Follows the exact pattern of `PHASE_TRANSITION` / `PhaseTransitionEvent`. The event carries the previous and new tendency, plus key metrics from the BifurcationResult.

The event count test in `test_phase_transition.py` checks `len(EventType)` — must be updated when adding the new value.

**Implementation**:
```python
# In enums.py
BIFURCATION_TENDENCY_CHANGE = "bifurcation_tendency_change"

# In events.py
class BifurcationTendencyEvent(TopologyEvent):
    event_type: EventType = Field(default=EventType.BIFURCATION_TENDENCY_CHANGE)
    previous_tendency: str  # "revolutionary" | "fascist" | "indeterminate"
    new_tendency: str
    consciousness_weighted_cross_solidarity: float
    mean_collective_identity_marginalized: float
    bridge_potential_weighted: float
    legitimation_index: float
```
