"""ElectoralSystem @17.45 — the clocked ambient machine (P25 U10, ADR136).

Pipeline position 17.45: after AllegianceSystem (17.42, which writes this
tick's per-class ``allegiance`` masses and ``hope`` field — read SAME tick,
17.42 < 17.45, because ``hope`` never survives the WorldState round-trip) and
before PolicySystem (17.47, which reads the governments register this system
writes so the delivery ledger's incumbent becomes the governing party — the
one-position lead lights U9's θ.betrayal term fully). Belongs to
``CONSEQUENCE``.

Per-sovereign election clock (the ``congress_interval_ticks`` idiom,
DoctrineSystem @14.7): a sovereign's ``JurisdictionLevel`` is its depth on the
ADMINISTERS DAG (apex = federal, one hop = state, deeper = local), its
interval is ``politics.cycle_ticks[level]``, and its electorate is the active
social classes occupying (TENANCY) a territory it claims — with the apex
representing the whole class set (the national electorate) when no TENANCY
link narrows it.

Each fired election runs, in order:

1. **L-SUSPEND check** — if any institution is in bonapartist mode
   (``institutionalist_bonapartist`` past its threshold, the other two
   fractions excluded) AND the mean claimed-territory legitimation sits below
   ``legitimacy_backfire_threshold`` (the legitimation floor), the clock is
   suspended: ``ELECTIONS_SUSPENDED`` fires, disillusion windows open for
   every loyal class, and no vote is counted. The regime's death is reachable,
   not decorative.
2. **The count** — per party, ``votes(p) = Σ_c population·turnout(c)·
   allegiance(c,p)/loyal_mass(c)`` over the turnout law
   (:func:`~babylon.formulas.politics.turnout_share`); FPTP winner by
   ``(−votes, id)``; a top-two margin inside ``recount_margin`` resolves
   through ξ_t (``resolve_rng``, the congress-purge III.7 precedent — one
   seeded coin). ``ELECTION_HELD`` carries turnout, competitiveness, winner.
3. **Government formation** — the winning party's aligned ruling-class faction
   is nudged up in every ``StateApparatus`` org's ``faction_balance`` (bounded
   by ``state_ai.max_faction_shift_per_tick`` — the deep state is the
   α-smoothing; Weimar is a parameter flow, not a script). The winner is
   written to the governments register. ``GOVERNMENT_FORMED``.
4. **Legitimation refresh** — each claimed territory's ``legitimation_index``
   moves toward ``turnout·competitiveness`` by ``legitimation_refresh_weight``
   (a walkover manufactures less consent than a contest). ``LEGITIMATION_REFRESH``.
5. **Institution balance shift** — ``update_internal_balance`` fires per
   institution (crisis from claimed-territory crisis phases, legitimacy from
   the refresh, no external threat modeled yet); the new balance is written
   back and its ``INSTITUTION_FACTION_SHIFT`` / ``INSTITUTION_BONAPARTIST_MODE``
   events published.
6. **H-collapse routing** — every electorate class whose plurality party lost
   opens a disillusion window; ``bridges_present`` (any incident SOLIDARITY
   edge) is stamped so AllegianceSystem routes the boosted conversion by T-7
   next tick (bridges → radicalize; no bridges → ``fascist_alignment``).

Byte-safety (charter §U10(d)): every motion sits behind the parties-exist
guard — a scenario with zero ``PoliticalFaction`` orgs never opens a window,
never fires a clock, never draws ξ_t. The six qa:regression fixtures carry no
parties, so all six are byte-identical with the system live.

Determinism (III.7): sorted iteration everywhere; ξ_t only at recount grain.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Final

from babylon.domain.institution.balance import update_internal_balance
from babylon.formulas.politics import competitiveness, turnout_share
from babylon.kernel.event_bus import Event
from babylon.kernel.system_base import SystemBase, resolve_rng
from babylon.kernel.tick_partition import TickPartition
from babylon.models.entities.state_apparatus_ai import FactionBalance
from babylon.models.enums import EdgeType, EventType, NodeType, OrgType, StateFaction

if TYPE_CHECKING:  # pragma: no cover
    import random

    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol
    from babylon.kernel.system_protocol import ContextType
    from babylon.models.graph import GraphNode

#: Governments register: ``{sovereign_id: {"party_id", "formed_tick",
#: "share"}}``. Written here on GOVERNMENT_FORMED; PolicySystem @17.47 reads it
#: SAME tick so the delivery ledger's incumbent is the governing party (U9's
#: θ.betrayal producer, ADR135). Owner: this file (sentinels/superstructure).
ELECTORAL_GOVERNMENTS_ATTR: Final[str] = "electoral_governments"

#: Disillusion windows: ``{class_id: {"opened_tick", "window_ticks",
#: "bridges_present"}}``. Written here on loss/suspension; AllegianceSystem
#: @17.42 reads it NEXT tick (17.42 < 17.45) to route the boosted conversion
#: by T-7. Owner: this file.
ELECTORAL_DISILLUSION_ATTR: Final[str] = "electoral_disillusion"

#: JurisdictionLevel keys (politics.cycle_ticks) by ADMINISTERS-DAG depth.
_LEVEL_BY_DEPTH: Final[tuple[str, str, str]] = ("federal", "state", "local")

#: Winning party ideology token → the ruling-class faction it steers toward
#: (§2.3: an elected government steers the existing state, it does not replace
#: it). A social-democratic win governs THROUGH the liberal-technocratic wing
#: (finance capital tolerates reform); the reactionary currents feed the
#: settler-populist mass base. security_state is never an electoral target —
#: it rises through crisis, not the ballot.
_FACTION_BY_IDEOLOGY: Final[dict[str, StateFaction]] = {
    "liberal_imperial": StateFaction.FINANCE_CAPITAL,
    "social_democratic": StateFaction.FINANCE_CAPITAL,
    "restorationist": StateFaction.SETTLER_POPULIST,
    "fascist": StateFaction.SETTLER_POPULIST,
}

#: Claimed-territory crisis phases counted as "in crisis" for the institution
#: balance's ``crisis_intensity`` input (the TickDynamicsSystem @4.0 phase set;
#: fresh at 17.45, unlike the one-tick-stale dialectical regime @18.0).
_CRISIS_PHASES: Final[frozenset[str]] = frozenset({"onset", "early", "deep"})


class ElectoralSystem(SystemBase):
    """Consequence-phase clocked election machine (U10)."""

    partition: ClassVar[TickPartition] = TickPartition.CONSEQUENCE
    position: ClassVar[float] = 17.45

    name: ClassVar[str] = "Electoral"
    # Elections route consent and perturb the existing state; they never mint
    # value (Spec 053 INV-001; the four-source license is untouched).
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
            # TRAP 3 / §U10(d): no ambient machine — no clock, no window, no
            # ξ_t. Every party-less scenario (the qa six) is byte-unchanged.
            return

        defines = services.defines.politics
        self._prune_windows(wrapped, context.tick)
        classes = self._active_classes(wrapped)
        if not classes:
            return

        for sovereign in self._sovereigns(wrapped):
            level = self._level_of(wrapped, sovereign.id)
            interval = int(dict(defines.cycle_ticks).get(level, 0))
            if interval <= 0 or context.tick <= 0 or context.tick % interval != 0:
                continue
            electorate = self._electorate(wrapped, sovereign.id, classes)
            if not electorate:
                continue
            self._run_election(
                wrapped, services, context, sovereign, parties, electorate, level, defines
            )

    # ------------------------------------------------------------------
    # Terrain readers
    # ------------------------------------------------------------------

    def _political_factions(self, graph: GraphProtocol) -> list[GraphNode]:
        return sorted(
            (
                node
                for node in graph.query_nodes(node_type=NodeType.ORGANIZATION)
                if node.attributes.get("org_type") == OrgType.POLITICAL_FACTION.value
            ),
            key=lambda n: n.id,
        )

    def _active_classes(self, graph: GraphProtocol) -> list[GraphNode]:
        return sorted(
            (
                node
                for node in graph.query_nodes(node_type=NodeType.SOCIAL_CLASS)
                if node.attributes.get("active", True)
            ),
            key=lambda n: n.id,
        )

    def _sovereigns(self, graph: GraphProtocol) -> list[GraphNode]:
        return sorted(graph.query_nodes(node_type=NodeType.SOVEREIGN), key=lambda n: n.id)

    def _level_of(self, graph: GraphProtocol, sovereign_id: str) -> str:
        """JurisdictionLevel key = ADMINISTERS-DAG depth (apex = federal)."""
        depth = 0
        current = sovereign_id
        seen: set[str] = set()
        for _ in range(len(_LEVEL_BY_DEPTH) + 2):  # bounded: DAG is shallow
            parent = self._administers_parent(graph, current)
            if parent is None or parent in seen:
                break
            seen.add(parent)
            depth += 1
            current = parent
        return _LEVEL_BY_DEPTH[min(depth, len(_LEVEL_BY_DEPTH) - 1)]

    def _administers_parent(self, graph: GraphProtocol, sovereign_id: str) -> str | None:
        parents = sorted(
            edge.source_id
            for edge in graph.query_edges(edge_type=EdgeType.ADMINISTERS)
            if edge.target_id == sovereign_id
        )
        return parents[0] if parents else None

    def _claimed_territories(self, graph: GraphProtocol, sovereign_id: str) -> list[str]:
        claimed: list[str] = []
        for node in sorted(graph.query_nodes(node_type=NodeType.TERRITORY), key=lambda n: n.id):
            rows = graph.query_territory_claims(node.id)
            if rows and rows[0][0] == sovereign_id:
                claimed.append(node.id)
        return claimed

    def _electorate(
        self, graph: GraphProtocol, sovereign_id: str, classes: list[GraphNode]
    ) -> list[GraphNode]:
        """The classes eligible to vote in this sovereign's election.

        A sovereign that claims no territory governs nothing and holds no
        election. The apex (no ADMINISTERS parent) represents the whole
        active class set — the national electorate. A sub-sovereign votes
        only the classes occupying (TENANCY) a territory it claims (you vote
        where you live; a jurisdiction with no residents is empty)."""
        claimed = set(self._claimed_territories(graph, sovereign_id))
        if not claimed:
            return []
        if self._administers_parent(graph, sovereign_id) is None:
            return classes
        occupants: set[str] = set()
        for edge in graph.query_edges(edge_type=EdgeType.TENANCY):
            if edge.target_id in claimed:
                occupants.add(edge.source_id)
        return [c for c in classes if c.id in occupants]

    # ------------------------------------------------------------------
    # The election
    # ------------------------------------------------------------------

    def _run_election(  # noqa: PLR0913 — the terrain is irreducibly wide
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
        sovereign: GraphNode,
        parties: list[GraphNode],
        electorate: list[GraphNode],
        level: str,
        defines: Any,
    ) -> None:
        claimed = self._claimed_territories(graph, sovereign.id)
        legitimation = self._mean_legitimation(graph, claimed)
        apparatus = services.defines.institution
        if self._bonapartist_suspension(graph, legitimation, defines, apparatus):
            self._suspend(graph, services, context.tick, sovereign.id, electorate, legitimation)
            return

        turnouts = {c.id: self._turnout(c, defines) for c in electorate}
        votes = self._count_votes(electorate, parties, turnouts)
        ranked = sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))
        total_votes = sum(votes.values())
        shares = [v / total_votes for _p, v in ranked] if total_votes > 0 else []
        winner = self._resolve_winner(ranked, shares, services, context.tick, defines)
        comp = competitiveness([v for _p, v in ranked])
        participation = sum(turnouts.values()) / len(turnouts) if turnouts else 0.0

        self._emit(
            services,
            context.tick,
            EventType.ELECTION_HELD,
            {
                "sovereign_id": sovereign.id,
                "jurisdiction_level": level,
                "turnout": participation,
                "competitiveness": comp,
                "winning_coalition": winner,
            },
        )
        self._form_government(graph, services, context.tick, sovereign.id, parties, winner, shares)
        self._refresh_legitimation(
            graph, services, context.tick, claimed, participation * comp, defines
        )
        self._shift_institutions(graph, services, context.tick, claimed, legitimation)
        self._open_loss_windows(graph, services, context.tick, electorate, parties, winner, defines)

    def _turnout(self, node: GraphNode, defines: Any) -> float:
        attrs = node.attributes
        allegiance = dict(attrs.get("allegiance") or {})
        loyal_mass = sum(float(v) for v in allegiance.values())
        hope = float(attrs.get("hope", 0.0) or 0.0)
        repression = float(attrs.get("repression_faced", 0.0) or 0.0)
        return turnout_share(
            base_turnout=float(defines.base_turnout),
            loyal_mass=loyal_mass,
            hope=hope,
            repression_faced=repression,
            suppression_weight=float(defines.suppression_cost_weight),
        )

    def _count_votes(
        self,
        electorate: list[GraphNode],
        parties: list[GraphNode],
        turnouts: dict[str, float],
    ) -> dict[str, float]:
        """FPTP tally: each class's turnout is split among parties by its
        allegiance share (the abstention residual simply does not vote)."""
        votes: dict[str, float] = {p.id: 0.0 for p in parties}
        for node in electorate:
            attrs = node.attributes
            allegiance = dict(attrs.get("allegiance") or {})
            loyal_mass = sum(float(v) for v in allegiance.values())
            if loyal_mass <= 0.0:
                continue
            population = float(attrs.get("population", 1) or 1)
            cast = population * turnouts.get(node.id, 0.0)
            for party_id, mass in allegiance.items():
                if party_id in votes:
                    votes[party_id] += cast * (float(mass) / loyal_mass)
        return votes

    def _resolve_winner(
        self,
        ranked: list[tuple[str, float]],
        shares: list[float],
        services: ServicesProtocol,
        tick: int,
        defines: Any,
    ) -> str:
        if not ranked:
            return ""
        if len(ranked) >= 2 and shares and (shares[0] - shares[1]) < float(defines.recount_margin):
            # Recount-grade tie: one seeded coin (III.7, the congress
            # precedent) between the top two, lexicographically ordered.
            rng: random.Random = resolve_rng(services, tick)
            return ranked[0][0] if rng.random() < 0.5 else ranked[1][0]
        return ranked[0][0]

    # ------------------------------------------------------------------
    # L-SUSPEND
    # ------------------------------------------------------------------

    def _bonapartist_suspension(
        self, graph: GraphProtocol, legitimation: float, defines: Any, apparatus: Any
    ) -> bool:
        """L-SUSPEND: legitimation below the floor AND ANY institution in
        bonapartist mode ⟹ the clock is suspended."""
        if legitimation >= float(defines.legitimacy_backfire_threshold):
            return False
        dominance = float(apparatus.bonapartist_threshold)
        exclusion = float(apparatus.bonapartist_exclusion_threshold)
        return any(
            self._is_bonapartist(node.attributes.get("internal_balance"), dominance, exclusion)
            for node in graph.query_nodes(node_type=NodeType.INSTITUTION)
        )

    @staticmethod
    def _is_bonapartist(balance: object, dominance: float, exclusion: float) -> bool:
        if not isinstance(balance, dict):
            return False
        bona = float(balance.get("institutionalist_bonapartist", 0.0) or 0.0)
        liberal = float(balance.get("liberal_technocratic", 0.0) or 0.0)
        revanchist = float(balance.get("revanchist_fascist", 0.0) or 0.0)
        return bona > dominance and liberal < exclusion and revanchist < exclusion

    def _suspend(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        tick: int,
        sovereign_id: str,
        electorate: list[GraphNode],
        legitimation: float,
    ) -> None:
        self._emit(
            services,
            tick,
            EventType.ELECTIONS_SUSPENDED,
            {"sovereign_id": sovereign_id, "legitimation_index": legitimation},
        )
        # Suspension is a rupture: every loyal class enters a disillusion
        # window (there was something to vote for, and the ritual was taken).
        loyal = [
            c
            for c in electorate
            if sum(float(v) for v in (c.attributes.get("allegiance") or {}).values()) > 0.0
        ]
        self._open_windows(graph, services, tick, loyal, services.defines.politics)

    # ------------------------------------------------------------------
    # Government formation
    # ------------------------------------------------------------------

    def _form_government(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        tick: int,
        sovereign_id: str,
        parties: list[GraphNode],
        winner: str,
        shares: list[float],
    ) -> None:
        governments = dict(graph.get_graph_attr(ELECTORAL_GOVERNMENTS_ATTR, None) or {})
        governments[sovereign_id] = {
            "party_id": winner,
            "formed_tick": tick,
            "share": shares[0] if shares else 0.0,
        }
        graph.set_graph_attr(ELECTORAL_GOVERNMENTS_ATTR, governments)

        winning_party = next((p for p in parties if p.id == winner), None)
        ideology = str(winning_party.attributes.get("ideology", "")) if winning_party else ""
        target = _FACTION_BY_IDEOLOGY.get(ideology)
        shift = (
            self._perturb_faction_balance(graph, services, target) if target is not None else 0.0
        )
        self._emit(
            services,
            tick,
            EventType.GOVERNMENT_FORMED,
            {
                "sovereign_id": sovereign_id,
                "governing_coalition": winner,
                "faction_balance_shift": shift,
            },
        )

    def _perturb_faction_balance(
        self, graph: GraphProtocol, services: ServicesProtocol, target: StateFaction
    ) -> float:
        """Nudge every StateApparatus org's faction_balance toward the
        winner's aligned faction, bounded by max_faction_shift_per_tick."""
        from babylon.ooda.state_ai.faction_dynamics import renormalize_faction_balance

        max_shift = float(services.defines.state_ai.max_faction_shift_per_tick)
        total_shift = 0.0
        for node in sorted(graph.query_nodes(node_type=NodeType.ORGANIZATION), key=lambda n: n.id):
            raw = node.attributes.get("faction_balance")
            if not isinstance(raw, dict):
                continue
            previous = FactionBalance(**raw)
            proposed = self._toward(previous, target)
            updated = renormalize_faction_balance(proposed, max_shift, previous)
            graph.update_node(node.id, faction_balance=updated.model_dump())
            total_shift += abs(getattr(updated, target.value) - getattr(previous, target.value))
        return total_shift

    @staticmethod
    def _toward(previous: FactionBalance, target: StateFaction) -> FactionBalance:
        """A proposed balance with all mass on the target faction; the
        renormalizer clamps the per-tick delta to max_faction_shift."""
        weights = {
            StateFaction.FINANCE_CAPITAL: 0.0,
            StateFaction.SECURITY_STATE: 0.0,
            StateFaction.SETTLER_POPULIST: 0.0,
        }
        weights[target] = 1.0
        return FactionBalance(
            finance_capital=weights[StateFaction.FINANCE_CAPITAL],
            security_state=weights[StateFaction.SECURITY_STATE],
            settler_populist=weights[StateFaction.SETTLER_POPULIST],
            stability=previous.stability,
            legitimacy=previous.legitimacy,
        )

    # ------------------------------------------------------------------
    # Legitimation + institutions
    # ------------------------------------------------------------------

    def _mean_legitimation(self, graph: GraphProtocol, claimed: list[str]) -> float:
        values: list[float] = []
        for territory_id in claimed:
            node = graph.get_node(territory_id)
            if node is None:
                continue
            values.append(float(node.attributes.get("legitimation_index", 0.5) or 0.5))
        return sum(values) / len(values) if values else 0.5

    def _refresh_legitimation(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        tick: int,
        claimed: list[str],
        refresh: float,
        defines: Any,
    ) -> None:
        weight = float(defines.legitimation_refresh_weight)
        for territory_id in claimed:
            node = graph.get_node(territory_id)
            if node is None:
                continue
            index = float(node.attributes.get("legitimation_index", 0.5) or 0.5)
            new_index = min(1.0, max(0.0, index + weight * (refresh - index)))
            graph.update_node(territory_id, legitimation_index=new_index)
            self._emit(
                services,
                tick,
                EventType.LEGITIMATION_REFRESH,
                {
                    "territory_id": territory_id,
                    "refresh": refresh,
                    "legitimation_index": new_index,
                },
            )

    def _shift_institutions(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        tick: int,
        claimed: list[str],
        legitimacy: float,
    ) -> None:
        crisis = self._crisis_intensity(graph, claimed)
        for node in sorted(graph.query_nodes(node_type=NodeType.INSTITUTION), key=lambda n: n.id):
            raw = node.attributes.get("internal_balance")
            if not isinstance(raw, dict):
                continue
            from babylon.models.entities.institution import InternalBalanceOfForces

            balance = InternalBalanceOfForces(
                **{k: v for k, v in raw.items() if k != "hegemonic_fraction"}
            )
            new_balance, events = update_internal_balance(
                balance,
                crisis_intensity=crisis,
                legitimacy=legitimacy,
                external_threat=0.0,
                institution_id=node.id,
            )
            graph.update_node(node.id, internal_balance=new_balance.model_dump())
            self._publish_institution_events(services, tick, events)

    def _crisis_intensity(self, graph: GraphProtocol, claimed: list[str]) -> float:
        if not claimed:
            return 0.0
        in_crisis = 0
        for territory_id in claimed:
            node = graph.get_node(territory_id)
            if node is None:
                continue
            phase = str(node.attributes.get("tick_crisis_phase", "normal"))
            if phase in _CRISIS_PHASES:
                in_crisis += 1
        return in_crisis / len(claimed)

    def _publish_institution_events(
        self, services: ServicesProtocol, tick: int, events: list[Any]
    ) -> None:
        for event in events:
            if type(event).__name__ == "BonapartistModeEvent":
                self._emit(
                    services,
                    tick,
                    EventType.INSTITUTION_BONAPARTIST_MODE,
                    {
                        "institution_id": getattr(event, "institution_id", ""),
                        "bonapartist_weight": getattr(event, "bonapartist_weight", 0.0),
                    },
                )
            else:
                self._emit(
                    services,
                    tick,
                    EventType.INSTITUTION_FACTION_SHIFT,
                    {
                        "institution_id": getattr(event, "institution_id", ""),
                        "old_fraction": str(getattr(event, "old_fraction", "")),
                        "new_fraction": str(getattr(event, "new_fraction", "")),
                    },
                )

    # ------------------------------------------------------------------
    # H-collapse / disillusion windows
    # ------------------------------------------------------------------

    def _open_loss_windows(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        tick: int,
        electorate: list[GraphNode],
        parties: list[GraphNode],
        winner: str,
        defines: Any,
    ) -> None:
        party_ids = {p.id for p in parties}
        losers = [c for c in electorate if self._plurality(c, party_ids) not in ("", winner)]
        self._open_windows(graph, services, tick, losers, defines)

    @staticmethod
    def _plurality(node: GraphNode, party_ids: set[str]) -> str:
        allegiance = {
            k: float(v)
            for k, v in dict(node.attributes.get("allegiance") or {}).items()
            if k in party_ids
        }
        if not allegiance:
            return ""
        return str(max(sorted(allegiance), key=lambda k: allegiance[k]))

    def _open_windows(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        tick: int,
        classes: list[GraphNode],
        defines: Any,
    ) -> None:
        if not classes:
            return
        windows = dict(graph.get_graph_attr(ELECTORAL_DISILLUSION_ATTR, None) or {})
        window_ticks = int(defines.disillusion_window_ticks)
        for node in classes:
            bridges = self._has_bridges(graph, node.id)
            windows[node.id] = {
                "opened_tick": tick,
                "window_ticks": window_ticks,
                "bridges_present": bridges,
            }
            self._emit(
                services,
                tick,
                EventType.DISILLUSION_WINDOW_OPEN,
                {
                    "class_id": node.id,
                    "window_ticks": window_ticks,
                    "bridges_present": bridges,
                },
            )
        graph.set_graph_attr(ELECTORAL_DISILLUSION_ATTR, windows)

    @staticmethod
    def _has_bridges(graph: GraphProtocol, class_id: str) -> bool:
        """A SOLIDARITY edge incident to the class = a bridge out of atomized
        despair (T-7: bridges route the disillusioned toward organization)."""
        for edge in graph.query_edges(edge_type=EdgeType.SOLIDARITY):
            if edge.source_id == class_id or edge.target_id == class_id:
                strength = edge.attributes.get("solidarity_strength", 0.0)
                if isinstance(strength, (int, float)) and strength > 0.0:
                    return True
        return False

    def _prune_windows(self, graph: GraphProtocol, tick: int) -> None:
        windows = graph.get_graph_attr(ELECTORAL_DISILLUSION_ATTR, None)
        if not windows:
            return
        live = {
            class_id: row
            for class_id, row in dict(windows).items()
            if int(row.get("opened_tick", 0)) + int(row.get("window_ticks", 0)) > tick
        }
        graph.set_graph_attr(ELECTORAL_DISILLUSION_ATTR, live)

    # ------------------------------------------------------------------

    @staticmethod
    def _emit(
        services: ServicesProtocol,
        tick: int,
        event_type: EventType,
        payload: dict[str, Any],
    ) -> None:
        services.event_bus.publish(Event(type=event_type, tick=tick, payload=payload))


__all__ = [
    "ELECTORAL_DISILLUSION_ATTR",
    "ELECTORAL_GOVERNMENTS_ATTR",
    "ElectoralSystem",
]
