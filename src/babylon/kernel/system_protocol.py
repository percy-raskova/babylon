"""Protocol definition for simulation systems."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, Union, runtime_checkable

if TYPE_CHECKING:
    from babylon.engine.context import TickContext
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol

# Type alias for context parameter - accepts both legacy dict and typed TickContext
ContextType = Union[dict[str, Any], "TickContext"]


@runtime_checkable
class System(Protocol):
    """Protocol defining a historical materialist system."""

    @property
    def name(self) -> str:
        """The identifier of the system."""
        ...

    def step(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
    ) -> None:
        """Apply system logic to the world graph.

        Args:
            graph: Mutable NetworkX graph representing WorldState.
            services: ServicesProtocol with config, formulas, event_bus, database.
            context: TickContext or dict with 'tick' (int) and optional metadata.
                TickContext is the preferred type; dict is supported for backward
                compatibility with existing tests.
        """
        ...
