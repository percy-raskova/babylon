"""Ground rent extraction for Volume III equalization (Feature 043, FR-010).

Implements the Marxian ground rent circuit that extracts value from the
surplus and reproduction fund based on land tenure composition.

Two forms of ground rent:

1. **Absolute Rent**: Extracted from surplus value by virtue of private
   land monopoly, regardless of locational advantage. Proportional to
   the private land share (excluding public and trust land).

2. **Differential Rent (Type I)**: Extracted from surplus value based on
   locational advantages that produce above-average profit rates. Only
   positive — below-average hexes have no locational surplus to extract.

The rent is split between:
- **rent_from_v**: Residential rent intercepted from variable capital
  (worker reproduction fund). Tenants pay this from wages.
- **rent_from_s**: Commercial/industrial rent that divides surplus value
  into profit of enterprise and ground rent.

See Also:
    :mod:`babylon.economics.substrate.equalization`: Capital migration logic.
    :mod:`babylon.economics.substrate.transitions`: Discrete tenure mutations.
    :class:`babylon.config.defines.RentCircuitDefines`: Tunable coefficients.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from babylon.config.defines import RentCircuitDefines
from babylon.economics.substrate.types import HexEconomicState


class GroundRentResult(BaseModel):
    """Result of ground rent extraction for a single hex.

    Args:
        absolute_rent: Rent from private land monopoly.
        differential_rent: Rent from locational advantage (>= 0).
        total_rent: absolute_rent + differential_rent.
        rent_from_v: Portion extracted from variable capital (residential).
        rent_from_s: Portion extracted from surplus value (commercial/industrial).
    """

    model_config = ConfigDict(frozen=True)

    absolute_rent: float = Field(ge=0.0, description="Rent from private land monopoly")
    differential_rent: float = Field(ge=0.0, description="Rent from locational advantage")
    total_rent: float = Field(ge=0.0, description="absolute_rent + differential_rent")
    rent_from_v: float = Field(ge=0.0, description="Portion from variable capital")
    rent_from_s: float = Field(ge=0.0, description="Portion from surplus value")


_ZERO_RENT = GroundRentResult(
    absolute_rent=0.0,
    differential_rent=0.0,
    total_rent=0.0,
    rent_from_v=0.0,
    rent_from_s=0.0,
)


def compute_ground_rent(
    state: HexEconomicState,
    r_avg: float,
    defines: RentCircuitDefines | None = None,
) -> GroundRentResult:
    """Compute ground rent extraction for a hex with tenure composition.

    Implements FR-010 of spec 026 (as amended by spec 043): ground rent
    is extracted from variable capital and surplus value based on tenure
    shares and local advantages (Differential Rent).

    Args:
        state: Hex economic state with optional tenure_composition.
        r_avg: Capital-weighted average profit rate across the grid.
        defines: Rent circuit parameters. Uses defaults if None.

    Returns:
        GroundRentResult with absolute and differential rent decomposition.
    """
    if state.tenure_composition is None:
        return _ZERO_RENT

    if defines is None:
        defines = RentCircuitDefines()

    tenure = state.tenure_composition
    s = state.surplus_value

    # ------------------------------------------------------------------
    # Private land share: excludes public and trust land
    # Trust land operates under qualitatively different property regime
    # (spec 038 INDIGENOUS filtration) — no appreciation/extraction.
    # ------------------------------------------------------------------
    private_land_share = max(0.0, 1.0 - tenure.public - tenure.trust_land)

    # ------------------------------------------------------------------
    # ABSOLUTE RENT
    # R_abs = s * absolute_rent_fraction * private_land_share
    # Baseline extraction from private monopoly on land.
    # ------------------------------------------------------------------
    absolute_rent = s * defines.absolute_rent_fraction * private_land_share

    # ------------------------------------------------------------------
    # DIFFERENTIAL RENT (Type I)
    # Only positive: below-average profit locations have no locational
    # surplus to extract. Per Marxian theory, differential rent arises
    # from superior land (higher profit rate) relative to marginal land.
    #
    # R_diff = elasticity * max(0, r_local - r_avg) * s * land_intensity
    # where land_intensity = fraction of hex in productive rent-bearing use
    # (commercial + industrial + residential_rental)
    # ------------------------------------------------------------------
    r_local = state.profit_rate
    profit_advantage = max(0.0, r_local - r_avg)
    land_intensity = tenure.commercial + tenure.industrial + tenure.residential_rental

    differential_rent = defines.differential_rent_elasticity * profit_advantage * s * land_intensity

    total_rent = absolute_rent + differential_rent

    # ------------------------------------------------------------------
    # SPLIT: v-sourced vs s-sourced
    #
    # Residential rent (owner-occupied + rental) is intercepted from v
    # (the worker's reproduction fund). Commercial/industrial rent
    # divides surplus value s into profit of enterprise and ground rent.
    # ------------------------------------------------------------------
    residential_share = tenure.residential_owner_occupied + tenure.residential_rental
    commercial_share = tenure.commercial + tenure.industrial
    total_productive = residential_share + commercial_share

    if total_productive > 0.0:
        v_fraction = residential_share / total_productive
        s_fraction = commercial_share / total_productive
    else:
        v_fraction = 0.0
        s_fraction = 0.0

    rent_from_v = total_rent * v_fraction
    rent_from_s = total_rent * s_fraction

    return GroundRentResult(
        absolute_rent=absolute_rent,
        differential_rent=differential_rent,
        total_rent=total_rent,
        rent_from_v=rent_from_v,
        rent_from_s=rent_from_s,
    )


__all__ = [
    "GroundRentResult",
    "compute_ground_rent",
]
