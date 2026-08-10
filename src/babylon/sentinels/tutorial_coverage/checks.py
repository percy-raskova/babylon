"""The tutorial option-coverage sentinel (static; currently non-gating).

Per ``ai/_inbox/t6-tutorial-bdd-ruling.md`` (BD, 2026-07-21): "an option with no
scenario is a seam (∂L boundary node) — red." This sensor is that check made
real. From the M7 cutover until the Amendment AF (ADR186) deletion ceremony
the option universe was the Rust/Ratatui client's keybar hint tables
(``rust/crates/babylon-tui/src/views/keybar.rs``, parsed as text by the
now-deleted ``babylon.sentinels._rust.declared_keybar_hints``); every
``(surface, key)`` hint row had to be exercised by some authored
:class:`~babylon.game.tutorial.TutorialStep`'s ``anchor``
(``"binding:<Surface>:<key>"`` — :mod:`babylon.game.tutorial`'s own anchor
grammar) or carry a cited
:class:`~babylon.sentinels.exemptions.SentinelExemption` in
:data:`~babylon.sentinels.tutorial_coverage.registry.TUTORIAL_COVERAGE_EXEMPTIONS`.

**RETAINED_CONTENT_ONLY (ADR186 sentinel disposition table, AF clause vii):**
the Rust client and its keybar are gone, so this sensor currently has no live
option universe to gate — :func:`check_every_binding_covered_or_exempted` and
:func:`check_every_exemption_still_names_a_real_binding` are the surviving
RECONCILIATION ALGORITHM (declared options vs. exercised anchors vs.
exemptions), kept alive and mutation-tested
(``tests/unit/sentinels/test_tutorial_coverage.py``) via explicit
``options=``/``exercised=`` arguments — never against a live default, since
none exists. :data:`_GATING` is deliberately empty: a green run here is
honest ("nothing live to check"), not a claim of coverage. The next client's
own binding/option surface (Bevy, Program 28+) needs a new extractor wired
back into a live ``_declared_options()`` before this sensor can gate again;
:func:`_exercised_anchors` (the ``babylon.game`` AST scan side) needs no such
rewiring and stays live.

Scope -- STATIC coherence only: reads Python source with :mod:`ast`; never
imports ``babylon.game.tutorial`` (layer 0.5, same rank as every other
sentinel).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from babylon.sentinels._ast import tutorial_step_anchors
from babylon.sentinels.base import SCOPE_NOT_DECLARED, LabelledCheck, run_sensor
from babylon.sentinels.exemptions import SentinelExemption, is_exempt
from babylon.sentinels.report import finding
from babylon.sentinels.tutorial_coverage.registry import TUTORIAL_COVERAGE_EXEMPTIONS

#: Repo root (this file is ``<root>/src/babylon/sentinels/tutorial_coverage/checks.py``).
_REPO_ROOT: Path = Path(__file__).resolve().parents[4]

#: Where authored :class:`~babylon.game.tutorial.TutorialStep` scripts live.
_SCRIPT_SCAN_ROOT: str = "src/babylon/game"


def _scan(root: str) -> list[Path]:
    """List a scan root's Python files, deterministically ordered.

    :param root: Repo-relative directory to scan.
    :returns: Sorted absolute paths.
    """
    return sorted((_REPO_ROOT / root).rglob("*.py"))


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
    options: tuple[tuple[str, str, str, str, int], ...],
    exercised: frozenset[str] | None = None,
    exemptions: tuple[SentinelExemption, ...] = TUTORIAL_COVERAGE_EXEMPTIONS,
) -> list[str]:
    """Every declared binding is exercised by a script or carries an exemption.

    No live default: since the Amendment AF (ADR186) deletion ceremony there
    is no client keybar to source ``options`` from, so callers (currently
    only this sensor's own mutation-validated tests) must supply the
    declared-binding universe explicitly.

    :param options: Declared bindings to judge, as ``(anchor, surface, key,
        file, line)`` rows.
    :param exercised: Anchors the authored scripts exercise (defaults to the
        live ``babylon.game`` scan; injectable).
    :param exemptions: Declared exemption rows (injectable).
    :returns: Sorted agent-legible finding strings (empty when every option is
        covered or exempted).
    :raises SentinelCheckError: If a scanned file is missing or unparseable.
    """
    live_exercised = _exercised_anchors() if exercised is None else exercised
    findings: list[str] = []
    for anchor, surface, key, file, line in options:
        if anchor in live_exercised:
            continue
        if is_exempt(("binding", surface, key), exemptions):
            continue
        findings.append(
            finding(
                error_class="tutorial-option-uncovered",
                symbol=anchor,
                file=file,
                line=line,
                problem=(
                    f"the {surface} keybar's {key!r} hint is a real player-facing "
                    "option with no TutorialStep exercising it and no cited exemption"
                ),
                remedy=(
                    "either author a TutorialStep whose anchor is "
                    f"{anchor!r} (ai/_inbox/t6-tutorial-bdd-ruling.md) or add a dated "
                    "SentinelExemption to "
                    "babylon.sentinels.tutorial_coverage.registry."
                    "TUTORIAL_COVERAGE_EXEMPTIONS keyed "
                    f'("binding", {surface!r}, {key!r})'
                ),
            )
        )
    return sorted(findings)


def check_every_exemption_still_names_a_real_binding(
    options: tuple[tuple[str, str, str, str, int], ...],
    exemptions: tuple[SentinelExemption, ...] = TUTORIAL_COVERAGE_EXEMPTIONS,
) -> list[str]:
    """Every declared exemption's key still names a currently-declared binding.

    The dual of :func:`check_every_binding_covered_or_exempted` -- an
    exemption whose binding was renamed or removed is dead weight that would
    silently mask a FUTURE binding coincidentally reusing the same class/key
    (:mod:`babylon.sentinels.exemptions`'s own exact-tuple-match design does
    not protect against a stale row being *reused* by a new, unrelated finding
    unless something keeps the registry honest against the live source).

    No live default (see the module docstring's RETAINED_CONTENT_ONLY note):
    callers must supply ``options`` explicitly.

    :param options: Declared bindings, as ``(anchor, surface, key, file,
        line)`` rows.
    :param exemptions: Declared exemption rows (injectable).
    :returns: Sorted agent-legible finding strings for exemptions with no
        matching live hint row (empty when every exemption is still grounded).
    """
    live_keys = {(surface, key) for _anchor, surface, key, _file, _line in options}
    findings: list[str] = []
    for exemption in exemptions:
        if exemption.key[0] != "binding" or len(exemption.key) != 3:
            continue
        _kind, surface, key = exemption.key
        if (surface, key) in live_keys:
            continue
        findings.append(
            finding(
                error_class="tutorial-exemption-stale",
                symbol=".".join(exemption.key),
                file="src/babylon/sentinels/tutorial_coverage/registry.py",
                line=0,
                problem=(
                    f"exemption keyed {exemption.key!r} names no currently-declared "
                    f"{surface} keybar hint for key {key!r}"
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
    return (
        "TUTORIAL-COVERAGE: no live option universe since the Ratatui client's "
        "deletion (Amendment AF / ADR186) — the reconciliation algorithm is "
        "RETAINED_CONTENT_ONLY, exercised by tests/unit/sentinels/"
        "test_tutorial_coverage.py; nothing live to gate until a future "
        "client wires its own option surface back in"
    )


#: Deliberately empty: no live option universe to gate against since the
#: Ratatui client's keybar was deleted (Amendment AF / ADR186) — see the
#: module docstring. A green run here is honest ("nothing live to check"),
#: not a claim of coverage.
_GATING: tuple[LabelledCheck, ...] = ()


def main(argv: list[str] | None = None) -> int:
    """CLI entry point -- ``tools/sentinel_check.py tutorial-coverage [--check]``.

    :param argv: Forwarded CLI args (``--check`` is accepted for the
        dispatcher's uniform contract).
    :returns: 0 clean (always, today -- :data:`_GATING` is empty), 2
        infrastructure failure.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="CI mode (no-op alias)")
    parser.parse_args(argv)
    return run_sensor("TUTORIAL-COVERAGE", _GATING, (), _summary, scope=SCOPE_NOT_DECLARED)


if __name__ == "__main__":
    sys.exit(main())
