"""The tutorial option-coverage sentinel — every player-facing option is taught.

Per ``ai/_inbox/t6-tutorial-bdd-ruling.md`` (BD, 2026-07-21): the tutorial IS
the BDD acceptance suite, and "an option with no scenario is a seam" — this
sensor makes that a gate. Since the M7 cutover (§5.5 of the M7 contracts) the
option universe is the Rust keybar's hint tables
(``rust/crates/babylon-tui/src/views/keybar.rs``, read as text by
:func:`babylon.sentinels._rust.declared_keybar_hints`): every ``(surface,
key)`` hint row must be exercised by an authored
:class:`~babylon.game.tutorial.TutorialStep` or carry a cited
:class:`~babylon.sentinels.exemptions.SentinelExemption` — and the universe
itself gates on a floor, so a broken extractor reads RED, never vacuously
green.

Gating and local/on-demand:
``uv run python tools/sentinel_check.py tutorial-coverage --check``.

Layer 0.5: reads ``babylon.game`` statically via :mod:`ast` and the keybar
via text — it may not import ``babylon.tui`` (import-linter contract,
``pyproject.toml``).
"""

from babylon.sentinels.tutorial_coverage.checks import (
    check_every_binding_covered_or_exempted,
    check_every_exemption_still_names_a_real_binding,
    check_option_universe_floor,
    main,
)

__all__ = [
    "check_every_binding_covered_or_exempted",
    "check_every_exemption_still_names_a_real_binding",
    "check_option_universe_floor",
    "main",
]
