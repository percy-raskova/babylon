Event Interceptor Reference
===========================

The Event Interceptor pattern implements Chain of Responsibility for event
processing in Epoch 2 adversarial mechanics. Interceptors enable the State,
Fascist factions, and other adversarial actors to block or modify player
actions before they take effect.

.. contents:: On this page
   :local:
   :depth: 2

Overview
--------

Interceptors sit between player actions and the event bus, providing a
hook for adversarial mechanics without requiring UI changes. This is the
Epoch 1→2 bridge pattern.

**Key Components:**

- :py:mod:`babylon.engine.interceptor` - Interceptor base classes
- :py:class:`~babylon.engine.interceptor.EventInterceptor` - Abstract base
- :py:class:`~babylon.engine.interceptor.InterceptResult` - Allow/block/modify result
- :py:class:`~babylon.engine.interceptor.WorldContext` - Read-only state protocol

InterceptResult Actions
-----------------------

Interceptors return one of three outcomes:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Action
     - Method
     - Description
   * - **Allow**
     - ``InterceptResult.allow(event)``
     - Pass event unchanged to next interceptor
   * - **Block**
     - ``InterceptResult.block(reason)``
     - Stop event with narrative reason
   * - **Modify**
     - ``InterceptResult.modify(new_event, reason)``
     - Transform event before emission

**Example:**

.. code-block:: python

   from babylon.engine.interceptor import InterceptResult

   # Allow an event to pass through unchanged
   result = InterceptResult.allow(event)

   # Block an event with narrative reason
   result = InterceptResult.block("State security forces detained the organizers")

   # Modify an event (e.g., reduce effectiveness)
   modified = Event(
       type=event.type,
       tick=event.tick,
       payload={**event.payload, "effectiveness": 0.5}
   )
   result = InterceptResult.modify(modified, "Reduced due to surveillance")

Priority System
---------------

Interceptors run in priority order (higher = earlier). This ensures security
checks run before faction interference, which runs before validation.

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Priority Range
     - Purpose
   * - **90-100**
     - Security/State interceptors (block first)
   * - **50-89**
     - Faction/adversarial interceptors
   * - **10-49**
     - Resource/validation interceptors
   * - **1-9**
     - Logging/audit interceptors (run last)

WorldContext Protocol
---------------------

The :class:`WorldContext` protocol provides read-only access to world state
for interceptor decisions. Implementations should expose only the minimum
information needed for blocking/modification decisions.

**Minimal Interface:**

.. code-block:: python

   class WorldContext(Protocol):
       @property
       def tick(self) -> int:
           """Current simulation tick."""
           ...

**Extended Contexts** may include:

- Territory surveillance levels
- Faction alignments
- Repression capacity
- Resource availability

Creating Custom Interceptors
----------------------------

To create a custom interceptor, subclass :class:`EventInterceptor`:

.. code-block:: python

   from babylon.engine.interceptor import EventInterceptor, InterceptResult
   from babylon.engine.event_bus import Event

   class SecurityInterceptor(EventInterceptor):
       """State security that blocks AGITATE events in surveilled areas."""

       @property
       def name(self) -> str:
           return "state_security"

       @property
       def priority(self) -> int:
           return 100  # High priority, runs first

       def intercept(
           self, event: Event, context: WorldContext | None
       ) -> InterceptResult:
           if event.type == "AGITATE" and self._is_surveilled(context):
               return InterceptResult.block(
                   "State security forces detained the organizers"
               )
           return InterceptResult.allow(event)

       def _is_surveilled(self, context: WorldContext | None) -> bool:
           # Check territory heat, surveillance level, etc.
           return False

Blocked Event Auditing
----------------------

When events are blocked, a :class:`BlockedEvent` record is created for
audit purposes:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field
     - Type
     - Description
   * - ``event``
     - ``Event``
     - The blocked event
   * - ``interceptor_name``
     - ``str``
     - Name of blocking interceptor
   * - ``reason``
     - ``str``
     - Narrative reason for blocking
   * - ``blocked_at``
     - ``datetime``
     - Timestamp of block

This enables the AI narrative layer to explain why player actions failed
with in-universe reasons rather than mechanical explanations.

See Also
--------

- :doc:`/concepts/event-system` - Event system architecture
- :doc:`/reference/events` - Event types and lifecycle
- :py:mod:`babylon.engine.interceptor` - Source code
