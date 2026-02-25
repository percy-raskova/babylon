# Quickstart: Dialectical Field Topology

**Feature**: 002-dialectical-field-topology
**Branch**: `002-dialectical-field-topology`

## Prerequisites

- Python 3.12+
- Poetry environment: `poetry install`
- scipy (new dependency): `poetry add scipy`
- Existing systems functional (systems 1-13 in simulation engine)

## Development Workflow

### 1. Run existing tests first

```bash
mise run test:unit    # Verify baseline passes
```

### 2. Implementation order

Follow system ordering (each depends on the previous):

1. **EdgeMode enum** (`src/babylon/models/enums.py`)
   - Add `EdgeMode(StrEnum)` with 5 values
   - No existing code affected (new attribute, separate from EdgeType)

2. **Field Registry** (`src/babylon/engine/field_registry.py`)
   - Open registry mapping field names to computation + normalization callables
   - Register 4 initial fields: exploitation, immiseration, imperial_rent, displacement

3. **ContradictionFieldSystem** (`src/babylon/engine/systems/contradiction_field.py`)
   - Reads from economic calculator outputs on nodes
   - Writes `contradiction_fields: dict[str, float]` to each node
   - Writes to `persistent_data["contradiction_history"]` for temporal derivatives

4. **FieldDerivativeSystem** (`src/babylon/engine/systems/field_derivative.py`)
   - Reads `contradiction_fields` from nodes and history from `persistent_data`
   - Computes gradient (edge), Laplacian (node), df/dt, d2f/dt2
   - Writes `field_derivatives` to nodes and `field_gradients` to edges

5. **Ollivier-Ricci curvature** (`src/babylon/formulas/curvature.py`)
   - Pure function: `compute_ollivier_ricci(graph, alpha=0.5) -> dict[tuple, float]`
   - Uses scipy.optimize.linprog for Wasserstein-1 distance
   - Called by FieldDerivativeSystem only when topology changes

6. **EdgeTransitionSystem** (`src/babylon/engine/systems/edge_transition.py`)
   - Evaluates compound predicates against field values and derivatives
   - Fires edge mode transitions per the state machine
   - Handles CO-OPTIVE suppression, latent contradiction, and bifurcation

### 3. Key patterns to follow

**Auto-wrap guard** (every system method that tests call directly):
```python
from babylon.engine.graph_protocol import GraphProtocol
from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

def step(self, graph, services, context):
    if not isinstance(graph, GraphProtocol):
        graph = NetworkXAdapter.wrap(graph)
    # ... system logic
```

**Nested dict write** (copy-modify-writeback):
```python
fields = dict(node.attributes.get("contradiction_fields", {}))
fields["exploitation"] = new_value
graph.update_node(node.node_id, contradiction_fields=fields)
```

**Cross-tick state**:
```python
history = context.persistent_data.setdefault("contradiction_history", {})
```

### 4. Testing

```bash
# Unit tests for individual systems
poetry run pytest tests/unit/engine/test_contradiction_field_system.py -v

# Math tests for curvature
poetry run pytest tests/unit/formulas/test_curvature.py -v

# Integration test for multi-tick evolution
poetry run pytest tests/integration/test_field_topology_integration.py -v

# Full suite
mise run test:unit
```

### 5. Type checking

```bash
poetry run mypy src/babylon/engine/systems/contradiction_field.py --strict
poetry run mypy src/babylon/engine/systems/field_derivative.py --strict
poetry run mypy src/babylon/engine/systems/edge_transition.py --strict
```

## Key Files Reference

| File | Purpose |
|------|---------|
| `src/babylon/engine/systems/protocol.py` | System protocol: `step(graph, services, context)` |
| `src/babylon/engine/graph_protocol.py` | GraphProtocol (18 methods) |
| `src/babylon/engine/adapters/inmemory_adapter.py` | NetworkXAdapter with `wrap()` |
| `src/babylon/engine/context.py` | TickContext with `persistent_data` |
| `src/babylon/models/enums.py` | All enums (add EdgeMode here) |
| `src/babylon/engine/simulation_engine.py` | System execution order |
| `src/babylon/config/defines.py` | GameDefines thresholds |
