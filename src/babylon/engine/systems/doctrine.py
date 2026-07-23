"""DoctrineSystem — the party's ideological development over the Doctrine Tree.

Owner-ratified 2026-07-15 (the six DT rulings). Each tick, per ORGANIZATION node,
this system runs the deterministic doctrine loop built from the pure mechanics in
:mod:`babylon.domain.doctrine.mechanics`:

1. **Decay** — every accumulated tag strength erodes by ``tag_decay_rate``
   (Ruling 3, 0.55%/tick): unexercised theory fades.
2. **Accrue theoretical labour** — ``study_allocation × cadre_level`` (Ruling 4).
   ``cadre_level`` is the MVP surplus proxy: theoretical labour is intellectual
   work, so a party's *cadre quality* (not its material budget) is the apt
   capacity measure. ``study_allocation`` is the midpoint of the ratified band.
3. **Bootstrap the root** — the free ``class_consciousness`` root is acquired
   once TL is non-negative, seeding starting tag strength.
4. **Greedy auto-acquire** — the cheapest affordable, unlocked, non-trap node is
   acquired (deterministic: min ``cost_tl``, id tie-break); its ``tag_deltas``
   add to the accumulator and its ``cost_tl`` is spent. This is the AI party's
   OODA-driven study; the player's ``study`` verb (Unit 7) targets a specific node.
5. **Trap firing** — any *reachable* trap (all parents held) whose
   ``trap_condition`` holds against the current tags is fallen into (acquired
   involuntarily, its deltas applied), and a ``DOCTRINE_TRAP_SPRUNG`` event fires.

Every ``congress_interval_ticks`` the **Party Congress** convenes first (Unit 5,
Ruling 5 / DT-5, :mod:`babylon.domain.doctrine.congress`): one purge attempt
against the first held trap, resolved by a weighted draw from the
seed-deterministic tick RNG (:func:`~babylon.kernel.system_base.resolve_rng`,
Constitution III.7 — same seed, same history), with tag deltas since the last
congress biasing the odds inside a clamped contingency band.

After the per-org doctrine loop, :func:`compute_doctrine` also decays that
org's outgoing mass-work SOLIDARITY edges (Unit 6 write side, ADR087):
``mass_work_solidarity_decay_rate`` per tick, floored at 0. This is graph-level
state a verb resolver wrote (:func:`babylon.engine.actions._mass_work.apply_mass_work_solidarity`),
not a `step_organization` mechanic — a mass link not renewed by work withers.

Determinism: the per-tick loop is RNG-free; the congress consumes the seeded
tick RNG only when a purge is actually attempted (an org holds a trap AND can
afford ``trap_escape_tl``). Byte-safe on the qa:regression goldens by
construction: those five scenarios carry no organization nodes, so this system
is a no-op — and draws nothing — there.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar, Final

from babylon.domain.doctrine import evaluate_trap_condition, load_doctrine_tree
from babylon.domain.doctrine.congress import held_sprung_traps, run_congress
from babylon.domain.doctrine.mechanics import (
    accrue_theoretical_labor,
    acquire,
    can_acquire,
    decay_tags,
)
from babylon.kernel.event_bus import Event
from babylon.kernel.tick_partition import TickPartition
from babylon.models.enums import EdgeMode, EdgeType, EventType, NodeType
from babylon.models.enums.doctrine import DoctrineTag, PracticeVariable

if TYPE_CHECKING:
    import random
    from collections.abc import Mapping

    from babylon.config.defines.doctrine import DoctrineDefines
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol
    from babylon.models.entities.doctrine import DoctrineNode, DoctrineTree

from babylon.kernel.system_base import SystemBase, resolve_rng
from babylon.kernel.system_protocol import ContextType

#: Graph register carrying each org's ``(self_organization, representation)``
#: political-form position (P25 U11 §3.4, ADR137). Owned by this file — see
#: ``sentinels/superstructure/registry.py``. Read by ContradictionSystem @18.0
#: (one tick stale by pipeline position: I-ORD compliant).
POLITICAL_FORM_POSITIONS_ATTR: Final[str] = "political_form_org_positions"

#: ``compute_doctrine``'s triple ``kind`` string -> the EventType it publishes
#: as (ADR073 Unit 6a). Every kind ``compute_doctrine`` can return MUST have an
#: entry here — a missing kind would silently drop an event (Constitution
#: III.11), so ``DoctrineSystem.step`` indexes this dict directly (no
#: ``.get()`` fallback) and a bad kind raises loudly instead.
_KIND_TO_EVENT_TYPE: dict[str, EventType] = {
    "sprung": EventType.DOCTRINE_TRAP_SPRUNG,
    "escaped": EventType.DOCTRINE_TRAP_ESCAPED,
    "purge_failed": EventType.DOCTRINE_PURGE_FAILED,
}


def _apply_deltas(tags: dict[DoctrineTag, float], deltas: object) -> dict[DoctrineTag, float]:
    """Add a node's ``tag_deltas`` (signed ints) onto the float accumulator."""
    result = dict(tags)
    if isinstance(deltas, dict):
        for tag, delta in deltas.items():
            key = tag if isinstance(tag, DoctrineTag) else DoctrineTag(tag)
            result[key] = result.get(key, 0.0) + float(delta)
    return result


