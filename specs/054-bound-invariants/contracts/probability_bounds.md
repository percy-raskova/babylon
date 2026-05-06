# Contract: Probability Bounds (US1 — INV-006)

**Predicate ID**: INV-006
**User Story**: US1 (P1)
**Source**: [spec.md §US1](../spec.md#user-story-1--probability-values-stay-in-0-1-priority-p1)
**Tests**: `tests/property/invariants/test_probability_bounds.py`
**Invariant class**: `babylon.engine.invariants.ProbabilityInRange`

## Predicate

For every `(ModelClass, field_name)` pair returned by
`discover_probability_fields()`, every instance of `ModelClass` in the
post-state, and every `EdgeType.SOLIDARITY` edge in the post-graph:

```text
∀ entity ∈ post.entities, ∀ (Cls, field_name) where isinstance(entity, Cls):
    0.0 <= getattr(entity, field_name) <= 1.0

∀ edge ∈ post.graph.edges where edge.type == EdgeType.SOLIDARITY:
    0.0 <= edge.solidarity_strength <= 1.0
```

**Tolerance**: Exact comparison (`tolerance=0.0`). The `Probability`
constrained type's contract is the closed interval `[0, 1]`; values at
the boundary are legal.

## Inputs (Hypothesis strategies)

| Strategy | Source |
|----------|--------|
| `worldstate_with_probability_fields_strategy()` | `tests/property/strategies/worldstate.py` |

The strategy populates every Probability-typed field with a draw from
`st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)`.

## Test predicates

### Predicate A — Per-entity field bound (post-`run_tick`)

```python
@given(state=worldstate_with_probability_fields_strategy())
@settings()
def test_probability_post_runtick_in_range(state, service_container_fixture, tick_context_fixture):
    post = SimulationEngine.run_tick(state.to_graph(), service_container_fixture, tick_context_fixture)
    post_state = WorldState.from_graph(post)
    invariant = ProbabilityInRange(field_pairs=discover_probability_fields())
    result = invariant.check(state, post_state)
    assert result.ok, result.msg
```

### Predicate B — Per-formula domain (allow-list scan)

```python
@pytest.mark.parametrize("formula", discover_probability_formulas(), ids=lambda f: f.__name__)
def test_probability_formula_in_range(formula):
    @given(args=formula_input_strategy(formula))
    @settings(max_examples=100)
    def _check(args):
        result = formula(**args)
        assert 0.0 <= result <= 1.0, f"{formula.__name__}({args}) = {result}"
    _check()
```

### Predicate C — SOLIDARITY edge strength (post-`SolidaritySystem.step`)

```python
@given(state=worldstate_with_solidarity_edges_strategy())
@settings()
def test_solidarity_strength_in_range(state, service_container_fixture, tick_context_fixture):
    harness = BoundInvariantHarness(
        system=SolidaritySystem,
        invariants=[ProbabilityInRange(field_pairs=[(Relationship, "solidarity_strength")])],
    )
    result = harness.run(state, service_container_fixture, tick_context_fixture)
    assert result.outcomes["probability_in_range"].ok
```

### Predicate D — Round-trip preservation (FR-012)

```python
@given(state=worldstate_with_probability_fields_strategy())
def test_probability_round_trip_preserves_bound(state):
    graph = state.to_graph()
    rehydrated = WorldState.from_graph(graph)  # must not raise ValidationError
    invariant = ProbabilityInRange(field_pairs=discover_probability_fields())
    assert invariant.check(state, rehydrated).ok
```

## Failure modes

| Cause | Symptom | Remediation |
|-------|---------|-------------|
| A System writes a raw float > 1.0 to a Probability field via `update_node` | Predicate A fails on the System; failure msg names the field and entity | Either clip the write OR add `bypasses_bound_invariant: ClassVar[dict[str, str]] = {"probability_in_range": "<reason>"}` to the System |
| A formula returns a value outside `[0, 1]` due to numerical overflow | Predicate B fails on the formula | Fix the formula; do not paper over with clipping unless the math is correct |
| Round-trip re-validates a stored value as out-of-bounds | Predicate D fails | The graph node carries an illegal value — find which System wrote it |

## Out of scope

- Pydantic constructor validation (already covered by Pydantic itself; the
  test would always pass and add no signal).
- `Coefficient`, `Intensity`, `Ideology` constrained types (these are
  semantically distinct types whose bounds may have different meaning;
  could be a sister spec).
- Probability values inside `pyo3` / Cython extensions (none in this
  codebase).
