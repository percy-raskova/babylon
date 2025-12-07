"""Retry decorator for transient failure handling.

In the material world, systems fail. Networks drop.
Databases timeout. The revolutionary must persevere.
"""

import functools
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def retry_on_exception(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: type[Exception] | tuple[type[Exception], ...] = Exception,
    logger: logging.Logger | None = None,
) -> Callable[[F], F]:
    """Decorator that retries a function on specified exceptions.

    Uses exponential backoff to avoid hammering failing resources.
    This is a materialist approach: we respect the physical constraints
    of the systems we depend on.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier applied to delay after each retry
        exceptions: Exception types that trigger a retry
        logger: Logger instance for retry messages

    Returns:
        Decorated function with retry logic

    Example:
        @retry_on_exception(max_retries=3, delay=1.0, exceptions=(ConnectionError,))
        def fetch_data():
            return requests.get("https://api.example.com")
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _logger = logger or logging.getLogger(func.__module__)
            current_delay = delay
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        _logger.error(
                            "Function %s failed after %d attempts: %s",
                            func.__name__,
                            max_retries + 1,
                            str(e),
                        )
                        raise

                    _logger.warning(
                        "Function %s failed (attempt %d/%d): %s. Retrying in %.1fs...",
                        func.__name__,
                        attempt + 1,
                        max_retries + 1,
                        str(e),
                        current_delay,
                    )

                    time.sleep(current_delay)
                    current_delay *= backoff

            # This should never be reached, but satisfies the type checker
            if last_exception:
                raise last_exception
            raise RuntimeError("Retry logic failed unexpectedly")

        return wrapper  # type: ignore[return-value]

    return decorator
