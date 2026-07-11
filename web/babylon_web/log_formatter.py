"""JSON Lines log formatter for the Babylon web application.

Mirrors the engine's ``babylon.kernel.log.JSONFormatter`` pattern but
is self-contained — no dependency on the simulation engine.

Output format (one JSON object per line)::

    {"ts": "2026-03-02T17:30:00Z", "level": "INFO", "logger": "game.api",
     "msg": "GET /api/games/ 200 (12.3ms)", "func": "game_list", "line": 42,
     "correlation_id": "abc-def-123"}
"""

from __future__ import annotations

import json
import logging
import traceback
from datetime import UTC, datetime

# Fields to omit from the extra dict (already in the base record).
_SKIP_FIELDS = frozenset(
    {
        "name",
        "msg",
        "args",
        "created",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "exc_info",
        "exc_text",
        "message",
        "taskName",
    }
)


class WebJSONFormatter(logging.Formatter):
    """JSON Lines formatter — zero external dependencies.

    Produces one compact JSON object per log line with consistent field
    order: ts, level, logger, msg, func, line, plus any extra fields.

    Sensitive fields (password, token, secret, key) are redacted.
    """

    _SENSITIVE_KEYS = frozenset({"password", "token", "secret", "api_key", "authorization"})

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON object."""
        entry: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "func": record.funcName,
            "line": record.lineno,
        }

        # Merge extra fields (anything set via logger.info("msg", extra={...}))
        for key, value in record.__dict__.items():
            if key in _SKIP_FIELDS or key.startswith("_"):
                continue
            if key in self._SENSITIVE_KEYS:
                entry[key] = "***REDACTED***"
            else:
                entry[key] = value

        # Exception info
        if record.exc_info and record.exc_info[1] is not None:
            entry["exc_type"] = type(record.exc_info[1]).__name__
            entry["exc_msg"] = str(record.exc_info[1])
            entry["exc_tb"] = traceback.format_exception(*record.exc_info)

        return json.dumps(entry, default=str, ensure_ascii=False)
