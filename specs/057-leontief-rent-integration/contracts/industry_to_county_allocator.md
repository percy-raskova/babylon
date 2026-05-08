# Contract: `IndustryToCountyAllocator`

**Spec**: 057 / FR-004, US4
**Location**: `src/babylon/economics/tensor_hierarchy/leontief_rent/industry_to_county_allocator.py` (NEW)
**Pattern**: Protocol + `Default*` (Spec 058's `CachedSource[T]` mixin)

## Interface

```python
@runtime_checkable
class IndustryToCountyAllocator(Protocol):
    def allocate(
        self,
        phi_vector: np.ndarray,        # Shape (n_industries,) — per-industry rent
        bea_industries: list[str],     # Order matches phi_vector
        year: int,                      # Tick year
    ) -> dict[str, float] | NoDataSentinel: ...
```

## Algorithm (per FR-004 + research.md §R4)

Inputs:

- `phi_vector` — per-industry rent, output of `ProductionChainRentCalculator.calculate(...).phi_vector`
- `bea_industries` — ordered BEA Summary codes (length must equal `len(phi_vector)`)
- `year` — tick year for QCEW lookup
- (injected at construction) QCEW reader, BEA-NAICS crosswalk reader, EventBus, `LeontiefRentDefines`

For each county FIPS in QCEW for the look-back window `[year - max_years, year]`:

1. Find the most recent `y' ≤ year` in the look-back window with QCEW data for this county
2. If no such `y'` exists, skip this county (absent from result dict)
3. For each NAICS code with employment data in QCEW at `(fips, y')`:
   - Compute `share[fips, naics] = qcew_emp[fips, naics, y'] / qcew_emp_national[naics, y']`
4. Aggregate to BEA Summary level via `xref_naics_bea_summary`:
   - `bea_share[fips, bea_code] = Σ_{naics → bea_code} share[fips, naics]`
   - Missing crosswalk rows contribute zero (no error)
5. Per-county rent allocation:
   - `county_rent[fips] = Σᵢ phi_vector[i] · bea_share[fips, bea_industries[i]]`
6. Normalize by total county employment-hours:
   - `phi_hour[fips] = county_rent[fips] / county_emp_hours[fips, y']`
   - `county_emp_hours[fips, y'] = Σ_naics qcew_emp[fips, naics, y'] · 2080`
7. If `y' < year`, emit `CalibrationWarning(QcewCarryForward, county_fips=fips, year=year, look_back_year=y', look_back_distance=year - y')`
8. Per-county outlier check: if `phi_hour[fips] < threshold_low` or `phi_hour[fips] > threshold_high`, emit `CalibrationWarning(PhiHourOutlier, ...)` (FR-008)

Return: `{fips: phi_hour}` for all counties with data in the window.

If the look-back window contains no QCEW data for any county (uniform suppression — would be unusual): return `NoDataSentinel`.

## Contract

| Aspect | Requirement |
|---|---|
| **Return shape** | `dict[str, float]` mapping `county_fips → phi_hour`. Counties absent from QCEW within the look-back window are absent from the dict. |
| **Conservation invariant** | `Σ_fips phi_hour[fips] · county_emp_hours[fips]` SHOULD recover `Σᵢ phi_vector[i] · y[i]` (national-total) within 1.0% tolerance (SC-003). Deviations beyond this typically indicate NAICS-BEA crosswalk gaps; logged but not asserted at runtime. |
| **Carry-forward bound** | Maximum look-back is `LeontiefRentDefines.qcew_carry_forward_max_years` (default 5; per Clarifications 2026-05-08) |
| **Carry-forward warning** | Exactly one `QcewCarryForwardEvent` per (county_fips, year, look_back_distance) per allocation call |
| **Outlier warning** | Exactly one `PhiHourOutlierEvent` per (county_fips, allocation call) for each county whose `phi_hour` falls outside `[phi_hour_outlier_threshold_low, phi_hour_outlier_threshold_high]` |
| **No silent zero** | A county whose look-back window has no data MUST be absent from the result dict — never present with `phi_hour = 0.0` (per FR-004 + Clarifications 2026-05-08). |
| **Cache semantics** | Default `cache_negative_results = True`; cache key = `year` (not the full input tuple — `phi_vector` is a function of year via the upstream calculator) |
| **Determinism** | Iteration order over QCEW counties MUST be stable (sorted by `county_fips` ascending) so `event_bus.get_history()` ordering is reproducible per Constitution III.7 |

## Acceptance criteria

| ID | Test | Method |
|---|------|--------|
| AC1 | Synthetic 2-industry, 2-county allocation recovers national total within 1% | `test_synthetic_two_county_conservation` — fabricate inputs with known shares; assert `abs(allocation_total - national_total) / national_total < 0.01` |
| AC2 | County with zero employment in an industry receives zero allocation from that industry | `test_zero_employment_zero_allocation` — fabricate county with `share[fips, naics_X] = 0`; assert allocation `phi_hour[fips]` excludes industry_X's contribution |
| AC3 | Carry-forward triggered for missing (county, year=Y) when (county, Y-1) has data | `test_carry_forward_one_year` — fabricate QCEW with `(fips, Y) = absent`, `(fips, Y-1) = present`; assert (a) `fips` present in result, (b) exactly one `QcewCarryForwardEvent(county_fips=fips, year=Y, look_back_year=Y-1, look_back_distance=1)` in event history |
| AC4 | Carry-forward bounded at max_years | `test_carry_forward_beyond_window` — fabricate QCEW with `(fips, Y) = absent` and `(fips, Y - max_years - 1) = present`; assert `fips` absent from result (no carry-forward beyond bound) |
| AC5 | Outlier detection fires for `phi_hour > threshold_high` | `test_outlier_event_high` — fabricate inputs producing `phi_hour > 1000.0`; assert exactly one `PhiHourOutlierEvent` in event history |
| AC6 | `NoDataSentinel` when entire window is empty | `test_window_uniformly_empty_returns_sentinel` — fabricate QCEW with no data in any year of the window; assert `isinstance(result, NoDataSentinel)` |
| AC7 | Determinism — bit-identical result dict + event history across two calls | `test_determinism_dict_and_event_order` — call `allocate(...)` twice; assert `result1 == result2` and `[e.payload for e in bus1] == [e.payload for e in bus2]` |
