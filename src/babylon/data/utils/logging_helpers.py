"""Structured logging helpers for data ingestion."""

from __future__ import annotations

import logging

from babylon.utils.log import redact_params, redact_url


def _sanitize_context(context: dict[str, object] | None) -> dict[str, object]:
    """Redact sensitive fields in logging context."""
    if not context:
        return {}

    sanitized: dict[str, object] = {}
    for key, value in context.items():
        if key in {"params", "headers"} and isinstance(value, dict):
            sanitized[key] = redact_params(value)
        elif key in {"url", "endpoint"} and isinstance(value, str):
            sanitized[key] = redact_url(value)
        else:
            sanitized[key] = value
    return sanitized


def log_api_error(
    logger: logging.Logger,
    error: Exception,
    *,
    context: dict[str, object] | None = None,
    level: int = logging.WARNING,
) -> None:
    """Log an API error with structured context."""
    extra = _sanitize_context(context)

    if hasattr(error, "to_dict"):
        exception_details = error.to_dict()
    else:
        exception_details = {
            "error_type": error.__class__.__name__,
            "message": str(error),
        }

    extra.update(
        {
            "exception": exception_details,
            "error_type": error.__class__.__name__,
            "error_code": getattr(error, "error_code", None),
            "status_code": getattr(error, "status_code", None),
            "url": getattr(error, "url", None),
        }
    )

    logger.log(level, str(error), extra=extra)


def log_api_retry(
    logger: logging.Logger,
    *,
    reason: str,
    attempt: int,
    max_retries: int,
    wait_time: float,
    context: dict[str, object] | None = None,
) -> None:
    """Log a retry decision with structured context."""
    extra = _sanitize_context(context)
    extra.update(
        {
            "retry_reason": reason,
            "attempt": attempt,
            "max_retries": max_retries,
            "wait_time": wait_time,
        }
    )
    logger.warning("Retrying API request: %s", reason, extra=extra)


__all__ = ["log_api_error", "log_api_retry"]
