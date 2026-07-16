"""Wave 6 C4: the tick pipeline consumes a wired cpi_source.

``_compute_county_states`` carried ``real_wage_deflator`` at a frozen 1.0
(nominal == real) with no data hook — every wage/wealth figure the tick
pipeline produces was nominal-only, the "wages never naked" gap. This gate
pins the contract (same shape as Wave 6 D8's ``unemployment_source`` gate):
when ``services.cpi_source`` is wired it supplies the CPIAUCSL-based
base-year real-wage deflator (``get_cpi_deflator``); when it is absent — or
returns honest ``None`` — the engine keeps its documented 1.0
graceful-degradation default (so headless synthetic scenarios and
qa:regression, which never wire it, are byte-identical). Unlike
``median_wage`` (endogenous, source consulted only on bootstrap), the
deflator is re-read every tick — CPI is an external national series, not a
simulated trajectory the engine should own after tick 1.
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.tick.system import TickDynamicsSystem
from babylon.engine.services import ServiceContainer

WAYNE = "26163"


class _StubCPISource:
    """Minimal CPIAUCSL-shaped source returning a real 2011 deflator."""

    def get_cpi_deflator(self, year: int, base_year: int = 2015) -> float | None:
        return 1.18 if year == 2011 else None


def test_compute_county_states_reads_cpi_source() -> None:
    """A wired cpi_source supplies the real CPI-based deflator."""
    services = ServiceContainer.create(cpi_source=_StubCPISource())
    system = TickDynamicsSystem()

    states = system._compute_county_states(2011, [WAYNE], services, None)

    assert states[WAYNE].real_wage_deflator == pytest.approx(1.18)


def test_compute_county_states_defaults_deflator_without_source() -> None:
    """No cpi_source => the engine's documented 1.0 default is preserved."""
    services = ServiceContainer.create()
    system = TickDynamicsSystem()

    states = system._compute_county_states(2011, [WAYNE], services, None)

    assert states[WAYNE].real_wage_deflator == pytest.approx(1.0)


def test_honest_none_from_source_keeps_default() -> None:
    """Honest None from the source (unavailable year) never fabricates a deflator."""
    services = ServiceContainer.create(cpi_source=_StubCPISource())
    system = TickDynamicsSystem()

    states = system._compute_county_states(1800, [WAYNE], services, None)

    assert states[WAYNE].real_wage_deflator == pytest.approx(1.0)
