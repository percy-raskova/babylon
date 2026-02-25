"""Contract: DispossessionEventSystem (System #18).

Records aggregate dispossession events and tracks value transfers.
Position: After ImperialRentSystem (#6), before DecompositionSystem (#7).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import networkx as nx

from babylon.engine.services import ServiceContainer


# ---------------------------------------------------------------------------
# Data source protocol (DI)
# ---------------------------------------------------------------------------
@runtime_checkable
class TerritoryDispossessionDataSource(Protocol):
    """Provides county-level dispossession rate data from multiple sources."""

    def get_foreclosure_rate(self, fips: str, year: int) -> float | None:
        """Return annual foreclosure filing rate for county-year."""
        ...

    def get_eviction_rate(self, fips: str, year: int) -> float | None:
        """Return annual eviction filing rate for county-year."""
        ...

    def get_displacement_rate(self, fips: str, year: int) -> float | None:
        """Return net out-migration rate due to housing costs."""
        ...

    def get_institutional_ownership(self, fips: str, year: int) -> float | None:
        """Return fraction of housing owned by institutional investors."""
        ...


# ---------------------------------------------------------------------------
# System contract
# ---------------------------------------------------------------------------
class DispossessionEventSystem:
    """System #18: Primitive Accumulation / Dispossession Events.

    Reads territory dispossession rates from loaded data.
    Generates aggregate DispossessionEvent records per territory per tick.
    Tracks value transfers between territories (balanced accounting).
    Feeds updated rates to existing DispossessionDataSource protocol for
    class transition engine integration (Feature 016).
    Publishes DISPOSSESSION_EVENT and VALUE_TRANSFER events.

    Graph mutations:
        - Reads: territory nodes "wealth", "fips_code", edge data
        - Writes: territory nodes "dispossession_intensity",
                  "value_transferred_out", "value_transferred_in"
    """

    @property
    def name(self) -> str:
        return "DispossessionEventSystem"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: dict[str, Any],
    ) -> None:
        """Execute dispossession event computation for all territory nodes."""
        ...
