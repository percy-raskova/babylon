"""single_county: the smallest graph where the Vol III financial layer fires."""

from __future__ import annotations

import pytest

from babylon.engine.scenarios import create_single_county_scenario

pytestmark = pytest.mark.unit


def test_scenario_carries_a_real_county_fips() -> None:
    state, _config, _defines = create_single_county_scenario()
    fips = [t.county_fips for t in state.territories.values() if t.county_fips]
    assert fips == ["26163"]


def test_scenario_is_deterministic() -> None:
    a = create_single_county_scenario()[0]
    b = create_single_county_scenario()[0]
    assert a.model_dump() == b.model_dump()


def test_financial_layer_fires_through_the_production_path() -> None:
    """After stepping with the Wayne overrides, county interest is nonzero.

    This is the U9-inertness detector in miniature: the interest number must
    come out of TickDynamicsSystem's real calculator chain (tensor_registry ->
    SurplusDistributionCalculator), not a stamped fixture.

    Only 3 ticks are needed: the annual pipeline fires on tick 0 (the FIRST
    ``step()`` call sees ``context.tick == state.tick == 0``, and
    ``0 % WEEKS_PER_YEAR == 0``), computing county year ``2010`` (the
    ``TickDynamicsSystem._determine_year`` default ``base_year``) — the exact
    year ``tests/fixtures/single_county_wayne.json`` was extracted for (see
    that fixture's ``_provenance`` for the year-selection rationale). Ticks 1
    and 2 are non-boundary ticks that only exercise ``_accrue_flows``; they
    are driven here purely to prove the fired state SURVIVES the
    ``WorldState`` round-trip across subsequent ticks, mirroring how
    ``tools.regression_test``'s harness actually calls ``step()``.
    """
    from tools.regression_test import build_single_county_overrides

    from babylon.engine.simulation_engine import step

    state, config, defines = create_single_county_scenario()
    overrides = build_single_county_overrides(defines)
    context: dict = {}
    for _ in range(3):
        state = step(state, config, context, defines, calculator_overrides=overrides)
    tick_dynamics = context.get("_tick_dynamics")
    assert tick_dynamics, "TickDynamicsSystem never stamped county state"
    county_states = tick_dynamics.get("county_states", {})
    assert "26163" in county_states
    distribution = county_states["26163"].surplus_distribution
    assert distribution is not None
    assert distribution.interest_payments > 0.0
    financial = context.get("_national_financial")
    assert financial, "national_financial never persisted (Task 7 regression)"
    assert financial["endogenous_interest"]["rate"] > 0.0
