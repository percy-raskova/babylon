# Research: Fundamental Tensor Primitive

**Feature**: 011-fundamental-tensor-primitive
**Date**: 2026-02-01

## Executive Summary

The Babylon codebase has a **functional but incomplete tensor foundation**. The existing `ValueTensor4x3` model provides the correct 4×3 structure (departments × value components), but tensors are created ephemerally during hydration and immediately discarded after extracting scalar values. This spec transforms tensors into **persistent cached primitives** that serve as the single source of truth for all economic data.

---

## R1: Existing Tensor Implementation

### Current State

**Location**: `src/babylon/economics/tensor.py`

The existing implementation provides:
- `DepartmentRow`: Frozen Pydantic model with `c`, `v`, `s` fields (Currency type)
- `ValueTensor4x3`: County-year tensor with four `DepartmentRow` instances
- Computed properties: `profit_rate`, `exploitation_rate`, `organic_composition`
- Shadow labor support: `visibility_g33`, `shadow_subsidy`, `exploitation_rate_fortunati`

### Gap Analysis

| Feature | Exists | Gap |
|---------|--------|-----|
| 4×3 structure | ✅ | - |
| Pydantic validation | ✅ | - |
| Computed ratios | ✅ | - |
| Labor-hour units | ❌ | Values stored as Currency |
| Multi-tensor container | ❌ | Single county-year only |
| Caching/registry | ❌ | Created per-invocation |
| "No data" sentinel | ❌ | Missing data raises exceptions |
| Geographic aggregation | ❌ | No county→state→nation |

### Decision

**Extend existing `ValueTensor4x3`** rather than replace it.

**Rationale**:
1. The 4×3 shape aligns with Marxist departmental analysis
2. Existing computed properties are well-tested
3. Pydantic validation catches invalid data early
4. Extension preserves backward compatibility with existing tests

**Alternatives Rejected**:
- **NumPy ndarray**: Loses Pydantic validation and semantic field names
- **xarray DataArray**: Overkill for fixed 4×3 shape, adds dependency
- **Complete rewrite**: Discards working test suite and computed field logic

---

## R2: SNLT Conversion Strategy

### The Transformation Problem

Converting monetary values to labor-time requires the Socially Necessary Labor Time (SNLT) conversion factor. Per Marx, SNLT varies with:
- Productivity (more productive economy = less SNLT per dollar)
- Time (productivity changes across years)

### Spec Clarification

From the spec's Assumption #1:
> Until SNLT conversion is fully implemented, tensor values represent wage-proportional labor-time proxies. Derived ratios (r, e, OCC) are exact; absolute magnitudes require SNLT calibration.

### Decision

**Year-specific conversion factors as configuration**, with factor = 1.0 as interim default.

**Implementation**:
```python
class SNLTConfig(BaseModel):
    """Year-specific SNLT conversion factors."""
    model_config = ConfigDict(frozen=True)

    factors: dict[int, float] = Field(default_factory=dict)
    default_factor: float = Field(default=1.0, ge=0.0)

    def get_factor(self, year: int) -> float:
        return self.factors.get(year, self.default_factor)
```

**Key Insight**: Derived ratios (profit rate, exploitation rate, OCC) are **unit-independent**. The ratio `s/v` is the same whether measured in dollars or labor-hours because units cancel. This means the proxy is **exact for ratios**, only approximate for absolute magnitudes.

**Alternatives Rejected**:
- **Single global SNLT**: Ignores productivity changes over time
- **Inflation adjustment**: Masks real productivity changes; conflates nominal with real

---

## R3: BEA Ratio Fallback Pattern

### The Problem

BEA publishes c/v and s/v ratios at the industry level, but:
- Not all years have complete data
- Not all industries have ratios for all years
- County-level analysis requires applying industry ratios to QCEW data

### Spec Clarification

From FR-015:
> When BEA ratios are missing for a FIPS/year but QCEW data exists, the tensor MUST use the nearest available year's BEA ratio (temporal interpolation).

### Decision

**Temporal interpolation with cascade fallback**:

1. Query exact `(industry, year)` from BEA tables
2. If missing: Query nearest prior year for same industry
3. If no prior: Query nearest future year for same industry
4. If none found: Use department-level YAML defaults (existing behavior)

