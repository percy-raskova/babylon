# Data Model: Capital Stock Dynamics

**Feature**: 012-capital-stock-dynamics
**Date**: 2026-02-01
**Phase**: 1 - Data Model & Contracts

## Overview

This document defines the data model for Capital Stock Dynamics, including new types, their relationships to existing models, and validation constraints.

## Type Hierarchy

```
babylon.economics
├── tensor.py (existing)
│   ├── ValueTensor4x3      # Primitive: c, v, s flows per county-year
│   ├── DepartmentRow       # Row of tensor: c, v, s for one department
│   └── NoDataSentinel      # Missing data marker
│
├── tensor_registry.py (existing)
│   ├── TensorRegistry      # Cache for ValueTensor4x3
│   └── GeoLevel            # Aggregation levels
│
├── depreciation.py (NEW)
│   └── DepreciationConfig  # Depreciation rate configuration
│
├── capital_stock.py (NEW)
│   └── CapitalStockCalculator  # Computes K from c flows
│
└── derived_metrics.py (NEW)
    └── DerivedTensorMetrics    # K, r_stock, OCC, e for county-year
```

## New Types

### DepreciationConfig

```python
@dataclass(frozen=True)
class DepreciationConfig:
    """Configuration for capital depreciation rate (δ).

    The depreciation rate determines how much of the capital stock
    is consumed each period. Based on BEA fixed asset tables.

    Attributes:
        rate: Annual depreciation rate (default 0.07 = 7%).
            Valid range: [0.01, 0.20].

    Example:
        >>> config = DepreciationConfig(rate=0.07)
        >>> config.rate
        0.07
    """

    rate: float = 0.07

    def __post_init__(self) -> None:
        """Validate depreciation rate is in valid range."""
        if not 0.01 <= self.rate <= 0.20:
            raise ValueError(
                f"Depreciation rate must be in [0.01, 0.20], got {self.rate}"
            )

    @classmethod
    def slow(cls) -> DepreciationConfig:
        """Slow depreciation (δ = 0.05) for sensitivity analysis."""
        return cls(rate=0.05)

    @classmethod
    def fast(cls) -> DepreciationConfig:
        """Fast depreciation (δ = 0.10) for sensitivity analysis."""
        return cls(rate=0.10)
```

**Constraints**:
- Rate must be in [0.01, 0.20] (1% to 20% annual)
- Immutable (frozen dataclass)
- Default 0.07 traces to BEA average depreciation rate

### CapitalStockCalculator

```python
class CapitalStockCalculator:
    """Computes capital stock (K) from constant capital flows (c).

    Uses the perpetual inventory method with TSSI historical cost valuation:
        K[t+1] = K[t] × (1 - δ) + Σ_μ c^μ[t]

    Initial capital stock assumes steady state:
        K_0 = c_0 / δ

    Args:
        registry: TensorRegistry providing access to ValueTensor4x3 data.
        depreciation: Depreciation configuration (default: δ = 0.07).

    Example:
        >>> registry = TensorRegistry()
        >>> # ... hydrate registry with data ...
        >>> calculator = CapitalStockCalculator(registry)
        >>> K = calculator.get_K("26163", 2022)
        >>> if K:
        ...     print(f"Capital stock: {K}")
    """

    def __init__(
        self,
        registry: TensorRegistry,
        depreciation: DepreciationConfig | None = None,
    ) -> None: ...

    @property
    def depreciation_rate(self) -> float:
        """Get the depreciation rate δ."""
        ...

    def get_K(self, fips: str, year: int) -> float | NoDataSentinel:
        """Get capital stock for a specific county-year.

        Returns cached value if available, otherwise computes from
        time series starting at first available year.

        Args:
            fips: 5-digit FIPS county code.
            year: Calendar year.

        Returns:
            Capital stock K in labor-hours, or NoDataSentinel if data unavailable.
        """
        ...

    def compute_time_series(
        self, fips: str, start_year: int | None = None, end_year: int | None = None
    ) -> dict[int, float]:
        """Compute capital stock for all available years in range.

        Args:
            fips: 5-digit FIPS county code.
            start_year: First year (default: MIN_YEAR from registry).
            end_year: Last year (default: MAX_YEAR from registry).

        Returns:
            Dictionary mapping year -> capital stock K.
            Missing years are skipped (not interpolated).
        """
        ...

    def get_K_aggregate(
        self, level: GeoLevel, code: str, year: int
    ) -> float | NoDataSentinel:
        """Get aggregated capital stock for state or nation.

        Aggregates are the sum of constituent county capital stocks.

        Args:
            level: Aggregation level (STATE or NATION).
            code: Geographic code ("26" for Michigan, "US" for nation).
            year: Calendar year.

        Returns:
            Aggregated capital stock, or NoDataSentinel if insufficient data.
        """
        ...

    def clear_cache(self) -> None:
        """Clear cached capital stock values."""
        ...

    def cache_info(self) -> dict[str, int]:
        """Get cache statistics."""
        ...
```

