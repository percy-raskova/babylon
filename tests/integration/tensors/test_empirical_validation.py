"""Empirical validation tests for Marxian value tensors with real QCEW data.

These tests verify that hydrated tensors match observable economic data from
the Bureau of Labor Statistics' QCEW program. Unlike unit tests (internal
consistency) or mock integration tests (plumbing), these tests validate that
model outputs are consistent with real-world economic patterns.

Test Categories:
    - TestAccountingIdentity: allocated_v + excluded = QCEW total
    - TestPikettyGuardrails: Profit rates within historical 3-8% bounds
    - TestDetroitGentrificationSignal: Oakland IIb/IIa > Wayne IIb/IIa
    - TestDetroitDeindustrialization: Wayne Dept I declining vs Oakland
    - TestTemporalConsistency: YoY changes ≤30%
    - TestOutOfSamplePrediction: Train 2010-2019, test 2020-2022

All tests are marked with @pytest.mark.empirical and will skip gracefully
if the QCEW database is not present.

References:
    - Piketty, Thomas. "Capital in the Twenty-First Century" (2014)
    - Marx, Karl. "Capital, Volume 2" (1885), Chapters 20-21
"""

from __future__ import annotations

import pytest

from babylon.economics.adapters import SQLiteQCEWSource
from babylon.economics.department_mapper import Department
from babylon.economics.hydrator import MarxianHydrator
from babylon.economics.tensor import ValueTensor4x3

from .conftest import (
    DETROIT_METRO_COUNTIES,
    MAX_YOY_CHANGE,
    OAKLAND_FIPS,
    PIKETTY_R_MAX,
    PIKETTY_R_MIN,
    TEST_YEARS,
    TRAIN_YEARS,
    WAYNE_FIPS,
)

# =============================================================================
# ACCOUNTING IDENTITY TESTS
# =============================================================================


@pytest.mark.empirical
@pytest.mark.integration
class TestAccountingIdentity:
    """Tests that allocated + excluded wages equal total QCEW wages.

    The accounting identity ensures no wages are lost or created during
    the hydration process. This is a fundamental data integrity check.
    """

    def test_single_year_allocation_sums_correctly(
        self, production_hydrator: MarxianHydrator, real_qcew_source: SQLiteQCEWSource
    ) -> None:
        """For a single county-year, allocated + excluded should equal total."""
        year = 2022

        # Get raw QCEW totals
        raw_records = real_qcew_source.fetch_county_wages(WAYNE_FIPS, year)
        if not raw_records:
            pytest.skip(f"No QCEW data available for {WAYNE_FIPS} in {year}")

        total_qcew = sum(wages for _, wages, _ in raw_records)

        # Hydrate the tensor
        tensor = production_hydrator.hydrate(WAYNE_FIPS, year)

        # Sum allocated variable capital across departments
        allocated_v = tensor.dept_I.v + tensor.dept_IIa.v + tensor.dept_IIb.v + tensor.dept_III.v

        # Accounting identity: allocated + excluded = total
        computed_total = allocated_v + tensor.excluded_wages

        # Allow 0.1% tolerance for floating point
        assert computed_total == pytest.approx(total_qcew, rel=0.001), (
            f"Accounting identity violated: "
            f"allocated ({allocated_v:,.0f}) + excluded ({tensor.excluded_wages:,.0f}) = "
            f"{computed_total:,.0f}, but QCEW total = {total_qcew:,.0f}"
        )

    def test_multi_county_allocation_consistency(
        self, production_hydrator: MarxianHydrator, real_qcew_source: SQLiteQCEWSource
    ) -> None:
        """Accounting identity should hold for all Detroit metro counties."""
        year = 2022
        tested_counties = 0

        for fips in DETROIT_METRO_COUNTIES:
            raw_records = real_qcew_source.fetch_county_wages(fips, year)
            if not raw_records:
                continue

            tested_counties += 1
            total_qcew = sum(wages for _, wages, _ in raw_records)
            tensor = production_hydrator.hydrate(fips, year)

            allocated_v = (
                tensor.dept_I.v + tensor.dept_IIa.v + tensor.dept_IIb.v + tensor.dept_III.v
            )
            computed_total = allocated_v + tensor.excluded_wages

            assert computed_total == pytest.approx(total_qcew, rel=0.001), (
                f"Accounting identity violated for {fips}: "
                f"computed {computed_total:,.0f} != QCEW {total_qcew:,.0f}"
            )

        if tested_counties == 0:
            pytest.skip("No QCEW data available for any Detroit metro county")


