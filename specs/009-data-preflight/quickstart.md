# Quickstart: Data Preflight & Loader Unification

**Branch**: `009-data-preflight` | **Date**: 2026-01-31

## Overview

This feature adds preflight validation for simulation data sources. When you run the simulation, it checks that all required data files exist before starting.

## For Users

### Running with Preflight

Preflight runs automatically when starting the simulation:

```bash
# Run simulation (preflight checks automatically)
python -m babylon

# If data is missing, you'll see:
# ❌ PREFLIGHT FAILED
#
# Missing Data:
#   - LODES: Missing data/lodes/us_xwalk.csv
#     Hint: Download from https://lehd.ces.census.gov/data/lodes/
#   - TIGER: Missing data/tiger/county/tl_2024_us_county.shp
#     Hint: Download from Census Bureau TIGER/Line
```

### Running Preflight Only

```bash
# Check data availability without starting simulation
python -m babylon.data.cli preflight --loaders census,lodes,tiger

# With online validation (checks API endpoints)
python -m babylon.data.cli preflight --online
```

### Data File Locations

| Data Source | Location | Source |
|-------------|----------|--------|
| LODES | `data/lodes/us_xwalk.csv` | [LEHD LODES](https://lehd.ces.census.gov/data/lodes/) |
| TIGER | `data/tiger/county/tl_2024_us_county.shp` | [Census TIGER/Line](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html) |
| QCEW | `data/qcew/*.csv` | [BLS QCEW](https://www.bls.gov/cew/downloadable-data-files.htm) |
| Census | API-based | Requires `CENSUS_API_KEY` env var |

## For Developers

### Implementing VerificationProtocol

To add preflight support to a new loader:

```python
from pathlib import Path
from babylon.data.loader_base import DataLoader
from babylon.data.preflight import PreflightCheck

class MyLoader(DataLoader):
    """Example loader with preflight support."""

    def check_source_files(
        self,
        data_dir: Path,
        online: bool = False,
    ) -> list[PreflightCheck]:
        """Check if required data files exist."""
        checks = []

        # Check for required file
        data_file = data_dir / "mydata" / "required.csv"
        if not data_file.exists():
            checks.append(PreflightCheck(
                check_id="myloader:required_file",
                status="fail",
                message=f"Missing {data_file}",
                hint="Download from https://example.com/data",
            ))
        elif data_file.stat().st_size == 0:
            checks.append(PreflightCheck(
                check_id="myloader:required_file",
                status="fail",
                message=f"File is empty: {data_file}",
                hint="Re-download the file",
            ))
        else:
            checks.append(PreflightCheck(
                check_id="myloader:required_file",
                status="ok",
                message=f"Found {data_file}",
            ))

        return checks
```

### Registering with Preflight

Add your loader to the whitelist in `preflight.py`:

```python
VERIFICATION_LOADERS: dict[str, type[VerificationProtocol]] = {
    "census": CensusLoader,
    "lodes": LodesCrosswalkLoader,
    "tiger": TIGERCountyLoader,
    "myloader": MyLoader,  # Add new loader here
}
```

### Testing

```bash
# Run existing preflight tests
pytest tests/unit/data/test_preflight.py -v

# Run Detroit scenario integration tests
pytest tests/integration/data/test_preflight_detroit.py -v
```

## Common Issues

### Git LFS Files Not Pulled

```
❌ PREFLIGHT FAILED
  - Census: CBSA file is Git LFS pointer
    Hint: Run `git lfs pull --include "data/census/cbsa_delineation_2023.xlsx"`
```

**Fix**: Run the suggested `git lfs pull` command.

### Missing API Keys

```
⚠️ PREFLIGHT WARNING
  - Census: CENSUS_API_KEY is not set
    Hint: Optional but recommended for higher rate limits
```

**Fix**: Set the environment variable or proceed with warnings.

### Empty Data Files

```
❌ PREFLIGHT FAILED
  - LODES: File exists but is empty: data/lodes/us_xwalk.csv
    Hint: Re-download the file
```

**Fix**: Delete and re-download the corrupted file.
