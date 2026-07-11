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
    """Raised when ``persist_full_tick`` (or the atomic resolution path)
    is invoked for a ``(session_id, tick)`` that has already been written.

    Spec 061 FR-005 (Real Backend Wire-Up): resolved ticks are immutable.
    The implementation guards this via ``INSERT ... ON CONFLICT
    (session_id, tick) DO NOTHING RETURNING id`` against ``tick_log``;
    if the RETURNING clause yields no row, the tick was already resolved
    by a prior (or concurrent) writer, and this exception is raised so
    the caller can surface a 409 Conflict to the API client.

    This is **distinct** from :class:`MonotonicityViolationError`:

    - ``MonotonicityViolationError`` is raised by the lower-level
      ``persist_tick`` protocol method when an UPSERT-style retry
      attempts to overwrite an existing tick with a *different* payload
      — it is the post-spec-056 idempotency guard.
    - ``TickAlreadyResolved`` is raised by the higher-level resolve
      flow when any second resolution is attempted, regardless of
      whether the new payload matches — the resolve flow is a one-shot
      operation per FR-005.

    Args:
        session_id: The session whose tick was already resolved.
        tick: The tick number that the caller tried to re-resolve.
    """

    def __init__(self, session_id: UUID, tick: int) -> None:
        self.session_id = session_id
        self.tick = tick
        super().__init__(
            f"Tick {tick} for session {session_id} has already been resolved; "
            "resolved ticks are immutable per spec 061 FR-005."
        )


class MonotonicityViolationError(Exception):
    """Raised when ``persist_tick`` is called with a DIFFERENT payload for
    an already-persisted ``(session_id, tick)`` pair.

    Per Constitution II.6 (State is Data) and III.7 (Determinism), the
    persisted record for tick N is immutable once written *with respect
    to its content*. Implementations of
    :meth:`RuntimePersistence.persist_tick` MUST raise this exception
    when a re-persist supplies a payload that differs from the
    already-stored payload for the same ``(session_id, tick)`` pair.

    A re-persist with the **same** payload (the canonical UPSERT-retry
    pattern used by ``persistence_observer.py:146`` and
    ``session_recorder.py:168``) succeeds idempotently and does NOT
    raise. This preserves existing retry semantics while blocking
    silent rewrite of historical state.

    Spec 056 (US4 / INV-016): payload comparison is on the
    canonical-serialized form (the final dict / JSON / bytes that would
    be written), not the in-memory object — avoids spurious mismatches
    from non-deterministic ordering of dict keys / set iteration / etc.

    Args:
        tick: The tick number that an overwrite was attempted on.
        existing_payload: The payload currently persisted for that tick,
            if available (in-memory backends populate this; Postgres may
            populate it post-SELECT).
        attempted_payload: The differing payload that the caller tried
            to persist.
    """

    def __init__(
        self,
        tick: int,
        existing_payload: Any | None = None,
        attempted_payload: Any | None = None,
    ) -> None:
        self.tick = tick
        self.existing_payload = existing_payload
        self.attempted_payload = attempted_payload
        super().__init__(
            f"Cannot overwrite already-persisted tick {tick} with different "
            f"payload (use identical payload for idempotent retry)"
        )


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
        graph: BabylonGraph,
        events: list[dict[str, Any]] | None = None,
        *,
        session_id: UUID | None = None,
    ) -> None:
        """Persist a complete state snapshot at the given tick.

        Full snapshot, not diff. **Monotonic-idempotent semantics**
        (refined by Spec 056 F7=B clarification, 2026-05-07):

        - If ``(session_id, tick)`` is not yet persisted, the payload
          is written and the method returns successfully.
        - If ``(session_id, tick)`` IS already persisted, the
          implementation MUST compare the new payload against the
          existing payload (canonical-serialized equality):

          - **Same payload**: succeed silently (idempotent retry —
            preserves the existing observer / recorder retry semantics
            in ``persistence_observer.py:146`` and
            ``session_recorder.py:168``).
          - **Different payload**: raise
            :exc:`MonotonicityViolationError` with ``existing_payload``,
            ``attempted_payload``, and ``tick`` populated.

        Silent overwrite of differing payloads is forbidden — it
        would silently rewrite history and break the audit trail
        invariant required by Constitution II.6 (State is Data) and
        III.7 (Determinism — replay from any tick).

        Args:
            tick: The tick number to persist.
            graph: The full simulation graph with all node/edge attributes.
            events: Optional list of simulation events from this tick.
            session_id: Session scope (required for Postgres, optional for SQLite).

        Raises:
            MonotonicityViolationError: If ``(session_id, tick)`` is
                already persisted with a different payload.
        """
        ...

    def hydrate_graph(
        self,
        tick: int | None = None,
        *,
        session_id: UUID | None = None,
    ) -> BabylonGraph:
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
    "MonotonicityViolationError",
    "PostgresRuntimeExtensions",
    "RuntimePersistence",
    "TickAlreadyResolved",
    "TraceCollector",
    "TraceLevel",
    "VectorStoreProtocol",
]
