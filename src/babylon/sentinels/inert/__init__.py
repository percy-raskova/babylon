"""Inert sentinel: a declared store/producer must be reachable from production.

Instance of the Sentinel pattern guarding Babylon's dominant failure mode
(2026-07-18 audit: 9 instances of machinery built, tested in isolation, never
connected). Registry = the hand-curated stores/producers plus the dated
exemption list; checks = three static AST rules (every declared store's
writer has a production caller; every declared producer has a production
reference; no undeclared accumulator-shaped class exists).

Founding incident: :class:`~game.fog.ledger.IntelLedger` defines
``append()`` with real, passing unit tests and ZERO production callers — all
13 bridge call sites read the shared frozen ``_EMPTY_INTEL_LEDGER`` constant
instead, so ``read_intel()`` could only ever answer ``"unknown"`` and the
``intel_staleness_ticks``/``intel_unknown_ticks`` coefficients (plus their
``model_validator``) were inert.
"""

from babylon.sentinels.inert.checks import (
    detect_accumulator_classes,
    is_test_source,
    producer_reference_sites,
    producers_without_production_caller,
    store_writer_call_sites,
    stores_without_production_writer,
    undeclared_accumulator_stores,
)
from babylon.sentinels.inert.registry import (
    DECLARED_PRODUCERS,
    DECLARED_STORES,
    INERT_EXEMPTIONS,
    PRODUCTION_ROOTS,
    DeclaredProducer,
    DeclaredStore,
)

__all__ = [
    "DECLARED_PRODUCERS",
    "DECLARED_STORES",
    "INERT_EXEMPTIONS",
    "PRODUCTION_ROOTS",
    "DeclaredProducer",
    "DeclaredStore",
    "detect_accumulator_classes",
    "is_test_source",
    "producer_reference_sites",
    "producers_without_production_caller",
    "store_writer_call_sites",
    "stores_without_production_writer",
    "undeclared_accumulator_stores",
]
