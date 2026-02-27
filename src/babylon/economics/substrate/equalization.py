"""Volume III capital equalization at hex level.

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26

Migrates capital between hexes based on profit rate gradient. Capital
flows from below-average to above-average profit rate hexes, modeling
the tendency of the rate of profit to equalize.

Formula: ``delta_c[hex] = alpha * (r[hex] - r_avg) * c[hex]``

Conservation proof:
    ``sum(delta_c) = alpha * sum((r[i] - r_avg) * c[i])``
    ``= alpha * (sum(r[i]*c[i]) - r_avg * sum(c[i]))``
    ``= alpha * (r_avg * C_total - r_avg * C_total) = 0``

See Also:
    :mod:`babylon.economics.substrate.types`: HexEconomicState and HexGrid.
    :mod:`babylon.economics.substrate.conservation`: Conservation checking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from babylon.economics.substrate.types import HexEconomicState, HexGrid


class DefaultHexEqualizationComputer:
    """Compute Volume III capital equalization via profit rate gradient.

    Capital migrates from low-profit to high-profit hexes. The average
    profit rate is capital-weighted (not arithmetic mean) to ensure
    conservation by construction.
    """

    def equalize_capital(self, grid: HexGrid, alpha: float = 0.01) -> HexGrid:
        """Migrate capital between hexes based on profit rate gradient.

        Args:
            grid: HexGrid with current profit rates and capital stocks.
            alpha: Migration speed coefficient (default 0.01).

        Returns:
            New HexGrid with updated constant capital stocks.
        """
        from babylon.economics.substrate.types import HexGrid as HexGridType

        hex_ids = list(grid.hexes.keys())
        if not hex_ids:
            return grid

        # Compute capital-weighted average profit rate
        total_s = 0.0
        total_cv = 0.0
        for hex_state in grid.hexes.values():
            total_s += hex_state.surplus_value
            total_cv += hex_state.constant_capital + hex_state.variable_capital

        r_avg = total_s / total_cv if total_cv > 0 else 0.0

        # Compute delta_c for each hex
        deltas: dict[str, float] = {}
        for h3_id, hex_state in grid.hexes.items():
            r_i = hex_state.profit_rate
            c_i = hex_state.constant_capital
            deltas[h3_id] = alpha * (r_i - r_avg) * c_i

        # Apply deltas with floor at zero
        updated_hexes: dict[str, HexEconomicState] = {}
        for h3_id, hex_state in grid.hexes.items():
            new_c = max(0.0, hex_state.constant_capital + deltas[h3_id])

            # Recompute profit rate with new c
            total_cv_new = new_c + hex_state.variable_capital
            new_profit_rate = hex_state.surplus_value / total_cv_new if total_cv_new > 0 else 0.0

            updated_hexes[h3_id] = hex_state.model_copy(
                update={
                    "constant_capital": new_c,
                    "profit_rate": new_profit_rate,
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
    "DefaultHexEqualizationComputer",
]
