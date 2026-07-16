"""Owner-queue item 60: real median-wage BOOTSTRAP via a wired wage_source.

``CountyEconomicState.median_wage`` is ENDOGENOUS — it bootstraps at the
21.0 placeholder and then moves under wage-pressure/compression dynamics.
The deficiency was the placeholder bootstrap, not the carry. This gate pins
the contract: when ``services.wage_source`` is wired it supplies the
INITIAL county median hourly wage (``get_county_median_hourly_wage``, the
employment-weighted p50 estimator over QCEW 6-digit industry wages); once a
previous state exists the source is never consulted again — data seeds the
initial condition, simulation dynamics own the trajectory. Unwired or
honest-``None`` keeps the documented 21.0 default (so headless synthetic
scenarios and qa:regression are byte-identical).
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.tick.system import TickDynamicsSystem
from babylon.engine.services import ServiceContainer

WAYNE = "26163"


class _StubWageSource:
    """Minimal QCEW-shaped source returning a real Wayne p50 hourly wage."""

    def __init__(self) -> None:
        self.calls = 0

    def get_county_median_hourly_wage(self, fips: str, year: int) -> float | None:
        self.calls += 1
        return 26.5 if fips == WAYNE else None


def test_bootstrap_reads_wage_source_when_no_previous_state() -> None:
    """First tick for a county: the wired source seeds median_wage."""
    services = ServiceContainer.create(wage_source=_StubWageSource())
    system = TickDynamicsSystem()

    states = system._compute_county_states(2011, [WAYNE], services, None)

    assert states[WAYNE].median_wage == pytest.approx(26.5)


def test_previous_state_wins_over_source() -> None:
    """median_wage is endogenous: once prev exists, the source is not consulted.

    Wage-pressure dynamics compound tick over tick — re-reading data every
    tick would clobber the simulation's own trajectory.
    """
    source = _StubWageSource()
    services = ServiceContainer.create(wage_source=source)
    system = TickDynamicsSystem()

    first = system._compute_county_states(2011, [WAYNE], services, None)
    calls_after_bootstrap = source.calls
    second = system._compute_county_states(2011, [WAYNE], services, first)

    assert second[WAYNE].median_wage == pytest.approx(first[WAYNE].median_wage)
    assert source.calls == calls_after_bootstrap


def test_unwired_keeps_documented_default() -> None:
    """No wage_source => the engine's documented 21.0 bootstrap is preserved."""
    services = ServiceContainer.create()
    system = TickDynamicsSystem()

    states = system._compute_county_states(2011, [WAYNE], services, None)

    assert states[WAYNE].median_wage == pytest.approx(21.0)


def test_honest_none_keeps_default() -> None:
    """Source returns None (unknown county) => default, never a fabricated wage."""
    services = ServiceContainer.create(wage_source=_StubWageSource())
    system = TickDynamicsSystem()

    states = system._compute_county_states(2011, ["01001"], services, None)

    assert states["01001"].median_wage == pytest.approx(21.0)
