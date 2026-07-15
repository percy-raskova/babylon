"""The data-coverage sentinel — declared reference-data dependency map.

Babylon's economic tick degrades *silently* when the reference database lacks a
county/year row: the source adapters return a falsy
:class:`~babylon.domain.economics.tensor.NoDataSentinel` and the computation
quietly falls back to a placeholder instead of crashing. This sentinel turns
that silent degradation into a **declared, checked coverage map**: every
computation that depends on reference data must name its requirement in
:data:`~babylon.sentinels.coverage.registry.DATA_REQUIREMENTS`, and each declared
requirement must be *coherent* — it must name a reference-data source class that
actually exists in the code.

**Scope — STATIC coherence only.** The sensor here
(:func:`~babylon.sentinels.coverage.checks.check_source_classes_exist`) proves,
statically via :mod:`ast`, that every declared source class is still defined at
its declared module path. It NEVER reads the 6 GB reference DB and NEVER runs the
engine, so it lives in the always-on dev fast-gate. The complementary *coverage
probe* — does the reference DB actually hold the rows each requirement needs — is
a NIGHTLY concern, shipped later against a Parquet subset, and is explicitly out
of scope for this module.

Layer 0.5 (same rank as :mod:`babylon.config`): imports nothing above
:mod:`babylon.models`. The declared registry is pure data; any check logic that
would need a live source class reads the source file statically instead.
"""
