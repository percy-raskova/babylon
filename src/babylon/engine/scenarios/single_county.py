"""``single_county``: the smallest graph where the Vol III financial layer
fires through the production path.

Feature: qa-regression-modernization E2a. Wayne County, Michigan (FIPS
``26163``, Detroit metro) is the imperial-core county this scenario stamps:
one core-bourgeoisie owner, one labor-aristocracy worker (the class pair
Wayne's real unionized-manufacturing wage structure implies — Wayne workers
draw imperial super-wages, they are not the periphery proletariat of the
``two_node``/``imperial_circuit`` topologies), and one Territory carrying
``county_fips="26163"``. ``county_fips`` is a real declared field on both
:class:`~babylon.models.entities.social_class.SocialClass` (spec-065
per-county attribution) and
:class:`~babylon.models.entities.territory.Territory` (the field
``TickDynamicsSystem`` resolves county identity from — see
``babylon.domain.economics.tick.graph_bridge.resolve_county_identity``), so
both are stamped (vocabulary sentinel Rule (c): only real declared fields are
stamped, never invented attribute shapes).

Wired against ``tools.regression_test.build_single_county_overrides``'s real
``TensorRegistry`` (hydrated from the committed
``tests/fixtures/single_county_wayne.json`` extraction, D4) and the Vol III
``distribution_calculator``, the county pipeline exercises the distribution
identity ``s = p + i + r + t`` (Capital Vol. III Part V: surplus = profit of
enterprise + interest + ground rent + taxes on surplus) for real, not as a
schema-static zero.
"""

from __future__ import annotations

from babylon.config.defines import GameDefines
from babylon.models.config import SimulationConfig
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import SocialClass
from babylon.models.entities.territory import Territory
from babylon.models.entity_registry import CORE_BOURGEOISIE_ID, LABOR_ARISTOCRACY_ID
from babylon.models.enums import EdgeType, SectorType, SocialRole
from babylon.models.world_state import WorldState

#: Wayne County, Michigan (Detroit metro) — the imperial-core county whose
#: real reference-tensor data backs this scenario's financial layer.
WAYNE_COUNTY_FIPS: str = "26163"

#: Graph-local territory node id. NOT the FIPS: ``Territory.id`` is
#: constrained to ``^(T[0-9]{3,}|[0-9a-f]{15})$`` (a bridge-minted label or a
#: 15-char H3 hex — never a 5-char FIPS); county identity rides on
#: ``county_fips`` alone (``resolve_county_identity``).
_TERRITORY_NODE_ID: str = "T001"


def create_single_county_scenario() -> tuple[WorldState, SimulationConfig, GameDefines]:
    """Create the Wayne-County-seeded minimal financial-layer scenario.

    One core-bourgeoisie owner (:data:`~babylon.models.entity_registry.CORE_BOURGEOISIE_ID`),
    one labor-aristocracy worker
    (:data:`~babylon.models.entity_registry.LABOR_ARISTOCRACY_ID`), one
    EXPLOITATION edge (worker -> owner), one WAGES edge (owner -> worker,
    PPP super-wages), one Territory keyed to Wayne County
    (``county_fips="26163"``), and one TENANCY edge (worker -> territory).
    Mirrors :func:`babylon.engine.scenarios._legacy.create_two_node_scenario`'s
    construction shape.

    Returns:
        ``(state, config, defines)`` — a tick-0 ``WorldState`` whose sole
        territory carries ``county_fips == "26163"``, a default
        ``SimulationConfig``, and default ``GameDefines`` (this scenario's
        financial-layer wiring lives in calculator_overrides, not defines
        overrides — see ``tools.regression_test.build_single_county_overrides``).
    """
    owner = SocialClass(
        id=CORE_BOURGEOISIE_ID,
        name="Wayne County Core Bourgeoisie",
        role=SocialRole.CORE_BOURGEOISIE,
        description="Detroit-area capital owner drawing surplus from Wayne County production",
        wealth=0.5,
        ideology=0.5,  # type: ignore[arg-type]  # Validator converts float to IdeologicalProfile
        organization=0.8,
        repression_faced=0.1,
        subsistence_threshold=0.1,
        county_fips=WAYNE_COUNTY_FIPS,
    )

    worker = SocialClass(
        id=LABOR_ARISTOCRACY_ID,
        name="Wayne County Labor Aristocracy",
        role=SocialRole.LABOR_ARISTOCRACY,
        description="Unionized Detroit-area worker benefiting from imperial super-wages",
        wealth=0.5,
        ideology=0.0,  # type: ignore[arg-type]  # Validator converts float to IdeologicalProfile
        organization=0.4,
        repression_faced=0.2,
        subsistence_threshold=0.3,
        county_fips=WAYNE_COUNTY_FIPS,
    )

    exploitation = Relationship(
        source_id=LABOR_ARISTOCRACY_ID,
        target_id=CORE_BOURGEOISIE_ID,
        edge_type=EdgeType.EXPLOITATION,
        description="Surplus extraction from Wayne County production",
        value_flow=0.0,
        tension=0.0,
    )

    wages = Relationship(
        source_id=CORE_BOURGEOISIE_ID,
        target_id=LABOR_ARISTOCRACY_ID,
        edge_type=EdgeType.WAGES,
        description="Super-wages from imperial rent, paid to Wayne County labor aristocracy",
        value_flow=0.0,
        tension=0.0,
    )

    territory = Territory(
        id=_TERRITORY_NODE_ID,
        name="Wayne County",
        county_fips=WAYNE_COUNTY_FIPS,
        sector_type=SectorType.INDUSTRIAL,
        biocapacity=100.0,
        max_biocapacity=100.0,
    )

    tenancy = Relationship(
        source_id=LABOR_ARISTOCRACY_ID,
        target_id=_TERRITORY_NODE_ID,
        edge_type=EdgeType.TENANCY,
        description="Worker land tenancy in Wayne County",
        value_flow=0.0,
        tension=0.0,
    )

    state = WorldState(
        tick=0,
        entities={CORE_BOURGEOISIE_ID: owner, LABOR_ARISTOCRACY_ID: worker},
        territories={_TERRITORY_NODE_ID: territory},
        relationships=[exploitation, wages, tenancy],
        event_log=[],
    )

    config = SimulationConfig()
    defines = GameDefines()

    return state, config, defines
