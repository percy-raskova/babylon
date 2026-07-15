"""Epistemic Horizon system (fog of war) — Phase 1 SHADOW ONLY.

Program: ``project/research/epistemic-horizon-program-proposal.md``. Source
formulas + the three worked ``M_r`` examples: ``ai/epochs/epoch3/fog-of-war.yaml``
lines 86-330 ("Slice 2.10: The Epistemic Horizon").

"Intelligence is not about PRESENCE but about RELATIONSHIP. You know what
the masses tell you." — the corpus's thesis. This system computes, per
TERRITORY node, how well the player org can perceive that territory's true
state, from inputs already live elsewhere in the engine:

- ``p_acquiescence`` (P(S|A)) — already computed by :class:`~babylon.engine.systems.survival.SurvivalSystem`.
- ``class_consciousness`` — an HONEST, DOCUMENTED PROXY for the corpus's
  "ideological alignment" (I_a). The corpus additionally lists org reputation
  and historical actions as I_a inputs (fog-of-war.yaml:186-193); Phase 1 does
  not model those, so I_a here is class_consciousness alone. This is a known
  simplification, flagged in the program proposal's Phase-1 caveats — NOT the
  full corpus I_a.
- a per-role class factor (C_f), a new defines category
  (:class:`~babylon.config.defines.epistemic_horizon.EpistemicHorizonDefines`).

PHASE 1 SCOPE (binding, see the program proposal): shadow attrs only. NO
masking, NO reveal gating, NO Investigate wiring, NO decay. Nothing else in
the engine reads ``mass_receptivity`` / ``intel_confidence`` / ``vision_state``
yet — they are write-only, byte-safe-by-construction outputs (the P19
shadow-attr precedent: new attrs invisible to dense goldens because nothing
consumes them).

Runs LAST in ``_DEFAULT_SYSTEMS`` (after all 26 prior systems, including
OODA/Survival/Consciousness) because it OBSERVES the fully-mutated tick — it
must read this tick's ``p_acquiescence`` and ``class_consciousness``, not
last tick's stale values. It creates no value and consumes no RNG
(Constitution III.7: pure deterministic computation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from babylon.models.enums import EdgeType, SocialRole

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol

from babylon.kernel.system_base import SystemBase
from babylon.kernel.system_protocol import ContextType


def _coerce_role(raw: object) -> SocialRole | None:
    """Coerce a graph-node ``role`` attr to ``SocialRole`` (mirrors
    ``babylon.engine.systems.reactionary._coerce_role``'s convention: the
    attr may be a live ``SocialRole`` enum member (fresh ``to_graph()``
    output) or a plain string (post-persistence round trip)."""
    if isinstance(raw, SocialRole):
        return raw
    if isinstance(raw, str):
        try:
            return SocialRole(raw)
        except ValueError:
            return None
    return None


def _class_consciousness_of(attrs: dict[str, Any]) -> float:
    """Read ``class_consciousness`` from the ``ideology`` sub-dict (mirrors
    ``babylon.engine.systems.ideology._get_ideology_profile_from_node``'s
    read convention). Missing/malformed ``ideology`` -> the
    ``IdeologicalProfile`` model's own default (0.0), not a fabricated value."""
    ideology = attrs.get("ideology")
    if isinstance(ideology, dict):
        return float(ideology.get("class_consciousness", 0.0))
    return 0.0


def compute_epistemic_horizon(
    graph: GraphProtocol,
    defines: Any,
) -> None:
    """Compute and write shadow M_r/I_c/vision_state onto territory nodes.

    Extracted from :meth:`EpistemicHorizonSystem.step` (pure
    graph-in/graph-out function, no ``services``/``context`` dependency
    beyond the one defines category) so the web bridge can recompute this
    tick's shadow attrs on its own post-``WorldState``-round-trip graph —
    see ``web/game/engine_bridge.py::_carry_epistemic_horizon``'s docstring
    for why a recompute (not a ``persistent_context`` stash, unlike
    ``TickDynamicsSystem``'s carry) is the correct fix for this system's
    altitude gap: every input this function reads (``p_acquiescence``,
    ``ideology.class_consciousness``, ``role``, ``population`` — all real
    ``SocialClass`` model fields — plus the TENANCY/PRESENCE edges) survives
    the round trip untouched, so calling this twice against the same
    tenant-class state reproduces byte-identical output (Constitution III.7).

    Per TERRITORY node:

    1. Resolve tenant SocialClass nodes via incoming TENANCY edges (mirrors
       ``TerritorySystem._suppress_organization``'s TENANCY resolution — the
       engine-side equivalent of the bridge's tenancy resolution).
    2. ``M_r`` = population-weighted mean over tenant classes of
       ``(1 - p_acquiescence) * class_consciousness * C_f``.
    3. ``C_p`` (cadre presence) = 1.0 if any PLAYER-CONTROLLED org (a node
       whose attrs carry ``is_player=True`` — today, only the
       ``PoliticalFaction`` subtype exposes that field; see the program
       report for the honest-null consequence in ``wayne_county``) has a
       PRESENCE edge to the territory, else 0.0.
    4. ``I_c`` = B_o + (C_p * M_r), clamped to [0, 1].
    5. ``vision_state`` = "desert" / "mud" / "water" per the defines
       thresholds.

    Constitution III.11 honest-null: a territory with NO tenant classes (or
    only zero-population tenants) gets none of the three attrs — ``M_r``
    cannot be honestly computed, and since ``I_c``/``vision_state`` are
    *derived from* ``M_r``, fabricating them from an implicit M_r=0 would
    smuggle the same dishonesty in through the back door. All three attrs
    are written together, or not at all.

    Args:
        graph: The graph to mutate in place (a live engine-tick graph, or a
            post-round-trip ``new_graph`` the bridge is about to persist).
        defines: This session's ``EpistemicHorizonDefines``
            (``services.defines.epistemic_horizon`` / ``game_defines.epistemic_horizon``).
    """
    role_factor: dict[SocialRole, float] = {
        SocialRole.PERIPHERY_PROLETARIAT: defines.class_factor_periphery_proletariat,
        SocialRole.LUMPENPROLETARIAT: defines.class_factor_lumpenproletariat,
        SocialRole.PETTY_BOURGEOISIE: defines.class_factor_petty_bourgeoisie,
        SocialRole.LABOR_ARISTOCRACY: defines.class_factor_labor_aristocracy,
    }

    for territory in graph.query_nodes(node_type="territory"):
        territory_id = territory.id

        weighted_sum = 0.0
        total_population = 0.0

        for edge in graph.query_edges(edge_type=EdgeType.TENANCY):
            if edge.target_id != territory_id:
                continue
            tenant = graph.get_node(edge.source_id)
            if tenant is None or tenant.node_type != "social_class":
                continue

            attrs = tenant.attributes
            population = float(attrs.get("population", 0) or 0)
            if population <= 0.0:
                continue

            p_acquiescence = float(attrs.get("p_acquiescence", 0.0))
            ideological_alignment = _class_consciousness_of(attrs)
            role = _coerce_role(attrs.get("role"))
            class_factor = (
                defines.class_factor_default
                if role is None
                else role_factor.get(role, defines.class_factor_default)
            )

            class_m_r = (1.0 - p_acquiescence) * ideological_alignment * class_factor
            weighted_sum += class_m_r * population
            total_population += population

        if total_population <= 0.0:
            # Honest absence (Constitution III.11): no tenant classes with
            # positive population -> no M_r, no I_c, no vision_state.
            continue

        mass_receptivity = weighted_sum / total_population

        cadre_presence = 0.0
        for edge in graph.query_edges(edge_type=EdgeType.PRESENCE):
            if edge.target_id != territory_id:
                continue
            org = graph.get_node(edge.source_id)
            if org is not None and org.attributes.get("is_player", False):
                cadre_presence = 1.0
                break

        intel_confidence = max(
            0.0,
            min(1.0, defines.base_observation + cadre_presence * mass_receptivity),
        )

        if mass_receptivity < defines.desert_threshold:
            vision_state = "desert"
        elif mass_receptivity >= defines.water_threshold:
            vision_state = "water"
        else:
            vision_state = "mud"

        graph.update_node(
            territory_id,
            mass_receptivity=mass_receptivity,
            intel_confidence=intel_confidence,
            vision_state=vision_state,
        )


class EpistemicHorizonSystem(SystemBase):
    """Phase 1 SHADOW: Mass Receptivity (M_r) / Intel Confidence (I_c) / Vision State.

    See :func:`compute_epistemic_horizon` for the formula/algorithm — this
    class is now a thin ``SystemBase`` adapter over that pure function.
    """

    name: ClassVar[str] = "Epistemic Horizon"
    # Spec 053 INV-001: does not mutate hex c+v+s; opted in by default-deny.
    creates_value: ClassVar[bool] = False

    def step(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        _context: ContextType,
    ) -> None:
        """Compute and write shadow M_r/I_c/vision_state onto territory nodes."""
        compute_epistemic_horizon(graph, services.defines.epistemic_horizon)
