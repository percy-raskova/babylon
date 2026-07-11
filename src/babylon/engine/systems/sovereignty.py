"""Spec-070 SovereigntySystem (T042, FR-019, FR-020, FR-035, FR-043).

Reads Sovereign nodes + their CLAIMS edges, computes per-Territory
``metabolic_impact`` (FR-019) and ``effective_controller`` (FR-020),
publishes them via ``context.persistent_data`` for the MetabolismSystem
extension to consume (FR-043), and emits ``DUAL_POWER_ACTIVE`` when
multiple Sovereigns hold non-zero CLAIMS on the same Territory
(FR-035).

Pipeline position: ~17.5 (between ConsciousnessSystem at 17 and
ContradictionSystem at 18). Belongs to ``CONSEQUENCE_SYSTEMS`` per
spec-056 partition + spec-070 FR-042.

Determinism notes (III.7):

- Effective-controller tiebreak (when two CLAIMS edges have identical
  ``control_level``) uses Sovereign ID lexicographic ordering (handled
  by :meth:`GraphProtocol.query_territory_claims` which sorts by
  ``(-control_level, sovereign_id)``).
- DUAL_POWER_ACTIVE event emission is per-Territory in sorted-ID order.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any, ClassVar

from babylon.formulas.balkanization import calculate_metabolic_impact
from babylon.kernel.event_bus import Event
from babylon.kernel.system_base import SystemBase
from babylon.models.enums import EventType, ExtractionPolicy

if TYPE_CHECKING:  # pragma: no cover
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol
    from babylon.kernel.system_protocol import ContextType


class SovereigntySystem(SystemBase):
    """Crystallizes Sovereign extraction policy into per-Territory
    metabolic impact (FR-019, FR-043) + diagnoses dual-power
    configurations (FR-035).

    Reads:
        - Sovereign nodes (``_node_type == "sovereign"``).
        - CLAIMS edges incident to each Sovereign.

    Writes (via ``context.persistent_data``):
        - ``balkanization.metabolic_impact_by_territory``:
          ``{territory_id -> float}`` of the effective metabolic_impact
          to apply (sum across CLAIMS edges weighted by control_level —
          but per FR-020 + the data-model.md effective-controller
          resolution, only the highest-control_level Sovereign's
          impact applies, not double-counted).
        - ``balkanization.effective_controller_by_territory``:
          ``{territory_id -> sovereign_id}`` mapping for downstream
          systems.

    Emits:
        - ``DUAL_POWER_ACTIVE`` per Territory where ≥2 CLAIMS edges
          have ``control_level > 0.0`` (FR-035).
    """

    name: ClassVar[str] = "Sovereignty"
    creates_value: ClassVar[bool] = False

    def step(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
    ) -> None:
        wrapped = self._wrap_graph(graph)
        tick = self._extract_tick(context)
        persistent = self._extract_persistent(context)

        # Resolve effective controller + metabolic_impact per Territory.
        impact_by_territory: dict[str, float] = {}
        controller_by_territory: dict[str, str] = {}
        dual_power_territories: list[tuple[str, list[str], float]] = []

        # Enumerate territories deterministically by node ID.
        territory_ids = sorted(node.id for node in wrapped.query_nodes(node_type="territory"))
        for territory_id in territory_ids:
            claims = wrapped.query_territory_claims(territory_id)
            if not claims:
                continue
            # FR-020: highest control_level wins (with sorted-ID tiebreak
            # already applied by query_territory_claims).
            controller_id, _control, _legal = claims[0]
            sov_node = wrapped.get_node(controller_id)
            if sov_node is None:
                continue
            policy = self._coerce_policy(sov_node.attributes.get("extraction_policy"))
            if policy is None:
                continue
            impact_by_territory[territory_id] = calculate_metabolic_impact(policy)
            controller_by_territory[territory_id] = controller_id

            # FR-035: emit DUAL_POWER_ACTIVE if ≥2 Sovereigns have
            # control_level > 0.0.
            active_claimants = [row for row in claims if row[1] > 0.0]
            if len(active_claimants) >= 2:
                dual_power_territories.append(
                    (
                        territory_id,
                        [row[0] for row in active_claimants],
                        sum(row[1] for row in active_claimants),
                    )
                )

        persistent["balkanization.metabolic_impact_by_territory"] = impact_by_territory
        persistent["balkanization.effective_controller_by_territory"] = controller_by_territory

        # Re-attach persistent_data into context (in case context.persistent_data
        # was None before).
        if isinstance(context, dict):
            context.setdefault("persistent_data", persistent)
            context["persistent_data"] = persistent
        else:
            with contextlib.suppress(AttributeError):
                context.persistent_data = persistent

        # Emit DUAL_POWER_ACTIVE events in sorted-territory order.
        for territory_id, competing, control_sum in dual_power_territories:
            self._publish(
                services,
                Event(
                    type=EventType.DUAL_POWER_ACTIVE,
                    tick=tick,
                    payload={
                        "territory_id": territory_id,
                        "competing_sovereign_ids": sorted(competing),
                        "control_level_sum": control_sum,
                    },
                ),
            )

    @staticmethod
    def _extract_tick(context: ContextType) -> int:
        tick = context.get("tick", 0) if isinstance(context, dict) else getattr(context, "tick", 0)
        return int(tick)

    @staticmethod
    def _extract_persistent(context: ContextType) -> dict[str, Any]:
        if isinstance(context, dict):
            persistent = context.get("persistent_data")
            if persistent is None:
                persistent = {}
                context["persistent_data"] = persistent
            return dict(persistent) if not isinstance(persistent, dict) else persistent
        existing = getattr(context, "persistent_data", None)
        if existing is None:
            return {}
        if isinstance(existing, dict):
            return existing
        return dict(existing)

    @staticmethod
    def _coerce_policy(raw: object) -> ExtractionPolicy | None:
        if raw is None:
            return None
        if isinstance(raw, ExtractionPolicy):
            return raw
        if not isinstance(raw, str):
            return None
        try:
            return ExtractionPolicy(raw)
        except (ValueError, KeyError):
            return None
