"""Persistence protocols for backend-agnostic simulation state storage.

Feature 037: PostgreSQL Runtime Database.

Defines the formal interface boundary between the simulation engine
and storage backends. Both SQLite (``RuntimeDatabase``) and PostgreSQL
(``PostgresRuntime``) implement ``RuntimePersistence``.

Constitution II.6 compliance: all persistence methods are called
**outside** tick computation. Zero DB I/O during tick.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

import networkx as nx


class TraceLevel(IntEnum):
    """Trace verbosity levels. Each level includes everything below it."""

    NONE = 0
    SUMMARY = 1
    DEBUG = 2
    TRACE = 3


@runtime_checkable
class RuntimePersistence(Protocol):
    """Backend-agnostic simulation state persistence.

    The simulation engine interacts with the persistence layer exclusively
    through this protocol. Both SQLite (dev/test) and Postgres (production)
    implement it.
    """

    def persist_tick(
        self,
        tick: int,
        graph: nx.DiGraph[str],
        events: list[dict[str, Any]] | None = None,
        *,
        session_id: UUID | None = None,
    ) -> None:
        """Persist a complete state snapshot at the given tick.

        Full snapshot, not diff. Idempotent via UPSERT semantics.

        Args:
            tick: The tick number to persist.
            graph: The full simulation graph with all node/edge attributes.
            events: Optional list of simulation events from this tick.
            session_id: Session scope (required for Postgres, optional for SQLite).
        """
        ...

    def hydrate_graph(
        self,
        tick: int | None = None,
        *,
        session_id: UUID | None = None,
    ) -> nx.DiGraph[str]:
        """Load a complete state snapshot from storage.

        If tick is None, loads the latest available tick.

        Args:
            tick: The tick number to load, or None for latest.
            session_id: Session scope.

        Returns:
            A fully populated NetworkX DiGraph.
        """
        ...

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
    ) -> None:
        """Record tick replay metadata (RNG state, mutations, timings).

        Args:
            tick: The tick number.
            rng_state: Serialized RNG state for deterministic replay.
            mutations: Summary of state mutations applied this tick.
            invariant_checks: Conservation checks and sum-to-one results.
            wall_time_ms: Total tick execution wall time in milliseconds.
            system_timings: Per-system execution time in milliseconds.
            session_id: Session scope.
        """
        ...

    def set_metadata(self, key: str, value: str) -> None:
        """Store a key-value metadata pair.

        Args:
            key: Metadata key.
            value: Metadata value (serialized as string).
        """
        ...

    def get_metadata(self, key: str) -> str | None:
        """Retrieve a metadata value by key.

        Args:
            key: Metadata key.

        Returns:
            The stored value, or None if not found.
        """
        ...


@runtime_checkable
class PostgresRuntimeExtensions(Protocol):
    """Extended methods specific to PostgresRuntime.

    These methods persist subsystems added after the original
    ``RuntimePersistence`` protocol (Features 002, 022, 029, 032, 036).
    The ``PersistenceObserver`` accesses these via ``isinstance()`` check.
    """

    def persist_graph_metadata(
        self,
        tick: int,
        economy: dict[str, Any],
        state_finances: dict[str, Any],
        tick_dynamics: dict[str, Any] | None,
        *,
        session_id: UUID,
    ) -> None:
        """Persist graph-level metadata (economy, state finances, tick dynamics).

        Args:
            tick: The tick number.
            economy: GlobalEconomy.model_dump().
            state_finances: {state_id: StateFinance.model_dump()}.
            tick_dynamics: NationalTickParameters + SmoothedCoefficients, or None.
            session_id: Session scope.
        """
        ...

    def persist_community_state(
        self,
        tick: int,
        community_states: dict[str, Any],
        memberships: list[dict[str, Any]],
        *,
        session_id: UUID,
    ) -> None:
        """Persist hypergraph community state and membership records.

        Args:
            tick: The tick number.
            community_states: {CommunityType: CommunityState dict}.
            memberships: List of CommunityMembership dicts.
            session_id: Session scope.
        """
        ...

    def hydrate_community_state(
        self,
        tick: int,
        *,
        session_id: UUID,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Load community state and memberships at a specific tick.

        Args:
            tick: The tick number.
            session_id: Session scope.

        Returns:
            Tuple of (community_states dict, memberships list).
        """
        ...

    def persist_hex_state(
        self,
        tick: int,
        hex_states: list[dict[str, Any]],
        *,
        session_id: UUID,
    ) -> None:
        """Persist per-hex economic state. Bulk insert ~1,500 rows.

        Args:
            tick: The tick number.
            hex_states: List of HexEconomicState dicts.
            session_id: Session scope.
        """
        ...

    def persist_infrastructure_state(
        self,
        tick: int,
        terrain_states: list[dict[str, Any]],
        link_states: list[dict[str, Any]],
        *,
        session_id: UUID,
    ) -> None:
        """Persist Feature 036 infrastructure topology state.

        Args:
            tick: The tick number.
            terrain_states: Per-hex terrain + biocapacity + internet state.
            link_states: Per-edge infrastructure link state.
            session_id: Session scope.
        """
        ...

    def persist_contradiction_fields(
        self,
        tick: int,
        fields: list[dict[str, Any]],
        curvatures: list[dict[str, Any]],
        *,
        session_id: UUID,
    ) -> None:
        """Persist Feature 002 contradiction field values and edge curvatures.

        Args:
            tick: The tick number.
            fields: Per-node field values with derivatives.
            curvatures: Per-edge Ollivier-Ricci curvature values.
            session_id: Session scope.
        """
        ...

    def persist_action_results(
        self,
        tick: int,
        results: list[dict[str, Any]],
        *,
        session_id: UUID,
    ) -> None:
        """Persist OODA action resolution outcomes (Feature 032).

        Args:
            tick: The tick number.
            results: List of action result dicts.
            session_id: Session scope.
        """
        ...

    def persist_tick_summary(
        self,
        tick: int,
        summary: dict[str, Any],
        *,
        session_id: UUID,
    ) -> None:
        """Persist pre-aggregated tick summary for time-series endpoints.

        Args:
            tick: The tick number.
            summary: Aggregated metrics dict.
            session_id: Session scope.
        """
        ...

    def persist_traces(
        self,
        session_id: UUID,
        tick: int,
        trace_events: list[dict[str, Any]],
    ) -> None:
        """Bulk insert trace events to trace_log.

        Called by TraceRecorder.flush() after tick completion.

        Args:
            session_id: Session scope.
            tick: The tick number.
            trace_events: List of structured trace event dicts.
        """
        ...

    def create_session_partition(self, session_id: UUID) -> None:
        """Create a trace_log partition for a new session.

        Args:
            session_id: Session to partition.
        """
        ...

    def drop_session_partition(self, session_id: UUID) -> None:
        """Drop a trace_log partition for a completed/archived session.

        Args:
            session_id: Session to clean up.
        """
        ...

    def export_session_to_parquet(
        self,
        session_id: UUID,
        output_dir: str,
    ) -> list[str]:
        """Export all session data to Parquet files.

        Args:
            session_id: Session to export.
            output_dir: Directory for Parquet output files.

        Returns:
            List of generated Parquet file paths.
        """
        ...


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
        data: dict[str, Any],
        *,
        level: TraceLevel = TraceLevel.DEBUG,
        node_id: str | None = None,
    ) -> None:
        """Buffer a trace event (called during tick execution).

        Events accumulate in memory. No I/O occurs.

        Args:
            system: Name of the engine system producing the event.
            event: Event type (e.g., 'formula_eval', 'edge_mode_transition').
            data: Structured event payload.
            level: Minimum verbosity level required for this event.
            node_id: Optional node reference for node-specific events.
        """
        ...

    def flush(self, session_id: UUID, tick: int) -> None:
        """Write buffered events to persistent storage.

        Called AFTER tick computation completes.

        Args:
            session_id: Session scope for the trace data.
            tick: The tick number.
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


@runtime_checkable
class VectorStoreProtocol(Protocol):
    """Backend-agnostic vector storage for semantic search.

    Implementations: PgVectorStore (Feature 037).
    The Retriever interacts only through this protocol.
    """

    def add_chunks(self, chunks: list[Any]) -> None:
        """Store document chunks with their embeddings.

        Args:
            chunks: List of objects with id, content, embedding, metadata.
        """
        ...

    def query_similar(
        self,
        query_embedding: list[float],
        k: int = 10,
        where: dict[str, Any] | None = None,
        include: list[str] | None = None,
    ) -> tuple[list[str], list[str], list[list[float]], list[dict[str, Any]], list[float]]:
        """Find the k most similar chunks to the query embedding.

        Args:
            query_embedding: The query vector.
            k: Number of results to return.
            where: Optional metadata filter.
            include: Fields to include in results.

        Returns:
            Tuple of (ids, documents, embeddings, metadatas, distances).
        """
        ...

    def delete_chunks(self, chunk_ids: list[str]) -> None:
        """Delete chunks by their IDs.

        Args:
            chunk_ids: List of chunk IDs to remove.
        """
        ...

    def get_collection_count(self) -> int:
        """Return the total number of chunks in the store.

        Returns:
            Count of stored chunks.
        """
        ...


__all__ = [
    "PostgresRuntimeExtensions",
    "RuntimePersistence",
    "TraceCollector",
    "TraceLevel",
    "VectorStoreProtocol",
]
