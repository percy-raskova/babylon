# Contract: `BEAMappings` and the typed BEA-to-Department loader

**Module**: `src/babylon/economics/tensor_hierarchy/mappings/_models.py` + `mappings/__init__.py`
**Introduced by**: Spec 058 / FR-009 (US4, Bundle 1)
**Replaces**: runtime TOML reparse in `src/babylon/economics/department_mapper.py`
**Status**: Draft (this is the contract; implementation lands in commit 7)

This contract specifies the typed `BEAMappings` model and its module-level loader. Companion contracts: [`protocol_kit.md`](protocol_kit.md), [`source_registry.md`](source_registry.md).

---

## 1. Public surface

```python
# economics/tensor_hierarchy/mappings/_models.py
class DepartmentMapping(BaseModel):
    model_config = ConfigDict(frozen=True)
    bea_code: str = Field(min_length=1)
    department: Literal["I", "II", "III"]
    weight: float = Field(ge=0.0, le=1.0)


class BEAMappings(BaseModel):
    model_config = ConfigDict(frozen=True)
    mappings: list[DepartmentMapping] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_invariants(self) -> Self: ...

    def get_departments(self, bea_code: str) -> Mapping[str, float]: ...


# economics/tensor_hierarchy/mappings/__init__.py
__all__ = ["BEAMappings", "BEA_TO_DEPARTMENT", "DepartmentMapping"]

BEA_TO_DEPARTMENT: Final[BEAMappings] = BEAMappings.model_validate(
    tomllib.loads(_TOML_PATH.read_text())
)
```

---

## 2. Semantic guarantees

### Construction-time invariants (enforced by `_check_invariants` model validator)

| Invariant | Detail | Failure mode |
|-----------|--------|--------------|
| **Per-bea_code uniqueness** | No two `DepartmentMapping` entries with the same `(bea_code, department)` pair. | `pydantic.ValidationError` with message `f"Duplicate (bea_code, department) entry: {key}"` |
| **Per-bea_code weight sum == 1.0** | For each `bea_code`, the sum of `weight` over all entries with that `bea_code` MUST equal `1.0` within `1e-9` tolerance. | `pydantic.ValidationError` with message `f"BEA code {code!r} weights sum to {total!r}, expected 1.0 (within 1e-9)"` |
| **At least one mapping** | `mappings` is `Field(min_length=1)`. | `pydantic.ValidationError` with standard "list too short" message |

### Per-row constraints (enforced by Pydantic field validators)

| Constraint | Detail | Failure mode |
|------------|--------|--------------|
| `bea_code` is non-empty string | `Field(min_length=1)` | `pydantic.ValidationError` |
| `department` ∈ {"I", "II", "III"} | `Literal["I", "II", "III"]` | `pydantic.ValidationError` |
| `weight` ∈ [0.0, 1.0] | `Field(ge=0.0, le=1.0)` | `pydantic.ValidationError` |

### Frozen semantics

| Guarantee | Detail |
|-----------|--------|
| **Both models are `frozen=True`** | Mutating any field after construction raises `pydantic.ValidationError`. Pydantic-2 enforces this at the BaseModel level. |
| **`mappings` is a `list` not a `tuple`** | Pydantic-2 frozen models still allow `list` fields; the list itself is not mutated by Pydantic but the user MUST treat it as immutable. (Mutating `bea_mappings.mappings.append(...)` works at the Python level but is a contract violation; mypy strict catches it because the field is declared `list[DepartmentMapping]`.) |
| **`get_departments()` returns a fresh dict** | Each call constructs a new dict to prevent mutation leaking back into `mappings`. Caller may mutate the returned dict freely; mutations have no effect on the singleton. |

### Loading semantics

| Guarantee | Detail |
|-----------|--------|
| **Once-at-import-time** | `BEA_TO_DEPARTMENT` is computed when `babylon.economics.tensor_hierarchy.mappings` is first imported. Subsequent imports return the same instance from Python's module cache. |
| **Loud failure on bad TOML** | Per spec Edge Cases: TOML missing → `FileNotFoundError`; TOML malformed → `tomllib.TOMLDecodeError`; schema mismatch → `pydantic.ValidationError`. ALL fail at import time, NOT at first use. |
| **No silent fallback** | There is no try/except around the load. If the TOML is broken, the entire `babylon.economics.tensor_hierarchy` package fails to import. This is intentional: Constitution III.4 (Data Catalog) requires fixture data to be valid; an invalid fixture is a fatal configuration bug. |

### Runtime usage

| Guarantee | Detail |
|-----------|--------|
| **Singleton consumption** | All callers (`department_mapper.py`, future spec-057 code) MUST consume `BEA_TO_DEPARTMENT` directly: `from babylon.economics.tensor_hierarchy.mappings import BEA_TO_DEPARTMENT`. NOT `BEAMappings.model_validate(reread_toml())`. |
| **`get_departments(code)` is the lookup API** | `BEA_TO_DEPARTMENT.get_departments("541")` returns a `Mapping[str, float]` (department → weight). Raises `KeyError` if `code` is not present. |
| **Linear scan, not indexed** | `get_departments` does a list comprehension over `self.mappings`. With ~150 rows, this is ~µs per call. Indexing (e.g., a `dict[str, list[DepartmentMapping]]` cache) is out-of-scope for Bundle 1; can be added if profiling shows it matters. |

