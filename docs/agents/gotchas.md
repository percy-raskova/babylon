# Common Gotchas

Lessons from debugging sessions. Read this before implementing engine code.

## WorldState.events is Per-Tick, NOT Cumulative

```python
# WRONG: Accumulating events across ticks
accumulated_events = accumulated_events + new_events
new_state = state.model_copy(update={"events": accumulated_events})

# RIGHT: Each tick gets fresh events
new_state = state.model_copy(update={"events": tick_events})
```

The engine creates fresh `WorldState` each tick. `events` contains ONLY that tick's events. "No events this tick" = `[]`, not duplicates from previous tick.

## Graph Round-Trip Can Lose Mutations

`WorldState.to_graph()` → Systems mutate graph → `WorldState.from_graph()`

**Gotcha**: `from_graph()` excludes computed fields and uses model defaults:

```python
# In from_graph(), these are excluded:
social_class_computed = {"consumption_needs"}
territory_excluded = {"p_acquiescence", "p_revolution"}
```

If you add a field to SocialClass, ensure `to_graph()` serializes it AND `from_graph()` doesn't exclude it.

**Gotcha**: Using `data.get("field", 0.0)` masks missing field bugs:

```python
# This silently uses 0.0 if s_bio missing from graph node
consumption = data.get("s_bio", 0.0) + data.get("s_class", 0.0)
```

## Systems Mutate Shared Graph In-Place

Systems execute in strict order, each seeing previous systems' mutations:

```
ImperialRent → Solidarity → Consciousness → Survival → Struggle → Contradiction → Territory → Metabolism
```

Access node data via `graph.nodes[node_id]["wealth"]`, not model attributes.

## Mypy Misses Pydantic Attribute Errors

```python
# This passes mypy but fails at runtime:
snapshot: TopologySnapshot = monitor.history[-1]
phase = snapshot.phase  # AttributeError: 'TopologySnapshot' has no attribute 'phase'
```

Pydantic models use dynamic attributes that bypass static analysis. **Runtime tests are essential.**

## Immutability via model_copy()

WorldState is frozen. ALL mutations return new instances:

```python
# WRONG
state.tick = state.tick + 1  # Raises ValidationError

# RIGHT
new_state = state.model_copy(update={"tick": state.tick + 1})
```

## Dependency Injection Over Discovery

```python
# WRONG: Discovering dependencies at runtime
def __init__(self):
    self.metrics = self._find_observer(MetricsCollector)

# RIGHT: Explicit injection
def __init__(self, metrics_collector: MetricsCollector):
    self.metrics = metrics_collector
```
