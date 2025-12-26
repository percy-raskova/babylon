Event System Reference
======================

This reference documents the typed event system that enables the AI narrative
layer to observe simulation state changes. For conceptual background, see
:doc:`/concepts/event-system`.

Overview
--------

The simulation emits typed Pydantic events during each tick. Events are
captured by the :class:`EventBus`, converted to typed models, and persisted
in :attr:`WorldState.events`. This enables:

- AI narrative generation from structured data
- Event-driven analysis and visualization
- Replay and counterfactual scenarios

**Key Components:**

- :py:mod:`babylon.models.events` - Pydantic event models (13 classes)
- :py:mod:`babylon.models.enums` - EventType enum (11 types)
- :py:mod:`babylon.engine.event_bus` - Pub/sub event bus
- :py:mod:`babylon.engine.simulation_engine` - Event conversion

EventType Enum
--------------

All events are categorized by type. The :class:`EventType` enum defines 11
distinct event types:

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - EventType
     - Category
     - Description
   * - ``SURPLUS_EXTRACTION``
     - Economic
     - Imperial rent extracted from worker
   * - ``IMPERIAL_SUBSIDY``
     - Economic
     - Subsidy paid to comprador state
   * - ``ECONOMIC_CRISIS``
     - Economic
     - Crisis event triggered
   * - ``CONSCIOUSNESS_TRANSMISSION``
     - Consciousness
     - Ideology transmitted via solidarity edge
   * - ``MASS_AWAKENING``
     - Consciousness
     - Class consciousness crosses threshold
   * - ``SOLIDARITY_AWAKENING``
     - Consciousness
     - Source enters active struggle
   * - ``EXCESSIVE_FORCE``
     - Struggle
     - Spark event (George Floyd Dynamic)
   * - ``UPRISING``
     - Struggle
     - Revolt triggered
   * - ``SOLIDARITY_SPIKE``
     - Struggle
     - Solidarity infrastructure built
   * - ``RUPTURE``
     - Contradiction
     - Tension reaches 1.0
   * - ``PHASE_TRANSITION``
     - Topology
     - Percolation state changes

Event Class Hierarchy
---------------------

Events form a type hierarchy with shared base classes:

.. code-block:: text

   SimulationEvent (base - frozen)
   |
   +-- EconomicEvent (amount: Currency)
   |   +-- ExtractionEvent (SURPLUS_EXTRACTION)
   |   +-- SubsidyEvent (IMPERIAL_SUBSIDY)
   |   +-- CrisisEvent (ECONOMIC_CRISIS)
   |
   +-- ConsciousnessEvent (target_id: str)
   |   +-- TransmissionEvent (CONSCIOUSNESS_TRANSMISSION)
   |   +-- MassAwakeningEvent (MASS_AWAKENING)
   |
   +-- StruggleEvent (node_id: str)
   |   +-- SparkEvent (EXCESSIVE_FORCE)
   |   +-- UprisingEvent (UPRISING)
   |   +-- SolidaritySpikeEvent (SOLIDARITY_SPIKE)
   |
   +-- ContradictionEvent (edge: str)
   |   +-- RuptureEvent (RUPTURE)
   |
   +-- TopologyEvent (percolation_ratio, num_components)
       +-- PhaseTransitionEvent (PHASE_TRANSITION)

Base Event Model
----------------

SimulationEvent
~~~~~~~~~~~~~~~

All events inherit from :class:`SimulationEvent`:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field
     - Type
     - Description
   * - ``event_type``
     - ``EventType``
     - Discriminator for event category
   * - ``tick``
     - ``int``
     - Simulation tick when event occurred
   * - ``timestamp``
     - ``datetime | None``
     - Optional wall-clock time

**Model Configuration:**

- ``frozen=True``: Events are immutable after creation
- ``extra="forbid"``: No additional fields allowed

Economic Events
---------------

Events related to value extraction and imperial rent dynamics.

EconomicEvent (Base)
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field
     - Type
     - Description
   * - ``amount``
     - ``Currency``
     - Value transferred in this event

ExtractionEvent
~~~~~~~~~~~~~~~

Emitted when imperial rent is extracted via EXPLOITATION edge.

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field
     - Type
     - Description
   * - ``event_type``
     - ``EventType``
     - Always ``SURPLUS_EXTRACTION``
   * - ``source_id``
     - ``str``
     - Worker node ID (extracted from)
   * - ``target_id``
     - ``str``
     - Owner node ID (extracted to)
   * - ``amount``
     - ``Currency``
     - Amount of rent extracted
   * - ``mechanism``
     - ``str``
     - Extraction mechanism (default: "imperial_rent")

