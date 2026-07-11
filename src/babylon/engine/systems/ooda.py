"""OODA Loop System — organizational action resolution (Feature 032).

Orchestrates the three-layer turn resolution each tick:
1. Layer 0: Automatic metabolism (Business self-sustaining activity)
2. Action Phase: Initiative-ordered organizational actions
3. Layer 3: Consequence propagation (consciousness, heat, edges, infrastructure)

See Also:
    ``specs/032-ooda-loop-system/spec.md``
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any, ClassVar

from babylon.kernel.system_base import SystemBase
from babylon.kernel.system_protocol import ContextType
from babylon.models.enums import EventType, OrgType
from babylon.ooda.cycle_time import compute_cycle_time
from babylon.ooda.initiative import (
    compute_community_embeddedness,
    compute_initiative_score,
    resolve_action_order,
)
from babylon.ooda.layer0 import process_layer0
from babylon.ooda.layer3 import process_layer3
from babylon.ooda.npc_stub import select_npc_actions
from babylon.ooda.types import ActionResult, InitiativeScore, OODAProfile, TurnResolution

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol
    from babylon.topology.graph import BabylonGraph


def _compat_graph(graph: GraphProtocol) -> BabylonGraph:
    """Narrow a ``step()`` graph argument to the nx-compat world surface.

    Helper (Amendment L) for subsystem helpers that read/write raw payload
    dicts (``graph.nodes(data=True)``, ``graph.edges[u, v][...]``) —
    BabylonGraph's permanent authoring surface (constitution II.12). Lives
    engine-side because it downcasts to the concrete topology substrate,
    which the kernel base class must not import (Program 14 layering).

    Raises:
        TypeError: If the backend does not expose that surface.
    """
    from babylon.topology.graph import BabylonGraph

    if isinstance(graph, BabylonGraph):
        return graph
    raise TypeError(f"Unsupported graph backend: {type(graph).__name__}")


class OODASystem(SystemBase):
    """Orchestrates organizational action resolution each tick.

    Three-phase turn resolution:
    1. Layer 0 — automatic metabolism for Business orgs
    2. Action Phase — initiative-ordered actions for all orgs
    3. Layer 3 — consequence propagation
    """

    # Spec 053 INV-001: does not mutate hex c+v+s; opted in by default-deny.
    creates_value: ClassVar[bool] = False

    name: ClassVar[str] = "ooda"

    def step(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
    ) -> None:
        """Execute OODA loop for all organizations.

        Args:
            graph: Mutable world graph.
            services: ServicesProtocol with defines, event_bus.
            context: TickContext or dict with 'tick'.
        """
        defines = services.defines.ooda
        tick = context.get("tick", 0) if isinstance(context, dict) else getattr(context, "tick", 0)

        # Amendment L transition: subsystem helpers (layer0/layer3/effects)
        # still speak the nx-compat payload surface; narrow once here.
        graph = _compat_graph(graph)

        # --- Phase 1: Layer 0 (automatic metabolism) ---
        layer0_results = process_layer0(graph, services)

        # --- Phase 2: Action Phase ---
        # Collect all org nodes
        org_nodes = _collect_org_nodes(graph)

        # Compute initiative scores
        initiative_scores = []
        max_orgs = 1000
        for org_id, org_data in org_nodes[:max_orgs]:
            profile_data = org_data.get("ooda_profile", {})
            profile = OODAProfile(**profile_data) if profile_data else OODAProfile()

            cycle_time = compute_cycle_time(profile, defines)

            # Jurisdiction for state apparatus
            jurisdiction = None
            if org_data.get("org_type") == OrgType.STATE_APPARATUS.value:
                from babylon.models.enums import JurisdictionLevel

                jur_val = org_data.get("jurisdiction")
                if jur_val:
                    with contextlib.suppress(ValueError):
                        jurisdiction = JurisdictionLevel(jur_val)

            counter_intel = float(org_data.get("counter_intel_score", 0.0))
            embeddedness = compute_community_embeddedness(org_id, graph)
            momentum = float(org_data.get("momentum", 0.0))

            score = compute_initiative_score(
                org_id=org_id,
                cycle_time=cycle_time,
                jurisdiction=jurisdiction,
                counter_intel_score=counter_intel,
                community_embeddedness=embeddedness,
                momentum=momentum,
                defines=defines,
            )
            initiative_scores.append(score)

        # Sort by initiative
        initiative_order = resolve_action_order(initiative_scores)

        # Resolve actions in initiative order
        action_phase_results: list[ActionResult] = []

        # Get player actions from context
        player_actions: dict[str, Any] = {}
        if isinstance(context, dict):
            player_actions = context.get("persistent_data", {}).get("player_actions", {})
        else:
            pd = getattr(context, "persistent_data", {})
            player_actions = pd.get("player_actions", {}) if isinstance(pd, dict) else {}

        # Lift org_data_lookup outside the loop (was reconstructed per-iteration
        # in the original inline loop body; identical result, smaller alloc).
        org_data_lookup = dict(org_nodes)

        max_actions_total = 500
        for score in initiative_order:
            if len(action_phase_results) >= max_actions_total:
                break
            new_results = self._resolve_for_organization(
                score=score,
                org_data_lookup=org_data_lookup,
                player_actions=player_actions,
                defines=defines,
                graph=graph,
                services=services,
            )
            action_phase_results.extend(new_results)

        # --- Phase 3: Layer 3 (consequence propagation) ---
        all_results = layer0_results + action_phase_results
        layer3_effects = process_layer3(all_results, graph, defines)

        # Publish the turn resolution on context so the web bridge (and any
        # downstream reader) sees the REAL per-action results instead of the
        # old pre/post diff fakery. mode="json" flattens the StrEnum/nested-
        # enum payloads the bridge persists; simulation_engine.step() syncs
        # context.persistent_data back to the caller's persistent_context.
        resolution = TurnResolution(
            tick=tick,
            layer0_results=layer0_results,
            initiative_order=initiative_order,
            action_phase_results=action_phase_results,
            layer3_effects=layer3_effects,
        )
        resolution_payload = resolution.model_dump(mode="json")
        if isinstance(context, dict):
            context.setdefault("persistent_data", {})["turn_resolution"] = resolution_payload
        else:
            context.persistent_data["turn_resolution"] = resolution_payload

        # Emit summary event
        if services.event_bus:
            from babylon.kernel.event_bus import Event

            services.event_bus.publish(
                Event(
                    type=EventType.ORGANIZATIONAL_ACTION,
                    tick=tick,
                    payload={
                        "layer0_count": len(layer0_results),
                        "action_count": len(action_phase_results),
                        "org_count": len(initiative_order),
                    },
                )
            )

    def _resolve_for_organization(
        self,
        score: InitiativeScore,
        org_data_lookup: dict[str, dict[str, Any]],
        player_actions: dict[str, Any],
        defines: Any,
        graph: BabylonGraph,
        services: ServicesProtocol,
    ) -> list[ActionResult]:
        """Resolve one organization's action(s) for the current tick.

        Extracted from ``step`` body for test-time instrumentation
        (Spec 056 US2 ``OrganizationActionSpy``). Behavior preserved;
        the refactor is purely structural — the inline loop body became
        a named method. ``unittest.mock.patch.object(OODASystem,
        "_resolve_for_organization", ...)`` is the canonical seam for
        per-organization action spying / interleaving simulations.

        Args:
            score: Initiative score for the organization being resolved.
            org_data_lookup: Pre-computed mapping of org_id → org_data
                dict (lifted out of the action-phase loop for efficiency).
            player_actions: Player-provided actions per org_id from the
                context's persistent_data.
            defines: OODA defines from services.defines.ooda.
            graph: Mutable world graph (threaded to the player-verb
                resolvers so they can apply real effects).
            services: ServicesProtocol (defines) for the resolvers.

        Returns:
            List of ``ActionResult`` produced for this organization
            (empty if the org is a Business — those are handled in
            Layer 0 — or if it produced no actions this tick).
        """
        org_data = org_data_lookup.get(score.org_id, {})

        # Skip Business orgs (handled in Layer 0)
        if org_data.get("org_type") == OrgType.BUSINESS.value:
            return []

        results: list[ActionResult] = []

        # Check for player-provided actions
        org_player_actions = player_actions.get(score.org_id)
        if org_player_actions:
            # Player actions dispatch through the verb-resolver registry for
            # REAL graph effects. A missing resolver yields a loud failure
            # ActionResult (never a silent success). Lazy import mirrors the
            # existing lazy-import style below and avoids any import cycle.
            from babylon.engine.actions import resolve_player_action

            for action_data in org_player_actions:
                action = (
                    action_data
                    if not isinstance(action_data, dict)
                    else _action_from_dict(action_data, score.org_id)
                )
                results.append(
                    resolve_player_action(
                        action=action,
                        org_attrs=org_data,
                        graph=graph,
                        services=services,
                    )
                )
        else:
            # NPC action selection
            territory_ids: list[str] = org_data.get("territory_ids", [])
            target_id = territory_ids[0] if territory_ids else score.org_id

            npc_actions = select_npc_actions(
                org_id=score.org_id,
                org_attrs=org_data,
                target_id=target_id,
                defines=defines,
            )
            for action in npc_actions:
                results.append(
                    ActionResult(
                        action=action,
                        success=True,
                        events_generated=[EventType.ORGANIZATIONAL_ACTION.value],
                    )
                )

        return results


def _collect_org_nodes(graph: BabylonGraph) -> list[tuple[str, dict[str, Any]]]:
    """Collect all organization nodes from the graph.

    Args:
        graph: World graph.

    Returns:
        List of (node_id, node_data) for organization nodes.
    """
    orgs: list[tuple[str, dict[str, Any]]] = []
    max_nodes = 1000
    for node_id, data in graph.nodes(data=True):
        if data.get("_node_type") == "organization":
            orgs.append((node_id, dict(data)))
        if len(orgs) >= max_nodes:
            break
    return orgs


def _action_from_dict(data: dict[str, Any], org_id: str) -> Any:
    """Convert a dict to an Action instance.

    Args:
        data: Action dict with action_type, target_id, etc.
        org_id: Fallback org_id if not in dict.

    Returns:
        Action instance.
    """
    from babylon.ooda.types import Action

    return Action(
        org_id=data.get("org_id", org_id),
        action_type=data["action_type"],
        target_id=data["target_id"],
        action_point_cost=data.get("action_point_cost", 1),
        params=data.get("params", {}),
    )
