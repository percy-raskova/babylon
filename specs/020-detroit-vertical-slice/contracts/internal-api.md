# Internal API Contracts: 020-detroit-vertical-slice

**Date**: 2026-02-23

This feature has no external REST/GraphQL APIs. All contracts are internal Python function signatures.

## Contract 1: Calculator Factory

```python
# src/babylon/economics/factory.py

def create_economics_services(
    session_factory: Callable[[], Session],
    tensor_registry: TensorRegistry,
) -> dict[str, Any]:
    """Create all economics calculator instances from database session.

    Returns dict with keys matching ServiceContainer field names.
    All 7 calculator slots + tensor_registry are populated.
    """
```

**Preconditions**:
- `session_factory` yields sessions connected to marxist-data-3NF.sqlite
- `tensor_registry` is already hydrated for desired years

**Postconditions**:
- Returned dict has exactly 8 keys (7 calculators + tensor_registry)
- All values are non-None
- All calculators are functional (methods callable, data sources connected)

## Contract 2: Modified step() Function

```python
# src/babylon/engine/simulation_engine.py

def step(
    state: WorldState,
    config: SimulationConfig,
    persistent_context: dict[str, Any] | None = None,
    defines: GameDefines | None = None,
    calculator_overrides: dict[str, Any] | None = None,  # NEW
) -> WorldState:
    """Execute one simulation tick.

    calculator_overrides: if provided, forwarded as kwargs to
    ServiceContainer.create(). Keys match ServiceContainer field names.
    """
```

**Backward compatibility**: Existing callers passing 4 positional args continue to work unchanged.

## Contract 3: Modified ServiceContainer.create()

```python
# src/babylon/engine/services.py

@classmethod
def create(
    cls,
    config: SimulationConfig | None = None,
    defines: GameDefines | None = None,
    metrics: MetricsCollectorProtocol | None = None,
    *,
    melt_calculator: Any = None,
    basket_calculator: Any = None,
    gamma_calculator: Any = None,
    capital_calculator: Any = None,
    throughput_calculator: Any = None,
    transition_engine: Any = None,
    imperial_rent_calculator: Any = None,
    tensor_registry: Any = None,  # NEW
) -> ServiceContainer:
```

## Contract 4: Modified Simulation.from_sqlite()

```python
# src/babylon/engine/simulation.py

@classmethod
def from_sqlite(
    cls,
    fips_codes: list[str],
    year: int = 2022,
    observers: list[SimulationObserver] | None = None,
    defines: GameDefines | None = None,
    years: Sequence[int] | None = None,  # NEW
) -> Simulation:
    """Create simulation from SQLite database.

    years: if provided, hydrate TensorRegistry for all specified years
    and wire economics calculators into ServiceContainer.
    If None, single-year behavior unchanged (backward compatible).
    """
```

## Contract 5: Time Series Extraction

```python
# src/babylon/engine/simulation.py

def get_time_series(self) -> list[dict[str, Any]]:
    """Extract time series records from completed simulation.

    Returns list of dicts, one per county per year-boundary tick.
    Each dict contains: year, fips, class_distribution, profit_rate,
    phi_hour, throughput_position, tau, data_source.
    """
```

## Contract 6: New Adapters

```python
# src/babylon/economics/melt/adapters.py

class SQLiteBEANationalGDPSource:
    """Implements BEADataSource protocol using fact_bea_national_industry."""

    def __init__(self, session_factory: Callable[[], Session]) -> None: ...
    def get_gdp(self, year: int) -> float | None: ...


class SQLiteQCEWNationalEmploymentSource:
    """Implements QCEWDataSource protocol using fact_qcew_annual."""

    def __init__(self, session_factory: Callable[[], Session]) -> None: ...
    def get_national_employment(self, year: int) -> int | None: ...
```

```python
# src/babylon/economics/gamma/adapters.py

class MVPUnpaidCareHoursSource:
    """Implements UnpaidCareHoursSource with hardcoded ATUS estimates."""

    def get_unpaid_care_hours(self, year: int) -> float | None: ...
```
