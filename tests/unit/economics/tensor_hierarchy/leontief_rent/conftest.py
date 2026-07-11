"""Fixtures for Spec 057 Leontief imperial-rent pipeline unit tests.

Provides mock data sources implementing the Spec 057 Protocols
(``PeripheryLaborCoefficientsSource``, ``FinalDemandSource``,
``IndustryToCountyAllocator``) plus a stub ``EventBus`` capture for
asserting ``CalibrationWarning`` event emissions.

The mock-source pattern mirrors ``tests/unit/economics/melt/conftest.py``
and the project conftest hierarchy described in the project ``CLAUDE.md``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import numpy as np
import pytest

from babylon.domain.economics.tensor import NoDataSentinel
from babylon.domain.economics.tensor_hierarchy.types import PeripheryLaborCoefficients

# =============================================================================
# EventBus capture (lightweight stand-in for tests)
# =============================================================================


@dataclass
class CapturedEvent:
    """A frozen snapshot of one ``EventBus.publish(Event(...))`` call."""

    type: str
    tick: int
    payload: dict[str, Any]


class FakeEventBus:
    """Test stand-in for ``babylon.kernel.event_bus.EventBus`` that captures
    every ``publish(Event(...))`` call into an ordered list.

    Tests assert via ``bus.history`` rather than wiring real subscribers.
    """

    def __init__(self) -> None:
        self.history: list[CapturedEvent] = []

    def publish(self, event: Any) -> None:
        # Accept either the project's frozen Event dataclass or any object
        # exposing ``type``/``tick``/``payload`` attributes.
        self.history.append(
            CapturedEvent(
                type=event.type,
                tick=event.tick,
                payload=dict(event.payload),
            )
        )

    def subscribe(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def get_history(self) -> list[CapturedEvent]:
        return list(self.history)


@pytest.fixture
def fake_event_bus() -> FakeEventBus:
    return FakeEventBus()


# =============================================================================
# Mock BEA industry source
# =============================================================================


@pytest.fixture
def fake_bea_industries() -> list[str]:
    """A small synthetic BEA Summary industry list for unit tests."""
    return ["111", "211", "311", "423", "541"]  # 5 industries


# =============================================================================
# Mock periphery wage source
# =============================================================================


class FakePeripheryLaborCoefficientsSource:
    """Mock implementing the Spec 057 PeripheryLaborCoefficientsSource Protocol.

    Returns deterministic ``PeripheryLaborCoefficients`` for any year in
    ``ratios_by_year``; ``NoDataSentinel`` otherwise.
    """

    def __init__(
        self,
        ratios_by_year: dict[int, np.ndarray] | None = None,
        industries: list[str] | None = None,
    ) -> None:
        self._ratios_by_year = ratios_by_year or {}
        self._industries = industries or ["111", "211", "311", "423", "541"]

    def get_coefficients(self, year: int) -> PeripheryLaborCoefficients | NoDataSentinel:
        if year not in self._ratios_by_year:
            return NoDataSentinel(fips="", year=year, reason="missing periphery wage data for year")
        return PeripheryLaborCoefficients(
            year=year,
            industries=self._industries,
            wage_ratios=self._ratios_by_year[year],
        )


# =============================================================================
# Mock final-demand source
# =============================================================================


class FakeFinalDemandSource:
    """Mock implementing the Spec 057 FinalDemandSource Protocol."""

    def __init__(self, demand_by_year: dict[int, np.ndarray] | None = None) -> None:
        self._demand_by_year = demand_by_year or {}

    def get_final_demand(self, year: int) -> np.ndarray:
        if year not in self._demand_by_year:
            msg = f"No final-demand data for year {year}"
            raise ValueError(msg)
        return self._demand_by_year[year]


# =============================================================================
# Helpers
# =============================================================================


def make_uniform_ratios(industries: Iterable[str], value: float = 8.25) -> np.ndarray:
    """Build a uniform ``wage_ratios`` array — handy for ERDI-broadcast tests."""
    return np.full(len(list(industries)), value, dtype=np.float64)
