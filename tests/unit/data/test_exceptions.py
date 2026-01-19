"""Unit tests for data-layer exception types."""

from __future__ import annotations

from babylon.data.exceptions import CensusAPIError, SchemaCheckError
from babylon.utils.exceptions import DatabaseError, SchemaError


def test_schema_check_error_inherits_from_schema_error() -> None:
    assert issubclass(SchemaCheckError, SchemaError)
    assert issubclass(SchemaCheckError, DatabaseError)


def test_schema_check_error_carries_hint_in_details() -> None:
    error = SchemaCheckError("Schema drift", hint="Rebuild database")
    assert error.hint == "Rebuild database"
    assert error.details.get("hint") == "Rebuild database"


def test_data_api_error_redacts_url_and_merges_details() -> None:
    error = CensusAPIError(
        status_code=503,
        message="Service unavailable",
        url="https://api.census.gov/data/2017/acs/acs5?key=secret&get=NAME",
        details={
            "endpoint": "https://api.census.gov/data/2017/acs/acs5",
            "params": {"key": "secret"},
        },
    )

    assert "secret" not in error.url
    assert "secret" not in str(error)
    assert error.error_code == "DAPI_503"
    assert error.details["status_code"] == 503
    assert error.details["url"] == error.url
    assert error.details["endpoint"] == "https://api.census.gov/data/2017/acs/acs5"
    assert isinstance(error.details.get("params"), dict)
    assert error.details["params"]["key"] == "***"