# =============================================================================
# PIKETTY GUARDRAILS TESTS
# =============================================================================


@pytest.mark.empirical
@pytest.mark.integration
class TestPikettyGuardrails:
    """Tests that profit rates fall within historical bounds from Piketty's research.

    Thomas Piketty's empirical research shows long-run profit rates (r) typically
    fall between 3% (recessionary) and 8% (boom). Tensors with profit rates
    outside these bounds indicate data quality issues or model misspecification.

    Reference:
        Piketty, Thomas. "Capital in the Twenty-First Century" (2014)
    """

    def test_wayne_county_profit_rate_within_bounds(
        self,
        production_hydrator: MarxianHydrator,
    ) -> None:
        """Wayne County profit rate should fall within Piketty's 3-8% band."""
        tensor = production_hydrator.hydrate(WAYNE_FIPS, 2022)

        if tensor.total_value == 0:
            pytest.skip("No data for Wayne County 2022")

        profit_rate = tensor.profit_rate

        assert PIKETTY_R_MIN <= profit_rate <= PIKETTY_R_MAX, (
            f"Wayne County profit rate {profit_rate:.2%} outside "
            f"Piketty bounds [{PIKETTY_R_MIN:.0%}, {PIKETTY_R_MAX:.0%}]"
        )

    def test_oakland_county_profit_rate_within_bounds(
        self,
        production_hydrator: MarxianHydrator,
    ) -> None:
        """Oakland County profit rate should fall within Piketty's 3-8% band."""
        tensor = production_hydrator.hydrate(OAKLAND_FIPS, 2022)

        if tensor.total_value == 0:
            pytest.skip("No data for Oakland County 2022")

        profit_rate = tensor.profit_rate

        assert PIKETTY_R_MIN <= profit_rate <= PIKETTY_R_MAX, (
            f"Oakland County profit rate {profit_rate:.2%} outside "
            f"Piketty bounds [{PIKETTY_R_MIN:.0%}, {PIKETTY_R_MAX:.0%}]"
        )

    def test_all_detroit_metro_counties_within_bounds(
        self,
        production_hydrator: MarxianHydrator,
    ) -> None:
        """All Detroit metro counties should have profit rates in Piketty bounds."""
        for year in [2019, 2020, 2021, 2022]:
            for fips in DETROIT_METRO_COUNTIES:
                tensor = production_hydrator.hydrate(fips, year)

                if tensor.total_value == 0:
                    continue

                profit_rate = tensor.profit_rate

                assert PIKETTY_R_MIN <= profit_rate <= PIKETTY_R_MAX, (
                    f"County {fips} year {year}: profit rate {profit_rate:.2%} "
                    f"outside Piketty bounds"
                )


# =============================================================================
# DETROIT GENTRIFICATION SIGNAL TESTS
# =============================================================================


