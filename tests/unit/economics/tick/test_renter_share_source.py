"""Wave 6 C2: the tick pipeline consumes a wired housing_source.

``_compute_county_states`` carried ``renter_share`` at a frozen ``0.0``
default with no data hook, so the seam registry flags ``tick_renter_share``
as FROZEN. This gate pins the symmetric contract (same shape as the
Wave 6 D8 ``unemployment_source`` gate): when ``services.housing_source`` is
wired it supplies the per-county ACS renter share
(``get_county_renter_share``); when it is absent — or the county-year row is
(honest ``None``) — the engine keeps its documented prev-carry/0.0 graceful-
degradation default (so headless synthetic scenarios and qa:regression,
which never wire it, are byte-identical).
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.tick.system import TickDynamicsSystem
from babylon.engine.services import ServiceContainer

WAYNE = "26163"


class _StubHousingSource:
    """Minimal ACS-shaped source returning a real Wayne renter share."""

    def get_county_renter_share(self, fips: str, year: int) -> float | None:
        return 0.62 if fips == WAYNE else None


def test_compute_county_states_reads_housing_source() -> None:
    """A wired housing_source supplies the real per-county renter share."""
    services = ServiceContainer.create(housing_source=_StubHousingSource())
    system = TickDynamicsSystem()

    states = system._compute_county_states(2011, [WAYNE], services, None)

    assert states[WAYNE].renter_share == pytest.approx(0.62)


def test_compute_county_states_defaults_renter_share_without_source() -> None:
    """No housing_source => the engine's documented 0.0 default is preserved."""
    services = ServiceContainer.create()
    system = TickDynamicsSystem()

    states = system._compute_county_states(2011, [WAYNE], services, None)

    assert states[WAYNE].renter_share == pytest.approx(0.0)


def test_absent_county_row_keeps_default() -> None:
    """Honest None from the source (unknown county) never fabricates a share."""
    services = ServiceContainer.create(housing_source=_StubHousingSource())
    system = TickDynamicsSystem()

    states = system._compute_county_states(2011, ["01001"], services, None)

    assert states["01001"].renter_share == pytest.approx(0.0)
