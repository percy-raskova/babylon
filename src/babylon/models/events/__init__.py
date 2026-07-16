"""Events package — Spec 059 US2 / ADR-004 (FR-007).

Replaces the historical 1119-LOC ``models/events.py`` single file with a
package whose ``__init__.py`` re-exports the full public surface unchanged.
The original implementation lives at ``_legacy.py`` while the content split
into thematic sub-files (``_base.py`` / ``economic.py`` / ``consciousness.py``
/ ``struggle.py`` / ``contradiction.py`` / ``topology.py`` / ``system.py`` per
data-model.md §2.3) is deferred to a follow-up — preserving byte-equality
and import equivalence trumps SC-002's per-file LOC budget for this commit.

Import equivalence (FR-003 / contracts/import-equivalence.md C3): every
existing ``from babylon.models.events import X`` resolves unchanged via this
re-export.

Discriminated union (Spec 059 US2 / ADR-004): the leaf variants now carry a
``kind: Literal["..."]`` field; ``TickEvent = Annotated[Union[...],
Field(discriminator="kind")]`` enables Pydantic discriminator dispatch.
``deserialize_event`` was DELETED in Spec 059 US2 (FR-006 / SC-003). Callers
use ``TickEventAdapter.validate_python(data)`` directly. Legacy callers
deserializing events without a ``kind`` field should inject it from
``event_type`` first — see ``babylon.models.world_state._validate_event``.
"""

from __future__ import annotations

from babylon.models.events._legacy import (
    EVENT_CLASS_MAP,
    AxiomViolationEvent,
    BifurcationTendencyEvent,
    ClassDecompositionEvent,
    ConsciousnessEvent,
    ContradictionEvent,
    ControlRatioCrisisEvent,
    CrisisEvent,
    DoctrineEvent,
    DoctrinePurgeFailedEvent,
    DoctrineTrapEscapedEvent,
    DoctrineTrapSprungEvent,
    EconomicEvent,
    EndgameEvent,
    ExtractionEvent,
    MassAwakeningEvent,
    PhaseTransitionEvent,
    PhiHourOutlierEvent,
    QcewCarryForwardEvent,
    RuptureEvent,
    SimulationEvent,
    SolidaritySpikeEvent,
    SparkEvent,
    StruggleEvent,
    SubsidyEvent,
    SuperwageCrisisEvent,
    TerminalDecisionEvent,
    TickEvent,
    TickEventAdapter,
    TopologyEvent,
    TransmissionEvent,
    UprisingEvent,
)
from babylon.models.events.dispossession_payloads import (
    DispossessionCascadeEvent,
    DispossessionEvent,
    EcologicalOvershootEvent,
    ReserveArmyPressureEvent,
    ValueTransferEvent,
)
from babylon.models.events.struggle_payloads import (
    FascistRevanchismEvent,
    PeripheralRevoltEvent,
    PowerVacuumEvent,
    RevolutionaryOffensiveEvent,
    SpontaneousRiotEvent,
)

# deserialize_event was deleted in Spec 059 US2 / FR-006 / SC-003. Use
# TickEventAdapter.validate_python(data) for new code; legacy-data callers
# (events without `kind` field) should inject ``kind`` from ``event_type``
# first — see babylon.models.world_state._validate_event for the canonical
# pattern.

__all__ = [
    # Root + intermediate bases (5 + 1)
    "SimulationEvent",
    "EconomicEvent",
    "ConsciousnessEvent",
    "StruggleEvent",
    "ContradictionEvent",
    "TopologyEvent",
    # 22 leaf variants
    "ExtractionEvent",
    "SubsidyEvent",
    "CrisisEvent",
    "SuperwageCrisisEvent",
    "ClassDecompositionEvent",
    "ControlRatioCrisisEvent",
    "TerminalDecisionEvent",
    "TransmissionEvent",
    "MassAwakeningEvent",
    "SparkEvent",
    "UprisingEvent",
    "SolidaritySpikeEvent",
    "RuptureEvent",
    "PhaseTransitionEvent",
    "BifurcationTendencyEvent",
    "EndgameEvent",
    "AxiomViolationEvent",
    "QcewCarryForwardEvent",
    "PhiHourOutlierEvent",
    # ADR073 Doctrine Tree (Unit 6a)
    "DoctrineEvent",
    "DoctrineTrapSprungEvent",
    "DoctrineTrapEscapedEvent",
    "DoctrinePurgeFailedEvent",
    # Discriminated union machinery
    "TickEvent",
    "TickEventAdapter",
    # Legacy dispatch (kept for backward compat with non-kind data)
    "EVENT_CLASS_MAP",
    # Wave 1 item W1.1 struggle-system payloads (struggle_payloads.py)
    "PowerVacuumEvent",
    "RevolutionaryOffensiveEvent",
    "FascistRevanchismEvent",
    "SpontaneousRiotEvent",
    "PeripheralRevoltEvent",
    # Wave 1 item W1.1 dispossession/reserve-army/metabolism payloads
    # (dispossession_payloads.py)
    "DispossessionEvent",
    "ValueTransferEvent",
    "ReserveArmyPressureEvent",
    "DispossessionCascadeEvent",
    "EcologicalOvershootEvent",
]
