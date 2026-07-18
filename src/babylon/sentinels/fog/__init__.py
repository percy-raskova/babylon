"""Fog-containment sentinel: no political field escapes an out-of-reach mask.

Instance of the Sentinel pattern guarding Constitution Article VIII.12
("silent no-op / disarmed guardrail") applied to the political layer: for
any node outside the player's organizing reach with no ledger coverage,
every ``POLITICAL_FIELDS``/``ORG_POLITICAL_FIELDS`` member must be masked to
``None`` by :func:`game.fog.filter.apply_fog` — a Hypothesis property test
(hundreds of generated ``(field-subset, arbitrary-value, node-id)`` cases
per run) verifies this holds across shapes no hand-written example would
think to try. Only the declared exemption list lives in this layer-0.5
package; the property test itself (needs ``game.fog.filter``, a ``web.*``
module) lives in ``tools/fog_containment_probe.py`` — see that module's and
this package's ``registry`` module docstrings.
"""

from babylon.sentinels.fog.registry import (
    FOG_CONTAINMENT_EXEMPTIONS,
    FogContainmentExemption,
)

__all__ = ["FOG_CONTAINMENT_EXEMPTIONS", "FogContainmentExemption"]
