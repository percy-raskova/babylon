"""CAMPAIGN verb resolver (verb-dispatch engine).

Broadcast propaganda (``ActionType.PROPAGANDIZE``). Thin delegate to the
Feature-032 effects machinery — same five-factor consciousness pathway as
EDUCATE, but scaled by the propagandize action base (symmetric inverse of
EDUCATE; less precise than education).

**Mass-work SOLIDARITY (Unit 6 write side, ADR087):** PROPAGANDIZE is one of
the three mass-work verbs that create-or-strengthen an org -> class
SOLIDARITY edge when targeting a ``social_class`` node, amplified by the
org's MASS_LINK doctrine tag — the one direct graph write this resolver makes.

**Campaign(Election) sub-verbs (P25 U11, ADR137):** an org that has acquired a
reformist-fork stance may pass ``params["mode"]`` to run the electoral variants,
each gated on the stance's declared
:class:`~babylon.models.entities.doctrine.DoctrineCapability`:

* ``election:run`` — the Debs road. The campaign IS mass work: the classic
  five-factor consciousness path still fires, and the SOLIDARITY write is
  scaled by ``politics.debs_solidarity_efficiency`` (η_cse — real recruitment,
  below the direct-mass-work base).
* ``election:boycott`` — principled abstention. Converts a *live* disillusion
  window (the ``electoral_disillusion`` register the ElectoralSystem publishes
  at T-7) into agitation at ``politics.boycott_conversion``, and pays
  ``politics.sect_isolation_rate`` in MASS_LINK decay every time it is used.
  Where no window is open the conversion is zero: boycotting a hope the base
  still holds is pure sect isolation, priced.

A ``mode`` the acting org has not acquired is refused LOUDLY (III.11); it never
silently falls back to the classic path.

See Also:
    :func:`babylon.engine.actions.educate.resolve_educate`: the sibling
    consciousness-class resolver.
    :func:`babylon.engine.actions._mass_work.apply_mass_work_solidarity`.
    :mod:`babylon.engine.actions._capability`: the doctrine-capability gate.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.engine.actions._capability import grants_verb_mode
from babylon.engine.actions._mass_work import apply_mass_work_solidarity
from babylon.models.enums import EventType, NodeType
from babylon.models.enums.doctrine import DoctrineTag
from babylon.ooda.action_effects import resolve_action
from babylon.ooda.types import ActionResult

if TYPE_CHECKING:
    from babylon.config.defines.politics import PoliticsDefines
    from babylon.kernel.services import ServicesProtocol
    from babylon.ooda.types import Action
    from babylon.topology.graph import BabylonGraph

#: Graph attribute holding the ElectoralSystem's live T-7 disillusion windows
#: (read by raw string: the engine layer must not import a sibling system).
_DISILLUSION_ATTR = "electoral_disillusion"
#: Campaign(Election) sub-mode: stand candidates as class-struggle agitation.
_MODE_RUN = "election:run"
#: Campaign(Election) sub-mode: refuse the ballot and organize the abstainers.
_MODE_BOYCOTT = "election:boycott"
#: Every sub-mode this resolver knows how to run.
_MODES: frozenset[str] = frozenset({_MODE_RUN, _MODE_BOYCOTT})


def resolve_campaign(
    action: Action,
    org_attrs: dict[str, Any],
    graph: BabylonGraph,
    services: ServicesProtocol,
) -> ActionResult:
    """Resolve a player CAMPAIGN action into a real consciousness effect.

    Args:
        action: The CAMPAIGN action (``action_type == ActionType.PROPAGANDIZE``).
            An optional ``mode`` param selects a Campaign(Election) sub-verb.
        org_attrs: Acting organization's node attributes.
        graph: World graph (written by the mass-work SOLIDARITY producer).
        services: ServicesProtocol providing the OODA/organization/reactionary/
            doctrine/politics defines.

    Returns:
        :class:`~babylon.ooda.types.ActionResult` carrying the five-factor
        ``consciousness_delta`` (non-None on the classic and RUN paths), or a
        loud refusal when the org has not acquired the requested sub-mode.
    """
    mode = str(action.params.get("mode", "")).strip()
    if not mode:
        return _resolve_classic(action, org_attrs, graph, services)

    if mode not in _MODES:
        return ActionResult(
            action=action,
            success=False,
            failure_reason=f"CAMPAIGN: unknown election mode {mode!r}",
        )

    capability = f"campaign:{mode}"
    if not grants_verb_mode(org_attrs, capability):
        return ActionResult(
            action=action,
            success=False,
            failure_reason=(f"CAMPAIGN({mode}): no acquired doctrine stance grants {capability!r}"),
        )

    if mode == _MODE_RUN:
        return _resolve_election_run(action, org_attrs, graph, services)
    return _resolve_election_boycott(action, org_attrs, graph, services.defines.politics)


def _resolve_classic(
    action: Action,
    org_attrs: dict[str, Any],
    graph: BabylonGraph,
    services: ServicesProtocol,
    efficiency: float = 1.0,
) -> ActionResult:
    """Mass-work SOLIDARITY write + the five-factor consciousness pathway."""
    apply_mass_work_solidarity(
        graph,
        action.org_id,
        org_attrs,
        action.target_id,
        services.defines.doctrine,
        efficiency=efficiency,
    )
    return resolve_action(
        action,
        org_attrs,
        graph,
        services.defines.ooda,
        services.defines.organization,
        services.defines.reactionary,
        doctrine=services.defines.doctrine,
    )


def _resolve_election_run(
    action: Action,
    org_attrs: dict[str, Any],
    graph: BabylonGraph,
    services: ServicesProtocol,
) -> ActionResult:
    """Campaign(Election, mode=RUN): the ballot line as a recruitment engine."""
    efficiency = float(services.defines.politics.debs_solidarity_efficiency)
    result = _resolve_classic(action, org_attrs, graph, services, efficiency=efficiency)
    effects = {
        **result.direct_effects,
        "election_mode": _MODE_RUN,
        "solidarity_efficiency": efficiency,
    }
    return result.model_copy(update={"direct_effects": effects})


def _resolve_election_boycott(
    action: Action,
    org_attrs: dict[str, Any],
    graph: BabylonGraph,
    politics: PoliticsDefines,
) -> ActionResult:
    """Campaign(Election, mode=BOYCOTT): convert broken hope, pay in isolation."""
    target_node = graph.nodes.get(action.target_id)
    if target_node is None:
        return ActionResult(
            action=action,
            success=False,
            failure_reason="CAMPAIGN(election:boycott) target not found in graph",
        )

    isolation = _decay_mass_link(graph, action.org_id, org_attrs, politics.sect_isolation_rate)

    windows = graph.get_graph_attr(_DISILLUSION_ATTR, None) or {}
    window_live = action.target_id in windows
    conversion = float(politics.boycott_conversion) if window_live else 0.0

    effects: dict[str, Any] = {
        "election_mode": _MODE_BOYCOTT,
        "disillusion_window_live": window_live,
        "boycott_conversion": conversion,
        "mass_link_decay": isolation,
    }

    if conversion > 0.0 and target_node.get("_node_type") == NodeType.SOCIAL_CLASS.value:
        ideology = dict(target_node.get("ideology") or {})
        if ideology:
            ideology["agitation"] = float(ideology.get("agitation", 0.0)) + conversion
            graph.update_node(action.target_id, ideology=ideology)
            effects["agitation_delta"] = conversion

    return ActionResult(
        action=action,
        success=True,
        direct_effects=effects,
        events_generated=[EventType.ORGANIZATIONAL_ACTION.value],
    )


def _decay_mass_link(
    graph: BabylonGraph,
    org_id: str,
    org_attrs: dict[str, Any],
    rate: float,
) -> float:
    """Erode the acting org's MASS_LINK tag; return the decay actually applied."""
    tags = dict(org_attrs.get("doctrine_tags") or {})
    current = float(tags.get(DoctrineTag.MASS_LINK, 0.0))
    if current <= 0.0:
        return 0.0
    applied = min(current, float(rate))
    tags[DoctrineTag.MASS_LINK] = current - applied
    graph.update_node(org_id, doctrine_tags=tags)
    return applied


__all__ = ["resolve_campaign"]
