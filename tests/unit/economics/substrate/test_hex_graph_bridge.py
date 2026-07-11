"""Unit tests for hex-to-graph bridge (R7 → R6 → Graph).

RED phase: Tests for the hex_graph_bridge module:
- R6TerritoryState model
- aggregate_r7_to_r6() pure function
- write_hex_state_to_graph() / read_hex_state_from_graph()
- R8 terrain/utility forwarding
- Feedback stub hooks

Feature: hex-substrate-graph-bridge
"""

from __future__ import annotations

import pydantic
import pytest

# These imports will fail in RED phase (module doesn't exist yet)
from babylon.economics.substrate.hex_graph_bridge import (
    R6TerritoryState,
    aggregate_r7_to_r6,
    read_hex_state_from_graph,
    write_hex_state_to_graph,
)
from babylon.economics.substrate.types import HexGrid
from babylon.topology.graph import BabylonGraph

# Fixtures are inherited from conftest.py in the substrate directory


# ============================================================================
# Helpers
# ============================================================================


def _make_mock_graph_with_r6_territories(
    r6_ids: list[str],
) -> object:
    """Create a BabylonGraph with territory nodes at R6 IDs."""

    G = BabylonGraph()
    for r6_id in r6_ids:
        G.add_node(
            r6_id,
            _node_type="territory",
            name=f"Territory {r6_id[:8]}",
            sector_type="INDUSTRIAL",
        )

    return G


# ============================================================================
# R6TerritoryState Model
# ============================================================================


@pytest.mark.unit
class TestR6TerritoryState:
    """Tests for R6TerritoryState Pydantic model."""

    def test_create_basic(self) -> None:
        """Create a basic R6TerritoryState."""
        state = R6TerritoryState(
            h3_index="8626163ffffff",
            county_fips="26163",
            total_capital=800.0,
            constant_capital=400.0,
            variable_capital=250.0,
            surplus_value=150.0,
            employment=3000.0,
            profit_rate=0.23,
            exploitation_rate=0.60,
            organic_composition=1.6,
            dept_shares=(0.20, 0.35, 0.25, 0.20),
            r7_child_count=3,
        )
        assert state.h3_index == "8626163ffffff"
        assert state.total_capital == pytest.approx(800.0)

    def test_frozen(self) -> None:
        """R6TerritoryState is immutable."""
        state = R6TerritoryState(
            h3_index="8626163ffffff",
            county_fips="26163",
            total_capital=100.0,
            constant_capital=50.0,
            variable_capital=30.0,
            surplus_value=20.0,
            employment=100.0,
            profit_rate=0.25,
            exploitation_rate=0.67,
            organic_composition=1.67,
            dept_shares=(0.25, 0.25, 0.25, 0.25),
            r7_child_count=1,
        )
        with pytest.raises(pydantic.ValidationError):
            state.total_capital = 999.0  # type: ignore[misc]


# ============================================================================
# aggregate_r7_to_r6
# ============================================================================


