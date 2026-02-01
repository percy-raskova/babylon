# Data Model: Data Preflight & Loader Unification

**Branch**: `009-data-preflight` | **Date**: 2026-01-31

## Entities

### PreflightCheck (existing)

Single preflight check result. **No changes required.**

```python
@dataclass(frozen=True)
class PreflightCheck:
    check_id: str                              # e.g., "lodes:crosswalk"
    status: Literal["ok", "warn", "fail"]
    message: str                               # Human-readable description
    hint: str | None = None                    # Actionable guidance
    details: dict[str, object] = field(...)   # Structured metadata
```

### PreflightResult (existing)

Aggregated preflight results. **No changes required.**

```python
@dataclass
class PreflightResult:
    checks: list[PreflightCheck]

    @property
    def failures(self) -> list[PreflightCheck]: ...
    @property
    def warnings(self) -> list[PreflightCheck]: ...
    @property
    def ok(self) -> bool: ...
```

### ScenarioDataConfig (new)

Configuration for scenario-specific data requirements.

```python
@dataclass(frozen=True)
class ScenarioDataConfig:
    """Data requirements for a simulation scenario."""

    name: str                          # e.g., "detroit"
    required_loaders: list[str]        # e.g., ["qcew", "lodes", "census", "tiger"]
    county_fips: list[str]             # e.g., ["26163", "26125", "26099"]
    year_range: tuple[int, int]        # e.g., (2010, 2025)

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not self.required_loaders:
            raise ValueError("required_loaders cannot be empty")
        if self.year_range[0] > self.year_range[1]:
            raise ValueError("year_range start must be <= end")
```

**Validation Rules**:
- `required_loaders` must not be empty
- `year_range` start must be <= end
- `county_fips` are 5-digit strings (2 state + 3 county)

**Relationships**:
- Used by `run_scenario_preflight()` to determine which loaders to check
- Maps to `LoaderConfig` temporal/geographic parameters

### VerificationProtocol (new)

Protocol for loaders that can verify their source file requirements.

```python
class VerificationProtocol(Protocol):
    """Protocol for loaders with source file verification capability."""

    def check_source_files(
        self,
        data_dir: Path,
        online: bool = False,
    ) -> list[PreflightCheck]:
        """Verify required source files exist and are valid.

        Args:
            data_dir: Base data directory (e.g., Path("data/")).
            online: If True, validate network endpoints.

        Returns:
            List of PreflightCheck results.
        """
        ...
```

**Implementers**:
- `CensusLoader` - checks CBSA file, API key
- `LodesCrosswalkLoader` - checks `us_xwalk.csv[.gz]`
- `TIGERCountyLoader` - checks shapefile presence

## Entity Relationships

```
┌─────────────────────┐
│ ScenarioDataConfig  │
├─────────────────────┤
│ name                │
│ required_loaders    │──────┐
│ county_fips         │      │
│ year_range          │      │
└─────────────────────┘      │
                             │ references
                             ▼
┌─────────────────────┐   ┌─────────────────────────┐
│ run_scenario_       │   │ VERIFICATION_LOADERS    │
│ preflight()         │──▶│ (whitelist registry)    │
└─────────────────────┘   └─────────────────────────┘
                                      │
                                      │ instantiates
                                      ▼
                          ┌───────────────────────┐
                          │ VerificationProtocol  │
                          │ .check_source_files() │
                          └───────────────────────┘
                                      │
                                      │ returns
                                      ▼
                          ┌─────────────────────┐
                          │ list[PreflightCheck]│
                          └─────────────────────┘
                                      │
                                      │ aggregates to
                                      ▼
                          ┌─────────────────────┐
                          │ PreflightResult     │
                          └─────────────────────┘
```

## State Transitions

Preflight is stateless. No persistent state changes occur during preflight checks.

**Exit Conditions**:
- `PreflightResult.ok == True` → Simulation may proceed
- `PreflightResult.ok == False` → Simulation blocked, report printed

## Predefined Scenarios

```python
SCENARIOS: dict[str, ScenarioDataConfig] = {
    "detroit": ScenarioDataConfig(
        name="detroit",
        required_loaders=["qcew", "lodes", "census", "tiger"],
        county_fips=["26163", "26125", "26099"],  # Wayne, Oakland, Macomb
        year_range=(2010, 2025),
    ),
}
```

Additional scenarios can be added as the simulation expands to other metropolitan areas.