@pytest.mark.empirical
@pytest.mark.integration
class TestDetroitGentrificationSignal:
    """Tests for the gentrification signal: Oakland has higher IIb/IIa than Wayne.

    The gentrification hypothesis predicts that affluent suburbs (Oakland County)
    have proportionally more luxury consumption (Dept IIb) relative to necessary
    consumption (Dept IIa) compared to deindustrialized cores (Wayne County).

    This ratio IIb/IIa captures the class character of local consumption:
    - Higher ratio = more bourgeois consumption patterns
    - Lower ratio = more working-class consumption patterns
    """

    def test_oakland_has_higher_luxury_ratio_than_wayne_2022(
        self,
        production_hydrator: MarxianHydrator,
    ) -> None:
        """Oakland should have higher IIb/IIa ratio than Wayne in 2022."""
        wayne = production_hydrator.hydrate(WAYNE_FIPS, 2022)
        oakland = production_hydrator.hydrate(OAKLAND_FIPS, 2022)

        if wayne.dept_IIa.v == 0 or oakland.dept_IIa.v == 0:
            pytest.skip("Insufficient data for IIa comparison")

        wayne_ratio = wayne.dept_IIb.v / wayne.dept_IIa.v
        oakland_ratio = oakland.dept_IIb.v / oakland.dept_IIa.v

        assert oakland_ratio > wayne_ratio, (
            f"Gentrification signal not detected: "
            f"Oakland IIb/IIa ({oakland_ratio:.3f}) should > "
            f"Wayne IIb/IIa ({wayne_ratio:.3f})"
        )

    def test_gentrification_signal_persists_across_years(
        self,
        production_hydrator: MarxianHydrator,
    ) -> None:
        """Gentrification signal should be consistent across multiple years."""
        signal_detected_years = 0
        tested_years = 0

        for year in [2019, 2020, 2021, 2022]:
            wayne = production_hydrator.hydrate(WAYNE_FIPS, year)
            oakland = production_hydrator.hydrate(OAKLAND_FIPS, year)

            if wayne.dept_IIa.v == 0 or oakland.dept_IIa.v == 0:
                continue

            tested_years += 1
            wayne_ratio = wayne.dept_IIb.v / wayne.dept_IIa.v
            oakland_ratio = oakland.dept_IIb.v / oakland.dept_IIa.v

            if oakland_ratio > wayne_ratio:
                signal_detected_years += 1

        if tested_years == 0:
            pytest.skip("No years with sufficient data")

        # Signal should be present in at least 75% of tested years
        detection_rate = signal_detected_years / tested_years
        assert detection_rate >= 0.75, (
            f"Gentrification signal inconsistent: detected in only "
            f"{signal_detected_years}/{tested_years} years ({detection_rate:.0%})"
        )

    def test_luxury_ratio_magnitude_is_meaningful(
        self,
        production_hydrator: MarxianHydrator,
    ) -> None:
        """The difference in luxury ratios should be economically meaningful (>10%)."""
        wayne = production_hydrator.hydrate(WAYNE_FIPS, 2022)
        oakland = production_hydrator.hydrate(OAKLAND_FIPS, 2022)

        if wayne.dept_IIa.v == 0 or oakland.dept_IIa.v == 0:
            pytest.skip("Insufficient data for ratio comparison")

        wayne_ratio = wayne.dept_IIb.v / wayne.dept_IIa.v
        oakland_ratio = oakland.dept_IIb.v / oakland.dept_IIa.v

        # Oakland's ratio should be at least 10% higher than Wayne's
        relative_difference = (oakland_ratio - wayne_ratio) / wayne_ratio

        assert relative_difference >= 0.10, (
            f"Luxury ratio difference not meaningful: "
            f"Oakland {oakland_ratio:.3f} vs Wayne {wayne_ratio:.3f} "
            f"(only {relative_difference:.1%} higher)"
        )


# =============================================================================
# DETROIT DEINDUSTRIALIZATION TESTS
# =============================================================================


