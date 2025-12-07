"""Shared fixtures for history module tests.

Provides common WorldState and SimulationConfig instances for testing
the history stack, checkpointing, and I/O functionality.
"""

from datetime import UTC, datetime

import pytest

from babylon.models import (
    EdgeType,
    Relationship,
    SimulationConfig,
    SocialClass,
    SocialRole,
    WorldState,
)


@pytest.fixture
def worker() -> SocialClass:
    """Create a periphery worker social class."""
    return SocialClass(
        id="C001",
        name="Periphery Worker",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=0.5,
        ideology=0.0,
        organization=0.1,
        repression_faced=0.5,
    )


@pytest.fixture
def owner() -> SocialClass:
    """Create a core owner social class."""
    return SocialClass(
        id="C002",
        name="Core Owner",
        role=SocialRole.CORE_BOURGEOISIE,
        wealth=0.9,
        ideology=0.0,
        organization=0.8,
        repression_faced=0.1,
    )


@pytest.fixture
def exploitation_edge() -> Relationship:
    """Create an exploitation relationship from worker to owner."""
    return Relationship(
        source_id="C001",
        target_id="C002",
        edge_type=EdgeType.EXPLOITATION,
        value_flow=0.2,
        tension=0.3,
    )


@pytest.fixture
def sample_world_state(
    worker: SocialClass,
    owner: SocialClass,
    exploitation_edge: Relationship,
) -> WorldState:
    """Create a minimal WorldState with two nodes and one edge."""
    return WorldState(
        tick=0,
        entities={"C001": worker, "C002": owner},
        relationships=[exploitation_edge],
        event_log=["Initial state created"],
    )


@pytest.fixture
def sample_config() -> SimulationConfig:
    """Create a default SimulationConfig."""
    return SimulationConfig()


@pytest.fixture
def sample_datetime() -> datetime:
    """Create a fixed datetime for deterministic tests."""
    return datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
