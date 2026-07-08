"""Unit tests for PostgresRuntime (mocked psycopg).

Tests verify SQL parameter construction, UPSERT semantics, session isolation,
and JSONB serialization without requiring a live PostgreSQL instance.

Phase 3 (T011-T013, T015-T024): State persistence and hydration tests.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import networkx as nx
import pytest

from babylon.engine.graph import BabylonGraph
from babylon.persistence.postgres_runtime import PostgresRuntime

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def session_id() -> UUID:
    """Stable session ID for tests."""
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture()
def mock_cursor() -> MagicMock:
    """Mock psycopg cursor with dict_row support."""
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchone = MagicMock(return_value=None)
    cursor.fetchall = MagicMock(return_value=[])
    cursor.rowcount = 0
    return cursor


@pytest.fixture()
def mock_conn(mock_cursor: MagicMock) -> MagicMock:
    """Mock psycopg connection with cursor and transaction support."""
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor = MagicMock(return_value=mock_cursor)

    @contextmanager
    def mock_transaction() -> Any:
        yield

    conn.transaction = mock_transaction
    return conn


@pytest.fixture()
def mock_pool(mock_conn: MagicMock) -> MagicMock:
    """Mock psycopg ConnectionPool."""
    pool = MagicMock()

    @contextmanager
    def mock_connection() -> Any:
        yield mock_conn

    pool.connection = mock_connection
    return pool


@pytest.fixture()
def runtime(mock_pool: MagicMock) -> PostgresRuntime:
    """PostgresRuntime with mocked pool."""
    return PostgresRuntime(mock_pool)


def _build_graph(
    nodes: dict[str, dict[str, Any]] | None = None,
    edges: list[tuple[str, str, dict[str, Any]]] | None = None,
) -> nx.DiGraph[str]:
    """Build a test graph."""
    graph = BabylonGraph()
    if nodes:
        for node_id, attrs in nodes.items():
            graph.add_node(node_id, **attrs)
    if edges:
        for source, target, attrs in edges:
            graph.add_edge(source, target, **attrs)
    return graph


# ══════════════════════════════════════════════════════════════════════
# T011: persist_tick — node_state + edge_state inserts
# ══════════════════════════════════════════════════════════════════════


class TestPersistTick:
    """Tests for PostgresRuntime.persist_tick()."""

    def test_requires_session_id(self, runtime: PostgresRuntime) -> None:
        """persist_tick raises ValueError when session_id is None."""
        graph = _build_graph()
        with pytest.raises(ValueError, match="session_id is required"):
            runtime.persist_tick(tick=0, graph=graph)

    def test_persists_social_class_nodes(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """persist_tick writes SocialClass nodes with promoted columns."""
        graph = _build_graph(
            nodes={
                "worker_1": {
                    "type": "SocialClass",
                    "wealth": 50.0,
                    "ideology": {"class_consciousness": 0.3},
                    "organization": 0.5,
                    "class_position": "proletariat",
                },
            }
        )
        runtime.persist_tick(tick=0, graph=graph, session_id=session_id)

        # Verify executemany was called for nodes
        assert mock_cursor.executemany.called
        node_call = mock_cursor.executemany.call_args_list[0]
        sql = node_call[0][0]
        rows = node_call[0][1]

        assert "INSERT INTO node_state" in sql
        assert "ON CONFLICT" in sql
        assert len(rows) == 1

        row = rows[0]
        assert row[0] == session_id  # session_id
        assert row[1] == 0  # tick
        assert row[2] == "worker_1"  # node_id
        assert row[3] == "SocialClass"  # node_type
        # row[4] is JSON attributes
        attrs = json.loads(row[4])
        assert attrs["wealth"] == 50.0
        # Promoted columns
        assert row[5] == 50.0  # wealth
        assert row[6] == 0.3  # consciousness (from ideology dict)
        assert row[7] == 0.5  # organization_level
        assert row[8] == "proletariat"  # class_position

    def test_persists_territory_nodes(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """persist_tick writes Territory nodes with promoted columns."""
        graph = _build_graph(
            nodes={
                "detroit": {
                    "type": "Territory",
                    "population": 670000,
                    "profit_rate": 0.15,
                    "sector_type": "MANUFACTURING",
                },
            }
        )
        runtime.persist_tick(tick=0, graph=graph, session_id=session_id)

        node_call = mock_cursor.executemany.call_args_list[0]
        rows = node_call[0][1]
        row = rows[0]

        assert row[3] == "Territory"
        assert row[9] == 670000  # population
        assert row[10] == 0.15  # profit_rate
        assert row[11] == "MANUFACTURING"  # sector_type

    def test_persists_organization_nodes(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """persist_tick writes Organization nodes with promoted columns."""
        graph = _build_graph(
            nodes={
                "org_1": {
                    "type": "Organization",
                    "org_type": "POLITICAL_FACTION",
                    "class_character": "proletarian",
                    "cohesion": 0.8,
                    "legal_standing": "LEGAL",
                    "is_institution": False,
                },
            }
        )
        runtime.persist_tick(tick=0, graph=graph, session_id=session_id)

        node_call = mock_cursor.executemany.call_args_list[0]
        rows = node_call[0][1]
        row = rows[0]

        assert row[3] == "Organization"
        assert row[12] == "POLITICAL_FACTION"  # org_type
        assert row[13] == "proletarian"  # class_character
        assert row[14] == 0.8  # cohesion
        assert row[15] == "LEGAL"  # legal_standing
        assert row[16] is False  # is_institution

    def test_persists_edges(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """persist_tick writes edges with promoted columns."""
        graph = _build_graph(
            nodes={"a": {"type": "SocialClass"}, "b": {"type": "SocialClass"}},
            edges=[
                (
                    "a",
                    "b",
                    {
                        "type": "EXPLOITATION",
                        "edge_mode": "DIRECT",
                        "value_flow": 100.0,
                        "tension": 0.7,
                        "solidarity_strength": None,
                        "weight": 1.5,
                    },
                ),
            ],
        )
        runtime.persist_tick(tick=0, graph=graph, session_id=session_id)

        # Second executemany call is for edges
        edge_call = mock_cursor.executemany.call_args_list[1]
        sql = edge_call[0][0]
        rows = edge_call[0][1]

        assert "INSERT INTO edge_state" in sql
        assert len(rows) == 1

        row = rows[0]
        assert row[0] == session_id
        assert row[2] == "a"  # source
        assert row[3] == "b"  # target
        assert row[4] == "EXPLOITATION"  # edge_type
        assert row[5] == "DIRECT"  # edge_mode
        assert row[7] == 100.0  # value_flow
        assert row[8] == 0.7  # tension
        assert row[9] is None  # solidarity_strength
        assert row[10] == 1.5  # weight

    def test_persists_events(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """persist_tick writes simulation events."""
        events = [
            {
                "type": "UPRISING",
                "entity_id": "worker_1",
                "community_type": "NEIGHBORHOOD",
                "message": "Workers revolt!",
            },
        ]
        # Need both nodes and edges for predictable call ordering
        graph = _build_graph(
            nodes={
                "worker_1": {"type": "SocialClass"},
                "boss_1": {"type": "SocialClass"},
            },
            edges=[("worker_1", "boss_1", {"type": "EXPLOITATION"})],
        )
        runtime.persist_tick(tick=5, graph=graph, events=events, session_id=session_id)

        # With nodes + edges + events, we get 3 executemany calls
        assert mock_cursor.executemany.call_count == 3
        event_call = mock_cursor.executemany.call_args_list[2]
        sql = event_call[0][0]
        rows = event_call[0][1]

        assert "INSERT INTO simulation_event" in sql
        assert len(rows) == 1
        assert rows[0][2] == "UPRISING"  # event_type
        assert rows[0][3] == "worker_1"  # entity_id

    def test_persists_events_with_datetime_timestamp(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """Bug P0 #6: datetime timestamps must not crash canonicalization.

        ``_canonical_payload`` runs before any DB access (``persist_tick``
        computes it unconditionally), so the mocked pool is sufficient to
        reproduce the TypeError.
        """
        events = [
            {"type": "UPRISING", "entity_id": "w1", "timestamp": datetime(2026, 7, 8, 1, 0)},
        ]
        graph = _build_graph(nodes={"w1": {"type": "SocialClass"}})
        runtime.persist_tick(tick=5, graph=graph, events=events, session_id=session_id)

        # Stored details keep the timestamp (isoformat via _json_default)
        rows = mock_cursor.executemany.call_args_list[-1][0][1]
        assert json.loads(rows[0][5])["timestamp"] == "2026-07-08T01:00:00"

    def test_retry_with_regenerated_timestamp_is_idempotent(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """Spec-056 B': a retry differing only in event wall-clock timestamps
        must return silently, not raise MonotonicityViolationError.

        Stored-side exclusion: fetchone → tick exists; fetchall feeds
        ``_canonical_payload_for_tick`` (nodes, edges, events in that order).
        """
        mock_cursor.fetchone.return_value = (1,)
        mock_cursor.fetchall.side_effect = [
            [],  # node_state rows
            [],  # edge_state rows
            [
                {
                    "details": {
                        "type": "UPRISING",
                        "entity_id": "w1",
                        "timestamp": "2026-07-08T01:00:00",
                    }
                }
            ],
        ]
        events = [
            # DIFFERENT wall clock than the stored row above
            {"type": "UPRISING", "entity_id": "w1", "timestamp": datetime(2026, 7, 8, 1, 5)},
        ]
        # Empty graph so the node/edge canonical sides are trivially equal
        runtime.persist_tick(tick=5, graph=_build_graph(), events=events, session_id=session_id)

        # Idempotent return: no re-persist of nodes/edges/events
        assert mock_cursor.executemany.call_count == 0

    def test_no_events_skips_event_insert(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """persist_tick skips event insert when events is None."""
        # Graph with nodes + edges to get 2 executemany calls
        graph = _build_graph(
            nodes={"a": {"type": "SocialClass"}, "b": {"type": "SocialClass"}},
            edges=[("a", "b", {"type": "EXPLOITATION"})],
        )
        runtime.persist_tick(tick=0, graph=graph, session_id=session_id)

        # 2 executemany calls (nodes + edges), not 3 (no events)
        assert mock_cursor.executemany.call_count == 2

    def test_empty_graph_skips_inserts(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """persist_tick with empty graph produces no executemany calls."""
        graph = _build_graph()
        runtime.persist_tick(tick=0, graph=graph, session_id=session_id)

        assert mock_cursor.executemany.call_count == 0

    def test_non_serializable_attrs_filtered(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """persist_tick filters non-JSON-serializable attributes."""
        graph = _build_graph(
            nodes={
                "a": {
                    "type": "SocialClass",
                    "wealth": 10.0,
                    "callback": lambda x: x,  # Not serializable
                },
            }
        )
        runtime.persist_tick(tick=0, graph=graph, session_id=session_id)

        node_call = mock_cursor.executemany.call_args_list[0]
        rows = node_call[0][1]
        attrs = json.loads(rows[0][4])

        assert "wealth" in attrs
        assert "callback" not in attrs

    def test_unknown_node_type_null_promoted_columns(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """Nodes with unknown type have all promoted columns as None."""
        graph = _build_graph(nodes={"x": {"type": "CustomType", "foo": "bar"}})
        runtime.persist_tick(tick=0, graph=graph, session_id=session_id)

        node_call = mock_cursor.executemany.call_args_list[0]
        rows = node_call[0][1]
        row = rows[0]

        # Promoted columns (indices 5-16) should all be None
        for i in range(5, 17):
            assert row[i] is None, f"Promoted column at index {i} should be None"


# ══════════════════════════════════════════════════════════════════════
# Spec-092 review fix — idempotency #2: persist_tick_events deletes
# existing (game_id, tick) rows before inserting, so a repeated
# resolve_tick() call for the same tick doesn't duplicate tick_event rows.
# ══════════════════════════════════════════════════════════════════════


class TestPersistTickEvents:
    """Tests for PostgresRuntime.persist_tick_events()."""

    def test_deletes_before_insert_for_idempotency(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """Each call issues a DELETE for (game_id, tick) before the INSERT,
        so a repeated call with the same tick doesn't duplicate rows."""
        events = [
            {
                "event_type": "uprising",
                "severity": "critical",
                "summary": "Workers rose up",
            },
        ]

        runtime.persist_tick_events(session_id, 5, events)

        assert mock_cursor.execute.call_count == 1
        delete_sql, delete_params = mock_cursor.execute.call_args_list[0][0]
        assert "DELETE FROM tick_event" in delete_sql
        assert delete_params == (session_id, 5)

        assert mock_cursor.executemany.call_count == 1
        insert_sql = mock_cursor.executemany.call_args_list[0][0][0]
        assert "INSERT INTO tick_event" in insert_sql

    def test_empty_events_still_deletes_stale_rows(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """A retry that now computes zero events must still clear any
        rows a prior attempt for the same tick left behind."""
        runtime.persist_tick_events(session_id, 5, [])

        assert mock_cursor.execute.call_count == 1
        assert "DELETE FROM tick_event" in mock_cursor.execute.call_args_list[0][0][0]
        assert mock_cursor.executemany.call_count == 0

    def test_shared_cursor_path_also_deletes_before_insert(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """The `_cursor` path (used by persist_full_tick) is idempotent too."""
        events = [{"event_type": "wage_payment", "severity": "informational", "summary": "Paid"}]

        runtime.persist_tick_events(session_id, 2, events, _cursor=mock_cursor)

        assert mock_cursor.execute.call_count == 1
        assert "DELETE FROM tick_event" in mock_cursor.execute.call_args_list[0][0][0]
        assert mock_cursor.executemany.call_count == 1


# ══════════════════════════════════════════════════════════════════════
# T012: hydrate_graph — graph reconstruction + JSONB round-trip
# ══════════════════════════════════════════════════════════════════════


class TestHydrateGraph:
    """Tests for PostgresRuntime.hydrate_graph()."""

    def test_requires_session_id(self, runtime: PostgresRuntime) -> None:
        """hydrate_graph raises ValueError when session_id is None."""
        with pytest.raises(ValueError, match="session_id is required"):
            runtime.hydrate_graph(tick=0)

    def test_hydrates_nodes_from_attributes(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """hydrate_graph reconstructs nodes from JSONB attributes."""
        mock_cursor.fetchall.side_effect = [
            # Nodes query
            [
                {
                    "node_id": "worker_1",
                    "node_type": "SocialClass",
                    "attributes": {"wealth": 50.0, "organization": 0.5},
                },
            ],
            # Edges query
            [],
        ]

        graph = runtime.hydrate_graph(tick=0, session_id=session_id)

        assert "worker_1" in graph.nodes
        assert graph.nodes["worker_1"]["_node_type"] == "SocialClass"
        assert graph.nodes["worker_1"]["wealth"] == 50.0
        assert graph.nodes["worker_1"]["organization"] == 0.5

    def test_hydrates_edges(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """hydrate_graph reconstructs edges with attributes."""
        mock_cursor.fetchall.side_effect = [
            # Nodes
            [
                {"node_id": "a", "node_type": "SocialClass", "attributes": {}},
                {"node_id": "b", "node_type": "SocialClass", "attributes": {}},
            ],
            # Edges
            [
                {
                    "source_id": "a",
                    "target_id": "b",
                    "edge_type": "EXPLOITATION",
                    "attributes": {"value_flow": 100.0},
                },
            ],
        ]

        graph = runtime.hydrate_graph(tick=0, session_id=session_id)

        assert graph.has_edge("a", "b")
        edge_data = graph.edges["a", "b"]
        assert edge_data["edge_type"] == "EXPLOITATION"
        assert edge_data["value_flow"] == 100.0

    def test_hydrates_latest_tick_when_none(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """hydrate_graph queries MAX(tick) when tick is None."""
        mock_cursor.fetchone.return_value = {"max_tick": 5}
        mock_cursor.fetchall.side_effect = [
            [{"node_id": "a", "node_type": "SocialClass", "attributes": {}}],
            [],
        ]

        graph = runtime.hydrate_graph(tick=None, session_id=session_id)

        assert "a" in graph.nodes
        # Verify the MAX query was made
        max_call = mock_cursor.execute.call_args_list[0]
        assert "MAX(tick)" in max_call[0][0]

    def test_hydrates_empty_graph_when_no_data(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """hydrate_graph returns empty graph when no ticks exist."""
        mock_cursor.fetchone.return_value = {"max_tick": None}

        graph = runtime.hydrate_graph(tick=None, session_id=session_id)

        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_attributes_not_dict_treated_as_empty(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """Non-dict attributes are treated as empty dict."""
        mock_cursor.fetchall.side_effect = [
            [{"node_id": "a", "node_type": "SocialClass", "attributes": "not_a_dict"}],
            [],
        ]

        graph = runtime.hydrate_graph(tick=0, session_id=session_id)

        assert "a" in graph.nodes
        assert graph.nodes["a"]["_node_type"] == "SocialClass"

    def test_jsonb_round_trip_fidelity(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """Verify complex nested data survives JSONB round-trip."""
        original_attrs = {
            "wealth": 42.5,
            "ideology": {
                "class_consciousness": 0.7,
                "revolutionary_potential": 0.3,
            },
            "history": [1, 2, 3],
            "nullable_field": None,
        }

        mock_cursor.fetchall.side_effect = [
            [
                {
                    "node_id": "complex_node",
                    "node_type": "SocialClass",
                    "attributes": original_attrs,
                }
            ],
            [],
        ]

        graph = runtime.hydrate_graph(tick=0, session_id=session_id)

        hydrated = graph.nodes["complex_node"]
        assert hydrated["wealth"] == original_attrs["wealth"]
        assert hydrated["ideology"] == original_attrs["ideology"]
        assert hydrated["history"] == original_attrs["history"]
        assert hydrated["nullable_field"] is None


# ══════════════════════════════════════════════════════════════════════
# T013: Extended persistence methods (graph_metadata, community, hex,
#       infrastructure, contradiction)
# ══════════════════════════════════════════════════════════════════════


class TestPersistGraphMetadata:
    """Tests for persist_graph_metadata."""

    def test_inserts_graph_metadata(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_conn: MagicMock,
    ) -> None:
        """persist_graph_metadata writes economy, state_finances, tick_dynamics."""
        economy = {"total_c": 1000.0, "total_v": 500.0}
        state_finances = {"tax_revenue": 200.0}
        tick_dynamics = {"profit_rate": 0.15}

        runtime.persist_graph_metadata(
            tick=0,
            economy=economy,
            state_finances=state_finances,
            tick_dynamics=tick_dynamics,
            session_id=session_id,
        )

        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0]
        sql = call_args[0]
        params = call_args[1]

        assert "INSERT INTO graph_metadata" in sql
        assert "ON CONFLICT" in sql
        assert params[0] == session_id
        assert params[1] == 0
        assert json.loads(params[2]) == economy
        assert json.loads(params[3]) == state_finances
        assert json.loads(params[4]) == tick_dynamics

    def test_null_tick_dynamics(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_conn: MagicMock,
    ) -> None:
        """persist_graph_metadata handles None tick_dynamics."""
        runtime.persist_graph_metadata(
            tick=0,
            economy={"x": 1},
            state_finances={"y": 2},
            tick_dynamics=None,
            session_id=session_id,
        )

        params = mock_conn.execute.call_args[0][1]
        assert params[4] is None  # tick_dynamics is None


class TestPersistCommunityState:
    """Tests for persist_community_state."""

    def test_persists_community_state_and_memberships(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """persist_community_state writes both community and membership rows."""
        community_states = {
            "NEIGHBORHOOD": {
                "category": "SPATIAL",
                "heat": 0.3,
                "cohesion": 0.7,
            },
        }
        memberships = [
            {
                "agent_id": "worker_1",
                "community_type": "NEIGHBORHOOD",
                "role": "MEMBER",
                "strength": 0.8,
            },
        ]

        runtime.persist_community_state(
            tick=0,
            community_states=community_states,
            memberships=memberships,
            session_id=session_id,
        )

        # First execute is community_state
        community_call = mock_cursor.execute.call_args_list[0]
        assert "INSERT INTO community_state" in community_call[0][0]

        # Second call is membership executemany
        membership_call = mock_cursor.executemany.call_args_list[0]
        assert "INSERT INTO community_membership" in membership_call[0][0]
        assert len(membership_call[0][1]) == 1

    def test_empty_memberships_skips_executemany(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """persist_community_state skips membership insert when empty."""
        runtime.persist_community_state(
            tick=0,
            community_states={"NEIGHBORHOOD": {"category": "SPATIAL"}},
            memberships=[],
            session_id=session_id,
        )

        assert mock_cursor.executemany.call_count == 0


class TestPersistHexState:
    """Tests for persist_hex_state."""

    def test_persists_hex_state_batch(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """persist_hex_state writes hex economic data via executemany."""
        hex_states = [
            {
                "h3_index": "872830828ffffff",
                "constant_capital": 1000.0,
                "variable_capital": 500.0,
                "surplus_value": 200.0,
                "employment": 50000,
            },
            {
                "h3_index": "872830829ffffff",
                "constant_capital": 2000.0,
                "variable_capital": 800.0,
            },
        ]

        runtime.persist_hex_state(tick=0, hex_states=hex_states, session_id=session_id)

        assert mock_cursor.executemany.called
        call_args = mock_cursor.executemany.call_args
        sql = call_args[0][0]
        rows = call_args[0][1]

        assert "INSERT INTO hex_state" in sql
        assert len(rows) == 2
        assert rows[0][2] == "872830828ffffff"

    def test_empty_hex_states_is_noop(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """persist_hex_state returns early on empty list."""
        runtime.persist_hex_state(tick=0, hex_states=[], session_id=session_id)
        assert mock_cursor.executemany.call_count == 0


class TestPersistInfrastructureState:
    """Tests for persist_infrastructure_state."""

    def test_persists_terrain_and_links(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """persist_infrastructure_state writes terrain + link rows."""
        terrain_states = [
            {
                "h3_index": "872830828ffffff",
                "terrain_type": "URBAN",
                "internet_access": True,
                "internet_quality": 0.9,
            },
        ]
        link_states = [
            {
                "source_h3": "872830828ffffff",
                "target_h3": "872830829ffffff",
                "link_id": "link_001",
                "infra_type": "ROAD",
                "condition": 0.8,
            },
        ]

        runtime.persist_infrastructure_state(
            tick=0,
            terrain_states=terrain_states,
            link_states=link_states,
            session_id=session_id,
        )

        assert mock_cursor.executemany.call_count == 2

    def test_skips_empty_terrain_and_links(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """persist_infrastructure_state skips executemany on empty lists."""
        runtime.persist_infrastructure_state(
            tick=0,
            terrain_states=[],
            link_states=[],
            session_id=session_id,
        )

        assert mock_cursor.executemany.call_count == 0


class TestPersistContradictionFields:
    """Tests for persist_contradiction_fields."""

    def test_persists_fields_and_curvatures(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """persist_contradiction_fields writes field values and edge curvatures."""
        fields = [
            {
                "node_id": "worker_1",
                "field_name": "exploitation_tension",
                "value": 0.75,
                "laplacian": -0.1,
                "dt": 0.05,
                "d2t": 0.01,
            },
        ]
        curvatures = [
            {
                "source_id": "a",
                "target_id": "b",
                "curvature": -1.5,
                "gradient": [0.1, 0.2, 0.3],
            },
        ]

        runtime.persist_contradiction_fields(
            tick=0, fields=fields, curvatures=curvatures, session_id=session_id
        )

        assert mock_cursor.executemany.call_count == 2

        # Fields
        field_call = mock_cursor.executemany.call_args_list[0]
        assert "INSERT INTO contradiction_field" in field_call[0][0]
        field_rows = field_call[0][1]
        assert len(field_rows) == 1
        assert field_rows[0][4] == 0.75  # value

        # Curvatures
        curvature_call = mock_cursor.executemany.call_args_list[1]
        assert "INSERT INTO edge_curvature" in curvature_call[0][0]
        curvature_rows = curvature_call[0][1]
        assert curvature_rows[0][4] == -1.5  # curvature
        # gradient is JSON-serialized
        assert json.loads(curvature_rows[0][5]) == [0.1, 0.2, 0.3]

    def test_skips_empty_fields_and_curvatures(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_cursor: MagicMock,
    ) -> None:
        """persist_contradiction_fields skips on empty lists."""
        runtime.persist_contradiction_fields(
            tick=0, fields=[], curvatures=[], session_id=session_id
        )
        assert mock_cursor.executemany.call_count == 0


# ══════════════════════════════════════════════════════════════════════
# T021: log_tick + persist_tick_summary
# ══════════════════════════════════════════════════════════════════════


class TestLogTick:
    """Tests for log_tick."""

    def test_log_tick_writes_tick_log(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_conn: MagicMock,
    ) -> None:
        """log_tick inserts rng_state, mutations, invariant_checks, system_timings."""
        runtime.log_tick(
            tick=0,
            rng_state=b"\x01\x02\x03",
            mutations={"node_a": {"wealth": 100}},
            invariant_checks={"conservation": True},
            wall_time_ms=42,
            system_timings={"EconomicSystem": 15, "SolidaritySystem": 10},
            session_id=session_id,
        )

        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0]
        sql = call_args[0]
        params = call_args[1]

        assert "INSERT INTO tick_log" in sql
        assert params[0] == session_id
        assert params[1] == 0  # tick
        assert params[2] == b"\x01\x02\x03"  # rng_state
        assert json.loads(params[3]) == {"node_a": {"wealth": 100}}  # mutations_json
        assert json.loads(params[4]) == {"conservation": True}  # invariant_checks
        # system_timings is at index 5, wall_time_ms at index 6
        assert json.loads(params[5]) == {"EconomicSystem": 15, "SolidaritySystem": 10}
        assert params[6] == 42  # wall_time_ms

    def test_log_tick_requires_session_id(
        self,
        runtime: PostgresRuntime,
    ) -> None:
        """log_tick raises ValueError when session_id is None."""
        with pytest.raises(ValueError, match="session_id is required"):
            runtime.log_tick(tick=0)


class TestPersistTickSummary:
    """Tests for persist_tick_summary."""

    def test_persists_tick_summary(
        self,
        runtime: PostgresRuntime,
        session_id: UUID,
        mock_conn: MagicMock,
    ) -> None:
        """persist_tick_summary writes summary metrics."""
        summary = {
            "year": 2025,
            "total_c": 10000.0,
            "total_v": 5000.0,
            "total_s": 3000.0,
            "exploitation_rate": 0.6,
            "profit_rate": 0.2,
            "imperial_rent": 1500.0,
            "avg_consciousness": 0.3,
            "solidarity_edge_count": 42,
            "antagonistic_edge_count": 15,
            "co_optive_edge_count": 5,
            "org_count": 10,
            "player_org_count": 3,
            "uprising_count": 2,
            "repression_count": 1,
            "conservation_check": True,
        }

        runtime.persist_tick_summary(tick=0, summary=summary, session_id=session_id)

        mock_conn.execute.assert_called_once()
        sql = mock_conn.execute.call_args[0][0]
        assert "INSERT INTO tick_summary" in sql
        assert "ON CONFLICT" in sql


# ══════════════════════════════════════════════════════════════════════
# T022: set_metadata / get_metadata
# ══════════════════════════════════════════════════════════════════════


class TestMetadata:
    """Tests for set_metadata / get_metadata.

    Metadata is stored as JSONB in tick_log at tick=-1 using a sentinel
    session UUID (all zeros). Key-value pairs accumulate via JSONB ||.
    """

    _SENTINEL = UUID("00000000-0000-0000-0000-000000000000")

    def test_set_metadata_writes_value(
        self,
        runtime: PostgresRuntime,
        mock_conn: MagicMock,
    ) -> None:
        """set_metadata upserts key-value as JSONB in tick_log."""
        runtime.set_metadata("scenario_name", "detroit_collapse")

        mock_conn.execute.assert_called_once()
        sql = mock_conn.execute.call_args[0][0]
        params = mock_conn.execute.call_args[0][1]

        assert "INSERT INTO tick_log" in sql
        assert "mutations_json" in sql
        assert params[0] == self._SENTINEL
        stored_json = json.loads(params[1])
        assert stored_json == {"scenario_name": "detroit_collapse"}

    def test_get_metadata_returns_value(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """get_metadata returns stored value from JSONB."""
        mock_cursor.fetchone.return_value = {
            "mutations_json": {"scenario_name": "detroit_collapse", "version": "1.0"}
        }

        result = runtime.get_metadata("scenario_name")
        assert result == "detroit_collapse"

    def test_get_metadata_returns_none_for_missing_key(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """get_metadata returns None when key not in JSONB."""
        mock_cursor.fetchone.return_value = {"mutations_json": {"other_key": "other_value"}}

        result = runtime.get_metadata("nonexistent")
        assert result is None

    def test_get_metadata_returns_none_when_no_row(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """get_metadata returns None when no metadata row exists."""
        mock_cursor.fetchone.return_value = None

        result = runtime.get_metadata("anything")
        assert result is None

    def test_get_metadata_handles_string_json(
        self,
        runtime: PostgresRuntime,
        mock_cursor: MagicMock,
    ) -> None:
        """get_metadata handles mutations_json returned as string."""
        mock_cursor.fetchone.return_value = {
            "mutations_json": '{"scenario_name": "detroit_collapse"}'
        }

        result = runtime.get_metadata("scenario_name")
        assert result == "detroit_collapse"


# ══════════════════════════════════════════════════════════════════════
# T025: PersistenceObserver
# ══════════════════════════════════════════════════════════════════════


class TestPersistenceObserver:
    """Tests for PersistenceObserver integration.

    Uses pytest.importorskip to gracefully skip if the engine import chain
    has issues unrelated to the persistence module.
    """

    @staticmethod
    def _import_observer() -> type:
        """Import PersistenceObserver, skipping on unrelated import errors."""
        try:
            from babylon.engine.observers.persistence_observer import (
                PersistenceObserver,
            )

            return PersistenceObserver
        except ImportError as e:
            pytest.skip(f"PersistenceObserver import chain broken: {e}")

    def test_observer_calls_persist_tick(self) -> None:
        """PersistenceObserver.on_tick calls persist_tick on backend."""
        PersistenceObserver = self._import_observer()
        from babylon.persistence.protocols import RuntimePersistence

        mock_persistence = MagicMock(spec=RuntimePersistence)
        observer = PersistenceObserver(
            persistence=mock_persistence,
            session_id=uuid4(),
        )

        from tests.factories import DomainFactory

        factory = DomainFactory()
        state = factory.create_world_state()

        observer.on_tick(previous_state=state, new_state=state)

        mock_persistence.persist_tick.assert_called_once()

    def test_observer_flushes_tracer(self) -> None:
        """PersistenceObserver flushes TraceRecorder after persist."""
        PersistenceObserver = self._import_observer()
        from babylon.persistence.protocols import RuntimePersistence, TraceCollector

        mock_persistence = MagicMock(spec=RuntimePersistence)
        mock_tracer = MagicMock(spec=TraceCollector)
        sid = uuid4()

        observer = PersistenceObserver(
            persistence=mock_persistence,
            session_id=sid,
            tracer=mock_tracer,
        )

        from tests.factories import DomainFactory

        factory = DomainFactory()
        state = factory.create_world_state()

        observer.on_tick(previous_state=state, new_state=state)

        mock_tracer.flush.assert_called_once_with(sid, state.tick)


# ══════════════════════════════════════════════════════════════════════
# Helpers / _extract_promoted_columns
# ══════════════════════════════════════════════════════════════════════


class TestExtractPromotedColumns:
    """Tests for _extract_promoted_columns static method."""

    def test_social_class_extracts_wealth_consciousness(self) -> None:
        """SocialClass type extracts wealth, consciousness, organization, class_position."""
        result = PostgresRuntime._extract_promoted_columns(
            "SocialClass",
            {
                "wealth": 100.0,
                "ideology": {"class_consciousness": 0.5},
                "organization": 0.8,
                "class_position": "proletariat",
            },
        )
        assert result[0] == 100.0  # wealth
        assert result[1] == 0.5  # consciousness
        assert result[2] == 0.8  # organization_level
        assert result[3] == "proletariat"  # class_position

    def test_territory_extracts_population(self) -> None:
        """Territory type extracts population, profit_rate, sector_type."""
        result = PostgresRuntime._extract_promoted_columns(
            "Territory",
            {"population": 500000, "profit_rate": 0.12, "sector_type": "SERVICE"},
        )
        assert result[4] == 500000  # population
        assert result[5] == 0.12  # profit_rate
        assert result[6] == "SERVICE"  # sector_type

    def test_organization_extracts_org_type(self) -> None:
        """Organization type extracts org_type, class_character, cohesion, legal, institution."""
        result = PostgresRuntime._extract_promoted_columns(
            "Organization",
            {
                "org_type": "UNION",
                "class_character": "proletarian",
                "cohesion": 0.9,
                "legal_standing": "BANNED",
                "is_institution": True,
            },
        )
        assert result[7] == "UNION"
        assert result[8] == "proletarian"
        assert result[9] == 0.9
        assert result[10] == "BANNED"
        assert result[11] is True

    def test_unknown_type_returns_all_none(self) -> None:
        """Unknown node type returns 12-tuple of None."""
        result = PostgresRuntime._extract_promoted_columns("UnknownType", {"some_attr": "value"})
        assert all(v is None for v in result)
        assert len(result) == 12

    def test_snake_case_type_aliases(self) -> None:
        """snake_case type aliases work (social_class, territory, organization)."""
        result = PostgresRuntime._extract_promoted_columns("social_class", {"wealth": 10.0})
        assert result[0] == 10.0

        result = PostgresRuntime._extract_promoted_columns("territory", {"population": 100})
        assert result[4] == 100

        result = PostgresRuntime._extract_promoted_columns("organization", {"org_type": "STATE"})
        assert result[7] == "STATE"


class TestMakeSerializable:
    """Tests for _make_serializable static method."""

    def test_filters_non_serializable(self) -> None:
        """_make_serializable removes non-JSON-serializable values."""
        attrs = {
            "number": 42,
            "string": "hello",
            "nested": {"a": 1},
            "lambda": lambda x: x,
            "set": {1, 2, 3},
        }
        result = PostgresRuntime._make_serializable(attrs)

        assert "number" in result
        assert "string" in result
        assert "nested" in result
        assert "lambda" not in result
        assert "set" not in result

    def test_preserves_none_values(self) -> None:
        """_make_serializable keeps None values (JSON null)."""
        attrs = {"field": None}
        result = PostgresRuntime._make_serializable(attrs)
        assert result["field"] is None
