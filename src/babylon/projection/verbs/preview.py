"""Per-verb preview estimates — resolver-parity where a resolver exists.

Port of the legacy bridge's ``preview_action`` + ``_preview_consciousness_delta``
(``web/game/engine_bridge.py``) into the projection layer (WO-38). Pure and
read-only over the graph: no session hydration, no mutation, no engine
import. The consciousness verbs (EDUCATE / CAMPAIGN / AID) source their
estimate from the SAME pure helper their resolvers call
(:func:`babylon.ooda.action_effects.compute_consciousness_delta`), so
preview == resolution (spec-116 FR-4.4); the remaining verbs pin the
documented heuristics the legacy preview shipped.
"""

from __future__ import annotations

from typing import Any

from babylon.config.defines import GameDefines
from babylon.models.enums import ActionType
from babylon.projection.verbs.view_models import VerbPreview
from babylon.topology import BabylonGraph

#: The nine canonical Article V player verbs, in plate order, mapped onto
#: the engine's OODA ``ActionType`` vocabulary. Relocated from the legacy
#: bridge (which now imports it back from here).
VERB_TO_ACTION_TYPE: dict[str, ActionType] = {
    "educate": ActionType.EDUCATE,
    "reproduce": ActionType.RECRUIT,
    "attack": ActionType.ATTACK_INFRASTRUCTURE,
    "mobilize": ActionType.PROTEST,
    "campaign": ActionType.PROPAGANDIZE,
    "aid": ActionType.PROVIDE_SERVICE,
    "investigate": ActionType.MAP_NETWORK,
    "move": ActionType.MOVE,
    "negotiate": ActionType.PROPOSE_ALLIANCE,
}

CANONICAL_VERBS: frozenset[str] = frozenset(VERB_TO_ACTION_TYPE)

#: Verbs whose CI estimate comes from the resolvers' own math.
_CONSCIOUSNESS_VERBS: frozenset[str] = frozenset({"educate", "campaign", "aid"})


def preview_consciousness_delta(
    org_data: dict[str, Any],
    target_id: str,
    action_type: ActionType,
    graph: BabylonGraph,
    *,
    defines: GameDefines | None = None,
) -> float:
    """Read-only CI estimate for the preview, via the resolvers' own math.

    Calls :func:`babylon.ooda.action_effects.compute_consciousness_delta`
    (pure, no mutation) so the preview reports the same collective-identity
    delta the EDUCATE / CAMPAIGN / AID resolvers would produce.

    ``compute_consciousness_delta``'s Step-7.5 doctrine theory bonus
    (ADR073) is gated only on ``doctrine is not None`` — NOT on
    ``action_type`` — so it must be threaded through exactly as each real
    resolver does, not passed unconditionally:

    - ``resolve_educate`` and ``resolve_campaign`` both call
      ``resolve_action(..., doctrine=services.defines.doctrine)``, so
      EDUCATE and CAMPAIGN previews include the bonus.
    - ``resolve_aid`` calls ``compute_consciousness_delta`` directly WITHOUT
      ``doctrine`` (defaults to ``None``), so the AID preview must omit it
      too — passing it unconditionally would OVER-state AID's estimate.

    :param org_data: Acting org node attributes (live payload; not mutated).
    :param target_id: Target community/entity id.
    :param action_type: The mapped engine ``ActionType``.
    :param graph: World graph (read-only).
    :param defines: Coefficient source; defaults to schema-default
        ``GameDefines()`` exactly as the legacy preview did (the defaults
        are sync-guarded against ``defines.yaml``).
    :returns: The estimated collective-identity delta, or ``0.0`` when the
        action has no consciousness effect.
    """
    from babylon.ooda.action_effects import compute_consciousness_delta

    resolved_defines = defines if defines is not None else GameDefines()
    doctrine = (
        resolved_defines.doctrine
        if action_type in (ActionType.EDUCATE, ActionType.PROPAGANDIZE)
        else None
    )
    delta = compute_consciousness_delta(
        org_data,
        target_id,
        action_type,
        graph,
        resolved_defines.ooda,
        resolved_defines.organization,
        doctrine,
    )
    return float(delta.collective_identity_delta) if delta is not None else 0.0


