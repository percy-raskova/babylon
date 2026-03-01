"""Buffered trace recorder for execution trace collection (Feature 037).

Implements ``TraceCollector`` protocol. Buffers trace events in memory
during tick computation, then flushes to persistent storage after tick
completion. Respects Constitution II.6: no DB I/O during tick.

Usage::

    from babylon.persistence.trace_recorder import TraceRecorder
    from babylon.persistence.protocols import TraceLevel

    recorder = TraceRecorder(level=TraceLevel.DEBUG, persistence=pg_runtime)

    # During tick (in-memory only):
    recorder.trace("ImperialRentSystem", "formula_eval", {"rent": 42.0})

    # After tick (flushes to DB):
    recorder.flush(session_id=session_id, tick=0)
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from babylon.persistence.protocols import TraceLevel

logger = logging.getLogger(__name__)


class TraceRecorder:
    """Buffered in-memory trace collector.

    Events are accumulated in a list during tick computation.
    ``flush()`` writes them to persistent storage and clears the buffer.

    When ``level`` is ``TraceLevel.NONE``, ``trace()`` is a no-op.

    Attributes:
        _level: Current trace verbosity level.
        _buffer: List of buffered trace event dicts.
        _persistence: Optional persistence backend for flush.
    """

    def __init__(
        self,
        level: TraceLevel = TraceLevel.NONE,
        persistence: Any = None,
    ) -> None:
        """Initialize the trace recorder.

        Args:
            level: Trace verbosity level.
            persistence: Optional ``PostgresRuntimeExtensions`` for flush.
        """
        self._level = level
        self._buffer: list[dict[str, Any]] = []
        self._persistence = persistence

    def trace(
        self,
        system: str,
        event: str,
        data: dict[str, Any],
        *,
        level: TraceLevel = TraceLevel.DEBUG,
        node_id: str | None = None,
    ) -> None:
        """Buffer a trace event (no I/O).

        Args:
            system: Name of the engine system.
            event: Event type.
            data: Structured payload.
            level: Minimum verbosity for this event.
            node_id: Optional node reference.
        """
        if self._level == TraceLevel.NONE:
            return
        if level > self._level:
            return

        self._buffer.append(
            {
                "system": system,
                "event": event,
                "data": data,
                "level": level.name,
                "node_id": node_id,
            }
        )

    def flush(self, session_id: UUID, tick: int) -> None:
        """Write buffered events to persistent storage and clear buffer.

        Args:
            session_id: Session scope.
            tick: The tick number.
        """
        if not self._buffer:
            return

        if self._persistence is not None:
            self._persistence.persist_traces(session_id, tick, self._buffer)
            logger.debug(
                "Flushed %d trace events for tick %d",
                len(self._buffer),
                tick,
            )

        self._buffer.clear()

    @property
    def level(self) -> TraceLevel:
        """The configured verbosity level."""
        return self._level

    @property
    def buffer_size(self) -> int:
        """Number of events currently buffered."""
        return len(self._buffer)


__all__ = ["TraceRecorder"]
