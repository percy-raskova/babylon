# Contract: `PeripheryLaborCoefficientsSource`

**Spec**: 057 / FR-002, US2
**Location**: `src/babylon/economics/tensor_hierarchy/leontief_rent/periphery_labor_coefficients.py` (NEW)
**Pattern**: Protocol + `Default*` (Spec 058's `CachedSource[T]` mixin)

## Interface

```python
@runtime_checkable
class PeripheryLaborCoefficientsSource(Protocol):
    def get_coefficients(
        self, year: int
    ) -> PeripheryLaborCoefficients | NoDataSentinel: ...

    @property
    def metadata(self) -> PeripheryWageMetadata: ...
```

## Contract

| Aspect | Requirement |
|---|---|
| **Return for valid year** | `PeripheryLaborCoefficients` with `.year == year`, `.industries` matching the BEA Summary list for `year`, and `.wage_ratios` a `np.ndarray` of shape `(n_industries,)`. All values finite. |
| **Return for missing year** | `NoDataSentinel` (per FR-007 + Clarifications 2026-05-08). MUST NOT raise. MUST NOT return synthetic data. |
| **Axiom violation handling** (`ratio < 1.0`) | Pass-through unchanged; emit `EventBus.publish(Event(type="calibration_warning.axiom_violation", tick=..., payload=AxiomViolationEvent(...).model_dump()))` per (industry, year, ratio) below 1.0 (FR-002 per Clarifications 2026-05-08). MUST NOT clamp at source layer (clamp lives at calculator per research.md §R5). |
| **Determinism** | Repeat queries for the same `year` MUST return bit-identical `wage_ratios` arrays (cache hit). Cold-cache fetch MUST return bit-identical results across processes given the same input data (PWT v10.x is a fixed publication per research.md §R1). |
| **Metadata** | `metadata` property returns a `PeripheryWageMetadata` instance identifying publication, periphery definition, units, base year, industry-disaggregation note, calibration anchor, and v1 simplification caveats per FR-002 and research.md §R1. |
| **Cache semantics** | Default `cache_negative_results = True` (Spec 058 default — PWT is stable within session). |
| **Test substitution** | `SourceRegistry.register(PeripheryLaborCoefficientsSource, MockSource, variant="test")` substitutes for tests; `cache.clear()` resets between tests. |

## Acceptance criteria

| ID | Test | Method |
|---|------|--------|
| AC1 | Returns valid `PeripheryLaborCoefficients` for a year present in PWT | `test_get_coefficients_present_year` — assert shape, dtype, finiteness, industry list match |
| AC2 | Returns `NoDataSentinel` for a year before PWT v10.x's earliest year (1950) | `test_get_coefficients_pre_pwt_year` — assert `isinstance(result, NoDataSentinel)`, no exception raised |
| AC3 | Pass-through with warning on ratio < 1.0 | `test_axiom_violation_pass_through` — inject mock data with `ratio = 0.95`; assert (a) returned coefficient `wage_ratios[i] == 0.95` (NOT clamped), (b) `event_bus.get_history()` contains exactly one `Event(type="calibration_warning.axiom_violation", ...)` with `payload["industry"] == industry_i`, `payload["ratio"] == 0.95` |
| AC4 | Determinism across two consecutive `get_coefficients(year)` calls | `test_determinism_repeat_query` — assert `np.array_equal(result1.wage_ratios, result2.wage_ratios)` |
| AC5 | Metadata round-trips | `test_metadata_shape` — assert `metadata.publication == "PWT v10.01"`, `metadata.base_year == 2017`, etc. |

## Failure modes (defensive — should not occur in production)

| Failure | Detection | Response |
|---|------|------|
| PWT data corruption (NaN in `wage_ratios`) | `PeripheryLaborCoefficients` model validator | `pydantic.ValidationError` at fetch time |
| Industry-list mismatch with current BEA Summary vintage | Validation at `imperial_rent.compute()` startup (per FR-006) | `ValueError` with diagnostic naming mismatched codes |
| `_fetch` raises (e.g., DB connection error) | `CachedSource._resolve` does NOT catch; exception propagates | Per project standard "fail loud in logic layer" — caller decides whether to retry |
