"""Default tick state initializer seeding from economic calculators.

Feature: 017-simulation-tick-dynamics

Seeds initial SimulationTickState from census/calculator data for
the first tick of a historical simulation run.

See Also:
    :mod:`babylon.economics.tick.types`: State models
    :mod:`babylon.economics.tick.system`: Pipeline orchestration
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from babylon.economics.dynamics.types import ClassDistribution
from babylon.economics.tick.types import (
    CountyEconomicState,
    NationalTickParameters,
    SimulationTickState,
    SmoothedCoefficients,
)

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer

logger = logging.getLogger(__name__)

# Default class shares (US national average approximation)
_DEFAULT_BOURGEOISIE: float = 0.01
_DEFAULT_PETIT_BOURGEOISIE: float = 0.09
_DEFAULT_LABOR_ARISTOCRACY: float = 0.40
_DEFAULT_PROLETARIAT: float = 0.35
_DEFAULT_LUMPENPROLETARIAT: float = 0.15

# Default county economic indicators
_DEFAULT_UNEMPLOYMENT: float = 0.05
_DEFAULT_U6: float = 0.10
_DEFAULT_PTER: float = 0.04
_DEFAULT_NILF: float = 0.06
_DEFAULT_MEDIAN_WAGE: float = 21.0
_DEFAULT_EMPLOYMENT: float = 100_000.0
_DEFAULT_V_REPRODUCTION: float = 12.0


class DefaultTickInitializer:
    """Initialize SimulationTickState from calculator services.

    Seeds the initial state for a historical simulation run from
    calculator services. Uses default values where calculators return
    sentinel or are unavailable.

    Example:
        >>> initializer = DefaultTickInitializer()
        >>> state = initializer.initialize(2015, ["26163"], services)
    """

    def initialize(
        self,
        year: int,
        county_fips: list[str],
        services: ServiceContainer,
    ) -> SimulationTickState:
        """Seed initial SimulationTickState.

        Args:
            year: Starting simulation year.
            county_fips: List of county FIPS codes to include.
            services: ServiceContainer with calculator services.

        Returns:
            Initial SimulationTickState with seeded data.
        """
        national_params = self._seed_national_params(year, services)
        county_states = self._seed_county_states(year, county_fips, services)
        coefficients = SmoothedCoefficients(
            alpha=0.3,
            gamma_basket=national_params.gamma_basket,
            gamma_III=national_params.gamma_III,
            gamma_import=0.35,
            is_initialized=False,
        )

        return SimulationTickState(
            year=year,
            national_params=national_params,
            county_states=county_states,
            coefficients=coefficients,
        )

    def _seed_national_params(
        self,
        year: int,
        services: ServiceContainer,
    ) -> NationalTickParameters:
        """Seed national parameters from calculators.

        Args:
            year: Starting year.
            services: ServiceContainer with calculators.

        Returns:
            NationalTickParameters with seeded values.
        """
        # Get tau from MELT calculator
        tau: float = 62.0
        estimated: bool = True
        if services.melt_calculator is not None:
            tau_result = services.melt_calculator.get_melt(year)
            if tau_result and isinstance(tau_result, (int, float)):
                tau = float(tau_result)

        # Get gamma_basket from basket calculator
        gamma_basket: float = 0.68
        if services.basket_calculator is not None:
            gb_result = services.basket_calculator.get_gamma_basket(year)
            gamma_basket = gb_result[0]
            estimated = gb_result[1]

        # Get gamma_III from gamma calculator
        gamma_iii: float = 0.33
        if services.gamma_calculator is not None:
            g3_result = services.gamma_calculator.compute(year)
            if g3_result and hasattr(g3_result, "gamma_iii"):
                gamma_iii = g3_result.gamma_iii

        tau_effective = tau * gamma_basket

        return NationalTickParameters(
            year=year,
            tau=tau,
            gamma_basket=gamma_basket,
            gamma_basket_raw=gamma_basket,
            gamma_III=gamma_iii,
            gamma_III_raw=gamma_iii,
            tau_effective=tau_effective,
            v_reproduction=_DEFAULT_V_REPRODUCTION,
            estimated=estimated,
        )

    def _seed_county_states(
        self,
        year: int,
        county_fips: list[str],
        services: ServiceContainer,
    ) -> dict[str, CountyEconomicState]:
        """Seed county states from calculators.

        Args:
            year: Starting year.
            county_fips: FIPS codes to initialize.
            services: ServiceContainer with calculators.

        Returns:
            Dict of FIPS -> CountyEconomicState with seeded values.
        """
        states: dict[str, CountyEconomicState] = {}
        clamped_dist_year = min(max(year, 2007), 2030)

        for fips in county_fips:
            # Get capital stock from calculator
            capital_stock: float = 0.0
            if services.capital_calculator is not None:
                k_result = services.capital_calculator.get_K(fips, year)
                if k_result and isinstance(k_result, (int, float)):
                    capital_stock = float(k_result)

            # Get throughput from calculator
            throughput_position: float = 1.0
            supply_chain_depth: float = 2.0
            if services.throughput_calculator is not None:
                tp_result = services.throughput_calculator.compute_metrics(fips, year)
                if tp_result and hasattr(tp_result, "pi") and tp_result.pi is not None:
                    throughput_position = tp_result.pi
                    supply_chain_depth = tp_result.supply_chain_depth

            dist = ClassDistribution(
                fips=fips,
                year=clamped_dist_year,
                bourgeoisie_share=_DEFAULT_BOURGEOISIE,
                petit_bourgeoisie_share=_DEFAULT_PETIT_BOURGEOISIE,
                labor_aristocracy_share=_DEFAULT_LABOR_ARISTOCRACY,
                proletariat_share=_DEFAULT_PROLETARIAT,
                lumpenproletariat_share=_DEFAULT_LUMPENPROLETARIAT,
            )

            clamped_year = min(max(year, 2007), 2040)
            states[fips] = CountyEconomicState(
                fips=fips,
                year=clamped_year,
                capital_stock=capital_stock,
                throughput_position=throughput_position,
                supply_chain_depth=supply_chain_depth,
                unemployment_rate=_DEFAULT_UNEMPLOYMENT,
                u6_rate=_DEFAULT_U6,
                pter_rate=_DEFAULT_PTER,
                nilf_rate=_DEFAULT_NILF,
                median_wage=_DEFAULT_MEDIAN_WAGE,
                employment=_DEFAULT_EMPLOYMENT,
                class_distribution=dist,
                phi_hour=0.0,
                crisis=False,
            )

        return states


__all__ = ["DefaultTickInitializer"]
