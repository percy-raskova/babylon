"""Pydantic event models for structured simulation events.

Sprint 3.1: Structured event persistence in WorldState.

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
      |     |-- SubsidyEvent (IMPERIAL_SUBSIDY) [future]
      |-- ConsciousnessEvent [future]
      |-- StruggleEvent [future]

Usage:

    from babylon.models.events import ExtractionEvent

    event = ExtractionEvent(
        tick=5,
        source_id="C001",
        target_id="C002",
        amount=10.5,
    )

See Also:
    :class:`babylon.engine.event_bus.Event`: The EventBus dataclass (internal)
    :class:`babylon.models.world_state.WorldState`: Where events are stored
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.enums import EventType
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
