# API Contracts: Bifurcation Analysis Functions

## consciousness.py

### consciousness_sigmoid

```python
def consciousness_sigmoid(
    collective_identity: float,
    midpoint: float,
    steepness: float,
) -> float:
    """Nonlinear transform with breakage cliff for consciousness weighting.

    Args:
        collective_identity: Raw CI value [0, 1].
        midpoint: Sigmoid inflection point (from BifurcationDefines).
        steepness: Slope at inflection (from BifurcationDefines).

    Returns:
        Transformed value [0, 1]. Near-zero below midpoint, near-one above.
    """
```

### consciousness_weighted_solidarity

```python
def consciousness_weighted_solidarity(
    edge: GraphEdge,
    graph: GraphProtocol,
    H: xgi.Hypergraph,
    community_states: dict[CommunityType, CommunityState],
    defines: BifurcationDefines,
) -> float:
    """Weight a solidarity edge by consciousness of connected agents' communities.

    Args:
        edge: A SOLIDARITY edge from the graph.
        graph: The simulation graph (for node attribute access).
        H: XGI hypergraph (for community membership lookup).
        community_states: Current community consciousness data.
        defines: Configurable parameters (sigmoid midpoint/steepness).

    Returns:
        Weighted solidarity value. Near-zero for assimilated communities,
        near-full for oppositional consciousness.
    """
```

## axis.py

### crosses_contradiction_axis

```python
def crosses_contradiction_axis(
    source_id: str,
    target_id: str,
    axis: ContradictionAxis,
    agent_memberships: dict[str, set[CommunityType]],
) -> bool:
    """Check whether an edge crosses a contradiction axis.

    Returns True if one endpoint is on the hegemonic side and the other
    is on the marginalized side of the given axis.
    """
```

### classify_edge_antagonism

```python
def classify_edge_antagonism(
    edge: GraphEdge,
    axis: ContradictionAxis,
    agent_memberships: dict[str, set[CommunityType]],
) -> Literal["lateral", "upward", "downward", "none"]:
    """Classify an antagonistic edge's direction relative to a contradiction axis.

    - lateral: both endpoints on the same side (within-group antagonism)
    - upward: from marginalized toward hegemonic (class struggle)
    - downward: from hegemonic toward marginalized (repression)
    - none: neither endpoint is on this axis
    """
```

### compute_axis_tendency

```python
def compute_axis_tendency(
    graph: GraphProtocol,
    H: xgi.Hypergraph,
    axis: ContradictionAxis,
    community_states: dict[CommunityType, CommunityState],
    agent_memberships: dict[str, set[CommunityType]],
    defines: BifurcationDefines,
) -> AxisTendency:
    """Compute solidarity vs antagonism balance along a single contradiction axis.

    Returns AxisTendency with tendency_ratio: >1.0 = solidarity-dominant,
    <1.0 = antagonism-dominant.
    """
```

## bridges.py

### detect_bridges

```python
def detect_bridges(
    H: xgi.Hypergraph,
    community_states: dict[CommunityType, CommunityState],
    axes: list[ContradictionAxis],
    defines: BifurcationDefines,
) -> list[BridgeInfo]:
    """Detect communities spanning contradiction axes and weight by consciousness.

    Only INSTITUTIONAL_EXCLUSION communities are candidates (lifecycle excluded).
    Bridge potential = infrastructure * sigmoid(collective_identity).
    """
```

## resilience.py

### compute_betti_numbers

```python
def compute_betti_numbers(subgraph: nx.Graph) -> tuple[int, int]:
    """Compute beta_0 and beta_1 for an undirected graph.

    beta_0 = number of connected components
    beta_1 = cycle rank = |E| - |V| + beta_0

    Returns:
        (beta_0, beta_1) tuple.
    """
```

### compute_equivalence_classes

```python
def compute_equivalence_classes(subgraph: nx.Graph) -> dict[int, int]:
    """Group nodes by identical neighbor sets, return size distribution.

    Returns:
        Dict mapping class_size -> count_of_classes_with_that_size.
    """
```

### find_critical_singletons

```python
def find_critical_singletons(subgraph: nx.Graph) -> list[str]:
    """Find articulation points whose removal increases beta_0.

    Returns:
        List of node IDs that are articulation points.
    """
```

