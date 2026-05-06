"""Volume I production computation at hex level.

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26

Computes per-hex surplus value (s), exploitation rate (s/v), and profit
rate (s/(c+v)) from department composition and capital stocks. Production
is a rate computation that does not create or destroy value — total
capital (c+v+s) is conserved.

See Also:
    :mod:`babylon.economics.substrate.types`: HexEconomicState and HexGrid.
    :mod:`babylon.economics.substrate.conservation`: Conservation checking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from babylon.economics.substrate.types import HexEconomicState, HexGrid


class DefaultHexProductionComputer:
    """Compute Volume I production rates at hex level.

    For each hex with employment > 0, computes:
        - profit_rate = s / (c + v) if (c + v) > 0
        - exploitation_rate = s / v if v > 0

    Conservation guarantee: sum(c+v+s) unchanged because production
    only computes derived rates, not new values.
    """

    # Spec 053 INV-001: substrate computer; conservation-preserving by
    # construction. Opt-out marker (default-deny per FR-004a).
    creates_value: ClassVar[bool] = False

    def compute_production(self, grid: HexGrid) -> HexGrid:
        """Compute per-hex surplus value and exploitation rate.

        Args:
            grid: HexGrid with hydrated capital stocks.

        Returns:
            New HexGrid with updated profit_rate and exploitation_rate.
        """
        from babylon.economics.substrate.types import HexGrid as HexGridType

        updated_hexes: dict[str, HexEconomicState] = {}

        for h3_id, hex_state in grid.hexes.items():
            c = hex_state.constant_capital
            v = hex_state.variable_capital
            s = hex_state.surplus_value

            # Compute rates
            total_cv = c + v
            profit_rate = s / total_cv if total_cv > 0 else 0.0
            exploitation_rate = s / v if v > 0 else 0.0

            updated_hexes[h3_id] = hex_state.model_copy(
                update={
                    "profit_rate": profit_rate,
                    "exploitation_rate": exploitation_rate,
                }
            )

        return HexGridType(
            hexes=updated_hexes,
            county_hex_ids=grid.county_hex_ids,
            res6_parents=grid.res6_parents,
            res5_parents=grid.res5_parents,
            res6_children=grid.res6_children,
            res5_children=grid.res5_children,
        )


__all__ = [
    "DefaultHexProductionComputer",
]
