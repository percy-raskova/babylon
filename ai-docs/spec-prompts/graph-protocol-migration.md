# Implementation Prompt: GraphProtocol Enforcement Migration

**Load this into plan mode. Read every file referenced. Implement in order.**

---

## Context

Babylon has a well-designed `GraphProtocol` (16 methods) and a working
`NetworkXAdapter` implementation. **Neither is used by any engine system.**
All 13 systems bypass the protocol and call raw NetworkX methods directly
on `nx.DiGraph`. This makes the protocol a dead abstraction and blocks
future backend migration (DuckDB).

This is a mechanical refactoring — no new features, no new algorithms.
Every raw NetworkX call has an existing protocol equivalent. The goal is
to enforce the protocol boundary so all new code (Volume I gaps, Detroit
vertical slice) is born clean.

**Scope**: ~86 node accesses, ~38 edge/iteration accesses, ~77 `nx.DiGraph`
type annotations across 22 files. Zero behavioral changes. All existing
tests must pass without modification.

---

## What Already Exists (READ ALL OF THESE FIRST)

### Protocol Layer (the interface you're enforcing)

```
src/babylon/engine/graph_protocol.py          # 16-method GraphProtocol (typing.Protocol)
src/babylon/engine/adapters/inmemory_adapter.py # NetworkXAdapter (reference implementation)
src/babylon/engine/adapters/query_mixin.py     # query_nodes, query_edges implementations
src/babylon/engine/adapters/aggregation_mixin.py # aggregate implementation
src/babylon/engine/adapters/subgraph_view.py   # SubgraphView for get_neighborhood
src/babylon/engine/adapters/subgraph_filter.py # Filter logic
src/babylon/models/graph.py                    # GraphNode, GraphEdge, TraversalQuery, TraversalResult
```

### System Layer (files you're migrating)

```
src/babylon/engine/systems/protocol.py         # System protocol — ROOT CAUSE (nx.DiGraph in signature)
src/babylon/engine/systems/economic.py         # 30 graph.nodes[ + 9 graph.edges — LARGEST
src/babylon/engine/systems/territory.py        # 10 graph.nodes[ + 6 graph.edges/iterations
src/babylon/engine/systems/vitality.py         # 8 graph.nodes[ + 1 graph.edges
src/babylon/engine/systems/struggle.py         # 7 graph.nodes[ + 5 graph.edges/in_edges
src/babylon/engine/systems/decomposition.py    # 7 graph.nodes[ + 1 iteration
src/babylon/engine/systems/solidarity.py       # 6 graph.nodes[ + 1 graph.edges
src/babylon/engine/systems/production.py       # 6 graph.nodes[ + 4 graph.edges/out_edges
src/babylon/engine/systems/contradiction.py    # 4 graph.nodes[ + 2 graph.edges
src/babylon/engine/systems/ideology.py         # 3 graph.nodes[ + 2 graph.edges/in_edges
src/babylon/engine/systems/metabolism.py        # 1 graph.nodes[ + 3 iterations
src/babylon/engine/systems/survival.py         # 2 graph.nodes[ + 2 iterations
src/babylon/engine/systems/event_template.py   # 2 graph.nodes[ + 4 nx.DiGraph annotations
src/babylon/engine/systems/control_ratio.py    # 2 iterations + 3 nx.DiGraph annotations
```

### Orchestration Layer (wiring you're updating)

```
src/babylon/engine/simulation_engine.py        # SimulationEngine.run_tick(graph: nx.DiGraph)
src/babylon/engine/event_evaluator.py          # 12 nx.DiGraph type annotations
src/babylon/engine/topology_monitor.py         # Direct nx.Graph(), nx.connected_components()
src/babylon/models/world_state.py              # to_graph() returns nx.DiGraph, from_graph() accepts it
```

---

## The Root Cause

In `src/babylon/engine/systems/protocol.py` line 28:

```python
def step(
    self,
    graph: nx.DiGraph[str],  # <-- This is the problem
    services: ServiceContainer,
    context: ContextType,
) -> None:
```

The `System` protocol declares its graph parameter as concrete `nx.DiGraph`.
This cascades: every system implementation accepts `nx.DiGraph`, every system
uses raw NetworkX methods, and the engine passes a raw graph.

