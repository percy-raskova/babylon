"""SC-007 import-boundary audit: in-scope tools/ MUST NOT import the legacy
in-memory engine path.

Spec: 064-headless-sim-runner (T041).

Per FR-014 / SC-007, the six in-scope tools (``audit_simulation``,
``monte_carlo``, ``parameter_analysis``, ``sensitivity_analysis``,
``profiler``, ``landscape_analysis``) and the migration seam
``tools/shared.py`` may not import any of:

* ``create_imperial_circuit_scenario`` / ``create_two_node_scenario``
  (legacy in-memory scenarios)
* ``babylon.engine.simulation_engine.step``
* ``babylon.models.world_state.WorldState`` (in-memory state object)

The remaining ``tools/`` scripts (``regression_test``,
``interview_persona``, ``necropolis_viewer``, ``verify_math_divergence``,
``vertical_slice``, ``tune_agent``) are intentionally OUT OF SCOPE for
spec-064 — their refactor is deferred. We only enforce the audit on the
six in-scope tools so the boundary is precise.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parents[2] / "tools"

IN_SCOPE_TOOLS: tuple[str, ...] = (
    "audit_simulation.py",
    "monte_carlo.py",
    "parameter_analysis.py",
    "sensitivity_analysis.py",
    "profiler.py",
    "landscape_analysis.py",
    "shared.py",
)

FORBIDDEN_NAMES: frozenset[str] = frozenset(
    {
        "create_imperial_circuit_scenario",
        "create_two_node_scenario",
        "step",
        "WorldState",
    }
)
FORBIDDEN_MODULES: tuple[str, ...] = (
    "babylon.engine.scenarios",
    "babylon.engine.simulation_engine",
    "babylon.models.world_state",
)


def _import_findings(source: str) -> list[str]:
    """Return a list of forbidden import strings found in the source."""
    findings: list[str] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in FORBIDDEN_MODULES:
            for alias in node.names:
                if alias.name in FORBIDDEN_NAMES or alias.name == "*":
                    findings.append(f"from {node.module} import {alias.name}")
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FORBIDDEN_MODULES:
                    findings.append(f"import {alias.name}")
    return findings


@pytest.mark.parametrize("tool_name", IN_SCOPE_TOOLS)
def test_in_scope_tool_has_no_forbidden_imports(tool_name: str) -> None:
    path = TOOLS_DIR / tool_name
    assert path.exists(), f"Expected in-scope tool not found: {path}"
    findings = _import_findings(path.read_text())
    assert not findings, f"{tool_name} contains spec-064-forbidden imports (SC-007): {findings}"
