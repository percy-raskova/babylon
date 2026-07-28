"""BUILD_INFRASTRUCTURE verb resolver (verb-dispatch engine).

Spec-108 FR-108-5 (Constitution II.13/Amendment O): ``ActionType.BUILD_INFRASTRUCTURE``
carries BOTH construction (new edge) and repair (existing degraded edge).
Amendment O forecloses a new verb — this closes the sharpest concrete gap the
spec surfaces: ``BUILD_INFRASTRUCTURE`` had NO resolver at all (unlike its
sibling ``ATTACK_INFRASTRUCTURE``, wired via ``engine/actions/attack.py``),
so a player-submitted BUILD action always failed loud with "no resolver
registered" even though the material effect it should trigger
(``ooda/layer3.py::_propagate_infrastructure``'s BUILD branch) already
existed and was simply unreachable.

**Registration status**: this resolver is implemented and unit-tested
directly (``tests/unit/engine/actions/test_build.py``) but is **NOT yet
added to** ``VERB_RESOLVERS`` (``engine/actions/__init__.py``). Doing so
would make BUILD_INFRASTRUCTURE the 10th canonical player verb, which
breaks ``tests/contract/verbs/test_registry.py``'s hard-pinned 9-verb count
and requires a companion "build" entry in
``src/babylon/projection/verbs/preview.py``'s ``VERB_TO_ACTION_TYPE`` (the
web bridge's own verb map, re-exported through ``web/game/engine_bridge.py``)
to keep ``TestBridgeParity`` green — ``src/babylon/projection/**`` is this
delegated unit's forbidden-file fence (another lane's territory). Per this
worktree's escalation discipline, the fence is not improvised around: the
registration is the next cross-lane step, not silently done here.

.. note::

    Director ruling 4 (ADR165, spec-108's "Director ruling required item
    4") resolves the community-scoped vs. corridor-scoped `condition`
    question as **uniform territory splash** — layer 3's *existing* BUILD
    branch keeps writing the community-scoped ``infrastructure`` float on
    the target Territory node (unchanged targeting shape, no ``Action``
    schema change), and ALSO uniformly repairs every corridor-mesh edge
    touching that territory (T6, ``ooda/layer3.py``'s new corridor-splash
    branch) — never edge-targeted in slice 1.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.models.enums import EventType
from babylon.ooda.types import ActionResult

if TYPE_CHECKING:
    from babylon.kernel.services import ServicesProtocol
    from babylon.ooda.types import Action
    from babylon.topology.graph import BabylonGraph


def resolve_build(
    action: Action,
    org_attrs: dict[str, Any],  # noqa: ARG001 — no acting-org state read (contrast resolve_attack's heat)
    graph: BabylonGraph,  # noqa: ARG001 — layer-3 mutates the target, not this resolver
    services: ServicesProtocol,  # noqa: ARG001 — no coefficient read at THIS resolver's level
) -> ActionResult:
    """Resolve a player BUILD_INFRASTRUCTURE action: carry it forward for layer 3.

    Mirrors ``resolve_attack``'s shape (``engine/actions/attack.py``): the
    resolver's own direct effect is minimal bookkeeping, and the actual
    material infrastructure increment on the TARGET node is applied by the
    EXISTING ``ooda.layer3._propagate_infrastructure`` BUILD branch (already
    present, previously unreachable because no player-verb path fed it —
    this resolver is that path). Unlike ``resolve_attack``, BUILD raises no
    self-heat on the acting org: construction/repair is not a covert or
    violent act that draws state attention onto its own actor.

    Args:
        action: The BUILD_INFRASTRUCTURE action
            (``action_type == ActionType.BUILD_INFRASTRUCTURE``).
        org_attrs: Acting organization's node attributes (unused).
        graph: World graph (unmutated by this resolver; layer 3 mutates the
            target after dispatch).
        services: ServicesProtocol (unused at this resolver's level; the
            repair-magnitude coefficients layer 3 reads live in
            ``TransportDefines``/``OODADefines``, not here).

    Returns:
        :class:`~babylon.ooda.types.ActionResult` carrying the BUILD action
        so layer 3 applies the infrastructure increment to the target, plus
        the first production emission of ``EventType.INFRASTRUCTURE_CHANGE``
        (D5 — reused, not reinvented, for BUILD/REPAIR/ATTACK narrative).
    """
    effects: dict[str, Any] = {"target_id": action.target_id}

    return ActionResult(
        action=action,
        success=True,
        direct_effects=effects,
        events_generated=[EventType.INFRASTRUCTURE_CHANGE.value],
    )


__all__ = ["resolve_build"]