@pytest.mark.unit
class TestAggregateR7ToR6:
    """Tests for aggregate_r7_to_r6()."""

    def test_basic_aggregation(self, hydrated_hex_grid: HexGrid) -> None:
        """Aggregate R7 hexes to R6 states produces correct count."""
        r6_states = aggregate_r7_to_r6(hydrated_hex_grid)

        # 3 counties × 1 R6 parent each = 3 R6 states
        assert len(r6_states) == 3

    def test_total_capital_conservation(self, hydrated_hex_grid: HexGrid) -> None:
        """Sum of R6 total_capital equals sum of all R7 c+v+s."""
        r6_states = aggregate_r7_to_r6(hydrated_hex_grid)

        r7_total = sum(
            h.constant_capital + h.variable_capital + h.surplus_value
            for h in hydrated_hex_grid.hexes.values()
        )
        r6_total = sum(s.total_capital for s in r6_states.values())
        assert r6_total == pytest.approx(r7_total)

    def test_component_conservation(self, hydrated_hex_grid: HexGrid) -> None:
        """Individual c, v, s components conserve through aggregation."""
        r6_states = aggregate_r7_to_r6(hydrated_hex_grid)

        r7_c = sum(h.constant_capital for h in hydrated_hex_grid.hexes.values())
        r7_v = sum(h.variable_capital for h in hydrated_hex_grid.hexes.values())
        r7_s = sum(h.surplus_value for h in hydrated_hex_grid.hexes.values())

        r6_c = sum(s.constant_capital for s in r6_states.values())
        r6_v = sum(s.variable_capital for s in r6_states.values())
        r6_s = sum(s.surplus_value for s in r6_states.values())

        assert r6_c == pytest.approx(r7_c)
        assert r6_v == pytest.approx(r7_v)
        assert r6_s == pytest.approx(r7_s)

    def test_profit_rate_is_weighted(self, hydrated_hex_grid: HexGrid) -> None:
        """Profit rate is Σs/Σ(c+v), not averaged."""
        r6_states = aggregate_r7_to_r6(hydrated_hex_grid)

        wayne_parent = "8626163ffffff"
        state = r6_states[wayne_parent]

        # Manual: Σs / Σ(c+v)
        child_ids = hydrated_hex_grid.res6_children[wayne_parent]
        total_s = sum(hydrated_hex_grid.hexes[c].surplus_value for c in child_ids)
        total_cv = sum(
            hydrated_hex_grid.hexes[c].constant_capital
            + hydrated_hex_grid.hexes[c].variable_capital
            for c in child_ids
        )
        expected_r = total_s / total_cv

        assert state.profit_rate == pytest.approx(expected_r)

    def test_r7_child_count(self, hydrated_hex_grid: HexGrid) -> None:
        """r7_child_count matches actual number of children."""
        r6_states = aggregate_r7_to_r6(hydrated_hex_grid)

        for r6_id, state in r6_states.items():
            expected = len(hydrated_hex_grid.res6_children[r6_id])
            assert state.r7_child_count == expected

    def test_dept_shares_sum_to_one(self, hydrated_hex_grid: HexGrid) -> None:
        """Department shares sum to 1.0 at R6."""
        r6_states = aggregate_r7_to_r6(hydrated_hex_grid)

        for state in r6_states.values():
            assert sum(state.dept_shares) == pytest.approx(1.0, abs=1e-10)

    def test_empty_grid(self) -> None:
        """Empty HexGrid produces empty R6 result."""
        grid = HexGrid(
            hexes={},
            county_hex_ids={},
            res6_parents={},
            res5_parents={},
            res6_children={},
            res5_children={},
        )
        r6_states = aggregate_r7_to_r6(grid)
        assert len(r6_states) == 0

    def test_county_fips_majority(self, hydrated_hex_grid: HexGrid) -> None:
        """County FIPS on R6 state is the majority county of children."""
        r6_states = aggregate_r7_to_r6(hydrated_hex_grid)

        # In our test grid, each R6 parent has children from only one county
        wayne_parent = "8626163ffffff"
        assert r6_states[wayne_parent].county_fips == "26163"

        oakland_parent = "8626125ffffff"
        assert r6_states[oakland_parent].county_fips == "26125"


# ============================================================================
# write/read hex state to/from graph
# ============================================================================


@pytest.mark.unit
class TestWriteHexStateToGraph:
    """Tests for write_hex_state_to_graph()."""

    def test_writes_hex_attributes(self, hydrated_hex_grid: HexGrid) -> None:
        """Verify hex_ attributes appear on territory nodes."""
        r6_states = aggregate_r7_to_r6(hydrated_hex_grid)
        r6_ids = list(r6_states.keys())
        graph = _make_mock_graph_with_r6_territories(r6_ids)

        write_hex_state_to_graph(graph, r6_states)

        for r6_id in r6_ids:
            node = graph.get_node(r6_id)
            assert node is not None
            attrs = node.attributes
            assert "hex_total_capital" in attrs
            assert "hex_profit_rate" in attrs
            assert "hex_employment" in attrs
            assert "hex_exploitation_rate" in attrs
            assert "hex_organic_composition" in attrs

    def test_no_new_nodes_created(self, hydrated_hex_grid: HexGrid) -> None:
        """Bridge writes only to existing territory nodes."""
        r6_states = aggregate_r7_to_r6(hydrated_hex_grid)
        # Only create 1 of 3 territory nodes
        graph = _make_mock_graph_with_r6_territories(list(r6_states.keys())[:1])

        initial_count = graph.count_nodes()
        write_hex_state_to_graph(graph, r6_states)

        assert graph.count_nodes() == initial_count

    def test_hex_prefix_no_collision_with_tick(self, hydrated_hex_grid: HexGrid) -> None:
        """hex_ and tick_ attributes coexist on the same node."""

        r6_states = aggregate_r7_to_r6(hydrated_hex_grid)
        r6_ids = list(r6_states.keys())

        G = BabylonGraph()
        for r6_id in r6_ids:
            G.add_node(
                r6_id,
                _node_type="territory",
                name=f"T-{r6_id[:8]}",
                sector_type="INDUSTRIAL",
                tick_capital_stock=999.0,  # Existing tick_ attribute
                tick_profit_rate=0.15,
            )
        graph = G

        write_hex_state_to_graph(graph, r6_states)

        node = graph.get_node(r6_ids[0])
        assert node is not None
        attrs = node.attributes
        # Both prefixes present
        assert "tick_capital_stock" in attrs
        assert "tick_profit_rate" in attrs
        assert "hex_total_capital" in attrs
        assert "hex_profit_rate" in attrs

    def test_roundtrip(self, hydrated_hex_grid: HexGrid) -> None:
        """Write then read produces identical R6 states."""
        r6_states = aggregate_r7_to_r6(hydrated_hex_grid)
        r6_ids = list(r6_states.keys())
        graph = _make_mock_graph_with_r6_territories(r6_ids)

        write_hex_state_to_graph(graph, r6_states)
        recovered = read_hex_state_from_graph(graph)

        assert len(recovered) == len(r6_states)
        for r6_id in r6_states:
            orig = r6_states[r6_id]
            rec = recovered[r6_id]
            assert rec.total_capital == pytest.approx(orig.total_capital)
            assert rec.profit_rate == pytest.approx(orig.profit_rate)
            assert rec.employment == pytest.approx(orig.employment)
            assert rec.r7_child_count == orig.r7_child_count


