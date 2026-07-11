"""Tests for crisis amplification logic.

Feature: 016-class-dynamics-engine
Task: T023
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.dynamics.crisis import DefaultCrisisAmplifier
from babylon.domain.economics.dynamics.types import TransitionRates


class TestDefaultCrisisAmplifier:
    """Tests for DefaultCrisisAmplifier per US4 acceptance scenarios."""

    def test_scenario1_crisis_amplifies_downward(self) -> None:
        """S1: Crisis=True -> downward rates multiplied by 2.5x, upward by 0.3x.

        Given a TRPF-triggered crisis flag, downward transition rates
        (dispossession, precaritization) are amplified and upward rates
        (accumulation, stabilization) are dampened.
        """
        amp = DefaultCrisisAmplifier()
        rates = TransitionRates(
            fips="00000",
            year=2010,
            dispossession=0.02,
            accumulation=0.01,
            precaritization=0.03,
            stabilization=0.05,
        )
        amplified = amp.amplify(rates, crisis=True)

        assert amplified.dispossession == pytest.approx(0.02 * 2.5)
        assert amplified.accumulation == pytest.approx(0.01 * 0.3)
        assert amplified.precaritization == pytest.approx(0.03 * 2.5)
        assert amplified.stabilization == pytest.approx(0.05 * 0.3)

    def test_scenario2_no_crisis_passthrough(self) -> None:
        """S2: Crisis=False -> rates returned unchanged."""
        amp = DefaultCrisisAmplifier()
        rates = TransitionRates(
            fips="00000",
            year=2015,
            dispossession=0.01,
            accumulation=0.005,
            precaritization=0.02,
            stabilization=0.05,
        )
        result = amp.amplify(rates, crisis=False)

        assert result.dispossession == pytest.approx(rates.dispossession)
        assert result.accumulation == pytest.approx(rates.accumulation)
        assert result.precaritization == pytest.approx(rates.precaritization)
        assert result.stabilization == pytest.approx(rates.stabilization)

    def test_crisis_rates_clamped_to_one(self) -> None:
        """Crisis amplification clamps rates to [0, 1]."""
        amp = DefaultCrisisAmplifier()
        rates = TransitionRates(
            fips="00000",
            year=2010,
            dispossession=0.50,  # 0.50 * 2.5 = 1.25, should clamp to 1.0
            accumulation=0.01,
            precaritization=0.50,
            stabilization=0.05,
        )
        amplified = amp.amplify(rates, crisis=True)

        assert amplified.dispossession <= 1.0
        assert amplified.precaritization <= 1.0

    def test_custom_amplification_factors(self) -> None:
        """Custom amplifier/dampener factors work correctly."""
        amp = DefaultCrisisAmplifier(crisis_amplifier=3.0, recovery_dampener=0.2)
        rates = TransitionRates(
            fips="00000",
            year=2010,
            dispossession=0.02,
            accumulation=0.01,
            precaritization=0.03,
            stabilization=0.05,
        )
        amplified = amp.amplify(rates, crisis=True)

        assert amplified.dispossession == pytest.approx(0.02 * 3.0)
        assert amplified.accumulation == pytest.approx(0.01 * 0.2)

    def test_scenario3_multi_period_magnitude(self) -> None:
        """SC-002: Crisis produces at least 2x transition magnitude.

        Sum of absolute share changes under crisis should be at least
        2x that of stable conditions when applied to same base rates.
        """
        amp = DefaultCrisisAmplifier()
        base_rates = TransitionRates(
            fips="00000",
            year=2015,
            dispossession=0.01,
            accumulation=0.005,
            precaritization=0.02,
            stabilization=0.05,
        )
        crisis_rates = amp.amplify(base_rates, crisis=True)

        # Total downward magnitude
        stable_down = base_rates.dispossession + base_rates.precaritization
        crisis_down = crisis_rates.dispossession + crisis_rates.precaritization
        assert crisis_down >= 2.0 * stable_down

    def test_preserves_fips_and_year(self) -> None:
        """Amplification preserves FIPS and year metadata."""
        amp = DefaultCrisisAmplifier()
        rates = TransitionRates(
            fips="26163",
            year=2010,
            dispossession=0.02,
            accumulation=0.01,
            precaritization=0.03,
            stabilization=0.05,
        )
        amplified = amp.amplify(rates, crisis=True)
        assert amplified.fips == "26163"
        assert amplified.year == 2010

    def test_protocol_compliance(self) -> None:
        """DefaultCrisisAmplifier satisfies CrisisAmplifier protocol."""
        from babylon.domain.economics.dynamics.data_sources import CrisisAmplifier

        amp: CrisisAmplifier = DefaultCrisisAmplifier()
        rates = TransitionRates(
            fips="00000",
            year=2015,
            dispossession=0.01,
            accumulation=0.005,
            precaritization=0.02,
            stabilization=0.05,
        )
        result = amp.amplify(rates, crisis=False)
        assert isinstance(result, TransitionRates)
