Event System Architecture
=========================

The Babylon simulation emits typed events to enable the AI narrative layer
to observe state changes without coupling to the simulation internals. This
document explains the conceptual architecture of the event system.

For technical reference, see :doc:`/reference/events`.

The Observer Pattern
--------------------

The event system implements the Observer pattern at the architecture level:

.. code-block:: text

   +------------------+     publishes      +-------------+
   |   Systems        | -----------------> |  EventBus   |
   | (ImperialRent,   |                    |  (pub/sub)  |
   |  Struggle, etc.) |                    +-------------+
   +------------------+                           |
                                                  | collects
                                                  v
   +------------------+     conversion     +-------------+
   |   WorldState     | <----------------- | step()      |
   |   .events[]      |                    | function    |
   +------------------+                    +-------------+
           |
           | reads
           v
   +------------------+
   |   AI Narrative   |
   |   Layer          |
   +------------------+

**Key Principle:** The AI narrative layer observes but never controls. Events
flow from simulation to observer, never the reverse. This follows ADR003:
"AI failures don't break game mechanics."

Why Typed Events?
-----------------

The simulation originally used string-based event logs::

   event_log = ["Tick 5: SURPLUS_EXTRACTION"]

This created several problems:

1. **Parsing burden**: AI had to extract structure from strings
2. **No type safety**: Typos and format changes caused silent failures
3. **Limited data**: Only event type, no payload details
4. **No filtering**: Couldn't query events by type or attribute

The typed event system solves these::

   events = [
       ExtractionEvent(
           tick=5,
           source_id="C001",
           target_id="C002",
           amount=0.15,
           mechanism="imperial_rent",
       )
   ]

Event Categories
----------------

Events are organized into semantic categories matching the simulation
systems that emit them:

Economic Events
~~~~~~~~~~~~~~~

Emitted by :class:`ImperialRentSystem`:

- **ExtractionEvent**: Imperial rent extracted from worker
- **SubsidyEvent**: Subsidy paid to comprador state
- **CrisisEvent**: Economic crisis detected, bourgeoisie responds

These events track value flow through the imperial circuit, enabling
narrative about exploitation and economic dynamics.

Consciousness Events
~~~~~~~~~~~~~~~~~~~~

Emitted by :class:`SolidaritySystem` and :class:`ConsciousnessSystem`:

- **TransmissionEvent**: Consciousness propagates via solidarity edge
- **MassAwakeningEvent**: Node crosses consciousness threshold

These events track the spread of revolutionary consciousness through
the solidarity network.

Struggle Events
~~~~~~~~~~~~~~~

Emitted by :class:`StruggleSystem`:

- **SparkEvent**: State violence triggers potential uprising
- **UprisingEvent**: Conditions trigger revolt
- **SolidaritySpikeEvent**: Uprising builds solidarity infrastructure

These implement the George Floyd Dynamic: state violence can spark
uprisings that build organizational capacity.

Contradiction Events
~~~~~~~~~~~~~~~~~~~~

Emitted by :class:`ContradictionSystem`:

- **RuptureEvent**: Tension on edge reaches maximum

Rupture events mark the qualitative breaking point where accumulated
contradictions explode.

Topology Events
~~~~~~~~~~~~~~~

Emitted by :class:`TopologyMonitor`:

- **PhaseTransitionEvent**: Percolation ratio crosses threshold

Phase transitions mark the crystallization of atomized leftism into
organized revolutionary force (or the reverse - fragmentation).

The Conversion Pipeline
-----------------------

Events undergo conversion from internal format to typed models:

.. code-block:: text

   1. System.step()
      |
      v
   2. event_bus.publish(EventType.SURPLUS_EXTRACTION, tick, payload)
      |
      v
   3. EventBus stores Event(type, tick, timestamp, payload)
      |
      v
   4. step() calls _convert_bus_event_to_pydantic(event)
      |
      v
   5. Returns ExtractionEvent(tick=..., source_id=..., ...)
      |
      v
   6. WorldState.events.append(extraction_event)

**The Conversion Function:**

The ``_convert_bus_event_to_pydantic()`` function in
:py:mod:`babylon.engine.simulation_engine` handles all 11 EventTypes:

