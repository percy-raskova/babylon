"""Edges / Tension dashboard (spec-111 C2) — the anti-inert contract.

``get_edges_dashboard`` / ``_build_edges_dashboard`` aggregate every live graph
edge: counts by mechanical ``edge_type`` and dialectical ``edge_mode``, the top
edges by ``value_flow`` and by ``tension``, and SOLIDARITY-strength summary
stats. Its frontend endpoint (``edges``) was ``Untyped`` with zero consumers —
this is the "where is the class war hottest" ranked companion to the field_flow
spatial lens.

These tests PIN the dashboard as NON-EMPTY for the canonical scenario so a
future refactor can't silently regress it to an empty payload (the
legitimation-index / hypergraph-communities trap: a panel rendering over a
permanently-empty source). wayne_county seeds a dense relationship graph
(exploitation / wages / solidarity / tenancy edges — ``_legacy_wayne.py``), so
``total_edges`` is well above zero from tick 0, no year boundary required.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def _wayne_edges() -> dict[str, object]:
    from game.engine_bridge import _build_edges_dashboard, _build_initial_state_for_scenario

    state = _build_initial_state_for_scenario("wayne_county")
    return _build_edges_dashboard(state.to_graph())


class TestEdgesDashboardIsReal:
    def test_wayne_county_has_a_dense_edge_graph(self) -> None:
        dashboard = _wayne_edges()
        assert dashboard["total_edges"] > 0, "wayne_county seeds a real relationship graph"

    def test_counts_by_type_covers_the_real_relations(self) -> None:
        dashboard = _wayne_edges()
        counts = dashboard["counts_by_type"]
        assert counts, "counts_by_type must be non-empty"
        # The canonical exploitation/wage/solidarity relations are all seeded.
        for edge_type in ("exploitation", "wages", "solidarity"):
            assert edge_type in counts, f"expected a seeded {edge_type!r} edge"
        assert sum(counts.values()) == dashboard["total_edges"]

    def test_top_by_tension_and_value_flow_are_ranked_and_bounded(self) -> None:
        dashboard = _wayne_edges()
        top_tension = dashboard["top_by_tension"]
        top_flow = dashboard["top_by_value_flow"]
        assert top_tension and len(top_tension) <= 10  # _EDGES_TOP_N
        assert top_flow and len(top_flow) <= 10
        # tension is sorted descending (the "hottest" edge first).
        tensions = [row["tension"] for row in top_tension]  # type: ignore[index, union-attr]
        assert tensions == sorted(tensions, reverse=True)
        # every row carries the endpoints the frontend renders.
        for row in top_tension:  # type: ignore[union-attr]
            assert {"source_id", "target_id", "edge_type", "tension", "value_flow"} <= set(row)

    def test_solidarity_strength_stats_reflect_the_seeded_edge(self) -> None:
        """wayne seeds one SOLIDARITY edge (Detroit prole <-> Dearborn workers,
        strength 0.05); the stats must report it, not an honest-null."""
        dashboard = _wayne_edges()
        stats = dashboard["solidarity_strength_stats"]
        assert stats["count"] >= 1  # type: ignore[index]
        assert stats["max"] is not None  # type: ignore[index]

    def test_edge_mode_counts_are_empty_until_edge_transition_runs(self) -> None:
        """Constitution III.11: edge_mode is None on a tick-0 graph
        (EdgeTransitionSystem has not run), so counts_by_mode is honestly
        empty — distinct from counts_by_type which is populated."""
        dashboard = _wayne_edges()
        assert dashboard["counts_by_mode"] == {}

    def test_payload_carries_the_full_contract_shape(self) -> None:
        dashboard = _wayne_edges()
        for key in (
            "total_edges",
            "counts_by_type",
            "counts_by_mode",
            "top_by_value_flow",
            "top_by_tension",
            "solidarity_strength_stats",
        ):
            assert key in dashboard, f"contract key {key!r} missing from edges payload"
