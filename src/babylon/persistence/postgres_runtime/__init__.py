"""PostgresRuntime package — Spec 059 US1 / ADR-005 Part A.

Replaces the historical 2094-LOC ``persistence/postgres_runtime.py`` single
file with a package whose ``__init__.py`` re-exports the ``PostgresRuntime``
class and its public surface unchanged. The original implementation lives at
``_legacy.py`` while the content split into focused IO sub-components
(``_pool.py`` / ``tick_io.py`` / ``archival_io.py`` / ``spatial_io.py`` /
``community_io.py`` / ``trace_io.py`` per data-model.md §2.1) is deferred to
a follow-up commit — preserving byte-equality and import equivalence trumps
SC-002's per-file LOC budget for this commit.

Import equivalence (FR-003 / contracts/import-equivalence.md C1): every
existing ``from babylon.persistence import PostgresRuntime`` and
``from babylon.persistence.postgres_runtime import …`` resolves unchanged
via this re-export.

Protocol satisfaction (contracts/protocol-satisfaction.md P1): the facade
continues to satisfy both ``RuntimePersistence`` and
``PostgresRuntimeExtensions``.
"""

from __future__ import annotations

from babylon.persistence.postgres_runtime._legacy import PostgresRuntime

__all__ = ["PostgresRuntime"]
