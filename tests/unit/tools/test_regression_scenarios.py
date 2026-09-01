"""Coverage-declaration data model: shape, validation, and literal-parseability."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest
from tools.regression_scenarios import (
    SCENARIO_COVERAGE,
    SCENARIOS,
    AtRestChannel,
    CoverageGap,
    ScenarioCoverage,
    SystemEvidence,
)

pytestmark = pytest.mark.unit

_MODULE = Path(__file__).resolve().parents[3] / "tools" / "regression_scenarios.py"
_REPOSITORY_ROOT = _MODULE.parent.parent


def test_every_canonical_scenario_has_a_declaration() -> None:
    declared = {c.scenario for c in SCENARIO_COVERAGE}
    assert set(SCENARIOS) <= declared, sorted(set(SCENARIOS) - declared)


def test_declarations_reject_blank_fields() -> None:
    with pytest.raises(ValueError, match="claim"):
        SystemEvidence(system="VitalitySystem", kind="event", key="X", claim="")
    with pytest.raises(ValueError, match="reason"):
        AtRestChannel(channel="financial_endogenous_rate", reason=" ")
    with pytest.raises(ValueError, match="remediation"):
        CoverageGap(system="SubstrateSystem", reason="no hex nodes", remediation="")


def test_declarations_reject_unknown_fields() -> None:
    with pytest.raises(ValueError):
        ScenarioCoverage(scenario="x", layers=(), systems=(), at_rest=(), bogus=1)  # type: ignore[call-arg]


def test_coverage_data_literals_are_ast_parseable() -> None:
    """The static sentinel reads these via ast.literal_eval — prove it can."""
    tree = ast.parse(_MODULE.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id
            in {"SCENARIO_COVERAGE_DATA", "COVERAGE_GAPS_DATA", "CHANNEL_WRITERS"}
        ):
            assert node.value is not None
            ast.literal_eval(node.value)  # raises if not a pure literal
            found.add(node.target.id)
    assert found == {"SCENARIO_COVERAGE_DATA", "COVERAGE_GAPS_DATA", "CHANNEL_WRITERS"}


@pytest.mark.parametrize(
    "script",
    ["tools/necropolis_viewer.py", "tools/regression_test.py"],
)
def test_tool_entrypoints_can_import_devtools_when_launched_as_scripts(script: str) -> None:
    """Direct script mode must not rely on pytest adding the repository root."""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = "src"
    completed = subprocess.run(  # noqa: S603 -- repository-owned script contract
        [sys.executable, script, "--help"],
        cwd=_REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert completed.returncode == 0, completed.stderr
    assert "usage:" in completed.stdout
