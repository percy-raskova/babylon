"""Unit tests for SimulationState protocol (T039).

This test validates that:
- SimulationState is a runtime_checkable Protocol
- Simulation class is an instance of SimulationState
- Protocol methods are callable via protocol type

See Also:
    - spec.md#SC-004: Protocol methods callable
    - spec.md#SC-005: mypy type-check protocols
"""

from __future__ import annotations

import pytest

from babylon.engine.simulation import Simulation
from babylon.models import SimulationConfig, WorldState
from babylon.models.snapshots import HexState, SimulationSnapshot, TerritoryState
from babylon.protocols import SimulationState


@pytest.fixture
def simulation_with_territory() -> Simulation:
    """Create a simulation with MVP territory state."""
    state = WorldState()
    config = SimulationConfig()
    sim = Simulation(state, config)

    territory = TerritoryState(
        territory_id="26163",
        controlling_polity="26163",
        hex_claims=frozenset(["8528a9c9bffffff"]),
        tick=0,
        profit_rate=0.15,
        equilibrium_r=0.15,
    )
    hexes = {"8528a9c9bffffff": HexState(h3_index="8528a9c9bffffff")}
    sim._initialize_mvp_territories(territories={"26163": territory}, hexes=hexes)

    return sim


class TestSimulationStateProtocol:
    """Test SimulationState protocol compliance."""

    def test_simulation_is_instance_of_simulation_state(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify Simulation is instance of SimulationState (T039 core test)."""
        sim = simulation_with_territory
        assert isinstance(sim, SimulationState)

    def test_protocol_is_runtime_checkable(self) -> None:
        """Verify SimulationState protocol is runtime_checkable."""
        # This test verifies the @runtime_checkable decorator is present
        # by successfully using isinstance()
        state = WorldState()
        config = SimulationConfig()
        sim = Simulation(state, config)

        # This would fail if @runtime_checkable wasn't applied
        result = isinstance(sim, SimulationState)
        assert result is True

    def test_non_simulation_is_not_instance(self) -> None:
        """Verify non-Simulation objects are not instances of SimulationState."""

        class NotASimulation:
            pass

        obj = NotASimulation()
        assert not isinstance(obj, SimulationState)


class TestSimulationStateMethodsCallable:
    """Test that SimulationState methods are callable via protocol type (SC-004)."""

    def test_get_current_tick_callable_via_protocol(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify get_current_tick() callable via SimulationState type."""

        def query_tick(sim: SimulationState) -> int:
            return sim.get_current_tick()

        result = query_tick(simulation_with_territory)
        assert result == 0

    def test_get_snapshot_callable_via_protocol(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify get_snapshot() callable via SimulationState type."""

        def query_snapshot(sim: SimulationState) -> SimulationSnapshot:
            return sim.get_snapshot()

        result = query_snapshot(simulation_with_territory)
        assert isinstance(result, SimulationSnapshot)
        assert "26163" in result.territories

    def test_get_territory_state_callable_via_protocol(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify get_territory_state() callable via SimulationState type."""

        def query_territory(sim: SimulationState, tid: str) -> TerritoryState | None:
            return sim.get_territory_state(tid)

        result = query_territory(simulation_with_territory, "26163")
        assert result is not None
        assert result.territory_id == "26163"

    def test_get_hexes_for_territory_callable_via_protocol(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify get_hexes_for_territory() callable via SimulationState type."""

        def query_hexes(sim: SimulationState, tid: str) -> set[str]:
            return sim.get_hexes_for_territory(tid)

        result = query_hexes(simulation_with_territory, "26163")
        assert "8528a9c9bffffff" in result


class TestSimulationStateInterfaceStability:
    """Test that GUI code can depend on SimulationState interface."""

    def test_gui_render_function_accepts_simulation_state(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify GUI-style function works with SimulationState parameter."""

        def render_map(sim: SimulationState) -> list[str]:
            """Example GUI render function that depends only on protocol."""
            snapshot = sim.get_snapshot()
            rendered = []
            for tid, territory in snapshot.territories.items():
                rendered.append(f"{tid}: rate={territory.profit_rate:.2f}")
            return rendered

        # This should work because Simulation implements SimulationState
        result = render_map(simulation_with_territory)
        assert len(result) == 1
        assert "26163" in result[0]

    def test_mock_simulation_state_can_be_created(self) -> None:
        """Verify a mock SimulationState can be used for testing."""

        class MockSimulationState:
            """Mock implementation for GUI testing."""

            def get_current_tick(self) -> int:
                return 42

            def get_snapshot(self) -> SimulationSnapshot:
                return SimulationSnapshot(tick=42, territories={}, hexes={}, edges=[])

            def get_territory_state(self, territory_id: str) -> TerritoryState | None:
                return None

            def get_hexes_for_territory(self, territory_id: str) -> set[str]:
                return set()

            def get_node_by_spatial_index(self, h3_index: str) -> TerritoryState | None:
                return None

        mock = MockSimulationState()

        # Mock should be instance of SimulationState protocol
        assert isinstance(mock, SimulationState)

        # GUI code should work with mock
        def gui_display_tick(sim: SimulationState) -> str:
            return f"Tick: {sim.get_current_tick()}"

        assert gui_display_tick(mock) == "Tick: 42"


# =============================================================================
# Feature 006-gui-protocol-extension: Spatial Query Tests (T021-T024)
# =============================================================================


# Valid H3 indices for testing (Detroit metro area, resolution 5)
# Generated via h3.latlng_to_cell(42.3314, -83.0458, 5) and neighbors
VALID_H3_WAYNE_1 = "852ab2c7fffffff"  # Wayne County hex 1
VALID_H3_WAYNE_2 = "852ab2c3fffffff"  # Wayne County hex 2 (neighbor)
VALID_H3_OAKLAND = "852ab2cffffffff"  # Oakland County hex (neighbor)
VALID_H3_UNCLAIMED = "852ab21bfffffff"  # Valid H3 but not claimed


@pytest.fixture
def simulation_with_multiple_territories() -> Simulation:
    """Create a simulation with multiple territories and H3 hexes."""
    state = WorldState()
    config = SimulationConfig()
    sim = Simulation(state, config)

    # Territory 1: Wayne County (26163)
    territory1 = TerritoryState(
        territory_id="26163",
        controlling_polity="26163",
        hex_claims=frozenset([VALID_H3_WAYNE_1, VALID_H3_WAYNE_2]),
        tick=0,
        profit_rate=0.15,
        equilibrium_r=0.15,
    )

    # Territory 2: Oakland County (26125)
    territory2 = TerritoryState(
        territory_id="26125",
        controlling_polity="26125",
        hex_claims=frozenset([VALID_H3_OAKLAND]),
        tick=0,
        profit_rate=0.20,
        equilibrium_r=0.20,
    )

    territories = {"26163": territory1, "26125": territory2}
    hexes = {
        VALID_H3_WAYNE_1: HexState(h3_index=VALID_H3_WAYNE_1),
        VALID_H3_WAYNE_2: HexState(h3_index=VALID_H3_WAYNE_2),
        VALID_H3_OAKLAND: HexState(h3_index=VALID_H3_OAKLAND),
    }
    sim._initialize_mvp_territories(territories=territories, hexes=hexes)

    return sim


class TestSpatialQueryValidH3:
    """T021: valid H3 index returns owning TerritoryState."""

    def test_valid_h3_returns_territory(
        self, simulation_with_multiple_territories: Simulation
    ) -> None:
        """Valid H3 index claimed by territory returns TerritoryState."""
        sim = simulation_with_multiple_territories

        # Query a hex claimed by Wayne County
        result = sim.get_node_by_spatial_index(VALID_H3_WAYNE_1)

        assert result is not None
        assert result.territory_id == "26163"

    def test_valid_h3_returns_correct_territory(
        self, simulation_with_multiple_territories: Simulation
    ) -> None:
        """Valid H3 index returns the correct owning territory."""
        sim = simulation_with_multiple_territories

        # Query a hex claimed by Oakland County
        result = sim.get_node_by_spatial_index(VALID_H3_OAKLAND)

        assert result is not None
        assert result.territory_id == "26125"
        assert result.profit_rate == 0.20

    def test_spatial_query_callable_via_protocol(
        self, simulation_with_multiple_territories: Simulation
    ) -> None:
        """Verify get_node_by_spatial_index() callable via SimulationState type."""

        def query_territory_by_hex(sim: SimulationState, h3_index: str) -> TerritoryState | None:
            return sim.get_node_by_spatial_index(h3_index)

        result = query_territory_by_hex(simulation_with_multiple_territories, VALID_H3_WAYNE_1)
        assert result is not None
        assert result.territory_id == "26163"


class TestSpatialQueryUnclaimedH3:
    """T022: valid H3 index not claimed returns None."""

    def test_unclaimed_h3_returns_none(
        self, simulation_with_multiple_territories: Simulation
    ) -> None:
        """Valid H3 index not claimed by any territory returns None."""
        sim = simulation_with_multiple_territories

        # Query a valid H3 hex that isn't claimed by any territory
        result = sim.get_node_by_spatial_index(VALID_H3_UNCLAIMED)

        assert result is None


class TestSpatialQueryInvalidH3:
    """T023: invalid H3 format raises ValueError."""

    def test_invalid_h3_raises_value_error(
        self, simulation_with_multiple_territories: Simulation
    ) -> None:
        """Invalid H3 index format raises ValueError."""
        sim = simulation_with_multiple_territories

        with pytest.raises(ValueError, match="Invalid H3 index"):
            sim.get_node_by_spatial_index("not-a-valid-h3")

    def test_malformed_hex_raises_value_error(
        self, simulation_with_multiple_territories: Simulation
    ) -> None:
        """Malformed hex string raises ValueError."""
        sim = simulation_with_multiple_territories

        with pytest.raises(ValueError, match="Invalid H3 index"):
            sim.get_node_by_spatial_index("ZZZZZZZZZZZZZZZ")

    def test_empty_string_raises_value_error(
        self, simulation_with_multiple_territories: Simulation
    ) -> None:
        """Empty string raises ValueError."""
        sim = simulation_with_multiple_territories

        with pytest.raises(ValueError, match="Invalid H3 index"):
            sim.get_node_by_spatial_index("")


class TestSpatialQueryCacheInvalidation:
    """T024: cache invalidated after step()."""

    def test_cache_invalidated_after_step(
        self, simulation_with_multiple_territories: Simulation
    ) -> None:
        """Spatial index cache is invalidated after step()."""
        sim = simulation_with_multiple_territories

        # First query builds the cache
        result1 = sim.get_node_by_spatial_index(VALID_H3_WAYNE_1)
        assert result1 is not None

        # Cache should exist now (internal check)
        assert sim._hex_to_territory is not None

        # Step should invalidate the cache
        sim.step()

        # Cache should be None after step
        assert sim._hex_to_territory is None

        # Query should still work (rebuilds cache)
        result2 = sim.get_node_by_spatial_index(VALID_H3_WAYNE_1)
        assert result2 is not None


class TestMockSimulationStateWithSpatialQuery:
    """Verify mock SimulationState can include spatial query."""

    def test_mock_with_spatial_query(self) -> None:
        """Mock SimulationState with get_node_by_spatial_index."""

        class MockSimulationStateWithSpatial:
            """Mock with spatial query support."""

            def get_current_tick(self) -> int:
                return 0

            def get_snapshot(self) -> SimulationSnapshot:
                return SimulationSnapshot(tick=0, territories={}, hexes={}, edges=[])

            def get_territory_state(self, territory_id: str) -> TerritoryState | None:
                return None

            def get_hexes_for_territory(self, territory_id: str) -> set[str]:
                return set()

            def get_node_by_spatial_index(self, h3_index: str) -> TerritoryState | None:
                # Mock returns a fixed territory for any valid H3 index
                if h3_index.startswith("852"):
                    return TerritoryState(
                        territory_id="99999",  # Valid 5-digit FIPS format
                        controlling_polity="99999",
                        hex_claims=frozenset([h3_index]),
                        tick=0,
                        profit_rate=0.5,
                        equilibrium_r=0.5,
                    )
                return None

        mock = MockSimulationStateWithSpatial()
        assert isinstance(mock, SimulationState)

        # Mock should respond to spatial queries
        result = mock.get_node_by_spatial_index(VALID_H3_WAYNE_1)
        assert result is not None
        assert result.territory_id == "99999"
