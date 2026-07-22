"""The tutorial option-coverage sentinel — every player-facing option is taught.

Per ``ai/_inbox/t6-tutorial-bdd-ruling.md`` (BD, 2026-07-21): the tutorial IS
the BDD acceptance suite, and "an option with no scenario is a seam" — this
sensor makes that a gate. Every class's own declared
:class:`~textual.binding.Binding` in ``babylon.tui``/``babylon.game`` must be
exercised by an authored :class:`~babylon.game.tutorial.TutorialStep` or carry
a cited :class:`~babylon.sentinels.exemptions.SentinelExemption`.

Gating and local/on-demand:
``uv run python tools/sentinel_check.py tutorial-coverage --check``.

Layer 0.5: reads ``babylon.tui``/``babylon.game`` statically via :mod:`ast` —
it may not import them (import-linter contract, ``pyproject.toml``).
"""

from babylon.sentinels.tutorial_coverage.checks import (
    check_every_binding_covered_or_exempted,
    check_every_exemption_still_names_a_real_binding,
    main,
)

__all__ = [
    "check_every_binding_covered_or_exempted",
    "check_every_exemption_still_names_a_real_binding",
    "main",
]
