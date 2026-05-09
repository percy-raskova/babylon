# Contract: `FinalDemandSource` — `Default*` implementation

**Spec**: 057 / FR-003, US3
**Location**: `src/babylon/economics/tensor_hierarchy/leontief_rent/final_demand.py` (NEW)
**Pattern**: Implements existing `FinalDemandSource(Protocol)` from `production_chain_rent.py:82` + extends `CachedSource[np.ndarray]`

## Interface (existing Protocol — `production_chain_rent.py:82`)

```python
class FinalDemandSource(Protocol):
    def get_final_demand(self, year: int) -> np.ndarray: ...
```

## New `Default*` adapter pattern

The Protocol does not return `NoDataSentinel` (it predates Spec 058). The new implementation reconciles by:

- `_fetch(year) -> np.ndarray | NoDataSentinel` — the `CachedSource[T]` contract (sentinel-on-miss per FR-007)
- `get_final_demand(year) -> np.ndarray` — the legacy Protocol adapter; raises `ValueError` if `_fetch` returned the sentinel

This lets the new source satisfy both the existing Protocol (callers get exception semantics) and the Spec 058 sentinel convention (callers using `_resolve` directly get sentinel semantics).

## Contract

| Aspect | Requirement |
|---|---|
| **Return for valid year** | `np.ndarray` of shape `(n_industries,)`, `dtype=float64`, ordered identically to `DefaultInterIndustryFlowSource(year).industries`. All entries non-negative (BEA final demand is non-negative by definition). |
| **Return for missing year (`_fetch`)** | `NoDataSentinel` |
| **Return for missing year (`get_final_demand`)** | `raise ValueError(f"No final-demand data for year {year}")` |
| **Source data** | BEA Use Table Summary level, "Total Final Uses (GDP)" column, from `marxist-data-3NF.sqlite` via `fact_bea_use_table` (table name confirmed at impl time per research.md §R2) |
| **Industry-list alignment** | MUST equal `DefaultInterIndustryFlowSource(year).industries` (validated by `imperial_rent.compute()` per FR-006) |
| **Cache semantics** | Default `cache_negative_results = True` |
| **National-total invariant** | `result.sum()` SHOULD be within 5% of independently-recoverable BEA published GDP final-demand total for that year (US3 acceptance scenario 1 — soft check, not assertion-grade) |

## Acceptance criteria

| ID | Test | Method |
|---|------|--------|
| AC1 | Returns shape-correct vector for a year with data | `test_get_final_demand_shape` — assert shape matches `n_industries`, dtype `float64`, non-negative |
| AC2 | `_fetch` returns sentinel for missing year | `test_fetch_missing_year_sentinel` — assert `isinstance(source._fetch(1900), NoDataSentinel)` |
| AC3 | `get_final_demand` raises for missing year | `test_get_final_demand_missing_year_raises` — `pytest.raises(ValueError, match=r"No final-demand data for year 1900")` |
| AC4 | National total ≈ BEA GDP final-demand within 5% | `test_national_total_matches_bea_gdp` — soft check using a fixture year; `assert abs(result.sum() - expected_gdp) / expected_gdp < 0.05` |
| AC5 | Industry order matches inter-industry flow source | `test_industry_order_matches_flow_source` — assert `flow_source.industries(year) == [...inferred order from result...]` (verified via shape + parallel ordering invariant) |
| AC6 | Determinism | `test_determinism_repeat_query` — `assert np.array_equal(source.get_final_demand(2015), source.get_final_demand(2015))` |
