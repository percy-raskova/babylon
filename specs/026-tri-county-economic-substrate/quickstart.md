# Quickstart: 026-tri-county-economic-substrate

**Branch**: `026-tri-county-economic-substrate`
**Prerequisites**: Features 021, 023, 024, 025, 014 implemented; TIGER shapefiles downloaded; QCEW/Census/LODES data loaded into SQLite.

## Setup

```bash
# Ensure dependencies are installed
poetry install

# Ensure on correct branch
git checkout 026-tri-county-economic-substrate

# Verify TIGER shapefiles exist
ls data/tiger/county/tl_2024_us_county.shp

# Verify SQLite database has prerequisite data
poetry run python -c "
from babylon.data.reference.schema import NormalizedBase
from sqlalchemy import create_engine, text
engine = create_engine('sqlite:///data/sqlite/marxist-data-3NF.sqlite')
with engine.connect() as conn:
    counties = conn.execute(text(
        \"SELECT COUNT(*) FROM dim_county WHERE state_fips='26'\"
    )).scalar()
    print(f'Michigan counties in DB: {counties}')
"
```

## Run Tests

```bash
# Unit tests for substrate module
poetry run pytest tests/unit/economics/substrate/ -v

# Integration test (requires loaded data)
poetry run pytest tests/integration/economics/test_substrate_pipeline.py -v

# Full check (lint + typecheck + unit tests)
mise run check
```

## Key Entry Points

| Task | Module | Function/Class |
|------|--------|----------------|
| Generate hex mesh | `substrate.spatial` | `generate_tri_county_mesh(config)` |
| Hydrate with QCEW | `substrate.hydrator` | `hydrate_hex_grid(grid, session)` |
| Volume I production | `substrate.production` | `compute_production(grid)` |
| Volume II circulation | `substrate.circulation` | `circulate_wages(grid, od_matrix)` |
| Volume III equalization | `substrate.equalization` | `equalize_capital(grid, config)` |
| Check conservation | `substrate.conservation` | `check_conservation(pre, post, label)` |
| Aggregate r7→r5 | `substrate.aggregation` | `aggregate_to_resolution(grid, target_res)` |

## Verify Conservation

After any operation, verify value is conserved:

```python
from babylon.economics.substrate.conservation import check_conservation

pre_total = sum(h.constant_capital + h.variable_capital + h.surplus_value
                for h in grid.hexes.values())
# ... run operation ...
post_total = sum(h.constant_capital + h.variable_capital + h.surplus_value
                 for h in new_grid.hexes.values())
check_conservation(pre_total, post_total, "Volume I Production")
# Logs warning if abs(diff) >= 1e-10
```
