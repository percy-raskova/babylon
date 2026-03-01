"""Contract: TraceRecorder observer for execution trace collection.

Feature 037: Postgres Runtime Database
Buffers structured trace events during tick execution and flushes
to persistent storage after tick completion. Respects Constitution II.6:
no DB I/O during tick computation.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Protocol, runtime_checkable
from uuid import UUID


class TraceLevel(IntEnum):
    """Trace verbosity levels. Each level includes everything from lower levels."""

    NONE = 0
    SUMMARY = 1
    DEBUG = 2
    TRACE = 3


@runtime_checkable
class TraceCollector(Protocol):
    """Protocol for collecting execution trace events during tick computation.

    Systems access the tracer through ServiceContainer or TickContext.
    When trace_level is NONE, the implementation is a no-op stub.
    """

    def trace(
        self,
        system: str,
        event: str,
        data: dict,
        *,
        level: TraceLevel = TraceLevel.DEBUG,
        node_id: str | None = None,
    ) -> None:
        """Buffer a trace event (called during tick execution).

        Events accumulate in memory. No I/O occurs.

        :param system: Name of the engine system producing the event.
        :param event: Event type (e.g., 'formula_eval', 'edge_mode_transition').
        :param data: Structured event payload.
        :param level: Minimum verbosity level required for this event.
        :param node_id: Optional node reference for node-specific events.
        """
        ...

    def flush(self, session_id: UUID, tick: int) -> None:
        """Write buffered events to persistent storage.

        Called AFTER tick computation completes. This is the only
        point where I/O occurs.

        :param session_id: Session scope for the trace data.
        :param tick: The tick number.
        """
        ...

    @property
    def level(self) -> TraceLevel:
        """The configured verbosity level for this collector."""
        ...

    @property
    def buffer_size(self) -> int:
        """Number of events currently buffered (for monitoring)."""
        ...