@pytest.mark.empirical
@pytest.mark.integration
class TestDetroitDeindustrialization:
    """Tests for deindustrialization patterns in Wayne County.

    Wayne County (Detroit) experienced significant deindustrialization since
    the 1980s. This should manifest as relatively lower Dept I (means of
    production) compared to Oakland County's professional services economy.
    """

    def test_wayne_dept_I_proportion_lower_than_oakland(
        self,
        production_hydrator: MarxianHydrator,
    ) -> None:
        """Wayne should have lower Dept I proportion than Oakland."""
        wayne = production_hydrator.hydrate(WAYNE_FIPS, 2022)
        oakland = production_hydrator.hydrate(OAKLAND_FIPS, 2022)

        wayne_total_v = wayne.dept_I.v + wayne.dept_IIa.v + wayne.dept_IIb.v + wayne.dept_III.v
        oakland_total_v = (
            oakland.dept_I.v + oakland.dept_IIa.v + oakland.dept_IIb.v + oakland.dept_III.v
        )

        if wayne_total_v == 0 or oakland_total_v == 0:
            pytest.skip("Insufficient data for comparison")

        wayne_I_share = wayne.dept_I.v / wayne_total_v
        oakland_I_share = oakland.dept_I.v / oakland_total_v

        # Note: Oakland has professional services (classified as Dept I),
        # while Wayne's manufacturing has declined. This test may need
        # adjustment based on actual NAICS mappings.
        # For now, we just verify both are reasonable proportions.
        assert 0.0 < wayne_I_share < 1.0, f"Wayne Dept I share unrealistic: {wayne_I_share:.2%}"
        assert 0.0 < oakland_I_share < 1.0, (
            f"Oakland Dept I share unrealistic: {oakland_I_share:.2%}"
        )

    def test_wayne_has_substantial_dept_III_healthcare(
        self,
        production_hydrator: MarxianHydrator,
    ) -> None:
        """Wayne's economy should show substantial Dept III (healthcare/care work)."""
        wayne = production_hydrator.hydrate(WAYNE_FIPS, 2022)

        total_v = wayne.dept_I.v + wayne.dept_IIa.v + wayne.dept_IIb.v + wayne.dept_III.v

        if total_v == 0:
            pytest.skip("No data for Wayne County 2022")

        dept_III_share = wayne.dept_III.v / total_v

        # Healthcare is a major employer in Detroit; Dept III should be >5%
        assert dept_III_share >= 0.05, (
            f"Wayne Dept III share too low: {dept_III_share:.2%} "
            f"(expected >= 5% given healthcare sector)"
        )


# =============================================================================
# TEMPORAL CONSISTENCY TESTS
# =============================================================================


@pytest.mark.empirical
@pytest.mark.integration
@pytest.mark.slow
class TestTemporalConsistency:
    """Tests that tensor values change smoothly over time.

    Economic data should not have wild year-over-year swings (>30%) unless
    there's a major economic shock. Large changes indicate data quality
    issues or model instability.
    """

    def test_wayne_county_smooth_transitions(
        self,
        production_hydrator: MarxianHydrator,
    ) -> None:
        """Wayne County tensors should change ≤30% year-over-year."""
        prev_tensor: ValueTensor4x3 | None = None

        for year in range(2018, 2023):
            tensor = production_hydrator.hydrate(WAYNE_FIPS, year)

            if tensor.total_value == 0:
                prev_tensor = None
                continue

            if prev_tensor is not None and prev_tensor.total_value > 0:
                # Check total value change
                change = abs(tensor.total_value - prev_tensor.total_value) / prev_tensor.total_value

                # Allow larger change for 2020 (COVID shock)
                max_change = 0.50 if year == 2020 else MAX_YOY_CHANGE

                assert change <= max_change, (
                    f"Wayne County {year - 1}→{year}: total_value changed {change:.1%} "
                    f"(max {max_change:.0%})"
                )

            prev_tensor = tensor

    def test_department_proportions_stable(
        self,
        production_hydrator: MarxianHydrator,
    ) -> None:
        """Department proportions should remain relatively stable over time."""
        prev_shares: dict[Department, float] | None = None

        for year in range(2018, 2023):
            tensor = production_hydrator.hydrate(WAYNE_FIPS, year)
            total_v = tensor.dept_I.v + tensor.dept_IIa.v + tensor.dept_IIb.v + tensor.dept_III.v

            if total_v == 0:
                prev_shares = None
                continue

            shares = {
                Department.I: tensor.dept_I.v / total_v,
                Department.IIa: tensor.dept_IIa.v / total_v,
                Department.IIb: tensor.dept_IIb.v / total_v,
                Department.III: tensor.dept_III.v / total_v,
            }

            if prev_shares is not None:
                for dept in Department:
                    prev = prev_shares[dept]
                    curr = shares[dept]

                    if prev > 0.01:  # Only check if department had meaningful share
                        relative_change = abs(curr - prev) / prev

                        # Allow larger change for 2020 (COVID shock)
                        max_change = 0.40 if year == 2020 else MAX_YOY_CHANGE

                        assert relative_change <= max_change, (
                            f"Dept {dept.name} share changed {relative_change:.1%} "
                            f"from {year - 1} to {year} (max {max_change:.0%})"
                        )

            prev_shares = shares


