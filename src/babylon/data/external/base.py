"""Base classes and utilities for data ingestion.

Provides a common interface for ingesting external data into SQLite.
All specific data source ingesters should inherit from DataIngester.
"""

from __future__ import annotations

import csv
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    """Result of an ingestion operation.

    Attributes:
        source_file: Path to the source CSV file
        rows_read: Number of rows read from source file
        rows_inserted: Number of rows successfully inserted
        rows_updated: Number of rows updated (for upsert operations)
        rows_skipped: Number of rows skipped (e.g., due to validation errors)
        errors: List of error messages encountered during ingestion
    """

    source_file: str
    rows_read: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Return True if ingestion was successful with no errors."""
        return len(self.errors) == 0 and self.rows_inserted > 0


class DataIngester[ModelT](ABC):
    """Abstract base class for data ingesters.

    Subclasses must implement:
        - parse_row: Convert a CSV row dict to a SQLAlchemy model instance
        - model_class property: Return the SQLAlchemy model class

    Example:
        >>> class CensusIngester(DataIngester[CensusPopulation]):
        ...     @property
        ...     def model_class(self):
        ...         return CensusPopulation
        ...
        ...     def parse_row(self, row):
        ...         return CensusPopulation(state_fips=row['state_fips'], ...)
    """

    @property
    @abstractmethod
    def model_class(self) -> type[ModelT]:
        """Return the SQLAlchemy model class for this ingester."""
        ...

    @abstractmethod
    def parse_row(self, row: dict[str, str]) -> ModelT | None:
        """Parse a CSV row dict into a model instance.

        Args:
            row: Dictionary of column name -> value from CSV

        Returns:
            Model instance, or None if row should be skipped
        """
        ...

    def validate_row(self, row: dict[str, str]) -> list[str]:  # noqa: ARG002
        """Validate a row before parsing.

        Override in subclasses to add custom validation.

        Args:
            row: Dictionary of column name -> value from CSV

        Returns:
            List of validation error messages (empty if valid)
        """
        return []

    def ingest_csv(
        self,
        session: Session,
        csv_path: Path | str,
        *,
        skip_header: bool = True,
        encoding: str = "utf-8",
        delimiter: str = ",",
    ) -> IngestResult:
        """Ingest data from a CSV file into the database.

        Args:
            session: SQLAlchemy session for database operations
            csv_path: Path to the CSV file
            skip_header: Whether to skip the header row (default True)
            encoding: File encoding (default UTF-8)
            delimiter: CSV delimiter (default comma)

        Returns:
            IngestResult with statistics about the operation
        """
        csv_path = Path(csv_path)
        result = IngestResult(source_file=str(csv_path))

        if not csv_path.exists():
            result.errors.append(f"File not found: {csv_path}")
            return result

        try:
            with open(csv_path, encoding=encoding, newline="") as f:
                reader = csv.DictReader(f, delimiter=delimiter)

                for row_num, row in enumerate(reader, start=2 if skip_header else 1):
                    result.rows_read += 1

                    # Validate row
                    errors = self.validate_row(row)
                    if errors:
                        for error in errors:
                            result.errors.append(f"Row {row_num}: {error}")
                        result.rows_skipped += 1
                        continue

                    # Parse row into model
                    try:
                        model = self.parse_row(row)
                        if model is None:
                            result.rows_skipped += 1
                            continue

                        session.add(model)
                        result.rows_inserted += 1

                    except Exception as e:
                        result.errors.append(f"Row {row_num}: {e}")
                        result.rows_skipped += 1
                        continue

            # Commit all changes
            session.commit()
            logger.info(
                f"Ingested {result.rows_inserted} rows from {csv_path.name} "
                f"({result.rows_skipped} skipped)"
            )

        except Exception as e:
            session.rollback()
            result.errors.append(f"Failed to read file: {e}")
            logger.error(f"Failed to ingest {csv_path}: {e}")

        return result

    def ingest_rows(
        self,
        session: Session,
        rows: list[dict[str, str]],
    ) -> IngestResult:
        """Ingest data from a list of row dictionaries.

        Useful for testing or when data comes from an API rather than CSV.

        Args:
            session: SQLAlchemy session for database operations
            rows: List of row dictionaries

        Returns:
            IngestResult with statistics about the operation
        """
        result = IngestResult(source_file="<in-memory>")

        for row_num, row in enumerate(rows, start=1):
            result.rows_read += 1

            # Validate row
            errors = self.validate_row(row)
            if errors:
                for error in errors:
                    result.errors.append(f"Row {row_num}: {error}")
                result.rows_skipped += 1
                continue

            # Parse row into model
            try:
                model = self.parse_row(row)
                if model is None:
                    result.rows_skipped += 1
                    continue

                session.add(model)
                result.rows_inserted += 1

            except Exception as e:
                result.errors.append(f"Row {row_num}: {e}")
                result.rows_skipped += 1
                continue

        # Commit all changes
        try:
            session.commit()
            logger.info(f"Ingested {result.rows_inserted} rows ({result.rows_skipped} skipped)")
        except Exception as e:
            session.rollback()
            result.errors.append(f"Commit failed: {e}")
            logger.error(f"Failed to commit: {e}")

        return result


def parse_int(value: str | None, default: int | None = None) -> int | None:
    """Parse a string to int, returning default if empty or invalid.

    Args:
        value: String value to parse
        default: Default value if parsing fails

    Returns:
        Parsed integer or default value
    """
    if value is None or value.strip() == "":
        return default
    try:
        # Handle comma-separated numbers like "1,234,567"
        return int(value.replace(",", ""))
    except ValueError:
        return default


def parse_float(value: str | None, default: float | None = None) -> float | None:
    """Parse a string to float, returning default if empty or invalid.

    Args:
        value: String value to parse
        default: Default value if parsing fails

    Returns:
        Parsed float or default value
    """
    if value is None or value.strip() == "":
        return default
    try:
        # Handle comma-separated numbers like "1,234.56"
        return float(value.replace(",", ""))
    except ValueError:
        return default


def validate_year(
    value: str | None,
    field_name: str = "year",
    min_year: int = 1900,
    max_year: int = 2100,
) -> list[str]:
    """Validate a year value and return any errors.

    Args:
        value: Year value to validate
        field_name: Name of the field for error messages
        min_year: Minimum valid year (default 1900)
        max_year: Maximum valid year (default 2100)

    Returns:
        List of error messages (empty if valid)
    """
    errors: list[str] = []

    if not value:
        errors.append(f"Missing required field: {field_name}")
    else:
        try:
            year = int(value)
            if year < min_year or year > max_year:
                errors.append(f"Year out of range: {year}")
        except ValueError:
            errors.append(f"Invalid {field_name}: {value}")

    return errors
