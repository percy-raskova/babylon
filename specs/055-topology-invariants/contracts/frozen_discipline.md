# Contract: Frozen Pydantic Discipline (US3 — INV-011)

**Predicate ID**: INV-011
**User Story**: US3 (P2)
**Source**: [spec.md §US3](../spec.md#user-story-3--frozen-pydantic-discipline-across-a-tick-priority-p2)
**Tests**: `tests/property/invariants/test_frozen_discipline.py`
**Constitution**: III.7 (Determinism Hash and Replayability), II.6 (State is Data, Engine is Transformation)

## Predicates (two layers)

### Layer 1 — Static class-level structural assertion (collection time)

```text
∀ cls ∈ discover_state_bearing_models():
    cls.model_config.get("frozen") is True
    OR cls has bypasses_topology_invariant marker with "frozen_discipline" key + non-empty justification
```

### Layer 2 — Runtime per-tick identity check

```text
∀ entity_id ∈ snapshot_ids(pre_state).keys() ∩ entities(post_state).keys():
    let pre_entity = pre_state.get(entity_id)
    let post_entity = post_state.get(entity_id)
    let same_python_id = id(pre_entity) is id(post_entity)
    let fields_equal = pre_entity.model_dump() == post_entity.model_dump()
    NOT (same_python_id AND NOT fields_equal)   # in-place mutation forbidden
```

## Inputs (Hypothesis strategies)

| Strategy | Source | Layer |
|----------|--------|-------|
| Discovery walker (no Hypothesis) | `tests/property/harness/model_class_registry.py` | 1 (parametrize) |
| `worldstate_strategy()` | `tests/property/strategies/worldstate.py` (existing) | 2 |

## Test predicates

### Predicate A — Static frozen audit (Layer 1)

```python
@pytest.mark.parametrize(
    "model_cls",
    discover_state_bearing_models(),
    ids=lambda c: c.__qualname__,
)
def test_state_bearing_model_is_frozen(model_cls):
    """Layer 1: every state-bearing Pydantic model class declares frozen=True.

    Delegates to assert_all_frozen() from harness/model_class_registry.py so
    the bypass-marker honoring + justification-non-empty logic lives in one
    place. Per-class parametrization keeps failures isolable to the single
    offending class.
    """
    assert_all_frozen([model_cls])
```

`assert_all_frozen` (defined in `tests/property/harness/model_class_registry.py`)
encapsulates: (a) `model_config.get("frozen") is True` check, (b)
`bypasses_topology_invariant` opt-out honoring, and (c) the FR-011
non-empty justification assertion. Calling it with a single-class list
per parametrize case keeps the failure trace pinned to the offending
class while routing all logic through one shared helper.

### Predicate B — Per-tick identity check (Layer 2)

```python
@given(pre_state=worldstate_strategy(min_entities=1, min_territories=1))
@settings(max_examples=100, derandomize=True, suppress_health_check=[HealthCheck.too_slow])
def test_no_in_place_mutation_per_tick(pre_state, services_fixture, ctx_fixture):
    """Layer 2: SimulationEngine.run_tick produces no in-place mutations."""
    pre_ids = snapshot_ids(pre_state)
    pre_dumps = {
        entity_id: entity.model_dump()
        for entity_id, entity in _iter_worldstate_collections(pre_state)
    }

    systems = [cls() for cls in all_systems()]
    engine = SimulationEngine(systems=systems)
    graph = pre_state.to_graph()
    engine.run_tick(graph, services_fixture, ctx_fixture)
    post_state = WorldState.from_graph(graph, tick=pre_state.tick + 1)

    post_dict = dict(_iter_worldstate_collections(post_state))

    for entity_id, pre_python_id in pre_ids.items():
        if entity_id not in post_dict:
            continue  # entity removed during tick — not an identity violation
        post_entity = post_dict[entity_id]
        post_python_id = id(post_entity)
        post_dump = post_entity.model_dump()
        pre_dump = pre_dumps[entity_id]

        # Legal: equal dumps AND same id (no mutation), OR different dumps AND different id (model_copy)
        # Illegal: same id AND different dumps (in-place mutation)
        if post_python_id == pre_python_id and post_dump != pre_dump:
            raise AssertionError(
                f"In-place mutation detected on entity {entity_id} "
                f"(class {type(post_entity).__name__}): same id() but field-different. "
                f"diff: {_dict_diff(pre_dump, post_dump)}"
            )
```

### Predicate C — Seeded violation is caught

```python
def test_seeded_dunder_bypass_is_detected(services_fixture, ctx_fixture):
    """Negative test — patch a System to dunder-bypass and assert caught."""
    state = _build_minimal_state()
    pre_ids = snapshot_ids(state)

    class MutatingSystem:
        name = "mutating_system_for_test"
        def step(self, graph, services, context):
            for node_id in graph.nodes:
                attrs = graph.nodes[node_id]
                if "wealth" in attrs:
                    # Dunder-bypass would have to happen on a model object;
                    # graph attrs are dicts, so simulate with a real model instance.
                    pass
            # Simulate via direct WorldState model dunder-bypass (test-only)
            for entity in state.entities.values():
                entity.__dict__["wealth"] = 999.0  # forbidden; bypasses Pydantic

    engine = SimulationEngine(systems=[MutatingSystem()])
    engine.run_tick(state.to_graph(), services_fixture, ctx_fixture)

    with pytest.raises(AssertionError, match="In-place mutation detected"):
        assert_no_in_place_mutation(pre_state=state, post_state=state, pre_ids=pre_ids)
```

## Failure modes

| Cause | Symptom | Remediation |
|-------|---------|-------------|
| A maintainer removes `frozen=True` from a state-bearing model class | Predicate A fails at collection time on the offending class | Restore `model_config = ConfigDict(frozen=True)`. If the model legitimately needs to be mutable, add `bypasses_topology_invariant` with a non-empty justification |
| A System uses `entity.__dict__["field"] = X` (dunder-bypass) | Predicate B fails on the offending entity ID | Refactor the System to use `model_copy(update={...})` |
| A library mutates a Pydantic model field through some other sidestep | Predicate B fails | Replace the library or wrap its output to return a fresh `model_copy` |
| A model legitimately needs to be non-frozen (rare) | Add `bypasses_topology_invariant: ClassVar[dict[str, str]] = {"frozen_discipline": "<reason>"}` | Justification MUST be non-empty per FR-011 |

## Out of scope

- Mutable containers held BY frozen models (`list`, `dict`, `set`
  attributes that downstream code mutates). Catching this is a follow-up
  invariant tracked in `research.md §4` end-of-section note.
- Pydantic's own `__setattr__` validation path (already enforced at
  runtime by Pydantic; no test coverage needed because failures raise
  immediately).
- Cross-tick identity preservation (entity ID survives across ticks but
  the underlying Python object may legitimately differ — the engine
  produces fresh instances per tick).