---

## Migration Strategy

### Phase 1: Protocol Signature (1 file, cascading type changes)

**Change the System protocol to accept GraphProtocol instead of nx.DiGraph.**

File: `src/babylon/engine/systems/protocol.py`

```python
# BEFORE
import networkx as nx
# ...
def step(self, graph: nx.DiGraph[str], ...) -> None:

# AFTER
from babylon.engine.graph_protocol import GraphProtocol
# ...
def step(self, graph: GraphProtocol, ...) -> None:
```

Then update `SimulationEngine.run_tick()` in `simulation_engine.py`:

```python
# BEFORE
def run_tick(self, graph: nx.DiGraph[str], ...) -> None:

# AFTER
def run_tick(self, graph: GraphProtocol, ...) -> None:
```

And the `step()` function in `simulation_engine.py`:

```python
# BEFORE
G = state.to_graph()  # returns nx.DiGraph

# AFTER — wrap in adapter
from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter
raw_graph = state.to_graph()  # still returns nx.DiGraph internally
G = NetworkXAdapter(raw_graph)  # wrap for protocol compliance
```

Update `_restore_graph_context` and `_save_graph_context` to use the adapter's
internal graph (add a `._graph` accessor or pass the raw graph separately).

**Do NOT change `WorldState.to_graph()` or `WorldState.from_graph()` yet.**
Those are in the model layer and can continue returning `nx.DiGraph` internally.
The adapter wraps it at the engine boundary.

### Phase 2: Node Access Pattern Migration (12 system files)

Replace raw `graph.nodes[id]` accesses with protocol methods.

**Pattern A: Read node attribute**

```python
# BEFORE
data = graph.nodes[node_id]
wealth = data.get("wealth", 0.0)
role = data.get("role")
active = data.get("active", True)

# AFTER
node = graph.get_node(node_id)
if node is None:
    continue  # or return, depending on context
wealth = node.attributes.get("wealth", 0.0)
role = node.attributes.get("role")
active = node.attributes.get("active", True)
```

**Pattern B: Update node attribute**

```python
# BEFORE
graph.nodes[node_id]["wealth"] = new_value
graph.nodes[node_id]["consciousness"] = new_consciousness

# AFTER
graph.update_node(node_id, wealth=new_value)
graph.update_node(node_id, consciousness=new_consciousness)
```

**Note**: Multiple attribute updates on the same node in the same block can
be batched into a single `update_node()` call:

```python
# BEFORE
graph.nodes[nid]["wealth"] = w
graph.nodes[nid]["consciousness"] = c
graph.nodes[nid]["agitation"] = a

# AFTER
graph.update_node(nid, wealth=w, consciousness=c, agitation=a)
```

**Pattern C: Check node existence**

```python
# BEFORE
if node_id in graph.nodes:

# AFTER
if graph.get_node(node_id) is not None:
```

### Phase 3: Edge Access Pattern Migration (12 system files)

**Pattern D: Iterate edges with data**

```python
# BEFORE
for source_id, target_id, data in graph.edges(data=True):
    if data.get("type") == "EXPLOITATION":
        value_flow = data.get("value_flow", 0.0)

# AFTER
for edge in graph.query_edges(edge_type="EXPLOITATION"):
    source_id = edge.source_id
    target_id = edge.target_id
    value_flow = edge.attributes.get("value_flow", 0.0)
```

**Pattern E: Update edge attribute**

```python
# BEFORE
graph.edges[source_id, target_id]["value_flow"] = rent

# AFTER
graph.update_edge(source_id, target_id, edge_type="EXPLOITATION", value_flow=rent)
```

Note: `update_edge` requires the edge_type discriminator. You must know the
edge type at the call site. In most cases it's already been checked in the
enclosing conditional (e.g., `if data.get("type") == "EXPLOITATION"`).

**Pattern F: Directional edge queries (in_edges / out_edges)**

```python
# BEFORE
for source_id, _, data in graph.in_edges(node_id, data=True):
    if data.get("type") == "SOLIDARITY":
        ...

# AFTER
neighborhood = graph.get_neighborhood(node_id, radius=1,
                                       edge_types={"SOLIDARITY"},
                                       direction="in")
# neighborhood is SubgraphView — iterate its nodes/edges
# OR use query_edges with source/target filter
for edge in graph.query_edges(edge_type="SOLIDARITY"):
    if edge.target_id == node_id:
        ...
```

