"""The Seam Observatory — a growable observable-field coverage gate.

Mechanical enforcement of Constitution VIII.12 (no silent no-op / disarmed
guardrail) and III.11 (Loud Failure) across Babylon's engine → web-bridge →
frontend seam. A declared registry of every player-observable quantity, plus
sensors that fail loudly on continuity gaps (Sensor 1), dead liveness
(Sensor 2), and false provenance (Sensor 3), and that force every new
observable into the registry so coverage grows with the codebase.

"Seam Observatory" is the human name for the subsystem; ``babylon.seams`` is the
code package (the frontend already ships an unrelated runtime ``observatory/``
dashboard — specs 096/099 — so the term is not reused in engine code).

Layer 0.5: importable by ``engine``, ``domain``, ``web.game.*`` and ``tools/*``;
imports nothing above :mod:`babylon.models` (enforced by an import-linter
contract in ``pyproject.toml``).
"""

from babylon.seams.registry import SEAM_REGISTRY
from babylon.seams.types import LivenessClass, SeamEntry, SeamScope

__all__ = ["SEAM_REGISTRY", "LivenessClass", "SeamEntry", "SeamScope"]