**Rationale**: BEA ratios are relatively stable across years for most industries. Temporal interpolation is more accurate than:
- Returning "no data" (loses usable QCEW wage data)
- National averages (ignores industry structure)

**Implementation**:
```python
def get_bea_ratio_with_fallback(
    source: BEADataSource,
    naics_code: str,
    year: int,
    ratio_type: Literal["cv", "sv"],
    max_delta: int = 5,
) -> float | None:
    # Try exact year
    if ratio := source.get_ratio(naics_code, year, ratio_type):
        return ratio

    # Try prior years (newest first)
    for delta in range(1, max_delta + 1):
        if ratio := source.get_ratio(naics_code, year - delta, ratio_type):
            return ratio

    # Try future years (oldest first)
    for delta in range(1, max_delta + 1):
        if ratio := source.get_ratio(naics_code, year + delta, ratio_type):
            return ratio

    return None  # Fall through to YAML defaults
```

---

## R4: Geographic Aggregation Strategy

### The Problem

The spec requires correct aggregation from county → state → nation (FR-016). With 3,143 counties × 50 states × ~50 years, pre-computing all aggregates would be memory-intensive.

### Spec Clarification

From the Clarifications section:
> Aggregation from county → state → nation: **Compute on-demand when requested, cache results** (lazy aggregation strategy).

### Decision

**Lazy computation with LRU caching**.

**Implementation**:
```python
class TensorRegistry:
    def __init__(self, maxsize: int = 10_000):
        self._county_cache: dict[tuple[str, int], ValueTensor4x3 | NoDataSentinel] = {}
        self._aggregate_cache = LRUCache(maxsize=maxsize // 10)

    def get_aggregate(
        self, level: GeoLevel, code: str, year: int
    ) -> ValueTensor4x3 | NoDataSentinel:
        cache_key = (level, code, year)
        if cache_key in self._aggregate_cache:
            return self._aggregate_cache[cache_key]

        # Compute aggregate
        if level == GeoLevel.STATE:
            county_fips = self._get_counties_for_state(code)
            tensors = [self.get(fips, year) for fips in county_fips]
            aggregate = self._sum_tensors([t for t in tensors if t])
        # ... similar for NATION

        self._aggregate_cache[cache_key] = aggregate
        return aggregate
```

**Memory Analysis**:
- County tensor: ~1KB (12 floats + metadata)
- 3,143 counties × 10 years = ~30MB for common queries
- LRU eviction prevents unbounded growth
- Full US × 50 years = ~157MB (within 500MB target)

---

## R5: "No Data" Sentinel Pattern

### The Problem

Zero is a valid economic value (a county could have zero Department III activity). The tensor must distinguish between:
- "This county has zero activity" (valid data)
- "We have no data for this county" (missing data)

### Spec Clarification

From Edge Cases:
> Hexagon requests data for FIPS code not in tensor: **Return a sentinel "no data" object** (distinct from zero values, per FR-014).

### Decision

**`NoDataSentinel` frozen dataclass with falsy `__bool__`**.

**Implementation**:
```python
@dataclass(frozen=True)
class NoDataSentinel:
    """Explicit marker for missing tensor data."""
    fips: str
    year: int
    reason: str

    def __bool__(self) -> bool:
        """Allows `if tensor := registry.get(fips, year)` pattern."""
        return False
```

**Consumer Pattern**:
```python
# Clean usage with walrus operator
if tensor := registry.get(fips, year):
    profit_rate = tensor.profit_rate
else:
    # Handle missing data (gray out hexagon, show placeholder, etc.)
    display_no_data(tensor.reason)
```

**Alternatives Rejected**:
- **None return**: Loses context (why is data missing?)
- **Exception raising**: Forces try/catch everywhere; missing data is expected
- **Optional[ValueTensor4x3]**: Same as None, loses reason

---

## R6: Hexagon Data Access Pattern

### The Problem

Hexagons must display economic data without touching the database (FR-004). The current architecture passes only scalar `profit_rate` via `TerritoryState`.

### Spec Clarification