---

## 3. Caller contract

### `department_mapper.py` post-Bundle-1

```python
from babylon.economics.tensor_hierarchy.mappings import BEA_TO_DEPARTMENT


def get_default_mapper() -> DepartmentMapper:
    """Return the default DepartmentMapper instance, backed by BEA_TO_DEPARTMENT.

    Per FR-009: this no longer reparses the TOML on every call. The mapper is
    constructed once at import time and reused.
    """
    return DepartmentMapper(mapping=BEA_TO_DEPARTMENT)
```

The change is mechanical: replace `tomllib.loads(open("...").read())` calls with `BEA_TO_DEPARTMENT`. No behavior change for the consumer of `DepartmentMapper`.

### Spec 057 forward consumer

When Spec 057 lands its Leontief calculator, it consumes `BEA_TO_DEPARTMENT` (or the `DepartmentMapper` wrapper) for the `dept_mapping` argument to `ProductionChainRentCalculator.calculate(...)`. The typed object provides static-analysis safety: mypy can verify that `dept_mapping["541"]["I"]` is a `float` and that `"541"` exists.

---

## 4. Test contract

`tests/unit/economics/tensor_hierarchy/test_bea_mappings.py` MUST cover:

### Production TOML acceptance

1. **Production TOML loads without error**: `from babylon.economics.tensor_hierarchy.mappings import BEA_TO_DEPARTMENT; assert isinstance(BEA_TO_DEPARTMENT, BEAMappings)`
2. **Production TOML has the same set of bea_codes as the pre-Bundle-1 untyped dict**: `assert set(m.bea_code for m in BEA_TO_DEPARTMENT.mappings) == EXPECTED_BEA_CODES`
3. **Production TOML's per-code weight sums all == 1.0**: redundant with the validator but explicit-test-as-documentation
4. **`get_departments(known_code)` returns a non-empty `Mapping[str, float]`**: `assert BEA_TO_DEPARTMENT.get_departments("541")` returns a dict with at least one (department, weight) entry
5. **`get_departments(unknown_code)` raises `KeyError`**: `with pytest.raises(KeyError): BEA_TO_DEPARTMENT.get_departments("ZZZ")`

### Synthetic malformed-fixture rejection

6. **Negative weight rejected**: `BEAMappings.model_validate({"mappings": [{"bea_code": "541", "department": "I", "weight": -0.1}]})` raises `pydantic.ValidationError`
7. **Weight > 1.0 rejected**: same shape with `weight=1.5`
8. **Unknown department rejected**: same shape with `department="IV"`
9. **Empty bea_code rejected**: `bea_code=""`
10. **Empty mappings list rejected**: `BEAMappings.model_validate({"mappings": []})` raises (Field min_length=1)
11. **Per-bea_code weight sum != 1.0 rejected**: `[{"bea_code": "541", "department": "I", "weight": 0.5}]` (sum = 0.5, not 1.0)
12. **Duplicate (bea_code, department) rejected**: `[{"bea_code": "541", "department": "I", "weight": 0.5}, {"bea_code": "541", "department": "I", "weight": 0.5}]` — even though weights sum to 1.0, the duplicate-key check fires first
13. **Frozen model rejects mutation**: `with pytest.raises(pydantic.ValidationError): bm.mappings = []`

### Equivalence with pre-Bundle-1 behavior

14. **Department lookups produce same results as pre-Bundle-1 reparse**: for every bea_code, `BEA_TO_DEPARTMENT.get_departments(code)` returns the same `(department, weight)` dict as the legacy `_reparse_and_lookup(code)` function (this test stays in the codebase post-Bundle-1 as a regression net; the `_reparse_and_lookup` helper is kept in `department_mapper.py` for one release as a parity reference, then deleted in Bundle 3)

---

## 5. Out-of-scope for Bundle 1

- Validating that the BEA codes in the TOML correspond to *real* BEA NAICS codes (i.e., that `"541"` is in the official BEA classification). This is a data-quality concern owned by the data ingest pipeline (Constitution III.4); the typed model only checks shape.
- Caching computed lookups (`get_departments` is fast enough; an `@lru_cache` could be added if profiling shows it matters)
- Async loading (TOML is small; synchronous is fine)
- TOML schema versioning (the TOML has no version field today; if/when it gets one, the loader can branch on version, but that's not in this bundle)
- Multi-region BEA mappings (the current TOML is global; per-region mappings would be a future enhancement, separately specified)

---

## 6. Spec 057 forward-compatibility note

Spec 057 will introduce `ProductionChainRentCalculator.calculate(dept_mapping=...)` where `dept_mapping` is currently a raw `dict[str, str]`. After Bundle 1, the natural typed signature is:

```python
def calculate(
    self,
    *,
    use_table: BEAUseTable,
    final_demand: FinalDemand,
    dept_mapping: BEAMappings,  # <-- typed per Bundle 1 / FR-009
    ...
) -> ProductionChainRent: ...
```

This is a Spec 057 design choice, not a Bundle 1 commitment. Bundle 1 just provides the typed model; Spec 057 chooses how to consume it.
