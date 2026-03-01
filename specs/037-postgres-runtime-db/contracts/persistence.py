"""Contract: RuntimePersistence protocol and PostgresRuntime extensions.

Feature 037: Postgres Runtime Database
Defines the backend-agnostic persistence interface that both SQLite
RuntimeDatabase and PostgresRuntime must implement.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

import networkx as nx


@runtime_checkable
class RuntimePersistence(Protocol):
    """Backend-agnostic simulation state persistence.

    The simulation engine interacts with the persistence layer exclusively
    through this protocol. Both SQLite (dev/test) and Postgres (production)
    implement it.

    Constitution II.6 compliance: All methods are called OUTSIDE tick
    computation. ``persist_tick`` after tick end, ``hydrate_graph`` before
    tick start. Zero DB I/O during tick.
    """

    def persist_tick(
        self,
        tick: int,
        graph: nx.DiGraph,
        events: list[dict] | None = None,
        *,
        session_id: UUID | None = None,
    ) -> None:
        """Persist a complete state snapshot at the given tick.

        Writes all node state, edge state, and events to storage.
        Full snapshot, not diff. Idempotent: re-persisting the same
        tick overwrites the previous snapshot.

        :param tick: The tick number to persist.
        :param graph: The full simulation graph with all node/edge attributes.
        :param events: Optional list of simulation events from this tick.
        :param session_id: Session scope (required for Postgres, optional for SQLite).
        """
        ...

    def hydrate_graph(
        self,
        tick: int | None = None,
        *,
        session_id: UUID | None = None,
    ) -> nx.DiGraph:
        """Load a complete state snapshot from storage.

        If tick is None, loads the latest available tick.

        :param tick: The tick number to load, or None for latest.
        :param session_id: Session scope.
        :returns: A fully populated NetworkX DiGraph.
        """
        ...

    def log_tick(
        self,
        tick: int,
        rng_state: bytes | None = None,
        mutations: dict | None = None,
        invariant_checks: dict | None = None,
        wall_time_ms: int | None = None,
        system_timings: dict | None = None,
        *,
        session_id: UUID | None = None,
    ) -> None:
        """Record tick replay metadata (RNG state, mutations, timings).

        :param tick: The tick number.
        :param rng_state: Serialized RNG state for deterministic replay.
        :param mutations: Summary of state mutations applied this tick.
        :param invariant_checks: Conservation checks and sum-to-one results.
        :param wall_time_ms: Total tick execution wall time in milliseconds.
        :param system_timings: Per-system execution time in milliseconds.
        :param session_id: Session scope.
        """
        ...

    def set_metadata(self, key: str, value: str) -> None:
        """Store a key-value metadata pair.

        :param key: Metadata key.
        :param value: Metadata value (serialized as string).
        """
        ...

    def get_metadata(self, key: str) -> str | None:
        """Retrieve a metadata value by key.

        :param key: Metadata key.
        :returns: The stored value, or None if not found.
        """
        ...


@runtime_checkable
class PostgresRuntimeExtensions(Protocol):
    """Extended methods specific to PostgresRuntime.

    These methods persist subsystems that were added after the original
    RuntimePersistence protocol was defined (Features 002, 022, 029,
    032, 036). The Simulation class accesses these through the concrete
    PostgresRuntime type, not the base protocol.
    """

    def persist_graph_metadata(
        self,
        tick: int,
        economy: dict,
        state_finances: dict,
        tick_dynamics: dict | None,
        *,
        session_id: UUID,
    ) -> None:
        """Persist graph-level metadata (economy, state finances, tick dynamics).

        :param tick: The tick number.
        :param economy: GlobalEconomy.model_dump().
        :param state_finances: {state_id: StateFinance.model_dump()}.
        :param tick_dynamics: NationalTickParameters + SmoothedCoefficients, or None.
        :param session_id: Session scope.
        """
        ...

    def persist_community_state(
        self,
        tick: int,
        community_states: dict,
        memberships: list[dict],
        *,
        session_id: UUID,
    ) -> None:
        """Persist hypergraph community state and membership records.

        :param tick: The tick number.
        :param community_states: {CommunityType: CommunityState dict}.
        :param memberships: List of CommunityMembership dicts.
        :param session_id: Session scope.
        """
        ...

    def hydrate_community_state(
        self,
        tick: int,
        *,
        session_id: UUID,
    ) -> tuple[dict, list[dict]]:
        """Load community state and memberships at a specific tick.

        :param tick: The tick number.
        :param session_id: Session scope.
        :returns: Tuple of (community_states dict, memberships list).
        """
        ...

    def persist_hex_state(
        self,
        tick: int,
        hex_states: list[dict],
        *,
        session_id: UUID,
    ) -> None:
        """Persist per-hex economic state. Bulk insert ~1,500 rows.

        :param tick: The tick number.
        :param hex_states: List of HexEconomicState dicts.
        :param session_id: Session scope.
        """
        ...

    def persist_infrastructure_state(
        self,
        tick: int,
        terrain_states: list[dict],
        link_states: list[dict],
        *,
        session_id: UUID,
    ) -> None:
        """Persist Feature 036 infrastructure topology state.

        :param tick: The tick number.
        :param terrain_states: Per-hex terrain + biocapacity + internet state.
        :param link_states: Per-edge infrastructure link state.
        :param session_id: Session scope.
        """
        ...

    def persist_contradiction_fields(
        self,
        tick: int,
        fields: list[dict],
        curvatures: list[dict],
        *,
        session_id: UUID,
    ) -> None:
        """Persist Feature 002 contradiction field values and edge curvatures.

        :param tick: The tick number.
        :param fields: Per-node field values with derivatives.
        :param curvatures: Per-edge Ollivier-Ricci curvature values.
        :param session_id: Session scope.
        """
        ...

    def persist_action_results(
        self,
        tick: int,
        results: list[dict],
        *,
        session_id: UUID,
    ) -> None:
        """Persist OODA action resolution outcomes (Feature 032).

        :param tick: The tick number.
        :param results: List of action result dicts.
        :param session_id: Session scope.
        """
        ...

    def persist_tick_summary(
        self,
        tick: int,
        summary: dict,
        *,
        session_id: UUID,
    ) -> None:
        """Persist pre-aggregated tick summary for time-series endpoints.

        :param tick: The tick number.
        :param summary: Aggregated metrics dict.
        :param session_id: Session scope.
        """
        ...

    def persist_traces(
        self,
        session_id: UUID,
        tick: int,
        trace_events: list[dict],
    ) -> None:
        """Bulk insert trace events to trace_log.

        Called by TraceRecorder.flush() after tick completion.

        :param session_id: Session scope.
        :param tick: The tick number.
        :param trace_events: List of structured trace event dicts.
        """
        ...

    def create_session_partition(self, session_id: UUID) -> None:
        """Create a trace_log partition for a new session.

        Called when a session is created with trace_level != NONE.

        :param session_id: Session to partition.
        """
        ...

    def drop_session_partition(self, session_id: UUID) -> None:
        """Drop a trace_log partition for a completed/archived session.

        Instant cleanup with zero dead tuples.

        :param session_id: Session to clean up.
        """
        ...

    def export_session_to_parquet(
        self,
        session_id: UUID,
        output_dir: str,
    ) -> list[str]:
        """Export all session data to Parquet files.

        :param session_id: Session to export.
        :param output_dir: Directory for Parquet output files.
        :returns: List of generated Parquet file paths.
        """
        ...
