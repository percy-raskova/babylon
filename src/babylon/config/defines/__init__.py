"""Game defines for centralized coefficient configuration.

This package provides the :class:`GameDefines` model which extracts
hardcoded values from systems into a single, configurable location.

Spec 058 (Bundle 1, FR-002): the historical ``babylon.config.defines``
monolith was split into a 12-sub-module package; the flat-import paths
(``from babylon.config.defines import X``) continue to resolve via the
re-exports below.
"""

from __future__ import annotations

from babylon.config.defines._assembler import GameDefines
from babylon.config.defines.consciousness import (
    BifurcationDefines,
    ConsciousnessDefines,
    ContradictionFieldDefines,
    EdgeTransitionDefines,
    SolidarityDefines,
)
from babylon.config.defines.doctrine import DoctrineDefines
from babylon.config.defines.economy_basic import (
    CrisisDefines,
    EconomyDefines,
    LeontiefRentDefines,
)
from babylon.config.defines.economy_class import (
    ClassDynamicsDefines,
    ClassSystemDefines,
    RentCircuitDefines,
)
from babylon.config.defines.economy_labor import (
    DispossessionDefines,
    ReserveArmyDefines,
    WorkingDayDefines,
)
from babylon.config.defines.endgame import (
    EndgameDefines,
    InitialDefines,
)
from babylon.config.defines.epistemic_horizon import EpistemicHorizonDefines
from babylon.config.defines.external_data import (
    ArcGISDefines,
    ExternalDataDefines,
    ServicesDefines,
)
from babylon.config.defines.ooda import OODADefines
from babylon.config.defines.organizations import (
    CommunityDefines,
    LifecycleDefines,
    MobilizeDefines,
    MoveDefines,
    NegotiateDefines,
    OrganizationDefines,
)
from babylon.config.defines.reactionary import ReactionaryDefines
from babylon.config.defines.state_apparatus import (
    InstitutionDefines,
    StateApparatusAIDefines,
)
from babylon.config.defines.survival import (
    AidDefines,
    BehavioralDefines,
    StruggleDefines,
    SurvivalDefines,
    TensionDefines,
    VitalityDefines,
)
from babylon.config.defines.territory import (
    CarceralDefines,
    InfrastructureDefines,
    InfraTerrainDefines,
    MetabolismDefines,
    TerritoryDefines,
    TopologyDefines,
)
from babylon.config.defines.tunables import (
    PrecisionDefines,
    TimescaleDefines,
)

__all__ = [
    "AidDefines",
    "ArcGISDefines",
    "BehavioralDefines",
    "BifurcationDefines",
    "CarceralDefines",
    "ClassDynamicsDefines",
    "ClassSystemDefines",
    "CommunityDefines",
    "ConsciousnessDefines",
    "ContradictionFieldDefines",
    "CrisisDefines",
    "DispossessionDefines",
    "EconomyDefines",
    "EdgeTransitionDefines",
    "EndgameDefines",
    "DoctrineDefines",
    "EpistemicHorizonDefines",
    "ExternalDataDefines",
    "GameDefines",
    "InfraTerrainDefines",
    "InfrastructureDefines",
    "InitialDefines",
    "InstitutionDefines",
    "LeontiefRentDefines",
    "LifecycleDefines",
    "MetabolismDefines",
    "MobilizeDefines",
    "MoveDefines",
    "NegotiateDefines",
    "OODADefines",
    "OrganizationDefines",
    "PrecisionDefines",
    "ReactionaryDefines",
    "RentCircuitDefines",
    "ReserveArmyDefines",
    "ServicesDefines",
    "SolidarityDefines",
    "StateApparatusAIDefines",
    "StruggleDefines",
    "SurvivalDefines",
    "TensionDefines",
    "TerritoryDefines",
    "TimescaleDefines",
    "TopologyDefines",
    "VitalityDefines",
    "WorkingDayDefines",
]
