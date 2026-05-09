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
| **Determinism** | Repeat queries for the same `year` MUST return bit-identical `wage_ratios` arrays (cache hit). Cold-cache fetch MUST return bit-identical results across processes given the same input data (Hickel ERDI time series is a fixed publication per research.md §R1, REVISED 2026-05-08). |
| **Metadata** | `metadata` property returns a `PeripheryWageMetadata` instance identifying publication (Hickel/Sullivan/Zoomkawala 2021 ERDI), periphery definition, units (dimensionless ERDI ratio), base year, industry-disaggregation note, calibration anchor, and v1 simplification caveats per FR-002 and research.md §R1. |
| **Cache semantics** | Default `cache_negative_results = True` (Spec 058 default — Hickel CSV is static). |
| **Source data** | `fact_hickel_erdi_annual` table in `marxist-data-3NF.sqlite`, ingested at setup from `/media/user/data/babylon-data/babylon_hickel_final.csv` per task T024d. The `scale_type` parameter (default `"Intensive"`) selects between Hickel's two methodological framings — see research.md §R8.4 for the distinction. |
| **Test substitution** | `SourceRegistry.register(PeripheryLaborCoefficientsSource, MockSource, variant="test")` substitutes for tests; `cache.clear()` resets between tests. |

## Acceptance criteria

| ID | Test | Method |
|---|------|--------|
| AC1 | Returns valid `PeripheryLaborCoefficients` for a year present in Hickel ERDI series | `test_get_coefficients_present_year` — for year 2015 + scale_type "Intensive", assert `wage_ratios.shape == (n_industries,)`, all elements equal `8.25` (the 2015 Intensive ERDI value per `babylon_hickel_final.csv`), dtype float64, finite |
| AC2 | Returns `NoDataSentinel` for a year before Hickel series start (1959) or after end (2018) | `test_get_coefficients_outside_window` — assert `isinstance(source.get_coefficients(1900), NoDataSentinel)` and same for 2030; no exception raised |
| AC3 | Pass-through with warning on ratio < 1.0 | `test_axiom_violation_pass_through` — inject mock data with `ERDI = 0.95` (would be unusual but possible); assert (a) returned `wage_ratios` ALL equal `0.95` (NOT clamped), (b) `event_bus.get_history()` contains exactly N `AxiomViolationEvent`s where N = n_industries (uniform broadcast → fires for every industry that year). Implementation MAY emit a single year-aggregate event instead — contract permits either pattern as long as the violation is observable in the bus history |
| AC4 | Determinism across two consecutive `get_coefficients(year)` calls | `test_determinism_repeat_query` — assert `np.array_equal(result1.wage_ratios, result2.wage_ratios)` |
| AC5 | Metadata round-trips | `test_metadata_shape` — assert `metadata.publication == "Hickel, Sullivan & Zoomkawala (2021) — ERDI time series"`, `metadata.base_year == 2017`, `metadata.units == "ERDI — dimensionless ratio (market exchange rate / PPP exchange rate)"`, etc. |

## Failure modes (defensive — should not occur in production)

| Failure | Detection | Response |
|---|------|------|
| PWT data corruption (NaN in `wage_ratios`) | `PeripheryLaborCoefficients` model validator | `pydantic.ValidationError` at fetch time |
| Industry-list mismatch with current BEA Summary vintage | Validation at `imperial_rent.compute()` startup (per FR-006) | `ValueError` with diagnostic naming mismatched codes |
| `_fetch` raises (e.g., DB connection error) | `CachedSource._resolve` does NOT catch; exception propagates | Per project standard "fail loud in logic layer" — caller decides whether to retry |
