"""Feature 021 territory-case fix: systems act on to_graph-shaped graphs.

RED-first tests for the node_type case bug (``reserve_army.py`` and
``dispossession_events.py`` queried ``"Territory"``; ``to_graph`` writes
``"territory"``) and the ``extra="forbid"`` round-trip latch: the systems
write attributes that must be either Territory model fields or entries in
``TERRITORY_EXCLUDED_FIELDS`` for the per-tick ``from_graph`` to survive.

Note on activation: with the case fixed the systems become ACTIVATABLE but
remain inert in current scenarios — no production seeder writes
``reserve_ratio`` / ``foreclosure_rate`` / ``median_wage`` onto territory
nodes (wiring a data source is the "wire the dormant sim" phase). These
tests seed the inputs explicitly.
"""

from __future__ import annotations

import pytest

from babylon.engine.services import ServiceContainer
from babylon.engine.systems.dispossession_events import DispossessionEventSystem
from babylon.engine.systems.reserve_army import ReserveArmySystem
from babylon.models.entities.territory import Territory
from babylon.models.enums import SectorType
from babylon.models.world_state import WorldState

pytestmark = pytest.mark.unit


def _wayne_state() -> WorldState:
    """WorldState whose to_graph output carries Feature-021 inputs."""
    return WorldState(
        tick=0,
        territories={
            "T001": Territory(
                id="T001",
                name="Wayne County",
                sector_type=SectorType.RESIDENTIAL,
                reserve_ratio=0.18,
                median_wage=45000.0,
                wealth=500_000_000.0,
                foreclosure_rate=0.08,
                eviction_rate=0.05,
                displacement_rate=0.03,
            ),
        },
    )


class TestTerritoryFeature021Fields:
    """Territory model carries the Feature-021 input fields."""

    def test_territory_accepts_feature021_inputs(self) -> None:
        """Territory model accepts reserve-army and dispossession inputs."""
        t = _wayne_state().territories["T001"]
        assert t.reserve_ratio == 0.18
        assert t.median_wage == 45000.0
        assert t.wealth == 500_000_000.0
        assert t.foreclosure_rate == 0.08


class TestReserveArmyOnProductionGraph:
    """ReserveArmySystem matches the graph shape production writes."""

    def test_mutates_to_graph_shaped_territory(self) -> None:
        """The system matches lowercase ``_node_type='territory'`` nodes."""
        graph = _wayne_state().to_graph()
        ReserveArmySystem().step(graph, ServiceContainer.create(), {"tick": 1})

        assert graph.nodes["T001"]["median_wage"] < 45000.0
        assert graph.nodes["T001"]["wage_pressure"] > 0.0

    def test_round_trip_survives_and_persists_wage(self) -> None:
        """from_graph neither crashes nor loses the mutated wage."""
        graph = _wayne_state().to_graph()
        ReserveArmySystem().step(graph, ServiceContainer.create(), {"tick": 1})

        state = WorldState.from_graph(graph, tick=1)  # must NOT raise
        assert state.territories["T001"].median_wage < 45000.0
        # computed output is per-tick: dropped on reconstruction
        assert not hasattr(state.territories["T001"], "wage_pressure")


class TestDispossessionOnProductionGraph:
    """DispossessionEventSystem matches the graph shape production writes."""

    def test_mutates_to_graph_shaped_territory(self) -> None:
        """The system matches lowercase ``_node_type='territory'`` nodes."""
        graph = _wayne_state().to_graph()
        DispossessionEventSystem().step(graph, ServiceContainer.create(), {"tick": 1})

        assert graph.nodes["T001"]["wealth"] < 500_000_000.0
        assert graph.nodes["T001"]["dispossession_intensity"] > 0.0

    def test_round_trip_survives_and_persists_wealth(self) -> None:
        """from_graph neither crashes nor loses the mutated wealth."""
        graph = _wayne_state().to_graph()
        DispossessionEventSystem().step(graph, ServiceContainer.create(), {"tick": 1})

        state = WorldState.from_graph(graph, tick=1)  # must NOT raise
        assert state.territories["T001"].wealth < 500_000_000.0
        # computed output is per-tick: dropped on reconstruction
        assert not hasattr(state.territories["T001"], "dispossession_intensity")


class TestFullTickLoop:
    """The real production seam — step() round-trips the graph every tick."""

    def test_wage_suppression_compounds_across_step_round_trips(self) -> None:
        """to_graph → all 26 systems → from_graph preserves compounding."""
        from babylon.engine.simulation_engine import step
        from babylon.models import SimulationConfig

        state = _wayne_state()
        config = SimulationConfig()
        wages = [state.territories["T001"].median_wage]
        for _ in range(3):
            state = step(state, config)
            wages.append(state.territories["T001"].median_wage)
        assert wages[0] > wages[1] > wages[2] > wages[3] > 0.0
