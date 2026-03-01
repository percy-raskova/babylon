# Quickstart: Bifurcation Topology Analysis

## Setup

No new dependencies. Uses existing NetworkX, XGI, and Pydantic.

## Usage

### Basic — Register BifurcationMonitor

```python
from babylon.engine.bifurcation_monitor import (
    BifurcationMonitor,
    InMemoryCommunityStateStore,
)
from babylon.engine.simulation import Simulation

# Community states from existing CommunitySystem wiring
community_states = {
    CommunityType.NEW_AFRIKAN: CommunityState(
        community_type=CommunityType.NEW_AFRIKAN,
        consciousness=CommunityConsciousness(collective_identity=Probability(0.7)),
    ),
    # ... other communities
}

# Wrap in protocol-based store (future: swap to PostgresCommunityStateStore)
store = InMemoryCommunityStateStore(community_states)

# Create monitor with store
monitor = BifurcationMonitor(community_state_store=store)

# Register as observer (replaces TopologyMonitor)
sim = Simulation(state, config, observers=[monitor])
sim.run(ticks=20)

# Access results
for snapshot in monitor.bifurcation_history:
    print(f"Tick {snapshot.tick}: {snapshot.result.overall_tendency}")
    print(f"  Colonial axis: {snapshot.result.per_axis_tendency.get('colonial', 0):.2f}")
    print(f"  Raw beta_1: {snapshot.result.raw_beta_1}")
    print(f"  Filtered beta_1: {snapshot.result.filtered_beta_1}")
```

### Standalone Analysis (no engine)

```python
from babylon.bifurcation.analysis import bifurcation_tendency
from babylon.bifurcation.types import BifurcationResult
from babylon.config.defines import GameDefines

defines = GameDefines().bifurcation
graph = state.to_graph()
wrapped = NetworkXAdapter.wrap(graph)

# Build hypergraph from memberships
memberships = collect_all_memberships(wrapped)
H = build_community_hypergraph(memberships, community_states)

# Run analysis
result: BifurcationResult = bifurcation_tendency(wrapped, H, community_states, defines)
print(result.overall_tendency)  # "revolutionary" | "fascist" | "indeterminate"
```

### Individual Functions

```python
from babylon.bifurcation.consciousness import consciousness_weighted_solidarity
from babylon.bifurcation.resilience import compute_betti_numbers
from babylon.bifurcation.bridges import detect_bridges

# Weight a single edge
weight = consciousness_weighted_solidarity(edge, graph, H, community_states, defines)

# Compute Betti numbers
beta_0, beta_1 = compute_betti_numbers(solidarity_subgraph)

# Detect bridges
bridges = detect_bridges(H, community_states, CONTRADICTION_AXES, defines)
for bridge in bridges:
    print(f"{bridge.community_type}: potential={bridge.weighted_potential:.2f}")
```

## Testing

```bash
# Run all bifurcation tests
poetry run pytest tests/unit/bifurcation/ -v

# Run specific user story
poetry run pytest tests/unit/bifurcation/test_consciousness.py -v  # US1
poetry run pytest tests/unit/bifurcation/test_analysis.py -v       # US5 (assimilation trap)

# Integration with engine
poetry run pytest tests/integration/topology/test_bifurcation_integration.py -v
```

## Key Validation

The critical test — the assimilation trap:

```python
def test_assimilation_trap():
    """High cross-line solidarity + low CI = fascist, not revolutionary."""
    # Build graph with 20+ cross-line SOLIDARITY edges
    # All marginalized communities have collective_identity <= 0.2
    result = bifurcation_tendency(graph, H, community_states, defines)
    assert result.overall_tendency == "fascist"
    # The gap between raw and filtered Betti numbers reveals the trap:
    assert result.raw_beta_1 > 0       # Looks robust
    assert result.filtered_beta_1 == 0  # Actually fragile
```
