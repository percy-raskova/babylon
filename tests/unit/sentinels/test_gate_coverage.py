"""gate_coverage sentinel: the gate's estate declaration is complete and true-by-name.

INVARIANT tests run the real repo; MUTATION tests inject a broken registry;
INFRA tests prove loud failure (exit 2 semantics via SentinelCheckError).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.gate_coverage.checks import (
    check_bundle_evidence,
    check_declared_names_exist,
    check_union_covers_all_systems,
    engine_system_names,
)

pytestmark = pytest.mark.unit


def test_real_engine_system_count() -> None:
    """Count pin over the AST-read ``_SYSTEM_CLASSES`` (was hardcoded 30 and
    silently stale from U8's 31st system until U9's estate sweep caught it —
    the U8 closeout gate ran off-tree, ADR135 §estate)."""
    names = engine_system_names()
    assert len(names) == 32
    assert "MarketScissorsSystem" in names
    assert "AllegianceSystem" in names  # P25 U8, ADR134
    assert "PolicySystem" in names  # P25 U9, ADR135


def test_real_union_covers_all_systems() -> None:
    """Every one of the 30 systems is either evidenced or a declared gap."""
    assert check_union_covers_all_systems() == []


def test_real_declared_names_exist() -> None:
    assert check_declared_names_exist() == []


def test_real_bundle_evidence_holds() -> None:
    assert check_bundle_evidence() == []


def test_efficacy_reds_on_uncovered_system(tmp_path: Path) -> None:
    """MUTATION: a scenarios module declaring almost nothing must red."""
    module = tmp_path / "scenarios.py"
    module.write_text(
        "SCENARIO_COVERAGE_DATA = ("
        "{'scenario': 's', 'layers': (), 'systems': ("
        "{'system': 'VitalitySystem', 'kind': 'event', 'key': 'X', 'claim': 'c'},), "
        "'at_rest': ()},)\n"
        "COVERAGE_GAPS_DATA = ()\n"
        "CHANNEL_WRITERS = {}\n",
        encoding="utf-8",
    )
    findings = check_union_covers_all_systems(scenarios_path=module)
    assert findings, "29 uncovered systems must produce findings"
    assert any("MarketScissorsSystem" in f for f in findings)
    assert all("[gate-blindness]" in f for f in findings) or all("REMEDY" in f for f in findings)


def test_efficacy_reds_on_invented_system_name(tmp_path: Path) -> None:
    """MUTATION: a declaration naming a system that does not exist must red."""
    module = tmp_path / "scenarios.py"
    module.write_text(
        "SCENARIO_COVERAGE_DATA = ("
        "{'scenario': 's', 'layers': (), 'systems': ("
        "{'system': 'PhantomSystem', 'kind': 'event', 'key': 'X', 'claim': 'c'},), "
        "'at_rest': ()},)\n"
        "COVERAGE_GAPS_DATA = ()\n"
        "CHANNEL_WRITERS = {'wealth': ('AlsoPhantomSystem',)}\n",
        encoding="utf-8",
    )
    findings = check_declared_names_exist(scenarios_path=module)
    assert any("PhantomSystem" in f for f in findings)
    assert any("AlsoPhantomSystem" in f for f in findings)


def test_efficacy_reds_on_false_bundle_evidence(tmp_path: Path) -> None:
    """MUTATION: bundle evidence naming an event absent from the bundle reds."""
    module = tmp_path / "scenarios.py"
    module.write_text(
        "SCENARIO_COVERAGE_DATA = ("
        "{'scenario': 'detroit_tri_county', 'layers': (), 'systems': ("
        "{'system': 'OODASystem', 'kind': 'bundle_event', 'key': 'phantom_event_type', "
        "'claim': 'c'},), 'at_rest': ()},)\n"
        "COVERAGE_GAPS_DATA = ()\nCHANNEL_WRITERS = {}\n",
        encoding="utf-8",
    )
    findings = check_bundle_evidence(scenarios_path=module)
    assert any("phantom_event_type" in f for f in findings)


def test_efficacy_reds_on_false_bundle_field_path(tmp_path: Path) -> None:
    """MUTATION: bundle_field naming a dotted path absent from the bundle reds."""
    module = tmp_path / "scenarios.py"
    module.write_text(
        "SCENARIO_COVERAGE_DATA = ("
        "{'scenario': 'detroit_tri_county', 'layers': (), 'systems': ("
        "{'system': 'ContradictionSystem', 'kind': 'bundle_field', "
        "'key': 'terminal_state.phantom_field', 'claim': 'c'},), 'at_rest': ()},)\n"
        "COVERAGE_GAPS_DATA = ()\nCHANNEL_WRITERS = {}\n",
        encoding="utf-8",
    )
    findings = check_bundle_evidence(scenarios_path=module)
    assert any("phantom_field" in f for f in findings)


def test_efficacy_reds_on_forbidden_bundle_field_value(tmp_path: Path) -> None:
    """MUTATION: a bundle_field value matching a declared forbidden value reds.

    Points at the REAL committed baseline (default bundle_path) with a
    synthetic scenarios module whose row claims the real, present key
    ``terminal_state.max_tension`` but forbids its actual committed value
    (0.667728) — presence-only checking would pass this; the value check
    must not.
    """
    module = tmp_path / "scenarios.py"
    module.write_text(
        "SCENARIO_COVERAGE_DATA = ("
        "{'scenario': 'detroit_tri_county', 'layers': (), 'systems': ("
        "{'system': 'ContradictionSystem', 'kind': 'bundle_field', "
        "'key': 'terminal_state.max_tension', 'claim': 'c', "
        "'forbidden_values': ('0.667728',)},), 'at_rest': ()},)\n"
        "COVERAGE_GAPS_DATA = ()\nCHANNEL_WRITERS = {}\n",
        encoding="utf-8",
    )
    findings = check_bundle_evidence(scenarios_path=module)
    assert any("forbidden value" in f and "0.667728" in f for f in findings)


def test_infra_missing_module_is_loud(tmp_path: Path) -> None:
    with pytest.raises(SentinelCheckError):
        check_union_covers_all_systems(scenarios_path=tmp_path / "nope.py")
