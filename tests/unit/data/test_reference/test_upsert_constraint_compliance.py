"""Test that all ON CONFLICT clauses have matching UniqueConstraints.

SQLite requires UniqueConstraint (not unique Index) for ON CONFLICT clauses.
This test introspects schema models and greps loaders to ensure compliance.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import Index, UniqueConstraint

# Import all schema modules to ensure models are registered
from babylon.data.reference import schema  # noqa: F401

if TYPE_CHECKING:
    from collections.abc import Iterator


def get_unique_constraint_columns(model: type) -> set[frozenset[str]]:
    """Extract column sets from UniqueConstraints in a model's __table_args__."""
    constraints: set[frozenset[str]] = set()
    table_args = getattr(model, "__table_args__", ())

    if isinstance(table_args, tuple):
        for arg in table_args:
            if isinstance(arg, UniqueConstraint):
                cols = frozenset(arg.columns.keys()) if hasattr(arg, "columns") else frozenset()
                if not cols:
                    # Try _pending_colargs for pre-table-bind state
                    col_names: list[str] = []
                    for c in arg._pending_colargs:
                        if isinstance(c, str):
                            col_names.append(c)
                        elif c is not None and hasattr(c, "name") and c.name is not None:
                            col_names.append(c.name)
                    cols = frozenset(col_names)
                constraints.add(cols)
    return constraints


def get_unique_index_columns(model: type) -> set[frozenset[str]]:
    """Extract column sets from unique Indexes in a model's __table_args__."""
    indexes: set[frozenset[str]] = set()
    table_args = getattr(model, "__table_args__", ())

    if isinstance(table_args, tuple):
        for arg in table_args:
            if isinstance(arg, Index) and arg.unique:
                cols = frozenset(c if isinstance(c, str) else c.name for c in arg.expressions)
                indexes.add(cols)
    return indexes


def find_on_conflict_columns(loader_path: Path) -> Iterator[tuple[str, frozenset[str]]]:
    """Parse loader file and yield (table_name, columns) for ON CONFLICT clauses."""
    content = loader_path.read_text()

    # Pattern: on_conflict_do_update(index_elements=["col1", "col2", ...])
    pattern = r"on_conflict_do_update\s*\(\s*index_elements\s*=\s*\[([^\]]+)\]"

    for match in re.finditer(pattern, content):
        cols_str = match.group(1)
        cols = frozenset(c.strip().strip("\"'") for c in cols_str.split(","))
        yield loader_path.name, cols


def get_all_schema_models() -> list[type]:
    """Get all SQLAlchemy models from schema module via __all__ or introspection.

    Note:
        Uses DeclarativeBase instead of NormalizedBase for detection because
        importlib.reload() in test_database_config.py creates a new NormalizedBase
        class, breaking issubclass() checks for models that inherited from the
        original NormalizedBase. DeclarativeBase (from SQLAlchemy) is never reloaded.
    """
    from sqlalchemy.orm import DeclarativeBase

    models: list[type] = []
    for name in dir(schema):
        obj = getattr(schema, name)
        if (
            isinstance(obj, type)
            and hasattr(obj, "__tablename__")
            and issubclass(obj, DeclarativeBase)
            and obj.__module__ == "babylon.data.reference.schema"
        ):
            models.append(obj)
    return models


