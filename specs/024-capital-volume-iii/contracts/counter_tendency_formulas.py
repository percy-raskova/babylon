"""Contract: TRPF Counter-Tendencies (US5, FR-010, FR-011).

These are function signatures defining the public API contract.
Implementations go in src/babylon/economics/counter_tendencies/.
"""

from __future__ import annotations

from typing import Protocol

from babylon.economics.tensor import NoDataSentinel

# Placeholder type aliases
Currency = float


# ---------------------------------------------------------------------------
# Calculator Protocol
# ---------------------------------------------------------------------------


class CounterTendencyCalculator(Protocol):
    """Protocol for computing TRPF counter-tendency strength."""

    def compute_counter_tendencies(
        self,
        year: int,
        exploitation_rate_current: float,
        exploitation_rate_previous: float,
        productivity_growth: float,
        wage_growth: float,
        capital_goods_price_change: float,
        u6_unemployment: float,
        imperial_rent_flow: Currency,
        financial_profit_share: float,
    ) -> "CounterTendencyStrength | NoDataSentinel":
        """Compute all six counter-tendency indicators and net strength.

        Args:
            year: Analysis year.
            exploitation_rate_current: Current s/v ratio.
            exploitation_rate_previous: Prior year s/v ratio.
            productivity_growth: YoY labor productivity change.
            wage_growth: YoY real wage change.
            capital_goods_price_change: YoY PPI for capital goods.
            u6_unemployment: Broad unemployment rate (U-6).
            imperial_rent_flow: Net unequal exchange Phi (from Feature 013).
            financial_profit_share: Financial sector share of total profits.

        Returns:
            CounterTendencyStrength with all six indicators and net value.

        Post-conditions:
            - net > 0: counter-tendencies dominating
            - net < 0: TRPF tendency dominating
            - net ~ 0: balanced
        """
        ...

    def correlates_with_profit_rate(
        self,
        net_counter_tendency: float,
        profit_rate_trend: float,
    ) -> bool:
        """Check correlation between net CT and profit rate direction.

        Returns:
            True if signs match (both positive or both negative).
            SC-005 requires >= 80% correlation across simulation.
        """
        ...
