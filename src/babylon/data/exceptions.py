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

from babylon.exceptions import DataAPIError

__all__ = [
    "ArcGISAPIError",
    "CensusAPIError",
    "CFSAPIError",
    "EIAAPIError",
    "FCCAPIError",
    "FredAPIError",
]


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
