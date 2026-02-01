# Implementation Plan: Data Preflight & Loader Unification

**Branch**: `009-data-preflight` | **Date**: 2026-01-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/009-data-preflight/spec.md`

## Summary

Expand the preflight system to validate all data sources required for the Detroit scenario (QCEW, LODES, ACS, TIGER) before simulation starts. Introduce a `VerificationProtocol` that loaders implement to declare their source file requirements, enabling unified preflight checks. Integrate preflight into the simulation entry point to prevent mid-run crashes due to missing data.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: Pydantic 2.x (validation), SQLAlchemy 2.x (ORM), typer (CLI), tqdm (progress)
**Storage**: SQLite (marxist-data-3NF.sqlite for reference data)
**Testing**: pytest with existing markers (unit, integration)
**Target Platform**: Linux/macOS (CLI simulation engine)
**Project Type**: Single project (monorepo with src/babylon layout)
**Performance Goals**: Preflight completes in <5 seconds (SC-001)
**Constraints**: No network calls in offline mode; Git LFS pointer detection required
**Scale/Scope**: 3 loaders to update (CensusLoader, LodesCrosswalkLoader, TIGERCountyLoader)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| III.4 Data Source Traceability | PASS | All data sources (QCEW, LODES, ACS, TIGER) are federal sources on approved list |
| V.2 Zoom Where Data Exists | PASS | Detroit scenario validates data availability before simulation |
| II.6 State is Data, Engine is Transformation | PASS | Preflight checks are stateless validation; no simulation state mutation |
| I.8 Tragedy of Inevitability | N/A | Infrastructure feature, not simulation mechanics |
| VI.1 UI Observes, Never Controls | N/A | CLI preflight output is informational, not UI |

**Gate Status**: PASS - No violations. Feature is infrastructure that ensures data traceability.

## Project Structure

### Documentation (this feature)

```text
specs/009-data-preflight/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (protocol definitions)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/babylon/
├── data/
│   ├── preflight.py                 # MODIFY: Add VerificationProtocol, expand checks
│   ├── loader_base.py               # MODIFY: Add VerificationProtocol ABC
│   ├── census/
│   │   └── loader_3nf.py            # MODIFY: Implement VerificationProtocol
│   ├── lodes/
│   │   └── loader_3nf.py            # MODIFY: Implement VerificationProtocol
│   └── tiger/
│       └── loader.py                # MODIFY: Implement VerificationProtocol
├── __main__.py                      # MODIFY: Add preflight call before simulation

tests/
├── unit/
│   └── data/
│       └── test_preflight.py        # MODIFY: Add tests for new protocol
└── integration/
    └── data/
        └── test_preflight_detroit.py # NEW: Detroit scenario validation tests
```

**Structure Decision**: Single project structure. All changes are within existing `src/babylon/data/` and simulation entry point. No new packages required.

## Complexity Tracking

> **No violations requiring justification.** Feature uses existing patterns.

## Phase 0: Research

### Research Tasks

1. **Existing preflight patterns**: Understand current `run_preflight()` dispatch mechanism
2. **Loader ABC contract**: Review `DataLoader` abstract methods to identify extension point
3. **Detroit data requirements**: Identify specific files for Wayne/Oakland/Macomb counties

### Findings (inline)

**Existing Preflight Pattern**:
- `run_preflight()` in `preflight.py` dispatches to `_check_*` functions based on loader names
- Uses `AddCheckFn` callback pattern for accumulating checks
- Already has Git LFS detection for CBSA file (`_is_lfs_pointer`)

**Loader ABC Contract**:
- `DataLoader` ABC requires: `load()`, `get_dimension_tables()`, `get_fact_tables()`
- No current verification method - this is the extension point
- Loaders already have access to `LoaderConfig` for temporal/geographic scope

**Detroit Data Requirements**:
- QCEW: Existing `_check_qcew()` covers this
- LODES: `data/lodes/us_xwalk.csv` or `.gz` - need county filtering for Detroit
- TIGER: `data/tiger/county/tl_2024_us_county.shp` - shapefile presence check
- ACS: API-based, existing `_check_census()` covers this

## Phase 1: Design

### VerificationProtocol Interface

```python
from typing import Protocol
from babylon.data.preflight import PreflightCheck

