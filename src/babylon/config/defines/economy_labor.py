"""Labor-side dynamics: reserve army, dispossession, working day.

Spec 058: extracted from the historical ``babylon.config.defines`` monolith.
Re-exported via :mod:`babylon.config.defines.__init__`; composed into :class:`GameDefines` in :mod:`babylon.config.defines._assembler`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ReserveArmyDefines(BaseModel):
    """Reserve army of labor coefficients (Feature 021, FR-001/FR-002).

    Configures the bounded sigmoid that maps reserve_ratio to wage pressure.
    Higher reserve ratios produce stronger downward pressure on wages.

    See Also:
        ``specs/021-capital-volume-i/spec.md``: FR-001, FR-002, FR-003
    """

    model_config = ConfigDict(frozen=True)

    # Sigmoid parameters for wage pressure function
    sigmoid_k: float = Field(
        default=20.0,
        gt=0.0,
        le=100.0,
        description="Sigmoid steepness for reserve_ratio -> wage_pressure mapping",
    )
    sigmoid_r0: float = Field(
        default=0.08,
        gt=0.0,
        le=1.0,
        description="Reserve ratio at sigmoid midpoint (inflection point)",
    )

    # Saturation ceiling for wage pressure
    wage_pressure_ceiling: float = Field(
        default=0.5,
        gt=0.0,
        le=1.0,
        description="Maximum wage pressure coefficient (prevents total wage elimination)",
    )

    # Flow clamping
    min_employed_fraction: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description="Minimum fraction of labor force that must remain employed",
    )


class DispossessionDefines(BaseModel):
    """Dispossession event intensity weights (Feature 021, FR-004/FR-005).

    Configures the relative weight of each dispossession type when computing
    aggregate territory-level dispossession intensity.

    See Also:
        ``specs/021-capital-volume-i/spec.md``: FR-004, FR-005, FR-006
    """

    model_config = ConfigDict(frozen=True)

    # Intensity weights per dispossession type (must sum to ~1.0)
    weight_foreclosure: float = Field(
        default=0.40, ge=0.0, le=1.0, description="Game design: weight for foreclosure events."
    )
    weight_eviction: float = Field(
        default=0.30, ge=0.0, le=1.0, description="Game design: weight for eviction events."
    )
    weight_displacement: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Game design: weight for gentrification displacement events.",
    )
    weight_tax_sale: float = Field(
        default=0.05, ge=0.0, le=1.0, description="Game design: weight for tax sale events."
    )
    weight_eminent_domain: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description="Game design: weight for eminent domain events.",
    )
    weight_wage_theft: float = Field(
        default=0.03, ge=0.0, le=1.0, description="Game design: weight for wage theft events."
    )
    weight_incarceration_seizure: float = Field(
        default=0.03,
        ge=0.0,
        le=1.0,
        description="Game design: weight for incarceration-related seizure events.",
    )
    weight_pension_default: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description="Game design: weight for pension default events.",
    )

    # Deadweight loss fraction for value transfers
    deadweight_loss_fraction: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Game design: fraction of transferred value lost as deadweight (not received by anyone).",
    )
    transfer_scale: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description="Scale factor for wealth transfer amount: territory_wealth * intensity * scale",
    )


class WorkingDayDefines(BaseModel):
    """Working day characterization thresholds (Feature 021, FR-007/FR-008).

    Configures the threshold values for classifying territory-sector pairs
    by their dominant mode of surplus value extraction.

    See Also:
        ``specs/021-capital-volume-i/spec.md``: FR-007, FR-008, FR-011
    """

    model_config = ConfigDict(frozen=True)

    # Hours thresholds for exploitation mode classification
    absolute_hours_threshold: float = Field(
        default=45.0,
        gt=0.0,
        le=168.0,
        description="Game design: weekly hours above which exploitation is ABSOLUTE_DOMINANT.",
    )
    relative_hours_threshold: float = Field(
        default=40.0,
        gt=0.0,
        le=168.0,
        description="Game design: weekly hours at or below which exploitation may be RELATIVE_DOMINANT.",
    )

    # Intensity thresholds for exploitation mode classification
    intensity_threshold_high: float = Field(
        default=1.2,
        gt=0.0,
        description="Game design: labor intensity above which exploitation is RELATIVE_DOMINANT (with low hours).",
    )
    intensity_threshold_low: float = Field(
        default=1.1,
        gt=0.0,
        description="Game design: labor intensity below which exploitation is ABSOLUTE_DOMINANT (with high hours).",
    )

    # Visibility modifiers for consciousness dynamics
    absolute_visibility: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Game design: consciousness visibility modifier for ABSOLUTE exploitation.",
    )
    relative_visibility: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Game design: consciousness visibility modifier for RELATIVE exploitation.",
    )


__all__ = [
    "DispossessionDefines",
    "ReserveArmyDefines",
    "WorkingDayDefines",
]
