"""Event Interceptor pattern for Epoch 2 adversarial mechanics.

This module provides the Chain of Responsibility pattern for event processing,
enabling the State, Fascist factions, and other adversarial actors to block
or modify player actions before they take effect.

Epoch 1→2 Bridge: Enables adversarial mechanics without UI changes.

Example:
    >>> class SecurityInterceptor(EventInterceptor):
    ...     @property
    ...     def name(self) -> str:
    ...         return "state_security"
    ...
    ...     @property
    ...     def priority(self) -> int:
    ...         return 100  # High priority, runs first
    ...
    ...     def intercept(
    ...         self, event: Event, context: WorldContext | None
    ...     ) -> InterceptResult:
    ...         if event.type == "AGITATE" and self._is_surveilled(context):
    ...             return InterceptResult.block(
    ...                 "State security forces detained the organizers"
    ...             )
    ...         return InterceptResult.allow(event)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from babylon.engine.event_bus import Event


class WorldContext(Protocol):
    """Protocol for read-only world state passed to interceptors.

    This provides interceptors with the information they need to make
    blocking/modification decisions. Implementations should provide
    read-only access to relevant world state.

    The minimal interface requires only the current tick. Specific
    interceptor implementations may require richer context with
    territory data, surveillance levels, faction alignments, etc.
    """

    @property
    def tick(self) -> int:
        """Current simulation tick."""
        ...


@dataclass
class SimpleWorldContext:
    """Simple implementation of WorldContext for testing and basic use.

    Attributes:
        tick: Current simulation tick.
        data: Additional context data as key-value pairs.
    """

    tick: int = 0
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InterceptResult:
    """Result of interceptor processing with narrative reason.

    This immutable container holds the outcome of an interceptor's
    decision: whether to allow, block, or modify an event.

    The `reason` field is critical for the Narrative System - it provides
    the player-facing explanation for why their action was blocked or
    modified (e.g., "State security forces detained the organizers").

    Attributes:
        event: The event to continue with, or None if blocked.
        reason: Narrative explanation (required if blocked, optional if modified).

    Example:
        >>> # Allow an event to pass through unchanged
        >>> result = InterceptResult.allow(event)
        >>>
        >>> # Block an event with narrative reason
        >>> result = InterceptResult.block("Insufficient cadre labor")
        >>>
        >>> # Modify an event (e.g., reduce effectiveness)
        >>> modified = Event(type=event.type, tick=event.tick,
        ...                  payload={**event.payload, "effectiveness": 0.5})
        >>> result = InterceptResult.modify(modified, "Hostile territory reduced impact")
    """

    event: Event | None
    reason: str = ""

    def __post_init__(self) -> None:
        """Validate that blocked events have a reason."""
        if self.event is None and not self.reason:
            raise ValueError("Blocked events must have a reason")

    @classmethod
    def allow(cls, event: Event) -> InterceptResult:
        """Create a result that allows the event to pass through unchanged.

        Args:
            event: The original event to allow.

        Returns:
            InterceptResult with the event and empty reason.
        """
        return cls(event=event, reason="")

    @classmethod
    def block(cls, reason: str) -> InterceptResult:
        """Create a result that blocks the event.

        Args:
            reason: Narrative explanation for why the event was blocked.
                   This is displayed to the player in Epoch 2.

        Returns:
            InterceptResult with None event and the blocking reason.

        Raises:
            ValueError: If reason is empty.
        """
        if not reason:
            raise ValueError("Block reason cannot be empty")
        return cls(event=None, reason=reason)

    @classmethod
    def modify(cls, new_event: Event, reason: str = "") -> InterceptResult:
        """Create a result that modifies the event.

        Args:
            new_event: The modified event to continue with.
            reason: Optional narrative explanation for the modification.

        Returns:
            InterceptResult with the modified event and reason.
        """
        return cls(event=new_event, reason=reason)

    @property
    def is_blocked(self) -> bool:
        """Check if this result represents a blocked event."""
        return self.event is None

    @property
    def is_modified(self) -> bool:
        """Check if this result includes a modification reason."""
        return self.event is not None and bool(self.reason)


@dataclass(frozen=True)
class BlockedEvent:
    """Audit record for an event blocked by an interceptor.

    This immutable record captures the full context of a blocked event
    for debugging, testing, and narrative generation.

    Attributes:
        event: The original event that was blocked.
        interceptor_name: Name of the interceptor that blocked it.
        reason: Narrative reason for blocking.
        blocked_at: Wall-clock time when blocking occurred.
    """

    event: Event
    interceptor_name: str
    reason: str
    blocked_at: datetime = field(default_factory=datetime.now)


class EventInterceptor(ABC):
    """Abstract base class for event interceptors.

    Interceptors form a Chain of Responsibility that processes events
    before they are emitted to subscribers. Each interceptor can:

    - **Allow**: Pass the event unchanged (return InterceptResult.allow(event))
    - **Block**: Stop the event (return InterceptResult.block(reason))
    - **Modify**: Transform the event (return InterceptResult.modify(new_event, reason))

    Interceptors are sorted by priority (higher runs first) and executed
    in sequence. If any interceptor blocks, the chain stops immediately.

    This pattern enables Epoch 2 adversarial mechanics:

    - State can block player actions in surveilled territories
    - Fascist factions can disrupt organizing efforts
    - Resource constraints can prevent actions
    - Fog of War can mask intelligence gathering

    Example:
        >>> class ResourceInterceptor(EventInterceptor):
        ...     @property
        ...     def name(self) -> str:
        ...         return "resource_check"
        ...
        ...     @property
        ...     def priority(self) -> int:
        ...         return 50  # Medium priority
        ...
        ...     def intercept(
        ...         self, event: Event, context: WorldContext | None
        ...     ) -> InterceptResult:
        ...         if event.type == "RECRUIT" and not self._has_cadre(context):
        ...             return InterceptResult.block("Insufficient cadre labor")
        ...         return InterceptResult.allow(event)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Interceptor name for debugging and audit logs.

        This name appears in BlockedEvent records and log messages,
        helping developers trace which interceptor blocked or modified
        an event.

        Returns:
            A short, descriptive name (e.g., "state_security", "fog_of_war").
        """
        ...

    @property
    def priority(self) -> int:
        """Priority for chain ordering (higher runs first).

        Default priority is 100. Override to run earlier (higher) or
        later (lower) in the interceptor chain.

        Recommended priority ranges:
        - 90-100: Security/State interceptors (block first)
        - 50-89: Faction/adversarial interceptors
        - 10-49: Resource/validation interceptors
        - 1-9: Logging/audit interceptors (run last)

        Returns:
            Integer priority (higher = runs earlier).
        """
        return 100

    @abstractmethod
    def intercept(self, event: Event, context: WorldContext | None) -> InterceptResult:
        """Process an event through this interceptor.

        Examine the event and context to decide whether to allow, block,
        or modify the event. The decision should be based on game state
        accessible through the context.

        Args:
            event: The event to process.
            context: Optional world state context for decision making.
                    May be None for backwards compatibility with Epoch 1.

        Returns:
            InterceptResult indicating the decision:
            - InterceptResult.allow(event) to pass through
            - InterceptResult.block(reason) to stop the chain
            - InterceptResult.modify(new_event, reason) to transform
        """
        ...
