"""ReproductionRequirements computation and stub data source.

Feature: 025-tensor-hierarchy
Date: 2026-02-26

Implements:
- DefaultReproductionRequirementsComputer: Computes total reproduction cost
  from a ReproductionRequirements tensor via SNLT conversion.
- DefaultReproductionSource: Stub returning NoDataSentinel (CEX/ATUS data
  loader deferred pending constitutional amendment US4).

See Also:
    :mod:`babylon.domain.economics.tensor_hierarchy.types`: ReproductionRequirements type.
    :mod:`babylon.domain.economics.tensor_hierarchy.protocols`: ReproductionSource protocol.
"""

from __future__ import annotations

import logging

from babylon.domain.economics.tensor import NoDataSentinel
from babylon.domain.economics.tensor_hierarchy.types import ReproductionRequirements

logger = logging.getLogger(__name__)

# Reason used in all NoDataSentinel instances from this stub loader
_STUB_REASON = "CEX data source pending constitutional amendment (US4 deferred loader)"


class DefaultReproductionRequirementsComputer:
    """Computes total reproduction cost from a ReproductionRequirements tensor.

    The total reproduction cost for a social class is the sum of:

    1. **Consumption costs** (use-value → labor-hours via SNLT):
       For each department and use-value category consumed by the class,
       multiply the use-value amount by the Social Necessary Labor Time (SNLT,
       in hours per dollar) to convert to labor-hours.

    2. **Reproductive labor hours** (already in hours):
       Unpaid reproductive labor performed for the class (childcare, domestic
       work, etc.) from ATUS data.

    The formula:

    .. math::

        C_{class} = \\text{SNLT} \\times \\sum_{d,k} c_{class,d,k}
                    + \\sum_{r,t} l_{class,r,t}

    where :math:`c_{class,d,k}` is consumption in dept d / category k,
    and :math:`l_{class,r,t}` is reproductive labor of type t by laborer r.

    Example:
        >>> computer = DefaultReproductionRequirementsComputer()
        >>> cost = computer.total_reproduction_cost(req, "proletariat", snlt=0.5)
    """

    def total_reproduction_cost(
        self,
        requirements: ReproductionRequirements,
        social_class: str,
        snlt: float,
    ) -> float:
        """Compute total reproduction cost for a social class in labor-hours.

        Args:
            requirements: ReproductionRequirements tensor with consumption and
                reproductive labor data.
            social_class: Target social class name.
            snlt: Social Necessary Labor Time in hours per dollar.

        Returns:
            Total reproduction cost in labor-hours (float >= 0).
        """
        consumption_total = self._sum_consumption(requirements, social_class)
        labor_total = self._sum_reproductive_labor(requirements, social_class)
        return snlt * consumption_total + labor_total

    @staticmethod
    def _sum_consumption(
        requirements: ReproductionRequirements,
        social_class: str,
    ) -> float:
        """Sum all consumption use-values for a class across all departments.

        Args:
            requirements: Source tensor.
            social_class: Target class name.

        Returns:
            Total consumption use-value (dimensionless units).
        """
        class_consumption = requirements.consumption.get(social_class, {})
        total: float = 0.0
        for dept_items in class_consumption.values():
            for amount in dept_items.values():
                total += amount
        return total

    @staticmethod
    def _sum_reproductive_labor(
        requirements: ReproductionRequirements,
        social_class: str,
    ) -> float:
        """Sum all reproductive labor hours provided for a class.

        Args:
            requirements: Source tensor.
            social_class: Target class whose labor is summed.

        Returns:
            Total reproductive labor hours (float >= 0).
        """
        class_labor = requirements.reproductive_labor.get(social_class, {})
        total: float = 0.0
        for laborer_types in class_labor.values():
            for hours in laborer_types.values():
                total += hours
        return total


class DefaultReproductionSource:
    """Stub data source for ReproductionRequirements (CEX loader deferred).

    Returns NoDataSentinel for all queries. The production implementation
    requires CEX (Consumer Expenditure Survey) and ATUS (American Time Use
    Survey) data, which requires a constitutional amendment for US4 to proceed.

    Example:
        >>> source = DefaultReproductionSource()
        >>> req = source.get_requirements(2022)
        >>> bool(req)  # NoDataSentinel is falsy
        False
    """

    def get_requirements(self, year: int) -> NoDataSentinel:
        """Return NoDataSentinel — CEX/ATUS data loader is deferred.

        Args:
            year: Calendar year (ignored; data not available).

        Returns:
            NoDataSentinel with reason explaining the deferred loader.
        """
        return NoDataSentinel("national", year, _STUB_REASON)

    def total_reproduction_cost(
        self,
        social_class: str,  # noqa: ARG002
        year: int,
        snlt: float,  # noqa: ARG002
    ) -> NoDataSentinel:
        """Return NoDataSentinel — no data available to compute cost.

        Args:
            social_class: Target class name (ignored).
            year: Calendar year (used in sentinel).
            snlt: SNLT value (ignored).

        Returns:
            NoDataSentinel with reason explaining the deferred loader.
        """
        return NoDataSentinel("national", year, _STUB_REASON)


__all__ = [
    "DefaultReproductionRequirementsComputer",
    "DefaultReproductionSource",
]
