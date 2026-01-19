# DimensionLoader Pattern

This module provides a reusable `DimensionLoader[T]` class for idempotent dimension table loading with 3-tier caching.

## Overview

The DimensionLoader implements the get-or-create pattern used across all data loaders to manage dimension tables:

1. **In-memory cache check** (fastest)
1. **Database query** for existing record
1. **Create new record** if not found

This enables idempotent, resumable multi-year data loading without duplicate key violations.

## Usage

### Basic Example

```python
from babylon.data.loaders.dimension_loader import DimensionLoader
from babylon.data.normalize.schema import DimGender

# Create loader for a dimension table
loader = DimensionLoader(session, DimGender, "gender_code")

# Optionally pre-populate cache from existing database records
loader.initialize_from_db()

# Get or create records (idempotent)
gender_id = loader.get_or_create(gender_code="male", gender_label="Male")
```

### With Derived Fields

When dimension records have fields that must be computed from input:

```python
from babylon.data.loaders.dimension_loader import DimensionLoader
from babylon.data.normalize.schema import DimOwnership

loader = DimensionLoader(session, DimOwnership, "own_code")
loader.initialize_from_db()

def get_or_create_ownership(own_code: str, own_title: str) -> int:
    # Compute derived fields
    is_government = own_code in ("1", "2", "3", "4")
    is_private = own_code == "5"

    return loader.get_or_create(
        own_code=own_code,
        own_title=own_title,
        is_government=is_government,
        is_private=is_private,
    )
```

### With Post-Creation Updates

When existing records need flag updates (e.g., marking `has_qcew_data=True`):

```python
def get_or_create_industry(session, naics_code: str, industry_title: str) -> int:
    # Check if exists first
    existing_id = industry_loader.get(naics_code)
    if existing_id is not None:
        # Update flag on existing record
        existing = session.get(DimIndustry, existing_id)
        if existing and not existing.has_qcew_data:
            existing.has_qcew_data = True
        return existing_id

    # Create new with derived fields
    return industry_loader.get_or_create(
        naics_code=naics_code,
        industry_title=industry_title,
        has_qcew_data=True,
        # ... other fields
    )
```

## API Reference

### Constructor

```python
DimensionLoader[T](
    session: Session,      # SQLAlchemy session
    model_class: type[T],  # Dimension model class (e.g., DimGender)
    key_column: str,       # Unique key column name (e.g., "gender_code")
    cache: dict | None,    # Optional pre-populated cache
)
```

### Methods

| Method                               | Description                                                |
| ------------------------------------ | ---------------------------------------------------------- |
| `initialize_from_db() -> int`        | Pre-populate cache from database. Returns record count.    |
| `get_or_create(**kwargs) -> int`     | Get existing or create new record. Returns primary key ID. |
| `get(key_value: str) -> int \| None` | Lookup only, no creation. Returns ID or None.              |
| `cache` property                     | Access the key→ID mapping dictionary.                      |
| `len(loader)`                        | Number of records in cache.                                |
| `key in loader`                      | Check if key is in cache.                                  |

## Integration Pattern

When integrating into a loader class:

```python
class MyLoader(DataLoader):
    def _initialize_lookups(self, session: Session) -> dict[str, Any]:
        # Create DimensionLoaders
        my_dim_loader = DimensionLoader(session, DimMyDimension, "code")
        my_dim_loader.initialize_from_db()

        return {
            "my_dim_loader": my_dim_loader,
            # ... other lookups
        }

    def _process_row(self, row, lookups):
        dim_id = self._get_or_create_my_dim(
            row["code"],
            row["name"],
            lookups["my_dim_loader"],
        )
        # ... build fact row
```

## Migration Checklist

When migrating an existing `_get_or_create_*` method:

1. Add `DimensionLoader` import
1. Create loader instance in `_initialize_lookups()`
1. Call `loader.initialize_from_db()` after creation
1. Update method signature to accept loader instead of dict
1. Replace manual cache/query/create logic with `loader.get_or_create()`
1. Keep derived field computation in wrapper method
1. Update callers to pass loader from lookups
1. Update stats recording to use `len(loader)`

## Completed Migrations

- [x] Census loader (11 dimension methods) - Phase 1
- [x] Employment Industry loader (3 dimension methods) - Phase 3
- [ ] QCEW loader (3 dimension methods) - Pending
- [ ] Materials loader (2 dimension methods) - Pending

## Testing

Unit tests are in `tests/unit/data/loaders/test_dimension_loader.py`:

```bash
mise run test:unit -- tests/unit/data/loaders/test_dimension_loader.py -v
```
