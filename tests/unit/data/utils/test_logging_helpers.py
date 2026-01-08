"""Unit tests for data logging helpers."""

from __future__ import annotations

import logging

import pytest

from babylon.data.exceptions import CensusAPIError
from babylon.data.utils.logging_helpers import log_api_error, log_api_retry


@pytest.mark.unit
class TestLoggingHelpers:
    """Tests for structured API logging helpers."""

    def test_log_api_error_redacts_params(self, caplog: pytest.LogCaptureFixture) -> None:
        """API error logging should redact sensitive params."""
        logger = logging.getLogger("babylon.test.logging")
        error = CensusAPIError(
            status_code=503,
            message="Service unavailable",
            url="https://api.census.gov/data?key=secret",
            details={"params": {"key": "secret", "foo": "bar"}},
        )

        context = {
            "endpoint": "https://api.census.gov/data?key=secret",
            "params": {"key": "secret"},
        }

        with caplog.at_level(logging.WARNING):
            log_api_error(logger, error, context=context, level=logging.WARNING)

        assert caplog.records
        record = caplog.records[-1]
        assert "secret" not in record.endpoint
        assert record.params["key"] == "***"
        assert record.exception["error_code"].startswith("DAPI_")

    def test_log_api_retry_includes_context(self, caplog: pytest.LogCaptureFixture) -> None:
        """Retry logging should include structured retry context."""
        logger = logging.getLogger("babylon.test.retry")
        context = {"endpoint": "https://api.example.com", "params": {"key": "secret"}}

        with caplog.at_level(logging.WARNING):
            log_api_retry(
                logger,
                reason="server_error",
                attempt=2,
                max_retries=3,
                wait_time=1.5,
                context=context,
            )

        assert caplog.records
        record = caplog.records[-1]
        assert record.retry_reason == "server_error"
        assert record.attempt == 2
        assert record.max_retries == 3
        assert record.wait_time == 1.5
        assert record.params["key"] == "***"
