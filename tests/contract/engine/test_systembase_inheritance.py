"""Contract test: all 22 Systems inherit from SystemBase (Spec 059 SC-005).

Enumerates every System class in the codebase and asserts each is a subclass
of :class:`SystemBase`. Per research.md D1 the count is 22 (21 in
``engine/systems/`` + 1 in ``economics/tick/system/``), not 23 as ADR-003
asserts.

Red-phase: this test fails until ADR-003's migration waves (T051–T055)
complete. Green-phase: all 22 systems must pass.
"""

from __future__ import annotations

import importlib

import pytest

from babylon.kernel.system_base import SystemBase

# (module_path, class_name) — keep alphabetised by module within each grouping.
SYSTEMS: list[tuple[str, str]] = [
    # 21 in src/babylon/engine/systems/
    ("babylon.engine.systems.community", "CommunitySystem"),
    ("babylon.engine.systems.contradiction", "ContradictionSystem"),
    ("babylon.engine.systems.contradiction_field", "ContradictionFieldSystem"),
    ("babylon.engine.systems.control_ratio", "ControlRatioSystem"),
    ("babylon.engine.systems.decomposition", "DecompositionSystem"),
    ("babylon.engine.systems.dispossession_events", "DispossessionEventSystem"),
    ("babylon.engine.systems.economic", "ImperialRentSystem"),
    ("babylon.engine.systems.edge_transition", "EdgeTransitionSystem"),
    ("babylon.engine.systems.event_template", "EventTemplateSystem"),
    ("babylon.engine.systems.field_derivative", "FieldDerivativeSystem"),
    ("babylon.engine.systems.ideology", "ConsciousnessSystem"),
    ("babylon.engine.systems.lifecycle", "LifecycleSystem"),
    ("babylon.engine.systems.metabolism", "MetabolismSystem"),
    ("babylon.engine.systems.ooda", "OODASystem"),
    ("babylon.engine.systems.production", "ProductionSystem"),
    ("babylon.engine.systems.reserve_army", "ReserveArmySystem"),
    ("babylon.engine.systems.solidarity", "SolidaritySystem"),
    ("babylon.engine.systems.struggle", "StruggleSystem"),
    ("babylon.engine.systems.survival", "SurvivalSystem"),
    ("babylon.engine.systems.territory", "TerritorySystem"),
    ("babylon.engine.systems.vitality", "VitalitySystem"),
    # 1 in src/babylon/economics/tick/system/
    ("babylon.economics.tick.system", "TickDynamicsSystem"),
]


def test_systems_count_is_22() -> None:
    """research.md D1 / SC-005: exactly 22 Systems are migrated."""
    assert len(SYSTEMS) == 22, f"SYSTEMS list has {len(SYSTEMS)} entries; spec 059 SC-005 says 22"


@pytest.mark.parametrize(("module_path", "cls_name"), SYSTEMS)
def test_system_inherits_systembase(module_path: str, cls_name: str) -> None:
    """SC-005: ``issubclass(cls, SystemBase)`` for every System."""
    mod = importlib.import_module(module_path)
    cls = getattr(mod, cls_name)
    assert issubclass(cls, SystemBase), (
        f"{module_path}.{cls_name} must inherit from SystemBase (FR-009)"
    )
