"""Narrow protocols for intentional Python persistence periphery.

Authoritative campaign PostgreSQL writes belong to ``babylon-runtime``.
Python retains its deterministic local SQLite store, read-only PostgreSQL
projections, and the independent vector store.
"""

from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from babylon.topology.graph import BabylonGraph


class TraceLevel(IntEnum):
    """Trace verbosity levels. Each level includes everything below it."""

    NONE = 0
    SUMMARY = 1
    DEBUG = 2
    TRACE = 3


class TickAlreadyResolved(Exception):
    """A frozen Python resolve path attempted to resolve one tick twice."""

    def __init__(self, session_id: UUID, tick: int) -> None:
        self.session_id = session_id
        self.tick = tick
        super().__init__(f"Tick {tick} for session {session_id} is already resolved")


class MonotonicityViolationError(Exception):
    """A local SQLite retry supplied different bytes for a durable tick."""

    def __init__(
        self,
        tick: int,
        existing_payload: Any | None = None,
        attempted_payload: Any | None = None,
    ) -> None:
        self.tick = tick
        self.existing_payload = existing_payload
        self.attempted_payload = attempted_payload
        super().__init__(f"Cannot overwrite tick {tick} with a different payload")


@runtime_checkable
class RuntimePersistence(Protocol):
    """Frozen local-state surface implemented by :class:`RuntimeDatabase`.

    This protocol does not grant PostgreSQL authority and has no production
    PostgreSQL implementation after the Gate 3 cutover.
    """

    def persist_tick(
        self,
        tick: int,
        graph: BabylonGraph,
        events: list[dict[str, Any]] | None = None,
        *,
        session_id: UUID | None = None,
    ) -> None: ...

    def hydrate_graph(
        self,
        tick: int | None = None,
        *,
        session_id: UUID | None = None,
    ) -> BabylonGraph: ...

    def log_tick(
        self,
        tick: int,
        rng_state: bytes | None = None,
        mutations: dict[str, Any] | None = None,
        invariant_checks: dict[str, bool] | None = None,
        wall_time_ms: int | None = None,
        system_timings: dict[str, int] | None = None,
        *,
        session_id: UUID | None = None,
    ) -> None: ...

    def set_metadata(self, key: str, value: str) -> None: ...

    def get_metadata(self, key: str) -> str | None: ...


class ReadOnlyPostgres(Protocol):
    """Structural type for the retained read-only PostgreSQL projections."""

    _pool: Any


@runtime_checkable
class VectorStoreProtocol(Protocol):
    """Independent vector-search storage surface."""

    def add_chunks(self, chunks: list[Any]) -> None: ...

    def query_similar(
        self,
        query_embedding: list[float],
        k: int = 10,
        where: dict[str, Any] | None = None,
        include: list[str] | None = None,
    ) -> tuple[list[str], list[str], list[list[float]], list[dict[str, Any]], list[float]]: ...

    def delete_chunks(self, chunk_ids: list[str]) -> None: ...

    def get_collection_count(self) -> int: ...


__all__ = [
    "MonotonicityViolationError",
    "ReadOnlyPostgres",
    "RuntimePersistence",
    "TickAlreadyResolved",
    "TraceLevel",
    "VectorStoreProtocol",
]
