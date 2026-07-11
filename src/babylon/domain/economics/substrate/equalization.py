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
    :mod:`babylon.domain.economics.substrate.types`: HexEconomicState and HexGrid.
    :mod:`babylon.domain.economics.substrate.conservation`: Conservation checking.
    :mod:`babylon.domain.economics.substrate.ground_rent`: Ground rent extraction.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from babylon.config.defines import RentCircuitDefines
    from babylon.domain.economics.substrate.types import HexEconomicState, HexGrid

# Numerical-stability threshold: a hex contributes to the rate gradient only
# if its (c+v) basis is large enough to compute a well-defined profit rate
# without float overflow. ``s/(c+v)`` with subnormal cv can produce ``inf``,
# which then propagates to NaN via ``inf - inf`` in the gradient, breaking
# conservation. The threshold is well above the subnormal range so the
# c-weighted product won't overflow.
_MIN_RATE_BASIS: float = math.ldexp(1.0, -1000)  # ~9.3e-302


def _compute_capital_weighted_rates(
    hexes: dict[str, HexEconomicState],
) -> tuple[dict[str, float], float]:
    """Compute per-hex profit rate and the c-weighted average rate.

    Returns ``(per_hex_r, r_avg)`` where ``per_hex_r[h] = s/(c+v)`` (computed
    inline; not read from any stored field) and ``r_avg = sum(r_i*c_i) /
    sum(c_i)``. The c-weighted form is required by the conservation proof:

        sum_i delta_c_i = alpha * (sum_i r_i*c_i  -  r_avg * sum_i c_i) = 0
        ⇔   r_avg = sum_i (r_i * c_i) / sum_i c_i

    Hexes whose ``c+v`` is below ``_MIN_RATE_BASIS`` (subnormal range) are
    treated as ``r_i = 0`` to avoid intermediate overflow producing NaN.
    """
    per_hex_r: dict[str, float] = {}
    weighted_r_numer = 0.0
    c_total = 0.0
    for h3_id, hex_state in hexes.items():
        cv = hex_state.constant_capital + hex_state.variable_capital
        if cv > _MIN_RATE_BASIS:
            r_i = hex_state.surplus_value / cv
            if not math.isfinite(r_i):
                r_i = 0.0
        else:
            r_i = 0.0
        per_hex_r[h3_id] = r_i
        weighted_r_numer += r_i * hex_state.constant_capital
        c_total += hex_state.constant_capital
    r_avg = weighted_r_numer / c_total if c_total > 0 else 0.0
    return per_hex_r, r_avg


def _compute_non_negative_scale(
    proposed_deltas: dict[str, float],
    hexes: dict[str, HexEconomicState],
) -> float:
    """Compute the scale factor that keeps every post-step c >= 0.

    Returns the largest ``scale ∈ (0, 1]`` such that
    ``c_i + scale * proposed_deltas[i] >= 0`` for every hex. Linearity of
    scaling preserves ``sum(scale * delta) = scale * sum(delta) = 0``, so
    sum-conservation is maintained. Returns 0.0 if any negative delta
    targets a hex with ``c == 0`` (no flow possible from an empty hex).
    """
    scale = 1.0
    for h3_id, d in proposed_deltas.items():
        if d >= 0.0:
            continue
        c_i = hexes[h3_id].constant_capital
        if c_i == 0.0:
            return 0.0
        cap = c_i / (-d)
        if cap < scale:
            scale = cap
    return scale


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
        alpha: float | None = None,
        rent_defines: RentCircuitDefines | None = None,
    ) -> HexGrid:
        """Migrate capital between hexes based on profit rate gradient.

        When ``rent_defines`` is provided and hexes carry a
        ``tenure_composition``, ground rent is extracted from ``v`` and
        ``s`` before capital migration (FR-010, Feature 043).

        Args:
            grid: HexGrid with current profit rates and capital stocks.
            alpha: Migration speed coefficient. When ``None`` (the default),
                the value is sourced from ``GameDefines.economy.alpha_weekly``
                per spec 062 FR-029. The historical hard-coded ``0.01`` was
                an annual rate; under weekly tick cadence that compounded
                52× into the wrong magnitude. Pass an explicit float to
                override the GameDefines value (e.g., for unit tests that
                exercise specific gradients).
            rent_defines: Optional RentCircuitDefines for ground rent
                extraction.  None disables rent (backward compatible).

        Returns:
            New HexGrid with updated capital stocks.
        """
        if alpha is None:
            from babylon.config.defines import GameDefines

            alpha = GameDefines().economy.alpha_weekly
        from babylon.domain.economics.substrate.ground_rent import compute_ground_rent
        from babylon.domain.economics.substrate.types import HexGrid as HexGridType

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
        # Phase 2: Capital migration (conservation-preserving formulation)
        # ==============================================================
        # See _compute_capital_weighted_rates for the conservation proof
        # (the proof requires r_avg = sum(r_i*c_i)/sum(c_i), the c-weighted
        # mean — not the totals ratio sum(s_i)/sum(c_i+v_i)).
        per_hex_r, r_avg_post = _compute_capital_weighted_rates(working_hexes)

        # Compute proposed delta_c for each hex
        proposed_deltas: dict[str, float] = {
            h3_id: alpha * (per_hex_r[h3_id] - r_avg_post) * hex_state.constant_capital
            for h3_id, hex_state in working_hexes.items()
        }

        # Non-negativity scaling: if any proposed delta would push c_i
        # negative, scale ALL deltas down proportionally. Linearity preserves
        # sum(delta) = 0; non-negativity is guaranteed without the
        # value-destroying ``max(0.0, c_i + delta)`` floor used previously.
        scale = _compute_non_negative_scale(proposed_deltas, working_hexes)
        deltas: dict[str, float] = {h: scale * d for h, d in proposed_deltas.items()}

        # Apply deltas; no floor needed because scaling guarantees non-neg.
        # The tiny-negative guard catches float-rounding noise (capped at
        # 1e-12 absolute so we don't silently destroy real value).
        updated_hexes: dict[str, HexEconomicState] = {}
        for h3_id, hex_state in working_hexes.items():
            new_c = hex_state.constant_capital + deltas[h3_id]
            if -1e-12 < new_c < 0.0:
                new_c = 0.0
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
