"""Tests for PrecarityDeriver.

Feature: 017-simulation-tick-dynamics
Task: T015
"""

from __future__ import annotations

from babylon.domain.economics.tick.precarity import PrecarityDeriver


class TestPrecarityDeriver:
    """Tests for PrecarityDeriver precarity indicator derivation."""

    def test_default_coefficients(self) -> None:
        """Verify default coefficients (pter_fraction=0.4, nilf_fraction=0.6)."""
        deriver = PrecarityDeriver()
        assert deriver.pter_fraction == 0.4
        assert deriver.nilf_fraction == 0.6

    def test_basic_derivation(self) -> None:
        """Verify basic U-6, PTER, NILF derivation."""
        deriver = PrecarityDeriver()
        u6, pter, nilf = deriver.derive(
            unemployment_rate=0.05,
            precaritization_rate=0.10,
        )
        # u6 = unemployment + precaritization = 0.05 + 0.10 = 0.15
        assert abs(u6 - 0.15) < 0.001
        # pter = precaritization * pter_fraction = 0.10 * 0.4 = 0.04
        assert abs(pter - 0.04) < 0.001
        # nilf = precaritization * nilf_fraction = 0.10 * 0.6 = 0.06
        assert abs(nilf - 0.06) < 0.001

    def test_zero_precaritization(self) -> None:
        """Verify zero precaritization yields minimal precarity."""
        deriver = PrecarityDeriver()
        u6, pter, nilf = deriver.derive(
            unemployment_rate=0.05,
            precaritization_rate=0.0,
        )
        assert abs(u6 - 0.05) < 0.001
        assert abs(pter - 0.0) < 0.001
        assert abs(nilf - 0.0) < 0.001

    def test_high_precaritization(self) -> None:
        """Verify high precaritization scales correctly."""
        deriver = PrecarityDeriver()
        u6, pter, nilf = deriver.derive(
            unemployment_rate=0.08,
            precaritization_rate=0.30,
        )
        # u6 = 0.08 + 0.30 = 0.38
        assert abs(u6 - 0.38) < 0.001
        # pter = 0.30 * 0.4 = 0.12
        assert abs(pter - 0.12) < 0.001
        # nilf = 0.30 * 0.6 = 0.18
        assert abs(nilf - 0.18) < 0.001

    def test_custom_fractions(self) -> None:
        """Verify custom pter/nilf fractions are respected."""
        deriver = PrecarityDeriver(pter_fraction=0.5, nilf_fraction=0.5)
        u6, pter, nilf = deriver.derive(
            unemployment_rate=0.05,
            precaritization_rate=0.10,
        )
        assert abs(pter - 0.05) < 0.001
        assert abs(nilf - 0.05) < 0.001

    def test_u6_clamped_to_one(self) -> None:
        """Verify U-6 rate is clamped to [0, 1]."""
        deriver = PrecarityDeriver()
        u6, pter, nilf = deriver.derive(
            unemployment_rate=0.80,
            precaritization_rate=0.50,
        )
        # u6 would be 1.30 but should be clamped to 1.0
        assert u6 <= 1.0
        assert u6 >= 0.0

    def test_pter_and_nilf_clamped(self) -> None:
        """Verify PTER and NILF are clamped to [0, 1]."""
        deriver = PrecarityDeriver()
        u6, pter, nilf = deriver.derive(
            unemployment_rate=0.05,
            precaritization_rate=0.10,
        )
        assert 0.0 <= pter <= 1.0
        assert 0.0 <= nilf <= 1.0

    def test_handoff_rule_from_class_distribution(self) -> None:
        """Verify precaritization_rate can drive precarity from class shares.

        The handoff rule: lumpenproletariat_share maps to precaritization_rate,
        encoding the relationship between class decomposition and labor market
        precarity indicators.
        """
        deriver = PrecarityDeriver()
        # Lumpen share 0.15 -> precaritization_rate 0.15
        u6, pter, nilf = deriver.derive(
            unemployment_rate=0.053,
            precaritization_rate=0.15,
        )
        # u6 = 0.053 + 0.15 = 0.203
        assert abs(u6 - 0.203) < 0.001
