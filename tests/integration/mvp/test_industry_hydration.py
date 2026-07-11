"""Tests for industry hyperedge hydration and persistence."""

from __future__ import annotations

import pytest

from babylon.engine.hydration.reference import hydrate_industry_hyperedges
from babylon.engine.simulation import Simulation
from babylon.models.world_state import WorldState

# Needs the reference SQLite DB — excluded on CI until the item-40 subset artifact lands.
pytestmark = pytest.mark.requires_reference_db

# Detroit test case
WAYNE_FIPS = "26163"
OAKLAND_FIPS = "26125"
DETROIT_FIPS_CODES = [WAYNE_FIPS, OAKLAND_FIPS]


class TestIndustryHydration:
    def test_hydrate_industry_hyperedges_returns_industries(self) -> None:
        """Verify hydrate_industry_hyperedges parses data and returns IndustryHyperedge models."""
        industries = hydrate_industry_hyperedges(DETROIT_FIPS_CODES)

        assert len(industries) > 0

        first_key = list(industries.keys())[0]
        industry = industries[first_key]

        assert hasattr(industry, "naics_2digit")
        assert hasattr(industry, "total_employment")
        assert hasattr(industry, "total_wages")
        assert hasattr(industry, "occ")
        assert hasattr(industry, "profit_rate")
        assert hasattr(industry, "county_fips")

        assert industry.total_employment >= 0
        assert industry.total_wages >= 0
        assert industry.occ >= 0
        assert industry.profit_rate >= 0
        assert len(industry.county_fips) > 0
        for fips in industry.county_fips:
            assert fips in DETROIT_FIPS_CODES

    def test_world_state_to_graph_from_graph(self) -> None:
        """Verify that a WorldState with industries correctly serializes and deserializes."""
        industries = hydrate_industry_hyperedges(DETROIT_FIPS_CODES)

        state1 = WorldState(industries=industries)

        G = state1.to_graph()

        # Verify nodes are in the graph
        for ind_id in industries:
            assert ind_id in G.nodes
            assert G.nodes[ind_id]["_node_type"] == "industry"

        state2 = WorldState.from_graph(G, tick=0)

        assert len(state2.industries) == len(state1.industries)
        for ind_id, ind in state1.industries.items():
            assert ind_id in state2.industries
            assert state2.industries[ind_id].naics_2digit == ind.naics_2digit
            assert state2.industries[ind_id].total_employment == ind.total_employment
            assert state2.industries[ind_id].county_fips == ind.county_fips

    def test_simulation_from_sqlite_has_industries(self) -> None:
        """Verify Simulation.from_sqlite automatically hydrates industries."""
        sim = Simulation.from_sqlite(DETROIT_FIPS_CODES)

        state = sim.current_state
        assert hasattr(state, "industries")
        assert len(state.industries) > 0
