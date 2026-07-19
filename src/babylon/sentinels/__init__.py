"""The ``babylon.sentinels`` family — declared-invariant enforcement.

A **Sentinel** is Babylon's reusable pattern for turning a load-bearing engine
invariant into a mechanically-enforced, grows-with-the-codebase gate:

    *declared-invariant registry + loud static/dynamic checks + mutation-tested
    efficacy + a growth mechanism that forces new cases to be declared.*

The seam-coverage gate (:mod:`babylon.sentinels.seam`) is instance #1 — it holds
the engine ↔ web ↔ UI boundary faithful. Its siblings apply the same apparatus
to other earned invariants (determinism of the tick; round-trip conservation of
``WorldState`` ↔ graph). The shared machinery lives here:

- :mod:`babylon.sentinels.base` — :class:`~babylon.sentinels.base.SentinelCheckError`
  and the two-tier (gating / advisory) :func:`~babylon.sentinels.base.run_sensor`
  runner with its 0/1/2 exit-code contract.
- :mod:`babylon.sentinels.exemptions` — the ONE dated, owner-approved
  :class:`~babylon.sentinels.exemptions.SentinelExemption` record and its
  exact-tuple :func:`~babylon.sentinels.exemptions.is_exempt` matcher, used
  by every gate that holds a known finding open (gate-governance ruling,
  2026-07-18) instead of a bespoke per-gate exemption class.
- :mod:`babylon.sentinels._ast` — the static-analysis helpers every sensor reads
  source with (never importing or running the engine).

Layer 0.5 (same rank as :mod:`babylon.config`): importable everywhere below the
engine; imports nothing above :mod:`babylon.models`.
"""

from babylon.sentinels.base import SentinelCheckError, run_sensor
from babylon.sentinels.exemptions import SentinelExemption, is_exempt, stale_exemptions

__all__ = [
    "SentinelCheckError",
    "SentinelExemption",
    "is_exempt",
    "run_sensor",
    "stale_exemptions",
]
