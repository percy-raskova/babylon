"""Shared fixtures for D-P-D' lifecycle circuit tests (Feature 030)."""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines, LifecycleDefines
from babylon.domain.economics.lifecycle.types import DPDState, LegitimationState


@pytest.fixture
def lifecycle_defines() -> LifecycleDefines:
    """Default lifecycle defines."""
    return LifecycleDefines()


@pytest.fixture
def game_defines() -> GameDefines:
    """Default game defines with lifecycle."""
    return GameDefines()


@pytest.fixture
def scenario_1_dpd_state() -> DPDState:
    """Scenario 1: Basic population flow test state."""
    return DPDState(
        pop_d=2150.0,
        pop_p=6050.0,
        pop_d_prime=1800.0,
        rate_d_to_p=0.0556,
        rate_p_to_d_prime=0.0213,
        rate_d_prime_to_death=0.039,
        birth_rate=0.0107,
        wealth_d_prime=10_000_000.0,
    )


@pytest.fixture
def scenario_2_legitimation_state() -> LegitimationState:
    """Scenario 2: Legitimation index test state."""
    return LegitimationState(
        pension_coverage=0.73,
        ss_replacement_rate=0.43,
        healthcare_security=0.60,
        home_ownership_rate=0.66,
        retirement_confidence=0.50,
    )