def _cheapest_acquirable(tree: DoctrineTree, acquired: tuple[str, ...], tl: float) -> str | None:
    """The deterministically-chosen next node to auto-acquire, or ``None``.

    Cheapest affordable, unlocked, non-trap node; ties broken by node id so the
    choice is reproducible.
    """
    candidates = [node_id for node_id in tree.nodes if can_acquire(tree, acquired, node_id, tl)]
    if not candidates:
        return None
    return min(candidates, key=lambda nid: (tree.nodes[nid].cost_tl, nid))


def _decay_mass_work_solidarity_edges(graph: GraphProtocol, org_id: str, decay_rate: float) -> None:
    """Decay one org's outgoing SOLIDARITY edges (Unit 6 write side, ADR087).

    A mass link not renewed by work withers: every org-sourced SOLIDARITY
    edge's ``solidarity_strength`` shrinks multiplicatively each tick,
    floored at 0. Symmetric with the write side
    (:func:`babylon.engine.actions._mass_work.apply_mass_work_solidarity`) —
    both live at the engine layer (graph-level state a verb resolver wrote),
    not the domain-layer doctrine mechanics `step_organization` composes.
    Uses :meth:`~babylon.kernel.graph_protocol.GraphProtocol.query_edges`
    (not the concrete ``out_edges``) to stay protocol-typed.
    """
    for edge in graph.query_edges(edge_type=EdgeType.SOLIDARITY.value):
        if edge.source_id != org_id:
            continue
        strength = float(edge.attributes.get("solidarity_strength", 0.0))
        if strength <= 0.0:
            continue
        graph.update_edge(
            org_id,
            edge.target_id,
            EdgeType.SOLIDARITY.value,
            solidarity_strength=max(0.0, strength * (1.0 - decay_rate)),
        )


def _delivery_gap(graph: GraphProtocol, org_id: str) -> float:
    """A governing org's total delivery gap this period (P25 U11, ADR137, §3.1).

    Σ over the ``policy_delivery`` register's class rows whose ``incumbent_id`` is
    this org of ``max(0, promised − delivered)``. The register is written by
    PolicySystem @17.47 and read here one tick stale (I-ORD). The veto's material
    trace is this GAP, not a STRUCK flag — struck resolutions are never written to
    the register, so a gap (promise the ceiling then vetoes) is what "theory the
    line predicts, practice does not deliver" measurably looks like.
    """
    delivery = graph.get_graph_attr("policy_delivery", None) or {}
    total = 0.0
    for row in delivery.values():
        if str((row or {}).get("incumbent_id", "")) != org_id:
            continue
        gap = float((row or {}).get("promised", 0.0)) - float((row or {}).get("delivered", 0.0))
        if gap > 0.0:
            total += gap
    return total


