"""Wave 6 D8: the tick pipeline consumes a wired unemployment_source.

``_compute_county_states`` carried ``unemployment_rate`` from the previous
tick with a ``0.05`` bootstrap default and no data hook, so the seam registry
flagged ``tick_unemployment_rate`` as FROZEN. This gate pins the symmetric
contract (same shape as the item-25 Fix-C ``employment_source`` gate): when
``services.unemployment_source`` is wired it supplies the per-county BLS LAUS
U-3 rate (``get_county_unemployment_rate``); when it is absent — or the
county-year row is (honest ``None``) — the engine keeps its documented
prev-carry/0.05 graceful-degradation default (so headless synthetic scenarios
and qa:regression, which never wire it, are byte-identical).
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.tick.system import TickDynamicsSystem
from babylon.engine.services import ServiceContainer

WAYNE = "26163"


class _StubUnemploymentSource:
    """Minimal LAUS-shaped source returning a real Wayne U-3 rate."""

    def get_county_unemployment_rate(self, fips: str, year: int) -> float | None:
        return 0.102 if fips == WAYNE else None


def test_compute_county_states_reads_unemployment_source() -> None:
    """A wired unemployment_source supplies the real per-county U-3 rate."""
    services = ServiceContainer.create(unemployment_source=_StubUnemploymentSource())
    system = TickDynamicsSystem()

    states = system._compute_county_states(2011, [WAYNE], services, None)

    assert states[WAYNE].unemployment_rate == pytest.approx(0.102)


def test_compute_county_states_defaults_unemployment_without_source() -> None:
    """No unemployment_source => the engine's documented 0.05 default is preserved."""
    services = ServiceContainer.create()
    system = TickDynamicsSystem()

    states = system._compute_county_states(2011, [WAYNE], services, None)

    assert states[WAYNE].unemployment_rate == pytest.approx(0.05)


def test_absent_county_row_keeps_default() -> None:
    """Honest None from the source (unknown county) never fabricates a rate."""
    services = ServiceContainer.create(unemployment_source=_StubUnemploymentSource())
    system = TickDynamicsSystem()

    states = system._compute_county_states(2011, ["01001"], services, None)

    assert states["01001"].unemployment_rate == pytest.approx(0.05)