.. code-block:: python

   def _convert_bus_event_to_pydantic(event: Event) -> SimulationEvent | None:
       if event.type == EventType.SURPLUS_EXTRACTION:
           return ExtractionEvent(
               tick=event.tick,
               source_id=event.payload["source_id"],
               target_id=event.payload["target_id"],
               amount=event.payload["amount"],
               mechanism=event.payload.get("mechanism", "imperial_rent"),
           )
       # ... handlers for all 11 types

Observer Event Injection
------------------------

Observers like :class:`TopologyMonitor` run *after* the WorldState is frozen
for the current tick. They cannot add events to the current tick's state.

**Solution:** Observer events are injected into the *next* tick:

.. code-block:: text

   Tick N:
   1. step() produces new WorldState (frozen)
   2. Simulation.step() notifies observers
   3. TopologyMonitor.on_tick() detects phase transition
   4. TopologyMonitor stores event in _pending_events
   5. Simulation._collect_observer_events() reads pending events
   6. Events stored in persistent_context['_observer_events']

   Tick N+1:
   7. step() reads persistent_context['_observer_events']
   8. Observer events appended to WorldState.events
   9. persistent_context['_observer_events'] cleared

This design ensures:

- Observer events are captured (not lost)
- WorldState immutability is preserved
- Events appear in the tick where they were detected

Event Immutability
------------------

All event models use ``frozen=True`` configuration::

   class SimulationEvent(BaseModel):
       model_config = ConfigDict(frozen=True, extra="forbid")

This ensures:

- Events cannot be modified after creation
- No accidental mutation during processing
- Safe for concurrent access
- Hashable for use in sets/dicts

Graceful Degradation
--------------------

The conversion function implements graceful degradation:

.. code-block:: python

   def _convert_bus_event_to_pydantic(event: Event) -> SimulationEvent | None:
       # Unknown event types return None
       if event.type not in KNOWN_TYPES:
           return None

       # Missing payload fields use defaults
       return ExtractionEvent(
           source_id=event.payload.get("source_id", ""),
           # ...
       )

This ensures that:

- New event types don't crash old code
- Missing data produces valid (if incomplete) events
- The simulation never fails due to event processing

Narrative Integration
---------------------

The AI narrative layer reads typed events to generate prose::

   for event in world_state.events:
       if isinstance(event, ExtractionEvent):
           narrative += f"Imperial rent of {event.amount:.2f} "
           narrative += f"extracted from {event.source_id}.\n"

       elif isinstance(event, PhaseTransitionEvent):
           if event.new_state == "liquid":
               narrative += "The movement has crystallized. "
               narrative += "A vanguard party has emerged.\n"

The typed structure enables:

- Pattern matching on event types
- Access to structured payload data
- Consistent narrative generation
- Event-driven storytelling

Testing Events
--------------

The test infrastructure provides tools for event testing:

**DomainFactory:**

.. code-block:: python

   factory = DomainFactory()
   event = factory.create_extraction_event(tick=1, amount=0.1)

**BabylonAssert:**

.. code-block:: python

   Assert(world_state).has_event(ExtractionEvent)
   Assert(world_state).has_event(ExtractionEvent, amount_gt=0.0)
   Assert(world_state).has_events_count(3)

**Direct Testing:**

.. code-block:: python

   from babylon.engine.simulation_engine import step

   new_state = step(state, config)

   extraction_events = [
       e for e in new_state.events
       if isinstance(e, ExtractionEvent)
   ]
   assert len(extraction_events) > 0

Design Decisions
----------------

**Why Pydantic?**
   Pydantic provides validation, serialization, and immutability out of the
   box. Events can be serialized to JSON for persistence or transmission.

**Why a class hierarchy?**
   Shared base classes reduce code duplication and enable polymorphic
   handling. ``isinstance(event, EconomicEvent)`` catches all economic events.

**Why frozen models?**
   Immutability ensures events are reliable historical records. Once emitted,
   an event cannot be modified - it represents what happened at that tick.

**Why separate EventBus and typed events?**
   The EventBus uses simple dataclasses for internal pub/sub (minimal
   overhead). Conversion to Pydantic models happens once at tick boundary.

See Also
--------

- :doc:`/reference/events` - Complete event type reference
- :doc:`/reference/topology` - TopologyMonitor and phase transitions
- :doc:`architecture` - Overall simulation architecture
- :doc:`simulation-systems` - Systems that emit events