class VerificationProtocol(Protocol):
    """Protocol for loaders that can verify their source file requirements."""

    def check_source_files(
        self,
        data_dir: Path,
        online: bool = False,
    ) -> list[PreflightCheck]:
        """Check if required source files exist.

        Args:
            data_dir: Base data directory (e.g., data/).
            online: If True, validate network endpoints.

        Returns:
            List of PreflightCheck results.
        """
        ...
```

### Loader Registration (Explicit Whitelist)

Per clarification, loaders are registered explicitly in `preflight.py`:

```python
VERIFICATION_LOADERS: dict[str, type[VerificationProtocol]] = {
    "census": CensusLoader,
    "lodes": LodesCrosswalkLoader,
    "tiger": TIGERCountyLoader,
}
```

### Detroit Scenario Configuration

```python
@dataclass
class ScenarioDataConfig:
    """Configuration for scenario-specific data requirements."""

    name: str
    required_loaders: list[str]
    county_fips: list[str]
    year_range: tuple[int, int]

DETROIT_CONFIG = ScenarioDataConfig(
    name="detroit",
    required_loaders=["qcew", "lodes", "census", "tiger"],
    county_fips=["26163", "26125", "26099"],  # Wayne, Oakland, Macomb
    year_range=(2010, 2025),
)
```

### Entry Point Integration

Modify `src/babylon/__main__.py`:

```python
def main() -> None:
    """Run simulation with preflight validation."""
    # NEW: Run preflight before simulation
    from babylon.data.preflight import run_scenario_preflight

    result = run_scenario_preflight("detroit")
    if not result.ok:
        _print_preflight_report(result)
        sys.exit(1)

    # Existing simulation code...
```

### Data Model

See [data-model.md](./data-model.md) for entity definitions.

### API Contracts

See [contracts/](./contracts/) for protocol definitions.

## Implementation Sequence (Summary)

1. **Define VerificationProtocol** in `loader_base.py`
2. **Implement protocol** in CensusLoader, LodesCrosswalkLoader, TIGERCountyLoader
3. **Add scenario config** for Detroit in `preflight.py`
4. **Add `run_scenario_preflight()`** function
5. **Integrate with `__main__.py`** entry point
6. **Add tests** for new protocol and Detroit scenario

---

## Implementation Details Cross-Reference

### Step 1: Define VerificationProtocol

**Goal**: Add a typing.Protocol that loaders can implement to declare source file requirements.

| Aspect | Details |
|--------|---------|
| **Target File** | `src/babylon/data/loader_base.py` |
| **Insert Location** | After line 697 (before `__all__`), or as a separate import from preflight.py |
| **Design Reference** | [contracts/verification_protocol.py](./contracts/verification_protocol.py) - full interface |
| **Decision Rationale** | [research.md §2](./research.md) - why Protocol vs ABC |

**Code to Add**:
```python
from typing import Protocol
from pathlib import Path

class VerificationProtocol(Protocol):
    """Protocol for loaders that can verify their source file requirements."""

    def check_source_files(
        self,
        data_dir: Path,
        online: bool = False,
    ) -> list["PreflightCheck"]:
        """Verify required source files exist and are valid."""
        ...
