"""Wave 6 C3: the tick pipeline consumes a wired income_source.

``_compute_county_states`` had no bracket-ratio data hook — the epochs audit
(item 167) flagged that ``fact_census_income`` had been "collapsed to SUM"
with no bracket-aware reader, so the engine never carried a top/bottom
income-bracket household ratio at all. This gate pins the same contract shape
as the Wave 6 D8 ``unemployment_source`` gate: when ``services.income_source``
is wired it supplies the per-county ACS B19001 top/bottom ratio
(``get_county_bracket_ratio``); when it is absent — or the county-year row is
(honest ``None``) — the engine keeps its documented prev-carry/0.0
not-computed default (so headless synthetic scenarios and qa:regression,
which never wire it, are byte-identical).
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.tick.system import TickDynamicsSystem
from babylon.engine.services import ServiceContainer

WAYNE = "26163"


class _StubIncomeSource:
    """Minimal ACS-shaped source returning a real Wayne bracket ratio."""

    def get_county_bracket_ratio(self, fips: str, year: int) -> float | None:
        return 0.31 if fips == WAYNE else None


def test_compute_county_states_reads_income_source() -> None:
    """A wired income_source supplies the real per-county bracket ratio."""
    services = ServiceContainer.create(income_source=_StubIncomeSource())
    system = TickDynamicsSystem()

    states = system._compute_county_states(2011, [WAYNE], services, None)

    assert states[WAYNE].bracket_ratio == pytest.approx(0.31)


def test_compute_county_states_defaults_bracket_ratio_without_source() -> None:
    """No income_source => the engine's documented 0.0 default is preserved."""
    services = ServiceContainer.create()
    system = TickDynamicsSystem()

    states = system._compute_county_states(2011, [WAYNE], services, None)

    assert states[WAYNE].bracket_ratio == pytest.approx(0.0)


def test_absent_county_row_keeps_default() -> None:
    """Honest None from the source (unknown county) never fabricates a ratio."""
    services = ServiceContainer.create(income_source=_StubIncomeSource())
    system = TickDynamicsSystem()

    states = system._compute_county_states(2011, ["01001"], services, None)

    assert states["01001"].bracket_ratio == pytest.approx(0.0)
