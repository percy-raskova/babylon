# Protocol Contracts: Tensor Hierarchy

**Feature**: 025-tensor-hierarchy | **Date**: 2026-02-26

## Tensor Source Protocols

Each Level 1 tensor has a data source Protocol for dependency injection:

### InterIndustryFlowSource

```python
@runtime_checkable
class InterIndustryFlowSource(Protocol):
    """Loads BEA I-O coefficient data from SQLite."""

    def get_direct_requirements(self, year: int) -> InterIndustryFlow | NoDataSentinel:
        """Load the direct requirements coefficient matrix A for a given year."""
        ...

    def get_industry_codes(self) -> list[str]:
        """Return ordered list of BEA industry codes at Summary level."""
        ...

    def available_years(self) -> frozenset[int]:
        """Return set of years with I-O data available."""
        ...
```

### GeographicFlowSource

```python
@runtime_checkable
class GeographicFlowSource(Protocol):
    """Loads BTS FAF commodity flow data from SQLite."""

    def get_flows(self, year: int, commodity_code: str | None = None) -> GeographicFlow | NoDataSentinel:
        """Load O-D flow matrix for a given year and optional commodity."""
        ...

    def get_cfs_areas(self) -> list[str]:
        """Return ordered list of CFS Area codes."""
        ...

    def get_cfs_to_county_mapping(self) -> dict[str, list[str]]:
        """Return mapping from CFS Area code to list of county FIPS codes."""
        ...
```

### VisibilitySource

```python
@runtime_checkable
class VisibilitySource(Protocol):
    """Computes visibility metric by wrapping gamma module."""

    def get_visibility(self, year: int) -> VisibilityMetric | NoDataSentinel:
        """Compute diagonal visibility metric for a given year."""
        ...

    def get_shadow_subsidy(
        self, year: int, dept_iii_value: float, melt: float | None = None
    ) -> ShadowSubsidy | NoDataSentinel:
        """Compute shadow subsidy from visibility and Dept III value."""
        ...
```

### ReproductionSource (P4)

```python
@runtime_checkable
class ReproductionSource(Protocol):
    """Loads reproduction requirements from CEX + ATUS."""

    def get_requirements(self, year: int) -> ReproductionRequirements | NoDataSentinel:
        """Load consumption and labor requirements by social class."""
        ...

    def total_reproduction_cost(self, social_class: SocialRole, year: int, snlt: float) -> float | NoDataSentinel:
        """Compute total reproduction cost in labor-time units."""
        ...
```

### ClassTransitionSource (P5)

```python
@runtime_checkable
class ClassTransitionSource(Protocol):
    """Loads class transition matrices from PSID or programmatic input."""

    def get_transition_matrix(self, period: tuple[int, int]) -> ClassTransitionMatrix | NoDataSentinel:
        """Load transition matrix for a given time period."""
        ...

    def get_stationary_distribution(self, period: tuple[int, int]) -> StationaryDistribution | NoDataSentinel:
        """Compute long-run class distribution."""
        ...
```

## Computation Protocols

### LeontiefComputer

```python
@runtime_checkable
class LeontiefComputer(Protocol):
    """Computes Leontief inverse and total labor coefficients."""

    def compute_inverse(self, flow: InterIndustryFlow) -> LeontiefInverse:
        """Compute L = (I-A)^{-1}. Raises LinAlgError if singular."""
        ...

    def total_labor_coefficients(
        self, leontief: LeontiefInverse, direct_labor: ndarray
    ) -> ndarray:
        """Compute total labor (direct + indirect) per $ of final demand."""
        ...
```

### ImperialRentComputer

```python
@runtime_checkable
class ImperialRentComputer(Protocol):
    """Computes imperial rent field from geographic flows."""

    def compute_rent_field(self, flow: GeographicFlow) -> ImperialRentField:
        """Compute net value extraction (inflow - outflow) per area."""
        ...

    def decompose_symmetric_antisymmetric(
        self, flow: GeographicFlow
    ) -> tuple[sparse.csr_matrix, sparse.csr_matrix]:
        """Decompose F into symmetric (exchange) and antisymmetric (extraction)."""
        ...
```

### DepartmentAggregator

```python
@runtime_checkable
class DepartmentAggregator(Protocol):
    """Aggregates ~70 BEA industries to 4 Marxian departments."""

    def aggregate(
        self, flow: InterIndustryFlow, mapping: dict[str, Department]
    ) -> InterIndustryFlow:
        """Produce a 4x4 department-level I-O matrix."""
        ...

    def get_default_mapping(self) -> dict[str, Department]:
        """Load the BEA-to-department mapping from TOML data file."""
        ...
```