```

**Verification**:
- `mypy src/babylon/data/loader_base.py` passes
- Protocol is importable: `from babylon.data.loader_base import VerificationProtocol`

---

### Step 2a: Implement Protocol in LodesCrosswalkLoader

**Goal**: Add `check_source_files()` method to verify LODES crosswalk exists.

| Aspect | Details |
|--------|---------|
| **Target File** | `src/babylon/data/lodes/loader_3nf.py` |
| **Insert Location** | After line 103 (after `get_fact_tables()` method) |
| **Existing Pattern** | `_resolve_lodes_path()` at line 27-46 already finds the file |
| **Empty File Check** | [research.md §5](./research.md) - use `Path.stat().st_size > 0` |

**Required Checks** (from [research.md §3](./research.md)):
- File exists: `data/lodes/us_xwalk.csv` or `us_xwalk.csv.gz`
- File not empty: `st_size > 0`
- Not Git LFS pointer (pattern in [research.md §4](./research.md))

**Code to Add**:
```python
def check_source_files(
    self,
    data_dir: Path,
    online: bool = False,
) -> list[PreflightCheck]:
    """Check if LODES crosswalk file exists."""
    from babylon.data.preflight import PreflightCheck

    checks: list[PreflightCheck] = []
    csv_path = _resolve_lodes_path(data_dir / "lodes")

    if csv_path is None:
        checks.append(PreflightCheck(
            check_id="lodes:crosswalk",
            status="fail",
            message=f"Missing LODES crosswalk in {data_dir / 'lodes'}",
            hint="Download us_xwalk.csv from https://lehd.ces.census.gov/data/lodes/",
        ))
    elif csv_path.stat().st_size == 0:
        checks.append(PreflightCheck(
            check_id="lodes:crosswalk",
            status="fail",
            message=f"LODES crosswalk is empty: {csv_path}",
            hint="Re-download the file - it may be corrupted",
        ))
    else:
        checks.append(PreflightCheck(
            check_id="lodes:crosswalk",
            status="ok",
            message=f"Found {csv_path}",
        ))

    return checks
```

**Verification**:
- Unit test with missing file returns `status="fail"`
- Unit test with empty file returns `status="fail"`
- Unit test with valid file returns `status="ok"`

---

### Step 2b: Implement Protocol in TIGERCountyLoader

**Goal**: Add `check_source_files()` method to verify TIGER shapefile exists.

| Aspect | Details |
|--------|---------|
| **Target File** | `src/babylon/data/tiger/loader.py` |
| **Insert Location** | After line 146 (after `get_fact_tables()` method) |
| **Shapefile Path** | `TIGER_COUNTY_SHAPEFILE` constant at line 36 |
| **Year in Filename** | `tl_2024_us_county.shp` - hardcoded for now |

**Required Checks**:
- Shapefile exists: `data/tiger/county/tl_2024_us_county.shp`
- File not empty: `st_size > 0`

**Code to Add**:
```python
def check_source_files(
    self,
    data_dir: Path,
    online: bool = False,
) -> list[PreflightCheck]:
    """Check if TIGER county shapefile exists."""
    from babylon.data.preflight import PreflightCheck

    checks: list[PreflightCheck] = []
    shapefile_path = data_dir / TIGER_COUNTY_SHAPEFILE

    if not shapefile_path.exists():
        checks.append(PreflightCheck(
            check_id="tiger:county_shapefile",
            status="fail",
            message=f"Missing TIGER shapefile: {shapefile_path}",
            hint="Download from https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html",
        ))
    elif shapefile_path.stat().st_size == 0:
        checks.append(PreflightCheck(
            check_id="tiger:county_shapefile",
            status="fail",
            message=f"TIGER shapefile is empty: {shapefile_path}",
            hint="Re-download the shapefile",
        ))
    else:
        checks.append(PreflightCheck(
            check_id="tiger:county_shapefile",
            status="ok",
            message=f"Found {shapefile_path}",
        ))

    return checks
