"""Fixtures for integrated financial crisis assessment unit tests."""

from __future__ import annotations

from dataclasses import dataclass

import pytest


@dataclass(frozen=True)
class CrisisScenario:
    """Standard crisis scenario inputs."""

    interest_burden_ratio: float
    financialization_ratio: float
    default_rate: float
    credit_spread: float
    claims_exceed_surplus: bool


@pytest.fixture
def normal_scenario() -> CrisisScenario:
    """All indicators within safe bounds."""
    return CrisisScenario(
        interest_burden_ratio=0.15,
        financialization_ratio=2.0,
        default_rate=0.01,
        credit_spread=0.015,
        claims_exceed_surplus=False,
    )


@pytest.fixture
def crisis_scenario() -> CrisisScenario:
    """All indicators in crisis territory."""
    return CrisisScenario(
        interest_burden_ratio=0.55,
        financialization_ratio=4.0,
        default_rate=0.05,
        credit_spread=0.06,
        claims_exceed_surplus=True,
    )


@pytest.fixture
def latent_vulnerability_scenario() -> CrisisScenario:
    """Surface stability but financialization building."""
    return CrisisScenario(
        interest_burden_ratio=0.20,
        financialization_ratio=3.8,
        default_rate=0.01,
        credit_spread=0.02,
        claims_exceed_surplus=False,
    )
