"""Program 17 item-25 Fix C: the tick pipeline consumes a wired employment_source.

``_compute_county_states`` hardcoded ``employment = 100_000.0`` with no data hook
(unlike ``capital_stock``, which reads ``services.capital_calculator.get_K``), so
even with a real capital_calculator the derived rates mixed real K with a
placeholder headcount. This gate pins the symmetric contract: when
``services.employment_source`` is wired it supplies the per-county headcount
(``get_county_total_employment``); when it is absent the engine keeps its
documented 100k graceful-degradation default (so headless / qa:regression, which
never wire it, are byte-identical).
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.tick.system import TickDynamicsSystem
from babylon.engine.services import ServiceContainer

WAYNE = "26163"


class _StubEmploymentSource:
    """Minimal QCEW-shaped source returning a real Wayne headcount."""

    def get_county_total_employment(self, fips: str, year: int) -> int | None:
        return 719_741 if fips == WAYNE else None


def test_compute_county_states_reads_employment_source() -> None:
    """A wired employment_source supplies the real per-county headcount."""
    services = ServiceContainer.create(employment_source=_StubEmploymentSource())
    system = TickDynamicsSystem()

    states = system._compute_county_states(2011, [WAYNE], services, None)

    assert states[WAYNE].employment == pytest.approx(719_741.0)


def test_compute_county_states_defaults_employment_without_source() -> None:
    """No employment_source => the engine's documented 100k default is preserved."""
    services = ServiceContainer.create()
    system = TickDynamicsSystem()

    states = system._compute_county_states(2011, [WAYNE], services, None)

    assert states[WAYNE].employment == pytest.approx(100_000.0)
