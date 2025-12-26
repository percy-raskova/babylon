"""State finance model for sovereign entities.

This module defines the StateFinance model which tracks the financial state
of sovereign entities (nation-states, client states) in the Babylon simulation.

Epoch 1 (The Ledger) - Political Economy of Liquidity specification.

The StateFinance model represents the fiscal capacity of a state actor:

- Treasury: available liquid funds for deployment
- Budgets: allocated spending on repression (police) and social reproduction (welfare)
- Taxation: extraction rate from bourgeoisie class
- Tribute: imperial rent flowing from CLIENT_STATE relationships
- Debt: accumulated liabilities with ceiling constraint

Key computed field:

- burn_rate: police_budget + social_reproduction_budget (spending per tick)
"""

from pydantic import BaseModel, ConfigDict, computed_field

from babylon.models.types import Coefficient, Currency


class StateFinance(BaseModel):
    """Financial state of a sovereign entity (nation-state, client state).

    Tracks treasury, budgets, taxation, and debt for state-level fiscal mechanics.
    Part of the Political Economy of Liquidity (Epoch 1: The Ledger).

    Attributes:
        treasury: Available liquid funds for deployment. Defaults to 100.0.
        police_budget: Repression cost per tick. Defaults to 10.0.
        social_reproduction_budget: Welfare cost per tick. Defaults to 15.0.
        tax_rate: Extraction rate from bourgeoisie [0, 1]. Defaults to 0.3.
        tribute_income: Imperial rent from CLIENT_STATE relationships. Defaults to 0.0.
        debt_level: Accumulated liabilities. Defaults to 0.0.
        debt_ceiling: Maximum sustainable debt. Defaults to 500.0.

    Example:
        >>> finance = StateFinance(treasury=200.0, police_budget=20.0)
        >>> finance.burn_rate
        35.0
    """

    model_config = ConfigDict(frozen=True)

    treasury: Currency = 100.0
    police_budget: Currency = 10.0
    social_reproduction_budget: Currency = 15.0
    tax_rate: Coefficient = 0.3
    tribute_income: Currency = 0.0
    debt_level: Currency = 0.0
    debt_ceiling: Currency = 500.0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def burn_rate(self) -> Currency:
        """Calculate total spending per tick.

        Returns:
            Sum of police_budget and social_reproduction_budget.
        """
        return Currency(self.police_budget + self.social_reproduction_budget)
