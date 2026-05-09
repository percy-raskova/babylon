"""Tests for SC-002 Measurability: Labor Aristocracy share validation.

Feature: 013-melt-basket-visibility
Task: T051 [CHK046]
Revision: 2026-02-02 (wealth-based classification)

Purpose: Validate SC-002 (Labor Aristocracy share) using both:
1. Wealth-based classification (primary): LA = 40% by definition (50th-90th percentile)
2. Income-based classification (deprecated): LA share 30-50% for backward compatibility

Theoretical Background (2026-02-02 revision):
    Class position is now determined by wealth percentile (stock), NOT income (flow).
    - LA = 50th-90th percentile = 40% of population by DEFINITION
    - This resolves the 30-50% vs 50-70% debate without parameter tuning
    - γ_basket stays empirically grounded (0.68)

    The income-based tests are retained for backward compatibility but
    represent extraction rate (Φ_hour), not class position.

Key Values (2022):
- Wealth-based: LA = 40% (50th-90th percentile of wealth)
- Income-based (deprecated): LA = 30-50% (W > τ_effective)
- τ ≈ $65/hour (from BEA NIPA GDP / QCEW employment × 2080)
- γ_basket = 0.68 (MVP Hickel et al. methodology)
- τ_effective ≈ $44/hour (imperial rent break-even, NOT class threshold)

Data Sources:
- Wealth: Fed SCF (Survey of Consumer Finances)
- Income: BLS QCEW (Quarterly Census of Employment and Wages)
"""

from __future__ import annotations

import pytest

from babylon.economics.melt import (
    ClassPosition,
    NationalParameters,
)
from babylon.economics.melt.class_position import DefaultClassPositionClassifier


