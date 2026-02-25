"""Fixtures for TRPF counter-tendencies unit tests."""

from __future__ import annotations

from dataclasses import dataclass

import pytest


@dataclass(frozen=True)
class CounterTendencyInputs:
    """Standard test inputs for counter-tendency calculations."""

    exploitation_rate_current: float = 1.5
    exploitation_rate_previous: float = 1.4
    productivity_growth: float = 0.02
    wage_growth: float = 0.01
    capital_goods_price_change: float = -0.03
    u6_unemployment: float = 0.08
    imperial_rent_flow: float = 500_000_000_000.0
    financial_profit_share: float = 0.25


@pytest.fixture
def default_ct_inputs() -> CounterTendencyInputs:
    """Counter-tendency inputs where counter-tendencies dominate."""
    return CounterTendencyInputs()


@pytest.fixture
def weakening_ct_inputs() -> CounterTendencyInputs:
    """Counter-tendency inputs where TRPF dominates."""
    return CounterTendencyInputs(
        exploitation_rate_current=1.4,
        exploitation_rate_previous=1.4,  # No change
        productivity_growth=0.01,
        wage_growth=0.02,  # Wages rising faster
        capital_goods_price_change=0.01,  # Capital goods getting more expensive
        u6_unemployment=0.04,  # Reserve army shrinking
        imperial_rent_flow=300_000_000_000.0,  # Declining imperial rent
        financial_profit_share=0.15,
    )
