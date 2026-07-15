"""Seam-coverage sentinel — instance #1 of the ``babylon.sentinels`` family.

Mechanical enforcement of Constitution VIII.12 (no silent no-op / disarmed
guardrail) and III.11 (Loud Failure) across Babylon's engine → web-bridge →
frontend seam. A declared registry of every player-observable quantity
(:data:`SEAM_REGISTRY`), plus sensors that fail loudly on continuity gaps
(Sensor 1), dead liveness (Sensor 2), and false provenance (Sensor 3), and that
force every new observable into the registry so coverage grows with the codebase.

"Seam Observatory" is the human name for the subsystem; the code package is
``babylon.sentinels.seam`` (the frontend already ships an unrelated runtime
``observatory/`` dashboard — specs 096/099 — so that term is not reused here).

Layer 0.5: importable by ``engine``, ``domain``, ``web.game.*`` and ``tools/*``;
imports nothing above :mod:`babylon.models` (enforced by an import-linter
contract in ``pyproject.toml``). This package exposes the declared **data**
(registry + types); the static **checks** live in
:mod:`babylon.sentinels.seam.checks` and are run via ``tools/sentinel_check.py``.
"""

from babylon.sentinels.seam.registry import SEAM_REGISTRY
from babylon.sentinels.seam.types import LivenessClass, SeamEntry, SeamScope

__all__ = ["SEAM_REGISTRY", "LivenessClass", "SeamEntry", "SeamScope"]
