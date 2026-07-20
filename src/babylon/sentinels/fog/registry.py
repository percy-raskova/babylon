"""Declared invariants of the ``fog`` (containment) sentinel.

The invariant: for any node outside the player's organizing reach, with no
:class:`~game.fog.ledger.IntelLedger` coverage (tier ``"unknown"``), NO
political field's true value may survive ``apply_fog`` — every one must be
masked to ``None``. This is the mechanical core of Constitution Article
VIII.12's "silent no-op / disarmed guardrail" doctrine applied to the
POLITICAL layer specifically: a fog gate that occasionally forgets to mask
one field shape (a list, a nested dict, an empty string, a numeric zero) is
worse than no gate, because every existing example-based test only proves
the shapes someone thought to write.

Why a Hypothesis property, not another example test: the existing suite
(``tests/unit/web/fog/test_filter.py``) already pins ``apply_fog``'s
documented example shapes. This sentinel instead asks Hypothesis to
generate hundreds of ``(field-subset, arbitrary-value, node-id)``
combinations per run and shrink any escape to a minimal reproducer — the
same value proposition golden-trace/property-law layering already gives
the engine's economics, applied here to the fog boundary.

Why the harness lives in ``tools/``, not this package: verifying the
property means calling the REAL ``apply_fog``
(:mod:`game.fog.filter`) — importable without Django (verified: the fog
package is deliberately import-light, no ``babylon.*``/engine dependency),
but still a ``web.game.*`` module layered ABOVE ``babylon.*`` in this
codebase's dependency order. ``babylon.sentinels`` must never depend on
``web`` (only the reverse), so the property test itself lives in
``tools/fog_containment_probe.py`` — this package holds only the
declared exemption list, mirroring every other sentinel's package/harness
split (:mod:`babylon.sentinels.aggregation`, :mod:`babylon.sentinels.
partition`).

Layer 0.5: imports nothing above :mod:`babylon.models`.
"""

from __future__ import annotations

from typing import Final

from babylon.sentinels.exemptions import SentinelExemption

__all__ = ["FOG_CONTAINMENT_EXEMPTIONS"]

#: Deliberately EMPTY: every declared political field is expected to mask
#: cleanly. No field is exempted today. A future row's ``key`` must be
#: ``("political_field", field)`` (gate-governance ruling, 2026-07-18 —
#: replaces the bespoke ``FogContainmentExemption`` class with the
#: family-wide :class:`~babylon.sentinels.exemptions.SentinelExemption`).
FOG_CONTAINMENT_EXEMPTIONS: Final[tuple[SentinelExemption, ...]] = ()
