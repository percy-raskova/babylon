"""Unit tests for SurplusValueDistribution model.

Feature: 024-capital-volume-iii (US1, FR-001)
TDD Red Phase: Tests define expected behavior for surplus value decomposition.

Accounting identity: s = p + i + r + t
where p (profit of enterprise) is the RESIDUAL: p = s - i - r - t.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

from babylon.domain.economics.distribution.types import SurplusValueDistribution


@pytest.mark.unit
class TestSurplusValueDistributionFrozen:
    """SurplusValueDistribution must be immutable (frozen Pydantic model)."""

    def test_frozen_model_rejects_mutation(self) -> None:
        """Attempting to mutate a field raises ValidationError."""
        dist = SurplusValueDistribution(
            fips_code="26163",
            year=2020,
            total_surplus_produced=10_000.0,
            interest_payments=2_000.0,
            ground_rent=1_500.0,
            taxes_on_surplus=1_000.0,
        )
        with pytest.raises(ValidationError):
            dist.total_surplus_produced = 99_999.0  # type: ignore[misc]


@pytest.mark.unit
class TestProfitOfEnterprise:
    """Profit of enterprise is the residual: p = s - i - r - t."""

    def test_profit_is_residual(self) -> None:
        """p = 10000 - 2000 - 1500 - 1000 = 5500."""
        dist = SurplusValueDistribution(
            fips_code="26163",
            year=2020,
            total_surplus_produced=10_000.0,
            interest_payments=2_000.0,
            ground_rent=1_500.0,
            taxes_on_surplus=1_000.0,
        )
        assert dist.profit_of_enterprise == pytest.approx(5_500.0)

    def test_profit_zero_when_claims_equal_surplus(self) -> None:
        """When i + r + t = s, profit is exactly zero."""
        dist = SurplusValueDistribution(
            fips_code="26163",
            year=2020,
            total_surplus_produced=5_000.0,
            interest_payments=2_000.0,
            ground_rent=2_000.0,
            taxes_on_surplus=1_000.0,
        )
        assert dist.profit_of_enterprise == pytest.approx(0.0)


@pytest.mark.unit
class TestDistributionComplete:
    """Verify accounting identity s = p + i + r + t holds within epsilon."""

    def test_distribution_complete_normal_case(self) -> None:
        """Normal distribution satisfies accounting identity."""
        dist = SurplusValueDistribution(
            fips_code="26163",
            year=2020,
            total_surplus_produced=10_000.0,
            interest_payments=2_000.0,
            ground_rent=1_500.0,
            taxes_on_surplus=1_000.0,
        )
        assert dist.distribution_complete is True

    def test_distribution_complete_zero_surplus(self) -> None:
        """Zero surplus also satisfies identity: 0 = 0 + 0 + 0 + 0."""
        dist = SurplusValueDistribution(
            fips_code="26163",
            year=2020,
            total_surplus_produced=0.0,
            interest_payments=0.0,
            ground_rent=0.0,
            taxes_on_surplus=0.0,
        )
        assert dist.distribution_complete is True


@pytest.mark.unit
class TestFinancializationShare:
    """Interest as share of total surplus."""

    def test_financialization_share_calculation(self) -> None:
        """interest / total_surplus = 2000 / 10000 = 0.2."""
        dist = SurplusValueDistribution(
            fips_code="26163",
            year=2020,
            total_surplus_produced=10_000.0,
            interest_payments=2_000.0,
            ground_rent=1_500.0,
            taxes_on_surplus=1_000.0,
        )
        assert dist.financialization_share == pytest.approx(0.2)

    def test_financialization_share_zero_surplus_returns_zero(self) -> None:
        """Division by zero protection: returns 0.0 when surplus is zero."""
        dist = SurplusValueDistribution(
            fips_code="26163",
            year=2020,
            total_surplus_produced=0.0,
            interest_payments=0.0,
            ground_rent=0.0,
            taxes_on_surplus=0.0,
        )
        assert dist.financialization_share == 0.0


@pytest.mark.unit
class TestRentierShare:
    """Rent as share of total surplus."""

    def test_rentier_share_calculation(self) -> None:
        """rent / total_surplus = 1500 / 10000 = 0.15."""
        dist = SurplusValueDistribution(
            fips_code="26163",
            year=2020,
            total_surplus_produced=10_000.0,
            interest_payments=2_000.0,
            ground_rent=1_500.0,
            taxes_on_surplus=1_000.0,
        )
        assert dist.rentier_share == pytest.approx(0.15)

    def test_rentier_share_zero_surplus_returns_zero(self) -> None:
        """Division by zero protection: returns 0.0 when surplus is zero."""
        dist = SurplusValueDistribution(
            fips_code="26163",
            year=2020,
            total_surplus_produced=0.0,
            interest_payments=0.0,
            ground_rent=0.0,
            taxes_on_surplus=0.0,
        )
        assert dist.rentier_share == 0.0


@pytest.mark.unit
class TestClaimsExceedSurplus:
    """Detect when competing claims exceed total surplus."""

    def test_claims_do_not_exceed_surplus(self) -> None:
        """Normal case: i + r + t < s."""
        dist = SurplusValueDistribution(
            fips_code="26163",
            year=2020,
            total_surplus_produced=10_000.0,
            interest_payments=2_000.0,
            ground_rent=1_500.0,
            taxes_on_surplus=1_000.0,
        )
        assert dist.claims_exceed_surplus is False

    def test_claims_exceed_surplus_negative_profit(self) -> None:
        """When i + r + t > s, profit is negative and flag is True."""
        dist = SurplusValueDistribution(
            fips_code="26163",
            year=2020,
            total_surplus_produced=3_000.0,
            interest_payments=2_000.0,
            ground_rent=1_500.0,
            taxes_on_surplus=1_000.0,
        )
        # p = 3000 - 2000 - 1500 - 1000 = -1500
        assert dist.profit_of_enterprise == pytest.approx(-1_500.0)
        assert dist.claims_exceed_surplus is True

    def test_rent_alone_exceeds_surplus(self) -> None:
        """Rent alone can exceed surplus (hypergentrify scenario)."""
        dist = SurplusValueDistribution(
            fips_code="26163",
            year=2020,
            total_surplus_produced=1_000.0,
            interest_payments=0.0,
            ground_rent=5_000.0,
            taxes_on_surplus=0.0,
        )
        # p = 1000 - 0 - 5000 - 0 = -4000
        assert dist.profit_of_enterprise == pytest.approx(-4_000.0)
        assert dist.claims_exceed_surplus is True


@pytest.mark.unit
class TestZeroSurplus:
    """Zero surplus edge case: all components must be zero."""

    def test_zero_surplus_all_components_zero(self) -> None:
        """When total surplus is zero, all claims are zero."""
        dist = SurplusValueDistribution(
            fips_code="26163",
            year=2020,
            total_surplus_produced=0.0,
            interest_payments=0.0,
            ground_rent=0.0,
            taxes_on_surplus=0.0,
        )
        assert dist.profit_of_enterprise == pytest.approx(0.0)
        assert dist.financialization_share == 0.0
        assert dist.rentier_share == 0.0
        assert dist.claims_exceed_surplus is False
        assert dist.distribution_complete is True


@pytest.mark.unit
class TestFieldValidation:
    """Pydantic field constraints are enforced."""

    def test_fips_code_too_short_rejected(self) -> None:
        """FIPS code must be exactly 5 characters."""
        with pytest.raises(ValidationError):
            SurplusValueDistribution(
                fips_code="261",
                year=2020,
                total_surplus_produced=1_000.0,
                interest_payments=0.0,
                ground_rent=0.0,
                taxes_on_surplus=0.0,
            )

    def test_negative_surplus_rejected(self) -> None:
        """Total surplus produced cannot be negative."""
        with pytest.raises(ValidationError):
            SurplusValueDistribution(
                fips_code="26163",
                year=2020,
                total_surplus_produced=-1_000.0,
                interest_payments=0.0,
                ground_rent=0.0,
                taxes_on_surplus=0.0,
            )

    def test_year_out_of_range_rejected(self) -> None:
        """Year must be in [2007, 2040]."""
        with pytest.raises(ValidationError):
            SurplusValueDistribution(
                fips_code="26163",
                year=1999,
                total_surplus_produced=1_000.0,
                interest_payments=0.0,
                ground_rent=0.0,
                taxes_on_surplus=0.0,
            )


@pytest.mark.unit
class TestThresholdAccessorsAreGameDefinesBacked:
    """Honesty sweep (U2): the DEBT_SPIRAL_THRESHOLD/DISTRIBUTION_EPSILON
    Finals are gone; debt_spiral_threshold()/distribution_epsilon() read from
    GameDefines.capital_vol3 at call time, not at import time."""

    def test_debt_spiral_threshold_matches_capital_vol3(self) -> None:
        from babylon.config.defines import GameDefines
        from babylon.domain.economics.distribution.types import debt_spiral_threshold

        assert (
            debt_spiral_threshold() == GameDefines.load_default().capital_vol3.debt_spiral_threshold
        )

    def test_distribution_epsilon_matches_capital_vol3(self) -> None:
        from babylon.config.defines import GameDefines
        from babylon.domain.economics.distribution.types import distribution_epsilon

        assert (
            distribution_epsilon() == GameDefines.load_default().capital_vol3.distribution_epsilon
        )

    def test_explicit_defines_override_is_honoured(self) -> None:
        """A caller-supplied GameDefines wins over the process default — the
        behaviour the deleted module-level Finals made impossible."""
        from babylon.config.defines import GameDefines
        from babylon.domain.economics.distribution.types import (
            debt_spiral_threshold,
            distribution_epsilon,
        )

        base = GameDefines.load_default()
        overridden = base.model_copy(
            update={
                "capital_vol3": base.capital_vol3.model_copy(
                    update={"debt_spiral_threshold": 0.75, "distribution_epsilon": 1e-6}
                )
            }
        )
        assert debt_spiral_threshold(overridden) == pytest.approx(0.75)
        assert distribution_epsilon(overridden) == pytest.approx(1e-6)


@pytest.mark.unit
class TestProductionConsumesTheEpsilonAccessor:
    """The accessor is only useful if the SHIPPING code path calls it.

    Every other test here calls ``distribution_epsilon()`` directly, or
    compares the computed field against a value derived from that same call —
    both of which pass identically whether ``distribution_complete`` reads the
    accessor or hardcodes ``1e-9``. This drives an OVERRIDDEN ``defines.yaml``
    through the production computed field and asserts the verdict MOVES, which
    a hardcoded literal cannot do.
    """

    def test_distribution_complete_flips_when_the_yaml_tightens_epsilon(
        self, divergent_defines_yaml: Callable[..., Path]
    ) -> None:
        from babylon.domain.economics.distribution import types as distribution_types

        # Residual here is pure IEEE-754 representation error: p = s - i - r - t
        # then i + r + t + p re-associates the same doubles in a different
        # order. Deterministic, and ~5.55e-17 — comfortably inside the shipped
        # 1e-9 epsilon and comfortably outside a 1e-17 one.
        claim = SurplusValueDistribution(
            fips_code="26163",
            year=2020,
            total_surplus_produced=0.3,
            interest_payments=0.1,
            ground_rent=0.1,
            taxes_on_surplus=0.1,
        )
        assert claim.distribution_complete is True, "shipped epsilon should accept FP noise"

        divergent_defines_yaml(
            {"capital_vol3": {"distribution_epsilon": 1e-17}},
            distribution_types._default_defines,
        )
        assert claim.distribution_complete is False, (
            "distribution_complete ignored the tightened capital_vol3."
            "distribution_epsilon — it is reading a hardcoded literal, not the accessor"
        )
