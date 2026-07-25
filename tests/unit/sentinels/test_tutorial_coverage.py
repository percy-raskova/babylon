"""Tests for the tutorial option-coverage sentinel (T6).

Per ``ai/_inbox/t6-tutorial-bdd-ruling.md``: "an option with no scenario is a
seam — red." These tests prove the gate actually catches that: a live clean
run against the real repo, then mutation-validated proofs that an uncovered
binding reds the gate, a cited exemption clears it, and a stale exemption
(naming a binding that no longer exists) reds the gate the other way.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.sentinels.exemptions import SentinelExemption
from babylon.sentinels.tutorial_coverage.checks import (
    check_every_binding_covered_or_exempted,
    check_every_exemption_still_names_a_real_binding,
)
from babylon.sentinels.tutorial_coverage.registry import TUTORIAL_COVERAGE_EXEMPTIONS

pytestmark = pytest.mark.unit


def test_the_live_repo_is_clean() -> None:
    """Every real declared binding is covered or exempted, right now."""
    assert check_every_binding_covered_or_exempted() == []


def test_every_declared_exemption_is_grounded_against_the_live_repo() -> None:
    """No exemption in the registry is stale against the real BINDINGS."""
    assert check_every_exemption_still_names_a_real_binding() == []


def test_registry_rows_are_well_formed() -> None:
    """Every declared exemption's key is a well-formed ('binding', class, key) triple."""
    assert TUTORIAL_COVERAGE_EXEMPTIONS
    for exemption in TUTORIAL_COVERAGE_EXEMPTIONS:
        assert exemption.key[0] == "binding"
        assert len(exemption.key) == 3


def test_an_uncovered_binding_with_no_exemption_is_a_finding() -> None:
    """The efficacy proof: a real gap, injected, is caught."""
    options = (("binding:Ghost:x", "Ghost", "x", "src/babylon/tui/ghost.py", 7),)
    findings = check_every_binding_covered_or_exempted(
        options=options,
        exercised=frozenset(),
        exemptions=(),
    )
    assert len(findings) == 1
    assert "Ghost" in findings[0]
    assert "src/babylon/tui/ghost.py:7" in findings[0]


def test_an_exercised_anchor_clears_the_finding() -> None:
    """A binding whose anchor a script exercises needs no exemption at all."""
    options = (("binding:Ghost:x", "Ghost", "x", "src/babylon/tui/ghost.py", 7),)
    findings = check_every_binding_covered_or_exempted(
        options=options,
        exercised=frozenset({"binding:Ghost:x"}),
        exemptions=(),
    )
    assert findings == []


def test_a_cited_exemption_clears_the_finding() -> None:
    """An uncovered binding with a matching exemption is not a finding."""
    options = (("binding:Ghost:x", "Ghost", "x", "src/babylon/tui/ghost.py", 7),)
    exemption = SentinelExemption(
        key=("binding", "Ghost", "x"),
        reason="test fixture",
        owner="Persephone Raskova",
        date="2026-07-22",
        tracking_task="N/A (test fixture)",
    )
    findings = check_every_binding_covered_or_exempted(
        options=options,
        exercised=frozenset(),
        exemptions=(exemption,),
    )
    assert findings == []


def test_an_exemption_for_a_different_class_does_not_cross_match() -> None:
    """('binding', 'Ghost', 'x') never exempts ('binding', 'Other', 'x')."""
    options = (("binding:Other:x", "Other", "x", "src/babylon/tui/other.py", 3),)
    exemption = SentinelExemption(
        key=("binding", "Ghost", "x"),
        reason="test fixture",
        owner="Persephone Raskova",
        date="2026-07-22",
        tracking_task="N/A (test fixture)",
    )
    findings = check_every_binding_covered_or_exempted(
        options=options,
        exercised=frozenset(),
        exemptions=(exemption,),
    )
    assert len(findings) == 1
    assert "Other" in findings[0]


def test_a_stale_exemption_is_a_finding() -> None:
    """An exemption naming a binding that no longer exists reds the gate."""
    options = (("binding:Real:x", "Real", "x", "src/babylon/tui/real.py", 1),)
    exemption = SentinelExemption(
        key=("binding", "GoneClass", "gone_key"),
        reason="test fixture",
        owner="Persephone Raskova",
        date="2026-07-22",
        tracking_task="N/A (test fixture)",
    )
    findings = check_every_exemption_still_names_a_real_binding(
        options=options,
        exemptions=(exemption,),
    )
    assert len(findings) == 1
    assert "GoneClass" in findings[0]
    assert "gone_key" in findings[0]


def test_a_grounded_exemption_is_not_a_finding() -> None:
    options = (("binding:Real:x", "Real", "x", "src/babylon/tui/real.py", 1),)
    exemption = SentinelExemption(
        key=("binding", "Real", "x"),
        reason="test fixture",
        owner="Persephone Raskova",
        date="2026-07-22",
        tracking_task="N/A (test fixture)",
    )
    assert (
        check_every_exemption_still_names_a_real_binding(options=options, exemptions=(exemption,))
        == []
    )


def test_registry_rejects_a_malformed_row() -> None:
    """The shared SentinelExemption validator still fires for this family."""
    with pytest.raises(ValidationError):
        SentinelExemption(
            key=("binding", "X", "y"),
            reason="",
            owner="Persephone Raskova",
            date="2026-07-22",
            tracking_task="N/A",
        )