**Cache Structure**:
```python
# Internal cache: (fips, year) -> K value
_cache: dict[tuple[str, int], float]

# Time series cache: fips -> dict[year, K]
_time_series_cache: dict[str, dict[int, float]]
```

**Thread Safety**:
- Uses `threading.RLock()` for cache access
- Follows TensorRegistry pattern

### DerivedTensorMetrics

```python
@dataclass(frozen=True)
class DerivedTensorMetrics:
    """Container for derived economic ratios computed from tensor + capital stock.

    This is the primary output type for TRPF analysis, combining primitive
    tensor data with derived capital stock.

    Attributes:
        fips_code: 5-digit FIPS county code.
        year: Calendar year.
        capital_stock: K (accumulated capital stock in labor-hours).
        profit_rate_stock: r = s / (K + v) (stock-based profit rate).
        organic_composition: OCC = c / v (from tensor).
        exploitation_rate: e = s / v (from tensor).
        tensor: Source ValueTensor4x3.
        depreciation_rate: δ used for K computation.

    Example:
        >>> metrics = calculator.get_metrics("26163", 2022)
        >>> if metrics:
        ...     print(f"Stock-based profit rate: {metrics.profit_rate_stock:.4f}")
        ...     print(f"OCC: {metrics.organic_composition:.2f}")
    """

    fips_code: str
    year: int
    capital_stock: float  # K
    profit_rate_stock: float  # r = s / (K + v)
    organic_composition: float  # c / v
    exploitation_rate: float  # s / v
    tensor: ValueTensor4x3
    depreciation_rate: float

    @property
    def profit_rate_flow(self) -> float:
        """Flow-based profit rate s/(c+v) from underlying tensor."""
        return self.tensor.profit_rate

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary for analysis/export."""
        return {
            "fips_code": self.fips_code,
            "year": self.year,
            "capital_stock": self.capital_stock,
            "profit_rate_stock": self.profit_rate_stock,
            "profit_rate_flow": self.profit_rate_flow,
            "organic_composition": self.organic_composition,
            "exploitation_rate": self.exploitation_rate,
            "depreciation_rate": self.depreciation_rate,
            "total_c": float(self.tensor.total_c),
            "total_v": float(self.tensor.total_v),
            "total_s": float(self.tensor.total_s),
        }
```

## Relationships

```
┌─────────────────────┐
│   TensorRegistry    │
│ ─────────────────── │
│ get(fips, year)     │◄────────────────┐
│ get_aggregate(...)  │                 │
└─────────────────────┘                 │
          │                             │
          │ returns                     │ uses
          ▼                             │
┌─────────────────────┐        ┌────────┴────────────┐
│  ValueTensor4x3     │        │ CapitalStockCalc    │
│ ─────────────────── │◄───────│ ─────────────────── │
│ total_c             │        │ get_K(fips, year)   │
│ total_v             │        │ compute_time_series │
│ total_s             │        │ get_metrics(...)    │
│ profit_rate (flow)  │        └─────────┬───────────┘
└─────────────────────┘                  │
                                         │ produces
                                         ▼
                              ┌─────────────────────┐
                              │ DerivedTensorMetrics│
                              │ ─────────────────── │
                              │ capital_stock (K)   │
                              │ profit_rate_stock   │
                              │ organic_composition │
                              │ exploitation_rate   │
                              └─────────────────────┘
```