# ============================================================================
# R8 terrain/utility forwarding
# ============================================================================


@pytest.mark.unit
class TestTerrainUtilityForwarding:
    """Tests for R8 → R7 → R6 terrain and utility forwarding."""

    def test_terrain_water_fraction_forwarded(self, hydrated_hex_grid: HexGrid) -> None:
        """R7 terrain water fractions aggregate to R6."""
        from babylon.domain.geography.types import TerrainClassification

        # Mock R7 terrain: Wayne has 1/3 water children
        r7_terrain: dict[str, TerrainClassification] = {}
        from tests.unit.economics.substrate.conftest import WAYNE_HEX_IDS

        for i, hid in enumerate(WAYNE_HEX_IDS):
            r7_terrain[hid] = TerrainClassification(
                h3_index=hid,
                terrain_type="WATER" if i == 0 else "LAND",
                water_coverage_fraction=1.0 if i == 0 else 0.0,
            )

        r6_states = aggregate_r7_to_r6(
            hydrated_hex_grid,
            r7_terrain=r7_terrain,
        )

        wayne_parent = "8626163ffffff"
        state = r6_states[wayne_parent]
        # 1 of 3 Wayne R7 hexes is WATER → fraction ≈ 0.333
        assert state.terrain_water_fraction is not None
        assert state.terrain_water_fraction == pytest.approx(1.0 / 3.0)

    def test_utility_coverage_forwarded(self, hydrated_hex_grid: HexGrid) -> None:
        """R7 utility coverage averages to R6."""
        from tests.unit.economics.substrate.conftest import WAYNE_HEX_IDS

        # Mock R7 utility coverage
        r7_utility: dict[str, dict[str, float]] = {}
        for i, hid in enumerate(WAYNE_HEX_IDS):
            r7_utility[hid] = {
                "water_service": 1.0 if i < 2 else 0.5,
                "broadband": 0.5,
            }

        r6_states = aggregate_r7_to_r6(
            hydrated_hex_grid,
            r7_utility_coverage=r7_utility,
        )

        wayne_parent = "8626163ffffff"
        state = r6_states[wayne_parent]
        assert state.utility_coverage is not None
        # water_service: (1.0 + 1.0 + 0.5) / 3 ≈ 0.833
        assert state.utility_coverage["water_service"] == pytest.approx(
            (1.0 + 1.0 + 0.5) / 3.0,
        )
        # broadband: (0.5 + 0.5 + 0.5) / 3 = 0.5
        assert state.utility_coverage["broadband"] == pytest.approx(0.5)

    def test_no_terrain_data_leaves_none(self, hydrated_hex_grid: HexGrid) -> None:
        """Without terrain data, terrain_water_fraction is None."""
        r6_states = aggregate_r7_to_r6(hydrated_hex_grid)

        for state in r6_states.values():
            assert state.terrain_water_fraction is None


# ============================================================================
# Feedback stub hooks
# ============================================================================


@pytest.mark.unit
class TestFeedbackStubs:
    """Tests for graph → economics feedback stub hooks."""

    def test_feedback_protocol_exists(self) -> None:
        """GraphFeedback protocol is importable."""
        from babylon.economics.substrate.hex_graph_bridge import GraphFeedback

        # Protocol should be a class
        assert isinstance(GraphFeedback, type)

    def test_read_organizational_pressure_stub(self) -> None:
        """read_organizational_pressure returns empty dict stub."""

        from babylon.economics.substrate.hex_graph_bridge import (
            read_organizational_pressure,
        )

        G = BabylonGraph()
        graph = G

        result = read_organizational_pressure(graph)
        assert isinstance(result, dict)
        assert len(result) == 0
