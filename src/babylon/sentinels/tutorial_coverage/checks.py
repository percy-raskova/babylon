"""The tutorial option-coverage sentinel (static, gating).

Per ``ai/_inbox/t6-tutorial-bdd-ruling.md`` (BD, 2026-07-21): "an option with no
scenario is a seam (∂L boundary node) — red." This sensor is that check made
real: every player-facing :class:`~textual.binding.Binding` a Babylon TUI class
declares on its own ``BINDINGS`` must be exercised by some authored
:class:`~babylon.game.tutorial.TutorialStep`'s ``anchor`` (``"binding:<Class>:
<key>"`` — :mod:`babylon.game.tutorial`'s own anchor grammar) or carry a cited
:class:`~babylon.sentinels.exemptions.SentinelExemption` in
:data:`~babylon.sentinels.tutorial_coverage.registry.TUTORIAL_COVERAGE_EXEMPTIONS`.

A companion direction closes the reverse hole (an exemption that no longer
matches any live binding — the same "declared-but-absent" failure mode
:mod:`babylon.sentinels.coupling` checks for its own registry): every declared
exemption's key must still name a real, currently-declared binding.

Scope -- STATIC coherence only: reads source with :mod:`ast`; never imports
:mod:`textual`, ``babylon.tui``, or ``babylon.game.tutorial`` (layer 0.5, same
rank as every other sentinel).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from babylon.sentinels._ast import declared_bindings, tutorial_step_anchors
from babylon.sentinels.base import LabelledCheck, run_sensor
from babylon.sentinels.exemptions import SentinelExemption, is_exempt
from babylon.sentinels.report import finding
from babylon.sentinels.tutorial_coverage.registry import TUTORIAL_COVERAGE_EXEMPTIONS

#: Repo root (this file is ``<root>/src/babylon/sentinels/tutorial_coverage/checks.py``).
_REPO_ROOT: Path = Path(__file__).resolve().parents[4]

#: Where player-facing ``BINDINGS`` may be declared -- the live TUI shell and
#: its composition root (a future ``TutorialOverlay`` may land in either).
_BINDING_SCAN_ROOTS: tuple[str, ...] = ("src/babylon/tui", "src/babylon/game")

#: Where authored :class:`~babylon.game.tutorial.TutorialStep` scripts live.
_SCRIPT_SCAN_ROOT: str = "src/babylon/game"


def _scan(root: str) -> list[Path]:
    """List a scan root's Python files, deterministically ordered.

    :param root: Repo-relative directory to scan.
    :returns: Sorted absolute paths.
    """
    return sorted((_REPO_ROOT / root).rglob("*.py"))


def _declared_options(
    scan_roots: tuple[str, ...] = _BINDING_SCAN_ROOTS,
) -> tuple[tuple[str, str, str, str, int], ...]:
    """Every class's own declared binding, as an anchor plus its provenance.

    :param scan_roots: Repo-relative directories to scan (injectable for tests).
    :returns: ``(anchor, class_name, key, file, line)`` tuples, in scan order.
    :raises SentinelCheckError: If a scanned file is unparseable.
    """
    options: list[tuple[str, str, str, str, int]] = []
    for root in scan_roots:
        for path in _scan(root):
            rel = str(path.relative_to(_REPO_ROOT))
            for class_name, key, _action, line in declared_bindings(path):
                anchor = f"binding:{class_name}:{key}"
                options.append((anchor, class_name, key, rel, line))
    return tuple(options)


def _exercised_anchors(script_scan_root: str = _SCRIPT_SCAN_ROOT) -> frozenset[str]:
    """Every anchor exercised by some authored tutorial script.

    :param script_scan_root: Repo-relative directory to scan (injectable).
    :returns: The set of declared ``anchor=`` literals.
    :raises SentinelCheckError: If a scanned file is unparseable.
    """
    anchors: set[str] = set()
    for path in _scan(script_scan_root):
        anchors.update(tutorial_step_anchors(path))
    return frozenset(anchors)


def check_every_binding_covered_or_exempted(
    options: tuple[tuple[str, str, str, str, int], ...] | None = None,
    exercised: frozenset[str] | None = None,
    exemptions: tuple[SentinelExemption, ...] = TUTORIAL_COVERAGE_EXEMPTIONS,
) -> list[str]:
    """Every declared binding is exercised by a script or carries an exemption.

    :param options: Declared bindings to judge (defaults to the live scan;
        injectable so the efficacy test can supply an injected defect).
    :param exercised: Anchors the authored scripts exercise (defaults to the
        live scan; injectable).
    :param exemptions: Declared exemption rows (injectable).
    :returns: Sorted agent-legible finding strings (empty when every binding is
        covered or exempted).
    :raises SentinelCheckError: If a scanned file is missing or unparseable.
    """
    live_options = _declared_options() if options is None else options
    live_exercised = _exercised_anchors() if exercised is None else exercised
    findings: list[str] = []
    for anchor, class_name, key, file, line in live_options:
        if anchor in live_exercised:
            continue
        if is_exempt(("binding", class_name, key), exemptions):
            continue
        findings.append(
            finding(
                error_class="tutorial-option-uncovered",
                symbol=anchor,
                file=file,
                line=line,
                problem=(
                    f"{class_name}'s {key!r} binding is a real player-facing option "
                    "with no TutorialStep exercising it and no cited exemption"
                ),
                remedy=(
                    "either author a TutorialStep whose anchor is "
                    f"{anchor!r} (ai/_inbox/t6-tutorial-bdd-ruling.md) or add a dated "
                    "SentinelExemption to "
                    "babylon.sentinels.tutorial_coverage.registry."
                    "TUTORIAL_COVERAGE_EXEMPTIONS keyed "
                    f'("binding", {class_name!r}, {key!r})'
                ),
            )
        )
    return sorted(findings)


def check_every_exemption_still_names_a_real_binding(
    options: tuple[tuple[str, str, str, str, int], ...] | None = None,
    exemptions: tuple[SentinelExemption, ...] = TUTORIAL_COVERAGE_EXEMPTIONS,
) -> list[str]:
    """Every declared exemption's key still names a currently-declared binding.

    The dual of :func:`check_every_binding_covered_or_exempted` -- an
    exemption whose binding was renamed or removed is dead weight that would
    silently mask a FUTURE binding coincidentally reusing the same class/key
    (:mod:`babylon.sentinels.exemptions`'s own exact-tuple-match design does
    not protect against a stale row being *reused* by a new, unrelated finding
    unless something keeps the registry honest against the live source).

    :param options: Declared bindings (defaults to the live scan; injectable).
    :param exemptions: Declared exemption rows (injectable).
    :returns: Sorted agent-legible finding strings for exemptions with no
        matching live binding (empty when every exemption is still grounded).
    :raises SentinelCheckError: If a scanned file is missing or unparseable.
    """
    live_options = _declared_options() if options is None else options
    live_keys = {(class_name, key) for _anchor, class_name, key, _file, _line in live_options}
    findings: list[str] = []
    for exemption in exemptions:
        if exemption.key[0] != "binding" or len(exemption.key) != 3:
            continue
        _kind, class_name, key = exemption.key
        if (class_name, key) in live_keys:
            continue
        findings.append(
            finding(
                error_class="tutorial-exemption-stale",
                symbol=".".join(exemption.key),
                file="src/babylon/sentinels/tutorial_coverage/registry.py",
                line=0,
                problem=(
                    f"exemption keyed {exemption.key!r} names no currently-declared "
                    f"{class_name}.BINDINGS entry for key {key!r}"
                ),
                remedy="delete the stale row from TUTORIAL_COVERAGE_EXEMPTIONS",
            )
        )
    return sorted(findings)


def _summary(advisory_count: int) -> str:
    """Build the clean-run summary line.

    :param advisory_count: Number of advisory findings (always ``0`` -- this
        sensor has no advisory tier today).
    :returns: The one-line summary.
    """
    del advisory_count
    return "TUTORIAL-COVERAGE: every declared binding is covered or exempted; every exemption is grounded"


_GATING: tuple[LabelledCheck, ...] = (
    ("covered-or-exempted", check_every_binding_covered_or_exempted),
    ("exemption-grounded", check_every_exemption_still_names_a_real_binding),
)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point -- ``tools/sentinel_check.py tutorial-coverage [--check]``.

    :param argv: Forwarded CLI args (``--check`` is accepted for the
        dispatcher's uniform contract; this sensor always gates).
    :returns: 0 clean, 1 gating violation found, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="CI mode (no-op alias)")
    parser.parse_args(argv)
    return run_sensor("TUTORIAL-COVERAGE", _GATING, (), _summary)


if __name__ == "__main__":
    sys.exit(main())
