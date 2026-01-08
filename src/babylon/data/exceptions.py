"""Data layer API exceptions.

Provides specific exception classes for each external API used by the data
ingestion layer. All inherit from APIError for unified error handling.

Usage:
    from babylon.data.exceptions import CensusAPIError

    try:
        data = client.get_data(...)
    except CensusAPIError as e:
        logger.error(f"Census API failed: {e}")
        # Can also catch all data API errors with: except DataAPIError

Hierarchy:
    DataAPIError (from babylon.exceptions)
    ├── CensusAPIError - Census Bureau API (ACS, CFS)
    ├── FredAPIError - Federal Reserve FRED API
    ├── EIAAPIError - Energy Information Administration API
    ├── FCCAPIError - FCC Broadband Data Collection API
    ├── ArcGISAPIError - ArcGIS REST API (HIFLD, MIRTA)
    └── CFSAPIError - Census Commodity Flow Survey API
"""

from __future__ import annotations

import logging

from babylon.exceptions import DataAPIError

__all__ = [
    "ArcGISAPIError",
    "CensusAPIError",
    "CFSAPIError",
    "EIAAPIError",
    "FCCAPIError",
    "FredAPIError",
    "SchemaCheckError",
]


class SchemaCheckError(Exception):
    """Error during schema validation or migration checks.

    Attributes:
        message: Primary error message.
        hint: Optional guidance for resolving the error.
        details: Additional diagnostic information.
    """

    def __init__(
        self,
        message: str,
        hint: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        self.message = message
        self.hint = hint
        self.details: dict[str, object] = details or {}
        super().__init__(message)

    def __str__(self) -> str:
        if self.hint:
            return f"{self.message}\nHint: {self.hint}"
        return self.message

    def log(
        self,
        logger: logging.Logger,
        level: int = 40,  # logging.ERROR
        exc_info: bool = False,
    ) -> None:
        """Log this error with optional exception info.

        Args:
            logger: Logger instance to use.
            level: Logging level (default ERROR=40).
            exc_info: Whether to include exception traceback.
        """
        extra = {"hint": self.hint, "details": self.details}
        logger.log(level, self.message, exc_info=exc_info, extra=extra)


class CensusAPIError(DataAPIError):
    """Error from Census Bureau API (ACS, decennial, etc.)."""

    _service_name: str = "Census API"


class FredAPIError(DataAPIError):
    """Error from Federal Reserve FRED API."""

    _service_name: str = "FRED API"


class EIAAPIError(DataAPIError):
    """Error from Energy Information Administration API."""

    _service_name: str = "EIA API"


class FCCAPIError(DataAPIError):
    """Error from FCC Broadband Data Collection API."""

    _service_name: str = "FCC API"


class ArcGISAPIError(DataAPIError):
    """Error from ArcGIS REST API (HIFLD, MIRTA datasets)."""

    _service_name: str = "ArcGIS API"


class CFSAPIError(DataAPIError):
    """Error from Census Commodity Flow Survey API."""

    _service_name: str = "CFS API"
