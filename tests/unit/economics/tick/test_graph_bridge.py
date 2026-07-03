"""Tests for graph bridge round-trip serialization.

Feature: 017-simulation-tick-dynamics
Task: T008
"""

from __future__ import annotations

import networkx as nx

from babylon.economics.distribution.types import DebtAccumulation, SurplusValueDistribution
from babylon.economics.financial_crisis.types import FinancialCrisisAssessment
from babylon.economics.rent.types import HousingValueDecomposition, RentExtraction
from babylon.economics.tick.graph_bridge import (
    TICK_DYNAMICS_KEY,
    read_tick_state_from_graph,
    write_tick_state_to_graph,
)
from babylon.economics.tick.types import (
    BifurcationRiskMetric,
    CrisisPhase,
    CrisisState,
    NationalTickParameters,
    SimulationTickState,
    SmoothedCoefficients,
)
from tests.unit.economics.tick.conftest import WAYNE_FIPS, build_territory_graph


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
        assert node_data["tick_crisis_phase"] == "normal"
        assert node_data["tick_crisis_duration"] == 0
        assert node_data["tick_bifurcation_score"] == 0.0
        assert node_data["tick_wage_compression"] == 0.0
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
        assert recovered.crisis_state.phase == original.crisis_state.phase

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

    def test_round_trip_preserves_crisis_state(
        self,
        sample_tick_state: SimulationTickState,
    ) -> None:
        """Verify crisis state attributes survive round-trip (T065)."""
        graph = build_territory_graph()
        # Modify county to have active crisis with compression and bifurcation
        original_county = sample_tick_state.county_states[WAYNE_FIPS]
        crisis = CrisisState(
            phase=CrisisPhase.DEEP,
            consecutive_below=6,
            consecutive_recovery=0,
            crisis_start_period=3,
            crisis_duration=8,
            peak_severity=0.03,
            cumulative_wage_compression=0.15,
        )
        bifurcation = BifurcationRiskMetric(
            score=-0.42,
            solidarity_density=0.75,
            legitimation=0.60,
            class_burden_ratio=0.30,
        )
        modified_county = original_county.model_copy(
            update={
                "crisis_state": crisis,
                "bifurcation_risk": bifurcation,
            }
        )
        modified_state = sample_tick_state.model_copy(
            update={"county_states": {WAYNE_FIPS: modified_county}}
        )

        write_tick_state_to_graph(graph, modified_state)

        # Verify raw graph attributes
        node_data = graph.nodes[WAYNE_FIPS]
        assert node_data["tick_crisis_phase"] == "deep"
        assert node_data["tick_crisis_duration"] == 8
        assert node_data["tick_bifurcation_score"] == -0.42
        assert node_data["tick_wage_compression"] == 0.15

        # Verify round-trip reconstruction
        result = read_tick_state_from_graph(graph)
        assert result is not None
        recovered = result.county_states[WAYNE_FIPS]
        assert recovered.crisis_state.phase == CrisisPhase.DEEP
        assert recovered.crisis_state.crisis_duration == 8
        assert recovered.crisis_state.cumulative_wage_compression == 0.15
        assert recovered.bifurcation_risk.score == -0.42


