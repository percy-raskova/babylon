"""Simulation package — Spec 059 US1 / ADR-005 Part B.

Replaces the historical 1048-LOC ``engine/simulation.py`` single file with a
package whose ``__init__.py`` re-exports the ``Simulation`` class and its
public surface unchanged. The original implementation lives at ``_legacy.py``
while the content split into focused sub-components (``orchestrator.py`` /
``observer_dispatch.py`` / ``lifecycle.py`` / ``error_recovery.py`` per
data-model.md §2.2) is deferred to a follow-up commit — preserving
byte-equality and import equivalence trumps SC-002's per-file LOC budget for
this commit.

Import equivalence (FR-003 / contracts/import-equivalence.md C2): every
existing ``from babylon.engine import Simulation`` (via the engine package's
PEP 562 ``__getattr__``) and ``from babylon.engine.simulation import …``
resolves unchanged via this re-export.

Public API (contracts/protocol-satisfaction.md P2): the facade preserves the
18 public methods captured at pre-Bundle-2 baseline in
``reports/simulation-public-methods-before.txt``.
"""

from __future__ import annotations

from babylon.engine.simulation._legacy import Simulation

__all__ = ["Simulation"]
