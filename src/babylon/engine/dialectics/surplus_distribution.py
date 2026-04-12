"""SurplusDistributionDialectic — s = p + i + r + t (V3 Ch9-10).

Models how total surplus value decomposes into competing revenue claims:
profit of enterprise, interest, ground rent, and taxes.

See Also:
    :mod:`babylon.economics.distribution`: Surplus distribution calculators.
    :class:`babylon.engine.dialectics.crises.DebtSpiralCrisisDialectic`
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from babylon.engine.dialectics.base import Dialectic, EmptyPole, TickInputs, WorldView


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

    def sublate(self) -> Dialectic[Any, Any] | None:
        """Sublate to debt spiral when claims exceed surplus (FR-016).

        Returns:
            DebtSpiralCrisisDialectic if claims exceed surplus, else None.
        """
        from babylon.engine.dialectics.crises import DebtSpiralCrisisDialectic

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


__all__ = [
    "SurplusDistributionDialectic",
    "SurplusDistributionPole",
]
