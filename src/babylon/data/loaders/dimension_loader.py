"""Generic dimension loading with get-or-create pattern.

This module provides a reusable DimensionLoader class that implements the
get-or-create pattern with 3-tier caching (in-memory -> database -> create).

This pattern is used across all data loaders to manage dimension tables
idempotently, allowing for resumable and multi-year loading.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import inspect

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class DimensionLoader[T]:
    """Manages get-or-create for a single dimension type with caching.

    Implements a 3-tier lookup strategy:
    1. Check in-memory cache (fastest)
    2. Query database for existing record
    3. Create new record if not found

    This pattern ensures idempotent dimension loading - running the same
    loader multiple times will not create duplicate records.

    Usage:
        loader = DimensionLoader(
            session=session,
            model_class=DimIndustry,
            key_column="naics_code",
        )
        # Optionally pre-populate cache from database
        loader.initialize_from_db()

        # Get or create records
        industry_id = loader.get_or_create(
            naics_code="11",
            naics_title="Agriculture",
            naics_level=2,
        )

    Args:
        session: SQLAlchemy session for database operations.
        model_class: The dimension model class (e.g., DimIndustry).
        key_column: Name of the unique key column (e.g., "naics_code").
        cache: Optional pre-populated cache dict (key -> id).
    """

    def __init__(
        self,
        session: Session,
        model_class: type[T],
        key_column: str,
        cache: dict[str, int] | None = None,
    ) -> None:
        """Initialize the dimension loader."""
        self.session = session
        self.model_class = model_class
        self.key_column = key_column
        self._cache: dict[str, int] = cache if cache is not None else {}
        self._id_column = self._infer_id_column()

    def _infer_id_column(self) -> str:
        """Infer primary key column name from model class using SQLAlchemy introspection.

        Uses the model's mapper to find the actual primary key column name,
        which is more reliable than naming conventions.

        Returns:
            The primary key column name.

        Raises:
            ValueError: If the model has no primary key or multiple primary keys.
        """
        mapper_result = inspect(self.model_class)
        if mapper_result is None:
            msg = f"{self.model_class.__name__} is not a mapped SQLAlchemy class"
            raise ValueError(msg)
        pk_columns = list(mapper_result.primary_key)
        if len(pk_columns) != 1:
            msg = f"{self.model_class.__name__} must have exactly one primary key column"
            raise ValueError(msg)
        return str(pk_columns[0].name)

    def initialize_from_db(self) -> int:
        """Pre-populate cache from existing database records.

        Call this before get_or_create operations to avoid unnecessary
        database queries for records that already exist.

        Returns:
            Number of records loaded into cache.
        """
        key_attr = getattr(self.model_class, self.key_column)
        id_attr = getattr(self.model_class, self._id_column)
        query = self.session.query(key_attr, id_attr)
        results = query.all()
        self._cache = {str(key): int(id_) for key, id_ in results}
        return len(results)

    def get_or_create(self, **kwargs: Any) -> int:
        """Get existing record ID or create new, with caching.

        Args:
            **kwargs: All columns needed to create the record.
                      Must include the key_column.

        Returns:
            The primary key ID of the existing or newly created record.

        Raises:
            KeyError: If key_column is not in kwargs.
        """
        key_value = str(kwargs[self.key_column])

        # 1. Check cache (fastest)
        if key_value in self._cache:
            return self._cache[key_value]

        # 2. Check database
        key_attr = getattr(self.model_class, self.key_column)
        existing = self.session.query(self.model_class).filter(key_attr == key_value).first()
        if existing:
            id_value = int(getattr(existing, self._id_column))
            self._cache[key_value] = id_value
            return id_value

        # 3. Create new record
        record = self.model_class(**kwargs)
        self.session.add(record)
        self.session.flush()
        id_value = int(getattr(record, self._id_column))
        self._cache[key_value] = id_value
        return id_value

    def get(self, key_value: str) -> int | None:
        """Get existing record ID without creating.

        Args:
            key_value: The unique key to look up.

        Returns:
            The primary key ID or None if not found.
        """
        # Check cache first
        if key_value in self._cache:
            return self._cache[key_value]

        # Check database
        key_attr = getattr(self.model_class, self.key_column)
        existing = self.session.query(self.model_class).filter(key_attr == key_value).first()
        if existing:
            id_value = int(getattr(existing, self._id_column))
            self._cache[key_value] = id_value
            return id_value

        return None

    @property
    def cache(self) -> dict[str, int]:
        """Access the lookup cache (key -> id mapping)."""
        return self._cache

    def __len__(self) -> int:
        """Return number of records in cache."""
        return len(self._cache)

    def __contains__(self, key_value: str) -> bool:
        """Check if key is in cache."""
        return key_value in self._cache
