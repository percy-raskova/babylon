"""Action resolution and consciousness effects (Feature 032).

Extends the Feature 031 five-factor consciousness formula with
action-type-specific multipliers, membership overlap credibility,
AGITATE-EDUCATE coupling, and per-tick delta clamping.

See Also:
    ``specs/032-ooda-loop-system/contracts/consciousness-effect-contract.md``
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.config.defines import OODADefines, OrganizationDefines, ReactionaryDefines
from babylon.models.enums import ActionType, ConsciousnessTendency, EdgeType, EventType
from babylon.ooda._helpers import _compute_membership_overlap
from babylon.ooda.types import Action, ActionResult
from babylon.organizations.consciousness import tendency_modifier
from babylon.organizations.types import ConsciousnessDelta

if TYPE_CHECKING:
    from babylon.engine.graph import BabylonGraph

# The fascist action verbs (spec-071) and their emitted event types.
_FASCIST_VERBS: dict[ActionType, EventType] = {
    ActionType.POGROM: EventType.POGROM,
    ActionType.LOCKOUT: EventType.LOCKOUT,
    ActionType.VIGILANTISM: EventType.VIGILANTISM,
}


def compute_consciousness_delta(
    org_attrs: dict[str, Any],
    target_community_id: str,
    action_type: ActionType,
    graph: BabylonGraph,
    defines: OODADefines,
    org_defines: OrganizationDefines,
) -> ConsciousnessDelta | None:
    """Compute consciousness effect of an action on a target community.

    Args:
        org_attrs: Organization node attributes dict.
        target_community_id: Target community node ID.
        action_type: The action being performed.
        graph: World graph.
        defines: OODADefines coefficients.
        org_defines: OrganizationDefines for credibility/tendency.

    Returns:
        ConsciousnessDelta or None if action has no CI effect.
    """
    action_base = _get_effective_action_base(action_type, org_attrs, defines)
    if action_base == 0.0:
        return None

    org_id = str(org_attrs.get("id", ""))
    tendency_str = org_attrs.get("consciousness_tendency", "liberal")
    tendency = ConsciousnessTendency(tendency_str)
    cadre_level = float(org_attrs.get("cadre_level", 0.0))
    cohesion = float(org_attrs.get("cohesion", 0.0))

    # Short-circuit on zero factors
    if cadre_level == 0.0 or cohesion == 0.0:
        return ConsciousnessDelta(
            collective_identity_delta=0.0,
            tendency_pressure=tendency,
            tendency_magnitude=0.0,
            source_org_id=org_id,
        )

    # Step 2-3: Membership overlap and effective credibility
    overlap = _compute_membership_overlap(org_id, target_community_id, graph)
    base_credibility = _derive_credibility_from_attrs(org_attrs, org_defines)
    effective_credibility = base_credibility * max(overlap, 0.01)

    # Step 4: Base delta (five-factor formula)
    modifier = tendency_modifier(tendency, org_defines)
    base_delta = modifier * cadre_level * cohesion * effective_credibility

    # Step 5: Scale by action base
    scaled_delta = base_delta * action_base

    # Step 7: EDUCATE contestation bonus
    if action_type == ActionType.EDUCATE:
        target_data = graph.nodes.get(target_community_id, {})
        contestation = float(target_data.get("ideological_contestation", 0.0))
        if contestation > defines.contestation_threshold:
            scaled_delta *= defines.agitation_educate_bonus

    # Step 8: Clamp to max per-tick delta
    scaled_delta = max(
        -defines.max_ci_delta_per_tick,
        min(defines.max_ci_delta_per_tick, scaled_delta),
    )

    return ConsciousnessDelta(
        collective_identity_delta=scaled_delta,
        tendency_pressure=tendency,
        tendency_magnitude=abs(scaled_delta),
        source_org_id=org_id,
    )


def resolve_action(
    action: Action,
    org_attrs: dict[str, Any],
    graph: BabylonGraph,
    defines: OODADefines,
    org_defines: OrganizationDefines,
    reactionary: ReactionaryDefines | None = None,
) -> ActionResult:
    """Resolve a single action, computing effects.

    Args:
        action: The action to resolve.
        org_attrs: Acting organization's node attributes.
        graph: World graph.
        defines: OODADefines coefficients.
        org_defines: OrganizationDefines for credibility.
        reactionary: ReactionaryDefines for the spec-071 fascist verbs
            (POGROM / LOCKOUT / VIGILANTISM). Pass ``services.defines.reactionary``
            so verb effects honor any ``defines.yaml`` override (III.5);
            defaults to the dataclass defaults when omitted.

    Returns:
        ActionResult with success status and effects.
    """
    action_type = action.action_type
    target_id = action.target_id

    # Dispatch to specialized resolvers
    if action_type == ActionType.AGITATE:
        return _resolve_agitate(action, defines)

    if action_type in {ActionType.REPRESS, ActionType.SURVEIL}:
        return _resolve_repressive(action, org_attrs, graph, defines, org_defines)

    if action_type == ActionType.ASSIMILATE:
        return _resolve_assimilate(action, org_attrs, graph, defines, org_defines)

    if action_type in _FASCIST_VERBS:
        return _resolve_fascist_verb(action, graph, reactionary or ReactionaryDefines())

    # Consciousness-affecting actions
    ci_delta = compute_consciousness_delta(
        org_attrs,
        target_id,
        action_type,
        graph,
        defines,
        org_defines,
    )

    events: list[str] = [EventType.ORGANIZATIONAL_ACTION.value]

    return ActionResult(
        action=action,
        success=True,
        consciousness_delta=ci_delta,
        events_generated=events,
    )


def _resolve_fascist_verb(
    action: Action, graph: BabylonGraph, reactionary: ReactionaryDefines
) -> ActionResult:
    """Resolve a spec-071 fascist verb (POGROM / LOCKOUT / VIGILANTISM).

    Materially grounded, directly mutating the target's graph state:

    - **POGROM**: communal violence — raise the target's repression and
      destroy a fraction of its wealth.
    - **VIGILANTISM**: extra-state local repression — raise the target's
      repression.
    - **LOCKOUT**: the employer withdraws income — attenuate the target's
      incoming WAGES value_flow.

    All coefficients come from the caller-supplied :class:`ReactionaryDefines`
    (III.1 + III.5 — the run's defines, so ``defines.yaml`` overrides are
    honored, mirroring :class:`~babylon.engine.systems.reactionary.FascistFactionSystem`).
    """
    action_type = action.action_type
    target_id = action.target_id
    effects: dict[str, Any] = {}

    if action_type in {ActionType.POGROM, ActionType.VIGILANTISM} and target_id is not None:
        node = graph.get_node(target_id)
        if node is not None:
            increment = (
                reactionary.pogrom_repression_increment
                if action_type == ActionType.POGROM
                else reactionary.vigilantism_repression_increment
            )
            current_rep = float(node.attributes.get("repression_faced", 0.0))
            graph.update_node(target_id, repression_faced=min(1.0, current_rep + increment))
            effects["repression_increment"] = increment
            if action_type == ActionType.POGROM:
                current_wealth = float(node.attributes.get("wealth", 0.0))
                new_wealth = current_wealth * (1.0 - reactionary.pogrom_wealth_destruction)
                graph.update_node(target_id, wealth=new_wealth)
                effects["wealth_destroyed"] = current_wealth - new_wealth

    elif action_type == ActionType.LOCKOUT and target_id is not None:
        for edge in graph.query_edges(edge_type=EdgeType.WAGES):
            if edge.target_id != target_id:
                continue
            flow = float(edge.attributes.get("value_flow", 0.0))
            graph.update_edge(
                edge.source_id,
                edge.target_id,
                EdgeType.WAGES,
                value_flow=flow * (1.0 - reactionary.lockout_wage_attenuation),
            )
            effects["wage_attenuation"] = reactionary.lockout_wage_attenuation

    return ActionResult(
        action=action,
        success=True,
        direct_effects=effects,
        events_generated=[_FASCIST_VERBS[action_type].value],
    )


def _resolve_agitate(
    action: Action,
    defines: OODADefines,
) -> ActionResult:
    """AGITATE: no CI delta, increases contestation."""
    return ActionResult(
        action=action,
        success=True,
        consciousness_delta=None,
        direct_effects={
            "contestation_delta": defines.agitation_contestation_delta,
        },
        events_generated=[EventType.ORGANIZATIONAL_ACTION.value],
    )


def _resolve_repressive(
    action: Action,
    org_attrs: dict[str, Any],
    graph: BabylonGraph,  # noqa: ARG001 — reserved for future location-dependent backfire
    defines: OODADefines,
    org_defines: OrganizationDefines,
) -> ActionResult:
    """REPRESS/SURVEIL: backfire raises target CI."""
    action_type = action.action_type

    base_credibility = _derive_credibility_from_attrs(org_attrs, org_defines)
    action_base = defines.get_action_base(action_type.value)

    backfire_delta = action_base * base_credibility
    backfire_delta = min(backfire_delta, defines.max_ci_delta_per_tick)

    ci_delta = ConsciousnessDelta(
        collective_identity_delta=backfire_delta,
        tendency_pressure=ConsciousnessTendency.REVOLUTIONARY,
        tendency_magnitude=backfire_delta,
        source_org_id=str(org_attrs.get("id", "")),
    )

    event_type = (
        EventType.STATE_REPRESSION.value
        if action_type == ActionType.REPRESS
        else EventType.STATE_SURVEILLANCE.value
    )

    return ActionResult(
        action=action,
        success=True,
        consciousness_delta=ci_delta,
        direct_effects={"backfire": True},
        events_generated=[event_type],
    )


def _resolve_assimilate(
    action: Action,
    org_attrs: dict[str, Any],
    graph: BabylonGraph,  # noqa: ARG001 — reserved for future location-dependent assimilation
    defines: OODADefines,
    org_defines: OrganizationDefines,
) -> ActionResult:
    """ASSIMILATE: negative CI effect, pushes LIBERAL tendency."""
    base_credibility = _derive_credibility_from_attrs(org_attrs, org_defines)
    ci_raw = -(defines.action_base_assimilate * base_credibility)
    ci_clamped = max(-defines.max_ci_delta_per_tick, ci_raw)

    ci_delta = ConsciousnessDelta(
        collective_identity_delta=ci_clamped,
        tendency_pressure=ConsciousnessTendency.LIBERAL,
        tendency_magnitude=abs(ci_clamped),
        source_org_id=str(org_attrs.get("id", "")),
    )

    return ActionResult(
        action=action,
        success=True,
        consciousness_delta=ci_delta,
        events_generated=[EventType.ORGANIZATIONAL_ACTION.value],
    )


def _get_effective_action_base(
    action_type: ActionType,
    org_attrs: dict[str, Any],
    defines: OODADefines,
) -> float:
    """Get effective action base, handling PROVIDE_SERVICE tendency split."""
    if action_type == ActionType.PROVIDE_SERVICE:
        tendency_str = org_attrs.get("consciousness_tendency", "liberal")
        tendency = ConsciousnessTendency(tendency_str)
        if tendency == ConsciousnessTendency.REVOLUTIONARY:
            return defines.action_base_provide_service
        if tendency == ConsciousnessTendency.LIBERAL:
            return defines.action_base_provide_service * 0.3
        return 0.0

    return defines.get_action_base(action_type.value)


def _derive_credibility_from_attrs(
    org_attrs: dict[str, Any],
    org_defines: OrganizationDefines,
) -> float:
    """Derive credibility from org attributes dict (without full Organization model).

    Args:
        org_attrs: Organization node attributes.
        org_defines: OrganizationDefines with credibility defaults.

    Returns:
        Credibility value in [0, 1].
    """
    from babylon.models.enums import OrgType

    org_type = org_attrs.get("org_type", "")

    if org_type == OrgType.CIVIL_SOCIETY.value:
        return float(org_attrs.get("legitimacy", org_defines.credibility_default_faction))

    if org_type == OrgType.POLITICAL_FACTION.value:
        return org_defines.credibility_default_faction

    if org_type == OrgType.STATE_APPARATUS.value:
        from babylon.models.enums import LegalStanding

        legal_standing = org_attrs.get("legal_standing", "")
        if legal_standing == LegalStanding.SOVEREIGN.value:
            return org_defines.credibility_sovereign
        if legal_standing == LegalStanding.CHARTERED.value:
            return org_defines.credibility_chartered
        return org_defines.credibility_default_state

    if org_type == OrgType.BUSINESS.value:
        emp = int(org_attrs.get("employment_count", 0))
        workforce = int(org_attrs.get("community_workforce", 1))
        if workforce <= 0:
            return 0.0
        return min(emp / workforce, 1.0)

    return 0.0


__all__ = [
    "compute_consciousness_delta",
    "resolve_action",
]