def _practice_env(
    graph: GraphProtocol, org_id: str, attrs: dict[str, Any]
) -> dict[PracticeVariable, float]:
    """Measure one org's material practice for the doctrine DSL (P25 U11, ADR137).

    I-FRESH quantities read fresh from the org's graph position each tick — the
    re-founded reformist fork's traps are gated on THESE, not on acquisition
    ``tag_deltas`` (the-electoral-question.md §3.1: "you are not told you
    liquidated; you measurably did"). Read-only, so byte-safe on the org-less qa
    six by never running (no org nodes ⟹ no calls).

    - SOLIDARITY_MASS: Σ ``solidarity_strength`` over the org's SOLIDARITY
      out-edges — its autonomous mass base; → 0 as the base withers.
    - CO_OPTIVE_SHARE: fraction of the org's incident edges carrying the
      ``co_optive`` :class:`EdgeMode` — dependence on concessions-for-quiescence.
    - PETTY_BOURGEOIS_DRIFT: ``1 − cadre_level`` — a CONTINUOUS material proxy
      for embourgeoisement (the professionalised remainder as cadre density
      falls), NEVER the discrete ``class_character`` label (Aleksandrov Test).
    - OFFICE_TENURE: the saturating norm of the org's accumulated ``office_tenure``
      field (the ``institutional_pull`` driver).
    - DELIVERY_DEPENDENCE: the saturating norm of the governing org's delivery
      gap, read from the ``policy_delivery`` register (:func:`_delivery_gap`).
    """
    solidarity_mass = 0.0
    for edge in graph.query_edges(edge_type=EdgeType.SOLIDARITY.value):
        if edge.source_id == org_id:
            solidarity_mass += float(edge.attributes.get("solidarity_strength", 0.0))

    incident = 0
    co_optive = 0
    for edge in graph.query_edges():
        if edge.source_id != org_id and edge.target_id != org_id:
            continue
        incident += 1
        if str(edge.attributes.get("edge_mode", "")) == EdgeMode.CO_OPTIVE.value:
            co_optive += 1
    co_optive_share = (co_optive / incident) if incident else 0.0

    cadre = float(attrs.get("cadre_level", 0.0))
    petty_bourgeois_drift = min(1.0, max(0.0, 1.0 - cadre))

    tenure = float(attrs.get("office_tenure", 0.0))
    office_tenure = tenure / (tenure + 1.0)  # saturating [0, 1)

    gap = _delivery_gap(graph, org_id)
    delivery_dependence = gap / (gap + 1.0)  # saturating [0, 1)

    return {
        PracticeVariable.SOLIDARITY_MASS: solidarity_mass,
        PracticeVariable.CO_OPTIVE_SHARE: co_optive_share,
        PracticeVariable.PETTY_BOURGEOIS_DRIFT: petty_bourgeois_drift,
        PracticeVariable.OFFICE_TENURE: office_tenure,
        PracticeVariable.DELIVERY_DEPENDENCE: delivery_dependence,
    }


def _political_form_position(
    practice_env: Mapping[PracticeVariable, float],
    tags: Mapping[DoctrineTag, float],
    office_tenure: float,
    institutional_pull: float,
) -> tuple[float, float]:
    """One org's ``(self_organization, representation)`` position (§3.4, ADR137).

    The ``political_form`` opposition is self-organization (A) ⇄ representation
    (B) — the class acting through its own organs versus delegating into the
    apparatus. U8 measured it NATIONALLY off allegiance mass; this is the same
    contradiction read at the ORGANIZATIONAL scale, and it re-homes the material
    content of the legacy liberal-trap detector (``engine/trap_detection.py``,
    whose only consumers are the legacy web client's serializers) into the
    engine, off hardcoded thresholds and onto measured practice:

    * **A — self-organization**: MASS_LINK plus the org's SOLIDARITY mass, the
      autonomous capacity it has actually built, saturated into [0, 1].
    * **B — representation**: the mean of institutional pull (Michels), CO_OPTIVE
      share (a base held by concessions), and saturated office tenure — the
      three ways an org's political existence ends up inside the machine.

    Both poles are bounded [0, 1], so the catalog can take a ratio-of-sums
    across orgs without an intensive-aggregation variance error.
    """
    mass_link = float(tags.get(DoctrineTag.MASS_LINK, 0.0))
    solidarity = float(practice_env.get(PracticeVariable.SOLIDARITY_MASS, 0.0))
    autonomous = max(0.0, mass_link + solidarity)
    self_organization = autonomous / (autonomous + 1.0)

    tenure = max(0.0, office_tenure)
    tenure_saturated = tenure / (tenure + 1.0)
    co_optive = float(practice_env.get(PracticeVariable.CO_OPTIVE_SHARE, 0.0))
    representation = (institutional_pull + co_optive + tenure_saturated) / 3.0
    return self_organization, representation


