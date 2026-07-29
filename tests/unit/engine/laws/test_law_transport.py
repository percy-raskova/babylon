"""Behavioral laws for TransportSystem (P27 Phase-0 coverage backfill, Task 11).

Read end-to-end before writing: ``src/babylon/engine/systems/transport.py``
(``TransportSystem.step``, lines 118-182, and its module docstring for the
materialist-causality/default-OFF justification), plus the pure functions it
calls in ``src/babylon/domain/geography/corridor_mesh.py``
(``decay_all_links``, ``aggregate_connectivity_by_county_pair``) and the
clamp in ``src/babylon/domain/geography/inventory.py``
(``DefaultInfrastructureInventory.adjust_link_condition``).

Laws pinned (each traces to a specific source range -- see per-test
docstrings for file:line grounding):

  L1 -- decay is monotonic non-increasing and clamped: a link's ``condition``
        never rises during ``decay_all_links`` and never leaves ``[0.0, 1.0]``.
  L2 -- the demand signal is never negative (it is a sum of two
        non-negative terms by construction).
  L3 -- inactivity: a disabled gate OR a missing corridor mesh is a full
        no-op -- no keys are written to ``persistent_data``, no graph node
        is touched.
  L4 -- connectivity-aggregation invariant: no self-pair ever appears (an
        edge whose two endpoints share a territory contributes nothing),
        and every emitted key is canonically sorted, ``pair[0] < pair[1]``.

Caveat (NOT a law): this system does not conserve any scalar total the way
e.g. a wealth-transfer system would -- ``decay_all_links`` strictly *removes*
condition (a resource-consuming decay, not a transfer), so no
before==after conservation law holds here. See the module docstring's
``compute_overhang_delta`` for the one value this system derives that DOES
feed a downstream total (``transport_overhang_delta``), but that coupling is
explicitly "not yet wired" (transport.py:64-73) so no cross-system
conservation law can be pinned against it yet either.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.config.defines import GameDefines, TransportDefines
from babylon.domain.geography.corridor_mesh import (
    CorridorMesh,
    aggregate_connectivity_by_county_pair,
)
from babylon.domain.geography.inventory import DefaultInfrastructureInventory
from babylon.domain.geography.types import InfrastructureLinkState
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.transport import TransportSystem
from babylon.models.enums import FlowCategory, InfrastructureType
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


def _make_link(
    link_id: str, condition: float = 1.0, conductivity: float = 0.0
) -> InfrastructureLinkState:
    return InfrastructureLinkState(
        link_id=link_id,
        infra_type=InfrastructureType.HIGHWAY,
        capacity={FlowCategory.FREIGHT: 1.0},
        condition=condition,
        conductivity=conductivity,
    )


def _services(transport: TransportDefines) -> ServiceContainer:
    defines = GameDefines().model_copy(update={"transport": transport})
    return ServiceContainer.create(defines=defines)


def _graph_with_territory(territory_id: str) -> BabylonGraph:
    graph = BabylonGraph()
    graph.add_node(territory_id, _node_type="territory")
    return graph


class TestDecayIsMonotonicAndClamped:
    """L1: ``decay_all_links`` (corridor_mesh.py:124-154) always applies
    ``delta = -(decay_rate_per_tick + flux_coefficient * conductivity)``.
    ``TransportDefines.condition_decay_rate_per_tick`` is field-constrained
    ``gt=0.0`` and ``condition_decay_flux_coefficient`` is ``gt=0.0``
    (config/defines/transport.py:59-78), and ``conductivity`` is ``ge=0.0``
    (domain/geography/types.py:127-129) -- so ``delta`` is always strictly
    negative: condition can only fall or hold at its clamp floor, never
    rise. The clamp itself is ``inventory.py:149``
    (``max(0.0, min(1.0, ...))``)."""

    @given(
        condition=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        conductivity=st.floats(min_value=0.0, max_value=10.0, allow_nan=False),
        decay_rate=st.floats(min_value=1e-4, max_value=0.999, allow_nan=False),
        flux_coefficient=st.floats(min_value=1e-4, max_value=5.0, allow_nan=False),
    )
    @settings(max_examples=25, deadline=None)
    def test_condition_never_rises_and_stays_in_bounds(
        self,
        condition: float,
        conductivity: float,
        decay_rate: float,
        flux_coefficient: float,
    ) -> None:
        inventory = DefaultInfrastructureInventory()
        inventory.add_edge_link(
            "h1", "h2", _make_link("L", condition=condition, conductivity=conductivity)
        )
        mesh = CorridorMesh(
            inventory=inventory,
            territory_hexes={"T001": frozenset({"h1"}), "T002": frozenset({"h2"})},
        )
        graph = _graph_with_territory("T001")
        graph.add_node("T002", _node_type="territory")
        services = _services(
            TransportDefines(
                enabled=True,
                condition_decay_rate_per_tick=decay_rate,
                condition_decay_flux_coefficient=flux_coefficient,
            )
        )
        context = TickContext(tick=1)
        context.persistent_data["corridor_mesh"] = mesh

        TransportSystem().step(graph, services, context)

        new_condition = mesh.inventory.get_edge_links("h1", "h2")[0].condition
        assert 0.0 <= new_condition <= 1.0
        assert new_condition <= condition + 1e-12


class TestDemandSignalNeverNegative:
    """L2: ``_demand_signal`` (engine/systems/transport.py:89-104) is
    ``max(0.0, avg_conductivity - threshold) + (1.0 - avg_condition)``.
    ``avg_condition`` is a mean of values each bounded to ``[0.0, 1.0]``
    (``InfrastructureLinkState.condition``, types.py:113-118), so the
    second term is always ``>= 0.0``; the first term is a ``max(0.0, ...)``
    by construction. Sum of two non-negative terms is never negative."""

    @given(
        condition=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        conductivity=st.floats(min_value=0.0, max_value=10.0, allow_nan=False),
        threshold=st.floats(min_value=0.0, max_value=5.0, allow_nan=False),
    )
    @settings(max_examples=25, deadline=None)
    def test_signal_is_never_negative(
        self, condition: float, conductivity: float, threshold: float
    ) -> None:
        inventory = DefaultInfrastructureInventory()
        inventory.add_edge_link(
            "h1", "h2", _make_link("L", condition=condition, conductivity=conductivity)
        )
        mesh = CorridorMesh(inventory=inventory, territory_hexes={"T001": frozenset({"h1"})})
        graph = _graph_with_territory("T001")
        services = _services(TransportDefines(enabled=True, demand_signal_threshold=threshold))
        context = TickContext(tick=1)
        context.persistent_data["corridor_mesh"] = mesh

        TransportSystem().step(graph, services, context)

        signal = graph.nodes["T001"]["transport_demand_signal"]
        assert signal >= 0.0


class TestInactivityIsAFullNoOp:
    """L3: the master gate (``engine/systems/transport.py:134-136``,
    ``if not defines.enabled: return``) and the mesh-presence check
    (``:138-140``, ``if mesh is None: return``) each short-circuit before
    any mutation -- an honest absence (Constitution III.11), never a
    fabricated signal."""

    @pytest.mark.parametrize(
        "enabled,provide_mesh",
        [(False, True), (False, False), (True, False)],
    )
    def test_disabled_or_meshless_tick_writes_nothing(
        self, enabled: bool, provide_mesh: bool
    ) -> None:
        graph = _graph_with_territory("T001")
        services = _services(TransportDefines(enabled=enabled))
        context = TickContext(tick=1)
        if provide_mesh:
            context.persistent_data["corridor_mesh"] = CorridorMesh(
                inventory=DefaultInfrastructureInventory(),
                territory_hexes={"T001": frozenset({"h1"})},
            )

        TransportSystem().step(graph, services, context)

        assert "corridor_connectivity" not in context.persistent_data
        assert "transport_overhang_delta" not in context.persistent_data
        assert "transport_demand_signal" not in graph.nodes["T001"]


class TestConnectivityAggregationInvariant:
    """L4: ``aggregate_connectivity_by_county_pair``
    (domain/geography/corridor_mesh.py:157-203) skips same-territory edges
    (``:199-200``, ``if t_a == t_b: continue``) and always emits the
    lexicographically-sorted pair (``:201``,
    ``(t_a, t_b) if t_a < t_b else (t_b, t_a)``) -- exercised directly (not
    via ``TransportSystem.step``) since it is the pure aggregation function
    the system publishes verbatim into ``persistent_data``."""

    def test_no_self_pairs_and_keys_are_canonically_sorted(self) -> None:
        inventory = DefaultInfrastructureInventory()
        # h1, h2 both belong to T001: an intra-territory edge.
        inventory.add_edge_link("h1", "h2", _make_link("intra"))
        # h2, h3: h2 in T001, h3 in T002 -- an inter-territory edge.
        inventory.add_edge_link("h2", "h3", _make_link("inter"))
        mesh = CorridorMesh(
            inventory=inventory,
            territory_hexes={
                "T001": frozenset({"h1", "h2"}),
                "T002": frozenset({"h3"}),
            },
        )

        connectivity = aggregate_connectivity_by_county_pair(mesh)

        assert ("T001", "T001") not in connectivity
        for pair in connectivity:
            assert pair[0] < pair[1]
        assert connectivity == {("T001", "T002"): pytest.approx(1.0)}

    def test_empty_mesh_yields_empty_connectivity(self) -> None:
        mesh = CorridorMesh(inventory=DefaultInfrastructureInventory(), territory_hexes={})
        assert aggregate_connectivity_by_county_pair(mesh) == {}
