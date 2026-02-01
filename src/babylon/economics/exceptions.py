"""Exceptions for the economics package.

This module provides custom exceptions for tensor operations and data loading.

Feature: 011-fundamental-tensor-primitive
Implements: T054 from tasks.md

Example:
    >>> from babylon.economics.exceptions import TensorInitializationError
    >>> raise TensorInitializationError("Database connection failed")
"""

from __future__ import annotations


class TensorError(Exception):
    """Base exception for all tensor-related errors.

    All tensor-specific exceptions inherit from this class, enabling
    broad exception handling:

        try:
            registry.hydrate_counties(...)
        except TensorError as e:
            handle_tensor_error(e)
    """

    pass


class TensorInitializationError(TensorError):
    """Raised when tensor initialization fails.

    This exception is raised when:
    - SQLite database is unavailable or corrupt
    - Required tables are missing from the database
    - Database connection fails during hydration

    Example:
        >>> try:
        ...     registry.hydrate_counties(hydrator, fips_codes, years)
        ... except TensorInitializationError as e:
        ...     logger.error("Failed to initialize tensor registry: %s", e)
        ...     # Fall back to default behavior or re-raise
    """

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable description of the error.
            cause: Optional underlying exception that caused this error.
        """
        super().__init__(message)
        self.cause = cause


class TensorHydrationError(TensorError):
    """Raised when tensor hydration fails for a specific county-year.

    This is a less severe error than TensorInitializationError.
    Hydration can continue for other county-years.

    Attributes:
        fips: FIPS code that failed to hydrate.
        year: Year that failed to hydrate.

    Example:
        >>> try:
        ...     tensor = hydrator.hydrate("26163", 2022)
        ... except TensorHydrationError as e:
        ...     logger.warning("Could not hydrate %s/%d: %s", e.fips, e.year, e)
    """

    def __init__(
        self,
        message: str,
        fips: str,
        year: int,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable description of the error.
            fips: FIPS code that failed to hydrate.
            year: Year that failed to hydrate.
            cause: Optional underlying exception that caused this error.
        """
        super().__init__(message)
        self.fips = fips
        self.year = year
        self.cause = cause


__all__ = [
    "TensorError",
    "TensorHydrationError",
    "TensorInitializationError",
]
