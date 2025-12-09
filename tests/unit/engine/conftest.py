"""Minimal conftest for engine tests.

No database, no heavy fixtures. Pure unit tests.
"""

import pytest

from babylon.engine.scenarios import create_two_node_scenario
from babylon.engine.simulation import Simulation
from babylon.models.config import SimulationConfig
from babylon.models.world_state import WorldState


@pytest.fixture
def two_node_scenario() -> tuple[WorldState, SimulationConfig]:
    """Provide the standard two-node scenario (Worker vs Owner)."""
    return create_two_node_scenario()


@pytest.fixture
def simulation(two_node_scenario: tuple[WorldState, SimulationConfig]) -> Simulation:
    """Provide a fresh Simulation instance with the two-node scenario."""
    state, config = two_node_scenario
    return Simulation(initial_state=state, config=config)
