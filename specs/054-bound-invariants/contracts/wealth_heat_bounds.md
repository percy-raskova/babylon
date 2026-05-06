# Contract: Wealth ≥ 0 and Heat ≥ 0 (US2 — INV-007)

**Predicate ID**: INV-007
**User Story**: US2 (P2)
**Source**: [spec.md §US2](../spec.md#user-story-2--wealth--0-and-heat--0-across-all-22-systems-priority-p2)
**Tests**: `tests/property/invariants/test_wealth_heat_bounds.py`
**Invariant classes**: `babylon.engine.invariants.NonNegativeWealth`,
`babylon.engine.invariants.HeatNonNegativity` (both pre-existing)

## Predicate

For every System `S` in `SystemRegistry.all_systems()` and every
`WorldState` whose pre-state satisfies the invariants:

```text
∀ entity ∈ post.entities: entity.wealth >= 0.0
∀ territory ∈ post.territories: territory.heat >= 0.0
```

**Tolerance**: Exact comparison (`>= 0.0`). Wealth and heat are stock
quantities that cannot be negative by their material-relation semantics
(research §6).

## Inputs (Hypothesis strategies)

| Strategy | Source |
|----------|--------|
| `worldstate_strategy(min_entities=1, max_entities=200, max_edges=2000)` | `tests/property/strategies/worldstate.py` |
| Per-System pre-state factory (US2 isolation per Q2 clarify) | `tests/property/harness/system_registry.py` |

## Test predicates

### Predicate A — Per-System isolation (Q2 clarification)

```python
@pytest.mark.parametrize("system_cls", SystemRegistry.all_systems(),
                         ids=lambda s: s.__name__)
@given(pre=worldstate_strategy())
def test_wealth_heat_per_system(system_cls, pre, service_container_fixture, tick_context_fixture):
    harness = BoundInvariantHarness(
        system=system_cls,
        invariants=[NonNegativeWealth(), HeatNonNegativity()],
    )
    try:
        result = harness.run(pre, service_container_fixture, tick_context_fixture)
    except SystemPreconditionError as exc:
        pytest.skip(f"{system_cls.__name__} requires upstream state: {exc}")
    for inv_name, outcome in result.outcomes.items():
        if outcome == "SKIPPED":
            continue  # bypass marker present
        assert outcome.ok, f"{system_cls.__name__}: {outcome.msg}"
```

### Predicate B — Full-pipeline composition

```python
@given(pre=worldstate_strategy())
def test_wealth_heat_full_pipeline(pre, service_container_fixture, tick_context_fixture):
    post_graph = SimulationEngine.run_tick(pre.to_graph(), service_container_fixture, tick_context_fixture)
    post = WorldState.from_graph(post_graph)
    assert NonNegativeWealth().check(pre, post).ok
    assert HeatNonNegativity().check(pre, post).ok
```

### Predicate C — Coverage trace (per-System SC-002)

A non-Hypothesis test that simply asserts every System in
`SystemRegistry.all_systems()` produced *either* a `PASSED`, `FAILED`, or
`SKIPPED` outcome in Predicate A — no silent omissions.

```python
def test_per_system_coverage_complete(per_system_results):
    for system_cls in SystemRegistry.all_systems():
        assert system_cls.__name__ in per_system_results, \
            f"{system_cls.__name__} not exercised by per-System harness"
```

## Failure modes

| Cause | Symptom | Remediation |
|-------|---------|-------------|
| A System computes `entity.wealth -= cost` without bounding at 0 | Predicate A fails on that System | Bound the subtraction (`max(0.0, wealth - cost)`) OR wrap as a flow that explicitly transfers debt |
| A System decays heat below 0 | Predicate A fails | Bound the decay; or clamp at 0 |
| Full-pipeline composition produces neg-wealth that no single System produces (interaction bug) | Predicate B fails but Predicate A passes for every System | Two Systems are interacting destructively; trace via the per-System trace |
| A System legitimately produces transient neg-wealth that is offset within the step | Predicate A fails | Add `bypasses_bound_invariant: ClassVar[dict[str, str]] = {"non_negative_wealth": "<reason>"}` |

## Out of scope

- Other entity attributes (`organization`, `repression_faced`, …) — these
  are `Probability`-typed and covered by INV-006.
- Territory attributes other than `heat` (e.g., `population`,
  `infrastructure`) — would be a sister spec.
- Negative wealth modeled as `Debt` (separate field; a different
  invariant).
