"""Tests for savings rate schedule.

Feature: 016-class-dynamics-engine
Task: T005
"""

from __future__ import annotations

import pytest

from babylon.economics.dynamics.savings_schedule import DefaultSavingsRateSchedule
from babylon.economics.melt.types import ClassPosition


class TestDefaultSavingsRateSchedule:
    """Tests for DefaultSavingsRateSchedule."""

    def test_bourgeoisie_rate(self) -> None:
        """Bourgeoisie savings rate is 0.38 per SCF top 1%."""
        schedule = DefaultSavingsRateSchedule()
        assert schedule.get_savings_rate(ClassPosition.BOURGEOISIE) == pytest.approx(0.38)

    def test_petit_bourgeoisie_rate(self) -> None:
        """Petit-bourgeoisie savings rate is 0.20 per SCF 90th-99th."""
        schedule = DefaultSavingsRateSchedule()
        assert schedule.get_savings_rate(ClassPosition.PETIT_BOURGEOISIE) == pytest.approx(0.20)

    def test_labor_aristocracy_rate(self) -> None:
        """Labor aristocracy savings rate is 0.12 per SCF 50th-90th."""
        schedule = DefaultSavingsRateSchedule()
        assert schedule.get_savings_rate(ClassPosition.LABOR_ARISTOCRACY) == pytest.approx(0.12)

    def test_proletariat_rate(self) -> None:
        """Proletariat savings rate is 0.03 per SCF bottom 50%."""
        schedule = DefaultSavingsRateSchedule()
        assert schedule.get_savings_rate(ClassPosition.PROLETARIAT) == pytest.approx(0.03)

    def test_lumpenproletariat_rate(self) -> None:
        """Lumpenproletariat savings rate is 0.0 (no savings capacity)."""
        schedule = DefaultSavingsRateSchedule()
        assert schedule.get_savings_rate(ClassPosition.LUMPENPROLETARIAT) == pytest.approx(0.0)

    def test_phi_adjustment_positive(self) -> None:
        """Positive imperial rent adjusts savings upward."""
        schedule = DefaultSavingsRateSchedule()
        adjustment = schedule.get_phi_adjustment(phi_hour=3.50, wage=45000.0)
        assert adjustment > 0.0

    def test_phi_adjustment_capped_at_005(self) -> None:
        """Phi adjustment cannot exceed 0.05 (5 percentage points)."""
        schedule = DefaultSavingsRateSchedule()
        # Large phi_hour relative to wage to trigger cap
        adjustment = schedule.get_phi_adjustment(phi_hour=50.0, wage=20000.0)
        assert adjustment == pytest.approx(0.05)

    def test_phi_adjustment_zero_wage_guard(self) -> None:
        """When wage=0, phi_adjustment returns 0.0 (no division by zero)."""
        schedule = DefaultSavingsRateSchedule()
        adjustment = schedule.get_phi_adjustment(phi_hour=3.50, wage=0.0)
        assert adjustment == pytest.approx(0.0)

    def test_phi_adjustment_zero_phi_guard(self) -> None:
        """When phi_hour=0, phi_adjustment returns 0.0."""
        schedule = DefaultSavingsRateSchedule()
        adjustment = schedule.get_phi_adjustment(phi_hour=0.0, wage=45000.0)
        assert adjustment == pytest.approx(0.0)

    def test_phi_adjustment_formula(self) -> None:
        """Phi adjustment follows min(phi_hour * 2080 / wage, 0.05) formula."""
        schedule = DefaultSavingsRateSchedule()
        phi_hour = 3.50
        wage = 45000.0
        expected = min(phi_hour * 2080 / wage, 0.05)
        actual = schedule.get_phi_adjustment(phi_hour=phi_hour, wage=wage)
        assert actual == pytest.approx(expected)

    def test_protocol_compliance(self) -> None:
        """DefaultSavingsRateSchedule satisfies SavingsRateSource protocol."""
        from babylon.economics.dynamics.data_sources import SavingsRateSource

        source: SavingsRateSource = DefaultSavingsRateSchedule()
        assert source.get_savings_rate(ClassPosition.PROLETARIAT) is not None
