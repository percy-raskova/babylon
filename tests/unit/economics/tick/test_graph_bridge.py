"""Tests for graph bridge round-trip serialization.

Feature: 017-simulation-tick-dynamics
Task: T008
"""

from __future__ import annotations

import networkx as nx
from tests.unit.economics.tick.conftest import WAYNE_FIPS, build_territory_graph

from babylon.economics.tick.graph_bridge import (
    TICK_DYNAMICS_KEY,
    read_tick_state_from_graph,
    write_tick_state_to_graph,
)
from babylon.economics.tick.types import (
    NationalTickParameters,
    SimulationTickState,
    SmoothedCoefficients,
)


class TestWriteTickStateToGraph:
    """Tests for write_tick_state_to_graph."""

    def test_writes_national_params_to_graph_metadata(
        self,
        sample_tick_state: SimulationTickState,
    ) -> None:
        """Verify national params written to graph.graph["tick_dynamics"]."""
        graph = build_territory_graph()
        write_tick_state_to_graph(graph, sample_tick_state)

        assert TICK_DYNAMICS_KEY in graph.graph
        tick_data = graph.graph[TICK_DYNAMICS_KEY]
        assert tick_data["year"] == 2015
        assert isinstance(tick_data["national_params"], NationalTickParameters)
        assert isinstance(tick_data["coefficients"], SmoothedCoefficients)
        assert tick_data["is_year_boundary"] is True

    def test_writes_county_state_to_territory_nodes(
        self,
        sample_tick_state: SimulationTickState,
    ) -> None:
        """Verify county state written to territory node attributes."""
        graph = build_territory_graph()
        write_tick_state_to_graph(graph, sample_tick_state)

        node_data = graph.nodes[WAYNE_FIPS]
        assert node_data["tick_capital_stock"] == 1_000_000_000.0
        assert node_data["tick_throughput_position"] == 0.90
        assert node_data["tick_supply_chain_depth"] == 2.1
        assert node_data["tick_phi_hour"] == 3.50
        assert node_data["tick_crisis"] is False
        assert node_data["tick_unemployment_rate"] == 0.053
        assert node_data["tick_median_wage"] == 21.0

    def test_writes_class_distribution_as_dict(
        self,
        sample_tick_state: SimulationTickState,
    ) -> None:
        """Verify class distribution serialized as dict on node."""
        graph = build_territory_graph()
        write_tick_state_to_graph(graph, sample_tick_state)

        dist = graph.nodes[WAYNE_FIPS]["tick_class_distribution"]
        assert dist["bourgeoisie"] == 0.01
        assert dist["proletariat"] == 0.35

    def test_skips_non_territory_nodes(
        self,
        sample_tick_state: SimulationTickState,
    ) -> None:
        """Verify non-territory nodes are not modified."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(WAYNE_FIPS, _node_type="territory")
        graph.add_node("social_class_1", _node_type="social_class")
        write_tick_state_to_graph(graph, sample_tick_state)

        assert "tick_capital_stock" in graph.nodes[WAYNE_FIPS]
        assert "tick_capital_stock" not in graph.nodes["social_class_1"]

    def test_skips_missing_fips_nodes(
        self,
        sample_tick_state: SimulationTickState,
    ) -> None:
        """Verify no error when FIPS not in graph."""
        graph: nx.DiGraph[str] = nx.DiGraph()  # empty graph
        # Should not raise
        write_tick_state_to_graph(graph, sample_tick_state)
        assert TICK_DYNAMICS_KEY in graph.graph


class TestReadTickStateFromGraph:
    """Tests for read_tick_state_from_graph."""

    def test_returns_none_without_tick_data(self) -> None:
        """Verify returns None when no tick dynamics data present."""
        graph = build_territory_graph()
        result = read_tick_state_from_graph(graph)
        assert result is None

    def test_round_trip_preserves_state(
        self,
        sample_tick_state: SimulationTickState,
    ) -> None:
        """Verify write then read produces equivalent state."""
        graph = build_territory_graph()
        write_tick_state_to_graph(graph, sample_tick_state)
        result = read_tick_state_from_graph(graph)

        assert result is not None
        assert result.year == sample_tick_state.year
        assert result.national_params == sample_tick_state.national_params
        assert result.coefficients == sample_tick_state.coefficients

        # County state round-trip
        assert WAYNE_FIPS in result.county_states
        original = sample_tick_state.county_states[WAYNE_FIPS]
        recovered = result.county_states[WAYNE_FIPS]
        assert recovered.fips == original.fips
        assert recovered.capital_stock == original.capital_stock
        assert recovered.throughput_position == original.throughput_position
        assert recovered.phi_hour == original.phi_hour
        assert recovered.crisis == original.crisis

    def test_round_trip_preserves_class_distribution(
        self,
        sample_tick_state: SimulationTickState,
    ) -> None:
        """Verify class distribution survives round-trip."""
        graph = build_territory_graph()
        write_tick_state_to_graph(graph, sample_tick_state)
        result = read_tick_state_from_graph(graph)

        assert result is not None
        original_dist = sample_tick_state.county_states[WAYNE_FIPS].class_distribution
        recovered_dist = result.county_states[WAYNE_FIPS].class_distribution
        assert recovered_dist.bourgeoisie_share == original_dist.bourgeoisie_share
        assert recovered_dist.proletariat_share == original_dist.proletariat_share
        assert recovered_dist.lumpenproletariat_share == original_dist.lumpenproletariat_share
