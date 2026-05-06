# Contract: Variable Capital Conservation Under LODES Circulation

**Invariant ID**: INV-003
**User Story**: 3 (P1)
**Test File**: `tests/property/invariants/test_circulation_v.py`

## Predicate

For any generated `HexGrid` `pre` with N hexes and any row-stochastic sparse OD matrix `od ∈ R^{N×N}`:

```text
let (post, _boundary) = DefaultHexCirculationComputer().circulate_wages(pre, od)
let N = number of hexes in pre
assert |sum(v)_post − sum(v)_pre| < max(1e-10, 1e-11 * N)
assert sum(c)_post == sum(c)_pre  (exact)
assert sum(s)_post == sum(s)_pre  (exact)
```

## Inputs

| Input | Type | Strategy |
|-------|------|----------|
| `pre` | `HexGrid` | `hex_grid_strategy()` (N ∈ [1, 25 000]) |
| `od`  | `scipy.sparse.csr_matrix` | `od_matrix_strategy(N, flavor=…)` covering identity, empty_rows, dense, random; density ≤ 0.01 at large N to match LODES sparsity |

## Failure Mode

`pytest.fail(f"Circulation drifted sum(v) by {drift} > tol={tol(N)}")` or, for c/s, `f"Circulation mutated sum(c) by {drift} (must be exactly 0)"`.

## Acceptance

- Random sparse OD: drift below `tol(N)`.
- Identity OD: per-hex `v` unchanged within `tol(N)`.
- Empty-row OD: invariant still holds.
- `sum(c)` and `sum(s)` unchanged exactly.