class TestUpsertConstraintCompliance:
    """Verify ON CONFLICT clauses have matching UniqueConstraints."""

    def test_no_unique_index_with_on_conflict(self) -> None:
        """All ON CONFLICT columns must have UniqueConstraint, not just unique Index."""
        loader_dir = Path("src/babylon/data")
        violations: list[str] = []

        # Build lookup: column_set -> model name
        models = get_all_schema_models()
        unique_constraints: dict[frozenset[str], str] = {}
        unique_indexes: dict[frozenset[str], str] = {}

        for model in models:
            model_name = model.__name__
            for cols in get_unique_constraint_columns(model):
                unique_constraints[cols] = model_name
            for cols in get_unique_index_columns(model):
                unique_indexes[cols] = model_name

        # Check each loader's ON CONFLICT clauses
        for loader_path in loader_dir.rglob("*loader*.py"):
            for file_name, cols in find_on_conflict_columns(loader_path):
                if cols in unique_indexes and cols not in unique_constraints:
                    model_name = unique_indexes[cols]
                    violations.append(
                        f"{file_name}: ON CONFLICT {set(cols)} targets {model_name} "
                        f"which has unique Index but NOT UniqueConstraint"
                    )

        assert not violations, (
            "ON CONFLICT requires UniqueConstraint, not just unique Index:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_all_on_conflict_have_matching_constraint(self) -> None:
        """Every ON CONFLICT must have a corresponding UniqueConstraint."""
        loader_dir = Path("src/babylon/data")
        models = get_all_schema_models()

        # Collect all UniqueConstraint column sets
        all_constraints: set[frozenset[str]] = set()
        for model in models:
            all_constraints.update(get_unique_constraint_columns(model))

        # Check each loader
        missing: list[str] = []
        for loader_path in loader_dir.rglob("*loader*.py"):
            for file_name, cols in find_on_conflict_columns(loader_path):
                if cols not in all_constraints:
                    missing.append(
                        f"{file_name}: ON CONFLICT {set(cols)} has no matching UniqueConstraint"
                    )

        assert not missing, "ON CONFLICT clauses without matching UniqueConstraint:\n" + "\n".join(
            f"  - {m}" for m in missing
        )


class TestSpecificModelConstraints:
    """Verify specific models that use ON CONFLICT have UniqueConstraints."""

    def test_dim_geographic_hierarchy_has_unique_constraint(self) -> None:
        """DimGeographicHierarchy must have UniqueConstraint for ON CONFLICT."""
        from babylon.data.reference.schema import DimGeographicHierarchy

        expected = frozenset({"state_id", "county_id", "source_year"})
        constraints = get_unique_constraint_columns(DimGeographicHierarchy)

        assert expected in constraints, (
            f"DimGeographicHierarchy must have UniqueConstraint on {set(expected)}, "
            f"found constraints: {[set(c) for c in constraints]}"
        )

    def test_staging_arcgis_feature_has_unique_constraint(self) -> None:
        """StagingArcGISFeature must have UniqueConstraint for ON CONFLICT."""
        from babylon.data.reference.schema import StagingArcGISFeature

        expected = frozenset({"source_code", "object_id"})
        constraints = get_unique_constraint_columns(StagingArcGISFeature)

        assert expected in constraints, (
            f"StagingArcGISFeature must have UniqueConstraint on {set(expected)}, "
            f"found constraints: {[set(c) for c in constraints]}"
        )

    def test_dim_geographic_hierarchy_no_unique_index_on_conflict_columns(self) -> None:
        """DimGeographicHierarchy should NOT have unique Index on conflict columns."""
        from babylon.data.reference.schema import DimGeographicHierarchy

        conflict_cols = frozenset({"state_id", "county_id", "source_year"})
        indexes = get_unique_index_columns(DimGeographicHierarchy)

        assert conflict_cols not in indexes, (
            f"DimGeographicHierarchy should use UniqueConstraint, not Index for {set(conflict_cols)}"
        )

    def test_staging_arcgis_feature_no_unique_index_on_conflict_columns(self) -> None:
        """StagingArcGISFeature should NOT have unique Index on conflict columns."""
        from babylon.data.reference.schema import StagingArcGISFeature

        conflict_cols = frozenset({"source_code", "object_id"})
        indexes = get_unique_index_columns(StagingArcGISFeature)

        assert conflict_cols not in indexes, (
            f"StagingArcGISFeature should use UniqueConstraint, not Index for {set(conflict_cols)}"
        )
