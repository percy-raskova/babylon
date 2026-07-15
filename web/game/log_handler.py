"""Database logging handler for game events.

Provides a ``log_game_event`` function that persists significant events
to the ``game_event_log`` table in PostgreSQL. This is NOT a
``logging.Handler`` subclass — it is called explicitly at the API layer
for events worth persisting (game creation, tick resolution, errors).

Why explicit calls instead of a logging.Handler?
- Database writes in a logging handler risk infinite recursion (DB
  errors trigger logs that trigger DB writes).
- We want selective persistence — only game-significant events, not
  every DEBUG line.
- Explicit calls make it clear which events hit the database.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


def sanitize_for_log(value: object, *, max_length: int = 200) -> str:
    """Strip CR/LF and control chars from a value bound for a log line, and truncate.

    Prevents CodeQL ``py/log-injection`` (forged log lines via newline injection in
    user-controlled input).

    :param value: Any value to be logged.
    :param max_length: Cap on the returned string's length.
    :returns: A single-line, control-char-free, length-capped string.
    """
    text = str(value)
    cleaned = "".join(ch for ch in text if ch == " " or (ch.isprintable() and ch not in "\r\n"))
    return cleaned[:max_length]


def log_game_event(
    *,
    category: str,
    message: str,
    session_id: UUID | str | None = None,
    user_id: int | None = None,
    tick: int | None = None,
    details: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> None:
    """Persist a game event to the ``game_event_log`` table.

    Args:
        category: One of ``GameEventLog.EventCategory`` values.
        message: Human-readable event description.
        session_id: Game session UUID, if applicable.
        user_id: Django auth user ID, if applicable.
        tick: Game tick number, if applicable.
        details: Optional JSON-serializable dict of extra context.
        correlation_id: Request correlation ID for tracing.
    """
    try:
        # Late import to avoid circular imports at module load time
        from game.models import GameEventLog

        GameEventLog.objects.create(
            category=category,
            message=message,
            session_id=session_id,
            user_id=user_id,
            tick=tick,
            details=details,
            correlation_id=correlation_id,
        )
    except Exception:
        # Never let audit logging crash the request — log and move on
        logger.exception(
            "Failed to persist game event: category=%s message=%s",
            sanitize_for_log(category),
            sanitize_for_log(message),
        )
