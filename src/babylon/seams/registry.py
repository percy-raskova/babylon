"""The single declared source of truth for player-observable seam quantities.

Every quantity that crosses the engine → web-bridge → frontend seam is declared
here as one :class:`~babylon.seams.types.SeamEntry`. The sensors in
``tools/seam_*_check.py`` diff reality against this tuple and fail loudly when
something is computed-but-unserialized, serialized-but-unregistered,
serialized-but-unrendered, or classified dishonestly.

The registry grows with the codebase: Sensor 1, wired into the always-on dev
fast-gate, fails any newly-serialized wire key until a row is added here with a
deliberate liveness ruling. That forcing function is the "mutant" growth
mechanism — the registry cannot silently rot because adding an observable
without declaring it breaks the build.

Rows are added phase by phase (see the build plan). This literal is intentionally
hand-written, not generated: it is a dev-time contract, not player-moddable
runtime config, so it carries no round-trip/regeneration machinery.
"""

from __future__ import annotations

from babylon.seams.types import SeamEntry

#: The declared observable-field contract. Populated per build phase.
SEAM_REGISTRY: tuple[SeamEntry, ...] = ()
