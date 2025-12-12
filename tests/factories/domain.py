"""Domain factory for creating test entities.

This module provides the DomainFactory class, which creates properly configured
domain objects for testing. It consolidates duplicate fixture definitions
from across the test suite into a single, reusable API.

The factory methods use sensible defaults that can be overridden via kwargs.
This enables tests to express only the differences that matter for their
specific scenario.

Example::

    factory = DomainFactory()

    # Create with defaults
    worker = factory.create_worker()

    # Override specific fields
    wealthy_worker = factory.create_worker(wealth=100.0)

    # Create a complete world state
    state = factory.create_world_state(
        entities={"C001": worker, "C002": factory.create_owner()},
        relationships=[factory.create_relationship()]
    )
"""

from babylon.models import (
    EdgeType,
    Relationship,
    SocialClass,
    SocialRole,
    WorldState,
)


class DomainFactory:
    """Factory for creating test domain objects with sensible defaults.

    This factory consolidates the test fixture patterns used throughout
    the test suite. Each method creates a domain object with defaults
    that match common test scenarios.

    The defaults are:

    Worker (create_worker):
        - id: "C001"
        - name: "Test Worker"
        - role: PERIPHERY_PROLETARIAT
        - wealth: 0.5
        - ideology: 0.0 (neutral)
        - organization: 0.1
        - repression_faced: 0.5
        - subsistence_threshold: 0.3

    Owner (create_owner):
        - id: "C002"
        - name: "Test Owner"
        - role: CORE_BOURGEOISIE
        - wealth: 10.0
        - ideology: 0.5 (neutral)
        - organization: 0.7
        - repression_faced: 0.1
        - subsistence_threshold: 0.1

    Relationship (create_relationship):
        - source_id: "C001"
        - target_id: "C002"
        - edge_type: EXPLOITATION
        - value_flow: 0.0
        - tension: 0.0
    """

    def create_worker(
        self,
        *,
        id: str = "C001",
        name: str = "Test Worker",
        role: SocialRole = SocialRole.PERIPHERY_PROLETARIAT,
        wealth: float = 0.5,
        ideology: float = 0.0,
        organization: float = 0.1,
        repression_faced: float = 0.5,
        subsistence_threshold: float = 0.3,
    ) -> SocialClass:
        """Create a worker social class with test defaults.

        Args:
            id: Entity identifier (default: "C001").
            name: Human-readable name (default: "Test Worker").
            role: Social role in world system (default: PERIPHERY_PROLETARIAT).
            wealth: Economic resources (default: 0.5).
            ideology: Legacy ideology scalar [-1, 1] (default: 0.0 neutral).
            organization: Collective cohesion (default: 0.1).
            repression_faced: State violence level (default: 0.5).
            subsistence_threshold: Minimum wealth for survival (default: 0.3).

        Returns:
            SocialClass configured as a worker.
        """
        return SocialClass(
            id=id,
            name=name,
            role=role,
            wealth=wealth,
            ideology=ideology,  # type: ignore[arg-type]  # Validator converts float to IdeologicalProfile
            organization=organization,
            repression_faced=repression_faced,
            subsistence_threshold=subsistence_threshold,
        )

    def create_owner(
        self,
        *,
        id: str = "C002",
        name: str = "Test Owner",
        role: SocialRole = SocialRole.CORE_BOURGEOISIE,
        wealth: float = 10.0,
        ideology: float = 0.5,
        organization: float = 0.7,
        repression_faced: float = 0.1,
        subsistence_threshold: float = 0.1,
    ) -> SocialClass:
        """Create an owner social class with test defaults.

        Args:
            id: Entity identifier (default: "C002").
            name: Human-readable name (default: "Test Owner").
            role: Social role in world system (default: CORE_BOURGEOISIE).
            wealth: Economic resources (default: 10.0).
            ideology: Legacy ideology scalar [-1, 1] (default: 0.5 neutral).
            organization: Collective cohesion (default: 0.7).
            repression_faced: State violence level (default: 0.1).
            subsistence_threshold: Minimum wealth for survival (default: 0.1).

        Returns:
            SocialClass configured as an owner.
        """
        return SocialClass(
            id=id,
            name=name,
            role=role,
            wealth=wealth,
            ideology=ideology,  # type: ignore[arg-type]  # Validator converts float to IdeologicalProfile
            organization=organization,
            repression_faced=repression_faced,
            subsistence_threshold=subsistence_threshold,
        )

    def create_relationship(
        self,
        *,
        source_id: str = "C001",
        target_id: str = "C002",
        edge_type: EdgeType = EdgeType.EXPLOITATION,
        value_flow: float = 0.0,
        tension: float = 0.0,
    ) -> Relationship:
        """Create a relationship edge with test defaults.

        Args:
            source_id: Origin entity ID (default: "C001").
            target_id: Destination entity ID (default: "C002").
            edge_type: Nature of relationship (default: EXPLOITATION).
            value_flow: Imperial rent amount (default: 0.0).
            tension: Dialectical tension (default: 0.0).

        Returns:
            Relationship configured with given parameters.
        """
        return Relationship(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            value_flow=value_flow,
            tension=tension,
        )

    def create_world_state(
        self,
        *,
        tick: int = 0,
        entities: dict[str, SocialClass] | None = None,
        relationships: list[Relationship] | None = None,
        event_log: list[str] | None = None,
    ) -> WorldState:
        """Create a world state with test defaults.

        Args:
            tick: Current turn number (default: 0).
            entities: Map of entity ID to SocialClass (default: empty dict).
            relationships: List of relationships (default: empty list).
            event_log: List of events (default: empty list).

        Returns:
            WorldState configured with given parameters.
        """
        return WorldState(
            tick=tick,
            entities=entities if entities is not None else {},
            relationships=relationships if relationships is not None else [],
            event_log=event_log if event_log is not None else [],
        )
