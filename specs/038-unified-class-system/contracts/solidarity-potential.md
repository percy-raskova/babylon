# Contract: Solidarity Potential with Class-Pair Matrix

**Spec**: FR-006
**Module**: `src/babylon/formulas/community.py` (existing, extended usage)
**Module**: `src/babylon/config/defines.py` (ClassSystemDefines.base_class_solidarity)

---

## Current Signature (Unchanged)

```python
def calculate_solidarity_potential(
    base_solidarity: float,
    shared_count: int,
    rent_a: float,
    rent_b: float,
    overlap_bonus: float = 0.1,
    rent_penalty: float = 0.05,
) -> float:
    """base + (overlap_bonus * shared_count) - (rent_penalty * |rent_a - rent_b|)"""
```

The formula itself does not change. What changes is how `base_solidarity` is computed by callers.

---

## New Caller Contract

```python
# Before (Feature 022 — flat constant):
base_solidarity = 0.3  # or some default

# After (Feature 038 — class-pair matrix lookup):
defines = services.defines.class_system
base_solidarity = defines.get_base_solidarity(
    class_a=agent_a_class.name,  # ClassPosition.name
    class_b=agent_b_class.name,
)
```

---

## Behavioral Contracts

### BC-010: Matrix Symmetry
```
GIVEN class_a and class_b
WHEN get_base_solidarity(class_a, class_b) is called
THEN result == get_base_solidarity(class_b, class_a)
```

### BC-011: Negative Output Permitted
```
GIVEN base_solidarity = 0.0 (e.g., BOURGEOISIE-PROLETARIAT)
AND shared_count = 0
AND rent differential > 0
WHEN calculate_solidarity_potential is called
THEN result < 0 (active antagonism)
AND no floor clamp is applied
```

### BC-012: Monotonic Community Overlap
```
GIVEN fixed class positions and rent values
WHEN shared_count increases
THEN solidarity_potential increases monotonically
```

### BC-013: Monotonic Rent Differential
```
GIVEN fixed class positions and shared_count
WHEN |rent_a - rent_b| increases
THEN solidarity_potential decreases monotonically
```

### BC-014: Zero Community Overlap Baseline
```
GIVEN shared_count = 0 and rent_a = rent_b
WHEN calculate_solidarity_potential is called
THEN result == base_solidarity (pure class-pair relationship)
```
