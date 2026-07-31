"""Shared apparatus for the ``babylon.sentinels`` family.

A **Sentinel** is Babylon's reusable enforcement pattern: a *declared-invariant
registry* + *loud static/dynamic checks* + *mutation-tested efficacy* that
*grows with the codebase*. The seam-coverage gate (``babylon.sentinels.seam``)
is instance #1; determinism and round-trip conservation are its siblings. This
module holds what every sentinel reuses — the infrastructure-failure error type
and the two-tier (gating / advisory) check runner with its exit-code contract —
so a new sensor is a registry + a handful of check functions, nothing more.

Dependency-light **by design** (layer 0.5, same rank as :mod:`babylon.config`):
importable by ``engine``, ``domain``, ``web.game.*`` and ``tools/*`` alike;
imports nothing above :mod:`babylon.models`. The boundary is enforced by an
import-linter contract in ``pyproject.toml``.
"""

from __future__ import annotations

import sys
from collections.abc import Callable

#: A single check: returns its violation/finding strings (empty == clean).
Check = Callable[[], list[str]]

#: ``(human-readable label, check)`` pairs, the unit a runner iterates.
LabelledCheck = tuple[str, Check]

#: Passed as ``scope=`` by a sensor that has not yet stated what it does and
#: does not examine.
#:
#: A clean sentinel prints a count — ``"2 declared store(s)"``, ``"0 of 1
#: declared computed field(s)"`` — and a reader naturally infers *coverage*
#: from it. For a registry-scoped sensor that inference is wrong: the count is
#: the size of the hand-curated watch list, not the size of the population.
#: The anti-cry-wolf design that keeps those lists closed is correct; the
#: reporting is what misleads.
#:
#: So :func:`run_sensor` requires every sensor to say what its result covers,
#: and this sentinel is the honest answer for one that has not been audited
#: yet. It prints a loud undeclared-scope line rather than a plausible-sounding
#: claim — the omission is visible instead of silent, which is III.11's Loud
#: Failure applied to the gates themselves. Replacing one of these with a real
#: sentence requires *reading* that sensor; guessing would re-create the exact
#: defect this exists to fix.
SCOPE_NOT_DECLARED = "\x00undeclared\x00"


class SentinelCheckError(RuntimeError):
    """A sensor could not run — source missing or unparseable (exit 2, not 1).

    Distinguishes *infrastructure* failure (the gate itself is broken) from a
    *coverage* violation (the gate works and found drift). Both are loud
    (Constitution III.11); only the latter is fixed by editing registry rows.
    """


def run_sensor(
    name: str,
    gating: tuple[LabelledCheck, ...],
    advisory: tuple[LabelledCheck, ...],
    summary: Callable[[int], str],
    *,
    scope: str,
) -> int:
    """Run a sentinel's two check tiers and return its process exit code.

    Gating findings red the build (exit 1); advisory findings print loudly but
    never gate; a :class:`SentinelCheckError` from any check is an
    infrastructure failure (exit 2) — never swallowed into a false pass.

    :param name: The sentinel's short uppercase tag (e.g. ``"SEAM"``); prefixes
        every emitted line (``"{name} VIOLATION [...]"`` / ``"{name} ADVISORY
        [...]"`` / ``"{name} ERROR: ..."``).
    :param gating: Ordered gating checks; any non-empty result reds the gate.
    :param advisory: Ordered advisory checks; results print but do not gate.
    :param summary: Called with the advisory-finding count to build the clean
        one-line summary printed to stdout when no gating violation occurred.
    :param scope: What a clean result here does and does not cover, printed
        beneath the summary. Keyword-only and **required**: a green sentinel is
        read as evidence of coverage, and for a registry-scoped sensor that
        reading is wrong, so stating the bound is not optional. Pass
        :data:`SCOPE_NOT_DECLARED` for a sensor not yet audited — it prints a
        loud undeclared line rather than a claim nobody checked.
    :returns: 0 clean, 1 gating violations found, 2 infrastructure failure.
    """
    exit_code = 0
    try:
        for label, check in gating:
            for violation in check():
                print(f"{name} VIOLATION [{label}]: {violation}", file=sys.stderr)
                exit_code = 1
        advisory_count = 0
        for label, check in advisory:
            for finding in check():
                print(f"{name} ADVISORY [{label}]: {finding}", file=sys.stderr)
                advisory_count += 1
    except SentinelCheckError as exc:
        print(f"{name} ERROR: {exc}", file=sys.stderr)
        return 2

    if exit_code == 0:
        print(summary(advisory_count))
        if scope == SCOPE_NOT_DECLARED:
            print(
                f"{name} SCOPE: NOT DECLARED — this sensor has not stated what it "
                "does and does not examine, so the clean line above is not "
                "evidence of coverage."
            )
        else:
            print(f"{name} SCOPE: {scope}")
    return exit_code
