"""Transport Substrate system (spec-108, Constitution II.13/Amendment O).

Program 26 U5e (engine train), slice 1. Position 9.5 -- immediately after
:class:`~babylon.engine.systems.economic.ImperialRentSystem` (9.0) and
before :class:`~babylon.engine.systems.dispossession_events.DispossessionEventSystem`
(10.0), per ``specs/108-transport-substrate/plan.md``'s primary candidate.

**Materialist-causality justification.** This system operates on the
corridor mesh -- the physical substrate mediating Volume II circulation --
so it must run AFTER Production (@3.0) has generated the tick's material
output and AFTER ImperialRent (@9.0) has moved value through the 5-phase
imperial circuit (the mesh's demand signal should reflect a materially
fresh tick, not a stale one), but strictly BEFORE the Action phase
(:class:`~babylon.engine.systems.ooda.OODASystem` @14.0) so a fresh demand
signal is available for the sovereign's OODA budget evaluation (ADR165 item
2's design reframe) THIS tick, and so the corridor mesh this system decays
is the SAME mesh object layer-3's consequence pass
(:func:`babylon.ooda.layer3._propagate_infrastructure`, invoked from inside
OODASystem @14.0) applies BUILD/ATTACK uniform-splash to (ADR165 item 4,
T6) -- Consequences (@14.5+) then see this tick's already-decayed,
already-splashed mesh state, never a stale snapshot.

**Default-OFF.** ``TransportDefines.enabled`` is the master gate
(program-11's own constraint: "defines-gated... default OFF -> baselines
byte-identical"). A disabled or mesh-less tick is a full no-op --
:class:`~babylon.domain.geography.corridor_mesh.CorridorMesh` is composed by
a separate, later loader/composer unit (mirrors the ``vol2_step`` gated-
no-op precedent, spec-108 FR-108-10) and stored into
``context.persistent_data["corridor_mesh"]`` before this system can act on
it; its absence is an honest absence (Constitution III.11), never a
fabricated signal.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, ClassVar

from babylon.domain.geography.corridor_mesh import (
    CorridorMesh,
    aggregate_connectivity_by_county_pair,
    decay_all_links,
    touching_link_ids,
)
from babylon.kernel.system_base import SystemBase
from babylon.kernel.tick_partition import TickPartition

if TYPE_CHECKING:
    from babylon.config.defines import TransportDefines
    from babylon.domain.geography.types import InfrastructureLinkState
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol
    from babylon.kernel.system_protocol import ContextType


def compute_overhang_delta(stranded_value_ratio: float, damping_coefficient: float) -> float:
    """Pure coupling function for the realization-crisis coupling (D4, T10).

    ``delta = clamp(stranded_value_ratio, 0.0, 1.0) * damping_coefficient``
    -- the damped share of transport-stranded value that would feed into
    ``commodity_overhang`` (spec-108 FR-108-3 third bullet: unrouted goods
    are commodity-capital stuck at C', unable to realize as M').

    **Not yet wired** into
    ``assess_circulation_crisis``'s call site (``_compute_county_circulation_state``)
    -- tasks.md T10's own prerequisite (resolve the ``CirculationCrisisAssessment``
    vs. ``RealizationCrisis`` ambiguity, research.md S8) is an unaudited
    ownership question for a P25/covenant-sensitive module this delegated
    unit did not open. Provided, tested, and called from
    :meth:`TransportSystem.step` (result stored in
    ``context.persistent_data["transport_overhang_delta"]``) so a future
    wiring pass has a real, calibratable coupling function rather than a
    hardcoded literal.

    Args:
        stranded_value_ratio: Fraction of corridor-mesh capacity currently
            degraded (a proxy for stranded freight/labor value until a real
            FAF-derived magnitude exists, U3).
        damping_coefficient: ``CapitalVolumeIIDefines.transport_overhang_damping_coefficient``
            (ADR165 Director ruling 3).

    Returns:
        The damped delta, always ``>= 0.0``.
    """
    clamped_ratio = max(0.0, min(1.0, stranded_value_ratio))
    return clamped_ratio * damping_coefficient


def _demand_signal(links: Sequence[InfrastructureLinkState], threshold: float) -> float:
    """SYNTHETIC demand-signal formula for a territory's touching links.

    ``max(0, avg_conductivity - threshold) + (1 - avg_condition)`` --
    conductivity sustained above the Director-ruled threshold (ADR165 item
    2) contributes directly; degraded condition contributes regardless of
    threshold (a territory can need repair even with low usage pressure).
    Not derived from a Marx numerical illustration (unlike e.g.
    ``dept_i_share_required``) -- a slice-1 engineering proposal, flagged
    SYNTHETIC per this worktree's `InfrastructureDefines` precedent.
    """
    if not links:
        return 0.0
    avg_condition = sum(link.condition for link in links) / len(links)
    avg_conductivity = sum(link.conductivity for link in links) / len(links)
    return max(0.0, avg_conductivity - threshold) + (1.0 - avg_condition)


class TransportSystem(SystemBase):
    """Corridor condition decay + demand-signal + connectivity aggregation.

    See the module docstring for the position/materialist-causality
    justification and the default-OFF gate.
    """

    partition: ClassVar[TickPartition] = TickPartition.MATERIAL_BASE
    position: ClassVar[float] = 9.5
    name: ClassVar[str] = "Transport Substrate"

    def step(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
    ) -> None:
        """Decay the corridor mesh, publish demand signals + connectivity.

        Args:
            graph: World graph (mutated in place — territory demand-signal
                writes only).
            services: ServicesProtocol supplying ``defines.transport``.
            context: TickContext — reads/writes ``persistent_data["corridor_mesh"]``,
                writes ``persistent_data["corridor_connectivity"]`` and
                ``persistent_data["transport_overhang_delta"]``.
        """
        defines: TransportDefines = services.defines.transport
        if not defines.enabled:
            return

        mesh: CorridorMesh | None = context.persistent_data.get("corridor_mesh")
        if mesh is None:
            return

        decay_all_links(
            mesh,
            defines.condition_decay_rate_per_tick,
            defines.condition_decay_flux_coefficient,
        )

        connectivity = aggregate_connectivity_by_county_pair(mesh)
        context.persistent_data["corridor_connectivity"] = connectivity

        links_by_id: dict[str, InfrastructureLinkState] = {
            link.link_id: link
            for source_h3, target_h3 in mesh.inventory.get_all_edges()
            for link in mesh.inventory.get_edge_links(source_h3, target_h3)
        }

        overhang_ratios: list[float] = []
        for territory_id in sorted(mesh.territory_hexes):
            links = [links_by_id[link_id] for link_id in touching_link_ids(mesh, territory_id)]
            if not links:
                continue

            overhang_ratios.append(1.0 - sum(link.condition for link in links) / len(links))

            if graph.get_node(territory_id) is None:
                continue
            signal = _demand_signal(links, defines.demand_signal_threshold)
            graph.update_node(territory_id, transport_demand_signal=signal)

        # Aggregate national stranded-value proxy (mean degradation ratio
        # across every territory this tick touched) — T10's coupling
        # function, damping coefficient sourced from CapitalVolumeIIDefines
        # (ADR165 item 3, NOT TransportDefines).
        national_ratio = sum(overhang_ratios) / len(overhang_ratios) if overhang_ratios else 0.0
        context.persistent_data["transport_overhang_delta"] = compute_overhang_delta(
            national_ratio,
            services.defines.capital_vol2.transport_overhang_damping_coefficient,
        )

        # Keep the (mutated) mesh available for layer3's uniform-splash
        # consumption later this same tick (T6/ADR165 item 4).
        context.persistent_data["corridor_mesh"] = mesh


__all__ = ["TransportSystem", "compute_overhang_delta"]
