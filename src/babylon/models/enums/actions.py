"""Player and state action vocabulary enums (Constitution V).

Spec 058: extracted from the historical ``babylon.models.enums`` monolith.
Re-exported via :mod:`babylon.models.enums.__init__`.
"""

from __future__ import annotations

from enum import StrEnum


class DecisionMode(StrEnum):
    """How an organization makes decisions (Feature 032).

    Determines the Decide phase duration in the OODA cycle time
    computation. Faster decision modes yield shorter cycle times
    and higher initiative scores.

    Values:
        AUTOCRATIC: Single leader decides (fastest, base 1.0)
        DELEGATE: Trusted delegates (fast, base 2.0)
        DEMOCRATIC: Majority vote (moderate, base 3.0)
        CONSENSUS: Full consensus (slowest, base 5.0)
    """

    AUTOCRATIC = "autocratic"
    DELEGATE = "delegate"
    DEMOCRATIC = "democratic"
    CONSENSUS = "consensus"


class ActionType(StrEnum):
    """Organizational action types for OODA resolution (Feature 032).

    21 action types across 7 categories. Eligibility depends on OrgType
    and organization attributes.

    Values:
        RECRUIT: Recruit new members
        ORGANIZE: Build organizational capacity
        EDUCATE: Raise consciousness through education
        AGITATE: Raise contestation (precondition for effective EDUCATE)
        PROPAGANDIZE: Broadcast messaging
        FUNDRAISE: Generate resources
        PROVIDE_SERVICE: Direct community service provision
        EMPLOY: Hire workers (Business only)
        REPRESS: State coercion (StateApparatus or violence_capacity > 0)
        PROTEST: Public demonstration
        STRIKE: Withdraw labor
        EXPROPRIATE: Seize assets
        SURVEIL: Monitor targets (StateApparatus or surveillance_capacity > 0)
        INFILTRATE: Plant agents (StateApparatus only)
        COUNTER_INTEL: Build counter-intelligence
        MAP_NETWORK: Intelligence gathering
        PROPOSE_ALLIANCE: Seek alliance
        DENOUNCE: Public denunciation
        BUILD_INFRASTRUCTURE: Build community infrastructure
        ATTACK_INFRASTRUCTURE: Destroy infrastructure
        ASSIMILATE: Absorb into hegemonic norm
    """

    RECRUIT = "recruit"
    ORGANIZE = "organize"
    EDUCATE = "educate"
    AGITATE = "agitate"
    PROPAGANDIZE = "propagandize"
    FUNDRAISE = "fundraise"
    PROVIDE_SERVICE = "provide_service"
    EMPLOY = "employ"
    REPRESS = "repress"
    PROTEST = "protest"
    STRIKE = "strike"
    EXPROPRIATE = "expropriate"
    SURVEIL = "surveil"
    INFILTRATE = "infiltrate"
    COUNTER_INTEL = "counter_intel"
    MAP_NETWORK = "map_network"
    PROPOSE_ALLIANCE = "propose_alliance"
    DENOUNCE = "denounce"
    BUILD_INFRASTRUCTURE = "build_infrastructure"
    ATTACK_INFRASTRUCTURE = "attack_infrastructure"
    ASSIMILATE = "assimilate"


__all__ = [
    "ActionType",
    "DecisionMode",
]