**Example:**

.. code-block:: python

   from babylon.models.events import ExtractionEvent
   from babylon.models.enums import EventType

   event = ExtractionEvent(
       tick=5,
       source_id="C001",
       target_id="C002",
       amount=0.15,
       mechanism="imperial_rent",
   )
   assert event.event_type == EventType.SURPLUS_EXTRACTION

SubsidyEvent
~~~~~~~~~~~~

Emitted when imperial subsidy is paid via CLIENT_STATE edge.

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field
     - Type
     - Description
   * - ``event_type``
     - ``EventType``
     - Always ``IMPERIAL_SUBSIDY``
   * - ``source_id``
     - ``str``
     - Core bourgeoisie node ID
   * - ``target_id``
     - ``str``
     - Comprador state node ID
   * - ``amount``
     - ``Currency``
     - Subsidy amount
   * - ``repression_boost``
     - ``float``
     - Increase to target's repression capacity

CrisisEvent
~~~~~~~~~~~

Emitted when economic crisis conditions are detected.

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field
     - Type
     - Description
   * - ``event_type``
     - ``EventType``
     - Always ``ECONOMIC_CRISIS``
   * - ``pool_ratio``
     - ``float``
     - Current imperial rent pool ratio
   * - ``aggregate_tension``
     - ``float``
     - Total system tension
   * - ``decision``
     - ``str``
     - Bourgeoisie response (e.g., "AUSTERITY")
   * - ``wage_delta``
     - ``float``
     - Change in wage rates

Consciousness Events
--------------------

Events related to ideology drift and consciousness transmission.

ConsciousnessEvent (Base)
~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field
     - Type
     - Description
   * - ``target_id``
     - ``str``
     - Node whose consciousness is affected

TransmissionEvent
~~~~~~~~~~~~~~~~~

Emitted when consciousness is transmitted via SOLIDARITY edge.

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field
     - Type
     - Description
   * - ``event_type``
     - ``EventType``
     - Always ``CONSCIOUSNESS_TRANSMISSION``
   * - ``source_id``
     - ``str``
     - Transmitting node ID
   * - ``target_id``
     - ``str``
     - Receiving node ID
   * - ``delta``
     - ``float``
     - Consciousness change magnitude
   * - ``solidarity_strength``
     - ``float``
     - Edge strength facilitating transmission

MassAwakeningEvent
~~~~~~~~~~~~~~~~~~

Emitted when a node's consciousness crosses the awakening threshold.

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field
     - Type
     - Description
   * - ``event_type``
     - ``EventType``
     - Always ``MASS_AWAKENING``
   * - ``target_id``
     - ``str``
     - Awakened node ID
   * - ``old_consciousness``
     - ``float``
     - Consciousness before awakening
   * - ``new_consciousness``
     - ``float``
     - Consciousness after awakening
   * - ``triggering_source``
     - ``str``
     - Node that triggered awakening

Struggle Events
---------------

Events related to the Agency Layer (George Floyd Dynamic).

StruggleEvent (Base)
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field
     - Type
     - Description
   * - ``node_id``
     - ``str``
     - Node where struggle occurs

SparkEvent
~~~~~~~~~~

Emitted when EXCESSIVE_FORCE event occurs (stochastic police brutality).

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field
     - Type
     - Description
   * - ``event_type``
     - ``EventType``
     - Always ``EXCESSIVE_FORCE``
   * - ``node_id``
     - ``str``
     - Target of state violence
   * - ``repression``
     - ``float``
     - Repression level at node
   * - ``spark_probability``
     - ``float``
     - Probability that triggered event

UprisingEvent
~~~~~~~~~~~~~

Emitted when conditions trigger revolt.

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field
     - Type
     - Description
   * - ``event_type``
     - ``EventType``
     - Always ``UPRISING``
   * - ``node_id``
     - ``str``
     - Node where uprising occurs
   * - ``trigger``
     - ``str``
     - What triggered uprising (e.g., "spark", "p_rev")
   * - ``agitation``
     - ``float``
     - Agitation level at trigger
   * - ``repression``
     - ``float``
     - Repression level at trigger

SolidaritySpikeEvent
~~~~~~~~~~~~~~~~~~~~

