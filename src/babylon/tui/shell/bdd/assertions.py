"""The three BDD assertion layers (design §G): behavior · render · algebra.

One transcript validates all three: every verb is exercised (coverage), the emitted text is what
the player should see (render), and the state the verbs produced obeys the mathematical-core
property laws (algebra). Determinism uses the v1.0 replay-identity hash; content-hash arrives
with III.13. The algebra layer honors honest-None (III.11): an absent Φ feed is an absence,
never a violation — only present values are law-checked.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from babylon.projection.verbs.preview import CANONICAL_VERBS
from babylon.projection.view_models import EconomyView
from babylon.tui.shell.bdd.harness import TutorialStep


class CoverageError(AssertionError):
    """Layer 1: a canonical verb was never exercised (a dead option = ∂L red gate)."""


class RenderError(AssertionError):
    """Layer 2: the emitted screen text did not contain an expected fragment."""


class InvariantError(AssertionError):
    """Layer 3: an algebraic property law was violated."""


def assert_coverage(steps: Sequence[TutorialStep]) -> None:
    """Layer 1 — every canonical verb appears in the step script."""
    exercised = {step.verb for step in steps}
    missing = sorted(CANONICAL_VERBS - exercised)
    if missing:
        raise CoverageError(f"verbs never exercised (dead options): {missing}")


def assert_render(captured: str, expect: Sequence[str]) -> None:
    """Layer 2 — every expected fragment appears in the captured screen text."""
    for fragment in expect:
        if fragment not in captured:
            raise RenderError(f"expected {fragment!r} in emitted screen text; not found")


def assert_invariants(econ: EconomyView, replay_hashes: Sequence[str]) -> None:
    """Layer 3 — Φ component non-negativity, tri-decomposition closure, hash stability."""
    components = (
        ("phi_unequal_exchange", econ.phi_unequal_exchange),
        ("phi_reproduction", econ.phi_reproduction),
        ("phi_domestic", econ.phi_domestic),
    )
    for name, value in components:
        if value is not None and value < 0:
            raise InvariantError(f"Φ component {name}={value} < 0")
    if econ.phi_decomposition_total is not None:
        present = [value for _, value in components if value is not None]
        if len(present) == len(components):
            expected = sum(present)
            if not math.isclose(econ.phi_decomposition_total, expected, rel_tol=1e-9):
                raise InvariantError(
                    f"Φ closure broken: total={econ.phi_decomposition_total} "
                    f"≠ φ_UE+φ_repro+φ_dom={expected}"
                )
    if len(set(replay_hashes)) > 1:
        raise InvariantError(f"replay-identity hash drifted across run: {list(replay_hashes)}")
