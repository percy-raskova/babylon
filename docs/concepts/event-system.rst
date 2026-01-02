Event System Architecture
=========================

The Babylon simulation emits typed events to enable the AI narrative layer
to observe state changes without coupling to the simulation internals. This
document explains the conceptual architecture of the event system.

For technical reference, see :doc:`/reference/events`.

The Observer Pattern
--------------------

The event system implements the Observer pattern at the architecture level:

.. mermaid::

   flowchart LR
       subgraph engine["Simulation Engine"]
           SYS["Systems<br/>(ImperialRent,<br/>Struggle, etc.)"]
           BUS["EventBus<br/>(pub/sub)"]
           STEP["step()<br/>function"]
       end

       subgraph state["State Layer"]
           WS["WorldState<br/>.events[]"]
       end

       subgraph observer["Observer Layer"]
           AI["AI Narrative<br/>Layer"]
       end

       SYS -->|"publishes"| BUS
       BUS -->|"collects"| STEP
       STEP -->|"conversion"| WS
       WS -->|"reads"| AI

   %% Necropolis Codex styling
   classDef engine fill:#4A1818,stroke:#6B4A3A,color:#D4C9B8
   classDef state fill:#6B4A3A,stroke:#8B7B6B,color:#D4C9B8
   classDef observer fill:#1A3A1A,stroke:#2A6B2A,color:#39FF14

   class SYS,BUS,STEP engine
   class WS state
   class AI observer

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

.. mermaid::

   flowchart TB
       A["1. System.step()"] --> B["2. event_bus.publish()<br/>EventType.SURPLUS_EXTRACTION"]
       B --> C["3. EventBus stores<br/>Event(type, tick, timestamp, payload)"]
       C --> D["4. step() calls<br/>_convert_bus_event_to_pydantic()"]
       D --> E["5. Returns<br/>ExtractionEvent(tick=..., source_id=...)"]
       E --> F["6. WorldState.events.append()<br/>extraction_event"]

   %% Necropolis Codex styling
   classDef system fill:#4A1818,stroke:#6B4A3A,color:#D4C9B8
   classDef bus fill:#6B4A3A,stroke:#8B7B6B,color:#D4C9B8
   classDef state fill:#1A3A1A,stroke:#2A6B2A,color:#39FF14

   class A system
   class B,C,D bus
   class E,F state

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

.. mermaid::

   flowchart TB
       subgraph tickN["Tick N"]
           N1["1. step() produces<br/>new WorldState (frozen)"]
           N2["2. Simulation.step()<br/>notifies observers"]
           N3["3. TopologyMonitor.on_tick()<br/>detects phase transition"]
           N4["4. TopologyMonitor stores<br/>event in _pending_events"]
           N5["5. _collect_observer_events()<br/>reads pending events"]
           N6["6. Events stored in<br/>persistent_context"]
       end

       subgraph tickN1["Tick N+1"]
           N7["7. step() reads<br/>persistent_context"]
           N8["8. Observer events<br/>appended to WorldState.events"]
           N9["9. persistent_context<br/>cleared"]
       end

       N1 --> N2 --> N3 --> N4 --> N5 --> N6
       N6 -.->|"next tick"| N7
       N7 --> N8 --> N9

   %% Necropolis Codex styling
   classDef tickN fill:#4A1818,stroke:#6B4A3A,color:#D4C9B8
   classDef tickN1 fill:#1A3A1A,stroke:#2A6B2A,color:#39FF14

   class N1,N2,N3,N4,N5,N6 tickN
   class N7,N8,N9 tickN1

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
