"""Unconsumed sentinel: a declared computed value must have a real reader.

Instance of the Sentinel pattern guarding a failure mode distinct from
:mod:`babylon.sentinels.inert` (2026-07-18 audit): a producer FUNCTION can
have a real, non-test production caller (satisfying the inert sentinel's own
rule) while the VALUE it returns is written once and read by nothing —
computed, stored, dead. Registry = the hand-curated computed-field rows plus
the dated exemption list; checks = one static AST rule (every declared dict
key has >=1 non-test production read site).

Founding incident: :func:`~babylon.formulas.consciousness_routing.
compute_reification_buffer` is called every tick from
``engine/systems/ideology.py::ConsciousnessSystem.step`` and its result is
written onto ``material_conditions["reification_buffer"]`` — a real,
reachable producer. Nothing downstream ever reads that key back.
"""

from babylon.sentinels.unconsumed.checks import (
    computed_fields_without_consumer,
    is_test_source,
    reader_sites,
)
from babylon.sentinels.unconsumed.registry import (
    DECLARED_COMPUTED_FIELDS,
    PRODUCTION_ROOTS,
    UNCONSUMED_EXEMPTIONS,
    DeclaredComputedField,
    UnconsumedExemption,
)

__all__ = [
    "DECLARED_COMPUTED_FIELDS",
    "PRODUCTION_ROOTS",
    "UNCONSUMED_EXEMPTIONS",
    "DeclaredComputedField",
    "UnconsumedExemption",
    "computed_fields_without_consumer",
    "is_test_source",
    "reader_sites",
]
