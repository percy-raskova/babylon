"""Precarity state model for social class economic conditions.

This module defines the PrecarityState model which tracks the economic
precarity of working-class populations in the Babylon simulation.

Epoch 1 (The Ledger) - Political Economy of Liquidity specification.

The PrecarityState model captures the material conditions that determine
whether a class can survive through acquiescence or must turn to revolution:

- nominal_wage: Raw wage in currency units
- ppp_factor: Purchasing power parity adjustment
- inflation_index: Price level multiplier
- subsistence_threshold: Minimum for survival
- organization: Collective capacity to resist

Key computed fields:

- real_wage: (nominal_wage * ppp_factor) / inflation_index
- precarity_index: 1 - sigmoid(real_wage - subsistence_threshold)
- proletarianization_risk: precarity_index * (1 - organization)

The sigmoid function maps the wage-subsistence gap to a probability:

- When real_wage >> subsistence_threshold, precarity_index -> 0 (secure)
- When real_wage << subsistence_threshold, precarity_index -> 1 (precarious)
- When real_wage == subsistence_threshold, precarity_index -> 0.5 (marginal)
"""

import math

from pydantic import BaseModel, ConfigDict, Field, computed_field

from babylon.models.types import Coefficient, Currency, Probability


class PrecarityState(BaseModel):
    """Economic precarity metrics for a social class.

    Tracks nominal wages, PPP, inflation and computes real wages and precarity.
    Part of the Political Economy of Liquidity (Epoch 1: The Ledger).

    Attributes:
        nominal_wage: Raw wage in currency units. Defaults to 10.0.
        ppp_factor: Purchasing power parity adjustment [0, 1]. Defaults to 1.0.
        inflation_index: Price level multiplier (>= 1.0). Defaults to 1.0.
        subsistence_threshold: Minimum for survival. Defaults to 5.0.
        organization: Collective capacity to resist [0, 1]. Defaults to 0.5.

    Example:
        >>> precarity = PrecarityState(nominal_wage=3.0, subsistence_threshold=5.0)
        >>> precarity.real_wage
        3.0
        >>> precarity.precarity_index > 0.5  # Below subsistence = precarious
        True
    """

    model_config = ConfigDict(frozen=True)

    nominal_wage: Currency = 10.0
    ppp_factor: Coefficient = 1.0
    inflation_index: float = Field(default=1.0, ge=1.0)
    subsistence_threshold: Currency = 5.0
    organization: Probability = 0.5

    @computed_field  # type: ignore[prop-decorator]
    @property
    def real_wage(self) -> Currency:
        """Calculate real wage adjusted for PPP and inflation.

        Returns:
            (nominal_wage * ppp_factor) / inflation_index
        """
        return Currency((self.nominal_wage * self.ppp_factor) / self.inflation_index)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def precarity_index(self) -> Probability:
        """Calculate precarity based on wage-subsistence gap.

        Uses sigmoid function to map gap to probability:
        - precarity = 1 - sigmoid(real_wage - subsistence_threshold)
        - At subsistence threshold: precarity = 0.5
        - Above subsistence: precarity < 0.5 (secure)
        - Below subsistence: precarity > 0.5 (precarious)

        Returns:
            Probability [0, 1] where 1 is maximum precarity.
        """
        diff = float(self.real_wage) - float(self.subsistence_threshold)
        sigmoid_value = 1.0 / (1.0 + math.exp(-diff))
        return Probability(1.0 - sigmoid_value)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def proletarianization_risk(self) -> Probability:
        """Calculate risk of class falling into precarious proletariat.

        Risk is modulated by organization: organized classes can resist
        proletarianization even under precarious conditions.

        - proletarianization_risk = precarity_index * (1 - organization)
        - High organization provides protection (multiplier near 0)
        - Low organization means full exposure to precarity

        Returns:
            Probability [0, 1] where 1 is maximum risk.
        """
        return Probability(float(self.precarity_index) * (1.0 - float(self.organization)))