Emitted when solidarity infrastructure is built during uprising.

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field
     - Type
     - Description
   * - ``event_type``
     - ``EventType``
     - Always ``SOLIDARITY_SPIKE``
   * - ``node_id``
     - ``str``
     - Node gaining solidarity
   * - ``solidarity_gained``
     - ``float``
     - Amount of solidarity added
   * - ``edges_affected``
     - ``int``
     - Number of edges strengthened
   * - ``triggered_by``
     - ``str``
     - Cause (e.g., "uprising")

Contradiction Events
--------------------

Events related to tension accumulation and rupture.

ContradictionEvent (Base)
~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field
     - Type
     - Description
   * - ``edge``
     - ``str``
     - Edge identifier (format: "source->target")

RuptureEvent
~~~~~~~~~~~~

Emitted when tension on an edge reaches 1.0.

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field
     - Type
     - Description
   * - ``event_type``
     - ``EventType``
     - Always ``RUPTURE``
   * - ``edge``
     - ``str``
     - Edge that ruptured

Topology Events
---------------

Events related to network structure and phase transitions.

TopologyEvent (Base)
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field
     - Type
     - Description
   * - ``percolation_ratio``
     - ``Probability``
     - L_max / total_nodes
   * - ``num_components``
     - ``int``
     - Number of disconnected components

PhaseTransitionEvent
~~~~~~~~~~~~~~~~~~~~

Emitted when percolation ratio crosses a threshold boundary.

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field
     - Type
     - Description
   * - ``event_type``
     - ``EventType``
     - Always ``PHASE_TRANSITION``
   * - ``previous_state``
     - ``str``
     - Previous phase ("gaseous", "transitional", "liquid")
   * - ``new_state``
     - ``str``
     - New phase after transition
   * - ``largest_component_size``
     - ``int``
     - Size of giant component (L_max)
   * - ``is_resilient``
     - ``bool | None``
     - Resilience test result (if available)

**Phase State Thresholds:**

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - State
     - Threshold
     - Meaning
   * - Gaseous
     - ``ratio < 0.1``
     - Atomized, no coordination capacity
   * - Transitional
     - ``0.1 <= ratio < 0.5``
     - Emerging structure, unstable
   * - Liquid
     - ``ratio >= 0.5``
     - Giant component, vanguard formation

Event Lifecycle
---------------

Events flow through the system in this sequence:

1. **Emission**: Systems call ``event_bus.publish(type, tick, payload)``
2. **Collection**: ``EventBus.get_history()`` returns all events for tick
3. **Conversion**: ``_convert_bus_event_to_pydantic()`` creates typed models
4. **Persistence**: Events appended to ``WorldState.events``
5. **Observation**: AI/narrative layer reads typed events

**Observer Events (Sprint 3.3):**

Observers like :class:`TopologyMonitor` emit events after the tick completes.
These are collected via ``get_pending_events()`` and injected into the
*next* tick's ``WorldState.events`` via ``persistent_context['_observer_events']``.

Factory Methods
---------------

The :class:`DomainFactory` provides factory methods for creating events in tests:

.. code-block:: python

   from tests.factories.domain import DomainFactory

   factory = DomainFactory()

   # Create events
   extraction = factory.create_extraction_event(tick=1, amount=0.1)
   subsidy = factory.create_subsidy_event(tick=1, amount=0.05)
   transmission = factory.create_transmission_event(tick=1, delta=0.1)
   spark = factory.create_spark_event(tick=1, repression=0.8)
   uprising = factory.create_uprising_event(tick=1, agitation=0.7)
   phase = factory.create_phase_transition_event(
       tick=1,
       previous_state="gaseous",
       new_state="liquid",
   )

Assertions
----------

The :class:`BabylonAssert` class provides semantic assertions for events:

.. code-block:: python

   from tests.assertions import Assert
   from babylon.models.events import ExtractionEvent

   # Assert event exists
   Assert(world_state).has_event(ExtractionEvent)

   # Assert event with specific fields
   Assert(world_state).has_event(
       ExtractionEvent,
       source_id="C001",
       target_id="C002",
   )

   # Assert event count
   Assert(world_state).has_events_count(3)

   # Assert amount condition
   Assert(world_state).has_event(ExtractionEvent, amount_gt=0.0)

See Also
--------

- :doc:`/concepts/event-system` - Conceptual explanation of event architecture
- :doc:`/reference/topology` - TopologyMonitor and phase transitions
- :doc:`/reference/systems` - Systems that emit events
- :py:mod:`babylon.engine.event_bus` - Event bus implementation
