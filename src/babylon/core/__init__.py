"""Core cross-cutting primitives shared by all subsystems.

Spec 058 (Bundle 1): introduces :mod:`babylon.core.protocol_kit` providing
``DataSource``, ``CachedSource[T]``, and ``SourceRegistry`` — the standardized
scaffolding for the project's pervasive Protocol + ``Default*`` data-source
pattern.

Per ADR-002 § "Negative / tradeoffs": the ``core/`` package is intentionally
narrow — additions require an ADR, to prevent it from becoming a junk drawer.
"""
