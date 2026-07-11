"""Kernel protocol for the injectable database connection.

``babylon.persistence.database.DatabaseConnection`` is the SQLAlchemy
implementation; this protocol is the surface the engine's service container
types against, so SQLAlchemy plumbing lives in the persistence layer and the
engine holds only the contract (Constitution II.6 — "no DB I/O during tick";
Program 14 Phase 1 removed the concrete import from the engine's DI).

Structural conformance is pinned by ``tests/unit/kernel/``.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any, Protocol


class DatabaseProtocol(Protocol):
    """Injectable database connection surface.

    :meth:`session` yields a live session inside a context manager;
    :meth:`close` disposes the underlying engine.
    """

    def session(self) -> AbstractContextManager[Any]:
        """Open a session context; commit/rollback semantics are the impl's."""
        ...

    def close(self) -> None:
        """Dispose of the connection's resources."""
        ...
