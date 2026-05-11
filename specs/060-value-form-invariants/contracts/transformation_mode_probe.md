# Contract: Transformation-Mode Probe

**Spec**: [../spec.md](../spec.md) — FR-021
**Source of truth**: [research.md R3](../research.md)
**Implementation**: `tests/_helpers/invariants/transformation_mode.py`

## Purpose

Tests that depend on the transformation engine being in
redistribution-active mode (FR-005-redistribution-arm, FR-006, FR-007,
FR-019) MUST gate on a single probe. This contract defines that probe.

Duplicating the probe across tests is forbidden by FR-021.

## Decision rule

Per `src/babylon/engine/dialectics/transformation.py:54-55`:

> weight < 0 → values dominate prices (low equalization).
> weight > 0 → prices of production fully equalized.

The probe MUST classify modes as:

| Condition | Mode | Tests SKIP? |
|---|---|---|
| `world.dialectics["transformation"].weight > 0` | `REDISTRIBUTION_ACTIVE` | No — RUN |
| `world.dialectics["transformation"].weight ≤ 0` | `PROPORTIONAL_PRICES` | Yes — SKIP |

The strict `> 0` boundary is intentional: at `weight == 0`, the
TransformationDialectic is exactly at the value/price boundary; the
test prefers to SKIP (false-pass risk) rather than RUN with degenerate
behavior.

## Public API

```python
from enum import StrEnum

class TransformationMode(StrEnum):
    PROPORTIONAL_PRICES = "proportional"
    REDISTRIBUTION_ACTIVE = "redistribution"

def probe_transformation_mode(world: WorldState) -> TransformationMode:
    ...

def skip_unless_active(world: WorldState, spec_ref: str = "spec-060") -> None:
    """pytest.skip if not in REDISTRIBUTION_ACTIVE mode.

    Skip reason format: "Transformation engine in proportional-prices
    mode (weight ≤ 0). Test gated by {spec_ref} FR-008."
    """
```

## Failure modes

| Failure | Behavior |
|---|---|
| `world.dialectics` has no `"transformation"` key | `KeyError` propagated to the caller (test ERROR, not FAIL). |
| `transformation` exists but has no `weight` attribute | `AttributeError` propagated. |
| `weight` is `nan` | Treat as `PROPORTIONAL_PRICES` (SKIP). |

## Consumers

The following tests MUST import this probe:

- `tests/integration/economics/test_aggregate_equalities.py` (only for the redistribution-active arm; the proportional-prices arm runs unconditionally and asserts trivial equality)
- `tests/integration/economics/test_wage_occ_asymmetry.py`
- `tests/integration/economics/test_productivity_shock_decoupling.py`
- `tests/integration/economics/test_volume_iii_equalization.py`

## Anti-pattern

Tests MUST NOT re-detect transformation mode by:
- Comparing prices to values × τ numerically (tautological).
- Reading `equalization_alpha` (a different mechanism — see research.md R2).
- Inspecting `TransformationPole` fields other than `weight`.
- Calling private methods of `TransformationDialectic`.
