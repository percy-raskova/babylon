"""The verb-plate provider — nine verbs, eligibility, affordability (WO-38).

Port of the legacy bridge's ``get_verb_eligibility`` into the projection
layer. Evaluates, on one bounded graph pass, the same target-existence
predicate each per-verb target list applies — so a verb is marked
ineligible exactly when its target list would come back empty — and pairs
every ineligible verb with the player-facing ``(reason, remedy)`` copy.
Affordability rides along per verb via
:func:`babylon.models.vanguard_resources.check_can_afford` (the same
function that gates submission, so the plate can never disagree with a
submit rejection); the UI disables on ``eligible`` only, never on
``can_afford``.

MOVE/NEGOTIATE/INVESTIGATE honesty note: their eligibility comes from real
graph predicates (a territory node exists / another org exists / own
territories non-empty) — eligibility must never launder a fixture into
``eligible: true``.

Unit "verb-targeting" (shell-interconnect): the same bounded pass that
computes each eligibility boolean also retains the underlying entity ids
that made it true, surfaced per verb as :attr:`~babylon.projection.verbs.
view_models.VerbRow.candidate_target_ids` — a picker can enumerate real,
honest targets without ever touching the graph itself. ``reproduce``'s own
candidate set is deliberately empty: it always targets the acting org
itself (its own eligibility row's comment below), never an explicit id.
"""

from __future__ import annotations

from babylon.config.defines import GameDefines
from babylon.models.enums.topology import NodeType
from babylon.models.vanguard_resources import VanguardResources, check_can_afford
from babylon.projection.territory_anchor import tenancy_members_by_territory
from babylon.projection.verbs.copy import VERB_INELIGIBILITY_COPY
from babylon.projection.verbs.preview import VERB_TO_ACTION_TYPE, preview_verb
from babylon.projection.verbs.view_models import VerbPlateView, VerbRow
from babylon.topology import BabylonGraph


def build_verb_plate(
    graph: BabylonGraph,
    org_id: str,
    *,
    tick: int,
    defines: GameDefines | None = None,
) -> VerbPlateView | None:
    """Build the nine-verb plate for one acting org.

    :param graph: World graph (read-only).
    :param org_id: The acting organization id.
    :param tick: The tick the plate is computed against (provenance stamp).
    :param defines: Coefficient source for the embedded previews.
    :returns: The frozen plate view, or ``None`` when the org is absent
        from the graph (honest absence — the caller renders an absence
        block, never a fabricated plate).
    """
    if org_id not in graph.nodes:
        return None

    org_data = graph.nodes[org_id]
    own_tids = {str(t) for t in org_data.get("territory_ids", [])}

    tenancy_members = tenancy_members_by_territory(graph)
    social_class_ids = sorted(
        {class_id for tid in own_tids for class_id in tenancy_members.get(tid, [])}
    )
    has_social_class = bool(social_class_ids)

    # One bounded pass over the graph gathers every remaining predicate
    # input AND the underlying entity ids each one is true because of (unit
    # "verb-targeting" — the module docstring's own candidate-set note).
    territory_ids: list[str] = []  # campaign; move
    org_in_reach_ids: list[str] = []  # aid (org arm); attack (org arm)
    mobilizable_org_ids: list[str] = []  # mobilize (business/civil_society)
    institution_in_reach_ids: list[str] = []  # attack (institution arm)
    other_org_ids: list[str] = []  # negotiate (anywhere in the graph)
    has_territory_node = False  # campaign; move
    for node_id, data in graph.nodes(data=True):
        node_type = data.get("_node_type")
        if node_type == NodeType.TERRITORY:
            has_territory_node = True
            territory_ids.append(str(node_id))
            continue
        node_tids = {str(t) for t in data.get("territory_ids", [])}
        if node_type == NodeType.ORGANIZATION and node_id != org_id:
            other_org_ids.append(str(node_id))
            if node_tids & own_tids:
                org_in_reach_ids.append(str(node_id))
                if str(data.get("org_type", "")) in ("business", "civil_society"):
                    mobilizable_org_ids.append(str(node_id))
        elif node_type == NodeType.INSTITUTION and node_tids & own_tids:
            institution_in_reach_ids.append(str(node_id))

    has_org_in_reach = bool(org_in_reach_ids)
    has_mobilizable_org = bool(mobilizable_org_ids)
    has_institution_in_reach = bool(institution_in_reach_ids)
    has_other_org = bool(other_org_ids)

    eligible_by_verb: dict[str, bool] = {
        "educate": has_social_class,
        "aid": has_social_class or has_org_in_reach,
        "attack": has_org_in_reach or has_institution_in_reach,
        "mobilize": has_mobilizable_org,
        "campaign": has_territory_node,
        "move": has_territory_node,
        "investigate": bool(own_tids),
        "reproduce": True,  # always targets the acting org itself
        "negotiate": has_other_org,
    }

    # Honest per-verb candidate id sets (unit "verb-targeting") — the SAME
    # entity domain each eligibility boolean above tests, sorted for
    # determinism, never inventing an id beyond what the one bounded pass
    # above actually found. "reproduce" is deliberately empty: it always
    # targets the acting org itself (its own eligibility row's comment
    # above), so it has no EXPLICIT-target candidates to enumerate.
    candidate_ids_by_verb: dict[str, tuple[str, ...]] = {
        "educate": tuple(social_class_ids),
        "aid": tuple(sorted(set(social_class_ids) | set(org_in_reach_ids))),
        "attack": tuple(sorted(set(org_in_reach_ids) | set(institution_in_reach_ids))),
        "mobilize": tuple(sorted(mobilizable_org_ids)),
        "campaign": tuple(sorted(territory_ids)),
        "move": tuple(sorted(territory_ids)),
        "investigate": tuple(sorted(own_tids)),
        "reproduce": (),
        "negotiate": tuple(sorted(other_org_ids)),
    }

    resources = VanguardResources.from_organization(
        cadre_level=float(org_data.get("cadre_level", 0.0)),
        cohesion=float(org_data.get("cohesion", 0.0)),
        budget=float(org_data.get("budget", 0.0)),
        heat=float(org_data.get("heat", 0.0)),
        territory_count=len(own_tids),
    )

    rows: list[VerbRow] = []
    for verb in VERB_TO_ACTION_TYPE:
        eligible = eligible_by_verb[verb]
        reason, remedy = (None, None) if eligible else VERB_INELIGIBILITY_COPY[verb]
        can_afford, afford_reason = check_can_afford(resources, verb)
        rows.append(
            VerbRow(
                verb=verb,
                eligible=eligible,
                reason=reason,
                remedy=remedy,
                can_afford=can_afford,
                afford_note=None if can_afford else afford_reason,
                preview=preview_verb(graph, org_id, verb, defines=defines),
                candidate_target_ids=candidate_ids_by_verb[verb],
            )
        )

    return VerbPlateView(org_id=org_id, tick=tick, verbs=tuple(rows))
