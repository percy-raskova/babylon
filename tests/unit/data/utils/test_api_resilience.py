"""Unit tests for API resilience helpers."""

from __future__ import annotations

import pytest

from babylon.data.utils.api_resilience import (
    RetryPolicy,
    should_retry_exception,
    should_retry_status,
)


class DummyError(Exception):
    """Synthetic error for retry classification tests."""


@pytest.mark.unit
class TestRetryPolicy:
    """Tests for retry policy behavior."""

    def test_backoff_seconds_uses_exponential_growth(self) -> None:
        """Backoff should grow exponentially by attempt."""
        policy = RetryPolicy(max_retries=3, base_delay=1.0, backoff_factor=2.0, jitter=0.0)
        assert policy.backoff_seconds(0) == 1.0
        assert policy.backoff_seconds(1) == 2.0
        assert policy.backoff_seconds(2) == 4.0

    def test_should_retry_status_for_transient_codes(self) -> None:
        """Retryable status codes should be classified as transient."""
        policy = RetryPolicy()
        assert should_retry_status(429, policy) is True
        assert should_retry_status(503, policy) is True

    def test_should_not_retry_status_for_client_error(self) -> None:
        """Non-retryable status codes should not be retried."""
        policy = RetryPolicy()
        assert should_retry_status(400, policy) is False

    def test_should_retry_exception_for_transient_type(self) -> None:
        """Transient exception types should be retryable."""
        error = DummyError("boom")
        assert should_retry_exception(error, (DummyError,)) is True
        assert should_retry_exception(error, (ValueError,)) is False
