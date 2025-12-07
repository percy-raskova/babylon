"""Protocol definition for simulation systems."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import networkx as nx

from babylon.models.config import SimulationConfig


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
        config: SimulationConfig,
        context: dict[str, Any],
    ) -> None:
        """
        Apply system logic to the world graph.

        Args:
            graph: Mutable NetworkX graph representing WorldState
            config: Read-only simulation configuration
            context: Shared dictionary for 'events' (list[str]) and 'tick' (int)
        """
        ...
