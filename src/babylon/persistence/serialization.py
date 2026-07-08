"""Shared JSON canonicalization helpers for persistence backends.

Both :class:`~babylon.persistence.runtime_db.RuntimeDatabase` and
:class:`~babylon.persistence.postgres_runtime.PostgresRuntime` persist
per-tick event dicts and compare canonical payloads for the spec-056
monotonic-idempotent contract. Event ``timestamp`` values are wall-clock
(:class:`~babylon.models.events.SimulationEvent` uses
``default_factory=datetime.now``) and therefore differ across retries of
the same tick; they are excluded from canonical comparison but preserved
in storage.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any
from uuid import UUID


def json_default(obj: object) -> str:
    """Fallback serializer for ``json.dumps`` — handles datetime/date/UUID.

    Args:
        obj: The non-JSON-native object encountered by the encoder.

    Returns:
        ISO-8601 string for :class:`~datetime.datetime` /
        :class:`~datetime.date`, ``str(obj)`` for :class:`~uuid.UUID`.

    Raises:
        TypeError: For any other non-serializable type.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def canonical_event_json(event: dict[str, Any]) -> str:
    """Canonical JSON for one event dict, excluding wall-clock ``timestamp``.

    Used by both sides of the spec-056 monotonic-idempotent comparison so
    that a retried tick whose only difference is regenerated event
    timestamps compares equal to the stored payload.

    Args:
        event: One event dict (``SimulationEvent.model_dump()`` shape or
            the JSON-decoded stored ``details`` row).

    Returns:
        Sort-keyed JSON string with the top-level ``timestamp`` key removed.
    """
    return json.dumps(
        {k: v for k, v in event.items() if k != "timestamp"},
        sort_keys=True,
        default=json_default,
    )
