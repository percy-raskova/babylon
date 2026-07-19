"""U2 acceptance (design §4, §8.3): year 2041 arrives at tick ~1612 of a
5200-tick campaign — INSIDE every canonical run — and NationalTickParameters
is on the already-live MELT path. This walks the real clock across that
boundary and asserts no ValidationError escapes, and that the Vol III layer
degrades to NoDataSentinel rather than raising.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.domain.economics.credit.interest import DefaultInterestCalculator
from babylon.domain.economics.tensor import NoDataSentinel
from babylon.domain.economics.tick.system import TickDynamicsSystem
from babylon.kernel.sim_clock import SIM_EPOCH_YEAR, WEEKS_PER_YEAR
from tests.unit.economics.tick.conftest import MockMELTCalculator
from tests.unit.economics.tick.test_system import _make_services

pytestmark = pytest.mark.unit

#: The exact tick the design names as the crash point (§1.4, §8.3).
_CEILING_CROSSING_TICK = (2041 - SIM_EPOCH_YEAR) * WEEKS_PER_YEAR


def test_the_documented_crash_tick_is_inside_a_canonical_campaign() -> None:
    """Pin the arithmetic the design's severity claim rests on."""
    assert pytest.approx(1612, abs=WEEKS_PER_YEAR) == _CEILING_CROSSING_TICK
    assert _CEILING_CROSSING_TICK < 5200


def test_melt_path_survives_every_year_of_a_5200_tick_campaign() -> None:
    """NationalTickParameters is built once per year boundary for 100 years."""
    system = TickDynamicsSystem()
    services = _make_services(melt_calculator=MockMELTCalculator(tau=62.0, accept_any_year=True))
    for tick in range(0, 5200, WEEKS_PER_YEAR):  # bounded: 100 iterations
        year = SIM_EPOCH_YEAR + tick // WEEKS_PER_YEAR
        try:
            params = system._compute_national_params(year, services, prev_coefficients=None)
        except ValidationError as exc:  # pragma: no cover — the defect under test
            pytest.fail(f"ValidationError at tick {tick} (year {year}): {exc}")
        assert params is not None
        assert params.year == year, (
            f"year {year} was silently relabeled {params.year} — the clamp is back"
        )


def test_vol3_layer_degrades_rather_than_raising_past_the_ceiling() -> None:
    """Past MODELED_YEAR_CEILING the financial layer is ABSENT, not broken."""
    from tests.unit.economics.credit.conftest import MockInterestRateSource

    calc = DefaultInterestCalculator(
        rate_source=MockInterestRateSource(data={2041: (0.03, 0.04, 0.02)})
    )
    for tick in range(_CEILING_CROSSING_TICK, 5200, WEEKS_PER_YEAR):  # bounded
        year = SIM_EPOCH_YEAR + tick // WEEKS_PER_YEAR
        result = calc.compute_interest_rate_state(year)
        assert isinstance(result, NoDataSentinel), (
            f"year {year} produced a structured model past the modeled window"
        )
        assert "modeled" in result.reason.lower()
