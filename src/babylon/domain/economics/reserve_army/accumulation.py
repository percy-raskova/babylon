"""Accumulation-loop calculator: the Ch. 25 reserve-army producer.

Feature: 021-capital-volume-i / vol1-value-production program, Unit U3.

Implements the causal chain Marx describes in Capital Vol. I, Ch. 25 ("The
General Law of Capitalist Accumulation"): a RISING organic composition of
capital (more dead labor — machinery — relative to living labor) displaces
workers into the industrial reserve army; firm failures (bankruptcy) add a
second, independent inflow. Before this module, both ends of that chain were
live (``ValueTensor4x3.organic_composition`` is QCEW-populated;
``ReserveArmyDynamics.mechanization_displacement``/``firm_failures`` are
modeled fields) but nothing connected them, and ``ReserveArmySystem`` (#5)
read a ``reserve_ratio`` scalar that no scenario ever seeded — "gated
dormancy" (program prompt §2b/§2g).

This module derives ``ReserveArmyDynamics`` from the organic-composition
delta and the FRED-derived bankruptcy rate, then accumulates each tick's net
inflow into a persistent per-territory stock (``Territory.reserve_army_stock``)
whose share of the labor force (``stock / (stock + employment)``) is
``reserve_ratio`` — a real, derived producer rather than a fabricated seed
(Constitution III.8, Aleksandrov Test; ADR108 ruling (a)).

See Also:
    :mod:`babylon.domain.economics.reserve_army.types`: ``ReserveArmyDynamics``
    :mod:`babylon.domain.economics.reserve_army.calculator`: The sibling
        wage-pressure calculator this module's output feeds downstream, via
        ``ReserveArmySystem`` (#5).
    :mod:`babylon.domain.economics.tick.system`: ``TickDynamicsSystem`` wires
        this calculator into the tick pipeline (``_compute_accumulation_loop``).
"""

from __future__ import annotations

import math

from babylon.config.defines.economy_labor import ReserveArmyDefines
from babylon.domain.economics.reserve_army.types import ReserveArmyDynamics


class DefaultAccumulationLoopCalculator:
    """Derives ``ReserveArmyDynamics`` and ``reserve_ratio`` from the loop.

    Args:
        defines: ``ReserveArmyDefines`` carrying the mechanization/firm-failure
            coefficients. Defaults to ``ReserveArmyDefines()`` schema defaults.

    Example:
        >>> calc = DefaultAccumulationLoopCalculator()
        >>> dynamics = calc.compute_dynamics(
        ...     fips_code="26163", tick=52,
        ...     occ_current=2.5, occ_prior=2.0,
        ...     bankruptcy_rate=0.02, employment=100_000.0,
        ... )
        >>> dynamics.mechanization_displacement
        2500
        >>> new_stock, reserve_ratio = calc.compute_reserve_ratio(
        ...     prior_stock=0.0, dynamics=dynamics, employment=100_000.0,
        ... )
        >>> reserve_ratio
        0.034...
    """

    def __init__(self, defines: ReserveArmyDefines | None = None) -> None:
        """Initialize with the reserve-army coefficients.

        Args:
            defines: Configuration with mechanization_displacement_rate,
                firm_failure_conversion_rate. Defaults to schema defaults.
        """
        self._defines = defines if defines is not None else ReserveArmyDefines()

    def compute_dynamics(
        self,
        fips_code: str,
        tick: int,
        occ_current: float | None,
        occ_prior: float | None,
        bankruptcy_rate: float | None,
        employment: float,
    ) -> ReserveArmyDynamics | None:
        """Compute this period's reserve-army flow (Ch. 25).

        Args:
            fips_code: 5-digit county FIPS code.
            tick: Current simulation tick.
            occ_current: This year's organic composition (c/v) from
                ``ValueTensor4x3.organic_composition``, or ``None`` if the
                tensor registry has no data for this county-year.
            occ_prior: Last year's organic composition, or ``None`` if
                unavailable (e.g. the campaign's first simulated year — no
                prior year exists to diff against).
            bankruptcy_rate: FRED-derived bankruptcy rate in [0, 1] for this
                county-year, or ``None`` if the dispossession data source has
                no reading.
            employment: County employment this year — the base the
                displacement/failure coefficients scale against.

        Returns:
            ``ReserveArmyDynamics`` with this tick's flows, or ``None`` when
            neither input produces a nonzero flow — an honest empty domain
            (Constitution III.11), never a fabricated zero-flow record.
        """
        if employment <= 0.0:
            return None

        mechanization_displacement = 0
        if (
            occ_current is not None
            and occ_prior is not None
            and math.isfinite(occ_current)
            and math.isfinite(occ_prior)
        ):
            delta_occ = occ_current - occ_prior
            if delta_occ > 0.0:
                mechanization_displacement = round(
                    delta_occ * employment * self._defines.mechanization_displacement_rate
                )

        firm_failures = 0
        if bankruptcy_rate is not None and bankruptcy_rate > 0.0:
            firm_failures = round(
                bankruptcy_rate * employment * self._defines.firm_failure_conversion_rate
            )

        if mechanization_displacement == 0 and firm_failures == 0:
            return None

        return ReserveArmyDynamics(
            fips_code=fips_code,
            tick=tick,
            mechanization_displacement=mechanization_displacement,
            firm_failures=firm_failures,
            expansion_absorption=0,
            emigration=0,
        )

    def compute_reserve_ratio(
        self,
        prior_stock: float,
        dynamics: ReserveArmyDynamics,
        employment: float,
    ) -> tuple[float, float]:
        """Accumulate this tick's net inflow into the reserve-army stock.

        Args:
            prior_stock: The territory's carried ``reserve_army_stock``
                (``0.0`` if this is the first accumulation this session — a
                genuine initial condition, not a fabricated value).
            dynamics: This tick's ``ReserveArmyDynamics`` flow.
            employment: County employment — the other half of the labor
                force denominator.

        Returns:
            ``(new_stock, reserve_ratio)`` — stock floored at ``0.0`` (a
            reserve army cannot go negative), ratio =
            ``new_stock / (new_stock + employment)``, clamped to [0, 1].
        """
        new_stock = max(0.0, prior_stock + dynamics.net_inflow)
        denominator = new_stock + employment
        if denominator <= 0.0:
            return new_stock, 0.0
        reserve_ratio = new_stock / denominator
        return new_stock, min(reserve_ratio, 1.0)


__all__ = ["DefaultAccumulationLoopCalculator"]
