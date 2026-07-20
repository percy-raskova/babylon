"""Substrate physical-stock coefficients (#39 T6).

``raw_material_stock`` depletion/regeneration -- a genuinely PARALLEL stock
family to ``Territory.biocapacity``/``MetabolismDefines`` (D-T6-3): same
``ΔB = R - E·η`` formula shape (:func:`babylon.formulas.metabolic_rift.
calculate_biocapacity_delta`), but its own coefficients, because
``raw_material_stock`` (a dollar-denominated USGS mineral-value stock) and
``biocapacity`` (an ecological-limits index) are different physical
quantities with no reason to share a sensitivity to extraction. No energy or
biocapacity stock coefficients exist here -- no reference-data source backs
those two (see ``engine/systems/substrate.py`` module docstring).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SubstrateDefines(BaseModel):
    """Raw-material stock depletion/regeneration coefficients."""

    model_config = ConfigDict(frozen=True)

    depletion_scale: float = Field(
        default=1.0,
        ge=0.0,
        le=10.0,
        description=(
            "Game design: multiplier applied to a territory's "
            "extraction_intensity before it drives raw_material_stock "
            "depletion -- lets raw-material sensitivity to extraction "
            "diverge from Territory.biocapacity's own (MetabolismSystem) "
            "dynamics. 1.0 = extraction_intensity applies unscaled."
        ),
    )
    regeneration_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description=(
            "Game design: fraction of raw_material_stock regenerated per "
            "tick. Minerals are non-renewable, so the default is 0.0 "
            "(monotone depletion); nonzero exists for modding a renewable "
            "substrate variant, not as a balancing fudge factor."
        ),
    )
    entropy_factor: float = Field(
        default=1.2,
        gt=1.0,
        le=3.0,
        description=(
            "Game design: extraction costs more than it yields "
            "(thermodynamic inefficiency) -- mirrors "
            "MetabolismDefines.entropy_factor's convention for this "
            "parallel raw_material_stock family."
        ),
    )


__all__ = ["SubstrateDefines"]
