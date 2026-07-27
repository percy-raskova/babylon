"""The five electoral goldens — §5.5's behavioral-contract scenarios (ADR140).

Five named golden scenarios in the qa:regression idiom (determinism
contracts, not scale samples), each a thin terrain over an existing material
substrate plus the ambient political machine
(:func:`~babylon.engine.scenarios.electoral_fixture.apply_political_terrain`):

- ``mitterrand`` / ``syriza`` stand on the **Wayne single_county substrate**
  (real hydrator-extracted fiscal facts: ``t_claim`` ≈ $175.7M,
  ``total_surplus`` ≈ $3.23B, endogenous interest ≈ 1.78%). Wayne's
  ``tick_phi_hour`` is a MEASURED 0.0, so the U12-E periphery mirror engages
  and every gauntlet bar runs contracted ×``periphery_ceiling_factor`` —
  the rent-starved terrain where Allende geometry is the default (§4).
- ``weimar`` / ``debs`` / ``bernie_valve`` stand on the **two_node
  substrate** (no φ measurement ⟹ core bars), exercising the ballot
  machine: consolidation through elections, spoiler arithmetic, and both
  routings of the disillusion valve.

Registers (an opening agenda, a seated reform government) are seeded via
``WorldState.superstructure_registers`` — the sanctioned scenario convention
(ADR135) riding the U13 carrier. Scenario-specific coefficients live in the
``SCENARIOS`` registry's ``defines_overrides``, never here (III.1).

Determinism: factories are pure constructors — every value below is a
literal; contingency in-run is the engine's own seeded ξ_t.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.domain.politics.policy import PolicyAgendaItem
from babylon.engine.scenarios.electoral_fixture import apply_political_terrain
from babylon.models.entities.organization import StateApparatus
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.entities.state_apparatus_ai import FactionBalance
from babylon.models.enums import ClassCharacter, EdgeType, JurisdictionLevel
from babylon.models.enums.politics import PolicyAxis

if TYPE_CHECKING:
    from babylon.config.defines import GameDefines
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState

#: The Wayne substrate's class ids (single_county.py).
_WAYNE_WORKER = "C003"
_WAYNE_OWNER = "C004"

#: The two_node substrate's class ids (_legacy.py).
_WORKER = "C001"
_OWNER = "C002"

_SOCDEM = "org/party-socdem"
_LIBERAL = "org/party-liberal"
_RESTORATIONIST = "org/party-restorationist"
_FASCIST = "org/party-fascist"
_FED = "SOV_USA_FED"


def _social_wage_agenda(count: int, promised: float, magnitude: float) -> list[dict[str, object]]:
    """A seeded calibration agenda: ``count`` identical SOCIAL_WAGE promises."""
    return [
        PolicyAgendaItem(
            sovereign_id=_FED,
            axis=PolicyAxis.SOCIAL_WAGE,
            magnitude=magnitude,
            promised=promised,
            drafted_tick=0,
            source_org_id="",
        ).model_dump(mode="json")
        for _ in range(count)
    ]


def _seated(party_id: str) -> dict[str, dict[str, object]]:
    """An electoral_governments register with ``party_id`` in office at tick 0."""
    return {_FED: {"party_id": party_id, "formed_tick": 0, "share": 0.55}}


def _voter(
    entity: SocialClass,
    allegiance: dict[str, float],
    *,
    population: int = 1,
    agitation: float = 0.0,
    repression: float = 0.0,
    national_identity: float | None = None,
    class_consciousness: float | None = None,
    wealth: float | None = None,
) -> SocialClass:
    """A class re-seeded as a deterministic voter (repression zeroed)."""
    profile = entity.ideology
    updates: dict[str, object] = {
        "allegiance": allegiance,
        # Zero repression makes P(S|R) infinite — the worker revolts at tick 1
        # and Struggle severs its exploitation edge (a topology change the
        # dense contract forbids). Voters needing a stable wage relation carry
        # a small nonzero repression instead.
        "repression_faced": repression,
        "population": population,
        "ideology": IdeologicalProfile(
            class_consciousness=(
                profile.class_consciousness if class_consciousness is None else class_consciousness
            ),
            national_identity=(
                profile.national_identity if national_identity is None else national_identity
            ),
            agitation=agitation,
        ),
    }
    if wealth is not None:
        updates["wealth"] = wealth
    return entity.model_copy(update=updates)


def _with_worker_twin(state: WorldState, twin_id: str, *, source_id: str = _WORKER) -> WorldState:
    """Clone a worker's material base under a new class id.

    Every edge touching ``source_id`` is mirrored onto the twin
    (exploitation, wages, tenancy), so the engine treats both workers
    symmetrically. Applied BEFORE the political terrain so the party layer
    sees the twin as substrate. The twin exists because BabylonGraph stores
    one edge per (source, target) pair and the worker↔owner pairs are
    already taken by the material triangle — a SOLIDARITY bridge needs a
    class pair of its own (worker↔worker, which is also what solidarity IS).
    """
    twin = state.entities[source_id].model_copy(update={"id": twin_id})
    mirrored = [
        rel.model_copy(
            update={
                "source_id": twin_id if rel.source_id == source_id else rel.source_id,
                "target_id": twin_id if rel.target_id == source_id else rel.target_id,
            }
        )
        for rel in state.relationships
        if source_id in (rel.source_id, rel.target_id)
    ]
    return state.model_copy(
        update={
            "entities": {**state.entities, twin_id: twin},
            "relationships": [*state.relationships, *mirrored],
        }
    )


def _membership(party_id: str, class_id: str) -> Relationship:
    return Relationship(
        source_id=party_id,
        target_id=class_id,
        edge_type=EdgeType.MEMBERSHIP,
        description=f"{party_id} base among {class_id}",
    )


def _solidarity(a: str, b: str, strength: float) -> Relationship:
    return Relationship(
        source_id=a,
        target_id=b,
        edge_type=EdgeType.SOLIDARITY,
        solidarity_strength=strength,
        description="The organizing bridge the ballot cannot tax",
    )


def _with_doctrine(state: WorldState, org_id: str, *stances: str, pull: float = 0.0) -> WorldState:
    """Stamp doctrine stances (and optional institutional pull) on an org."""
    org = state.organizations[org_id]
    org = org.model_copy(
        update={
            "acquired_doctrine_ids": (*org.acquired_doctrine_ids, *stances),
            "institutional_pull": pull,
        }
    )
    return state.model_copy(update={"organizations": {**state.organizations, org_id: org}})


def _warm(state: WorldState) -> WorldState:
    """Return the round-trip fixed point of a factory state (ADR140).

    ``to_graph`` synthesizes edges (org/institution PRESENCE) that
    ``from_graph`` then materializes as Relationship rows — so a raw factory
    state's edge set differs from every post-tick state's. The dense golden
    contract requires a STATIC relationship topology per scenario
    (Constitution III.11); warming through one round-trip makes tick 0's
    topology identical to tick 1..N's.
    """
    from babylon.models.world_state import WorldState as _WS

    return _WS.from_graph(state.to_graph(), tick=0)


def _commit_coupling(party_id: str) -> Relationship:
    """The popular-front CO_OPTIVE coupling, seeded at zero dependence.

    ElectoralSystem accrues dependence onto this edge for COMMITTED orgs
    (U12-A); seeding it keeps the dense topology static — the run moves the
    attribute, never the edge set.
    """
    return Relationship(
        source_id=party_id,
        target_id=_FED,
        edge_type=EdgeType.TRANSACTIONAL,
        value_flow=0.0,
        description="Popular-front commitment coupling toward the defended apex",
    )


def create_mitterrand_scenario() -> tuple[WorldState, SimulationConfig, GameDefines]:
    """Reform in office on the Wayne terrain — the tournant de la rigueur.

    The seated socdem government opens with a 24-item social-wage agenda
    drained in one boundary-tick burst (``policy_agenda_rate`` override):
    each successive item borrows against a shrinking funded ceiling as debt
    service compounds at the live endogenous rate — the O'Connor spiral —
    until bond discipline binds and delivery collapses to the funded floor
    (the forced austerity turn). Incidence sits past the periphery-contracted
    capital tolerance (CAPITAL_STRIKE every item; Wayne's fixture carries no
    capital-stock series, so the equalization outflow is an honest 0.0) and
    under the judicial bar. First ceiling contact resolves the governance
    fork: capitulate — no dual-power organs stand on the terrain.
    """
    from babylon.engine.scenarios.single_county import create_single_county_scenario

    state, config, defines = create_single_county_scenario()
    state = apply_political_terrain(
        state, worker_id=_WAYNE_WORKER, owner_id=_WAYNE_OWNER, include_michigan=False
    )
    entities = {
        _WAYNE_WORKER: _voter(
            state.entities[_WAYNE_WORKER],
            {_SOCDEM: 0.6, _LIBERAL: 0.2},
            population=3,
        ),
        _WAYNE_OWNER: _voter(
            state.entities[_WAYNE_OWNER],
            {_LIBERAL: 0.5, _RESTORATIONIST: 0.3},
            population=2,
        ),
    }
    state = state.model_copy(
        update={
            "entities": {**state.entities, **entities},
            "superstructure_registers": {
                "electoral_governments": _seated(_SOCDEM),
                "policy_agenda": _social_wage_agenda(24, promised=2.4e8, magnitude=0.06),
            },
        }
    )
    return _warm(state), config, defines


def create_syriza_scenario() -> tuple[WorldState, SimulationConfig, GameDefines]:
    """The governance road's captured party — capitulate WITH organs live.

    Same Wayne terrain, but the seated socdem carries accumulated
    ``institutional_pull`` past ``governance_capture_threshold`` AND a second
    live claimant stands on the territory (dual-power organs present via a
    Michigan CLAIMS row) — the fork must still resolve CAPITULATE: capture
    dominates organs (§3.5; the scenario-scale twin of
    ``test_captured_party_capitulates_even_with_organs``). The office is
    retained; the delivery-gap machinery IS the PASOK trajectory — the
    betrayal integral crosses mid-run, windows open, and the atomized base
    (no SOLIDARITY bridges) routes to fascist alignment: the Golden Dawn
    shadow.
    """
    from babylon.engine.scenarios.single_county import create_single_county_scenario

    state, config, defines = create_single_county_scenario()
    state = apply_political_terrain(state, worker_id=_WAYNE_WORKER, owner_id=_WAYNE_OWNER)
    state = _with_doctrine(state, _SOCDEM, "governance_road", pull=0.65)
    entities = {
        _WAYNE_WORKER: _voter(
            state.entities[_WAYNE_WORKER],
            {_SOCDEM: 0.7, _LIBERAL: 0.1},
            population=3,
            agitation=0.5,
        ),
        _WAYNE_OWNER: _voter(
            state.entities[_WAYNE_OWNER],
            {_SOCDEM: 0.4, _LIBERAL: 0.4},
            population=2,
        ),
    }
    state = state.model_copy(
        update={
            "entities": {**state.entities, **entities},
            "relationships": [
                *state.relationships,
                _commit_coupling(_SOCDEM),
                # The second live claimant — dual-power organs stand on the
                # terrain, and the fork must STILL capitulate (capture wins).
                Relationship(
                    source_id="SOV_MI_STATE",
                    target_id="T001",
                    edge_type=EdgeType.CLAIMS,
                    control_level=0.4,
                    description="Contested claim: the dual-power organ on Wayne",
                ),
            ],
            "superstructure_registers": {
                "electoral_governments": _seated(_SOCDEM),
                "policy_agenda": _social_wage_agenda(6, promised=1.9e8, magnitude=0.06),
            },
        }
    )
    return _warm(state), config, defines


def create_weimar_scenario() -> tuple[WorldState, SimulationConfig, GameDefines]:
    """Fascist consolidation THROUGH the ballot — never via script.

    Falling wages (extraction override), no SOLIDARITY bridge anywhere, an
    intact electoral machine. The owner-base opens national-identity-heavy;
    the worker's disillusion windows route conversion into fascist alignment
    (no bridges), the fascist vehicle's allegiance coupling compounds, and
    the machine seats it by FPTP. A StateApparatus org carries the
    ``faction_balance`` the win perturbs toward SETTLER_POPULIST (ADR136's
    first production write-back — Weimar as parameter flow), and the
    bonapartist presidency stands ready: when hopeless elections drag mean
    legitimation under the floor, the clock suspends (L-SUSPEND).
    """
    from babylon.engine.scenarios._legacy import create_two_node_scenario
    from babylon.models.entities.institution import (
        Institution,
        InternalBalanceOfForces,
        ReproductionMechanism,
    )
    from babylon.models.enums import ApparatusType, SocialFunction

    state, config, defines = create_two_node_scenario()
    territory = state.territories["T001"].model_copy(update={"county_fips": "26163"})
    state = state.model_copy(update={"territories": {**state.territories, "T001": territory}})
    state = apply_political_terrain(state, include_michigan=False)
    interior = StateApparatus(
        id="org/state-interior",
        name="Interior Ministry",
        class_character=ClassCharacter.BOURGEOIS,
        jurisdiction=JurisdictionLevel.NATIONAL,
        territory_ids=["T001"],
        faction_balance=FactionBalance(
            finance_capital=0.4,
            security_state=0.3,
            settler_populist=0.3,
            stability=0.5,
            legitimacy=0.5,
        ),
        rng_seed=0,
    )
    presidency = Institution(
        id="INST_PRESIDENCY",
        name="The Presidency",
        apparatus_type=ApparatusType.RSA_EXECUTIVE,
        social_function=SocialFunction.ADJUDICATION,
        internal_balance=InternalBalanceOfForces(
            liberal_technocratic=0.2,
            revanchist_fascist=0.25,
            institutionalist_bonapartist=0.55,
        ),
        reproduction=ReproductionMechanism(
            succession_protocol=True,
            legal_self_perpetuation=True,
        ),
        jurisdiction=frozenset({"national"}),
        territory_ids=["T001"],
    )
    entities = {
        _WORKER: _voter(
            state.entities[_WORKER],
            {_SOCDEM: 0.3, _LIBERAL: 0.2, _FASCIST: 0.1},
            population=2,
            agitation=0.2,
            repression=0.2,
            national_identity=0.5,
            class_consciousness=0.35,
        ),
        _OWNER: _voter(
            state.entities[_OWNER],
            {_RESTORATIONIST: 0.3, _FASCIST: 0.45},
            population=3,
            agitation=0.4,
            national_identity=0.65,
            class_consciousness=0.3,
            wealth=0.35,
        ),
    }
    # The reactionary financier hedge deepens into open bankrolling
    # (Thyssen, 1932): re-weight the donor's existing fascist funding edge.
    relationships = [
        rel.model_copy(update={"value_flow": 90.0})
        if (
            rel.source_id == "org/donor-finance"
            and rel.target_id == _FASCIST
            and rel.edge_type == EdgeType.TRANSACTIONAL
        )
        else rel
        for rel in state.relationships
    ]
    state = state.model_copy(
        update={
            "entities": {**state.entities, **entities},
            "relationships": relationships,
            "organizations": {**state.organizations, interior.id: interior},
            "institutions": {**state.institutions, presidency.id: presidency},
        }
    )
    return _warm(state), config, defines


def create_debs_scenario() -> tuple[WorldState, SimulationConfig, GameDefines]:
    """The independent line under FPTP — the mode's honest trade.

    The socdem current holds ``independent_ballot_line``: its votes are
    taxed toward the same-pole machine (the liberal), the lesser-evil
    arithmetic seats the greater evil (the restorationist), and the
    vote-share ceiling binds — but the worker base carries a live SOLIDARITY
    bridge, so every loss window routes boosted conversion into
    ORGANIZATION, not fascist drift: what the ballot denies, the class
    accumulates (§2.3).
    """
    from babylon.engine.scenarios._legacy import create_two_node_scenario

    state, config, defines = create_two_node_scenario()
    territory = state.territories["T001"].model_copy(update={"county_fips": "26163"})
    state = state.model_copy(update={"territories": {**state.territories, "T001": territory}})
    state = _with_worker_twin(state, "C005")
    state = _with_worker_twin(state, "C007")
    state = apply_political_terrain(state)
    state = _with_doctrine(state, _SOCDEM, "independent_ballot_line")
    # The machine-loyal labor aristocracy: same wage relation, machine
    # allegiance, twice the mass. A worker-majority electorate would simply
    # elect the workers' own line — the independent's ceiling is set by
    # this stratum, whose hope runs through the machine's donor-pulled
    # platform and whose numbers outweigh the militant base (1912).
    petit_bourgeois = _voter(
        state.entities["C007"],
        {_LIBERAL: 0.55, _RESTORATIONIST: 0.15},
        population=10,
        wealth=0.32,
    )
    entities = {
        _WORKER: _voter(
            state.entities[_WORKER],
            {_SOCDEM: 0.45, _LIBERAL: 0.25},
            population=2,
            agitation=0.5,
            repression=0.2,
            wealth=0.35,
        ),
        "C005": _voter(
            state.entities["C005"],
            {_SOCDEM: 0.45, _LIBERAL: 0.25},
            population=2,
            agitation=0.5,
            repression=0.2,
            wealth=0.35,
        ),
        "C007": petit_bourgeois,
        _OWNER: _voter(
            state.entities[_OWNER],
            {_RESTORATIONIST: 0.5, _LIBERAL: 0.1},
            population=3,
            wealth=2.0,
        ),
    }
    state = state.model_copy(
        update={
            "entities": {**state.entities, **entities},
            "relationships": [
                *state.relationships,
                _membership(_SOCDEM, "C005"),
                _membership(_LIBERAL, "C007"),
                _membership(_RESTORATIONIST, "C007"),
                _solidarity(_WORKER, "C005", 0.4),
            ],
        }
    )
    return _warm(state), config, defines


def create_bernie_valve_scenario() -> tuple[WorldState, SimulationConfig, GameDefines]:
    """The hope valve, both routings, one deterministic run.

    Three worker classes on the Wayne terrain share the same material base
    and the same entryist hope machine (committed to the standing popular
    front ⟹ viability 1.0; wealth pinned near subsistence ⟹ steep
    counterfactual ΔP(S|A)): the hope years spike H and suppress organizing
    conversion for ALL of them (L-VALVE), while the host machine
    derecognizes the entryist surge (U12-C — the superdelegate reflex). The
    seated reform government's ledger then betrays — the integral crosses,
    disillusion windows open, and the SAME operator routes the twins apart:
    the bridged workers surge into organization (Bernie→DSA), the atomized
    twin drifts into fascist alignment (Obama→Trump). §2.5's topology
    chooses; the game never does.
    """
    from babylon.engine.scenarios.single_county import create_single_county_scenario

    state, config, defines = create_single_county_scenario()
    # Two twins BEFORE the terrain: C006 is the Wayne worker's bridge
    # partner (both bridged), C005 is the atomized control — same class,
    # same hope, no edge out of despair.
    state = _with_worker_twin(state, "C005", source_id=_WAYNE_WORKER)
    state = _with_worker_twin(state, "C006", source_id=_WAYNE_WORKER)
    state = apply_political_terrain(
        state, worker_id=_WAYNE_WORKER, owner_id=_WAYNE_OWNER, include_michigan=False
    )
    state = _with_doctrine(state, _SOCDEM, "entryism")

    entities = {
        worker_id: _voter(
            state.entities[worker_id],
            {_SOCDEM: 0.8},
            population=2,
            agitation=0.5,
            # The waged worker survives on Wayne's wage flow; the twins buy
            # their window ticks with savings (no hydrator wage keys reach
            # mirrored edges — they starve mid-run, attrs frozen thereafter).
            wealth=0.25 if worker_id == _WAYNE_WORKER else 0.35,
        )
        for worker_id in (_WAYNE_WORKER, "C005", "C006")
    }
    entities[_WAYNE_OWNER] = _voter(
        state.entities[_WAYNE_OWNER],
        {_LIBERAL: 0.6, _RESTORATIONIST: 0.3},
        population=3,
    )
    state = state.model_copy(
        update={
            "entities": {**state.entities, **entities},
            "relationships": [
                *state.relationships,
                _membership(_SOCDEM, "C005"),
                _membership(_SOCDEM, "C006"),
                _solidarity(_WAYNE_WORKER, "C006", 0.4),
                _commit_coupling(_SOCDEM),
            ],
            "superstructure_registers": {
                "electoral_governments": _seated(_SOCDEM),
                "policy_agenda": _social_wage_agenda(8, promised=1.9e8, magnitude=0.06),
            },
        }
    )
    return _warm(state), config, defines
