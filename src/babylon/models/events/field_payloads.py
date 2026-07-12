"""Feature-002 contradiction-field event payloads.

Mirrors the ``payload={...}`` dict built at its publish site in
:class:`babylon.engine.systems.field_derivative.FieldDerivativeSystem`. The
:class:`~babylon.models.events._legacy.SimulationEvent` base owns the
common ``event_type`` + ``tick`` + ``timestamp`` fields.
"""

from __future__ import annotations

from pydantic import Field

from babylon.models.enums import EventType
from babylon.models.events._legacy import SimulationEvent


class PrincipalContradictionShiftEvent(SimulationEvent):
    """PRINCIPAL_CONTRADICTION_SHIFT event payload (field_derivative.py:362-373).

    Emitted when the field with the largest |df/dt| (the "principal
    field") changes from the previous tick.
    """

    event_type: EventType = Field(default=EventType.PRINCIPAL_CONTRADICTION_SHIFT)
    previous_field: str | None = None
    new_field: str
    max_abs_df_dt: float


__all__ = [
    "PrincipalContradictionShiftEvent",
]
