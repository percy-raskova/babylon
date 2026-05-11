"""Unit tests for Scenario ABC + registry — Spec 059 US4 / ADR-006.1.

Verifies:
- Each of the 6 ported scenarios auto-registers at import time.
- get_scenario(name) returns the right subclass.
- Two subclasses with the same ``name`` raise ``ValueError`` at class-definition
  time (collision detection per US4 acceptance #2 / contracts/protocol-satisfaction.md P6).
- The 6 backward-compat shims (``create_*_scenario``) resolve.
"""

from __future__ import annotations

import pytest

from babylon.engine.scenarios import (
    _SCENARIO_REGISTRY,
    HighTensionScenario,
    ImperialCircuitScenario,
    LaborAristocracyScenario,
    Scenario,
    TwoNodeScenario,
    USScenario,
    WayneCountyScenario,
    create_high_tension_scenario,
    create_imperial_circuit_scenario,
    create_labor_aristocracy_scenario,
    create_two_node_scenario,
    create_us_scenario,
    create_wayne_county_scenario,
    get_scenario,
    list_scenarios,
)

EXPECTED = {
    "two_node": TwoNodeScenario,
    "high_tension": HighTensionScenario,
    "labor_aristocracy": LaborAristocracyScenario,
    "imperial_circuit": ImperialCircuitScenario,
    "us": USScenario,
    "wayne_county": WayneCountyScenario,
}


class TestRegistry:
    def test_six_scenarios_registered(self) -> None:
        for name in EXPECTED:
            assert name in _SCENARIO_REGISTRY, (
                f"Scenario '{name}' not registered (expected via __init_subclass__)"
            )

    def test_registry_maps_to_correct_subclass(self) -> None:
        for name, expected_cls in EXPECTED.items():
            assert _SCENARIO_REGISTRY[name] is expected_cls, (
                f"_SCENARIO_REGISTRY['{name}'] is {_SCENARIO_REGISTRY[name].__name__}, expected {expected_cls.__name__}"
            )

    def test_get_scenario_resolves(self) -> None:
        assert get_scenario("imperial_circuit") is ImperialCircuitScenario

    def test_list_scenarios_sorted(self) -> None:
        names = list_scenarios()
        assert names == sorted(names)
        for n in EXPECTED:
            assert n in names


class TestNameCollision:
    def test_duplicate_name_raises_value_error(self) -> None:
        """US4 acceptance #2: subclass collision is fatal at class-def time."""
        with pytest.raises(ValueError, match="name collision"):

            class Duplicate(Scenario):
                name = "imperial_circuit"  # collides with ImperialCircuitScenario

                def build(self, *args, **kwargs):  # type: ignore[override]
                    raise NotImplementedError


class TestBackwardCompatShims:
    """FR-003 / contracts/import-equivalence.md C5: every legacy free-function
    name continues to resolve."""

    def test_all_six_shims_exist(self) -> None:
        for fn in (
            create_two_node_scenario,
            create_high_tension_scenario,
            create_labor_aristocracy_scenario,
            create_imperial_circuit_scenario,
            create_us_scenario,
            create_wayne_county_scenario,
        ):
            assert callable(fn)

    def test_wayne_county_top_level_module_shim(self) -> None:
        """The top-level ``babylon.engine.scenarios_wayne_county`` shim still resolves."""
        from babylon.engine.scenarios_wayne_county import (
            create_wayne_county_scenario as wc_via_shim,
        )

        assert wc_via_shim is create_wayne_county_scenario