## Validation Rules

### DepreciationConfig

| Field | Type | Constraint | Rationale |
|-------|------|------------|-----------|
| rate | float | [0.01, 0.20] | BEA data range; outside this is unrealistic |

### CapitalStockCalculator

| Operation | Validation | Behavior |
|-----------|------------|----------|
| get_K with missing tensor | NoDataSentinel returned | Return sentinel with reason |
| get_K with year < MIN_YEAR | NoDataSentinel returned | "Year outside data range" |
| K computation yields negative | Clamp to 0.0 | Capital cannot be negative |
| Missing year in time series | Skip year | Continue from last available |

### DerivedTensorMetrics

| Field | Type | Constraint | Rationale |
|-------|------|------------|-----------|
| capital_stock | float | >= 0.0 | Capital cannot be negative |
| profit_rate_stock | float | May be inf | Division by zero if (K + v) = 0 |
| organic_composition | float | May be inf | Division by zero if v = 0 |
| exploitation_rate | float | May be inf | Division by zero if v = 0 |

## Computation Formulas

### Capital Stock (K)

**Initial Value (t = first available year)**:
```
K_0 = total_c_0 / δ
```

**Subsequent Values**:
```
K[t] = K[t-1] × (1 - δ) + total_c[t-1]
```

Where:
- total_c = Σ_μ c^μ = dept_I.c + dept_IIa.c + dept_IIb.c + dept_III.c
- δ = depreciation rate (default 0.07)

### Stock-Based Profit Rate

```
r_stock = total_s / (K + total_v)
```

Where:
- total_s = Σ_μ s^μ (from tensor)
- total_v = Σ_μ v^μ (from tensor)
- K = capital stock (computed)

### Organic Composition of Capital (OCC)

```
OCC = total_c / total_v
```

This is already a computed_field on ValueTensor4x3, but included in DerivedTensorMetrics for convenience.

### Exploitation Rate (e)

```
e = total_s / total_v
```

Also already on ValueTensor4x3.

## Edge Cases

### Division by Zero

When denominator is zero, return `float('inf')`:

```python
# Profit rate when (K + v) = 0
if capital_stock + tensor.total_v == 0.0:
    profit_rate_stock = float("inf")
else:
    profit_rate_stock = tensor.total_s / (capital_stock + tensor.total_v)
```

This matches existing ValueTensor4x3 behavior.

### Negative Capital Stock

Theoretically impossible but can occur with extreme depreciation. Clamp to zero:

```python
K_new = max(0.0, K_prev * (1 - delta) + total_c)
```

### Missing Years

Skip and continue from last available:

```python
years = [2010, 2011, 2013, 2014]  # 2012 missing
# K[2013] computed from K[2011], not interpolated K[2012]
```

Log warning when this occurs.

### First Year Without Data

If first year in range has no data, move to next available:

```python
start_year = 2010  # requested
first_available = 2012  # actual
K_0 = total_c[2012] / δ  # Initialize from 2012
```

## Integration Points

### With TensorRegistry

```python
# CapitalStockCalculator uses TensorRegistry as data source
registry = TensorRegistry()
registry.hydrate_counties(hydrator, fips_codes, years)

calculator = CapitalStockCalculator(registry)
K = calculator.get_K("26163", 2022)
```

### With Simulation Engine

```python
# SimulationEngine can optionally use CapitalStockCalculator
# for TRPF analysis during simulation
engine = SimulationEngine(
    registry=registry,
    capital_stock_calculator=calculator,  # Optional
)
```

### With Analysis Scripts

```python
# Export time series for statistical analysis
import pandas as pd

fips = "26163"
years = range(2010, 2025)
time_series = calculator.compute_time_series(fips, 2010, 2024)
metrics = [calculator.get_metrics(fips, y) for y in time_series.keys()]

df = pd.DataFrame([m.to_dict() for m in metrics if m])
```
