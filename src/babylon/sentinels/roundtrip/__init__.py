"""Round-Trip conservation sentinel — ``WorldState`` ↔ graph fidelity.

Instance #3 of the :mod:`babylon.sentinels` family (after the Seam gate and
Determinism). Its invariant: for a **declared** set of core, round-trip-critical
node fields, ``WorldState.from_graph(state.to_graph())`` conserves every value
byte-for-byte. This is the mechanical guard against the class of bug that once
crashed the canonical run at tick 52 — ``Territory.county_fips`` silently dropped
on reconstruction — and against any future field that stops surviving the round
trip.

The round trip is **known-lossy by design** for transient per-tick attributes
(``tick_*`` / ``flow_*`` graph writes, computed fields, ``institution_relations``
and non-core ``Relationship`` attrs). The sentinel therefore does **not** assert
whole-state equality — that would false-alarm on pre-existing, intentional loss.
Instead :data:`~babylon.sentinels.roundtrip.registry.ROUNDTRIP_REGISTRY` declares
exactly the core material fields that genuinely round-trip today; the check
(``tests/unit/sentinels/test_roundtrip.py``) asserts conservation over that set.

Layer 0.5 (same rank as :mod:`babylon.config`): the *declared registry* lives
here as pure data; the round-trip *logic* — which runs the engine to build a
live ``WorldState`` — lives in the test layer, above the import boundary.
"""

from babylon.sentinels.roundtrip.registry import ROUNDTRIP_REGISTRY, RoundTripField

__all__ = ["ROUNDTRIP_REGISTRY", "RoundTripField"]