The `get_neighborhood()` approach is more performant for dense neighborhoods.
The `query_edges()` approach is simpler for sparse lookups. Choose based on
context — prefer `get_neighborhood()` when the system already needs the
neighbor nodes too.

### Phase 4: Node Iteration Pattern Migration

**Pattern G: Iterate all nodes of a type**

```python
# BEFORE
for node_id in graph.nodes():
    data = graph.nodes[node_id]
    if data.get("_node_type") != "social_class":
        continue
    # process node

# AFTER
for node in graph.query_nodes(node_type="social_class"):
    node_id = node.id
    # access via node.attributes or node.wealth (convenience property)
```

**Pattern H: Iterate all nodes with data**

```python
# BEFORE
for node_id, data in graph.nodes(data=True):
    role = data.get("role")

# AFTER
for node in graph.query_nodes():
    role = node.attributes.get("role")
```

### Phase 5: Topology Monitor Migration

`topology_monitor.py` directly creates `nx.Graph()` objects and calls
`nx.connected_components()`. Replace with `execute_traversal()`.

```python
# BEFORE (build_solidarity_graph)
solidarity_graph: nx.Graph[str] = nx.Graph()
for u, v, data in G.edges(data=True):
    if data.get("type") == "SOLIDARITY":
        solidarity_graph.add_edge(u, v, weight=data.get("weight", 0.0))

# AFTER
from babylon.models.graph import TraversalQuery
result = graph.execute_traversal(TraversalQuery(
    query_type="connected_components",
    start_node=None,  # whole graph
    edge_filter=EdgeFilter(edge_types={"SOLIDARITY"}),
))
components = result.components
```

```python
# BEFORE (calculate_percolation_ratio)
components = list(nx.connected_components(solidarity_graph))

# AFTER
# Already handled by execute_traversal above
percolation_ratio = result.percolation_ratio
```

The topology monitor functions accept `nx.DiGraph` parameters. Change them
to accept `GraphProtocol`.

### Phase 6: Event Evaluator Type Annotations

`event_evaluator.py` has 12 `nx.DiGraph` type annotations. Replace all with
`GraphProtocol`. These are pure type changes — no behavioral impact.

### Phase 7: WorldState Adapter Boundary

`WorldState.to_graph()` returns `nx.DiGraph`. Do NOT change this method.
Instead, the wrapping happens at the `step()` function boundary in
`simulation_engine.py` (already done in Phase 1).

`WorldState.from_graph()` accepts `nx.DiGraph`. This stays as-is because
the adapter wraps the raw graph — when you need to call `from_graph()`,
unwrap it:

```python
# In step() after systems have run:
raw_graph = G._graph  # NetworkXAdapter exposes underlying nx.DiGraph
return WorldState.from_graph(raw_graph, tick=state.tick + 1, ...)
```

If `NetworkXAdapter` does not expose `._graph`, add a property:

```python
# In inmemory_adapter.py
@property
def underlying_graph(self) -> nx.DiGraph[str]:
    """Access the underlying NetworkX graph for serialization."""
    return self._graph
```

This is acceptable because the serialization boundary (WorldState conversion)
is an infrastructure concern, not a system concern. Systems never see this.

---

## File-by-File Execution Order

Process in this exact order to maintain a working codebase at each step:

1. **`inmemory_adapter.py`** — Add `underlying_graph` property if missing
2. **`systems/protocol.py`** — Change `nx.DiGraph[str]` → `GraphProtocol`
3. **`simulation_engine.py`** — Wrap graph in adapter, update type annotations
4. **`systems/economic.py`** — Largest file (30+9 replacements). Do this first
   to establish the migration pattern. Run `mise run test:unit` after.
