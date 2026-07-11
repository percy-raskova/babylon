"""Reserve Army of Labor domain types (Feature 021, FR-001/FR-002).

Frozen Pydantic models for reserve army composition and flow dynamics.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ReserveArmyState(BaseModel):
    """Composition of the industrial reserve army for a territory-year.

    Decomposes the surplus population into Marx's four categories:
    floating (between jobs), latent (underemployed/discouraged),
    stagnant (chronic irregular employment), and pauperized (unable to work).

    Args:
        fips_code: 5-digit county FIPS code.
        year: Calendar year.
        floating_reserve: Workers between jobs (approx. U-3 count).
        latent_reserve: Underemployed/discouraged (approx. U-6 - U-3).
        stagnant_reserve: Chronic irregular employment (PTER count).
        pauperized: Unable to work (Census disability + institutionalized).
        labor_force: Total civilian labor force.
    """

    model_config = ConfigDict(frozen=True)

    fips_code: str = Field(min_length=5, max_length=5)
    year: int = Field(ge=2005, le=2030)
    floating_reserve: int = Field(ge=0)
    latent_reserve: int = Field(ge=0)
    stagnant_reserve: int = Field(ge=0)
    pauperized: int = Field(ge=0)
    labor_force: int = Field(gt=0)

    @property
    def total_reserve(self) -> int:
        """Total reserve army (excludes pauperized per Marx)."""
        return self.floating_reserve + self.latent_reserve + self.stagnant_reserve

    @property
    def reserve_ratio(self) -> float:
        """Reserve ratio: total_reserve / labor_force, in [0, 1]."""
        ratio = self.total_reserve / self.labor_force
        return min(ratio, 1.0)


class ReserveArmyDynamics(BaseModel):
    """Per-tick flow rates governing reserve army formation and absorption.

    Args:
        fips_code: 5-digit county FIPS code.
        tick: Simulation tick.
        mechanization_displacement: Workers displaced by automation this tick.
        firm_failures: Workers from bankrupt enterprises.
        expansion_absorption: Workers hired during expansion.
        emigration: Workers leaving territory.
    """

    model_config = ConfigDict(frozen=True)

    fips_code: str = Field(min_length=5, max_length=5)
    tick: int = Field(ge=0)
    mechanization_displacement: int = Field(ge=0)
    firm_failures: int = Field(ge=0)
    expansion_absorption: int = Field(ge=0)
    emigration: int = Field(ge=0)

    @property
    def net_inflow(self) -> int:
        """Net change to reserve army (positive = growing)."""
        inflows = self.mechanization_displacement + self.firm_failures
        outflows = self.expansion_absorption + self.emigration
        return inflows - outflows
