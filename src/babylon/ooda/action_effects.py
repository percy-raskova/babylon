"""Action resolution and consciousness effects (Feature 032).

Extends the Feature 031 five-factor consciousness formula with
action-type-specific multipliers, membership overlap credibility,
AGITATE-EDUCATE coupling, and per-tick delta clamping.

See Also:
    ``specs/032-ooda-loop-system/contracts/consciousness-effect-contract.md``
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.config.defines import (
    DoctrineDefines,
    OODADefines,
    OrganizationDefines,
    ReactionaryDefines,
)
from babylon.domain.organizations.consciousness import tendency_modifier
from babylon.domain.organizations.types import ConsciousnessDelta
from babylon.models.enums import ActionType, ConsciousnessTendency, EdgeType, EventType, NodeType
from babylon.models.enums.doctrine import DoctrineTag
from babylon.ooda._helpers import _compute_membership_overlap
from babylon.ooda.types import Action, ActionResult

if TYPE_CHECKING:
    from babylon.topology.graph import BabylonGraph

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
    doctrine: DoctrineDefines | None = None,
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

    # Step 7.5 (DoctrineSystem Unit 6b, ADR073): the theory bonus — corpus:
    # "High CLASS_ANALYSIS: correct prioritization, theory bonus". The org's
    # accumulated class-analysis doctrine scales its consciousness-raising;
    # tag capped at the corpus range ceiling (10).
    if doctrine is not None:
        doctrine_tags = org_attrs.get("doctrine_tags") or {}
        class_analysis = float(
            doctrine_tags.get(DoctrineTag.CLASS_ANALYSIS, doctrine_tags.get("class_analysis", 0.0))
        )
        if class_analysis > 0:
            scaled_delta *= 1.0 + doctrine.theory_bonus_per_class_analysis * min(
                class_analysis, 10.0
            )

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
    doctrine: DoctrineDefines | None = None,
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
        doctrine,
    )

    events: list[str] = [EventType.ORGANIZATIONAL_ACTION.value]

    return ActionResult(
        action=action,
        success=True,
        consciousness_delta=ci_delta,
        events_generated=events,
    )


def _bump_repression_edge(
    graph: BabylonGraph, source_id: str, target_id: str, increment: float
) -> None:
    """Create-or-strengthen a REPRESSION edge (source -> target), task #42-B.

    Mirrors the ``repression_faced`` scalar bump this always accompanies
    (same call site, same ``increment``) and the create-or-strengthen-or-skip
    idiom :func:`~babylon.engine.actions._mass_work.apply_mass_work_solidarity`
    established for the identical constraint: the graph stores one edge per
    node pair (``multigraph=False``), so blindly adding a REPRESSION edge over
    an existing DIFFERENT edge type would silently clobber it. Skipping is the
    honest failure mode; clobbering would be a silent data-corruption bug.

    ``EdgeType.REPRESSION`` had zero producers before this (3 read-only
    consumers: ``negotiate.py``, ``bifurcation/axis.py``,
    ``bifurcation/analysis.py`` — all read the ``weight`` attribute this
    writes).
    """
    existing = graph.get_edge(source_id, target_id, EdgeType.REPRESSION.value)
    if existing is not None:
        graph.update_edge(
            source_id,
            target_id,
            EdgeType.REPRESSION.value,
            weight=min(1.0, existing.weight + increment),
        )
    elif not graph.has_edge(source_id, target_id):
        graph.add_edge(
            source_id,
            target_id,
            edge_type=EdgeType.REPRESSION.value,
            weight=min(1.0, increment),
        )
    # else: (source_id, target_id) already holds a different edge type --
    # skip rather than clobber it (see docstring).


def _propagate_repression_to_class_base(
    graph: BabylonGraph,
    org_target_id: str,
    increment: float,
) -> list[str]:
    """Propagate a REPRESS/SURVEIL increment onto an organization's class base.

    Adversary-train W5: closes the severed link W1/W2 flagged and left open.
    Live REPRESS targets are ALWAYS non-state ``organization`` nodes
    (:func:`~babylon.ooda.npc_stub._gather_repress_target_candidates` --
    ``SocialClass`` is deliberately excluded there because it has no ``heat``
    field and is frozen ``extra="forbid"``). But ``Organization`` has no
    ``repression_faced`` field either -- a direct bump on the org node is a
    write that cannot survive ``WorldState.from_graph()``'s round-trip (an
    undeclared attribute, silently dropped, Pydantic's default
    ``extra="ignore"``), so it never reached ``SurvivalSystem``'s P(S|R)
    denominator or ``ConsciousnessSystem``'s continuous repression term --
    a fabricated effect, not a material one (Aleksandrov Test).

    The honest replacement: state violence against an organization IS
    violence against its class base (COINTELPRO raids on the Party were
    repression of its membership's class -- ``ai/epochs/epoch3/
    repression-logic.yaml``'s COINTELPRO module names "SOLIDARITY edges in
    topology graph" as its own ``primary_target``). The org's class base is
    read the SAME way :func:`~babylon.engine.actions._mass_work.
    apply_mass_work_solidarity` WRITES it: an org -> social_class
    ``SOLIDARITY`` edge -- the only real production producer of that edge
    shape (``MEMBERSHIP`` org->class edges are declared vocabulary with zero
    production writers; see ``models.enums.topology.NodeType``'s docstring
    and the vocabulary sentinel's ``UNSTAMPED_QUERY_ALLOWLIST``).

    The increment is SPLIT evenly across every connected class (id-sorted,
    deterministic iteration -- Constitution III.7) rather than replicated in
    full to each: a REPRESS/SURVEIL action's intensity is finite, so an org
    organizing several classes spreads the state's attention across its
    whole base rather than triggering N independent full-strength
    repressions. No new ``OODADefines`` coefficient is introduced -- the
    split is a pure structural division of the SAME ``repress_heat_delta``/
    ``surveil_heat_delta`` increment the direct social_class path already
    uses, not a new tunable.

    Args:
        graph: World graph (mutated: every SOLIDARITY-linked social_class
            node's ``repression_faced`` is bumped by its even share of
            *increment*, clamped at 1.0 -- same idiom as the direct
            social_class path in :func:`_resolve_repressive`).
        org_target_id: The ``organization`` node id the state action targeted.
        increment: The SAME ``repress_heat_delta``/``surveil_heat_delta``
            this org target would have received directly, had ``Organization``
            declared the field.

    Returns:
        The id-sorted list of social_class node ids that received a share of
        *increment*. Empty if the org has no SOLIDARITY-linked class base
        (e.g. a Business NPC that never performed mass work) -- an honest
        no-op, not a masked failure.
    """
    connected_class_ids: list[str] = []
    max_edges = 1000
    matched_edges = graph.query_edges(
        edge_type=EdgeType.SOLIDARITY.value,
        predicate=lambda e: e.source_id == org_target_id,
    )
    for idx, edge in enumerate(matched_edges):
        if idx >= max_edges:
            break
        target_node = graph.nodes.get(edge.target_id)
        if target_node is not None and target_node.get("_node_type") == NodeType.SOCIAL_CLASS.value:
            connected_class_ids.append(edge.target_id)

    if not connected_class_ids:
        return []

    connected_class_ids.sort()
    split_increment = increment / len(connected_class_ids)
    for class_id in connected_class_ids:
        node = graph.get_node(class_id)
        if node is None:
            continue
        current = float(node.attributes.get("repression_faced", 0.0))
        graph.update_node(class_id, repression_faced=min(1.0, current + split_increment))

    return connected_class_ids


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

    POGROM/VIGILANTISM also stamp a REPRESSION edge (acting org -> target,
    task #42-B) alongside the ``repression_faced`` scalar bump, weighted by
    the SAME increment (see :func:`_bump_repression_edge`).

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
            _bump_repression_edge(graph, action.org_id, target_id, increment)
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
    graph: BabylonGraph,
    defines: OODADefines,
    org_defines: OrganizationDefines,
) -> ActionResult:
    """REPRESS/SURVEIL: backfire raises target CI, repression IS material.

    Mirrors :func:`_resolve_fascist_verb`'s task #42-B pattern: raise the
    target's ``repression_faced`` scalar (same clamp-at-1.0 idiom) and stamp
    a REPRESSION edge (acting org -> target) via :func:`_bump_repression_edge`,
    weighted by the SAME increment. Adversary-train W1 (2026-07-22): before
    this, REPRESS/SURVEIL computed only a (never-consumed) CI backfire and
    tagged ``events_generated`` — the target's ``repression_faced`` was
    never touched, so ``SurvivalSystem``'s P(S|R) denominator
    (``survival.py``) and ``ConsciousnessSystem``'s continuous repression
    term (``ideology.py``) never saw a state-produced value (Aleksandrov
    Test: a formal construct — ``repression_faced`` — with no material
    producer is not grounded).

    The increment reuses ``OODADefines.repress_heat_delta`` /
    ``surveil_heat_delta`` (0.15 / 0.05) — the SAME coefficients
    :func:`~babylon.ooda.layer3._propagate_heat` already uses for this
    identical action pair's community-heat bump ("repression IS
    high-profile attention"), rather than inventing a new tunable: one
    action, one intensity, two downstream readouts (heat, repression_faced).

    Adversary-train W5 (2026-07-22): the live Wayne campaign's REPRESS/SURVEIL
    target is ALWAYS a non-state ``organization`` node (task #73's
    ``npc_stub._gather_repress_target_candidates`` deliberately excludes
    SocialClass), but ``Organization`` declares no ``repression_faced``
    field — W1's original unconditional bump on an org target was a write
    that could never survive ``WorldState.from_graph()``'s round-trip (a
    fabricated effect, not a material one). This resolver now branches on
    the target's ``_node_type``: a ``social_class`` target keeps the DIRECT
    bump unchanged (below); an ``organization`` target instead PROPAGATES
    the increment to its SOLIDARITY-linked class base
    (:func:`_propagate_repression_to_class_base` — see its docstring for
    the full Aleksandrov grounding and the split rule). The org node itself
    never receives a phantom ``repression_faced`` write again. The
    REPRESSION edge (acting org -> target) still stamps unconditionally,
    regardless of target type — that edge shape was always legitimate
    provenance (the 3 read-only consumers, the chronicle bulletin) and is
    untouched by this change.

    No-ops (no ``repression_increment``/edge stamp, only the CI backfire)
    when *target_id* names no live node — mirrors the fascist-verb guard.
    """
    action_type = action.action_type
    target_id = action.target_id

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

    effects: dict[str, Any] = {"backfire_delta": backfire_delta}
    node = graph.get_node(target_id)
    if node is not None:
        increment = (
            defines.repress_heat_delta
            if action_type == ActionType.REPRESS
            else defines.surveil_heat_delta
        )
        if node.node_type == NodeType.SOCIAL_CLASS.value:
            current_rep = float(node.attributes.get("repression_faced", 0.0))
            graph.update_node(target_id, repression_faced=min(1.0, current_rep + increment))
            effects["repression_increment"] = increment
        elif node.node_type == NodeType.ORGANIZATION.value:
            propagated_ids = _propagate_repression_to_class_base(graph, target_id, increment)
            if propagated_ids:
                effects["repression_increment"] = increment
                effects["repression_propagated_to"] = propagated_ids
        _bump_repression_edge(graph, action.org_id, target_id, increment)

    return ActionResult(
        action=action,
        success=True,
        consciousness_delta=ci_delta,
        direct_effects=effects,
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