class TestSC002WealthBased:
    """Test SC-002 (revised): LA share = 40% by definition (wealth-based).

    With the wealth-based model, LA = 50th-90th percentile wealth.
    This is a definitional fact (90 - 50 = 40 percentage points),
    not an empirical measurement.

    This resolves the 30-50% vs 50-70% debate without parameter tuning.
    """

    @pytest.fixture
    def classifier(self) -> DefaultClassPositionClassifier:
        """Provide class position classifier."""
        return DefaultClassPositionClassifier()

    def test_la_share_is_40_percent_by_definition(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """SC-002 (wealth-based): LA = 40% by definition.

        LA = 50th-90th percentile = 40 percentage points.
        This is definitional, not empirically validated.
        """
        # Simulate uniform wealth distribution (percentiles 0-99)
        percentiles = [float(p) for p in range(100)]

        shares = classifier.classify_wealth_distribution(percentiles)

        # LA = exactly 40% (50, 51, ..., 89 = 40 values out of 100)
        assert abs(shares[ClassPosition.LABOR_ARISTOCRACY] - 0.40) < 1e-10, (
            f"LA share {shares[ClassPosition.LABOR_ARISTOCRACY]:.1%} != 40%. "
            "This is definitional (50th-90th percentile)."
        )

    def test_full_class_distribution_by_definition(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Test all class shares match definitional percentile ranges."""
        # Uniform wealth distribution
        percentiles = [float(p) for p in range(100)]
        # All employed for simplicity
        employment = [True] * 100

        shares = classifier.classify_wealth_distribution(percentiles, employment)

        # Bourgeoisie: 99 only = 1%
        assert abs(shares[ClassPosition.BOURGEOISIE] - 0.01) < 1e-10

        # Petit Bourgeoisie: 90-98 = 9%
        assert abs(shares[ClassPosition.PETIT_BOURGEOISIE] - 0.09) < 1e-10

        # Labor Aristocracy: 50-89 = 40%
        assert abs(shares[ClassPosition.LABOR_ARISTOCRACY] - 0.40) < 1e-10

        # Proletariat: 0-49, all employed = 50%
        assert abs(shares[ClassPosition.PROLETARIAT] - 0.50) < 1e-10

        # Lumpenproletariat: none in this simulation
        assert abs(shares[ClassPosition.LUMPENPROLETARIAT] - 0.00) < 1e-10

    def test_privileged_classes_near_majority(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """LA + Petit Bourgeoisie = 49% (near majority).

        This captures the "bought off" segment of the population:
        - LA (40%) + PB (9%) = 49%
        - With Bourgeoisie (1%) = 50% system beneficiaries
        """
        percentiles = [float(p) for p in range(100)]
        shares = classifier.classify_wealth_distribution(percentiles)

        privileged = (
            shares[ClassPosition.LABOR_ARISTOCRACY] + shares[ClassPosition.PETIT_BOURGEOISIE]
        )

        # LA + PB = 49%
        assert abs(privileged - 0.49) < 1e-10

        # Full beneficiary class (incl. Bourgeoisie) = 50%
        full_privileged = privileged + shares[ClassPosition.BOURGEOISIE]
        assert abs(full_privileged - 0.50) < 1e-10


class TestSC002IncomeBased:
    """Test SC-002 (deprecated): Income-based LA share 30-50%.

    These tests validate the OLD income-based classification
    for backward compatibility. This model is deprecated.

    Note: Income-based classification measures extraction rate (Φ_hour),
    NOT class position. See TestSC002WealthBased for the canonical test.
    """

    @pytest.fixture
    def params_2022(self) -> NationalParameters:
        """2022 parameters for income-based classification.

        Note: These parameters are used for imperial rent calculation
        and backward-compatible income classification, NOT class position.
        """
        return NationalParameters(
            year=2022,
            tau=65.0,
            alpha=0.25,
            gamma_import=0.35,
            gamma_basket=0.68,
            tau_effective=44.2,  # Imperial rent break-even
            v_reproduction=12.0,
            estimated=True,
        )

    @pytest.fixture
    def classifier(self) -> DefaultClassPositionClassifier:
        """Provide class position classifier."""
        return DefaultClassPositionClassifier()

    @pytest.fixture
    def simulated_qcew_wage_distribution(self) -> list[float]:
        """Simulated 2022 QCEW national wage distribution."""
        return [
            # Bottom 10%: $8-14/hour
            8.0,
            9.0,
            10.0,
            10.5,
            11.0,
            11.5,
            12.0,
            12.5,
            13.0,
            14.0,
            # 10-25%: $14-19/hour
            14.5,
            15.0,
            15.5,
            16.0,
            16.5,
            17.0,
            17.5,
            18.0,
            18.5,
            19.0,
            19.0,
            19.0,
            19.5,
            19.5,
            19.5,
            # 25-50%: $19-28/hour
            20.0,
            20.5,
            21.0,
            21.5,
            22.0,
            22.5,
            23.0,
            23.5,
            24.0,
            24.5,
            25.0,
            25.5,
            26.0,
            26.5,
            27.0,
            27.0,
            27.5,
            27.5,
            28.0,
            28.0,
            28.0,
            28.0,
            28.5,
            28.5,
            29.0,
            # 50-65%: $29-37/hour
            29.5,
            30.0,
            30.5,
            31.0,
            32.0,
            33.0,
            34.0,
            35.0,
            36.0,
            37.0,
            37.5,
            38.0,
            38.5,
            39.0,
            40.0,
            # 65-75%: $40-50/hour
            41.0,
            42.0,
            43.0,
            44.0,
            45.0,
            46.0,
            47.0,
            48.0,
            49.0,
            50.0,
            # 75-90%: $50-85/hour
            52.0,
            54.0,
            56.0,
            58.0,
            60.0,
            62.0,
            65.0,
            70.0,
            75.0,
            80.0,
            82.0,
            84.0,
            86.0,
            88.0,
            90.0,
            # Top 10%: $90-150/hour
            92.0,
            95.0,
            100.0,
            105.0,
            110.0,
            115.0,
            120.0,
            130.0,
            140.0,
            150.0,
        ]

    def test_income_based_la_share_in_30_50_range(
        self,
        classifier: DefaultClassPositionClassifier,
        params_2022: NationalParameters,
        simulated_qcew_wage_distribution: list[float],
    ) -> None:
        """DEPRECATED: Income-based LA share should be 30-50%.

        This test validates backward compatibility with the old model.
        For canonical class position testing, see TestSC002WealthBased.

        The 30-50% range represents workers with W > τ_effective,
        meaning they have positive Φ_hour (extraction through consumption).
        """
        shares = classifier.classify_distribution(simulated_qcew_wage_distribution, params_2022)

        la_share = shares[ClassPosition.LABOR_ARISTOCRACY]

        # Backward compat: 30-50% income-based LA
        assert 0.30 <= la_share <= 0.50, (
            f"Income-based LA share {la_share:.1%} outside 30-50% range. "
            "Note: This is DEPRECATED. Use wealth-based classification."
        )

    def test_class_distribution_sums_to_one(
        self,
        classifier: DefaultClassPositionClassifier,
        params_2022: NationalParameters,
        simulated_qcew_wage_distribution: list[float],
    ) -> None:
        """Class shares must sum to 1.0 (100%)."""
        shares = classifier.classify_distribution(simulated_qcew_wage_distribution, params_2022)

        total = sum(shares.values())
        assert abs(total - 1.0) < 1e-9, f"Shares sum to {total}, expected 1.0"

    def test_proletariat_is_majority_income_based(
        self,
        classifier: DefaultClassPositionClassifier,
        params_2022: NationalParameters,
        simulated_qcew_wage_distribution: list[float],
    ) -> None:
        """In income-based model, proletariat is largest class."""
        shares = classifier.classify_distribution(simulated_qcew_wage_distribution, params_2022)

        proletariat_share = shares[ClassPosition.PROLETARIAT]

        # Proletariat (τ_effective >= W > V_reproduction) should be majority
        assert 0.35 <= proletariat_share <= 0.65, (
            f"Proletariat share {proletariat_share:.1%} outside 35-65% range"
        )

    def test_lumpen_share_is_minority(
        self,
        classifier: DefaultClassPositionClassifier,
        params_2022: NationalParameters,
        simulated_qcew_wage_distribution: list[float],
    ) -> None:
        """Lumpenproletariat (was Subproletariat) ~10%."""
        shares = classifier.classify_distribution(simulated_qcew_wage_distribution, params_2022)

        lumpen_share = shares[ClassPosition.LUMPENPROLETARIAT]

        # Lumpen (W <= V_reproduction) expected ~10%
        assert 0.05 <= lumpen_share <= 0.20, f"Lumpen share {lumpen_share:.1%} outside 5-20% range"

    def test_tau_effective_threshold_is_reasonable(
        self,
        params_2022: NationalParameters,
    ) -> None:
        """τ_effective should be well above median wage (~$28/hour).

        Note: τ_effective is the imperial rent break-even point,
        NOT the class threshold (which is now wealth-based).
        """
        median_wage = 28.0

        # τ_effective should be significantly above median
        assert params_2022.tau_effective > median_wage * 1.3, (
            f"τ_effective=${params_2022.tau_effective:.2f} too close to median"
        )

        # But not absurdly high
        assert params_2022.tau_effective < median_wage * 2.5, (
            f"τ_effective=${params_2022.tau_effective:.2f} too high"
        )
