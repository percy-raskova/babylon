"""Imperial Rent calculation via Emmanuel-Amin Unequal Exchange framework.

This module implements the imperial rent calculation as a derived corollary
to the Marxian value tensor. Imperial rent measures the structural subsidy
of imperialism - the gap between First World wages and Third World
reproduction costs.

**Theoretical Foundation (Emmanuel-Amin Unequal Exchange):**

Imperial rent is NOT measured against an abstract biological minimum.
It is measured against what it costs to reproduce a worker in the
global periphery (Third World). The differential represents value
transferred from periphery to core through unequal exchange.

**Current Implementation (Simple Baseline):**

    Phi = W_actual - P_periphery

Where:
- W_actual = Total variable capital (wages) in the core county
- P_periphery = Cost to reproduce a worker in the global periphery

This gross differential OVERSTATES individual worker subsidy because
value chain intermediaries (peripheral bourgeoisie, compradors, logistics,
finance) extract portions before it reaches core workers.

**Future Roadmap:**

- Model value chain extraction layers explicitly
- Apply extraction coefficient: Phi_worker = gross_differential * alpha
- Regional differentiation of periphery baselines
- Integration with World Bank/ILO peripheral wage data

Example:
    >>> from babylon.economics.reproduction import (
    ...     PeripheryReproductionBasket,
    ...     ImperialRentCalculator,
    ... )
    >>> basket = PeripheryReproductionBasket.default()
    >>> calculator = ImperialRentCalculator(basket)
    >>> rent = calculator.calculate_imperial_rent(50000.0, "26163", 2022)
    >>> rent  # ~$48,000 gross imperial rent
    48000.0

See Also:
    :mod:`babylon.economics.hydrator`: Integration point.
    :mod:`babylon.economics.tensor`: Economic primitive (ValueTensor4x3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import yaml
from pydantic import BaseModel, ConfigDict, Field, computed_field

from babylon.economics.tensor import ValueTensor4x3
from babylon.models.types import Currency


class PeripheryReproductionBasket(BaseModel):
    """Cost of reproducing a worker in the global periphery (Third World).

    This is NOT an abstract biological minimum. It represents the actual
    material conditions required to reproduce labor power in peripheral
    economies - the baseline against which imperial rent is measured.

    The Emmanuel-Amin framework: unequal exchange means First World wages
    vastly exceed what it costs to reproduce labor globally. The differential
    is imperial rent, distributed across the value chain.

    **Current Implementation:** Simple baseline with configurable values
    based on World Bank poverty data (~$2/day extreme poverty line).

    **Future Roadmap:**
    - Integrate World Bank/ILO data for peripheral wages by country/region
    - Model value chain layers
    - Apply extraction coefficients for worker-level subsidy estimates

    Args:
        annual_food_cost: Food cost (USD/year). Default ~$2.20/day.
        annual_shelter_cost: Basic housing (USD/year).
        annual_clothing_cost: Minimal clothing (USD/year).
        annual_healthcare_cost: Basic healthcare access (USD/year).
        annual_other_cost: Transport, miscellaneous (USD/year).

    Example:
        >>> basket = PeripheryReproductionBasket.default()
        >>> basket.annual_total
        2000.0
        >>> basket = PeripheryReproductionBasket(annual_food_cost=1000.0)
        >>> basket.annual_total
        2200.0
    """

    model_config = ConfigDict(frozen=True)

    # Annual reproduction cost components (USD, peripheral prices)
    annual_food_cost: Annotated[float, Field(ge=0.0)] = 800.0
    """Food cost (USD/year). Default ~$2.20/day, World Bank extreme poverty line."""

    annual_shelter_cost: Annotated[float, Field(ge=0.0)] = 600.0
    """Basic housing (USD/year). Peripheral economy rental costs."""

    annual_clothing_cost: Annotated[float, Field(ge=0.0)] = 100.0
    """Minimal clothing (USD/year). Basic apparel needs."""

    annual_healthcare_cost: Annotated[float, Field(ge=0.0)] = 200.0
    """Basic healthcare access (USD/year). Primary care, medications."""

    annual_other_cost: Annotated[float, Field(ge=0.0)] = 300.0
    """Transport, miscellaneous (USD/year). Commuting, basic goods."""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def annual_total(self) -> float:
        """Total annual reproduction cost in periphery.

        Returns:
            Sum of all cost components (USD/year).
        """
        return (
            self.annual_food_cost
            + self.annual_shelter_cost
            + self.annual_clothing_cost
            + self.annual_healthcare_cost
            + self.annual_other_cost
        )

    @classmethod
    def from_yaml(cls, path: Path) -> PeripheryReproductionBasket:
        """Load basket configuration from YAML file.

        The YAML file should have a 'periphery_reproduction' key with
        cost components as subkeys.

        Args:
            path: Path to YAML configuration file.

        Returns:
            PeripheryReproductionBasket with loaded values.

        Raises:
            FileNotFoundError: If path does not exist.
            KeyError: If 'periphery_reproduction' key missing.
        """
        with path.open() as f:
            data = yaml.safe_load(f)

        config = data["periphery_reproduction"]
        return cls(
            annual_food_cost=config.get("annual_food_cost", 800.0),
            annual_shelter_cost=config.get("annual_shelter_cost", 600.0),
            annual_clothing_cost=config.get("annual_clothing_cost", 100.0),
            annual_healthcare_cost=config.get("annual_healthcare_cost", 200.0),
            annual_other_cost=config.get("annual_other_cost", 300.0),
        )

    @classmethod
    def default(cls) -> PeripheryReproductionBasket:
        """Return default basket (~$2000/year peripheral reproduction).

        Uses World Bank extreme poverty line (~$2/day) as food baseline
        plus basic costs for shelter, clothing, healthcare, transport.

        Returns:
            PeripheryReproductionBasket with default values.
        """
        return cls()


class ImperialRentCalculator:
    """Calculates imperial rent as differential between core wages and periphery reproduction.

    **Current Implementation (Simple Baseline):**

    - Uses fixed peripheral reproduction cost from PeripheryReproductionBasket
    - Phi = W_actual - P_periphery (gross differential)
    - Does NOT model value chain intermediaries

    **Future Roadmap:**

    - Integrate World Bank/ILO peripheral wage data by country/region
    - Model value chain extraction layers (peripheral bourgeoisie, compradors)
    - Apply extraction coefficient: Phi_worker = gross_differential * alpha
    - Geographic specificity (different periphery baselines by region)

    The simple baseline OVERSTATES individual worker subsidy but correctly
    captures the structural relationship of unequal exchange.

    Args:
        periphery_basket: Configuration for peripheral reproduction costs.

    Example:
        >>> basket = PeripheryReproductionBasket.default()
        >>> calculator = ImperialRentCalculator(basket)
        >>> rent = calculator.calculate_imperial_rent(50000.0, "26163", 2022)
        >>> rent
        48000.0
        >>> calculator.periphery_baseline
        2000.0
    """

    def __init__(self, periphery_basket: PeripheryReproductionBasket) -> None:
        """Initialize calculator with periphery baseline configuration.

        Args:
            periphery_basket: Peripheral reproduction cost configuration.
        """
        self._periphery_basket = periphery_basket

    def calculate_imperial_rent(
        self,
        core_wages: Currency,
        fips_code: str,  # noqa: ARG002 - future: regional adjustments
        year: int,  # noqa: ARG002 - future: inflation adjustment
    ) -> float:
        """Calculate imperial rent (gross differential).

        Imperial rent is the difference between what core workers receive
        in wages and what it costs to reproduce a worker in the periphery.

        **Simple Baseline Formula:**
            Phi = W_actual - P_periphery

        This overstates individual worker subsidy but captures the
        structural relationship. Future implementations will apply
        extraction coefficients for value chain layers.

        Args:
            core_wages: Total variable capital (wages) from tensor.
            fips_code: County code (future: regional adjustments).
            year: Data year (future: inflation adjustment).

        Returns:
            Imperial rent Phi = core_wages - periphery_reproduction_cost.
            Can be negative if core wages below periphery baseline
            (degenerate case for US counties).
        """
        periphery_cost = self._periphery_basket.annual_total

        # Simple baseline: gross differential
        # Future: apply extraction coefficient, regional adjustments
        rent = core_wages - periphery_cost

        # Rent can be negative for degenerate cases (zero wages)
        return rent

    @property
    def periphery_baseline(self) -> Currency:
        """The peripheral reproduction cost used as baseline.

        Returns:
            Annual cost to reproduce a worker in the periphery (USD).
        """
        return Currency(self._periphery_basket.annual_total)


class ImperialRentResult(BaseModel):
    """Result of imperial rent calculation for a county-year.

    Wraps the economic primitive (ValueTensor4x3) and adds the
    imperial rent calculation as a derived corollary.

    **Interpretation Note:**

    The imperial_rent field represents the GROSS DIFFERENTIAL between
    core wages and peripheral reproduction cost. This overstates the
    actual subsidy received by individual workers because value chain
    intermediaries (peripheral bourgeoisie, compradors, etc.) extract
    portions of this differential before it reaches core workers.

    Future implementations will model these extraction layers explicitly.

    Args:
        tensor: The underlying Marxian value tensor.
        periphery_baseline: P_periphery - cost to reproduce worker in periphery.
        core_wages: W_actual - total variable capital (wages) in core.
        imperial_rent: Phi = W_actual - P_periphery (gross differential).

    Example:
        >>> result = hydrator.hydrate_with_rent("26163", 2022)
        >>> result.imperial_rent
        48000.0
        >>> result.wage_multiple
        25.0
        >>> result.imperial_rent_ratio
        0.96
    """

    model_config = ConfigDict(frozen=True)

    tensor: ValueTensor4x3
    """The underlying Marxian value tensor (economic primitive)."""

    periphery_baseline: Currency
    """P_periphery: Cost to reproduce a worker in the global periphery (USD/year)."""

    core_wages: Currency
    """W_actual: Total variable capital (wages) in the core county (USD/year)."""

    imperial_rent: float  # Can be negative for degenerate cases
    """Phi = W_actual - P_periphery: Gross imperial rent (USD/year).

    Can be negative if core wages are below periphery baseline (degenerate case).
    """

    @computed_field  # type: ignore[prop-decorator]
    @property
    def imperial_rent_ratio(self) -> float:
        """Phi as proportion of core wages.

        Represents the fraction of wages that exceeds peripheral reproduction cost.
        A ratio of 0.95 means 95% of wages are 'imperial surplus' above baseline.

        Returns:
            Phi / core_wages, or 0.0 if core_wages is zero.
        """
        if self.core_wages == 0.0:
            return 0.0
        return self.imperial_rent / self.core_wages

    @computed_field  # type: ignore[prop-decorator]
    @property
    def wage_multiple(self) -> float:
        """How many times peripheral reproduction cost the core wages represent.

        A multiple of 25x means core workers receive 25x what it costs
        to reproduce a worker in the periphery.

        Returns:
            core_wages / periphery_baseline, or inf if baseline is zero.
        """
        if self.periphery_baseline == 0.0:
            return float("inf")
        return self.core_wages / self.periphery_baseline


__all__ = [
    "ImperialRentCalculator",
    "ImperialRentResult",
    "PeripheryReproductionBasket",
]
