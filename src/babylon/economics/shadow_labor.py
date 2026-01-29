"""Shadow labor visibility calculations for Department III.

This module implements the Shadow Labor Sprint, adding the visibility
dimension (g_33) to distinguish monetized care work from shadow labor
subsidy in Department III (Social Reproduction).

**Theoretical Foundation:**

The visibility coefficient g_33 represents the fraction of reproductive
labor that enters the formal commodity circuit (monetized). The complement
(1 - g_33) represents shadow labor that subsidizes capital accumulation
without direct compensation.

**Formulas:**

.. math::

    v_{market} = T_{3,v} \\times w_{shadow} \\times g_{33}

    v_{shadow} = T_{3,v} \\times w_{shadow} \\times (1 - g_{33})

Where:
- :math:`T_{3,v}` = Total reproductive labor hours (from ATUS)
- :math:`w_{shadow}` = Shadow wage (replacement cost basis, $15.43/hour)
- :math:`g_{33}` = Visibility coefficient :math:`\\in [0, 1]`

**Boundary Conditions:**
- :math:`g_{33} = 1.0` → All care work monetized → :math:`v_{shadow} = 0`
- :math:`g_{33} = 0.0` → All care work unpaid → :math:`v_{market} = 0`

**Architecture: Lens Pattern:**

The visibility logic sits as a "Lens" or "View" on top of existing Department
III data. It does NOT modify the ValueTensor4x3 structure - it provides an
alternative decomposition for analytical purposes.

Example:
    >>> from babylon.economics.shadow_labor import ShadowLaborService
    >>> from babylon.data.atus import MockReproductionLoader
    >>> loader = MockReproductionLoader(
    ...     default_weekly_hours=1000/52,  # 1000 annual hours
    ...     shadow_wage_hourly=15.43,
    ... )
    >>> service = ShadowLaborService(loader=loader)
    >>> result = service.calculate_shadow_decomposition("06001", 2022, g_33_override=0.0)
    >>> result.v_shadow
    15430.0

See Also:
    :mod:`babylon.data.atus`: ATUS data loading infrastructure.
    :mod:`babylon.economics.reproduction`: Imperial rent calculation.
    :mod:`babylon.economics.tensor`: ValueTensor4x3 (economic primitive).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, computed_field

from babylon.data.atus.protocol import ReproductionLoaderProtocol


class ShadowLaborConfig(BaseModel):
    """Configuration for shadow labor visibility calculations.

    Controls how reproductive labor hours are split between monetized
    (formal commodity circuit) and shadow (unpaid household work) components.

    **Default g_33 = 0.3 Rationale:**

    ATUS 2022 data shows approximately 30% of care work is formally
    compensated (paid childcare, home health aides, nursing homes).
    The remaining 70% is unpaid household labor (shadow subsidy).

    **Default shadow_wage = $15.43/hour Rationale:**

    BLS Occupational Employment Statistics (May 2023) reports $15.43/hour
    median wage for Home Health and Personal Care Aides (SOC 31-1120).
    This represents the market replacement cost for unpaid care work.

    Args:
        g_33: Visibility coefficient [0, 1]. Fraction of care work monetized.
        shadow_wage_hourly: Hourly rate for valuing shadow labor (USD).

    Example:
        >>> config = ShadowLaborConfig()  # Defaults
        >>> config.g_33
        0.3
        >>> config = ShadowLaborConfig(g_33=0.5, shadow_wage_hourly=20.0)
        >>> config.g_33
        0.5
    """

    model_config = ConfigDict(frozen=True)

    g_33: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Visibility coefficient: fraction of care work that is monetized",
    )
    shadow_wage_hourly: float = Field(
        default=15.43,
        ge=0.0,
        description="Hourly rate for valuing shadow labor (replacement cost basis)",
    )


class ShadowLaborResult(BaseModel):
    """Result of shadow labor decomposition for a county-year.

    Decomposes reproductive labor value into monetized (v_market) and
    shadow (v_shadow) components based on the visibility coefficient g_33.

    **Value Conservation Invariant:**

    The visibility lens redistributes but does not create or destroy value:

    .. math::

        v_{market} + v_{shadow} = total\\_value

    **Interpretation:**
    - v_market: Value entering formal commodity circuit
    - v_shadow: Shadow subsidy to capital accumulation (unpaid)
    - shadow_subsidy_ratio: 1 - g_33 (fraction that is shadow)

    Args:
        fips_code: 5-digit FIPS county code.
        year: Data year.
        total_hours_annual: Annual reproductive labor hours.
        shadow_wage: Hourly replacement cost wage.
        g_33: Visibility coefficient used in calculation.

    Example:
        >>> result = ShadowLaborResult(
        ...     fips_code="06001",
        ...     year=2022,
        ...     total_hours_annual=1000.0,
        ...     shadow_wage=15.43,
        ...     g_33=0.3,
        ... )
        >>> result.total_value
        15430.0
        >>> result.v_market
        4629.0
        >>> result.v_shadow
        10801.0
    """

    model_config = ConfigDict(frozen=True)

    fips_code: str = Field(description="5-digit FIPS county code")
    year: int = Field(description="Data year")

    # Input values
    total_hours_annual: float = Field(
        ge=0.0,
        description="Annual reproductive labor hours (T_3,v)",
    )
    shadow_wage: float = Field(
        ge=0.0,
        description="Shadow wage (replacement cost, USD/hour)",
    )
    g_33: float = Field(
        ge=0.0,
        le=1.0,
        description="Visibility coefficient used in calculation",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_value(self) -> float:
        """Total reproductive labor value (monetized + shadow).

        .. math::

            total\\_value = T_{3,v} \\times w_{shadow}

        Returns:
            Total value in USD.
        """
        return self.total_hours_annual * self.shadow_wage

    @computed_field  # type: ignore[prop-decorator]
    @property
    def v_market(self) -> float:
        """Monetized care work value.

        The portion of reproductive labor that enters the formal
        commodity circuit (paid daycare, nursing homes, etc.).

        .. math::

            v_{market} = total\\_value \\times g_{33}

        Returns:
            Monetized value in USD.
        """
        return self.total_value * self.g_33

    @computed_field  # type: ignore[prop-decorator]
    @property
    def v_shadow(self) -> float:
        """Shadow subsidy value (unpaid reproductive labor).

        The portion of reproductive labor performed as unpaid household
        work, subsidizing capital accumulation without compensation.

        .. math::

            v_{shadow} = total\\_value \\times (1 - g_{33})

        Returns:
            Shadow subsidy value in USD.
        """
        return self.total_value * (1.0 - self.g_33)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def shadow_subsidy_ratio(self) -> float:
        """Ratio of shadow to total reproductive value.

        Simply the complement of the visibility coefficient.

        .. math::

            ratio = 1 - g_{33}

        Returns:
            Shadow subsidy ratio [0, 1].
        """
        return 1.0 - self.g_33


class ShadowLaborService:
    """Calculates shadow labor decomposition for Department III.

    This service provides a "Lens" view on reproductive labor, splitting
    it into monetized and shadow components without modifying the
    underlying ValueTensor4x3 structure.

    **Design Principle:**

    The shadow labor service operates alongside (not inside) the existing
    tensor/hydrator infrastructure. It takes reproductive labor hours
    from a loader and applies the visibility formula to produce the
    shadow decomposition.

    **Usage Pattern:**

    1. Inject a ReproductionLoaderProtocol implementation (e.g., MockReproductionLoader)
    2. Optionally provide a ShadowLaborConfig for custom defaults
    3. Call calculate_shadow_decomposition with county-year and optional g_33 override

    Args:
        loader: Data loader implementing ReproductionLoaderProtocol.
        config: Optional configuration (defaults to ShadowLaborConfig()).

    Example:
        >>> from babylon.data.atus import MockReproductionLoader
        >>> loader = MockReproductionLoader()
        >>> service = ShadowLaborService(loader=loader)
        >>> result = service.calculate_shadow_decomposition("06001", 2022)
        >>> result.v_shadow  # Shadow subsidy value
        11668.44  # 21 hours * 52 weeks * 15.43 * 0.7
    """

    def __init__(
        self,
        loader: ReproductionLoaderProtocol,
        config: ShadowLaborConfig | None = None,
    ) -> None:
        """Initialize service with loader and optional config.

        Args:
            loader: Data loader for reproductive labor hours.
            config: Configuration for visibility calculations.
        """
        self._loader = loader
        self._config = config or ShadowLaborConfig()

    def calculate_shadow_decomposition(
        self,
        fips_code: str,
        year: int,
        g_33_override: float | None = None,
    ) -> ShadowLaborResult:
        """Calculate shadow labor decomposition for a county-year.

        Loads reproductive labor hours from the configured loader and
        applies the visibility formula to produce monetized/shadow split.

        **Formula:**

        .. math::

            annual\\_hours = weekly\\_hours \\times 52

            v_{market} = annual\\_hours \\times w_{shadow} \\times g_{33}

            v_{shadow} = annual\\_hours \\times w_{shadow} \\times (1 - g_{33})

        Args:
            fips_code: 5-digit FIPS county code.
            year: Data year (>= 2003 for ATUS).
            g_33_override: Optional visibility coefficient override.
                If provided, takes precedence over config default.

        Returns:
            ShadowLaborResult with v_market and v_shadow decomposition.

        Example:
            >>> result = service.calculate_shadow_decomposition(
            ...     fips_code="06001",
            ...     year=2022,
            ...     g_33_override=1.0,  # Full monetization
            ... )
            >>> result.v_shadow
            0.0  # No shadow subsidy when fully monetized
        """
        # Load reproductive labor data
        summary = self._loader.load_county_summary(fips_code, year)
        shadow_wage = self._loader.get_shadow_wage(fips_code, year)

        # Convert weekly to annual hours
        annual_hours = summary.unpaid_care_hours_weekly * 52

        # Determine g_33 (override takes precedence)
        g_33 = g_33_override if g_33_override is not None else self._config.g_33

        return ShadowLaborResult(
            fips_code=fips_code,
            year=year,
            total_hours_annual=annual_hours,
            shadow_wage=shadow_wage,
            g_33=g_33,
        )


__all__ = [
    "ShadowLaborConfig",
    "ShadowLaborResult",
    "ShadowLaborService",
]
