"""The tutorial option-coverage sentinel (static, gating).

Per ``ai/_inbox/t6-tutorial-bdd-ruling.md`` (BD, 2026-07-21): "an option with no
scenario is a seam (∂L boundary node) — red." This sensor is that check made
real. Since the M7 cutover (the Textual estate and its ``BINDINGS`` idiom are
deleted; ``docs/superpowers/specs/2026-07-28-m7-cutover-contracts.md`` §5.5)
the option universe is the RUST client's keybar hint tables
(``rust/crates/babylon-tui/src/views/keybar.rs`` — Wave 1's one source of
truth for player-facing keys, parsed as text by
:func:`babylon.sentinels._rust.declared_keybar_hints`): every ``(surface,
key)`` hint row must be exercised by some authored
:class:`~babylon.game.tutorial.TutorialStep`'s ``anchor``
(``"binding:<Surface>:<key>"`` — :mod:`babylon.game.tutorial`'s own anchor
grammar) or carry a cited
:class:`~babylon.sentinels.exemptions.SentinelExemption` in
:data:`~babylon.sentinels.tutorial_coverage.registry.TUTORIAL_COVERAGE_EXEMPTIONS`.

A companion direction closes the reverse hole (an exemption that no longer
matches any live hint row — the same "declared-but-absent" failure mode
:mod:`babylon.sentinels.coupling` checks for its own registry), and a third
closes the DARK hole this re-architecture itself could open: after the
Textual deletion the old AST scan would have returned zero options and gone
vacuously green, so the extractor now gates on a declared floor
(:data:`_OPTION_FLOOR`) — a shrunken universe is RED, never silently clean
(the standing sentinel-every-error-class rule).

Scope -- STATIC coherence only: reads Python source with :mod:`ast` and Rust
source as text; never imports ``babylon.tui`` or ``babylon.game.tutorial``
(layer 0.5, same rank as every other sentinel).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from babylon.sentinels._ast import tutorial_step_anchors
from babylon.sentinels._rust import declared_keybar_hints
from babylon.sentinels.base import SCOPE_NOT_DECLARED, LabelledCheck, run_sensor
from babylon.sentinels.exemptions import SentinelExemption, is_exempt
from babylon.sentinels.report import finding
from babylon.sentinels.tutorial_coverage.registry import TUTORIAL_COVERAGE_EXEMPTIONS

#: Repo root (this file is ``<root>/src/babylon/sentinels/tutorial_coverage/checks.py``).
_REPO_ROOT: Path = Path(__file__).resolve().parents[4]

#: The Rust keybar source — the one player-facing option table (Wave 1;
#: the keybar and the help screen render from it, so they cannot drift).
_KEYBAR_SOURCE: str = "rust/crates/babylon-tui/src/views/keybar.rs"

#: The dark-extractor floor: the M7 re-key measured 62 live hint rows; a
#: universe below this floor means the extractor lost a whole table (an
#: arm/section rename in keybar.rs), which must read RED, never clean.
_OPTION_FLOOR: int = 40

#: Where authored :class:`~babylon.game.tutorial.TutorialStep` scripts live.
_SCRIPT_SCAN_ROOT: str = "src/babylon/game"


def _scan(root: str) -> list[Path]:
    """List a scan root's Python files, deterministically ordered.

    :param root: Repo-relative directory to scan.
    :returns: Sorted absolute paths.
    """
    return sorted((_REPO_ROOT / root).rglob("*.py"))


def _declared_options(
    keybar_source: str = _KEYBAR_SOURCE,
) -> tuple[tuple[str, str, str, str, int], ...]:
    """Every keybar hint row, as an anchor plus its provenance.

    :param keybar_source: Repo-relative keybar path (injectable for tests).
    :returns: ``(anchor, surface, key, file, line)`` tuples, in source order.
    :raises SentinelCheckError: If the keybar source is missing or parses to
        zero rows (the dark-extractor failure mode).
    """
    options: list[tuple[str, str, str, str, int]] = []
    for surface, key, _label, line in declared_keybar_hints(_REPO_ROOT / keybar_source):
        anchor = f"binding:{surface}:{key}"
        options.append((anchor, surface, key, keybar_source, line))
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


def check_option_universe_floor(
    options: tuple[tuple[str, str, str, str, int], ...] | None = None,
) -> list[str]:
    """The option universe has not gone dark (the vacuous-green dual).

    The M7 re-key's own failure mode: after the Textual deletion the old AST
    scan returned zero declared bindings, so both companion checks passed
    vacuously over a dead gate. A universe below :data:`_OPTION_FLOOR` means
    the extractor lost a whole hint table — RED, never clean.

    :param options: Declared hint rows (defaults to the live scan; injectable).
    :returns: One finding when the universe is below the floor, else empty.
    :raises SentinelCheckError: If the keybar source is missing/unparseable.
    """
    live_options = _declared_options() if options is None else options
    if len(live_options) >= _OPTION_FLOOR:
        return []
    return [
        finding(
            error_class="tutorial-option-universe-dark",
            symbol="declared_keybar_hints",
            file=_KEYBAR_SOURCE,
            line=0,
            problem=(
                f"the keybar extractor yielded only {len(live_options)} option rows "
                f"(floor: {_OPTION_FLOOR}) — the option universe has gone dark, the "
                "coverage checks above it are running vacuously"
            ),
            remedy=(
                "re-align babylon.sentinels._rust.declared_keybar_hints with "
                "keybar.rs's current shapes (hints() arms / GLOBAL_TAIL / "
                "help_sections()), or re-measure and re-declare _OPTION_FLOOR "
                "if the keybar legitimately shrank"
            ),
        )
    ]


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
    :returns: Sorted agent-legible finding strings (empty when every option is
        covered or exempted).
    :raises SentinelCheckError: If a scanned file is missing or unparseable.
    """
    live_options = _declared_options() if options is None else options
    live_exercised = _exercised_anchors() if exercised is None else exercised
    findings: list[str] = []
    for anchor, surface, key, file, line in live_options:
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
        matching live hint row (empty when every exemption is still grounded).
    :raises SentinelCheckError: If a scanned file is missing or unparseable.
    """
    live_options = _declared_options() if options is None else options
    live_keys = {(surface, key) for _anchor, surface, key, _file, _line in live_options}
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
    return "TUTORIAL-COVERAGE: the keybar option universe is live; every hint is covered or exempted; every exemption is grounded"


_GATING: tuple[LabelledCheck, ...] = (
    ("option-universe-floor", check_option_universe_floor),
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
    return run_sensor("TUTORIAL-COVERAGE", _GATING, (), _summary, scope=SCOPE_NOT_DECLARED)


if __name__ == "__main__":
    sys.exit(main())