def _decouples_cadre_valve(attrs: dict[str, Any], tree: DoctrineTree) -> bool:
    """Whether an acquired stance decouples the org's cadre from officeholding.

    Read from the tree the caller already holds (no second load). Bounded by the
    acquired list, itself bounded by the tree's node count.
    """
    acquired = tuple(attrs.get("acquired_doctrine_ids", ()))
    return any(
        tree.nodes[node_id].capabilities.cadre_valve_decouple
        for node_id in acquired
        if node_id in tree.nodes
    )


def _officeholder_capture(
    graph: GraphProtocol,
    org_id: str,
    attrs: dict[str, Any],
    capture_rate: float,
    tree: DoctrineTree,
) -> tuple[float, float]:
    """Accrue office tenure + institutional pull for a governing org (§3.3, ADR137).

    Reads the ``electoral_governments`` register (ElectoralSystem @17.45, one tick
    stale — I-ORD). While the org is a seated governing party its ``office_tenure``
    accrues one tick and its ``institutional_pull`` drifts toward 1 at
    ``office_capture_rate`` — Michels' iron law as a RATE, resisted by
    ``cadre_level × cohesion`` (a disciplined base slows the pull toward the
    officeholders' institutional median). Out of office the org keeps its
    accumulated tenure/pull (hysteresis; ``ADR084`` KeyFigure stays retired —
    this is org-level, no per-seat ledger).

    An org holding a stance whose ``DoctrineCapability`` sets
    ``cadre_valve_decouple`` (principled abstention) still accrues TENURE — the
    fact of the office is a fact — but takes NO institutional pull: it does not
    seat its cadre in the assembly, so there is no cadre to convert. That
    immunity to Michels is what the stance buys with its sect-isolation cost
    (P25 U11 §3.2, ADR137).

    Returns ``(office_tenure, pull)``.
    """
    tenure = float(attrs.get("office_tenure", 0.0))
    pull = float(attrs.get("institutional_pull", 0.0))
    governments = graph.get_graph_attr("electoral_governments", None) or {}
    governs = any(str((gov or {}).get("party_id", "")) == org_id for gov in governments.values())
    if not governs:
        return tenure, pull
    tenure += 1.0
    if _decouples_cadre_valve(attrs, tree):
        return tenure, pull
    resistance = 1.0 - min(
        1.0, float(attrs.get("cadre_level", 0.0)) * float(attrs.get("cohesion", 0.0))
    )
    pull = min(1.0, pull + capture_rate * resistance * (1.0 - pull))
    return tenure, pull


