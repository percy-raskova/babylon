"""The tutorial option-coverage sentinel — every player-facing option is taught.

Per ``ai/_inbox/t6-tutorial-bdd-ruling.md`` (BD, 2026-07-21): the tutorial IS
the BDD acceptance suite, and "an option with no scenario is a seam" — this
sensor makes that a gate. From the M7 cutover until the Amendment AF
(ADR186) deletion ceremony the option universe was the Rust/Ratatui
client's keybar hint tables, read as text by the now-deleted
``babylon.sentinels._rust.declared_keybar_hints``.

**RETAINED_CONTENT_ONLY (ADR186 sentinel disposition table):** the keybar is
gone, so this sensor has no live option universe to gate today —
:func:`~babylon.sentinels.tutorial_coverage.checks.
check_every_binding_covered_or_exempted` and
:func:`~babylon.sentinels.tutorial_coverage.checks.
check_every_exemption_still_names_a_real_binding` survive as a tested
reconciliation algorithm (declared options vs. exercised anchors vs.
exemptions), exercised only via explicit arguments
(``tests/unit/sentinels/test_tutorial_coverage.py``); the gating tuple is
empty until a future client wires its own option surface back in. See
``checks.py``'s module docstring for the full account.

Gating and local/on-demand:
``uv run python tools/sentinel_check.py tutorial-coverage --check``.

Layer 0.5: reads ``babylon.game`` statically via :mod:`ast`.
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
