"""Canonical qa:regression scenario definitions and coverage declarations.

Extracted from ``tools/regression_test.py`` (this is its "successor module"
per the modernization spec §E1) so the scenario estate is importable data,
AST-readable by ``babylon.sentinels.gate_coverage``, and shared with the
coverage-truth probe without dragging in the whole harness.
"""

from __future__ import annotations

from typing import Any, Final

from shared import inject_parameter

from babylon.config.defines import GameDefines
from babylon.engine.scenarios import (
    create_imperial_circuit_scenario,
    create_two_node_scenario,
)

# Scenario configurations
SCENARIOS: Final[dict[str, dict[str, Any]]] = {
    "imperial_circuit": {
        "description": "4-node default scenario",
        "factory": "create_imperial_circuit_scenario",
        "defines_overrides": {},
    },
    "two_node": {
        "description": "Minimal worker vs owner",
        "factory": "create_two_node_scenario",
        "defines_overrides": {},
    },
    "starvation": {
        "description": "Low extraction efficiency stress",
        "factory": "create_imperial_circuit_scenario",
        "defines_overrides": {
            "economy.extraction_efficiency": 0.05,
        },
    },
    "glut": {
        "description": "High extraction with metabolic overshoot",
        "factory": "create_imperial_circuit_scenario",
        "defines_overrides": {
            "economy.extraction_efficiency": 0.99,
            "survival.default_subsistence": 0.0,
        },
    },
    "fascist_bifurcation": {
        "description": "Consciousness routing to national identity",
        "factory": "create_imperial_circuit_scenario",
        "defines_overrides": {
            "economy.extraction_efficiency": 0.7,
            "consciousness.sensitivity": 0.3,
        },
    },
}


def create_scenario(
    name: str,
) -> tuple[Any, Any, GameDefines]:
    """Create scenario by name.

    Args:
        name: Scenario name from SCENARIOS

    Returns:
        Tuple of (WorldState, SimulationConfig, GameDefines)
    """
    config = SCENARIOS[name]

    # Call factory function
    factory_name = config["factory"]
    if factory_name == "create_imperial_circuit_scenario":
        state, sim_config, base_defines = create_imperial_circuit_scenario()
    elif factory_name == "create_two_node_scenario":
        state, sim_config, base_defines = create_two_node_scenario()
    else:
        raise ValueError(f"Unknown factory: {factory_name}")

    # Apply overrides
    defines = base_defines
    for path, value in config["defines_overrides"].items():
        defines = inject_parameter(defines, path, value)

    return state, sim_config, defines
