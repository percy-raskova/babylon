"""Capital Volume III Dialectics — Distribution, TRPF, Credit, Rent, Imperial.

Volume III completes the outermost layer of the dialectical engine. Where
Volume I models production (how surplus value is created) and Volume II
models circulation (how it is realized), Volume III models distribution:
how total surplus value decomposes into competing claims — profit of
enterprise, interest, ground rent, and taxes — and the systemic dynamics
this decomposition drives.

Five primary dialectics:

* :class:`SurplusDistributionDialectic` (Ch9-10): Surplus Value Distribution
* :class:`TRPFDialectic` (Ch13-15): Falling Profit Rate ↔ Counter-Tendencies
* :class:`CreditDialectic` (Ch21-33): Real Capital ↔ Fictitious Capital
* :class:`RentDialectic` (Ch37-47): Ground Rent extraction categories
* :class:`ImperialDialectic` (Ch14 §V + MLM-TW): Core ↔ Periphery

Two crisis sublation types:

* :class:`DebtSpiralCrisisDialectic`: From SurplusDistributionDialectic
* :class:`FinancialCrisisDialectic`: From CreditDialectic

Delegation Pattern:
    Dialectic classes are **thin shells** around existing domain logic.
    Each pole model reimplements the domain formula (e.g., ``p = s - i - r - t``)
    rather than calling the domain calculator directly, because the dialectic
    layer receives pre-computed inputs and operates at a higher abstraction level.
    The mathematical formulas are **identical** to their domain counterparts.

    .. list-table:: Domain Delegation Map
       :header-rows: 1

       * - Dialectic
         - Reimplements
         - Domain Source
       * - ``SurplusDistributionDialectic``
         - ``p = s - i - r - t``
         - ``economics.distribution.SurplusValueDistribution``
       * - ``RentDialectic``
         - ``total_rent = agri + resource + urban``
         - ``economics.rent.RentExtraction``
       * - ``TRPFDialectic``
         - (delegates directly)
         - ``counter_tendencies.CounterTendencyStrength``
       * - ``CreditDialectic``
         - (delegates directly)
         - ``credit.FictitiousCapitalStock.ratio_to_real()``
       * - ``ImperialDialectic``
         - (delegates directly)
         - ``formulas.fundamental_theorem``

Future Work:
    A ``ValueTransformationDialectic`` (labor-value hours → money wages)
    is needed to bridge the value-price gap. See the Transformation Problem
    (V3 Ch9): values must be converted to prices of production for the
    simulation to model wage-setting realistically. This is deferred to
    a future specification (see spec 024, Assumptions, line 221).

See Also:
    :mod:`babylon.engine.dialectics.volume_1`: Production dialectics.
    :mod:`babylon.engine.dialectics.volume_2`: Circulation dialectics.
    :mod:`babylon.economics.distribution`: Surplus distribution calculators.
    :mod:`babylon.economics.credit`: Credit cycle and fictitious capital.
    :mod:`babylon.economics.counter_tendencies`: TRPF counter-tendencies.
    :mod:`babylon.economics.rent`: Ground rent extraction.
    :mod:`babylon.economics.financial_crisis`: Integrated crisis assessment.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from babylon.economics.counter_tendencies.types import CounterTendencyStrength
from babylon.economics.credit.types import (
    FINANCIALIZATION_BUBBLE,
    FictitiousCapitalStock,
)
from babylon.engine.dialectics.base import Dialectic, EmptyPole, TickInputs, WorldView
from babylon.formulas.fundamental_theorem import (
    calculate_imperial_rent,
    calculate_labor_aristocracy_ratio,
)

# ===========================================================================
# Pole Models — lightweight wrappers for dialectic-relevant state
# ===========================================================================


class SurplusDistributionPole(BaseModel):
    """Pole A for the Distribution dialectic.

    Reimplements the surplus value distribution identity from
    ``economics.distribution.SurplusValueDistribution`` for the
    dialectic layer. The formula ``p = s - i - r - t`` is identical
    to ``SurplusValueDistribution.profit_of_enterprise``. This is
    intentional: the dialectic receives pre-computed distribution
    inputs and does not perform data-source lookups.

    See Also:
        :class:`babylon.economics.distribution.types.SurplusValueDistribution`

    Attributes:
        total_surplus: Total surplus value produced (s).
        interest_payments: Interest claim on surplus (i).
        ground_rent: Ground rent claim on surplus (r).
        taxes: Tax claim on surplus (t).
    """

    model_config = ConfigDict(frozen=True)

    total_surplus: float = Field(..., description="Total surplus value s.")
    interest_payments: float = Field(default=0.0, ge=0.0, description="Interest claim i.")
    ground_rent: float = Field(default=0.0, ge=0.0, description="Ground rent claim r.")
    taxes: float = Field(default=0.0, ge=0.0, description="Tax claim t.")

    @property
    def profit_of_enterprise(self) -> float:
        """Residual: p = s - i - r - t."""
        return self.total_surplus - self.interest_payments - self.ground_rent - self.taxes

    @property
    def claims_exceed_surplus(self) -> bool:
        """Whether claims exceed total surplus (FR-016)."""
        return self.profit_of_enterprise < 0.0


class ProfitRateState(BaseModel):
    """Pole A for the TRPF dialectic.

    Attributes:
        profit_rate: Current average rate of profit.
        profit_rate_trend: Year-over-year change in profit rate.
        organic_composition: c/v ratio (OCC).
    """

    model_config = ConfigDict(frozen=True)

    profit_rate: float = Field(default=0.0, description="Current r = s/(c+v).")
    profit_rate_trend: float = Field(default=0.0, description="Year-over-year change.")
    organic_composition: float = Field(default=0.0, ge=0.0, description="OCC = c/v.")


class CreditPole(BaseModel):
    """Pole A for the Credit dialectic — real capital side.

    Attributes:
        total_real_capital: Accumulated real capital stock K.
        profit_rate: Industrial profit rate.
        gdp: Real GDP for financialization ratio computation.
    """

    model_config = ConfigDict(frozen=True)

    total_real_capital: float = Field(..., ge=0.0, description="Real capital stock K.")
    profit_rate: float = Field(default=0.0, description="Industrial profit rate.")
    gdp: float = Field(..., gt=0.0, description="Real GDP.")


class RentPole(BaseModel):
    """Pole A for the Rent dialectic — three-category decomposition.

    Reimplements the three-category rent aggregation from
    ``economics.rent.types.RentExtraction``. The formula
    ``total_rent = agri + resource + urban`` is identical.
    This is intentional: the dialectic receives pre-aggregated
    county-level data and does not perform data-source lookups.

    See Also:
        :class:`babylon.economics.rent.types.RentExtraction`

    Attributes:
        agricultural_rent: Rent from farming / rural land.
        resource_rent: Rent from extractive industries.
        urban_rent: Rent from urban / building-site monopoly.
    """

    model_config = ConfigDict(frozen=True)

    agricultural_rent: float = Field(default=0.0, ge=0.0)
    resource_rent: float = Field(default=0.0, ge=0.0)
    urban_rent: float = Field(default=0.0, ge=0.0)

    @property
    def total_rent(self) -> float:
        """Total ground rent across all categories."""
        return self.agricultural_rent + self.resource_rent + self.urban_rent


class CoreEconomy(BaseModel):
    """Pole A for the Imperial dialectic — core / imperialist side.

    Attributes:
        core_wages: Wages paid to core workers (Wc).
        value_produced: Value produced by core workers (Vc).
        profit_rate: Core industrial profit rate.
    """

    model_config = ConfigDict(frozen=True)

    core_wages: float = Field(..., gt=0.0, description="Core wages Wc.")
    value_produced: float = Field(..., gt=0.0, description="Value produced Vc.")
    profit_rate: float = Field(default=0.0, description="Core profit rate.")


class PeripheryEconomy(BaseModel):
    """Pole B for the Imperial dialectic — periphery / exploited side.

    Attributes:
        periphery_wages: Wages paid to periphery workers (Wp).
        extraction_rate: Imperial extraction efficiency alpha [0, 1].
        consciousness: Periphery resistance level Psi_p [0, 1].
    """

    model_config = ConfigDict(frozen=True)

    periphery_wages: float = Field(default=0.0, ge=0.0, description="Periphery wages Wp.")
    extraction_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Alpha.")
    consciousness: float = Field(default=0.0, ge=0.0, le=1.0, description="Psi_p.")


# ===========================================================================
# SurplusDistributionDialectic (V3 Ch9-10)
# ===========================================================================


class SurplusDistributionDialectic(Dialectic[SurplusDistributionPole, EmptyPole]):
    """Surplus Value Distribution — s = p + i + r + t.

    Named "Distribution" rather than "Transformation" to distinguish this
    from the value → price *transformation problem* (V3 Ch9-10), which is
    out of scope (spec 024, Assumptions). This dialectic models how total
    surplus decomposes into competing revenue claims.

    Pole A stores the s = p + i + r + t decomposition. Weight tracks the
    share of surplus retained by industrial capital (enterprise profit)
    versus claims by money-capital (interest), landed capital (rent),
    and the state (taxes).

    Weight semantics:
        < 0: Enterprise profit dominates (healthy accumulation).
        > 0: Claimants dominate (profit squeeze / debt spiral).

    Motion law:
        Reads upstream interest rate changes and recomputes the distribution.
        Weight shifts toward +1 as claims crowd out enterprise profit.

    Sublation:
        When ``claims_exceed_surplus`` is True,
        sublates to :class:`DebtSpiralCrisisDialectic`.
    """

    type_tag: str = "SurplusDistributionDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> SurplusDistributionDialectic:
        """Motion law T for surplus value distribution.

        Args:
            inputs: Upstream outputs. Looks for own id's entry with
                    ``interest_rate_increase`` (float).
            world: Read-only world context.

        Returns:
            New SurplusDistributionDialectic with updated weight and poles.
        """
        own = inputs.upstream.get(self.id, {})
        interest_shift = float(own.get("interest_rate_increase", 0.0))

        new_interest = self.pole_a.interest_payments * (1.0 + interest_shift)
        new_pole_a = self.pole_a.model_copy(update={"interest_payments": max(0.0, new_interest)})

        # Weight = how much of surplus goes to claims vs enterprise profit
        if new_pole_a.total_surplus > 0:
            claims_share = (
                new_pole_a.interest_payments + new_pole_a.ground_rent + new_pole_a.taxes
            ) / new_pole_a.total_surplus
            new_weight = max(-1.0, min(1.0, (claims_share * 2.0) - 1.0))
        else:
            new_weight = 0.0

        return self.model_copy(
            update={
                "pole_a": new_pole_a,
                "weight": new_weight,
                "tick_updated": world.tick,
            }
        )

    def sublate(self) -> DebtSpiralCrisisDialectic | None:
        """Sublate to debt spiral when claims exceed surplus (FR-016).

        Returns:
            DebtSpiralCrisisDialectic if claims exceed surplus, else None.
        """
        if self.pole_a.claims_exceed_surplus:
            return DebtSpiralCrisisDialectic(
                pole_a=EmptyPole(),
                pole_b=EmptyPole(),
                weight=0.0,
                parent_id=self.id,
                tick_created=self.tick_updated,
                tick_updated=self.tick_updated,
            )
        return None

    def observe(self) -> dict[str, Any]:
        """Project surplus distribution state.

        Returns:
            Observation dict with s, p, i, r, t components.
        """
        obs = super().observe()
        obs.update(
            {
                "total_surplus": self.pole_a.total_surplus,
                "profit_of_enterprise": self.pole_a.profit_of_enterprise,
                "interest_payments": self.pole_a.interest_payments,
                "ground_rent": self.pole_a.ground_rent,
                "taxes": self.pole_a.taxes,
                "claims_exceed_surplus": self.pole_a.claims_exceed_surplus,
            }
        )
        return obs

    def invariants(self) -> list[str]:
        """Verify accounting identity: s = p + i + r + t.

        Returns:
            List of violation descriptions.
        """
        violations = super().invariants()
        reconstructed = (
            self.pole_a.profit_of_enterprise
            + self.pole_a.interest_payments
            + self.pole_a.ground_rent
            + self.pole_a.taxes
        )
        if abs(reconstructed - self.pole_a.total_surplus) > 1e-6:
            violations.append(
                f"SurplusDistributionDialectic {self.id}: "
                f"accounting identity violated: "
                f"p+i+r+t={reconstructed} != s={self.pole_a.total_surplus}"
            )
        return violations


# ===========================================================================
# TRPFDialectic (V3 Ch13-15)
# ===========================================================================


class TRPFDialectic(Dialectic[ProfitRateState, CounterTendencyStrength]):
    """Tendency of the Rate of Profit to Fall ↔ Counteracting Tendencies.

    Pole A holds the tendency (profit rate trajectory). Pole B holds the
    counter-tendency vector from ``economics.counter_tendencies``.

    Weight semantics:
        < 0: TRPF dominating (profit rate falling, counter-tendencies weak).
        > 0: Counter-tendencies dominating (profit rate sustained).

    Motion law:
        Reads upstream OCC and exploitation rate changes, delegates to
        ``CounterTendencyStrength.net_counter_tendency`` for weight.

    No sublation: TRPF is a structural tendency, not an event.
    """

    type_tag: str = "TRPFDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> TRPFDialectic:
        """Motion law T for TRPF dynamics.

        Args:
            inputs: Upstream outputs. Looks for ``occ``, ``exploitation_rate``.
            world: Read-only world context.

        Returns:
            New TRPFDialectic with updated weight and poles.
        """
        own = inputs.upstream.get(self.id, {})
        new_occ = float(own.get("occ", self.pole_a.organic_composition))
        new_exploitation = float(own.get("exploitation_rate", 0.0))

        # Simple structural TRPF: as OCC rises, profit rate tends to fall
        # r = s/v / (c/v + 1) = exploitation_rate / (occ + 1)
        if new_occ + 1.0 > 0:
            implied_profit_rate = new_exploitation / (new_occ + 1.0)
        else:
            implied_profit_rate = self.pole_a.profit_rate

        new_trend = implied_profit_rate - self.pole_a.profit_rate

        new_pole_a = ProfitRateState(
            profit_rate=implied_profit_rate,
            profit_rate_trend=new_trend,
            organic_composition=new_occ,
        )

        # Weight = net counter-tendency mapped to [-1, 1]
        net_ct = self.pole_b.net_counter_tendency
        new_weight = max(-1.0, min(1.0, net_ct))

        return self.model_copy(
            update={
                "pole_a": new_pole_a,
                "weight": new_weight,
                "tick_updated": world.tick,
            }
        )

    def observe(self) -> dict[str, Any]:
        """Project TRPF state for downstream consumers.

        Returns:
            Observation dict with profit rate, OCC, net counter-tendency.
        """
        obs = super().observe()
        obs.update(
            {
                "profit_rate": self.pole_a.profit_rate,
                "profit_rate_trend": self.pole_a.profit_rate_trend,
                "organic_composition": self.pole_a.organic_composition,
                "net_counter_tendency": self.pole_b.net_counter_tendency,
            }
        )
        return obs


# ===========================================================================
# CreditDialectic (V3 Ch21-33)
# ===========================================================================


class CreditDialectic(Dialectic[CreditPole, FictitiousCapitalStock]):
    """Real Capital ↔ Fictitious Capital.

    Pole A holds the real capital stock and industrial profit rate.
    Pole B holds the accumulated fictitious capital claims via the
    ``FictitiousCapitalStock`` from ``economics.credit.types``.

    Weight semantics:
        < 0: Real capital dominates (healthy production).
        > 0: Fictitious capital dominates (financialization).

    Motion law:
        Reads upstream credit growth and default rates.
        Weight tracks the financialization index mapped to [-1, 1].

    Sublation:
        When financialization index exceeds ``FINANCIALIZATION_BUBBLE`` (3.5),
        sublates to :class:`FinancialCrisisDialectic`.
    """

    type_tag: str = "CreditDialectic"

    def _financialization_index(self) -> float:
        """Compute financialization index = total_claims / gdp."""
        return self.pole_b.ratio_to_real(self.pole_a.gdp)

    def step(self, inputs: TickInputs, world: WorldView) -> CreditDialectic:
        """Motion law T for credit dynamics.

        Args:
            inputs: Upstream outputs. Looks for ``credit_growth``, ``default_rate``.
            world: Read-only world context.

        Returns:
            New CreditDialectic with updated fictitious capital and weight.
        """
        own = inputs.upstream.get(self.id, {})
        credit_growth = float(own.get("credit_growth", 0.0))

        # Fictitious capital grows with credit expansion
        growth_factor = 1.0 + credit_growth
        new_fict = self.pole_b.model_copy(
            update={
                "government_debt": self.pole_b.government_debt * growth_factor,
                "corporate_equity": self.pole_b.corporate_equity * growth_factor,
                "corporate_debt": self.pole_b.corporate_debt * growth_factor,
                "household_debt": self.pole_b.household_debt * growth_factor,
            }
        )

        # Weight = financialization index normalized to [-1, 1]
        # Map: ratio 0 → -1, ratio BUBBLE_THRESHOLD → 0, ratio 2*BUBBLE → +1
        fin_index = new_fict.ratio_to_real(self.pole_a.gdp)
        normalized = (fin_index / FINANCIALIZATION_BUBBLE) - 1.0
        new_weight = max(-1.0, min(1.0, normalized))

        return self.model_copy(
            update={
                "pole_b": new_fict,
                "weight": new_weight,
                "tick_updated": world.tick,
            }
        )

    def sublate(self) -> FinancialCrisisDialectic | None:
        """Sublate to financial crisis when overaccumulation exceeds threshold.

        Returns:
            FinancialCrisisDialectic if financialization > BUBBLE threshold.
        """
        if self._financialization_index() > FINANCIALIZATION_BUBBLE:
            return FinancialCrisisDialectic(
                pole_a=EmptyPole(),
                pole_b=EmptyPole(),
                weight=0.0,
                parent_id=self.id,
                tick_created=self.tick_updated,
                tick_updated=self.tick_updated,
            )
        return None

    def observe(self) -> dict[str, Any]:
        """Project credit system state.

        Returns:
            Observation dict with financialization index, total claims, profit rate.
        """
        obs = super().observe()
        obs.update(
            {
                "financialization_index": self._financialization_index(),
                "total_claims": self.pole_b.total_claims,
                "total_real_capital": self.pole_a.total_real_capital,
                "profit_rate": self.pole_a.profit_rate,
                "gdp": self.pole_a.gdp,
            }
        )
        return obs


# ===========================================================================
# RentDialectic (V3 Ch37-47)
# ===========================================================================


class RentDialectic(Dialectic[RentPole, EmptyPole]):
    """Ground Rent extraction — Absolute ↔ Differential.

    Pole A holds the three-category rent decomposition (agricultural,
    resource, urban) from ``economics.rent.types``.

    Weight semantics:
        < 0: Rent is a minor claims category (small rentier share).
        > 0: Rent dominates surplus distribution (rentier economy).

    Motion law:
        Reads upstream ``total_surplus`` to compute rentier share.
        Weight = 2 * (rent_share) - 1, clamped to [-1, 1].
    """

    type_tag: str = "RentDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> RentDialectic:
        """Motion law T for rent dynamics.

        Args:
            inputs: Upstream outputs. Looks for ``total_surplus``.
            world: Read-only world context.

        Returns:
            New RentDialectic with updated weight.
        """
        own = inputs.upstream.get(self.id, {})
        total_surplus = float(own.get("total_surplus", 0.0))

        if total_surplus > 0:
            rentier_share = self.pole_a.total_rent / total_surplus
            new_weight = max(-1.0, min(1.0, (rentier_share * 2.0) - 1.0))
        else:
            new_weight = 0.0

        return self.model_copy(
            update={
                "weight": new_weight,
                "tick_updated": world.tick,
            }
        )

    def observe(self) -> dict[str, Any]:
        """Project rent extraction state.

        Returns:
            Observation dict with rent categories and total.
        """
        obs = super().observe()
        obs.update(
            {
                "total_rent": self.pole_a.total_rent,
                "agricultural_rent": self.pole_a.agricultural_rent,
                "resource_rent": self.pole_a.resource_rent,
                "urban_rent": self.pole_a.urban_rent,
            }
        )
        return obs

    def invariants(self) -> list[str]:
        """Verify rent components are non-negative.

        Returns:
            List of violation descriptions.
        """
        violations = super().invariants()
        if self.pole_a.total_rent < 0:
            violations.append(
                f"RentDialectic {self.id}: total rent is negative ({self.pole_a.total_rent})"
            )
        return violations


# ===========================================================================
# ImperialDialectic (V3 Ch14 §V + MLM-TW)
# ===========================================================================


class ImperialDialectic(Dialectic[CoreEconomy, PeripheryEconomy]):
    """Core ↔ Periphery — the Fundamental Theorem of MLM-TW.

    Pole A is the imperialist core. Pole B is the exploited periphery.
    Imperial Rent Phi = alpha * Wp * (1 - Psi_p).

    Weight semantics:
        < 0: Core extracts freely (labor aristocracy bribed, periphery suppressed).
        > 0: Periphery resists (decolonization, rising consciousness).

    Motion law:
        Delegates to ``formulas.fundamental_theorem.calculate_imperial_rent``
        and ``calculate_labor_aristocracy_ratio``. Weight derived from
        how far the labor aristocracy ratio Wc/Vc deviates from unity.

    Invariant:
        Imperial rent Phi >= 0 (core always extracts from periphery).
    """

    type_tag: str = "ImperialDialectic"

    def _compute_imperial_rent(self) -> float:
        """Compute Phi = alpha * Wp * (1 - Psi_p)."""
        return calculate_imperial_rent(
            alpha=self.pole_b.extraction_rate,
            periphery_wages=self.pole_b.periphery_wages,
            periphery_consciousness=self.pole_b.consciousness,
        )

    def _compute_lar(self) -> float:
        """Compute labor aristocracy ratio Wc/Vc."""
        return calculate_labor_aristocracy_ratio(
            core_wages=self.pole_a.core_wages,
            value_produced=self.pole_a.value_produced,
        )

    def step(self, inputs: TickInputs, world: WorldView) -> ImperialDialectic:
        """Motion law T for imperial dynamics.

        Args:
            inputs: Upstream outputs. Looks for ``extraction_boost``.
            world: Read-only world context.

        Returns:
            New ImperialDialectic with updated extraction and weight.
        """
        own = inputs.upstream.get(self.id, {})
        extraction_boost = float(own.get("extraction_boost", 0.0))

        new_extraction = min(1.0, self.pole_b.extraction_rate + extraction_boost)
        new_periphery = self.pole_b.model_copy(update={"extraction_rate": new_extraction})

        # Weight = deviation of LAR from 1.0
        # LAR > 1 → core bribed → weight < 0 (core dominates)
        # LAR < 1 → core exploited → weight > 0 (periphery resisting)
        lar = calculate_labor_aristocracy_ratio(
            core_wages=self.pole_a.core_wages,
            value_produced=self.pole_a.value_produced,
        )
        weight_shift = 1.0 - lar  # Positive when LAR < 1
        new_weight = max(-1.0, min(1.0, weight_shift))

        return self.model_copy(
            update={
                "pole_b": new_periphery,
                "weight": new_weight,
                "tick_updated": world.tick,
            }
        )

    def observe(self) -> dict[str, Any]:
        """Project imperial rent state.

        Returns:
            Observation dict with Phi, LAR, extraction parameters.
        """
        obs = super().observe()
        obs.update(
            {
                "imperial_rent_phi": self._compute_imperial_rent(),
                "labor_aristocracy_ratio": self._compute_lar(),
                "core_wages": self.pole_a.core_wages,
                "value_produced": self.pole_a.value_produced,
                "extraction_rate": self.pole_b.extraction_rate,
                "periphery_consciousness": self.pole_b.consciousness,
            }
        )
        return obs

    def invariants(self) -> list[str]:
        """Verify imperial rent Phi >= 0.

        Returns:
            List of violation descriptions.
        """
        violations = super().invariants()
        phi = self._compute_imperial_rent()
        if phi < 0:
            violations.append(f"ImperialDialectic {self.id}: imperial rent Phi is negative ({phi})")
        return violations


# ===========================================================================
# Crisis Sublation Types
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
            inputs: Upstream outputs (currently unused).
            world: Read-only world context.

        Returns:
            Updated crisis dialectic with new tick.
        """
        return self.model_copy(update={"tick_updated": world.tick})


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
            inputs: Upstream outputs (currently unused).
            world: Read-only world context.

        Returns:
            Updated crisis dialectic with new tick.
        """
        return self.model_copy(update={"tick_updated": world.tick})


__all__ = [
    "CoreEconomy",
    "CreditDialectic",
    "CreditPole",
    "DebtSpiralCrisisDialectic",
    "SurplusDistributionDialectic",
    "SurplusDistributionPole",
    "FinancialCrisisDialectic",
    "ImperialDialectic",
    "PeripheryEconomy",
    "ProfitRateState",
    "RentDialectic",
    "RentPole",
    "TRPFDialectic",
]
