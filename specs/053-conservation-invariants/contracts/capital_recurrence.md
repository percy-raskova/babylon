# Contract: Capital Stock Perpetual-Inventory Recurrence

**Invariant ID**: INV-005
**User Story**: 5 (P2)
**Test File**: `tests/property/invariants/test_capital_recurrence.py`

## Predicate

For any generated triple `(K_t, δ, I_t)` with `K_t ∈ [0, 1e9]`, `δ ∈ [0, 1]`, `I_t ∈ [0, 1e9]`:

```text
let K_t1 = CapitalStockCalculator().step(K_t, depreciation=δ, investment=I_t)
let expected = (1 − δ) * K_t + I_t
assert |K_t1 − expected| < 1e-10
```

Boundary cases (asserted as separate parametrized cases inside the same `@given`):

```text
δ = 0 ⇒ K_t1 == K_t + I_t
δ = 1 ⇒ K_t1 == I_t
I_t = 0 ⇒ K_t1 == (1 − δ) * K_t  AND  monotonically non-increasing in δ
```

## Inputs

| Input | Type | Strategy |
|-------|------|----------|
| `K_t` | `float` | `floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False)` |
| `δ`   | `float` | `floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)` |
| `I_t` | `float` | `floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False)` |

## Failure Mode

`pytest.fail(f"Recurrence violated: K_t={K_t}, δ={δ}, I_t={I_t}, K_t1={K_t1}, expected={expected}, drift={K_t1 - expected}")`

## Acceptance

- General recurrence holds within `1e-10`.
- All three boundary cases hold.
- Monotonicity check passes (increasing δ never increases K_t1 when I_t = 0).
