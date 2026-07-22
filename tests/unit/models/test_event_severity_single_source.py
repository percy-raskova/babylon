"""Single-source parity + AST-gate tests for T1.1 Unit U2.

Covers the acceptance bar from ``ai/_inbox/t11-seam-severity-design.md`` U2: both severity
surfaces (the web bridge's ``_classify_event`` and the Archive Chronicle's
``classify_event_salience``) resolve identically to
:func:`babylon.models.event_severity.resolve_severity` for all 84
:class:`~babylon.models.enums.events.EventType` members, including the loud
unclassified -> warning floor; and neither surface's source carries a local hand-copied
severity dict literal any more (the ``_EVENT_SEVERITY``/``EVENT_SEVERITY`` twins U2 retired).

**The mutation test named by the design (§4 U2):** reintroducing a local one-entry override in
ONE surface that differs from the generated table reds
:func:`TestBothSurfacesResolveIdenticallyAcrossAll84Members.test_both_surfaces_agree_with_each_other`
(and its two generated-table-comparison siblings). Verified locally by temporarily editing
``web/game/engine_bridge.py`` to reintroduce a one-entry ``_EVENT_SEVERITY`` override for
``economic_crisis`` that disagreed with the generated table, confirming this suite reds (both
the AST gate below and the parity tests), then reverting before commit — U6's seam_algebra
family later promotes this same class of check to a standing CI gate.
:class:`TestParityHelperIsNotVacuous` additionally pins the comparison LOGIC itself against a
synthetic mismatch, independent of any real source edit (the Seam Observatory's own "a green
check is worthless unless shown to red on a real defect" discipline).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from babylon.models.enums.events import EventType
from babylon.models.event_severity import SeverityTier, resolve_severity
from babylon.tui.chronicle_salience import classify_event_salience
from game.engine_bridge import _classify_event

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENGINE_BRIDGE_PATH = _REPO_ROOT / "web" / "game" / "engine_bridge.py"
_CHRONICLE_SALIENCE_PATH = _REPO_ROOT / "src" / "babylon" / "tui" / "chronicle_salience.py"

#: Both hand-copied literal names U2 retired — a regression reintroducing EITHER, in either
#: surface, is exactly the silent-drift failure mode single-sourcing eliminates.
_FORBIDDEN_LITERAL_NAMES = ("_EVENT_SEVERITY", "EVENT_SEVERITY")


def _module_level_assigned_names(path: Path) -> set[str]:
    """Every name a module-level ``Assign``/``AnnAssign`` binds, by AST (no import, no
    execution — the same static-only discipline every sentinel in this family uses).

    :param path: Source file to parse.
    :returns: The set of module-level bound names.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in tree.body:
        targets: list[ast.expr]
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        names.update(t.id for t in targets if isinstance(t, ast.Name))
    return names


class TestNoLocalSeverityLiteralRemainsInEitherSurface:
    """T1.1 U2 acceptance: no local severity literal remains in either surface (AST gate)."""

    @pytest.mark.parametrize("path", [_ENGINE_BRIDGE_PATH, _CHRONICLE_SALIENCE_PATH])
    def test_neither_hand_copied_name_is_module_level_bound(self, path: Path) -> None:
        bound = _module_level_assigned_names(path)
        offenders = bound & set(_FORBIDDEN_LITERAL_NAMES)
        assert offenders == set(), (
            f"{path}: a hand-copied severity literal has reappeared: {sorted(offenders)} — "
            "both surfaces must resolve through babylon.models.event_severity.resolve_severity"
        )


def _assert_tier_matches(label: str, actual: str, expected: SeverityTier) -> None:
    """One (label, actual, expected) comparison, factored out so
    :class:`TestParityHelperIsNotVacuous` can prove this exact comparison reds on a real
    mismatch, without needing to hand-edit a real surface's source.

    ``actual`` is typed plain ``str`` (not :data:`SeverityTier`) because the web bridge's
    ``_classify_event`` returns a bare ``str`` — this comparison is exactly what proves, at
    the value level, that its result is always one of the three tiers.

    :param label: A human-readable identifier for the failure message (the event type, or a
        synthetic marker from the efficacy test).
    :param actual: The tier a surface resolved.
    :param expected: The tier the generated table (or another surface) resolved.
    :raises AssertionError: If ``actual != expected``.
    """
    assert actual == expected, f"{label}: resolved {actual!r}, expected {expected!r}"


class TestBothSurfacesResolveIdenticallyAcrossAll84Members:
    """T1.1 U2 acceptance: both surfaces resolve identically for all 84 members."""

    def test_web_bridge_matches_the_generated_table(self) -> None:
        for event_type in EventType:
            expected = resolve_severity(event_type).tier
            actual = _classify_event(event_type.value)
            _assert_tier_matches(f"web bridge / {event_type}", actual, expected)

    def test_archive_chronicle_matches_the_generated_table(self) -> None:
        for event_type in EventType:
            expected_severity = resolve_severity(event_type)
            actual_severity = classify_event_salience(event_type)
            _assert_tier_matches(
                f"Archive Chronicle / {event_type}", actual_severity.tier, expected_severity.tier
            )
            assert actual_severity.unclassified == expected_severity.unclassified, (
                f"{event_type}: Archive Chronicle unclassified={actual_severity.unclassified!r}, "
                f"generated table unclassified={expected_severity.unclassified!r}"
            )

    def test_both_surfaces_agree_with_each_other(self) -> None:
        for event_type in EventType:
            web_tier = _classify_event(event_type.value)
            chronicle_tier = classify_event_salience(event_type).tier
            _assert_tier_matches(
                f"web bridge vs Archive Chronicle / {event_type}", web_tier, chronicle_tier
            )


class TestUnclassifiedFloorMatchesAcrossSurfaces:
    """The loud unclassified -> warning floor holds identically on both surfaces (design §2)."""

    def test_an_unclassified_type_is_warning_on_both_surfaces(self) -> None:
        # POPULATION_DEATH is a real EventType with no declared taxonomy row.
        assert _classify_event(EventType.POPULATION_DEATH.value) == "warning"
        salience = classify_event_salience(EventType.POPULATION_DEATH)
        assert salience.tier == "warning"
        assert salience.unclassified is True

    def test_a_garbage_string_is_warning_on_the_web_bridge(self) -> None:
        # Not even a real EventType value — the web bridge's own loud floor for a typo,
        # an empty string, or a test-fixture-only type (Constitution III.11: never the
        # legacy quiet "informational" degrade).
        assert _classify_event("totally_made_up_event_type") == "warning"
        assert _classify_event("") == "warning"


class TestParityHelperIsNotVacuous:
    """The comparison logic the parity tests share reds on a deliberate mismatch —
    the Seam Observatory's own "a green check is worthless unless shown to red on a real
    defect" discipline, pinned here independent of any real source-file edit."""

    def test_a_synthetic_mismatch_reds(self) -> None:
        with pytest.raises(AssertionError, match=r"resolved 'warning', expected 'critical'"):
            _assert_tier_matches("synthetic-mutation", "warning", "critical")