def preview_verb(
    graph: BabylonGraph,
    org_id: str,
    verb: str,
    *,
    target_id: str | None = None,
    defines: GameDefines | None = None,
) -> VerbPreview:
    """Estimate a proposed verb's effects without mutating state.

    Field-for-field port of the legacy ``preview_action`` minus session
    hydration — the caller supplies the graph. Read-only.

    :param graph: World graph (read-only).
    :param org_id: The acting organization id.
    :param verb: One of the nine canonical player verbs.
    :param target_id: Optional target territory or entity id; absent, the
        acting org is the resolved target (target-less plate preview).
    :param defines: Coefficient source for the consciousness estimate.
    :returns: The frozen preview estimate.
    :raises ValueError: If ``verb`` is not one of the nine canonical verbs
        (a caller bug — fail loud, Constitution III.11).
    """
    if verb not in CANONICAL_VERBS:
        raise ValueError(
            f"{verb!r} is not a canonical verb (expected one of {sorted(CANONICAL_VERBS)})"
        )

    action_type_enum = VERB_TO_ACTION_TYPE[verb]
    action_cost = 1.0
    warnings: list[str] = []
    affected_territory_ids: list[str] = []

    if org_id not in graph.nodes:
        return VerbPreview(
            estimated_consciousness_delta=0.0,
            estimated_heat_delta=0.0,
            action_point_cost=action_cost,
            success_probability=0.0,
            affected_territory_ids=(),
            warnings=(f"Organization '{org_id}' not found",),
        )

    org_data = graph.nodes[org_id]
    org_budget = float(org_data.get("budget", 0.0))
    org_heat = float(org_data.get("heat", 0.0))
    org_cohesion = float(org_data.get("cohesion", 0.5))

    if org_budget < action_cost:
        warnings.append("Insufficient budget for this action")
    if org_heat > 0.7:
        warnings.append("Organization heat is already elevated")

    estimated_consciousness_delta = 0.0
    estimated_heat_delta = 0.0
    success_probability = 0.5

    resolved_target = target_id or org_id
    if resolved_target in graph.nodes:
        target_data = graph.nodes[resolved_target]
        if target_data.get("under_eviction", False):
            warnings.append("Target territory is under eviction")

        if verb in _CONSCIOUSNESS_VERBS:
            estimated_consciousness_delta = preview_consciousness_delta(
                dict(org_data), resolved_target, action_type_enum, graph, defines=defines
            )
            estimated_heat_delta = -0.01 if verb == "aid" else 0.01
            success_probability = min(0.95, 0.4 + org_cohesion * 0.5)
        elif verb in {"attack", "mobilize"}:
            estimated_consciousness_delta = 0.02
            estimated_heat_delta = 0.08 * org_cohesion
            success_probability = min(0.8, 0.3 + org_cohesion * 0.4)
        elif verb == "reproduce":
            estimated_consciousness_delta = 0.01
            estimated_heat_delta = -0.01
            success_probability = min(0.95, 0.5 + org_cohesion * 0.4)
        elif verb in {"investigate", "negotiate", "move"}:
            estimated_consciousness_delta = 0.0
            estimated_heat_delta = 0.0
            success_probability = min(0.9, 0.6 + org_cohesion * 0.3)

        territory_ids = org_data.get("territory_ids", [])
        if isinstance(territory_ids, (list, tuple)):
            affected_territory_ids = [str(t) for t in territory_ids]
        if target_id and target_id not in affected_territory_ids:
            affected_territory_ids.append(target_id)
    else:
        warnings.append(f"Target '{resolved_target}' not found in current state")

    return VerbPreview(
        estimated_consciousness_delta=round(estimated_consciousness_delta, 4),
        estimated_heat_delta=round(estimated_heat_delta, 4),
        action_point_cost=action_cost,
        success_probability=round(success_probability, 4),
        affected_territory_ids=tuple(affected_territory_ids),
        warnings=tuple(warnings),
    )