class TestWriteFinancialState:
    """Tests for Feature 024 financial tick attributes on graph bridge."""

    def test_writes_default_financial_attrs_when_none(
        self,
        sample_tick_state: SimulationTickState,
    ) -> None:
        """Verify default (None) financial fields produce sensible defaults on nodes."""
        graph = build_territory_graph()
        write_tick_state_to_graph(graph, sample_tick_state)

        node_data = graph.nodes[WAYNE_FIPS]
        assert node_data["tick_interest_burden"] == 0.0
        assert node_data["tick_ground_rent"] == 0.0
        assert node_data["tick_rentier_share"] == 0.0
        assert node_data["tick_profit_of_enterprise"] == 0.0
        assert node_data["tick_financialization_share"] == 0.0
        assert node_data["tick_accumulated_debt"] == 0.0
        assert node_data["tick_claims_exceed_surplus"] is False
        assert node_data["tick_housing_fictitious_fraction"] is None
        assert node_data["tick_financial_crisis_signals"] == 0

    def test_writes_populated_financial_attrs(
        self,
        sample_tick_state: SimulationTickState,
    ) -> None:
        """Verify financial fields written when populated on county state."""
        svd = SurplusValueDistribution(
            fips_code="26163",
            year=2015,
            total_surplus_produced=1000.0,
            interest_payments=200.0,
            ground_rent=100.0,
            taxes_on_surplus=50.0,
        )
        rent = RentExtraction(
            fips_code="26163",
            year=2015,
            agricultural_rent=50.0,
            resource_rent=30.0,
            urban_rent=200.0,
        )
        housing = HousingValueDecomposition(
            fips_code="26163",
            year=2015,
            construction_value=100000.0,
            ground_rent_capitalized=50000.0,
            speculative_premium=30000.0,
        )
        debt = DebtAccumulation(
            fips_code="26163",
            year=2015,
            accumulated_debt=500.0,
            consecutive_deficit_ticks=3,
        )
        crisis = FinancialCrisisAssessment(
            fips_code="26163",
            year=2015,
            profit_squeeze=True,
            overaccumulation=True,
            credit_fragility=True,
            claims_exceed_surplus=True,
        )

        original_county = sample_tick_state.county_states[WAYNE_FIPS]
        modified_county = original_county.model_copy(
            update={
                "surplus_distribution": svd,
                "rent_extraction": rent,
                "housing_decomposition": housing,
                "debt_accumulation": debt,
                "financial_crisis": crisis,
            }
        )
        modified_state = sample_tick_state.model_copy(
            update={"county_states": {WAYNE_FIPS: modified_county}}
        )

        graph = build_territory_graph()
        write_tick_state_to_graph(graph, modified_state)

        node_data = graph.nodes[WAYNE_FIPS]
        assert node_data["tick_interest_burden"] == 200.0
        assert node_data["tick_ground_rent"] == 280.0  # 50 + 30 + 200
        assert node_data["tick_rentier_share"] == 0.1  # 100 / 1000
        assert node_data["tick_profit_of_enterprise"] == 650.0
        assert node_data["tick_financialization_share"] == 0.2  # 200 / 1000
        assert node_data["tick_accumulated_debt"] == 500.0
        assert node_data["tick_claims_exceed_surplus"] is False  # 200+100+50 < 1000
        expected_fict = (50000.0 + 30000.0) / 180000.0
        assert abs(node_data["tick_housing_fictitious_fraction"] - expected_fict) < 1e-9
        assert node_data["tick_financial_crisis_signals"] == 4

    def test_credit_cycle_phase_in_metadata(
        self,
        sample_tick_state: SimulationTickState,
    ) -> None:
        """Verify credit_cycle_phase written to graph metadata dict."""
        graph = build_territory_graph()
        write_tick_state_to_graph(graph, sample_tick_state)

        tick_data = graph.graph[TICK_DYNAMICS_KEY]
        assert tick_data["credit_cycle_phase"] == "expansion"

    def test_round_trip_financial_fields_default_to_none(
        self,
        sample_tick_state: SimulationTickState,
    ) -> None:
        """Verify read reconstructs county with None financial fields.

        The read path does not reconstruct full Pydantic financial objects
        from scalar node attributes. Financial fields remain at their
        default None values after round-trip.
        """
        graph = build_territory_graph()
        write_tick_state_to_graph(graph, sample_tick_state)
        result = read_tick_state_from_graph(graph)

        assert result is not None
        recovered = result.county_states[WAYNE_FIPS]
        assert recovered.surplus_distribution is None
        assert recovered.rent_extraction is None
        assert recovered.housing_decomposition is None
        assert recovered.debt_accumulation is None
        assert recovered.financial_crisis is None
