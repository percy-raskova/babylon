"""Protocol definition for simulation systems."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from babylon.engine.context import TickContext
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol

# Narrowed to TickContext (systems-dedup refactor): the legacy ``dict`` arm was
# removed once every System step-context (production + fixtures) became a
# TickContext. TickContext stays TYPE_CHECKING-imported so the kernel < models
# layering (Program 14) holds — this is a forward-ref alias, not a runtime import.
type ContextType = "TickContext"


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
            context: TickContext with 'tick' (int) and optional metadata.
        """
        ...
