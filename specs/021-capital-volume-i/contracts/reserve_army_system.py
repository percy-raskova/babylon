"""Contract: ReserveArmySystem (System #17).

Computes reserve army composition and applies wage pressure.
Position: After TickDynamicsSystem (#4), before SolidaritySystem (#5).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import networkx as nx

from babylon.engine.services import ServiceContainer


# ---------------------------------------------------------------------------
# Data source protocol (DI)
# ---------------------------------------------------------------------------
@runtime_checkable
class ReserveArmyDataSource(Protocol):
    """Provides county-level unemployment decomposition data."""

    def get_unemployment_decomposition(
        self,
        fips: str,
        year: int,
    ) -> dict[str, int] | None:
        """Return unemployment decomposition for a county-year.

        Returns dict with keys: labor_force, unemployed_u3, unemployed_u6,
        part_time_economic, discouraged, marginally_attached.
        Returns None if no data available.
        """
        ...


# ---------------------------------------------------------------------------
# Calculator protocol (DI)
# ---------------------------------------------------------------------------
@runtime_checkable
class WagePressureCalculator(Protocol):
    """Computes wage pressure from reserve army composition."""

    def compute_wage_pressure(
        self,
        reserve_ratio: float,
    ) -> float:
        """Return wage pressure coefficient in [0, 1].

        Higher reserve_ratio -> higher wage pressure (more suppression of v).
        Must saturate at high reserve ratios (bounded, no divergence).
        """
        ...


# ---------------------------------------------------------------------------
# System contract
# ---------------------------------------------------------------------------
class ReserveArmySystem:
    """System #17: Reserve Army of Labor.

    Reads unemployment decomposition from loaded data.
    Computes reserve army composition (floating, latent, stagnant, pauperized).
    Applies wage pressure to territory median_wage via bounded sigmoid.
    Publishes RESERVE_ARMY_PRESSURE events.

    Graph mutations:
        - Reads: territory nodes "median_wage", "fips_code"
        - Writes: territory nodes "median_wage" (reduced by pressure),
                  "reserve_ratio", "reserve_army_floating",
                  "reserve_army_latent", "reserve_army_stagnant"
    """

    @property
    def name(self) -> str:
        return "ReserveArmySystem"

    def step(
        self,
        graph: nx.DiGraph[str],
        services: ServiceContainer,
        context: dict[str, Any],
    ) -> None:
        """Execute reserve army computation for all territory nodes."""
        ...