From FR-020:
> Hexagons MUST receive data from: the primitive tensor, derived tensors, calculated values, or magic constants—never direct database access.

### Decision

**Hexagons receive `TensorRegistry` reference; query by FIPS from territory**.

**Pattern**:
```python
# In visualization layer initialization
class HexagonRenderer:
    def __init__(self, registry: TensorRegistry):
        self._registry = registry

    def render_hex(self, territory: TerritoryState, hex_state: HexState) -> None:
        # Get tensor for this territory's county
        tensor = self._registry.get(territory.fips, territory.year)

        if tensor:
            color = self._profit_rate_to_color(tensor.profit_rate)
            tooltip = self._format_tensor_summary(tensor)
        else:
            color = PALETTE.ASH  # No data
            tooltip = f"No data: {tensor.reason}"
```

**Verification**: Static import analysis confirms `src/babylon/ui/` does not import from `src/babylon/data/`.

---

## R7: Derived Tensor Values

### The Problem

Derived values (imperial rent, visibility metric, etc.) must be computed from the primitive tensor, not from separate database queries.

### Spec Clarification

From FR-005:
> All derived economic values (imperial rent, exploitation rate, etc.) MUST be computed from the primitive tensor, not from database queries.

From Edge Cases:
> Derived tensor produces negative values: **Allow negative values in derived tensors** (they have economic meaning, e.g., negative imperial rent indicates periphery status).

### Decision

**Derived values as computed properties on tensor; derived tensors as separate computations**.

**Implementation**:
```python
# On ValueTensor4x3 (per-county scalar derivations)
@computed_field
def imperial_rent(self) -> LaborHours:
    """Φ = total wages - total value produced.

    Positive = core (receiving imperial rent)
    Negative = periphery (donating imperial rent)
    """
    total_wages = self.total_v  # v represents wages in labor-hours
    total_value = self.total_value  # c + v + s
    return LaborHours(total_wages - total_value)

# Separate derived tensor class for multi-county analysis
class ImperialRentField:
    """Geographic distribution of imperial rent."""
    def __init__(self, registry: TensorRegistry, year: int):
        self._registry = registry
        self._year = year

    def get_rent(self, fips: str) -> LaborHours | NoDataSentinel:
        if tensor := self._registry.get(fips, self._year):
            return tensor.imperial_rent
        return NoDataSentinel(fips, self._year, "No tensor data")
```

---

## Data Source Traceability

Per Constitution III.4, all quantities must trace to federal data:

| Quantity | Source | Notes |
|----------|--------|-------|
| Wages (v proxy) | QCEW `total_wages_usd` | Bureau of Labor Statistics |
| Employment | QCEW `employment` | Bureau of Labor Statistics |
| c/v ratio | BEA Input-Output tables | Bureau of Economic Analysis |
| s/v ratio | BEA GDP by Industry | Bureau of Economic Analysis |
| Department allocation | NAICS → Dept mapping | Derived from BEA categories |
| SNLT factor | Configuration (TBD) | Requires calibration research |

---

## Performance Considerations

### Memory Budget

| Component | Estimate |
|-----------|----------|
| Single ValueTensor4x3 | ~1KB |
| 100 counties × 10 years | ~1MB |
| Full US (3,143) × 10 years | ~30MB |
| Full US × 50 years | ~157MB |
| Aggregate cache (LRU 1000) | ~1MB |
| **Total (typical simulation)** | **<50MB** |

### Load Time Budget

Target: 100 counties × 10 years in <5 seconds

| Operation | Estimate |
|-----------|----------|
| SQL query per county-year | ~10ms |
| 1,000 queries | ~10s (sequential) |
| Batch query (1,000 rows) | ~100ms |
| Python processing per tensor | ~0.5ms |
| **Total (batched)** | **<2s** |

**Recommendation**: Batch SQL queries by year to minimize round-trips.

---

## Open Questions (Deferred)

1. **SNLT Calibration Data**: Where do year-specific SNLT factors come from? (Deferred to future spec)
2. **Quarterly Aggregation**: FR-017 mentions quarterly → annual, but QCEW annual data is already aggregated (may be N/A)
3. **Derived Tensor Caching**: Should `ImperialRentField` cache its computations? (Implementation detail)
