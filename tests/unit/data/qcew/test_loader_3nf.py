"""Unit tests for QCEW loader error tracking."""

from __future__ import annotations

import pytest

from babylon.data.exceptions import QcewAPIError
from babylon.data.loader_base import LoadStats
from babylon.data.qcew.loader_3nf import QcewLoader


@pytest.mark.unit
class TestQcewLoaderApiErrors:
    """Tests for QCEW loader API error recording."""

    def test_handle_api_error_records_context_details(self) -> None:
        """API errors should include area/year details in LoadStats."""
        loader = QcewLoader()
        stats = LoadStats(source="qcew_hybrid")

        error = QcewAPIError(
            status_code=500,
            message="Server error",
            url="https://api.bls.gov/publicAPI/v1/123?key=secret",
            details={"endpoint": "https://api.bls.gov/publicAPI/v1/123?key=secret"},
        )

        loader._handle_api_error(error, area_code="01001", year=2022, stats=stats)

        assert len(stats.api_errors) == 1
        detail = stats.api_errors[0]
        assert detail.context == "qcew:01001:2022"
        assert detail.details is not None
        assert detail.details.get("loader") == "qcew"
        assert detail.details.get("area_code") == "01001"
        assert detail.details.get("year") == 2022
        assert detail.details.get("endpoint") == "https://api.bls.gov/publicAPI/v1/123?key=***"