def _apply_practice_drift(
    tags: dict[DoctrineTag, float],
    practice_env: Mapping[PracticeVariable, float],
    institutional_pull: float,
    delivery_gap: float,
    coeffs: Mapping[str, float],
) -> dict[DoctrineTag, float]:
    """Practice → tag drift: the re-founded reformist fork's tag movement comes
    from PRACTICE, not acquisition ``tag_deltas`` (P25 U11, §3.1). Three erosions,
    each applied only to a POSITIVE tag and floored at 0 (no spurious 0-entries):

    - CLASS_ANALYSIS decays by ``class_analysis_veto_decay × delivery_gap`` —
      theory rots when the line predicts deliveries the ceiling then vetoes (the
      Unit-6b theory bonus, run in reverse).
    - CLASS_ANALYSIS decays by ``reformist_theory_decay × institutional_pull`` —
      Michels' iron law expressed as theory rot under officeholder capture.
    - MASS_LINK decays by ``co_optive_dependence_drift × CO_OPTIVE_SHARE`` — a
      base held by concessions-for-quiescence is not a live mass link.
    """
    out = dict(tags)
    ca_decay = (
        coeffs.get("class_analysis_veto_decay", 0.0) * delivery_gap
        + coeffs.get("reformist_theory_decay", 0.0) * institutional_pull
    )
    if ca_decay > 0.0 and out.get(DoctrineTag.CLASS_ANALYSIS, 0.0) > 0.0:
        out[DoctrineTag.CLASS_ANALYSIS] = max(0.0, out[DoctrineTag.CLASS_ANALYSIS] - ca_decay)
    ml_decay = coeffs.get("co_optive_dependence_drift", 0.0) * practice_env.get(
        PracticeVariable.CO_OPTIVE_SHARE, 0.0
    )
    if ml_decay > 0.0 and out.get(DoctrineTag.MASS_LINK, 0.0) > 0.0:
        out[DoctrineTag.MASS_LINK] = max(0.0, out[DoctrineTag.MASS_LINK] - ml_decay)
    return out


def _reachable_traps(tree: DoctrineTree, acquired: tuple[str, ...]) -> list[DoctrineNode]:
    """Trap nodes whose every parent is already held (id-sorted for determinism)."""
    held = set(acquired)
    traps = [
        node
        for node in tree.nodes.values()
        if node.is_trap
        and node.id not in held
        and node.trap_condition is not None
        and all(parent in held for parent in node.parents)
    ]
    return sorted(traps, key=lambda n: n.id)


def _read_tags(raw: object) -> dict[DoctrineTag, float]:
    """Coerce a graph node's ``doctrine_tags`` attr to a float accumulator dict."""
    if not isinstance(raw, dict):
        return {}
    out: dict[DoctrineTag, float] = {}
    for tag, value in raw.items():
        key = tag if isinstance(tag, DoctrineTag) else DoctrineTag(tag)
        out[key] = float(value)
    return out


#: A typed empty measured-practice map — the default when a caller (a direct
#: unit test) supplies none. Named + shared so the ``{**tags, **practice}`` merge
#: below always infers ``dict[DoctrineTag | PracticeVariable, float]`` (mypy's
#: Mapping key type is invariant; an empty dict literal would collapse it).
_NO_PRACTICE: Mapping[PracticeVariable, float] = MappingProxyType({})


