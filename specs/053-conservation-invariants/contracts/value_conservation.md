# Contract: c+v+s Value Conservation Across Systems

**Invariant ID**: INV-001
**User Story**: 1 (P1)
**Test File**: `tests/property/invariants/test_value_conservation.py`

## Background

The c+v+s state lives ONLY in `HexEconomicState` inside `HexGrid`. The engine systems (`babylon.engine.systems.*`) operate on `nx.DiGraph[str]` with `wealth` attributes — they never touch hex c+v+s. The substrate computers (`babylon.economics.substrate.*`) are the classes that own the c+v+s mutations. INV-001 therefore splits into three sub-predicates:

## Predicate A — Per-substrate-computer conservation (T019)

For any generated `HexGrid` `pre` and any substrate computer class `C` where `getattr(C, "creates_value", False) is False`:

```text
let post = C().<primary_method>(pre)   # e.g. compute_production(pre), aggregate(pre, target_resolution=…), circulate_wages(pre, od)
let N    = len(pre.hexes)
assert |sum(c+v+s)_post − sum(c+v+s)_pre| < max(1e-10, 1e-11 * N)
```

## Predicate B — Per-engine-system "no hex mutation" (T019a)

For any generated `(WorldState, HexGrid)` pair `(world, hex_grid)` and any engine system class `S` where `getattr(S, "creates_value", False) is False`:

```text
let graph = world.to_graph()
S().step(graph, services_fixture, tick_context_fixture)
assert hex_grid is unchanged (every hex's c, v, s exactly equal to pre values)
```

Engine systems must not touch substrate state at all; this is a stronger assertion than tolerance-bounded conservation.

## Predicate C — Full-pipeline conservation (T020)

For any generated `(WorldState, HexGrid)` pair:

```text
let pre_cvs = sum_cvs(hex_grid)
let recorded = []   # delta records from creates_value=True systems
SimulationEngine(systems=...).run_tick(graph, services_fixture, tick_context_fixture)
# (services_fixture.event_bus collects per-system value-change events)
let post_cvs = sum_cvs(hex_grid)
let net_recorded = sum(recorded)
assert |post_cvs − pre_cvs − net_recorded| < max(1e-10, 1e-11 * N)
```

## Inputs

| Input | Type | Strategy |
|-------|------|----------|
| `pre` (Predicate A) | `HexGrid` | `hex_grid_strategy()` (T011) |
| `(world, hex_grid)` (Predicates B, C) | `tuple[WorldState, HexGrid]` | `worldstate_with_hexes_strategy()` (T014a) |
| `C` (Predicate A) | substrate computer class | `pytest.parametrize` over `_discover_non_opt_out_substrate_computers()` (T017a) |
| `S` (Predicate B) | engine system class | `pytest.parametrize` over `_discover_non_opt_out_engine_systems()` (T017) |

## Failure Mode

- Predicate A: `pytest.fail(f"INV-001: substrate computer {C.__name__} mutated sum(c+v+s) by {drift} > tol={tol(N)}; pre={pre}, post={post}")`
- Predicate B: `pytest.fail(f"INV-001: engine system {S.__name__} mutated hex c+v+s — engine systems must not touch substrate state")`
- Predicate C: `pytest.fail(f"INV-001: full-pipeline drift {drift} > tol={tol(N)}; per-system pre/post: {breakdown}")`

The Hypothesis-shrunk counterexample is a minimal input for which the assertion fails. The `pytest.parametrize` id identifies which class caused the failure for Predicates A and B.

## Acceptance

- All non-opt-out substrate computers pass Predicate A with `default` Hypothesis profile (100 examples each).
- All non-opt-out engine systems pass Predicate B (proves they don't touch hex state).
- The full-pipeline test passes Predicate C, catching any inter-system interaction bug that escapes both per-class tests.
- A deliberate regression in any participating class produces a counterexample within one test invocation (SC-003).
