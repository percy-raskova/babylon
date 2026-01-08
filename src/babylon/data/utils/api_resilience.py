"""Shared retry/backoff helpers for data API clients."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    """Retry/backoff policy for transient API failures.

    Args:
        max_retries: Maximum retry attempts before failing.
        base_delay: Base delay (seconds) for backoff calculation.
        backoff_factor: Exponential backoff multiplier.
        jitter: Optional random jitter (seconds) added to backoff.
        retry_statuses: HTTP status codes that should be retried.
        retry_status_classes: HTTP status code classes to retry (e.g., 5 for 5xx).
    """

    max_retries: int = 3
    base_delay: float = 0.5
    backoff_factor: float = 2.0
    jitter: float = 0.0
    retry_statuses: frozenset[int] = frozenset({429})
    retry_status_classes: frozenset[int] = frozenset({5})

    def backoff_seconds(self, attempt: int) -> float:
        """Calculate backoff time for a retry attempt."""
        delay = self.base_delay * (self.backoff_factor**attempt)
        if self.jitter > 0:
            delay += random.uniform(0.0, self.jitter)
        return delay


def should_retry_status(status_code: int, policy: RetryPolicy) -> bool:
    """Return True if the status code should be retried."""
    if status_code in policy.retry_statuses:
        return True
    status_class = status_code // 100
    return status_class in policy.retry_status_classes


def should_retry_exception(
    exc: BaseException, transient_exceptions: tuple[type[BaseException], ...]
) -> bool:
    """Return True if the exception type is retryable."""
    return isinstance(exc, transient_exceptions)


__all__ = ["RetryPolicy", "should_retry_exception", "should_retry_status"]