def step_organization(
    attrs: dict[str, Any],
    tree: DoctrineTree,
    defines: DoctrineDefines,
    practice_env: Mapping[PracticeVariable, float] | None = None,
    coeffs: Mapping[str, float] | None = None,
) -> tuple[tuple[str, ...], float, dict[DoctrineTag, float], list[str], str | None]:
    """Advance one organization's doctrine state by one tick (pure).

    A standing ``study_target_id`` (the player's Educate(Doctrine) order,
    Unit 7b) redirects acquisition: while the target is UNLOCKED (parents
    held) but unaffordable, the org SAVES its theoretical labor — greedy
    auto-acquire is suspended (directed study is wallet discipline); once
    affordable it is acquired and the order clears. While the target is
    still LOCKED, greedy continues (building the tree toward it). An
    invalid, trap, or already-held target clears the order.

    :param attrs: The org node's current attribute mapping.
    :param practice_env: The org's measured-practice quantities (P25 U11), merged
        with the tag totals into the trap-condition evaluation environment; the
        reformist fork's absorbing states are gated on this half. ``None`` (a
        direct pure-tag unit-test call) means no practice quantities.
    :param coeffs: ``@name`` threshold coefficients the trap conditions reference
        (the liquidation thresholds); ``None`` means no ``@`` references permitted.
    :returns: ``(acquired_ids, theoretical_labor, doctrine_tags,
        sprung_trap_ids, study_target_id)``.
    """
    acquired: tuple[str, ...] = tuple(attrs.get("acquired_doctrine_ids", ()))
    tl = float(attrs.get("theoretical_labor", 0.0))
    tags = _read_tags(attrs.get("doctrine_tags"))
    cadre = float(attrs.get("cadre_level", 0.0))
    raw_target = attrs.get("study_target_id")
    study_target: str | None = str(raw_target) if raw_target else None

    tags = decay_tags(tags, defines.tag_decay_rate)
    study_allocation = (defines.study_allocation_min + defines.study_allocation_max) / 2.0
    tl += accrue_theoretical_labor(cadre, study_allocation)

    if tree.root_id not in acquired and can_acquire(tree, acquired, tree.root_id, tl):
        acquired = acquire(acquired, tree.root_id)
        tags = _apply_deltas(tags, tree.nodes[tree.root_id].tag_deltas)

    target_node = tree.nodes.get(study_target) if study_target is not None else None
    if study_target is not None and (
        target_node is None or target_node.is_trap or study_target in acquired
    ):
        study_target = None
        target_node = None

    if target_node is not None and all(p in set(acquired) for p in target_node.parents):
        # Directed study: acquire when affordable, otherwise save — no greedy.
        if tl >= target_node.cost_tl:
            tl -= target_node.cost_tl
            acquired = acquire(acquired, target_node.id)
            tags = _apply_deltas(tags, target_node.tag_deltas)
            study_target = None
    else:
        candidate = _cheapest_acquirable(tree, acquired, tl)
        if candidate is not None:
            tl -= tree.nodes[candidate].cost_tl
            acquired = acquire(acquired, candidate)
            tags = _apply_deltas(tags, tree.nodes[candidate].tag_deltas)
            if study_target == candidate:
                study_target = None

    sprung: list[str] = []
    # The DSL env merges tag totals with measured practice (P25 U11); the
    # reformist fork's absorbing states are gated on the practice half against
    # @coeff thresholds, while pure-tag conditions ignore the practice keys.
    practice = practice_env if practice_env is not None else _NO_PRACTICE
    # Build via a covariant list of (key, value) pairs — a direct dict merge
    # trips mypy's invariant Mapping key type (DoctrineTag vs PracticeVariable).
    merged: list[tuple[DoctrineTag | PracticeVariable, float]] = [
        *tags.items(),
        *practice.items(),
    ]
    env = dict(merged)
    for trap in _reachable_traps(tree, acquired):
        if evaluate_trap_condition(trap.trap_condition or "", env, coeffs):
            acquired = acquire(acquired, trap.id)
            tags = _apply_deltas(tags, trap.tag_deltas)
            sprung.append(trap.id)

    return acquired, tl, tags, sprung, study_target


#: The five reformist-fork stances (P25 U11). An org holding more than one is in
#: a line struggle the congress resolves as a split (§3.3).
_REFORMIST_STANCES: tuple[str, ...] = (
    "abstention_boycott",
    "class_struggle_elections",
    "entryism",
    "independent_ballot_line",
    "governance_road",
)


def _resolve_line_struggle(
    acquired: tuple[str, ...], tl: float, retention: float
) -> tuple[tuple[str, ...], float, tuple[str, str] | None]:
    """Consolidate an org holding >1 reformist stance to its NEWEST line (§3.3).

    Switching stances is a congress motion resolved by the same DT-5 machinery:
    the org keeps its last-acquired stance and sheds the earlier branches, whose
    assets convert below par — theoretical labour is retained only at
    ``split_asset_retention`` ("electeds rarely follow you out; canvass-cadre
    skills don't convert at par"; hysteresis, "you become what you do"). Returns
    ``(acquired, tl, (old_stance, new_stance))``, or the inputs with ``None``
    when there is no line struggle to resolve.
    """
    held = [s for s in acquired if s in _REFORMIST_STANCES]
    if len(held) <= 1:
        return acquired, tl, None
    keep = held[-1]
    shed = set(held[:-1])
    consolidated = tuple(a for a in acquired if a not in shed)
    return consolidated, tl * retention, (held[0], keep)