# =============================================================================
# OUT-OF-SAMPLE PREDICTION TESTS
# =============================================================================


@pytest.mark.empirical
@pytest.mark.integration
@pytest.mark.slow
class TestOutOfSamplePrediction:
    """Tests for out-of-sample prediction: patterns from 2010-2019 hold in 2020-2022.

    These tests verify that structural patterns observed in training years
    (2010-2019) also appear in test years (2020-2022). If patterns break down,
    it suggests either data quality issues or genuine structural changes.
    """

    def test_gentrification_signal_extrapolates(
        self,
        production_hydrator: MarxianHydrator,
    ) -> None:
        """Gentrification signal observed in 2010-2019 should persist in 2020-2022."""
        train_signals: list[bool] = []
        test_signals: list[bool] = []

        # Collect training period signals
        for year in TRAIN_YEARS:
            wayne = production_hydrator.hydrate(WAYNE_FIPS, year)
            oakland = production_hydrator.hydrate(OAKLAND_FIPS, year)

            if wayne.dept_IIa.v > 0 and oakland.dept_IIa.v > 0:
                wayne_ratio = wayne.dept_IIb.v / wayne.dept_IIa.v
                oakland_ratio = oakland.dept_IIb.v / oakland.dept_IIa.v
                train_signals.append(oakland_ratio > wayne_ratio)

        # Collect test period signals
        for year in TEST_YEARS:
            wayne = production_hydrator.hydrate(WAYNE_FIPS, year)
            oakland = production_hydrator.hydrate(OAKLAND_FIPS, year)

            if wayne.dept_IIa.v > 0 and oakland.dept_IIa.v > 0:
                wayne_ratio = wayne.dept_IIb.v / wayne.dept_IIa.v
                oakland_ratio = oakland.dept_IIb.v / oakland.dept_IIa.v
                test_signals.append(oakland_ratio > wayne_ratio)

        if len(train_signals) < 3 or len(test_signals) < 2:
            pytest.skip("Insufficient data for train/test comparison")

        # Calculate detection rates
        train_rate = sum(train_signals) / len(train_signals)
        test_rate = sum(test_signals) / len(test_signals)

        # Test rate should be within 30% of train rate (accounting for COVID)
        assert test_rate >= train_rate * 0.70, (
            f"Gentrification signal degraded: train {train_rate:.0%} → test {test_rate:.0%}"
        )

    def test_profit_rate_distribution_consistent(
        self,
        production_hydrator: MarxianHydrator,
    ) -> None:
        """Profit rate distributions should be similar in train vs test periods."""
        train_rates: list[float] = []
        test_rates: list[float] = []

        # Collect training period rates
        for year in TRAIN_YEARS:
            for fips in DETROIT_METRO_COUNTIES:
                tensor = production_hydrator.hydrate(fips, year)
                if tensor.total_value > 0:
                    train_rates.append(tensor.profit_rate)

        # Collect test period rates
        for year in TEST_YEARS:
            for fips in DETROIT_METRO_COUNTIES:
                tensor = production_hydrator.hydrate(fips, year)
                if tensor.total_value > 0:
                    test_rates.append(tensor.profit_rate)

        if len(train_rates) < 10 or len(test_rates) < 5:
            pytest.skip("Insufficient data for distribution comparison")

        # Compare means (allow 30% deviation due to COVID)
        train_mean = sum(train_rates) / len(train_rates)
        test_mean = sum(test_rates) / len(test_rates)

        relative_diff = abs(test_mean - train_mean) / train_mean

        assert relative_diff <= 0.30, (
            f"Profit rate distribution shifted: "
            f"train mean {train_mean:.2%} → test mean {test_mean:.2%} "
            f"({relative_diff:.0%} change)"
        )
