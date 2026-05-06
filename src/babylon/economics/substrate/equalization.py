"""Volume III capital equalization at hex level.

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26 (amended 2026-04-09 for Feature 043 ground rent)

Migrates capital between hexes based on profit rate gradient. Capital
flows from below-average to above-average profit rate hexes, modeling
the tendency of the rate of profit to equalize.

When ``rent_defines`` is provided, ground rent is extracted from hexes
that carry a ``HexTenureComposition`` before capital migration (FR-010).

Formula: ``delta_c[hex] = alpha * (r[hex] - r_avg) * c[hex]``

Conservation proof:
    ``sum(delta_c) = alpha * sum((r[i] - r_avg) * c[i])``
    ``= alpha * (sum(r[i]*c[i]) - r_avg * sum(c[i]))``
    ``= alpha * (r_avg * C_total - r_avg * C_total) = 0``

See Also:
    :mod:`babylon.economics.substrate.types`: HexEconomicState and HexGrid.
    :mod:`babylon.economics.substrate.conservation`: Conservation checking.
    :mod:`babylon.economics.substrate.ground_rent`: Ground rent extraction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from babylon.config.defines import RentCircuitDefines
    from babylon.economics.substrate.types import HexEconomicState, HexGrid


class DefaultHexEqualizationComputer:
    """Compute Volume III capital equalization via profit rate gradient.

    Capital migrates from low-profit to high-profit hexes. The average
    profit rate is capital-weighted (not arithmetic mean) to ensure
    conservation by construction.

    When ``rent_defines`` is supplied, ground rent is extracted from
    hexes with ``tenure_composition`` before the capital migration step.
    """

    # Spec 053 INV-001: substrate computer; conservation-preserving by
    # construction. Opt-out marker (default-deny per FR-004a).
    creates_value: ClassVar[bool] = False

    def equalize_capital(
        self,
        grid: HexGrid,
        alpha: float = 0.01,
        rent_defines: RentCircuitDefines | None = None,
    ) -> HexGrid:
        """Migrate capital between hexes based on profit rate gradient.

        When ``rent_defines`` is provided and hexes carry a
        ``tenure_composition``, ground rent is extracted from ``v`` and
        ``s`` before capital migration (FR-010, Feature 043).

        Args:
            grid: HexGrid with current profit rates and capital stocks.
            alpha: Migration speed coefficient (default 0.01).
            rent_defines: Optional RentCircuitDefines for ground rent
                extraction.  None disables rent (backward compatible).

        Returns:
            New HexGrid with updated capital stocks.
        """
        from babylon.economics.substrate.ground_rent import compute_ground_rent
        from babylon.economics.substrate.types import HexGrid as HexGridType

        hex_ids = list(grid.hexes.keys())
        if not hex_ids:
            return grid

        # ==============================================================
        # Phase 1: Ground rent extraction (Feature 043, FR-010)
        # ==============================================================
        # Apply ground rent before migration so that the profit rate
        # gradient already reflects the rent burden.
        working_hexes: dict[str, HexEconomicState] = {}

        # Compute capital-weighted average profit rate for rent calc
        total_s = 0.0
        total_cv = 0.0
        for hex_state in grid.hexes.values():
            total_s += hex_state.surplus_value
            total_cv += hex_state.constant_capital + hex_state.variable_capital

        r_avg = total_s / total_cv if total_cv > 0 else 0.0

        if rent_defines is not None:
            for h3_id, hex_state in grid.hexes.items():
                rent = compute_ground_rent(hex_state, r_avg=r_avg, defines=rent_defines)
                if rent.total_rent > 0.0:
                    # Deduct rent from v and s
                    new_v = max(0.0, hex_state.variable_capital - rent.rent_from_v)
                    new_s = max(0.0, hex_state.surplus_value - rent.rent_from_s)

                    # Recompute rates with post-rent values
                    new_cv = hex_state.constant_capital + new_v
                    new_pr = new_s / new_cv if new_cv > 0 else 0.0
                    new_er = new_s / new_v if new_v > 0 else 0.0

                    working_hexes[h3_id] = hex_state.model_copy(
                        update={
                            "variable_capital": new_v,
                            "surplus_value": new_s,
                            "profit_rate": new_pr,
                            "exploitation_rate": new_er,
                        }
                    )
                else:
                    working_hexes[h3_id] = hex_state
        else:
            working_hexes = dict(grid.hexes)

        # ==============================================================
        # Phase 2: Capital migration (original equalization logic)
        # ==============================================================
        # Re-compute capital-weighted average profit rate post-rent
        total_s_post = 0.0
        total_cv_post = 0.0
        for hex_state in working_hexes.values():
            total_s_post += hex_state.surplus_value
            total_cv_post += hex_state.constant_capital + hex_state.variable_capital

        r_avg_post = total_s_post / total_cv_post if total_cv_post > 0 else 0.0

        # Compute delta_c for each hex
        deltas: dict[str, float] = {}
        for h3_id, hex_state in working_hexes.items():
            r_i = hex_state.profit_rate
            c_i = hex_state.constant_capital
            deltas[h3_id] = alpha * (r_i - r_avg_post) * c_i

        # Apply deltas with floor at zero
        updated_hexes: dict[str, HexEconomicState] = {}
        for h3_id, hex_state in working_hexes.items():
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
