"""Contract: NationalParameters frozen dataclass.

Feature: 013-melt-basket-visibility
Date: 2026-02-01

This contract defines the immutable container for annual national parameters
used in Labor Aristocracy threshold determination.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, computed_field


class NationalParameters(BaseModel):
    """Annual national parameters for class position determination.

    This frozen Pydantic model holds all parameters needed to classify
    wages into class positions and compute imperial rent metrics.

    Immutability Rationale:
        Parameters are point-in-time snapshots. Once computed for a year,
        they should not change during a simulation run. This enables:

        1. Safe caching without invalidation concerns
        2. Thread-safe sharing across consumers
        3. Consistent class position calculations

    Monetary Units:
        All monetary values are in current-year dollars (not inflation-adjusted)
        per TSSI (Temporal Single-System Interpretation). This ensures that
        τ = GDP / L reflects actual price levels, not adjusted values.

    Example:
        >>> params = NationalParameters(
        ...     year=2022,
        ...     tau=65.0,
        ...     alpha=0.25,
        ...     gamma_import=0.35,
        ...     gamma_basket=0.68,
        ...     tau_effective=44.2,
        ...     v_reproduction=12.0,
        ...     estimated=True,
        ... )
        >>> params.tau_effective
        44.2
        >>> params.is_mvp
        True

    See Also:
        :class:`MELTCalculator`: Computes τ from BEA/QCEW data
        :class:`BasketVisibilityCalculator`: Computes γ_basket
        :mod:`babylon.economics.tensor`: NoDataSentinel for missing data
    """

    model_config = ConfigDict(frozen=True)

    year: int = Field(
        ...,
        ge=2010,
        le=2030,
        description="Calendar year for which parameters were computed",
    )

    tau: float = Field(
        ...,
        gt=0,
        description="MELT (Monetary Expression of Labor Time) in $/labor-hour",
    )

    alpha: float = Field(
        ...,
        ge=0,
        le=1,
        description="Import share of consumption basket [0, 1]",
    )

    gamma_import: float = Field(
        ...,
        gt=0,
        le=1,
        description="Weighted average visibility of imported goods (0, 1]",
    )

    gamma_basket: float = Field(
        ...,
        gt=0,
        le=1,
        description="Basket visibility coefficient (0, 1]",
    )

    tau_effective: float = Field(
        ...,
        gt=0,
        description="Labor Aristocracy wage threshold in $/hour",
    )

    v_reproduction: float = Field(
        ...,
        gt=0,
        description="Subsistence/reproduction floor in $/hour",
    )

    estimated: bool = Field(
        default=False,
        description="True if using MVP hardcoded values (not computed from data)",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_mvp(self) -> bool:
        """Check if parameters were computed in MVP mode.

        Returns:
            True if estimated flag is set (using hardcoded γ_basket)
        """
        return self.estimated

    @computed_field  # type: ignore[prop-decorator]
    @property
    def gamma_basket_theoretical(self) -> float:
        """Compute theoretical γ_basket from α and γ_import.

        This can differ from the stored gamma_basket if MVP mode
        uses a hardcoded value.

        Returns:
            γ_basket = 1 / (α/γ_import + (1-α))
        """
        if self.alpha == 0:
            return 1.0
        return 1.0 / (self.alpha / self.gamma_import + (1 - self.alpha))

    def validate_theoretical_consistency(self) -> list[str]:
        """Check for theoretical inconsistencies in parameters.

        Returns:
            List of warning messages (empty if all checks pass)
        """
        warnings: list[str] = []

        # τ_effective should equal τ × γ_basket
        expected_tau_effective = self.tau * self.gamma_basket
        if abs(self.tau_effective - expected_tau_effective) > 0.01:
            warnings.append(
                f"τ_effective ({self.tau_effective}) != τ × γ_basket "
                f"({expected_tau_effective:.2f})"
            )

        # V_reproduction should be less than τ_effective
        if self.v_reproduction >= self.tau_effective:
            warnings.append(
                f"V_reproduction ({self.v_reproduction}) >= τ_effective "
                f"({self.tau_effective}): theoretically impossible"
            )

        return warnings
