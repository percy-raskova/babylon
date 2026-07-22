"""AllegianceSystem — the electoral valve and the allegiance terrain (P25 U8, ADR134).

Pipeline position 17.42: after ConsciousnessSystem (17.0, which writes this
tick's post-decay agitation) and FascistFactionSystem (17.4, whose
``fascist_alignment`` drift this system reads), BEFORE SovereigntySystem
(17.5) and the U10 ElectoralSystem (17.45, which will consume the hope
field). Belongs to ``CONSEQUENCE`` (spec-056 partition).

Three motions per tick, ALL gated on parties-exist (TRAP 3, charter §U8(d):
a scenario with zero ``PoliticalFaction`` orgs sees zero writes — the
qa:regression six are byte-identical because nothing ever fires, not because
a write is filtered):

1. **Allegiance drift** (brief §2.2): each class's allegiance distribution
   over the party terrain drifts by ``θ.align·fit + θ.contact·contact −
   θ.betrayal·gap_ratio`` (the betrayal term reads the PRIOR tick's
   delivery ledger, its producer landed with U9/ADR135; the media/ISA_COMM
   term still awaits its producer), plus the reactionary coupling — a class's
   ``fascist_alignment`` (@17.4) pulls its allegiance toward
   fascist-ideology parties: the same reactionary machinery, now with a
   ballot expression. Mass discipline via
   :func:`~babylon.formulas.politics.apply_allegiance_drift`.
2. **The hope field and THE VALVE** (brief §2.5): ``H(c) = Σ_p
   allegiance·viability·max(0, ΔP(S|A))`` — the believed arithmetic of the
   acquiescence branch (Aleksandrov, III.8) — throttles the FIRST production
   Agitation→Organization conversion pathway: ``organization +=
   rate·agitation·(1 − v·H)``. TRAP 1 ruling: this is a NEW quantity;
   the consciousness router (``route_agitation_to_ternary``) is never
   touched. ``HOPE_SPIKE`` publishes on a hope jump past
   ``hope_spike_gain``.
3. **The political_form producer** (closes U3's deferred W-C row): the
   dialectic analyzed is SYSTEM-LOYAL vs SYSTEM-OPPOSITIONAL (BD ruling
   2026-07-22) — ``political_labor_share = (loyal − oppositional) /
   (loyal + oppositional)`` where loyal = allegiance mass delegated into
   the system's channel and oppositional = organization, the autonomous
   capacity built against it. Published as a graph attribute for
   ContradictionSystem's ``GraphInputs`` @18.

Grounding of the U8 promise proxy (refined by U9's funding identity): a
party's promised transfer to class c is ``max(0, fit)·phi_social_share·
subsistence(c)`` — the promise scales with the class's needs and is bounded
by the theory's social-wage ceiling share; ``ΔP(S|A)`` is one counterfactual
evaluation of the existing survival sigmoid (T-5: previews are evaluations).
Viability before elections exist (U10 refines with real returns) is the
material proxy ``(funding_share + membership_share) / 2``.

Determinism (III.7): sorted iteration everywhere; no RNG.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from babylon.engine.systems.policy import POLICY_DELIVERY_ATTR
from babylon.formulas.politics import (
    allegiance_drift,
    apply_allegiance_drift,
    counterfactual_hope_gain,
    hope_field,
    interest_fit,
    platform_vector,
    valve_multiplier,
)
from babylon.kernel.event_bus import Event
from babylon.kernel.system_base import SystemBase
from babylon.kernel.tick_partition import TickPartition
from babylon.models.enums import EdgeType, EventType, NodeType, OrgType

if TYPE_CHECKING:  # pragma: no cover
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol
    from babylon.kernel.system_protocol import ContextType
    from babylon.models.graph import GraphNode

#: Ideology tokens marking a PoliticalFaction as the fascist ballot vehicle
#: (mirrors FascistFactionSystem's BalkanizationFaction token fallback).
_FASCIST_IDEOLOGY_TOKENS: tuple[str, ...] = ("fascist", "reaction", "revanch", "settler")

#: Persistent-state key for the previous tick's hope field (HOPE_SPIKE delta).
_HOPE_KEY = "politics.hope_by_class"


class AllegianceSystem(SystemBase):
    """Consequence-phase system for the ambient electoral machine (U8)."""

    partition: ClassVar[TickPartition] = TickPartition.CONSEQUENCE
    position: ClassVar[float] = 17.42

    name: ClassVar[str] = "Allegiance"
    # Allegiance/hope/organization mutate class political state, never hex
    # c+v+s (Spec 053 INV-001); politics routes value, it never mints it.
    creates_value: ClassVar[bool] = False

    def step(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
    ) -> None:
        wrapped = self._wrap_graph(graph)
        parties = self._political_factions(wrapped)
        if not parties:
            # TRAP 3: the ambient machine is absent — zero writes, zero
            # events, zero graph attrs. Every party-less scenario (including
            # all six qa:regression fixtures) is byte-unchanged.
            return

        defines = services.defines.politics
        steepness = services.defines.survival.steepness_k
        classes = sorted(
            (
                node
                for node in wrapped.query_nodes(node_type=NodeType.SOCIAL_CLASS)
                if node.attributes.get("active", True)
            ),
            key=lambda n: n.id,
        )
        if not classes:
            return

        membership = self._membership_map(wrapped, {p.id for p in parties})
        funding_share = self._funding_shares(wrapped, [p.id for p in parties])
        interest = {node.id: self._interest_vector(node) for node in classes}
        platforms = self._platforms(parties, classes, membership, funding_share, interest, defines)
        viability = self._viability(parties, membership, funding_share)

        # P25 U9 (ADR135): the PRIOR tick's per-class delivery ledger —
        # PolicySystem @17.47 writes it AFTER this system runs (17.47 >
        # 17.42), so the betrayal drift term always reads last tick's gap
        # (the one-tick lag is the I-ORD grain). Absent ledger ⟹ the term
        # is exactly zero, the pre-U9 arithmetic.
        delivery_raw = wrapped.get_graph_attr(POLICY_DELIVERY_ATTR, None)
        delivery: dict[str, dict[str, object]] = (
            {k: dict(v) for k, v in dict(delivery_raw).items()}
            if isinstance(delivery_raw, dict)
            else {}
        )

        prev_hope_raw = context.persistent_data.get(_HOPE_KEY, {})
        prev_hope: dict[str, float] = dict(prev_hope_raw) if prev_hope_raw else {}
        new_hope: dict[str, float] = {}
        loyal_mass = 0.0
        oppositional_mass = 0.0

        for node in classes:
            attrs = node.attributes
            allegiance = self._drift_allegiance(
                node, parties, platforms, membership, interest, defines, delivery
            )
            hope = self._hope(
                node, parties, allegiance, platforms, viability, interest, defines, steepness
            )
            organization = self._convert(attrs, hope, defines)

            updates: dict[str, object] = {"allegiance": allegiance, "hope": hope}
            if organization is not None:
                updates["organization"] = organization
            wrapped.update_node(node.id, **updates)

            self._maybe_publish_spike(
                services,
                context.tick,
                node.id,
                hope,
                prev_hope.get(node.id, 0.0),
                platforms,
                interest[node.id],
                defines,
            )
            new_hope[node.id] = hope
            loyal_mass += sum(allegiance.values())
            oppositional_mass += float(
                organization if organization is not None else attrs.get("organization", 0.0)
            )

        context.persistent_data[_HOPE_KEY] = new_hope

        # The political_form producer (U3's deferred W-C; BD ruling: the
        # dialectic is system-loyal vs system-oppositional).
        total = loyal_mass + oppositional_mass
        if total > 0.0:
            wrapped.set_graph_attr(
                "political_labor_share", (loyal_mass - oppositional_mass) / total
            )

    # ------------------------------------------------------------------
    # Terrain readers
    # ------------------------------------------------------------------

    def _political_factions(self, graph: GraphProtocol) -> list[GraphNode]:
        """Every PoliticalFaction org node, sorted by id (III.7)."""
        return sorted(
            (
                node
                for node in graph.query_nodes(node_type=NodeType.ORGANIZATION)
                if node.attributes.get("org_type") == OrgType.POLITICAL_FACTION.value
            ),
            key=lambda n: n.id,
        )

    def _membership_map(self, graph: GraphProtocol, party_ids: set[str]) -> dict[str, set[str]]:
        """party_id -> the class ids its MEMBERSHIP edges reach."""
        reach: dict[str, set[str]] = {pid: set() for pid in party_ids}
        for edge in graph.query_edges(edge_type=EdgeType.MEMBERSHIP):
            if edge.source_id in reach:
                reach[edge.source_id].add(edge.target_id)
        return reach

    def _funding_shares(self, graph: GraphProtocol, party_ids: list[str]) -> dict[str, float]:
        """party_id -> share of total TRANSACTIONAL inflow (0 when none)."""
        inflow = dict.fromkeys(party_ids, 0.0)
        for edge in graph.query_edges(edge_type=EdgeType.TRANSACTIONAL):
            if edge.target_id in inflow:
                inflow[edge.target_id] += float(edge.attributes.get("value_flow", 0.0))
        total = sum(inflow.values())
        if total <= 0.0:
            return dict.fromkeys(party_ids, 0.0)
        return {pid: flow / total for pid, flow in inflow.items()}

    def _interest_vector(self, node: GraphNode) -> tuple[float, float]:
        """A class's material interest vector: (survival margin, consciousness).

        Both components read real node state: the survival axis
        ``wealth − subsistence_threshold`` and the ideological axis
        ``class_consciousness`` (nested ideology dict, the @17.0 write).
        """
        attrs = node.attributes
        ideology = attrs.get("ideology") or {}
        margin = float(attrs.get("wealth", 0.0)) - float(attrs.get("subsistence_threshold", 0.0))
        consciousness = float(ideology.get("class_consciousness", 0.0) or 0.0)
        return (margin, consciousness)

    def _platforms(
        self,
        parties: list[GraphNode],
        classes: list[GraphNode],
        membership: dict[str, set[str]],
        funding_share: dict[str, float],
        interest: dict[str, tuple[float, float]],
        defines: object,
    ) -> dict[str, tuple[float, ...]]:
        """Derived platform per party (II.2 — computed fresh, never stored).

        Base terms: unit-weight interest vectors of the party's MEMBERSHIP
        classes. Donor terms: the party's funding share pulling along the
        mean interest vector of the terrain's bourgeois-margin classes (the
        donor's material interest IS capital's) — skipped honestly when no
        such class exists.
        """
        by_margin = sorted(classes, key=lambda n: interest[n.id][0], reverse=True)
        donor_interest = interest[by_margin[0].id] if by_margin else None

        platforms: dict[str, tuple[float, ...]] = {}
        for party in parties:
            base_terms = tuple(
                (1.0, interest[cid])
                for cid in sorted(membership.get(party.id, ()))
                if cid in interest
            )
            donor_terms: tuple[tuple[float, tuple[float, ...]], ...] = ()
            share = funding_share.get(party.id, 0.0)
            if share > 0.0 and donor_interest is not None:
                donor_terms = ((share, donor_interest),)
            platforms[party.id] = platform_vector(
                base_terms,
                donor_terms,
                donor_weight=defines.donor_platform_weight,  # type: ignore[attr-defined]
            )
        return platforms

    def _viability(
        self,
        parties: list[GraphNode],
        membership: dict[str, set[str]],
        funding_share: dict[str, float],
    ) -> dict[str, float]:
        """Pre-electoral viability proxy: mean of funding and base shares.

        U10 replaces this with real returns once the election clock runs.
        """
        total_members = sum(len(membership.get(p.id, ())) for p in parties)
        viability: dict[str, float] = {}
        for party in parties:
            member_share = (
                len(membership.get(party.id, ())) / total_members if total_members else 0.0
            )
            viability[party.id] = 0.5 * funding_share.get(party.id, 0.0) + 0.5 * member_share
        return viability

    # ------------------------------------------------------------------
    # Per-class motions
    # ------------------------------------------------------------------

    def _drift_allegiance(
        self,
        node: GraphNode,
        parties: list[GraphNode],
        platforms: dict[str, tuple[float, ...]],
        membership: dict[str, set[str]],
        interest: dict[str, tuple[float, float]],
        defines: object,
        delivery: dict[str, dict[str, object]],
    ) -> dict[str, float]:
        """One class's drifted allegiance masses over the party terrain."""
        attrs = node.attributes
        current_raw = attrs.get("allegiance") or {}
        fascist_alignment = float(attrs.get("fascist_alignment", 0.0))

        # The betrayal term (θ.betrayal, producer landed U9/ADR135): the
        # incumbent's PRIOR-tick delivery gap, as the dimensionless ratio
        # gap/promised, repels this class's allegiance from the incumbent.
        # Pre-U10 the ledger's incumbent is the enacting SOVEREIGN, which
        # no party id matches — the term goes live when U10 seats a
        # governing party as the incumbent (or a scenario stamps one).
        row = delivery.get(node.id) or {}
        incumbent_id = str(row.get("incumbent_id", ""))
        gap = row.get("gap")
        promised = row.get("promised")
        gap_ratio = 0.0
        if isinstance(gap, (int, float)) and isinstance(promised, (int, float)) and promised > 0.0:
            gap_ratio = min(1.0, max(0.0, float(gap) / float(promised)))

        ordered = [p.id for p in parties]
        current = tuple(float(current_raw.get(pid, 0.0)) for pid in ordered)
        deltas = []
        for party in parties:
            fit = interest_fit(interest[node.id], platforms[party.id])
            contact = 1.0 if node.id in membership.get(party.id, ()) else 0.0
            betrayed = gap_ratio if party.id == incumbent_id else 0.0
            delta = allegiance_drift(
                fit=fit,
                contact=contact,
                align_rate=defines.allegiance_align_rate,  # type: ignore[attr-defined]
                contact_rate=defines.allegiance_contact_rate,  # type: ignore[attr-defined]
                delivery_gap_term=betrayed,
                betrayal_rate=defines.allegiance_betrayal_rate,  # type: ignore[attr-defined]
            )
            if fascist_alignment > 0.0 and self._is_fascist_vehicle(party):
                # The reactionary coupling: @17.4's drift acquires its
                # ballot expression through the same align pacing.
                delta += defines.allegiance_align_rate * fascist_alignment  # type: ignore[attr-defined]
            deltas.append(delta)

        masses, _abstention = apply_allegiance_drift(current, tuple(deltas))
        return dict(zip(ordered, masses, strict=True))

    def _is_fascist_vehicle(self, party: GraphNode) -> bool:
        ideology = str(party.attributes.get("ideology", "")).lower()
        return any(token in ideology for token in _FASCIST_IDEOLOGY_TOKENS)

    def _hope(
        self,
        node: GraphNode,
        parties: list[GraphNode],
        allegiance: dict[str, float],
        platforms: dict[str, tuple[float, ...]],
        viability: dict[str, float],
        interest: dict[str, tuple[float, float]],
        defines: object,
        steepness: float,
    ) -> float:
        """H(c): the believed arithmetic of the acquiescence branch (§2.5)."""
        attrs = node.attributes
        wealth = float(attrs.get("wealth", 0.0))
        subsistence = float(attrs.get("subsistence_threshold", 0.0))
        terms = []
        for party in parties:
            fit = interest_fit(interest[node.id], platforms[party.id])
            promised = max(0.0, fit) * defines.phi_social_share * subsistence  # type: ignore[attr-defined]
            delta = counterfactual_hope_gain(wealth, subsistence, promised, steepness)
            terms.append((allegiance.get(party.id, 0.0), viability.get(party.id, 0.0), delta))
        return min(1.0, hope_field(tuple(terms)))

    def _convert(self, attrs: dict[str, Any], hope: float, defines: object) -> float | None:
        """THE VALVE: the real Agitation→Organization conversion (TRAP 1).

        Returns the new organization value, or ``None`` when there is
        nothing to convert (zero agitation leaves the field untouched).
        """
        ideology = attrs.get("ideology") or {}
        agitation = float(ideology.get("agitation", 0.0) or 0.0)
        if agitation <= 0.0:
            return None
        organization = float(attrs.get("organization", 0.0))
        gain = float(
            defines.organizing_conversion_rate  # type: ignore[attr-defined]
            * agitation
            * valve_multiplier(hope, defines.valve_strength)  # type: ignore[attr-defined]
        )
        if gain <= 0.0:
            return None
        return min(1.0, organization + gain)

    def _maybe_publish_spike(
        self,
        services: ServicesProtocol,
        tick: int,
        class_id: str,
        hope: float,
        prev_hope: float,
        platforms: dict[str, tuple[float, ...]],
        class_interest: tuple[float, float],
        defines: object,
    ) -> None:
        """Publish HOPE_SPIKE when H(c) jumps past the spike gain (§2.5)."""
        if hope - prev_hope <= defines.hope_spike_gain:  # type: ignore[attr-defined]
            return
        best_platform = max(
            sorted(platforms),
            key=lambda pid: (interest_fit(class_interest, platforms[pid]), pid),
        )
        services.event_bus.publish(
            Event(
                type=EventType.HOPE_SPIKE,
                tick=tick,
                payload={
                    "class_id": class_id,
                    "hope": hope,
                    "platform_id": best_platform,
                },
            )
        )