```

**Verification**:
- Unit test with missing shapefile returns `status="fail"`
- Unit test with valid shapefile returns `status="ok"`

---

### Step 2c: Implement Protocol in CensusLoader

**Goal**: Add `check_source_files()` method to verify CBSA file and API key.

| Aspect | Details |
|--------|---------|
| **Target File** | `src/babylon/data/census/loader_3nf.py` |
| **Insert Location** | Add method to `CensusLoader` class |
| **Existing Check** | `_check_census()` in preflight.py:164-204 has the logic |
| **Git LFS Check** | Use `cbsa_parser._is_lfs_pointer()` pattern |

**Required Checks** (from existing `_check_census()`):
- CBSA file exists: `data/census/cbsa_delineation_2023.xlsx`
- Not Git LFS pointer
- CENSUS_API_KEY environment variable (warn if missing, not fail)

**Code to Add**:
```python
def check_source_files(
    self,
    data_dir: Path,
    online: bool = False,
) -> list[PreflightCheck]:
    """Check Census loader prerequisites."""
    import os
    from babylon.data.preflight import PreflightCheck
    from babylon.data.census import cbsa_parser

    checks: list[PreflightCheck] = []
    cbsa_path = data_dir / "census" / "cbsa_delineation_2023.xlsx"

    if not cbsa_path.exists():
        checks.append(PreflightCheck(
            check_id="census:cbsa_file",
            status="fail",
            message=f"Missing CBSA delineation file: {cbsa_path}",
            hint="Download from Census Bureau delineation page",
        ))
    elif cbsa_parser._is_lfs_pointer(cbsa_path):
        checks.append(PreflightCheck(
            check_id="census:cbsa_file",
            status="fail",
            message=f"CBSA file is Git LFS pointer: {cbsa_path}",
            hint='Run `git lfs pull --include "data/census/cbsa_delineation_2023.xlsx"`',
        ))
    else:
        checks.append(PreflightCheck(
            check_id="census:cbsa_file",
            status="ok",
            message=f"Found {cbsa_path}",
        ))

    # API key is optional but recommended
    if not os.getenv("CENSUS_API_KEY"):
        checks.append(PreflightCheck(
            check_id="census:api_key",
            status="warn",
            message="CENSUS_API_KEY is not set",
            hint="Optional but recommended for higher rate limits",
        ))

    return checks
```

**Verification**:
- Unit test with missing CBSA file returns `status="fail"`
- Unit test with Git LFS pointer returns `status="fail"` with lfs pull hint
- Unit test without API key returns `status="warn"`

---

### Step 3: Add ScenarioDataConfig and Detroit Configuration

**Goal**: Define scenario configuration and register loaders.

| Aspect | Details |
|--------|---------|
| **Target File** | `src/babylon/data/preflight.py` |
| **Insert Location** | After line 71 (after `AddCheckFn` type alias) |
| **Data Model** | [data-model.md](./data-model.md) - ScenarioDataConfig definition |
| **Detroit FIPS** | Wayne=26163, Oakland=26125, Macomb=26099 |

**Code to Add**:
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ScenarioDataConfig:
    """Configuration for scenario-specific data requirements."""

    name: str
    required_loaders: list[str]
    county_fips: list[str]
    year_range: tuple[int, int]

    def __post_init__(self) -> None:
        if not self.required_loaders:
            raise ValueError("required_loaders cannot be empty")
        if self.year_range[0] > self.year_range[1]:
            raise ValueError("year_range start must be <= end")


# Loader registry (explicit whitelist per clarification)
VERIFICATION_LOADERS: dict[str, type] = {
    "census": None,  # Will import CensusLoader
    "lodes": None,   # Will import LodesCrosswalkLoader
    "tiger": None,   # Will import TIGERCountyLoader
}

# Predefined scenarios
SCENARIOS: dict[str, ScenarioDataConfig] = {
    "detroit": ScenarioDataConfig(
        name="detroit",
        required_loaders=["qcew", "lodes", "census", "tiger"],
        county_fips=["26163", "26125", "26099"],
        year_range=(2010, 2025),
    ),
}
```

**Note**: Lazy imports for loaders to avoid circular dependencies.

