"""Pydantic event models for structured simulation events.

Sprint 3.1: Structured event persistence in WorldState.
Sprint 3.1+: Expanded event type hierarchy for all 10 EventTypes.

These models replace raw dict payloads with typed, immutable event objects.
Events are frozen Pydantic models that capture:

- tick: When the event occurred
- timestamp: Wall-clock time
- event_type: EventType enum value
- Additional type-specific fields

Design Principle: Events are IMMUTABLE FACTS about what happened.
They should never be modified after creation.

Event Hierarchy:

.. code-block:: text

    SimulationEvent (base)
      |-- EconomicEvent (adds amount)
      |     |-- ExtractionEvent (SURPLUS_EXTRACTION)
      |     |-- SubsidyEvent (IMPERIAL_SUBSIDY)
      |     |-- CrisisEvent (ECONOMIC_CRISIS)
      |-- ConsciousnessEvent (adds target_id)
      |     |-- TransmissionEvent (CONSCIOUSNESS_TRANSMISSION)
      |     |-- MassAwakeningEvent (MASS_AWAKENING)
      |-- StruggleEvent (adds node_id)
      |     |-- SparkEvent (EXCESSIVE_FORCE)
      |     |-- UprisingEvent (UPRISING)
      |     |-- SolidaritySpikeEvent (SOLIDARITY_SPIKE)
      |-- ContradictionEvent (adds edge)
            |-- RuptureEvent (RUPTURE)

Usage:

    from babylon.models.events import ExtractionEvent, UprisingEvent

    event = ExtractionEvent(
        tick=5,
        source_id="C001",
        target_id="C002",
        amount=10.5,
    )

    uprising = UprisingEvent(
        tick=8,
        node_id="C001",
        trigger="spark",
        agitation=0.9,
        repression=0.7,
    )

See Also:
    :class:`babylon.engine.event_bus.Event`: The EventBus dataclass (internal)
    :class:`babylon.models.world_state.WorldState`: Where events are stored
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.enums import EventType, GameOutcome
from babylon.models.types import Currency


class SimulationEvent(BaseModel):
    """Base class for all simulation events (immutable).

    All events share common fields for temporal tracking.
    Subclasses add domain-specific fields.

    Attributes:
        event_type: The type of event (from EventType enum).
        tick: Simulation tick when the event occurred (0-indexed).
        timestamp: Wall-clock time when event was created.

    Example:
        Subclasses should set a default event_type::

            class ExtractionEvent(EconomicEvent):
                event_type: EventType = Field(default=EventType.SURPLUS_EXTRACTION)
    """

    model_config = ConfigDict(frozen=True)

    event_type: EventType = Field(
        ...,
        description="Type of simulation event",
    )
    tick: int = Field(
        ge=0,
        description="Simulation tick when event occurred (0-indexed)",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Wall-clock time when event was created",
    )


class EconomicEvent(SimulationEvent):
    """Economic events involving value transfer.

    Base class for events that involve currency flow
    (extraction, tribute, wages, subsidies).

    Attributes:
        amount: Currency amount involved in the transaction.
    """

    amount: Currency = Field(
        ge=0.0,
        description="Currency amount involved in the transaction",
    )


class ExtractionEvent(EconomicEvent):
    """Imperial rent extraction event (SURPLUS_EXTRACTION).

    Emitted when imperial rent is extracted from a periphery worker
    by the core bourgeoisie via EXPLOITATION edges.

    Attributes:
        event_type: Always SURPLUS_EXTRACTION.
        source_id: Entity ID of the worker being extracted from.
        target_id: Entity ID of the bourgeoisie receiving rent.
        mechanism: Description of extraction mechanism (default: "imperial_rent").

    Example:
        >>> event = ExtractionEvent(
        ...     tick=5,
        ...     source_id="C001",
        ...     target_id="C002",
        ...     amount=15.5,
        ... )
        >>> event.event_type
        <EventType.SURPLUS_EXTRACTION: 'surplus_extraction'>
    """

    event_type: EventType = Field(
        default=EventType.SURPLUS_EXTRACTION,
        description="Event type (always SURPLUS_EXTRACTION)",
    )
    source_id: str = Field(
        ...,
        min_length=1,
        description="Entity ID of the worker being extracted from",
    )
    target_id: str = Field(
        ...,
        min_length=1,
        description="Entity ID of the bourgeoisie receiving rent",
    )
    mechanism: str = Field(
        default="imperial_rent",
        description="Description of extraction mechanism",
    )


class SubsidyEvent(EconomicEvent):
    """Imperial subsidy event (IMPERIAL_SUBSIDY).

    Emitted when the core bourgeoisie subsidizes a client state to
    maintain stability. Wealth converts to repression capacity.

    Attributes:
        event_type: Always IMPERIAL_SUBSIDY.
        source_id: Entity ID of the core bourgeoisie providing subsidy.
        target_id: Entity ID of the client state receiving subsidy.
        repression_boost: Amount of repression capacity gained.

    Example:
        >>> event = SubsidyEvent(
        ...     tick=5,
        ...     source_id="C002",
        ...     target_id="C003",
        ...     amount=100.0,
        ...     repression_boost=0.25,
        ... )
        >>> event.event_type
        <EventType.IMPERIAL_SUBSIDY: 'imperial_subsidy'>
    """

    event_type: EventType = Field(
        default=EventType.IMPERIAL_SUBSIDY,
        description="Event type (always IMPERIAL_SUBSIDY)",
    )
    source_id: str = Field(
        ...,
        min_length=1,
        description="Entity ID of the core bourgeoisie providing subsidy",
    )
    target_id: str = Field(
        ...,
        min_length=1,
        description="Entity ID of the client state receiving subsidy",
    )
    repression_boost: float = Field(
        ...,
        ge=0.0,
        description="Amount of repression capacity gained",
    )


class CrisisEvent(SimulationEvent):
    """Economic crisis event (ECONOMIC_CRISIS).

    Emitted when the imperial rent pool depletes below critical threshold,
    triggering bourgeoisie crisis response (wage cuts + repression).

    Attributes:
        event_type: Always ECONOMIC_CRISIS.
        pool_ratio: Current pool divided by initial pool.
        aggregate_tension: Average tension across all edges.
        decision: Bourgeoisie decision (CRISIS, AUSTERITY, IRON_FIST, etc).
        wage_delta: Change in wage rate (negative for cuts).

    Example:
        >>> event = CrisisEvent(
        ...     tick=10,
        ...     pool_ratio=0.15,
        ...     aggregate_tension=0.7,
        ...     decision="CRISIS",
        ...     wage_delta=-0.05,
        ... )
        >>> event.event_type
        <EventType.ECONOMIC_CRISIS: 'economic_crisis'>
    """

    event_type: EventType = Field(
        default=EventType.ECONOMIC_CRISIS,
        description="Event type (always ECONOMIC_CRISIS)",
    )
    pool_ratio: float = Field(
        ...,
        ge=0.0,
        description="Current pool divided by initial pool",
    )
    aggregate_tension: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average tension across all edges",
    )
    decision: str = Field(
        ...,
        min_length=1,
        description="Bourgeoisie decision (CRISIS, AUSTERITY, IRON_FIST, etc)",
    )
    wage_delta: float = Field(
        ...,
        description="Change in wage rate (negative for cuts)",
    )


# =============================================================================
# Carceral Equilibrium Events (Sprint 3.4+)
# =============================================================================


class SuperwageCrisisEvent(SimulationEvent):
    """Super-wage crisis event (SUPERWAGE_CRISIS).

    Emitted when the imperial rent pool is exhausted and core bourgeoisie
    can no longer afford to pay super-wages to the labor aristocracy.
    This triggers the Carceral Turn phase transition.

    Attributes:
        event_type: Always SUPERWAGE_CRISIS.
        payer_id: Entity ID of the bourgeoisie who can't pay.
        receiver_id: Entity ID of the labor aristocracy not receiving wages.
        desired_wages: Amount of wages that were needed.
        available_pool: Amount available in the rent pool (zero or negative).

    Example:
        >>> event = SuperwageCrisisEvent(
        ...     tick=1040,
        ...     payer_id="C003",
        ...     receiver_id="C004",
        ...     desired_wages=5.0,
        ...     available_pool=0.0,
        ... )
        >>> event.event_type
        <EventType.SUPERWAGE_CRISIS: 'superwage_crisis'>
    """

    event_type: EventType = Field(
        default=EventType.SUPERWAGE_CRISIS,
        description="Event type (always SUPERWAGE_CRISIS)",
    )
    payer_id: str = Field(
        ...,
        min_length=1,
        description="Entity ID of the bourgeoisie who can't pay",
    )
    receiver_id: str = Field(
        ...,
        min_length=1,
        description="Entity ID of the labor aristocracy not receiving wages",
    )
    desired_wages: float = Field(
        ...,
        ge=0.0,
        description="Amount of wages that were needed",
    )
    available_pool: float = Field(
        ...,
        description="Amount available in the rent pool",
    )


class ClassDecompositionEvent(SimulationEvent):
    """Class decomposition event (CLASS_DECOMPOSITION).

    Emitted when the labor aristocracy splits into CARCERAL_ENFORCER
    and INTERNAL_PROLETARIAT fractions after a super-wage crisis.

    Attributes:
        event_type: Always CLASS_DECOMPOSITION.
        original_id: Entity ID of the labor aristocracy that split.
        enforcer_fraction: Fraction that became enforcers (default 0.3).
        proletariat_fraction: Fraction that became internal proletariat (0.7).

    Example:
        >>> event = ClassDecompositionEvent(
        ...     tick=1092,
        ...     original_id="C004",
        ...     enforcer_fraction=0.3,
        ...     proletariat_fraction=0.7,
        ... )
    """

    event_type: EventType = Field(
        default=EventType.CLASS_DECOMPOSITION,
        description="Event type (always CLASS_DECOMPOSITION)",
    )
    original_id: str = Field(
        ...,
        min_length=1,
        description="Entity ID of the labor aristocracy that split",
    )
    enforcer_fraction: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Fraction that became enforcers",
    )
    proletariat_fraction: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Fraction that became internal proletariat",
    )


class ControlRatioCrisisEvent(SimulationEvent):
    """Control ratio crisis event (CONTROL_RATIO_CRISIS).

    Emitted when the prisoner-to-guard ratio exceeds capacity,
    meaning the carceral apparatus can no longer contain the surplus population.

    Attributes:
        event_type: Always CONTROL_RATIO_CRISIS.
        prisoner_population: Size of the prisoner/surplus population.
        enforcer_population: Size of the enforcer/guard population.
        control_ratio: Prisoners per enforcer.
        capacity_threshold: Maximum ratio enforcers can handle.

    Example:
        >>> event = ControlRatioCrisisEvent(
        ...     tick=2340,
        ...     prisoner_population=1000,
        ...     enforcer_population=100,
        ...     control_ratio=10.0,
        ...     capacity_threshold=5.0,
        ... )
    """

    event_type: EventType = Field(
        default=EventType.CONTROL_RATIO_CRISIS,
        description="Event type (always CONTROL_RATIO_CRISIS)",
    )
    prisoner_population: int = Field(
        ...,
        ge=0,
        description="Size of the prisoner/surplus population",
    )
    enforcer_population: int = Field(
        ...,
        ge=0,
        description="Size of the enforcer/guard population",
    )
    control_ratio: float = Field(
        ...,
        ge=0.0,
        description="Prisoners per enforcer",
    )
    capacity_threshold: float = Field(
        ...,
        ge=0.0,
        description="Maximum ratio enforcers can handle",
    )


class TerminalDecisionEvent(SimulationEvent):
    """Terminal decision event (TERMINAL_DECISION).

    Emitted when the system bifurcates to either revolution or genocide
    based on the organization level of the surplus population.

    Attributes:
        event_type: Always TERMINAL_DECISION.
        outcome: Either "revolution" or "genocide".
        avg_organization: Average organization level of prisoners.
        revolution_threshold: Threshold above which revolution occurs.

    Example:
        >>> event = TerminalDecisionEvent(
        ...     tick=2860,
        ...     outcome="revolution",
        ...     avg_organization=0.65,
        ...     revolution_threshold=0.6,
        ... )
    """

    event_type: EventType = Field(
        default=EventType.TERMINAL_DECISION,
        description="Event type (always TERMINAL_DECISION)",
    )
    outcome: str = Field(
        ...,
        pattern="^(revolution|genocide)$",
        description="Terminal outcome: revolution or genocide",
    )
    avg_organization: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average organization level of prisoners",
    )
    revolution_threshold: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Threshold above which revolution occurs",
    )


# =============================================================================
# Consciousness Events
# =============================================================================


class ConsciousnessEvent(SimulationEvent):
    """Base class for consciousness-related events.

    Events involving changes to class consciousness or ideological state.

    Attributes:
        target_id: Entity whose consciousness changed.
    """

    target_id: str = Field(
        ...,
        min_length=1,
        description="Entity ID whose consciousness changed",
    )


class TransmissionEvent(ConsciousnessEvent):
    """Consciousness transmission event (CONSCIOUSNESS_TRANSMISSION).

    Emitted when class consciousness flows from a revolutionary periphery
    worker to a core worker via SOLIDARITY edges.

    Attributes:
        event_type: Always CONSCIOUSNESS_TRANSMISSION.
        source_id: Entity transmitting consciousness.
        delta: Amount of consciousness transmitted.
        solidarity_strength: Strength of the solidarity edge.

    Example:
        >>> event = TransmissionEvent(
        ...     tick=3,
        ...     target_id="C001",
        ...     source_id="C002",
        ...     delta=0.05,
        ...     solidarity_strength=0.8,
        ... )
        >>> event.event_type
        <EventType.CONSCIOUSNESS_TRANSMISSION: 'consciousness_transmission'>
    """

    event_type: EventType = Field(
        default=EventType.CONSCIOUSNESS_TRANSMISSION,
        description="Event type (always CONSCIOUSNESS_TRANSMISSION)",
    )
    source_id: str = Field(
        ...,
        min_length=1,
        description="Entity ID transmitting consciousness",
    )
    delta: float = Field(
        ...,
        description="Amount of consciousness transmitted",
    )
    solidarity_strength: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Strength of the solidarity edge",
    )


class MassAwakeningEvent(ConsciousnessEvent):
    """Mass awakening event (MASS_AWAKENING).

    Emitted when an entity's consciousness crosses the mass awakening
    threshold, signifying a qualitative shift in class consciousness.

    Attributes:
        event_type: Always MASS_AWAKENING.
        old_consciousness: Consciousness before awakening.
        new_consciousness: Consciousness after awakening.
        triggering_source: Entity that triggered the awakening.

    Example:
        >>> event = MassAwakeningEvent(
        ...     tick=7,
        ...     target_id="C001",
        ...     old_consciousness=0.4,
        ...     new_consciousness=0.7,
        ...     triggering_source="C002",
        ... )
        >>> event.event_type
        <EventType.MASS_AWAKENING: 'mass_awakening'>
    """

    event_type: EventType = Field(
        default=EventType.MASS_AWAKENING,
        description="Event type (always MASS_AWAKENING)",
    )
    old_consciousness: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Consciousness before awakening",
    )
    new_consciousness: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Consciousness after awakening",
    )
    triggering_source: str = Field(
        ...,
        min_length=1,
        description="Entity ID that triggered the awakening",
    )


# =============================================================================
# Struggle Events (Agency Layer - George Floyd Dynamic)
# =============================================================================


class StruggleEvent(SimulationEvent):
    """Base class for struggle events (Agency Layer).

    Events from the George Floyd Dynamic: Spark + Fuel = Explosion.

    Attributes:
        node_id: Entity where the struggle event occurred.
    """

    node_id: str = Field(
        ...,
        min_length=1,
        description="Entity ID where struggle occurred",
    )


class SparkEvent(StruggleEvent):
    """Excessive force spark event (EXCESSIVE_FORCE).

    Emitted when state violence (police brutality) occurs. This is
    the "spark" that can ignite an uprising if conditions are right.

    Attributes:
        event_type: Always EXCESSIVE_FORCE.
        repression: Current repression level faced by the entity.
        spark_probability: Probability that led to this spark.

    Example:
        >>> event = SparkEvent(
        ...     tick=5,
        ...     node_id="C001",
        ...     repression=0.8,
        ...     spark_probability=0.4,
        ... )
        >>> event.event_type
        <EventType.EXCESSIVE_FORCE: 'excessive_force'>
    """

    event_type: EventType = Field(
        default=EventType.EXCESSIVE_FORCE,
        description="Event type (always EXCESSIVE_FORCE)",
    )
    repression: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Current repression level faced by the entity",
    )
    spark_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Probability that led to this spark",
    )


class UprisingEvent(StruggleEvent):
    """Uprising event (UPRISING).

    Emitted when a spark + accumulated agitation triggers mass insurrection.
    The "explosion" in the George Floyd Dynamic.

    Attributes:
        event_type: Always UPRISING.
        trigger: What caused the uprising ("spark" or "revolutionary_pressure").
        agitation: Accumulated agitation level.
        repression: Current repression level.

    Example:
        >>> event = UprisingEvent(
        ...     tick=8,
        ...     node_id="C001",
        ...     trigger="spark",
        ...     agitation=0.9,
        ...     repression=0.7,
        ... )
        >>> event.event_type
        <EventType.UPRISING: 'uprising'>
    """

    event_type: EventType = Field(
        default=EventType.UPRISING,
        description="Event type (always UPRISING)",
    )
    trigger: str = Field(
        ...,
        min_length=1,
        description="What caused the uprising (spark or revolutionary_pressure)",
    )
    agitation: float = Field(
        ...,
        ge=0.0,
        description="Accumulated agitation level",
    )
    repression: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Current repression level",
    )


class SolidaritySpikeEvent(StruggleEvent):
    """Solidarity spike event (SOLIDARITY_SPIKE).

    Emitted when solidarity infrastructure is built through shared struggle.
    The lasting result of an uprising that enables future consciousness
    transmission.

    Attributes:
        event_type: Always SOLIDARITY_SPIKE.
        solidarity_gained: Total solidarity strength gained.
        edges_affected: Number of solidarity edges strengthened.
        triggered_by: What caused the spike (e.g., "uprising").

    Example:
        >>> event = SolidaritySpikeEvent(
        ...     tick=6,
        ...     node_id="C001",
        ...     solidarity_gained=0.3,
        ...     edges_affected=2,
        ...     triggered_by="uprising",
        ... )
        >>> event.event_type
        <EventType.SOLIDARITY_SPIKE: 'solidarity_spike'>
    """

    event_type: EventType = Field(
        default=EventType.SOLIDARITY_SPIKE,
        description="Event type (always SOLIDARITY_SPIKE)",
    )
    solidarity_gained: float = Field(
        ...,
        ge=0.0,
        description="Total solidarity strength gained",
    )
    edges_affected: int = Field(
        ...,
        ge=0,
        description="Number of solidarity edges strengthened",
    )
    triggered_by: str = Field(
        ...,
        min_length=1,
        description="What caused the spike (e.g., uprising)",
    )


# =============================================================================
# Contradiction Events
# =============================================================================


class ContradictionEvent(SimulationEvent):
    """Base class for dialectical contradiction events.

    Events from tension dynamics and phase transitions.

    Attributes:
        edge: The edge where the contradiction occurred (format: "source->target").
    """

    edge: str = Field(
        ...,
        min_length=1,
        description="Edge where contradiction occurred (format: source->target)",
    )


class RuptureEvent(ContradictionEvent):
    """Rupture event (RUPTURE).

    Emitted when tension on an edge reaches the critical threshold (1.0),
    triggering a phase transition. This represents the dialectical moment
    when accumulated contradictions become irreconcilable.

    Attributes:
        event_type: Always RUPTURE.

    Example:
        >>> event = RuptureEvent(
        ...     tick=12,
        ...     edge="C001->C002",
        ... )
        >>> event.event_type
        <EventType.RUPTURE: 'rupture'>
    """

    event_type: EventType = Field(
        default=EventType.RUPTURE,
        description="Event type (always RUPTURE)",
    )


# =============================================================================
# Topology Events (Sprint 3.3)
# =============================================================================


class TopologyEvent(SimulationEvent):
    """Events related to network topology analysis.

    Base class for percolation theory metrics and phase transition detection.
    Tracks the state of the solidarity network structure.

    Attributes:
        percolation_ratio: Ratio of largest component to total nodes (L_max / N).
        num_components: Number of disconnected solidarity components.
    """

    percolation_ratio: float = Field(
        ge=0.0,
        le=1.0,
        description="Ratio of largest component to total nodes",
    )
    num_components: int = Field(
        ge=0,
        description="Number of disconnected solidarity components",
    )


class PhaseTransitionEvent(TopologyEvent):
    """Phase transition detected in solidarity network.

    Emitted when percolation_ratio crosses threshold boundaries.

    4-Phase Model:
        - Gaseous (ratio < 0.1): Atomized, no coordination
        - Transitional (0.1 <= ratio < 0.5): Emerging structure
        - Liquid (ratio >= 0.5, cadre_density < 0.5): Mass movement (weak ties)
        - Solid (ratio >= 0.5, cadre_density >= 0.5): Vanguard party (strong ties)

    Attributes:
        event_type: Always PHASE_TRANSITION.
        previous_state: Phase before transition ("gaseous", "transitional", "liquid", "solid").
        new_state: Phase after transition.
        largest_component_size: Size of the giant component (L_max).
        cadre_density: Ratio of cadre to sympathizers (actual/potential liquidity).
        is_resilient: Whether network survives 20% node removal (Sword of Damocles test).

    Example:
        >>> event = PhaseTransitionEvent(
        ...     tick=10,
        ...     previous_state="gaseous",
        ...     new_state="liquid",
        ...     percolation_ratio=0.6,
        ...     num_components=2,
        ...     largest_component_size=12,
        ... )
        >>> event.event_type
        <EventType.PHASE_TRANSITION: 'phase_transition'>
    """

    event_type: EventType = Field(
        default=EventType.PHASE_TRANSITION,
        description="Event type (always PHASE_TRANSITION)",
    )
    previous_state: str = Field(
        ...,
        min_length=1,
        description="Phase before transition (gaseous, transitional, liquid, solid)",
    )
    new_state: str = Field(
        ...,
        min_length=1,
        description="Phase after transition (gaseous, transitional, liquid, solid)",
    )
    largest_component_size: int = Field(
        ge=0,
        description="Size of the largest connected component (L_max)",
    )
    cadre_density: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Ratio of cadre to sympathizers (actual/potential liquidity)",
    )
    is_resilient: bool | None = Field(
        default=None,
        description="Whether network survives purge (may be None if test not run)",
    )


# =============================================================================
# Endgame Events (Slice 1.6)
# =============================================================================


class EndgameEvent(SimulationEvent):
    """Endgame reached event (ENDGAME_REACHED).

    Emitted when a game-ending condition is met. The simulation terminates
    after this event with the specified outcome.

    Outcomes:
        - REVOLUTIONARY_VICTORY: Proletarian revolution succeeded
        - ECOLOGICAL_COLLAPSE: Metabolic rift has become fatal
        - FASCIST_CONSOLIDATION: Fascism has consolidated power

    Attributes:
        event_type: Always ENDGAME_REACHED.
        outcome: The GameOutcome that ended the simulation.

    Example:
        >>> event = EndgameEvent(
        ...     tick=50,
        ...     outcome=GameOutcome.REVOLUTIONARY_VICTORY,
        ... )
        >>> event.event_type
        <EventType.ENDGAME_REACHED: 'endgame_reached'>
    """

    event_type: EventType = Field(
        default=EventType.ENDGAME_REACHED,
        description="Event type (always ENDGAME_REACHED)",
    )
    outcome: GameOutcome = Field(
        ...,
        description="The game outcome that ended the simulation",
    )
