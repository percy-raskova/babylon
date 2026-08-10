"""Chronicle event salience classification (Program 24 P3 WO-48, T1.1 U2).

Relocated from ``babylon.tui.chronicle_salience`` by the Amendment AF
(ADR186) deletion ceremony: that module bundled this classification layer
with dedup/autopause/volume-floor mechanics and a Rich-rendered autopause
indicator, all consumed exclusively by the deleted Ratatui client's host
(``babylon.tui.host``) and its own tests. Only :class:`EventSalience` and
:func:`classify_event_salience` had a consumer outside the deleted client —
:mod:`babylon.game.session` calls :func:`classify_event_salience` directly
(deciding autopause-worthiness for the composition root's own event
handling), independent of any specific client — so only that piece
survives; ``dedupe_consecutive``, ``compute_autopause_state``,
``render_autopause_indicator``, and the volume-floor functions had no
surviving caller and were not carried forward.

**Salience** (T1.1 U2, ``ai/_inbox/t11-seam-severity-design.md``) delegates to
:func:`babylon.models.event_severity.resolve_severity` — U1's single-sourced
kind x terminal_proximity derivation, shared with
``web/game/engine_bridge.py``'s ``_classify_event``. Constitution III.11
("Loud Failure") governs the unclassified case: an unclassified
:class:`~babylon.models.enums.events.EventType` renders at **warning**-tier
visibility, and :attr:`EventSalience.unclassified` is ``True`` so the caller
can visibly mark it (never a silent, indistinguishable "informational").
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from babylon.models.enums.events import EventType
from babylon.models.event_severity import resolve_severity

__all__ = [
    "SeverityTier",
    "EventSalience",
    "classify_event_salience",
]

SeverityTier = Literal["critical", "warning", "informational"]
"""The three-bucket taxonomy (spec-061 FR-012), resolved by
:func:`babylon.models.event_severity.resolve_severity` (T1.1 U1/U2's single
source), not a locally hand-copied dict."""


class EventSalience(BaseModel):
    """One event's resolved tier, plus whether it fell through to the loud floor.

    A thin per-surface adapter over
    :class:`babylon.models.event_severity.EventSeverity` (T1.1 U2): identical
    shape, kept as this module's own type so its public API (and every
    existing caller) is unaffected by the single-sourcing underneath it.

    :param tier: the resolved :data:`SeverityTier`.
    :param unclassified: ``True`` when ``tier`` came from the loud
        unclassified floor (no declared row for this event type) rather than
        a real classification.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    tier: SeverityTier
    unclassified: bool = False


def classify_event_salience(event_type: EventType) -> EventSalience:
    """Resolve ``event_type``'s salience tier.

    T1.1 U2: delegates to :func:`babylon.models.event_severity.resolve_severity`
    — the single-sourced derivation shared with ``web/game/engine_bridge.py``'s
    ``_classify_event`` — so this surface and the web bridge can never
    silently drift apart the way their two hand-copied dicts could.

    Constitution III.11 ("Loud Failure"): an ``event_type`` with no declared
    classification row (any :class:`EventType` added after T1.1, or one of the
    37 never classified) renders at **warning**-tier visibility — never the
    legacy Python bridge's quiet "informational" degrade — with
    :attr:`EventSalience.unclassified` set so callers can visibly mark it.

    :param event_type: the event type to classify.
    :returns: the resolved :class:`EventSalience`.
    """
    severity = resolve_severity(event_type)
    return EventSalience(tier=severity.tier, unclassified=severity.unclassified)
