"""Conformance vector PINNING the D-1 scaled-`Int` workaround's numeric
DEVIATION from the frozen engine (F1 fix round, adversarial review of PR
#501). Earlier revisions of ``metabolism.bsl``'s D-1 claimed the workaround
"preserves the formula's exact value ... for ANY legal (1.0, 3.0] modded
value" -- FALSE, proven by execution: the frozen engine computes
``raw_extraction * entropy_factor`` as ONE binary64 multiply; this pack
computes ``(raw_extraction * entropy_factor_x1e6) / 1000000`` -- an exact
integer multiply followed by a correctly-rounded division. These are the
SAME real-valued function but DIFFERENT floating-point programs, and can
round to adjacent doubles (double rounding). See ``metabolism.bsl``'s own
(rewritten) D-1 for the full derivation of both error sources (grid
quantization, dominant for an arbitrary modded value; double rounding, the
residual even at zero quantization error).

This script prints TWO values for the same territory:

1. The FROZEN ENGINE's value -- ``MetabolismSystem().step()``, unmodified.
2. This pack's value, computed by a PURE-PYTHON REPLICA of
   ``metabolism.bsl``'s own binding chain (``bsl_biocapacity_update``
   below) -- every binding, in the SAME order, on `float` (IEEE-754
   binary64, identical to Rust's `f64`). Because both languages implement
   IEEE-754 basic operations identically (`+ - * /`, correctly rounded --
   ``bsl-language.rst`` §4.3), this replica's output is BIT-IDENTICAL to
   what the real Rust engine computes for the same scenario -- confirmed
   directly against ``rust/crates/babylon-tick``'s own build during
   authoring (both print ``1.4`` / ``0x3ff6666666666666`` for
   ``biocapacity``), which is why
   ``metabolism_rounding_divergence_conformance.rs`` can pin the SAME
   numbers this script prints without needing an FFI bridge into the Rust
   engine.

``biocapacity=3`` is the SMALLEST int-seedable ``TERRITORY.biocapacity``
value (with ``extraction_intensity=1`` and the shipped default
``entropy_factor=1.2``, so grid-quantization error is exactly ZERO here --
`1200000 / 1e6 == 1.2` exactly as a real number) that demonstrates the
double-rounding residual: the two engines diverge by exactly 2 ULP.

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" uv run python \\
        rust/crates/babylon-tick/content/scenarios/metabolism_rounding_divergence_conformance.py
"""

from __future__ import annotations

import struct

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.metabolism import MetabolismSystem
from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph

SUBJECT_ID = "divergent-county"
SEED = {
    "biocapacity": 3.0,
    "max_biocapacity": 100.0,
    "extraction_intensity": 1.0,
    "regeneration_rate": 0.02,
}
#: The exact integer `metabolism.bsl`'s `entropy-factor-x1e6` const carries
#: -- the shipped default `entropy_factor=1.2`, `x1,000,000`.
ENTROPY_FACTOR_X1E6 = 1_200_000


def hexf(value: float) -> str:
    """Big-endian hex dump of a float64's bit pattern, matching Rust's `{:016x}`."""
    return struct.pack(">d", value).hex()


def bsl_biocapacity_update(
    current: float,
    max_cap: float,
    extraction_intensity: float,
    regeneration_rate: float,
    entropy_factor_x1e6: int,
    hysteresis_rate: float,
) -> tuple[float, float]:
    """A pure-Python replica of `metabolism.bsl`'s own binding chain, in
    DECLARATION ORDER, on `float` (binary64) throughout -- see the module
    docstring for why this is bit-identical to the real Rust engine.
    """
    regeneration_raw = regeneration_rate * max_cap
    regeneration = 0.0 if current >= max_cap else regeneration_raw
    raw_extraction = (extraction_intensity * current) + 0.0
    ecological_cost_scaled = raw_extraction * entropy_factor_x1e6
    ecological_cost = ecological_cost_scaled / 1_000_000
    delta = regeneration - ecological_cost
    damage = raw_extraction * hysteresis_rate
    max_cap_minus_damage = max_cap - damage
    new_max = max_cap_minus_damage if max_cap_minus_damage > 0 else 0.0
    current_plus_delta = current + delta
    capped_at_ceiling = current_plus_delta if current_plus_delta < new_max else new_max
    new_biocapacity = capped_at_ceiling if capped_at_ceiling > 0 else 0.0
    return new_biocapacity, new_max


def build_graph() -> BabylonGraph:
    """Build the one-territory world."""
    graph = BabylonGraph()
    graph.add_node(SUBJECT_ID, NodeType.TERRITORY, **SEED)
    return graph


def main() -> None:
    """Run the frozen engine AND the pure-Python BSL replica, print both."""
    services = ServiceContainer.create()
    try:
        graph = build_graph()
        MetabolismSystem().step(graph, services, TickContext(tick=1))
        node = graph.get_node(SUBJECT_ID)
        if node is None:
            raise SystemExit(f"node {SUBJECT_ID} vanished during the tick")
        a = node.attributes
        frozen_bio = float(a["biocapacity"])
        frozen_max = float(a["max_biocapacity"])

        bsl_bio, bsl_max = bsl_biocapacity_update(
            SEED["biocapacity"],
            SEED["max_biocapacity"],
            SEED["extraction_intensity"],
            SEED["regeneration_rate"],
            ENTROPY_FACTOR_X1E6,
            0.005,
        )

        print("frozen engine (MetabolismSystem.step, unmodified):")
        print(f"  biocapacity     = {frozen_bio!r}  {hexf(frozen_bio)}")
        print(f"  max_biocapacity = {frozen_max!r}  {hexf(frozen_max)}")
        print()
        print("this pack's value (pure-Python replica of metabolism.bsl):")
        print(f"  biocapacity     = {bsl_bio!r}  {hexf(bsl_bio)}")
        print(f"  max_biocapacity = {bsl_max!r}  {hexf(bsl_max)}")
        print()
        print(f"biocapacity equal:     {frozen_bio == bsl_bio}")
        print(f"max_biocapacity equal: {frozen_max == bsl_max}")
    finally:
        services.database.close()


if __name__ == "__main__":
    main()