def compute_doctrine(
    graph: GraphProtocol,
    defines: DoctrineDefines,
    tree: DoctrineTree,
    *,
    tick: int = 0,
    rng: random.Random | None = None,
    coeffs: Mapping[str, float] | None = None,
) -> list[tuple[str, str, str]]:
    """Run the doctrine loop over every organization node; write state back.

    On a congress tick (``tick > 0`` and ``tick % congress_interval_ticks == 0``,
    ``rng`` provided) the Party Congress convenes FIRST — it sums up the period
    the org just lived through — then the ordinary per-tick step runs. The RNG
    is drawn only when a purge is actually attempted, so org-less graphs (the
    qa:regression goldens) never touch the stream.

    :returns: ``(org_id, node_id, kind)`` triples — ``kind`` is ``"sprung"``
        (trap fallen into), ``"escaped"`` (congress purge succeeded), or
        ``"purge_failed"`` — consumed by :meth:`DoctrineSystem.step` to
        publish as ``DoctrineEvent`` instances (Unit 6a, ADR073).
    """
    events: list[tuple[str, str, str]] = []
    positions: dict[str, dict[str, float]] = {}
    is_congress = tick > 0 and rng is not None and tick % defines.congress_interval_ticks == 0
    for node in graph.query_nodes(node_type=NodeType.ORGANIZATION):
        attrs = dict(node.attributes)
        org_id = str(attrs.get("id", node.id))

        if is_congress and rng is not None:
            acquired0 = tuple(attrs.get("acquired_doctrine_ids", ()))
            tl0 = float(attrs.get("theoretical_labor", 0.0))
            tags0 = _read_tags(attrs.get("doctrine_tags"))
            snapshot0 = _read_tags(attrs.get("congress_tag_snapshot"))
            # Same trap+affordability gate run_congress applies — the roll is
            # drawn only when an attempt will actually consume it.
            needs_roll = bool(held_sprung_traps(tree, acquired0)) and tl0 >= float(
                defines.trap_escape_tl
            )
            roll = rng.random() if needs_roll else 0.0
            outcome = run_congress(
                acquired=acquired0,
                theoretical_labor=tl0,
                tags=tags0,
                snapshot=snapshot0,
                tree=tree,
                defines=defines,
                roll=roll,
            )
            attrs["acquired_doctrine_ids"] = outcome.acquired
            attrs["theoretical_labor"] = outcome.theoretical_labor
            attrs["doctrine_tags"] = outcome.doctrine_tags
            attrs["congress_tag_snapshot"] = outcome.snapshot
            if outcome.attempted_trap_id is not None:
                kind = "escaped" if outcome.escaped else "purge_failed"
                events.append((org_id, outcome.attempted_trap_id, kind))
            # Line-struggle resolution (§3.3): an org holding >1 reformist stance
            # consolidates to its newest line at this congress, shedding the
            # earlier branches' assets (retained at split_asset_retention).
            retention = (
                float(coeffs["split_asset_retention"])
                if coeffs and "split_asset_retention" in coeffs
                else 1.0
            )
            consolidated, kept_tl, split = _resolve_line_struggle(
                tuple(attrs["acquired_doctrine_ids"]), float(attrs["theoretical_labor"]), retention
            )
            if split is not None:
                attrs["acquired_doctrine_ids"] = consolidated
                attrs["theoretical_labor"] = kept_tl
                events.append((org_id, f"{split[0]}|{split[1]}", "line_split"))

        practice_env = _practice_env(graph, org_id, attrs)
        capture_rate = (
            float(coeffs["office_capture_rate"])
            if coeffs and "office_capture_rate" in coeffs
            else 0.0
        )
        office_tenure, institutional_pull = _officeholder_capture(
            graph, org_id, attrs, capture_rate, tree
        )
        acquired, tl, tags, sprung, study_target = step_organization(
            attrs, tree, defines, practice_env=practice_env, coeffs=coeffs
        )
        tags = _apply_practice_drift(
            tags, practice_env, institutional_pull, _delivery_gap(graph, org_id), coeffs or {}
        )
        updates: dict[str, Any] = {
            "acquired_doctrine_ids": acquired,
            "theoretical_labor": tl,
            "doctrine_tags": tags,
            "study_target_id": study_target,
            "office_tenure": office_tenure,
            "institutional_pull": institutional_pull,
        }
        if is_congress:
            updates["congress_tag_snapshot"] = attrs["congress_tag_snapshot"]
        graph.update_node(org_id, **updates)
        self_organization, representation = _political_form_position(
            practice_env, tags, office_tenure, institutional_pull
        )
        positions[org_id] = {
            "self_organization": self_organization,
            "representation": representation,
        }
        _decay_mass_work_solidarity_edges(graph, org_id, defines.mass_work_solidarity_decay_rate)
        events.extend((org_id, trap_id, "sprung") for trap_id in sprung)

    # Published only when organizations exist: an org-less world has no
    # organizational political-form contradiction to read, and writing an empty
    # register would fabricate one (III.11) — and would move the org-less
    # qa:regression goldens for a reading that is absent by construction.
    if positions:
        graph.set_graph_attr(POLITICAL_FORM_POSITIONS_ATTR, positions)
    return events


