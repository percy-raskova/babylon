# Contract: Monetary Rescaling

**Spec**: [../spec.md](../spec.md) — FR-001, FR-002
**Data model**: [../data-model.md](../data-model.md) — `MonetaryRescaling`
**Implementation**: `tests/_helpers/invariants/monetary_rescaling.py`

## Purpose

US1 / FR-001 / FR-002 require running a tick at two monetary scales and
asserting that ratios are invariant. The rescaler is the operation that
produces the rescaled world.

## Operation

`rescale_currency_fields(world: WorldState, k: float) -> WorldState`

Walks every Pydantic model field across the entire `WorldState` tree.
Scales the field value by `k` iff the field's type annotation is
`Currency` (or a `Currency`-derived type). Leaves every other field
unchanged.

## Field rules

| Annotation | Action | Example fields |
|---|---|---|
| `Currency` | × k | `Organization.constant_capital`, `Organization.variable_capital`, `GlobalEconomy.melt`, prices |
| `Currency \| None` | × k if value is not None | `KeyFigure.assets` (if defined) |
| `LaborHours` | unchanged | `DepartmentRow.c`, `DepartmentRow.v`, `DepartmentRow.s`, `ValueTensor4x3.excluded_wages` |
| `Probability`, `Intensity`, `Ideology` | unchanged | bounded ratios on `SocialClass` |
| `int` (tick, counts) | unchanged | `WorldState.tick`, event counts |
| `str` (IDs, enums) | unchanged | every `_id` field |
| `list[Currency]` | element-wise × k | (hypothetical aggregate timeseries) |
| `dict[str, Currency]` | value-wise × k | per-sector currency maps |

## Implementation strategy

```python
import typing
from typing import get_args, get_origin
from babylon.models.types import Currency

def _is_currency_annotation(annot) -> bool:
    if annot is Currency:
        return True
    if get_origin(annot) is typing.Union:
        return any(_is_currency_annotation(a) for a in get_args(annot) if a is not type(None))
    if get_origin(annot) in (list, dict, tuple):
        return _is_currency_annotation(get_args(annot)[-1])
    return False
```

For each `BaseModel` instance encountered, iterate
`model.model_fields.items()`. If `field_info.annotation` is
`Currency`-shaped per the helper, multiply by `k`. Recurse into nested
`BaseModel`s.

## Invariants (FR-001)

| Invariant | Verification |
|---|---|
| Pure | `rescale(rescale(w, k), 1/k) == w` within 1e-15 |
| Composable | `rescale(rescale(w, a), b) == rescale(w, a*b)` within 1e-15 |
| Identity | `rescale(w, 1.0) == w` exactly |
| Labor-time fields untouched | for any `LaborHours` field f: `rescale(w, k).f == w.f` exactly |
| Tick counter untouched | `rescale(w, k).tick == w.tick` |

## Out of scope

- Rescaling Postgres-persisted state. The rescaler operates on
  in-memory `WorldState` only. Persistence tests use the
  serialization round-trip (FR-014).
- Rescaling derived metrics. The rescaler does not pre-compute
  `DerivedTensorMetrics`; the test re-runs the tick and reads the
  ratios from the resulting state.

## Error cases

| Input | Behavior |
|---|---|
| `k = 0` | `ValueError("Scaling factor must be positive")` |
| `k < 0` | `ValueError("Scaling factor must be positive")` |
| `k = inf` or `nan` | `ValueError("Scaling factor must be finite")` |
| `world` not a `WorldState` | `TypeError` |
| `k` very small or very large outside [1e-9, 1e9] | Warning emitted; test should not use scales outside this range to avoid IEEE-754 precision loss |