5. **`systems/territory.py`** — 10+6 replacements
6. **`systems/vitality.py`** — 8+1 replacements
7. **`systems/struggle.py`** — 7+5 replacements
8. **`systems/decomposition.py`** — 7+1 replacements
9. **`systems/solidarity.py`** — 6+1 replacements
10. **`systems/production.py`** — 6+4 replacements
11. **`systems/contradiction.py`** — 4+2 replacements
12. **`systems/ideology.py`** — 3+2 replacements
13. **`systems/survival.py`** — 2+2 replacements
14. **`systems/metabolism.py`** — 1+3 replacements
15. **`systems/event_template.py`** — 2+4 type annotation replacements
16. **`systems/control_ratio.py`** — 2+3 replacements
17. **`event_evaluator.py`** — 12 type annotation replacements
18. **`topology_monitor.py`** — 6 structural replacements (build_solidarity_graph etc.)

**Commit after each phase** (not each file). Suggested commits:
- `refactor(engine): change System protocol to accept GraphProtocol`
- `refactor(systems): migrate node/edge access to GraphProtocol`
- `refactor(engine): migrate topology_monitor to GraphProtocol`
- `refactor(engine): migrate event_evaluator type annotations`

---

## Critical Constraints

### DO NOT change:
- `WorldState.to_graph()` or `WorldState.from_graph()` signatures
- Any test file (tests should pass without changes)
- System execution order
- Any formula or algorithm
- Any event payload structure

### DO verify at each step:
- `mise run test:unit` passes (6,091 tests)
- `mise run lint` is clean
- `mise run typecheck` produces no NEW errors (37 pre-existing UI errors OK)
- No `import networkx` in any system file (except `TYPE_CHECKING` blocks
  that will be removed as annotations change)

### Edge cases to watch:
- **`graph.nodes[id]` as lvalue** (assignment): Must become `graph.update_node()`
- **`graph.nodes[id]` as rvalue** (read): Must become `graph.get_node()` + `.attributes`
- **`graph.edges[s, t]` as lvalue**: Must become `graph.update_edge()` with edge_type
- **`graph.edges(data=True)` iteration**: Must become `graph.query_edges()`
- **`graph.in_edges(id, data=True)`**: Must become `graph.get_neighborhood(direction="in")` or filtered `query_edges()`
- **`graph.out_edges(id, data=True)`**: Must become `graph.get_neighborhood(direction="out")` or filtered `query_edges()`
- **`node_id in graph.nodes`**: Must become `graph.get_node(id) is not None`
- **`data.get("_node_type")`**: Replaced by `node.node_type` on GraphNode
- **`data.get("type")` on edges**: Replaced by `edge.edge_type` on GraphEdge
- **`graph.graph["key"]`** (graph-level attributes in simulation_engine.py):
  This is a NetworkX-specific feature. Keep it behind the adapter boundary
  only — it's used for `tick_dynamics` persistence. Do NOT expose this in
  GraphProtocol.

### Performance note:
`graph.get_node()` returns a `GraphNode` Pydantic model (frozen, validated).
This adds object creation overhead vs raw dict access. For hot loops with
many nodes, consider caching the node object or using `query_nodes()` which
returns an iterator. The overhead is negligible for Detroit's graph size
(~10-20 nodes) but matters if the graph scales to thousands of nodes.

---

## Verification Criteria

1. **Zero `graph.nodes[` in system files** — grep must return 0 matches
2. **Zero `graph.edges(data=True)` in system files** — grep must return 0
3. **Zero `import networkx` in system files** (outside TYPE_CHECKING) — grep 0
4. **Zero `nx.DiGraph` annotations in system files** — grep must return 0
5. **All 6,091 unit tests pass** — `mise run test:unit`
6. **Lint clean** — `mise run lint`
7. **Typecheck no new errors** — `mise run typecheck` (37 pre-existing OK)
8. **Integration tests pass** — `mise run test:int`
9. **GraphProtocol isinstance check** — add a test that verifies
   `isinstance(NetworkXAdapter(nx.DiGraph()), GraphProtocol)` returns True

---

## What NOT to Build

- No DuckDB adapter (that's a future feature)
- No new protocol methods (the existing 16 are sufficient)
- No performance optimization (premature for Detroit's graph size)
- No changes to the graph model types (GraphNode, GraphEdge, etc.)
- No new test infrastructure (existing tests validate behavior)
- No migration of `WorldState.to_graph()` / `from_graph()` internals