### find_critical_cutsets

```python
def find_critical_cutsets(
    subgraph: nx.Graph,
    max_cutset_size: int = 3,
) -> list[frozenset[str]]:
    """Find minimal edge sets whose removal disconnects a component.

    Uses nx.minimum_edge_cut on each connected component.
    max_cutset_size limits search to small cutsets for performance.

    Returns:
        List of frozensets of node-pair tuples representing edge cutsets.
    """
```

### compute_purge_resilience

```python
def compute_purge_resilience(
    subgraph: nx.Graph,
    removal_rate: float,
    seed: int | None = None,
) -> float:
    """Targeted purge resilience: post-purge L_max / pre-purge L_max.

    Returns:
        Resilience ratio [0, 1]. Higher = more resilient.
    """
```

## ceiling.py

### compute_solidarity_ceiling

```python
def compute_solidarity_ceiling(
    node_a_id: str,
    node_b_id: str,
    graph: GraphProtocol,
    agent_memberships: dict[str, set[CommunityType]],
    defines: BifurcationDefines,
) -> SolidarityCeiling:
    """Compute material constraints on solidarity formation between two agents.

    Ceiling from wage gap ratio (interpolated between thresholds),
    plus bonuses for shared exploitation source and community membership.
    """
```

## legitimation.py

### compute_legitimation_amplifier

```python
def compute_legitimation_amplifier(
    graph: GraphProtocol,
    defines: BifurcationDefines,
) -> float:
    """Aggregate DPD legitimation index across territories into crisis amplifier.

    Reads legitimation_index from territory node attributes (set by LifecycleSystem).
    Population-weighted mean. Low legitimation → amplifier > 1.0.

    Returns:
        Crisis amplifier >= 1.0. Higher = more intense bifurcation.
    """
```

## analysis.py

### bifurcation_tendency

```python
def bifurcation_tendency(
    graph: GraphProtocol,
    H: xgi.Hypergraph,
    community_states: dict[CommunityType, CommunityState],
    defines: BifurcationDefines,
) -> BifurcationResult:
    """Compute full bifurcation analysis — the George Jackson model.

    Combines:
    1. Per-axis contradiction tendency (weakest-link)
    2. Community bridge potential (consciousness-weighted)
    3. Legitimation crisis amplifier (DPD integration)
    4. Topological resilience (two-pass: raw + filtered Betti numbers)

    Classification rules (weakest-link model):
    - All axes solidarity-dominant → "revolutionary" (if resilience adequate)
    - Any axis deeply antagonism-dominant → "fascist"
    - Marginal antagonism with bridge counterpressure → "indeterminate"
    """
```

## bifurcation_monitor.py

### CommunityStateStore

```python
class CommunityStateStore(Protocol):
    """Read interface for community consciousness data.

    Default implementation wraps the existing in-memory dict.
    Future PostgreSQL adapter implements the same protocol.
    """

    def get_all(self) -> dict[CommunityType, CommunityState]:
        """Return current community states snapshot."""
        ...
```

### InMemoryCommunityStateStore

```python
class InMemoryCommunityStateStore:
    """Default store wrapping the existing in-memory community_states dict.

    Args:
        states: Reference to the mutable community_states dict
            maintained by CommunitySystem.
    """

    def __init__(
        self,
        states: dict[CommunityType, CommunityState],
    ) -> None: ...

    def get_all(self) -> dict[CommunityType, CommunityState]: ...
```

### BifurcationMonitor

```python
class BifurcationMonitor(TopologyMonitor):
    """Extended topology observer with bifurcation analysis.

    Inherits all TopologyMonitor functionality (percolation, liquidity,
    phase classification, resilience testing). Adds consciousness-weighted
    bifurcation analysis per tick.

    Register instead of TopologyMonitor to get bifurcation analysis:
        store = InMemoryCommunityStateStore(community_states)
        monitor = BifurcationMonitor(community_state_store=store)
        sim = Simulation(state, config, observers=[monitor])
    """

    def __init__(
        self,
        community_state_store: CommunityStateStore | None = None,
        **kwargs: Any,
    ) -> None: ...

    @property
    def bifurcation_history(self) -> list[BifurcationSnapshot]: ...

    def get_pending_events(self) -> list[SimulationEvent]: ...
```