**Verification**:
- `ScenarioDataConfig("detroit", [], [], (2010, 2025))` raises ValueError
- `SCENARIOS["detroit"].county_fips` returns the 3 Detroit counties

---

### Step 4: Add run_scenario_preflight() Function

**Goal**: Create function that validates all data sources for a scenario.

| Aspect | Details |
|--------|---------|
| **Target File** | `src/babylon/data/preflight.py` |
| **Insert Location** | After `run_preflight()` function (after line 477) |
| **Relationship** | Calls existing `run_preflight()` + invokes VerificationProtocol on each loader |

**Code to Add**:
```python
def run_scenario_preflight(
    scenario_name: str,
    base_dir: Path | None = None,
    online: bool = False,
) -> PreflightResult:
    """Run preflight checks for a predefined scenario.

    Args:
        scenario_name: Name of scenario (e.g., "detroit").
        base_dir: Base directory for data files.
        online: If True, validate network endpoints.

    Returns:
        PreflightResult with all check outcomes.

    Raises:
        ValueError: If scenario_name is not recognized.
    """
    if scenario_name not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_name}. Available: {list(SCENARIOS.keys())}")

    scenario = SCENARIOS[scenario_name]
    resolved_base = base_dir or BaseConfig.BASE_DIR
    data_dir = resolved_base / "data"

    checks: list[PreflightCheck] = []

    # Import loaders lazily to avoid circular imports
    from babylon.data.census.loader_3nf import CensusLoader
    from babylon.data.lodes.loader_3nf import LodesCrosswalkLoader
    from babylon.data.tiger.loader import TIGERCountyLoader

    loader_classes = {
        "census": CensusLoader,
        "lodes": LodesCrosswalkLoader,
        "tiger": TIGERCountyLoader,
    }

    for loader_name in scenario.required_loaders:
        if loader_name in loader_classes:
            loader = loader_classes[loader_name]()
            if hasattr(loader, "check_source_files"):
                checks.extend(loader.check_source_files(data_dir, online=online))

    # Also run existing _check_* functions for loaders not yet migrated
    # (e.g., qcew uses _check_qcew)
    config = LoaderConfig()  # Default config for preflight
    existing_result = run_preflight(config, scenario.required_loaders, base_dir, online)
    checks.extend(existing_result.checks)

    return PreflightResult(checks=checks)
```

**Verification**:
- `run_scenario_preflight("unknown")` raises ValueError
- `run_scenario_preflight("detroit")` returns PreflightResult with checks for all 4 data sources

---

### Step 5: Integrate with __main__.py Entry Point

**Goal**: Run preflight before simulation starts; exit on failure.

| Aspect | Details |
|--------|---------|
| **Target File** | `src/babylon/__main__.py` |
| **Insert Location** | At start of `main()` function (after line 32) |
| **Exit Code** | `sys.exit(1)` on preflight failure (FR-010) |
| **Spec Reference** | [spec.md FR-005](./spec.md) - entry point integration |

**Code to Add** (insert at line 33):
```python
def _print_preflight_report(result: PreflightResult) -> None:
    """Print human-readable preflight failure report."""
    print("\n❌ PREFLIGHT FAILED\n")
    print("Missing Data:")
    for check in result.failures:
        print(f"  - {check.check_id}: {check.message}")
        if check.hint:
            print(f"    Hint: {check.hint}")
    if result.warnings:
        print("\nWarnings:")
        for check in result.warnings:
            print(f"  - {check.check_id}: {check.message}")


def main() -> None:
    """Run simulation with preflight validation."""
    # NEW: Run preflight before simulation
    from babylon.data.preflight import run_scenario_preflight

    result = run_scenario_preflight("detroit")
    if not result.ok:
        _print_preflight_report(result)
        sys.exit(1)

    # ... existing simulation code continues ...
```

**Verification**:
- With missing data: simulation exits with code 1 and prints report
- With all data present: simulation starts normally

---

### Step 6: Add Tests

**Goal**: Test new protocol and Detroit scenario validation.

