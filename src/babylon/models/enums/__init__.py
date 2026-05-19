"""Enumeration types for the Babylon simulation.

These StrEnums define the categorical types used throughout the
simulation. All values are lowercase snake_case for JSON serialization
compatibility. The classes are organized into themed sub-modules per
Spec 058 (Bundle 1, FR-001); the historical flat-import paths
(``from babylon.models.enums import X``) continue to resolve via the
re-exports below.

See ``specs/058-adr-bundle-1-pre-spec-057/`` for the categorization
rationale and the Q2 clarification on the public-import surface.
"""

from __future__ import annotations

from babylon.models.enums._resolution import resolve_edge_type
from babylon.models.enums.actions import (
    ActionType,
    DecisionMode,
)
from babylon.models.enums.balkanization import (
    ClaimLegalStatus,
    ColonialStance,
    ExtractionPolicy,
    FiscalStatus,
    PlayerMode,
    SovereigntyType,
    SupportType,
)
from babylon.models.enums.community import (
    CommunityType,
    HyperedgeCategory,
)
from babylon.models.enums.consciousness import (
    ConsciousnessTendency,
    ContradictionCharacter,
    ContradictionType,
    IntensityLevel,
)
from babylon.models.enums.events import (
    EventType,
    GameOutcome,
    ResolutionType,
)
from babylon.models.enums.legal import (
    DispossessionType,
    ExploitationMode,
    JurisdictionLevel,
    LegalStanding,
    LegalStatus,
    LegitimationClassification,
)
from babylon.models.enums.organizations import (
    ApparatusType,
    InternetResponseMode,
    LifecyclePhase,
    ServiceType,
    StateActionType,
    StateFaction,
    SurveillanceMethod,
    ThreadPhase,
)
from babylon.models.enums.social import (
    ClassCharacter,
    ClassInscription,
    MembershipRole,
    OrgType,
    RulingClassFraction,
    SocialFunction,
    SocialRole,
)
from babylon.models.enums.territory import (
    BiocapacityType,
    DisplacementPriorityMode,
    LocalityClass,
    OperationalProfile,
    SectorType,
    TerrainType,
    TerritoryType,
)
from babylon.models.enums.topology import (
    EdgeMode,
    EdgeType,
    FlowCategory,
    InfrastructureType,
    JunctionType,
    TopologyType,
)

__all__ = [
    "ActionType",
    "ApparatusType",
    "BiocapacityType",
    "ClaimLegalStatus",
    "ClassCharacter",
    "ClassInscription",
    "ColonialStance",
    "CommunityType",
    "ConsciousnessTendency",
    "ContradictionCharacter",
    "ContradictionType",
    "DecisionMode",
    "DisplacementPriorityMode",
    "DispossessionType",
    "EdgeMode",
    "EdgeType",
    "EventType",
    "ExploitationMode",
    "ExtractionPolicy",
    "FiscalStatus",
    "FlowCategory",
    "GameOutcome",
    "HyperedgeCategory",
    "InfrastructureType",
    "IntensityLevel",
    "InternetResponseMode",
    "JunctionType",
    "JurisdictionLevel",
    "LegalStanding",
    "LegalStatus",
    "LegitimationClassification",
    "LifecyclePhase",
    "LocalityClass",
    "MembershipRole",
    "OperationalProfile",
    "OrgType",
    "PlayerMode",
    "ResolutionType",
    "RulingClassFraction",
    "SectorType",
    "ServiceType",
    "SocialFunction",
    "SocialRole",
    "SovereigntyType",
    "StateActionType",
    "StateFaction",
    "SupportType",
    "SurveillanceMethod",
    "TerrainType",
    "TerritoryType",
    "ThreadPhase",
    "TopologyType",
    "resolve_edge_type",
]
