"""Behavioral laws for TerritorySystem (P27 Phase-0 backfill, plan Task 11 pattern).

Source read end-to-end first (F1 discipline):
``src/babylon/engine/systems/territory.py`` -- ``TerritorySystem.step()`` runs, in
strict order, ``_process_heat_dynamics`` -> ``_process_eviction_pipeline`` ->
``_process_spillover`` -> ``_process_necropolitics``.

Laws pinned (grounded in what reading step() + its coefficient bounds confirms):

  L1 -- heat bounds: a territory's ``heat`` attribute stays inside ``[0.0, 1.0]``
        after any single ``step()`` call, regardless of starting heat, profile,
        or territory_type. Grounded in ``_write_clamped(..., lo=0.0, hi=1.0)``
        at territory.py:137 (heat-dynamics write) and the explicit
        ``min(1.0, current_heat + spillover)`` at territory.py:307
        (spillover write, `current_heat` already non-negative post-clamp so
        the sum cannot go below 0 even though spillover's floor isn't
        re-clamped there).

  L2 -- population non-negativity: a territory's ``population`` never goes
        negative after ``step()``. Grounded in ``displacement_rate`` being
        Pydantic-constrained to ``[0.0, 1.0]`` (config/defines/territory.py:40-44),
        so ``displaced_pop = int(current_pop * displacement_rate) <= current_pop``
        at territory.py:246-247 (eviction pipeline); and
        ``concentration_camp_decay_rate`` likewise constrained to ``[0.0, 1.0]``
        (config/defines/territory.py:58-63), so
        ``new_pop = int(current_pop * (1.0 - decay_rate)) >= 0`` at
        territory.py:337-338 (necropolitics).

  L3 -- eviction monotonicity: once a territory's ``under_eviction`` flag is
        set True by ``step()``, no later ``step()`` call on the same graph ever
        reverts it to False. Grounded in ``_process_eviction_pipeline`` only
        ever writing ``under_eviction=True`` (territory.py:236-238) --
        there is no code path in this module that writes ``under_eviction=False``.

  L4 -- inactivity on ungated nodes: a ``social_class`` node with no TENANCY
        edge into a PENAL_COLONY territory is completely untouched by
        ``TerritorySystem.step()``. Grounded in every phase filtering to
        ``graph.query_nodes(node_type=NodeType.TERRITORY)``
        (territory.py:120, :229, :328) and the ONLY write to a non-territory
        node being ``_suppress_organization``'s ``graph.update_node(edge.source_id,
        organization=0.0)`` (territory.py:370), reached solely by walking
        TENANCY edges targeting a PENAL_COLONY (territory.py:361-370). A
        social_class node with no such edge falls through every phase
        unmodified.

Caveat (not a law -- recorded, not pinned): rent_level is NOT monotonically
non-decreasing under eviction in general. ``rent_spike_multiplier`` is only
constrained ``gt=0.0`` (config/defines/territory.py:35-38), not ``ge=1.0``, so a
custom define below 1.0 would make eviction-triggered rent spikes actually
*decrease* rent_level. The default (1.5) always increases it, but that is a
data fact, not a structural invariant the source enforces -- so no
"rent never decreases" law is claimed here.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.territory import TerritorySystem
from babylon.models.enums import NodeType, OperationalProfile, SectorType, TerritoryType
from babylon.topology.graph import BabylonGraph

_TERRITORY_ID = "T001"

# All values are real production enum members / Field-bounded ranges --
# never hand-invented attribute names (vocabulary-sentinel law, CLAUDE.md
# Gotchas). The node shape below mirrors the project's own
# tests/unit/engine/systems/test_territory_system.py fixtures exactly.

_profiles = st.sampled_from([OperationalProfile.HIGH_PROFILE, OperationalProfile.LOW_PROFILE])
_territory_types = st.sampled_from(list(TerritoryType))
_heats = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
_populations = st.integers(min_value=0, max_value=100_000)


def _build_single_territory_graph(
    *,
    profile: OperationalProfile,
    heat: float,
    population: int,
    rent_level: float,
    under_eviction: bool,
    territory_type: TerritoryType,
) -> BabylonGraph:
    """Build a one-node territory graph using the project's real node shape.

    Mirrors ``tests/unit/engine/systems/test_territory_system.py`` fixtures
    (e.g. ``test_high_profile_gains_heat``) -- the smallest real shape that
    exercises heat dynamics, eviction, and necropolitics.
    """
    graph = BabylonGraph()
    graph.add_node(
        _TERRITORY_ID,
        _node_type=NodeType.TERRITORY,
        id=_TERRITORY_ID,
        name="Law Test Territory",
        sector_type=SectorType.RESIDENTIAL,
        territory_type=territory_type,
        profile=profile,
        heat=heat,
        rent_level=rent_level,
        population=population,
        under_eviction=under_eviction,
    )
    return graph


# =============================================================================
# L1 -- heat bounds
# =============================================================================


@given(profile=_profiles, heat=_heats, territory_type=_territory_types)
@settings(max_examples=25, deadline=None)
def test_heat_stays_within_unit_interval(
    profile: OperationalProfile, heat: float, territory_type: TerritoryType
) -> None:
    """Heat is always clamped to [0.0, 1.0] after a single step(), for any
    starting heat in-range, either profile, and any territory_type."""
    graph = _build_single_territory_graph(
        profile=profile,
        heat=heat,
        population=1_000,
        rent_level=1.0,
        under_eviction=False,
        territory_type=territory_type,
    )
    services = ServiceContainer.create()
    context = TickContext(tick=1)

    TerritorySystem().step(graph, services, context)

    result_heat = graph.nodes[_TERRITORY_ID]["heat"]
    assert 0.0 <= result_heat <= 1.0


# =============================================================================
# L2 -- population non-negativity
# =============================================================================


@given(
    profile=_profiles,
    population=_populations,
    under_eviction=st.booleans(),
    territory_type=_territory_types,
)
@settings(max_examples=25, deadline=None)
def test_population_never_goes_negative(
    profile: OperationalProfile,
    population: int,
    under_eviction: bool,
    territory_type: TerritoryType,
) -> None:
    """Population never goes negative, whether from eviction displacement
    or CONCENTRATION_CAMP necropolitical decay, across the default
    (Pydantic-bounded [0,1]) coefficients."""
    graph = _build_single_territory_graph(
        profile=profile,
        heat=0.9,  # high enough to trigger eviction if under_eviction flips
        population=population,
        rent_level=1.0,
        under_eviction=under_eviction,
        territory_type=territory_type,
    )
    services = ServiceContainer.create()
    context = TickContext(tick=1)

    TerritorySystem().step(graph, services, context)

    assert graph.nodes[_TERRITORY_ID]["population"] >= 0


# =============================================================================
# L3 -- eviction monotonicity
# =============================================================================


@given(start_under_eviction=st.booleans(), heat=_heats)
@settings(max_examples=25, deadline=None)
def test_eviction_flag_never_reverts_once_set(start_under_eviction: bool, heat: float) -> None:
    """Once under_eviction becomes True, it stays True across every
    subsequent step() on the same graph -- no code path clears it."""
    graph = _build_single_territory_graph(
        profile=OperationalProfile.LOW_PROFILE,
        heat=heat,
        population=1_000,
        rent_level=1.0,
        under_eviction=start_under_eviction,
        territory_type=TerritoryType.CORE,
    )
    services = ServiceContainer.create()

    seen_true = start_under_eviction
    for tick in range(1, 6):
        context = TickContext(tick=tick)
        TerritorySystem().step(graph, services, context)
        current = graph.nodes[_TERRITORY_ID]["under_eviction"]
        if seen_true:
            assert current is True
        seen_true = seen_true or current


# =============================================================================
# L4 -- inactivity on ungated (non-territory, non-TENANCY-to-penal-colony) nodes
# =============================================================================


@given(
    wealth=st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
    organization=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
)
@settings(max_examples=25, deadline=None)
def test_social_class_without_tenancy_edge_is_untouched(wealth: float, organization: float) -> None:
    """A social_class node with no TENANCY edge into a PENAL_COLONY is
    completely unmodified by TerritorySystem.step() -- every phase filters
    to node_type=NodeType.TERRITORY, and the only non-territory write
    (_suppress_organization) is reached only via such a TENANCY edge."""
    graph = BabylonGraph()
    graph.add_node(
        "PERIPHERY_WORKER_ID",
        _node_type=NodeType.SOCIAL_CLASS,
        id="PERIPHERY_WORKER_ID",
        wealth=wealth,
        organization=organization,
    )
    services = ServiceContainer.create()
    context = TickContext(tick=1)

    TerritorySystem().step(graph, services, context)

    assert graph.nodes["PERIPHERY_WORKER_ID"]["wealth"] == wealth
    assert graph.nodes["PERIPHERY_WORKER_ID"]["organization"] == organization