| Test File | Purpose | Spec Reference |
|-----------|---------|----------------|
| `tests/unit/data/test_preflight.py` | Unit tests for VerificationProtocol | [spec.md SC-003](./spec.md) |
| `tests/integration/data/test_preflight_detroit.py` | Detroit scenario integration | [spec.md SC-002](./spec.md) |

**Unit Test Cases** (from [spec.md Acceptance Scenarios](./spec.md)):

```python
# tests/unit/data/test_preflight.py

def test_lodes_loader_missing_file():
    """Story 1, Scenario 1: Missing LODES reports failure with hint."""
    loader = LodesCrosswalkLoader()
    checks = loader.check_source_files(Path("/nonexistent"))
    assert checks[0].status == "fail"
    assert "lehd.ces.census.gov" in checks[0].hint

def test_tiger_loader_empty_file(tmp_path):
    """Edge case: Empty file treated as failure."""
    shapefile = tmp_path / "tiger/county/tl_2024_us_county.shp"
    shapefile.parent.mkdir(parents=True)
    shapefile.touch()  # Empty file
    loader = TIGERCountyLoader(data_dir=tmp_path)
    checks = loader.check_source_files(tmp_path)
    assert checks[0].status == "fail"
    assert "empty" in checks[0].message.lower()

def test_census_loader_lfs_pointer(tmp_path):
    """Edge case: Git LFS pointer detected."""
    cbsa = tmp_path / "census/cbsa_delineation_2023.xlsx"
    cbsa.parent.mkdir(parents=True)
    cbsa.write_bytes(b"version https://git-lfs.github.com/spec/v1\n...")
    loader = CensusLoader()
    checks = loader.check_source_files(tmp_path)
    lfs_check = next(c for c in checks if "lfs" in c.message.lower())
    assert lfs_check.status == "fail"
    assert "git lfs pull" in lfs_check.hint

def test_scenario_preflight_detroit_all_present(detroit_data_fixture):
    """Story 3: Detroit scenario with all data passes."""
    result = run_scenario_preflight("detroit", base_dir=detroit_data_fixture)
    assert result.ok
```

**Integration Test Cases**:

```python
# tests/integration/data/test_preflight_detroit.py

def test_detroit_preflight_validates_all_four_sources():
    """SC-002: Preflight checks QCEW, LODES, ACS, TIGER."""
    result = run_scenario_preflight("detroit")
    check_ids = {c.check_id.split(":")[0] for c in result.checks}
    assert {"qcew", "lodes", "census", "tiger"} <= check_ids

def test_detroit_partial_data_reports_mixed_results(tmp_path):
    """Story 3, Scenario 3: Partial data shows success + failure."""
    # Set up only QCEW data
    (tmp_path / "data/qcew").mkdir(parents=True)
    (tmp_path / "data/qcew/test.csv").touch()
    result = run_scenario_preflight("detroit", base_dir=tmp_path)
    assert not result.ok
    assert len(result.failures) > 0
```

**Verification**:
- `pytest tests/unit/data/test_preflight.py -v` passes
- `pytest tests/integration/data/test_preflight_detroit.py -v` passes
- Existing tests still pass: `pytest tests/unit/data/ -v` (SC-006)

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Breaking existing preflight tests | Run `test_preflight.py` after each change |
| False positives (files exist but wrong format) | Add file size > 0 check; leave format validation for loader |
| Git LFS detection edge cases | Reuse existing `_is_lfs_pointer()` pattern |
| Performance overhead | Preflight is I/O bound on file existence checks; <5s is achievable |

## Exit Criteria

- [ ] VerificationProtocol defined and documented
- [ ] 3 loaders implement protocol (Census, LODES, TIGER)
- [ ] Detroit scenario preflight validates all 4 data sources
- [ ] Entry point integration blocks simulation on preflight failure
- [ ] All existing tests pass (SC-006)
- [ ] New integration tests for Detroit scenario