class DoctrineSystem(SystemBase):
    """Advances every organization's Doctrine Tree state each tick.

    See the module docstring for the five-step per-org loop and the Party
    Congress (Unit 5). Seed-deterministic: the only stochastic element is the
    congress purge roll, drawn from :func:`resolve_rng` (Constitution III.7).
    Byte-safe on the org-less qa:regression scenarios (no orgs, no writes,
    no draws).
    """

    partition: ClassVar[TickPartition] = TickPartition.CONSEQUENCE
    position: ClassVar[float] = 14.7

    name: ClassVar[str] = "Doctrine"
    creates_value: ClassVar[bool] = False

    def __init__(self) -> None:
        super().__init__()
        self._tree: DoctrineTree | None = None

    def step(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
    ) -> None:
        """Run the doctrine loop over all organizations, writing per-org state.

        Doctrine events (trap sprung / congress escape / purge failed) are
        published onto ``services.event_bus`` the same way StruggleSystem
        publishes UPRISING (Unit 6a, ADR073): each ``(org_id, node_id, kind)``
        triple from :func:`compute_doctrine` becomes one ``Event`` with the
        matching :data:`_KIND_TO_EVENT_TYPE` EventType and a
        ``{"org_id", "node_id"}`` payload. The behavioural feedback into
        bifurcation/consciousness is Unit 6b, not this method.
        """
        tick = context.tick
        if self._tree is None:
            self._tree = load_doctrine_tree()
        politics = services.defines.politics
        # The politics coefficients the reformist fork needs (P25 U11): the
        # absorbing-state @coeff DSL thresholds + the officeholder-capture rate +
        # the practice→tag drift rates. Read once per tick, passed by name.
        coeffs = {
            "solidarity_liquidation_floor": politics.solidarity_liquidation_floor,
            "co_optive_liquidation_threshold": politics.co_optive_liquidation_threshold,
            "petty_bourgeois_liquidation_threshold": politics.petty_bourgeois_liquidation_threshold,
            "office_capture_rate": politics.office_capture_rate,
            "reformist_theory_decay": politics.reformist_theory_decay,
            "class_analysis_veto_decay": politics.class_analysis_veto_decay,
            "co_optive_dependence_drift": politics.co_optive_dependence_drift,
            "split_asset_retention": politics.split_asset_retention,
        }
        triples = compute_doctrine(
            graph,
            services.defines.doctrine,
            self._tree,
            tick=tick,
            rng=resolve_rng(services, tick),
            coeffs=coeffs,
        )
        for org_id, node_id, kind in triples:
            if kind == "line_split":
                # node_id encodes "old_stance|new_stance"; the richer payload
                # (assets_retained) is reconstructed from the define here.
                old_stance, _, new_stance = node_id.partition("|")
                services.event_bus.publish(
                    Event(
                        type=EventType.LINE_STRUGGLE_SPLIT,
                        tick=tick,
                        payload={
                            "org_id": org_id,
                            "old_stance": old_stance,
                            "new_stance": new_stance,
                            "assets_retained": politics.split_asset_retention,
                        },
                    )
                )
                continue
            services.event_bus.publish(
                Event(
                    type=_KIND_TO_EVENT_TYPE[kind],
                    tick=tick,
                    payload={"org_id": org_id, "node_id": node_id},
                )
            )
