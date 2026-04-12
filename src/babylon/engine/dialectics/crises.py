"""Crisis Sublation Dialectics — consolidated crisis types.

All crisis dialectics produced by sublation of primary dialectics.
Crisis dialectics are ``Dialectic[EmptyPole, EmptyPole]`` shells that
represent self-reinforcing or system-level disruptions.

Producers:
    - :class:`RealizationCrisisDialectic` ← CirculationDialectic
    - :class:`DisproportionalityCrisisDialectic` ← ReproductionDialectic
    - :class:`DebtSpiralCrisisDialectic` ← SurplusDistributionDialectic
    - :class:`FinancialCrisisDialectic` ← CreditDialectic

See Also:
    :class:`babylon.engine.dialectics.base.Dialectic`: Generic base class.
"""

from __future__ import annotations

from babylon.engine.dialectics.base import Dialectic, EmptyPole, TickInputs, WorldView

# ===========================================================================
# From CirculationDialectic (V2)
# ===========================================================================


class RealizationCrisisDialectic(Dialectic[EmptyPole, EmptyPole]):
    """Triggered when CirculationDialectic sublates due to realization failure.

    Commodity capital cannot be reconverted to money capital because
    commodities cannot find buyers at their value.
    """

    type_tag: str = "RealizationCrisisDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> RealizationCrisisDialectic:
        """Crisis persistence — realization crisis deepens.

        Args:
            inputs: Upstream outputs (currently unused).
            world: Read-only world context.

        Returns:
            Updated crisis dialectic with new tick.
        """
        _ = inputs
        return self.model_copy(update={"tick_updated": world.tick})


# ===========================================================================
# From ReproductionDialectic (V2)
# ===========================================================================


class DisproportionalityCrisisDialectic(Dialectic[EmptyPole, EmptyPole]):
    """Triggered when ReproductionDialectic sublates due to departmental imbalance.

    Department I and Department II fail to maintain the exchange relation
    I(v+s) = IIc required for simple reproduction.
    """

    type_tag: str = "DisproportionalityCrisisDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> DisproportionalityCrisisDialectic:
        """Crisis persistence — disproportionality deepens.

        Args:
            inputs: Upstream outputs (currently unused).
            world: Read-only world context.

        Returns:
            Updated crisis dialectic with new tick.
        """
        _ = inputs
        return self.model_copy(update={"tick_updated": world.tick})


# ===========================================================================
# From SurplusDistributionDialectic (V3)
# ===========================================================================


class DebtSpiralCrisisDialectic(Dialectic[EmptyPole, EmptyPole]):
    """Crisis dialectic produced when financial claims exceed surplus.

    Produced by :meth:`SurplusDistributionDialectic.sublate` when
    interest + rent + taxes > total surplus (FR-016).

    The debt spiral is self-reinforcing: unpaid interest accrues as
    new debt, which increases interest obligations, which further
    exceeds surplus. Resolution requires either devaluation of claims
    (crisis/default) or dramatic increase in surplus (impossible under
    TRPF conditions).
    """

    type_tag: str = "DebtSpiralCrisisDialectic"

    def step(self, _inputs: TickInputs, world: WorldView) -> DebtSpiralCrisisDialectic:
        """Crisis persistence — debt spiral deepens or resolves.

        Args:
            _inputs: Upstream outputs (currently unused).
            world: Read-only world context.

        Returns:
            Updated crisis dialectic with new tick.
        """
        return self.model_copy(update={"tick_updated": world.tick})


# ===========================================================================
# From CreditDialectic (V3)
# ===========================================================================


class FinancialCrisisDialectic(Dialectic[EmptyPole, EmptyPole]):
    """Crisis dialectic produced when fictitious capital overaccumulates.

    Produced by :meth:`CreditDialectic.sublate` when the financialization
    index exceeds ``FINANCIALIZATION_BUBBLE`` (3.5).

    Marx's insight: crisis appears as a money/credit crisis but the
    underlying cause is overproduction relative to profitable realization.
    The credit system delays but ultimately amplifies crisis.
    """

    type_tag: str = "FinancialCrisisDialectic"

    def step(self, _inputs: TickInputs, world: WorldView) -> FinancialCrisisDialectic:
        """Crisis persistence — financial crisis deepens or resolves.

        Args:
            _inputs: Upstream outputs (currently unused).
            world: Read-only world context.

        Returns:
            Updated crisis dialectic with new tick.
        """
        return self.model_copy(update={"tick_updated": world.tick})


__all__ = [
    "DebtSpiralCrisisDialectic",
    "DisproportionalityCrisisDialectic",
    "FinancialCrisisDialectic",
    "RealizationCrisisDialectic",
]
