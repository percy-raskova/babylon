"""Engine scenarios package — Scenario ABC + 6 ported builders.

ADR-006.1 / Spec 059 US4. Replaces the historical ``engine/scenarios.py``
single-file module with a package that holds:

- The :class:`Scenario` ABC + auto-registry (in :mod:`.base`).
- 6 thin subclass files that delegate to the legacy free-function builders
  for byte-equality with the pre-Bundle-2 baseline (SC-007).
- Backward-compat shims for the legacy free-function names
  (``create_*_scenario``) so existing call sites continue to resolve.
- The legacy implementations under ``_legacy`` / ``_legacy_wayne`` (kept as
  module-private attribute sources; do not import directly from outside the
  package).
- The 2 utilities (``get_multiverse_scenarios``, ``apply_scenario``) and 5
  private helpers from the legacy module are re-exported here so existing
  ``from babylon.engine.scenarios import …`` call sites continue to work.

Per :doc:`research.md` D3, only the **6 builder** functions are migrated
to ``Scenario`` subclasses; the 2 utilities are not migrated and remain
as free functions on this module.
"""

from __future__ import annotations

# Re-export legacy free functions + utilities + private helpers used outside
# this package. Existing imports of any of these resolve unchanged (FR-003 /
# contracts/import-equivalence.md C5).
from babylon.engine.scenarios._legacy import (  # noqa: F401
    apply_scenario,
    create_high_tension_scenario,
    create_imperial_circuit_scenario,
    create_labor_aristocracy_scenario,
    create_two_node_scenario,
    create_us_scenario,
    get_multiverse_scenarios,
)
from babylon.engine.scenarios._legacy_wayne import (  # noqa: F401
    create_wayne_county_scenario,
)

# Re-export Scenario ABC + registry surface.
from babylon.engine.scenarios.base import (
    _SCENARIO_REGISTRY,
    Scenario,
    get_scenario,
    list_scenarios,
)

# Re-export the 6 Scenario subclasses (importing populates _SCENARIO_REGISTRY).
from babylon.engine.scenarios.high_tension import HighTensionScenario
from babylon.engine.scenarios.imperial_circuit import ImperialCircuitScenario
from babylon.engine.scenarios.labor_aristocracy import LaborAristocracyScenario
from babylon.engine.scenarios.two_node import TwoNodeScenario
from babylon.engine.scenarios.us import USScenario
from babylon.engine.scenarios.wayne_county import WayneCountyScenario

__all__ = [
    # ABC + registry
    "Scenario",
    "_SCENARIO_REGISTRY",
    "get_scenario",
    "list_scenarios",
    # 6 Scenario subclasses
    "TwoNodeScenario",
    "HighTensionScenario",
    "LaborAristocracyScenario",
    "ImperialCircuitScenario",
    "USScenario",
    "WayneCountyScenario",
    # Legacy free-function shims (preserved for FR-003 import equivalence)
    "create_two_node_scenario",
    "create_high_tension_scenario",
    "create_labor_aristocracy_scenario",
    "create_imperial_circuit_scenario",
    "create_us_scenario",
    "create_wayne_county_scenario",
    # Utilities (not migrated — research.md D3)
    "apply_scenario",
    "get_multiverse_scenarios",
]
