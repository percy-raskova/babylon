"""Spec-103: bridge method contract tests (RED phase).

Tests for ``get_trade_flows``, ``get_county_import_exposure``, and
``get_trade_panel`` — the three new EngineBridge methods that power the Wire
INDEX per-bloc lines, Territory Detail import-exposure breakdown, and Analysis
trade panel.

All methods read persisted engine state (``boundary_flow_register``,
``dynamic_external_node_state``, and spec-100's ``county_exposure_by_external``
reference table) via the persistence pool's SQL. They degrade gracefully to
``has_data: False`` when the pool is unavailable or tables are empty/absent.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID

import pytest

from game.engine_bridge import EngineBridge

pytestmark = pytest.mark.unit

_SESSION = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
_COUNTY_FIPS = "26161"  # Wayne County, MI


# ---------------------------------------------------------------------- #
# Mock helpers
# ---------------------------------------------------------------------- #


def _mock_pool_with_boundary_flows() -> MagicMock:
    """A mock persistence pool seeded with boundary_flow_register + external node rows.

    The cursor returns different row sets depending on the SQL executed —
    we inspect ``cur.execute.call_args`` to dispatch. This mirrors the real
    bridge's two-table read pattern.
    """
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cursor
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)

    # Boundary-flow series rows: (tick, source_node_id, flow_type, magnitude)
    _boundary_rows = [
        (1, "canada", "drain_edge", 100.0),
        (1, "china", "drain_edge", 250.0),
        (2, "canada", "drain_edge", 105.0),
        (2, "china", "drain_edge", 260.0),
        (1, "canada", "trade_inbound", 50.0),
        (2, "canada", "trade_inbound", 55.0),
    ]

    # External-node latest rows: (node_id, kind, phi_year_inflow, bilateral_trade_value, bilateral_trade_tons, erdi_ratio)
    _external_rows = [
        ("canada", "international", 5200.0, 8_000_000.0, 12_000.0, 1.18),
        ("china", "international", 13_000.0, 20_000_000.0, 30_000.0, 1.42),
    ]

    # County-exposure weight rows (spec-100 table — may be absent in real life)
    _exposure_rows = [
        ("canada", 0.32),
        ("china", 0.55),
    ]

    def _execute(sql, params=None):
        sql_lower = sql.lower() if isinstance(sql, str) else ""
        if "boundary_flow_register" in sql_lower and "group by flow_type" in sql_lower:
            # Flow-type totals query: (flow_type, total, tick_count)
            cursor.fetchall.return_value = [
                ("drain_edge", 715.0, 2),
                ("trade_inbound", 105.0, 2),
            ]
        elif "boundary_flow_register" in sql_lower and "dest_node_id = " in sql_lower:
            # County-filtered boundary flow query
            cursor.fetchall.return_value = [
                (1, "canada", "drain_edge", 100.0),
                (2, "canada", "drain_edge", 105.0),
                (1, "china", "drain_edge", 250.0),
                (2, "china", "drain_edge", 260.0),
            ]
        elif "boundary_flow_register" in sql_lower:
            # Per-bloc series query (no county_fips filter)
            cursor.fetchall.return_value = _boundary_rows
        elif "dynamic_external_node_state" in sql_lower:
            cursor.fetchall.return_value = _external_rows
        elif "county_exposure" in sql_lower:
            cursor.fetchall.return_value = _exposure_rows
        else:
            cursor.fetchall.return_value = []

    cursor.execute.side_effect = _execute
    pool = MagicMock()
    pool.connection.return_value = conn
    return pool


def _make_mock_persistence_with_flows() -> MagicMock:
    """Mock persistence with a pool seeded with trade/exposure data."""
    mock = MagicMock()
    mock.get_metadata.return_value = None
    mock.get_session.return_value = {"scenario": "default"}
    graph = MagicMock()
    graph.graph = {"tick": 5}
    graph.nodes.return_value = iter([])
    graph.edges = MagicMock(return_value=iter([]))
    mock.hydrate_graph.return_value = graph
    mock._pool = _mock_pool_with_boundary_flows()
    return mock


def _make_mock_persistence_no_pool() -> MagicMock:
    """Mock persistence with NO _pool (SQLite dev/test degradation case)."""
    mock = MagicMock()
    mock.get_metadata.return_value = None
    mock.get_session.return_value = {"scenario": "default"}
    graph = MagicMock()
    graph.graph = {"tick": 0}
    graph.nodes.return_value = iter([])
    graph.edges = MagicMock(return_value=iter([]))
    mock.hydrate_graph.return_value = graph
    # No _pool attribute — simulates SQLite dev/test
    if hasattr(mock, "_pool"):
        del mock._pool
    return mock


# ---------------------------------------------------------------------- #
# get_trade_flows
# ---------------------------------------------------------------------- #


class TestGetTradeFlows:
    """FR-103-01: get_trade_flows returns per-bloc price/flow lines."""

    def test_returns_well_formed_payload(self) -> None:
        mock_persistence = _make_mock_persistence_with_flows()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_trade_flows(_SESSION)

        assert "tick" in result
        assert "has_data" in result
        assert "blocs" in result
        assert isinstance(result["blocs"], list)

    def test_blocs_have_required_fields(self) -> None:
        mock_persistence = _make_mock_persistence_with_flows()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_trade_flows(_SESSION)
        assert result["has_data"] is True, "seeded pool must surface has_data"
        assert len(result["blocs"]) >= 1
        bloc = result["blocs"][0]
        assert "node_id" in bloc
        assert "label" in bloc
        assert "kind" in bloc
        assert "latest" in bloc
        assert "phi_series" in bloc
        assert "trade_series" in bloc

    def test_latest_has_external_node_fields(self) -> None:
        mock_persistence = _make_mock_persistence_with_flows()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_trade_flows(_SESSION)
        bloc = result["blocs"][0]
        latest = bloc["latest"]
        assert "phi_year_inflow" in latest
        assert "bilateral_trade_value" in latest
        assert "bilateral_trade_tons" in latest
        assert "erdi_ratio" in latest

    def test_phi_series_is_time_series(self) -> None:
        mock_persistence = _make_mock_persistence_with_flows()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_trade_flows(_SESSION)
        bloc = next(b for b in result["blocs"] if b["node_id"] == "canada")
        assert len(bloc["phi_series"]) >= 1
        point = bloc["phi_series"][0]
        assert "tick" in point
        assert "magnitude" in point

    def test_degrades_gracefully_without_pool(self) -> None:
        """When the persistence layer has no _pool (SQLite), returns has_data: False."""
        mock_persistence = _make_mock_persistence_no_pool()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_trade_flows(_SESSION)

        assert result["has_data"] is False
        assert result["blocs"] == []


# ---------------------------------------------------------------------- #
# get_county_import_exposure
# ---------------------------------------------------------------------- #


class TestGetCountyImportExposure:
    """FR-103-02: get_county_import_exposure returns provenance breakdown."""

    def test_returns_well_formed_payload(self) -> None:
        mock_persistence = _make_mock_persistence_with_flows()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_county_import_exposure(_SESSION, _COUNTY_FIPS)

        assert result["county_fips"] == _COUNTY_FIPS
        assert "has_data" in result
        assert "total_exposure" in result
        assert "breakdown" in result
        assert "citations" in result

    def test_breakdown_has_contributors(self) -> None:
        mock_persistence = _make_mock_persistence_with_flows()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_county_import_exposure(_SESSION, _COUNTY_FIPS)
        assert result["has_data"] is True, "seeded pool must surface has_data"
        breakdown = result["breakdown"]
        assert "total" in breakdown
        assert "contributors" in breakdown
        assert isinstance(breakdown["contributors"], list)
        assert len(breakdown["contributors"]) >= 1

    def test_contributors_have_source_and_children(self) -> None:
        """Each bloc contributor has a source ref and drill-down children."""
        mock_persistence = _make_mock_persistence_with_flows()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_county_import_exposure(_SESSION, _COUNTY_FIPS)
        contributor = result["breakdown"]["contributors"][0]
        assert "label" in contributor
        assert "value" in contributor
        assert "share" in contributor
        assert "source" in contributor
        assert "children" in contributor
        assert isinstance(contributor["children"], list)

    def test_children_trace_to_reference_and_dynamic_sources(self) -> None:
        """The drill-down chain ends at reference_table + dynamic_table sources."""
        mock_persistence = _make_mock_persistence_with_flows()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_county_import_exposure(_SESSION, _COUNTY_FIPS)
        contributor = result["breakdown"]["contributors"][0]
        child_kinds = {child["source"]["kind"] for child in contributor["children"]}
        # The chain must include at least a reference_table or dynamic_table source
        assert child_kinds & {"reference_table", "dynamic_table"}, (
            f"drill-down children must trace to reference/dynamic tables, got {child_kinds}"
        )

    def test_citations_carry_reference_data(self) -> None:
        """The citations array carries terminal reference-data provenance."""
        mock_persistence = _make_mock_persistence_with_flows()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_county_import_exposure(_SESSION, _COUNTY_FIPS)
        citations = result["citations"]
        assert isinstance(citations, list)
        assert len(citations) >= 1
        cite = citations[0]
        assert "id" in cite
        assert "source" in cite
        assert "table" in cite

    def test_degrades_gracefully_without_pool(self) -> None:
        """When no pool, returns has_data: False with honest zeros."""
        mock_persistence = _make_mock_persistence_no_pool()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_county_import_exposure(_SESSION, _COUNTY_FIPS)

        assert result["has_data"] is False
        assert result["total_exposure"] == 0.0
        assert result["breakdown"]["contributors"] == []


# ---------------------------------------------------------------------- #
# get_trade_panel
# ---------------------------------------------------------------------- #


class TestGetTradePanel:
    """FR-103-03: get_trade_panel returns aggregate trade panel data."""

    def test_returns_well_formed_payload(self) -> None:
        mock_persistence = _make_mock_persistence_with_flows()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_trade_panel(_SESSION)

        assert "tick" in result
        assert "has_data" in result
        assert "total_phi_inflow" in result
        assert "total_trade" in result
        assert "blocs" in result
        assert "flow_types" in result

    def test_blocs_have_totals(self) -> None:
        mock_persistence = _make_mock_persistence_with_flows()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_trade_panel(_SESSION)
        assert result["has_data"] is True
        assert len(result["blocs"]) >= 1
        bloc = result["blocs"][0]
        assert "node_id" in bloc
        assert "label" in bloc
        assert "phi_inflow" in bloc
        assert "trade" in bloc
        assert "erdi_ratio" in bloc

    def test_flow_types_have_summary(self) -> None:
        mock_persistence = _make_mock_persistence_with_flows()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_trade_panel(_SESSION)
        assert len(result["flow_types"]) >= 1
        ft = result["flow_types"][0]
        assert "flow_type" in ft
        assert "total" in ft
        assert "tick_count" in ft

    def test_degrades_gracefully_without_pool(self) -> None:
        """When no pool, returns has_data: False with honest zeros."""
        mock_persistence = _make_mock_persistence_no_pool()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_trade_panel(_SESSION)

        assert result["has_data"] is False
        assert result["total_phi_inflow"] == 0.0
        assert result["blocs"] == []
