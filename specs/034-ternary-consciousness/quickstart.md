# Quickstart: 034-ternary-consciousness

## Prerequisites

- Python 3.12+
- Poetry environment: `poetry install`
- Pre-commit hooks: `poetry run pre-commit install`
- Branch: `034-ternary-consciousness`

## Key Files

### New Files (to be created)

| File | Purpose |
|------|---------|
| `src/babylon/models/entities/consciousness.py` | `TernaryConsciousness`, `SubstrateFloor`, `ProvenanceLevel` models |
| `src/babylon/formulas/consciousness.py` | `compute_ternary_consciousness()` pure function |
| `tests/unit/models/test_ternary_consciousness.py` | Model validation, simplex constraint, backward compat |
| `tests/unit/formulas/test_consciousness_computation.py` | Computation from org landscape, substrate floor, edge cases |

### Modified Files

| File | Change |
|------|--------|
| `src/babylon/models/entities/community.py` | `CommunityState.consciousness` type changes to `TernaryConsciousness`; `CONSCIOUSNESS_DEFAULTS` migrated to ternary |
| `src/babylon/engine/systems/community.py` | `CommunitySystem.step()` calls ternary computation after building hypergraph |
| `src/babylon/bifurcation/consciousness.py` | No formula changes; reads `r` via `collective_identity` property |
| `src/babylon/ooda/layer3.py` | Consciousness mutation path replaced by org landscape reads |
| `src/babylon/persistence/postgres_schema.py` | Add r, l, f columns to community_state table |
| `src/babylon/persistence/postgres_runtime.py` | Read/write ternary columns |

## Running Tests

```bash
# Run all community-related tests (should pass after migration)
poetry run pytest tests/unit/models/test_community_models.py -v
poetry run pytest tests/unit/engine/systems/test_community_system.py -v
poetry run pytest tests/unit/formulas/test_community_formulas.py -v

# Run new ternary-specific tests
poetry run pytest tests/unit/models/test_ternary_consciousness.py -v
poetry run pytest tests/unit/formulas/test_consciousness_computation.py -v

# Run bifurcation tests (should pass unchanged)
poetry run pytest tests/unit/bifurcation/ -v

# Full unit suite
mise run test:unit
```

## Verification

After implementation, verify:

1. `mise run check` passes (lint + format + typecheck + test:unit)
2. All existing community tests pass without modification
3. All existing bifurcation tests pass without modification
4. New ternary tests cover all 8 success criteria
