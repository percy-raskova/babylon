"""Coverage-truth probe: declared evidence is verified against a real run."""

from __future__ import annotations

import pytest
from tools.gate_coverage_probe import run_probe
from tools.regression_scenarios import ScenarioCoverage, SystemEvidence

pytestmark = pytest.mark.unit


def _cov(**kwargs) -> ScenarioCoverage:
    base = {"scenario": "two_node", "layers": ("material_base",), "systems": (), "at_rest": ()}
    base.update(kwargs)
    return ScenarioCoverage(**base)


def test_true_declaration_passes() -> None:
    cov = _cov(
        systems=(
            SystemEvidence(
                system="VitalitySystem",
                kind="entity_delta",
                key="C001.wealth",
                claim="worker wealth moves",
            ),
        )
    )
    assert run_probe(coverage=(cov,), max_ticks=10) == []


def test_efficacy_false_event_declaration_reds() -> None:
    """MUTATION: an event that never fires in two_node must produce a finding."""
    cov = _cov(
        systems=(
            SystemEvidence(
                system="OODASystem",
                kind="event",
                key="organizational_action",
                claim="orgs act (they cannot: none seeded)",
            ),
        )
    )
    findings = run_probe(coverage=(cov,), max_ticks=10)
    assert any("organizational_action" in f and "two_node" in f for f in findings)


def test_efficacy_false_delta_declaration_reds() -> None:
    """MUTATION: an entity attr that never changes must produce a finding."""
    cov = _cov(
        systems=(
            SystemEvidence(
                system="LifecycleSystem",
                kind="entity_delta",
                key="C001.active",
                claim="worker deactivates (it does not in 5 ticks)",
            ),
        )
    )
    findings = run_probe(coverage=(cov,), max_ticks=5)
    assert any("C001.active" in f for f in findings)


def test_unknown_scenario_is_loud() -> None:
    cov = _cov(scenario="no_such_scenario")
    with pytest.raises(KeyError):
        run_probe(coverage=(cov,), max_ticks=2)
