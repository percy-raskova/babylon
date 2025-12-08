"""Protocol definition for simulation systems."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import networkx as nx

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer


@runtime_checkable
class System(Protocol):
    """Protocol defining a historical materialist system."""

    @property
    def name(self) -> str:
        """The identifier of the system."""
        ...

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: dict[str, Any],
    ) -> None:
        """
        Apply system logic to the world graph.

        Args:
            graph: Mutable NetworkX graph representing WorldState
            services: ServiceContainer with config, formulas, event_bus, database
            context: Shared dictionary for 'tick' (int)
        """
        ...
