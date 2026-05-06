# Contract: H3 Hierarchical Sum Conservation (Sheaf Gluing)

**Invariant ID**: INV-002
**User Story**: 2 (P1)
**Test File**: `tests/property/invariants/test_h3_hierarchical.py`

## Predicate

For any generated `HexGrid` `grid` and any target resolution `r ∈ {6, 5}`:

```text
for each parent_id in grid.{res6,res5}_children:
    let children     = grid.{res6,res5}_children[parent_id]
    let child_total  = sum(c+v+s for h in children)
    let parent_total = aggregator.aggregate(grid, target_resolution=r)[parent_id]
    assert |child_total − parent_total| < 1e-10
```

And the cross-resolution gluing:

```text
let r6_global = sum(aggregator.aggregate(grid, 6).values())
let r5_global = sum(aggregator.aggregate(grid, 5).values())
let hex_total = sum(c+v+s for h in grid.hexes.values())
assert |hex_total − r6_global| < 1e-10
assert |hex_total − r5_global| < 1e-10
assert |r6_global − r5_global| < 1e-10
```

The same assertion MUST hold post-step, i.e., after any pipeline tick that mutates per-hex c/v/s.

## Inputs

| Input | Type | Strategy |
|-------|------|----------|
| `grid` | `HexGrid` | `hex_grid_strategy()` |

## Failure Mode

`pytest.fail(f"Sheaf gluing violated at resolution {r}: parent={parent_id}, drift={drift}")`

## Acceptance

- All res-6 parents glue exactly within `1e-10`.
- All res-5 parents glue exactly within `1e-10`.
- Cross-resolution totals match within `1e-10`.
- Empty-grid and single-hex edge cases pass trivially.
