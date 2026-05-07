# Contract: WorldState Round-Trip Identity (US4 — INV-012)

**Predicate ID**: INV-012
**User Story**: US4 (P3)
**Source**: [spec.md §US4](../spec.md#user-story-4--worldstate-graph-round-trip-as-a-property-priority-p3)
**Tests**: `tests/property/invariants/test_round_trip_identity.py`
**Constitution**: II.6 (State is Data, Engine is Transformation)

## Predicate

For every `WorldState` instance produced by `worldstate_strategy()`:

```text
∀ state ∈ WorldStrategy:
    let restored = WorldState.from_graph(state.to_graph(), tick=state.tick)
    restored.model_dump(exclude=PRODUCTION_EXCLUDE) ==
        state.model_dump(exclude=PRODUCTION_EXCLUDE)
```

Where `PRODUCTION_EXCLUDE` is read from production code at test collection
time per FR-010 (research §8 — refactor `from_graph` to expose the exclude
sets as named constants if not already exposed).

## Inputs (Hypothesis strategies)

| Strategy | Source |
|----------|--------|
| `worldstate_strategy()` | `tests/property/strategies/worldstate.py` (existing — Spec 040) |
| `worldstate_strategy(max_entities=8, max_relationships=8)` | Same strategy with bumped bounds for Predicate B (size-stress) |

## Test predicates

### Predicate A — Round-trip preserves model_dump modulo exclude-set

```python
@given(state=worldstate_strategy())
@settings(max_examples=200, derandomize=True)
def test_round_trip_preserves_model_dump(state):
    """Predicate A: from_graph(to_graph(state)) preserves model_dump exactly."""
    graph = state.to_graph()
    restored = WorldState.from_graph(graph, tick=state.tick)

    exclude = _build_exclude_set_from_production()
    assert restored.model_dump(exclude=exclude) == state.model_dump(exclude=exclude)
```

### Predicate B — Round-trip works at maximum-supported size within budget

```python
@given(state=worldstate_strategy(max_entities=8, max_relationships=8))
@settings(max_examples=50, derandomize=True, deadline=2000)  # 2 s per example
def test_round_trip_at_max_size(state):
    """Predicate B: round-trip on larger states still preserves model_dump."""
    graph = state.to_graph()
    restored = WorldState.from_graph(graph, tick=state.tick)

    exclude = _build_exclude_set_from_production()
    assert restored.model_dump(exclude=exclude) == state.model_dump(exclude=exclude)
```

### Predicate C — Every legal `EdgeType` round-trips faithfully

```python
@given(
    state=st.builds(
        _build_state_with_one_edge_per_type,
        edge_types=st.just(list(EdgeType)),
    )
)
@settings(max_examples=20, derandomize=True)
def test_round_trip_preserves_every_edge_type(state):
    """Predicate C: every EdgeType value survives the round-trip."""
    graph = state.to_graph()
    restored = WorldState.from_graph(graph, tick=state.tick)

    pre_edge_types = sorted(rel.edge_type for rel in state.relationships)
    post_edge_types = sorted(rel.edge_type for rel in restored.relationships)
    assert pre_edge_types == post_edge_types

    # Stronger: per-edge field-level equality
    for pre_rel, post_rel in zip(state.relationships, restored.relationships, strict=True):
        assert pre_rel.source_id == post_rel.source_id
        assert pre_rel.target_id == post_rel.target_id
        assert pre_rel.edge_type == post_rel.edge_type
        assert pre_rel.value_flow == pytest.approx(post_rel.value_flow)
        assert pre_rel.tension == pytest.approx(post_rel.tension)
```

## Helpers

```python
def _build_exclude_set_from_production() -> set[str]:
    """Read the from_graph exclude rules from production at runtime.

    The production code in src/babylon/models/world_state.py declares
    which fields are computed (consumption_needs) or excluded
    (p_acquiescence, p_revolution on Territory) during from_graph
    reconstruction. This helper imports those constants and assembles a
    set suitable for model_dump's `exclude=` parameter.

    The 'tick' field is always excluded (passed explicitly to
    from_graph; not derived from the graph itself).

    Reading from production at test time guarantees that adding a new
    computed field to from_graph automatically extends the test exclude
    set with no parallel edit (FR-010).
    """
    from babylon.models.world_state import (
        _SOCIAL_CLASS_COMPUTED_FIELDS,
        _TERRITORY_EXCLUDED_FIELDS,
    )
    exclude = {"tick"}
    # ... assemble nested-field-path exclude set per pydantic v2 conventions
    return exclude
```

## Failure modes

| Cause | Symptom | Remediation |
|-------|---------|-------------|
| A new field is added to `SocialClass` but not to the `to_graph` serializer | Predicate A fails: pre_dump contains the field, post_dump doesn't | Update `to_graph` to serialize the new field via `model_dump()`; update `from_graph` to deserialize it (and add to exclude set if it's computed) |
| `from_graph` uses `data.get("field", default)` and silently substitutes a default | Predicate A fails when the original value differs from the default | Replace `.get(default)` with `data["field"]` so missing fields raise loudly during round-trip |
| A new EdgeType is added but `to_graph` doesn't serialize the edge metadata | Predicate C fails: edge type lost or coerced | Update `to_graph` and `from_graph` together for any new EdgeType |

## Out of scope

- Cross-version round-trip (a graph serialized by an older `WorldState`
  schema and deserialized by a newer one) — separate compat-test
  concern.
- Round-trip through Postgres / pickle / JSON serialization — only the
  in-memory graph round-trip is in scope.
- Round-trip equality on computed fields — these are explicitly
  excluded by `from_graph` and are out-of-scope by design.
