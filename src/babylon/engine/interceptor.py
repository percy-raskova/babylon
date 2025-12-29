"""Event Interceptor pattern for Epoch 2 adversarial mechanics.

Chain of Responsibility for event processing. Interceptors can:
- **Allow**: Pass event unchanged
- **Block**: Stop event with narrative reason
- **Modify**: Transform event before emission

Enables State, Fascist factions, and adversarial actors to interfere
with player actions before they take effect.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from babylon.engine.event_bus import Event


class WorldContext(Protocol):
    """Read-only world state for interceptor decisions."""

    @property
    def tick(self) -> int:
        """Current simulation tick."""
        ...


@dataclass
class SimpleWorldContext:
    """Basic WorldContext for testing."""

    tick: int = 0
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InterceptResult:
    """Immutable result of interceptor processing.

    Attributes:
        event: Event to continue with, or None if blocked.
        reason: Narrative explanation (required if blocked).
    """

    event: Event | None
    reason: str = ""

    def __post_init__(self) -> None:
        """Validate blocked events have a reason."""
        if self.event is None and not self.reason:
            raise ValueError("Blocked events must have a reason")

    @classmethod
    def allow(cls, event: Event) -> InterceptResult:
        """Allow event unchanged."""
        return cls(event=event, reason="")

    @classmethod
    def block(cls, reason: str) -> InterceptResult:
        """Block event with narrative reason."""
        if not reason:
            raise ValueError("Block reason cannot be empty")
        return cls(event=None, reason=reason)

    @classmethod
    def modify(cls, new_event: Event, reason: str = "") -> InterceptResult:
        """Modify event, optionally with reason."""
        return cls(event=new_event, reason=reason)

    @property
    def is_blocked(self) -> bool:
        """True if event was blocked."""
        return self.event is None

    @property
    def is_modified(self) -> bool:
        """True if event was modified with reason."""
        return self.event is not None and bool(self.reason)


@dataclass(frozen=True)
class BlockedEvent:
    """Audit record for blocked events."""

    event: Event
    interceptor_name: str
    reason: str
    blocked_at: datetime = field(default_factory=datetime.now)


class EventInterceptor(ABC):
    """Abstract base for event interceptors.

    Priority ranges (higher runs first):
    - 90-100: Security/State (block first)
    - 50-89: Faction/adversarial
    - 10-49: Resource/validation
    - 1-9: Logging/audit (run last)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Interceptor name for logs and audit."""
        ...

    @property
    def priority(self) -> int:
        """Chain priority (higher = earlier). Default 100."""
        return 100

    @abstractmethod
    def intercept(self, event: Event, context: WorldContext | None) -> InterceptResult:
        """Process event. Return allow/block/modify result."""
        ...
