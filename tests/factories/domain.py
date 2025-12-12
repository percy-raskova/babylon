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
from babylon.models.events import (
    CrisisEvent,
    ExtractionEvent,
    MassAwakeningEvent,
    PhaseTransitionEvent,
    RuptureEvent,
    SimulationEvent,
    SolidaritySpikeEvent,
    SparkEvent,
    SubsidyEvent,
    TransmissionEvent,
    UprisingEvent,
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
        solidarity_strength: float = 0.0,
    ) -> Relationship:
        """Create a relationship edge with test defaults.

        Args:
            source_id: Origin entity ID (default: "C001").
            target_id: Destination entity ID (default: "C002").
            edge_type: Nature of relationship (default: EXPLOITATION).
            value_flow: Imperial rent amount (default: 0.0).
            tension: Dialectical tension (default: 0.0).
            solidarity_strength: Strength of solidarity edge (default: 0.0).
                For SOLIDARITY edges, set > 0.1 to count as potential,
                > 0.5 to count as actual in topology metrics.

        Returns:
            Relationship configured with given parameters.
        """
        return Relationship(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            value_flow=value_flow,
            tension=tension,
            solidarity_strength=solidarity_strength,
        )

    def create_world_state(
        self,
        *,
        tick: int = 0,
        entities: dict[str, SocialClass] | None = None,
        relationships: list[Relationship] | None = None,
        event_log: list[str] | None = None,
        events: list[SimulationEvent] | None = None,
    ) -> WorldState:
        """Create a world state with test defaults.

        Args:
            tick: Current turn number (default: 0).
            entities: Map of entity ID to SocialClass (default: empty dict).
            relationships: List of relationships (default: empty list).
            event_log: List of string events (default: empty list).
            events: List of structured SimulationEvent objects (default: empty list).

        Returns:
            WorldState configured with given parameters.
        """
        return WorldState(
            tick=tick,
            entities=entities if entities is not None else {},
            relationships=relationships if relationships is not None else [],
            event_log=event_log if event_log is not None else [],
            events=events if events is not None else [],
        )

    def create_extraction_event(
        self,
        *,
        tick: int = 0,
        source_id: str = "C001",
        target_id: str = "C002",
        amount: float = 1.0,
        mechanism: str = "imperial_rent",
    ) -> ExtractionEvent:
        """Create an extraction event with test defaults.

        Args:
            tick: Simulation tick when event occurred (default: 0).
            source_id: Entity ID of the worker being extracted from (default: "C001").
            target_id: Entity ID of the bourgeoisie receiving rent (default: "C002").
            amount: Currency amount extracted (default: 1.0).
            mechanism: Extraction mechanism description (default: "imperial_rent").

        Returns:
            ExtractionEvent configured with given parameters.
        """
        return ExtractionEvent(
            tick=tick,
            source_id=source_id,
            target_id=target_id,
            amount=amount,
            mechanism=mechanism,
        )

    def create_subsidy_event(
        self,
        *,
        tick: int = 0,
        source_id: str = "C002",
        target_id: str = "C003",
        amount: float = 50.0,
        repression_boost: float = 0.15,
    ) -> SubsidyEvent:
        """Create a subsidy event with test defaults.

        Args:
            tick: Simulation tick when event occurred (default: 0).
            source_id: Entity ID of the core bourgeoisie (default: "C002").
            target_id: Entity ID of the client state (default: "C003").
            amount: Currency amount of subsidy (default: 50.0).
            repression_boost: Repression capacity gained (default: 0.15).

        Returns:
            SubsidyEvent configured with given parameters.
        """
        return SubsidyEvent(
            tick=tick,
            source_id=source_id,
            target_id=target_id,
            amount=amount,
            repression_boost=repression_boost,
        )

    def create_crisis_event(
        self,
        *,
        tick: int = 0,
        pool_ratio: float = 0.2,
        aggregate_tension: float = 0.6,
        decision: str = "CRISIS",
        wage_delta: float = -0.05,
    ) -> CrisisEvent:
        """Create a crisis event with test defaults.

        Args:
            tick: Simulation tick when event occurred (default: 0).
            pool_ratio: Current pool divided by initial pool (default: 0.2).
            aggregate_tension: Average tension across edges (default: 0.6).
            decision: Bourgeoisie decision type (default: "CRISIS").
            wage_delta: Change in wage rate (default: -0.05).

        Returns:
            CrisisEvent configured with given parameters.
        """
        return CrisisEvent(
            tick=tick,
            pool_ratio=pool_ratio,
            aggregate_tension=aggregate_tension,
            decision=decision,
            wage_delta=wage_delta,
        )

    def create_transmission_event(
        self,
        *,
        tick: int = 0,
        source_id: str = "C001",
        target_id: str = "C002",
        delta: float = 0.05,
        solidarity_strength: float = 0.5,
    ) -> TransmissionEvent:
        """Create a transmission event with test defaults.

        Args:
            tick: Simulation tick when event occurred (default: 0).
            source_id: Entity transmitting consciousness (default: "C001").
            target_id: Entity receiving consciousness (default: "C002").
            delta: Amount of consciousness transmitted (default: 0.05).
            solidarity_strength: Strength of solidarity edge (default: 0.5).

        Returns:
            TransmissionEvent configured with given parameters.
        """
        return TransmissionEvent(
            tick=tick,
            source_id=source_id,
            target_id=target_id,
            delta=delta,
            solidarity_strength=solidarity_strength,
        )

    def create_mass_awakening_event(
        self,
        *,
        tick: int = 0,
        target_id: str = "C001",
        old_consciousness: float = 0.4,
        new_consciousness: float = 0.7,
        triggering_source: str = "C002",
    ) -> MassAwakeningEvent:
        """Create a mass awakening event with test defaults.

        Args:
            tick: Simulation tick when event occurred (default: 0).
            target_id: Entity whose consciousness crossed threshold (default: "C001").
            old_consciousness: Consciousness before awakening (default: 0.4).
            new_consciousness: Consciousness after awakening (default: 0.7).
            triggering_source: Entity that triggered awakening (default: "C002").

        Returns:
            MassAwakeningEvent configured with given parameters.
        """
        return MassAwakeningEvent(
            tick=tick,
            target_id=target_id,
            old_consciousness=old_consciousness,
            new_consciousness=new_consciousness,
            triggering_source=triggering_source,
        )

    def create_spark_event(
        self,
        *,
        tick: int = 0,
        node_id: str = "C001",
        repression: float = 0.7,
        spark_probability: float = 0.35,
    ) -> SparkEvent:
        """Create a spark event with test defaults.

        Args:
            tick: Simulation tick when event occurred (default: 0).
            node_id: Entity where spark occurred (default: "C001").
            repression: Repression level faced (default: 0.7).
            spark_probability: Probability that led to spark (default: 0.35).

        Returns:
            SparkEvent configured with given parameters.
        """
        return SparkEvent(
            tick=tick,
            node_id=node_id,
            repression=repression,
            spark_probability=spark_probability,
        )

    def create_uprising_event(
        self,
        *,
        tick: int = 0,
        node_id: str = "C001",
        trigger: str = "spark",
        agitation: float = 0.8,
        repression: float = 0.6,
    ) -> UprisingEvent:
        """Create an uprising event with test defaults.

        Args:
            tick: Simulation tick when event occurred (default: 0).
            node_id: Entity where uprising occurred (default: "C001").
            trigger: What caused the uprising (default: "spark").
            agitation: Accumulated agitation level (default: 0.8).
            repression: Current repression level (default: 0.6).

        Returns:
            UprisingEvent configured with given parameters.
        """
        return UprisingEvent(
            tick=tick,
            node_id=node_id,
            trigger=trigger,
            agitation=agitation,
            repression=repression,
        )

    def create_solidarity_spike_event(
        self,
        *,
        tick: int = 0,
        node_id: str = "C001",
        solidarity_gained: float = 0.2,
        edges_affected: int = 2,
        triggered_by: str = "uprising",
    ) -> SolidaritySpikeEvent:
        """Create a solidarity spike event with test defaults.

        Args:
            tick: Simulation tick when event occurred (default: 0).
            node_id: Entity where spike occurred (default: "C001").
            solidarity_gained: Total solidarity gained (default: 0.2).
            edges_affected: Number of edges strengthened (default: 2).
            triggered_by: What caused the spike (default: "uprising").

        Returns:
            SolidaritySpikeEvent configured with given parameters.
        """
        return SolidaritySpikeEvent(
            tick=tick,
            node_id=node_id,
            solidarity_gained=solidarity_gained,
            edges_affected=edges_affected,
            triggered_by=triggered_by,
        )

    def create_rupture_event(
        self,
        *,
        tick: int = 0,
        edge: str = "C001->C002",
    ) -> RuptureEvent:
        """Create a rupture event with test defaults.

        Args:
            tick: Simulation tick when event occurred (default: 0).
            edge: Edge where rupture occurred (default: "C001->C002").

        Returns:
            RuptureEvent configured with given parameters.
        """
        return RuptureEvent(
            tick=tick,
            edge=edge,
        )

    def create_phase_transition_event(
        self,
        *,
        tick: int = 0,
        previous_state: str = "gaseous",
        new_state: str = "liquid",
        percolation_ratio: float = 0.5,
        num_components: int = 1,
        largest_component_size: int = 5,
        is_resilient: bool | None = None,
    ) -> PhaseTransitionEvent:
        """Create a phase transition event with test defaults.

        Args:
            tick: Simulation tick when event occurred (default: 0).
            previous_state: Phase before transition (default: "gaseous").
            new_state: Phase after transition (default: "liquid").
            percolation_ratio: L_max / N ratio (default: 0.5).
            num_components: Number of components (default: 1).
            largest_component_size: Size of L_max (default: 5).
            is_resilient: Whether network survives purge (default: None).

        Returns:
            PhaseTransitionEvent configured with given parameters.
        """
        return PhaseTransitionEvent(
            tick=tick,
            previous_state=previous_state,
            new_state=new_state,
            percolation_ratio=percolation_ratio,
            num_components=num_components,
            largest_component_size=largest_component_size,
            is_resilient=is_resilient,
        )
