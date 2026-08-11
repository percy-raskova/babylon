"""``org_probe``: the two-org world backing the Organization estate's Python
byte gates (Organization foundation plan, Task 11, spec §11).

A compact, standalone factory — NOT a variant of
:mod:`babylon.engine.scenarios._legacy_wayne` (that module is shared
substrate under four goldens and this plan's Global Constraints forbid
touching it). One :class:`~babylon.models.entities.social_class.SocialClass`,
one :class:`~babylon.models.entities.territory.Territory`, one
:class:`~babylon.models.entities.organization.CivilSocietyOrg`, and one
:class:`~babylon.models.entities.organization.StateApparatus` — seeded so
``state.organizations`` and the ``NodeType.ORGANIZATION`` nodes
``WorldState.to_graph()`` projects from it are real, exercised evidence
rather than the honest-absence gap ``tools/regression_scenarios.py``'s
``COVERAGE_GAPS_DATA`` records for ``OODASystem``/``DoctrineSystem`` today
("no organizations are seeded in any canonical scenario").

The organization field values mirror
``_legacy_wayne._create_player_org``/``_create_state_apparatus_org`` exactly
(same cohesion/cadre_level/budget/violence/surveillance/``FactionBalance``
constants) — this scenario reuses their *values*, not their code, per the
plan's "constructed fresh from the public models" instruction. Ids are
``org/probe-civil`` / ``org/probe-state``, deliberately distinct from the
``ORG001``/``ORG002`` ids Wayne County uses, so the two scenarios' worlds
never collide even if ever combined.

Touches NO frozen engine CAPABILITY: this module lives under
``engine/scenarios/``, the qa/scenario estate the Program 27 freeze (ADR172)
leaves post-freeze-ACTIVE, not ``engine/systems/`` or ``formulas/``.
"""

from __future__ import annotations

from babylon.config.defines import GameDefines
from babylon.models.config import SimulationConfig
from babylon.models.entities.organization import CivilSocietyOrg, StateApparatus
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import SocialClass
from babylon.models.entities.state_apparatus_ai import FactionBalance
from babylon.models.entities.territory import Territory
from babylon.models.enums import (
    ClassCharacter,
    ConsciousnessTendency,
    EdgeType,
    JurisdictionLevel,
    LegalStanding,
    SectorType,
    ServiceType,
    SocialRole,
)
from babylon.models.world_state import WorldState

#: Deterministic graph-local ids. Distinct from the Wayne-County scenario's
#: ``C001``/``ORG001``/``ORG002``/``T001`` so the two worlds never collide.
_WORKERS_ID: str = "C900"
_TERRITORY_ID: str = "T900"
_CIVIL_SOCIETY_ORG_ID: str = "org/probe-civil"
_STATE_APPARATUS_ORG_ID: str = "org/probe-state"


def create_org_probe_scenario() -> tuple[WorldState, SimulationConfig, GameDefines]:
    """Create the two-org probe world for the Organization estate's byte gates.

    One :class:`~babylon.models.enums.SocialRole.PERIPHERY_PROLETARIAT`
    ``SocialClass``, one abstract ``Territory``, one
    :class:`~babylon.models.entities.organization.CivilSocietyOrg` (a
    nascent reading-group formation — the ``_create_player_org`` values:
    INFORMAL standing, mutual-aid service, cohesion 0.5, cadre_level 0.1,
    budget 100.0), and one
    :class:`~babylon.models.entities.organization.StateApparatus` (a county
    police apparatus — the ``_create_state_apparatus_org`` values: violence
    0.6, surveillance 0.5, a Security-State-leaning ``FactionBalance``,
    ``rng_seed=0`` for its own deterministic tiebreaker draw).

    One TENANCY relationship (worker -> territory, the ``single_county``
    precedent) is seeded so the scenario carries at least one tension-bearing
    edge — ``ContradictionSystem``'s ``_TENSION_EDGE_TYPES`` reads
    EXPLOITATION/WAGES/TENANCY only, and the dense-golden column-shape
    contract (``docs/reference/determinism-contract.rst``) requires every
    registered scenario to carry a real ``edge_*_tension`` column.

    :returns: ``(state, config, defines)`` — a tick-0 ``WorldState`` whose
        ``organizations`` dict carries exactly the two orgs above, a
        ``SimulationConfig(rng_seed=42)``, and default ``GameDefines``.
    """
    workers = SocialClass(
        id=_WORKERS_ID,
        name="Probe Workers",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        description="The class terrain the two probe organizations observe and act over",
        wealth=0.5,
        ideology=0.0,  # type: ignore[arg-type]  # Validator converts float to IdeologicalProfile
        organization=0.1,
        repression_faced=0.2,
        subsistence_threshold=0.3,
    )

    territory = Territory(
        id=_TERRITORY_ID,
        name="Probe County",
        sector_type=SectorType.RESIDENTIAL,
    )

    tenancy = Relationship(
        source_id=_WORKERS_ID,
        target_id=_TERRITORY_ID,
        edge_type=EdgeType.TENANCY,
        description="Worker land tenancy in Probe County",
        value_flow=0.0,
        tension=0.0,
    )

    civil_society_org = CivilSocietyOrg(
        id=_CIVIL_SOCIETY_ORG_ID,
        name="Probe Organizing Committee",
        class_character=ClassCharacter.PROLETARIAN,
        consciousness_tendency=ConsciousnessTendency.REVOLUTIONARY,
        legal_standing=LegalStanding.INFORMAL,
        service_type=ServiceType.MUTUAL_AID,
        cohesion=0.5,
        cadre_level=0.1,
        budget=100.0,
        heat=0.0,
    )

    state_apparatus_balance = FactionBalance(
        finance_capital=0.2,
        security_state=0.6,
        settler_populist=0.2,
        stability=0.5,
        legitimacy=0.5,
    )
    state_apparatus_org = StateApparatus(
        id=_STATE_APPARATUS_ORG_ID,
        name="Probe County Police Department",
        class_character=ClassCharacter.BOURGEOIS,
        consciousness_tendency=ConsciousnessTendency.LIBERAL,
        jurisdiction=JurisdictionLevel.COUNTY,
        cohesion=0.8,
        cadre_level=0.6,
        budget=100.0,
        heat=0.3,
        violence_capacity=0.6,
        surveillance_capacity=0.5,
        faction_balance=state_apparatus_balance,
        rng_seed=0,
    )

    state = WorldState(
        tick=0,
        entities={_WORKERS_ID: workers},
        territories={_TERRITORY_ID: territory},
        relationships=[tenancy],
        organizations={
            _CIVIL_SOCIETY_ORG_ID: civil_society_org,
            _STATE_APPARATUS_ORG_ID: state_apparatus_org,
        },
        event_log=[],
    )

    config = SimulationConfig(rng_seed=42)
    defines = GameDefines()

    return state, config, defines
