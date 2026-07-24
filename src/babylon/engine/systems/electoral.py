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
from babylon.domain.politics.conjuncture import (
    PopularFrontArm,
    consolidation_pressure,
    resolve_popular_front_arm,
)
from babylon.formulas.politics import competitiveness, turnout_share
from babylon.kernel.event_bus import Event
from babylon.kernel.system_base import SystemBase, resolve_rng
from babylon.kernel.tick_partition import TickPartition
from babylon.models.entities.state_apparatus_ai import FactionBalance
from babylon.models.enums import (
    ColonialStance,
    EdgeMode,
    EdgeType,
    EventType,
    ExtractionPolicy,
    NodeType,
    OrgType,
    StateFaction,
)

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

#: Popular-front conjuncture register (§3.4, U12): ``{"active", "since_tick",
#: "arms": {party_id: "commit"|"autonomy"}, "suppression": float}``. Written
#: here every tick the conjuncture holds; ConsciousnessSystem @17.0 reads the
#: ``suppression`` one tick stale (the fascist-channel throttle) and
#: AllegianceSystem @17.42 reads the ``arms`` one tick stale (valve exposure
#: + legitimation entanglement). Owner: this file (sentinels/superstructure).
POPULAR_FRONT_ATTR: Final[str] = "popular_front"

#: Derecognition register (§3.2 stance 3, U12): the sorted tuple of org ids
#: the host machines have expelled. Absorbing — expulsion is terminal
#: ("derecognition is the terminal case of host discipline", ADR137). The
#: register is stamped ONLY on the first crossing (absence, never a neutral
#: empty tuple — TRAP 3); spoiler arithmetic reads members as independents.
ELECTORAL_DERECOGNIZED_ATTR: Final[str] = "electoral_derecognized"

#: The doctrine stance that operates INSIDE a host duopoly machine (§3.2
#: stance 3): its influence is measured against the pole-matched host.
_ENTRYISM_STANCE: Final[str] = "entryism"

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

#: Spoiler-arithmetic ideology poles (§3.2 stance 4, ADR137 deferral landed
#: U12): an independent ballot line's votes come out of the LESSER-EVIL
#: coalition — the ideologically-nearest duopoly machine's share. The pole
#: map is the delegated-judgment half of the rule (ADR139): the left pole
#: pairs the social-democratic current with the liberal machine it
#: structurally spoils; the right pole pairs the fascist current with the
#: restorationist machine. An ideology outside the map spoils the
#: highest-vote non-independent party regardless of pole.
_SPOILER_POLES: Final[dict[str, str]] = {
    "liberal_imperial": "left",
    "social_democratic": "left",
    "restorationist": "right",
    "fascist": "right",
}

#: The doctrine stance that runs its own line (its votes subtract from the
#: nearest machine instead of folding into it).
_INDEPENDENT_LINE_STANCE: Final[str] = "independent_ballot_line"


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

        # P25 U12 (ADR139): the popular-front conjuncture is evaluated EVERY
        # tick (it is conjunctural weather, not clock-bound) before any
        # sovereign's election runs — a suspended clock does not postpone
        # the forced choice.
        self._popular_front_conjuncture(wrapped, services, context.tick, parties, classes)

        # P25 U12 (ADR139): derecognition counter-play is likewise EVERY-tick
        # terrain — the host watches its flank between elections, and the
        # purge must not wait for a clocked count.
        self._evaluate_derecognition(wrapped, services, context.tick, parties, classes)

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
    # The popular-front conjuncture (§3.4, U12)
    # ------------------------------------------------------------------

    def _popular_front_conjuncture(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        tick: int,
        parties: list[GraphNode],
        classes: list[GraphNode],
    ) -> None:
        """Evaluate the conjuncture and, while it holds, enforce its price.

        The trigger is the SINGLE consolidation-pressure measure
        (:func:`~babylon.domain.politics.conjuncture.consolidation_pressure`
        — the same math EndgameDetector's fascist_consolidation axis
        delegates to) crossing ``popular_front_trigger``. The crossing fires
        ``POPULAR_FRONT_CALLED`` once and resolves the forced choice for
        EVERY party org by stance (:func:`resolve_popular_front_arm`);
        autonomy is the absence of a write, while each committed org accrues
        CO_OPTIVE dependence toward the defended apex sovereign per active
        tick (``popular_front_cooptation_rate``) and the register's
        ``suppression`` (the committed share of the loyal mass) feeds the
        fascist-channel throttle ConsciousnessSystem reads next tick. When
        the pressure recedes the conjuncture closes; a second crossing is a
        new conjuncture and fires again.
        """
        defines = services.defines.politics
        pressure = self._consolidation_pressure(graph, services)
        register = dict(graph.get_graph_attr(POPULAR_FRONT_ATTR, None) or {})
        active = bool(register.get("active", False))

        if pressure < float(defines.popular_front_trigger):
            if active:
                register["active"] = False
                graph.set_graph_attr(POPULAR_FRONT_ATTR, register)
            return

        if not active:
            arms = {
                party.id: resolve_popular_front_arm(
                    tuple(party.attributes.get("acquired_doctrine_ids") or ())
                ).value
                for party in parties
            }
            register = {
                "active": True,
                "since_tick": tick,
                "arms": arms,
                "suppression": 0.0,
            }
            self._emit(
                services,
                tick,
                EventType.POPULAR_FRONT_CALLED,
                {
                    "axis_progress": pressure,
                    "trigger": float(defines.popular_front_trigger),
                },
            )

        committed = sorted(
            party_id
            for party_id, arm in dict(register["arms"]).items()
            if arm == PopularFrontArm.COMMIT.value
        )
        register["suppression"] = self._front_suppression(classes, committed)
        self._accrue_commit_coupling(graph, committed, float(defines.popular_front_cooptation_rate))
        graph.set_graph_attr(POPULAR_FRONT_ATTR, register)

    def _consolidation_pressure(self, graph: GraphProtocol, services: ServicesProtocol) -> float:
        """The single consolidation-pressure measure, read off the tick graph.

        The electoral adapter of :func:`consolidation_pressure`: ideology
        pairs from every social_class node (a node with no ideology dict is
        neither bearing nor fascist), the stance/extraction majorities from
        CLAIMS edges exactly as the detector reads them, and the
        honest-absent violence attrs (0.0 / 1.0 — no production writer
        exists tree-wide, so this route's third gate never fires today).
        """
        ideologies: list[tuple[float, float] | None] = []
        for node in sorted(graph.query_nodes(node_type=NodeType.SOCIAL_CLASS), key=lambda n: n.id):
            raw = node.attributes.get("ideology")
            if not isinstance(raw, dict):
                ideologies.append(None)
                continue
            ideologies.append(
                (
                    float(raw.get("national_identity", 0.0) or 0.0),
                    float(raw.get("class_consciousness", 0.0) or 0.0),
                )
            )
        return consolidation_pressure(
            tuple(ideologies),
            uphold_stance_majority=self._stance_claims_majority(graph, ColonialStance.UPHOLD),
            intensify_extraction_majority=self._extraction_claims_majority(
                graph, ExtractionPolicy.INTENSIFY
            ),
            state_violence_index=self._graph_float(graph, "state_violence_index", 0.0),
            state_violence_index_max=self._graph_float(graph, "state_violence_index_max", 1.0),
            fascist_majority_fraction=float(services.defines.endgame.fascist_majority_fraction),
        )

    @staticmethod
    def _graph_float(graph: GraphProtocol, key: str, default: float) -> float:
        value = graph.get_graph_attr(key, None)
        return float(value) if isinstance(value, (int, float)) else default

    @staticmethod
    def _claims_sovereign_stances(graph: GraphProtocol) -> dict[str, str]:
        """sovereign_id -> its ruling faction's colonial_stance (recognized only)."""
        stances: dict[str, str] = {}
        for node in graph.query_nodes(node_type=NodeType.SOVEREIGN):
            faction_id = node.attributes.get("ruling_faction_id")
            if not isinstance(faction_id, str):
                continue
            faction = graph.get_node(faction_id)
            if faction is None:
                continue
            stance = faction.attributes.get("colonial_stance")
            if isinstance(stance, str) and stance:
                stances[node.id] = stance
        return stances

    def _stance_claims_majority(self, graph: GraphProtocol, stance: ColonialStance) -> bool:
        """Whether ≥ half of CLAIMS edges originate from ``stance``-aligned sovereigns."""
        claims = list(graph.query_edges(edge_type=EdgeType.CLAIMS))
        if not claims:
            return False
        stances = self._claims_sovereign_stances(graph)
        target = sum(1 for edge in claims if stances.get(edge.source_id) == stance.value)
        return target / len(claims) >= 0.5

    @staticmethod
    def _extraction_claims_majority(graph: GraphProtocol, policy: ExtractionPolicy) -> bool:
        """Whether ≥ half of CLAIMS edges originate from ``policy`` sovereigns."""
        claims = list(graph.query_edges(edge_type=EdgeType.CLAIMS))
        if not claims:
            return False
        target = 0
        for edge in claims:
            sovereign = graph.get_node(edge.source_id)
            if sovereign is None:
                continue
            raw = sovereign.attributes.get("extraction_policy", "")
            if isinstance(raw, ExtractionPolicy):
                current = raw
            else:
                try:
                    current = ExtractionPolicy(str(raw))
                except ValueError:
                    continue
            if current is policy:
                target += 1
        return target / len(claims) >= 0.5

    @staticmethod
    def _front_suppression(classes: list[GraphNode], committed: list[str]) -> float:
        """The committed parties' share of the total loyal allegiance mass.

        The suppression IS the committed mass (org labor and credibility made
        material — no tuning coefficient): what the front's defense can
        throttle is proportional to what it actually holds. Zero loyal mass
        ⟹ 0.0 (a front nobody joined suppresses nothing).
        """
        committed_set = set(committed)
        loyal = 0.0
        held = 0.0
        for node in sorted(classes, key=lambda n: n.id):
            allegiance = dict(node.attributes.get("allegiance") or {})
            for party_id, mass in allegiance.items():
                value = float(mass)
                loyal += value
                if party_id in committed_set:
                    held += value
        if loyal <= 0.0:
            return 0.0
        return max(0.0, min(1.0, held / loyal))

    def _accrue_commit_coupling(
        self, graph: GraphProtocol, committed: list[str], rate: float
    ) -> None:
        """Accrue each committed org's CO_OPTIVE debt to the defended apex.

        The front's price is measured in the same dependence vocabulary as
        entryism's (U11): a TRANSACTIONAL edge org→apex carrying
        ``edge_mode=co_optive`` and a saturating ``co_optive_dependence``,
        which is precisely what ``_practice_env`` counts into CO_OPTIVE_SHARE
        — defending the state walks the org toward liquidationism with no
        punitive delta anywhere. The defended apex is the claims-dominant
        sovereign without an ADMINISTERS parent (the effective national
        state), tie-broken lexicographically; no apex ⟹ no edge (honest
        absence).
        """
        if not committed:
            return
        apex = self._defended_apex(graph)
        if apex is None:
            return
        for org_id in committed:
            existing = graph.get_edge(org_id, apex, EdgeType.TRANSACTIONAL)
            if existing is None:
                graph.add_edge(
                    org_id,
                    apex,
                    EdgeType.TRANSACTIONAL,
                    edge_mode=EdgeMode.CO_OPTIVE.value,
                    co_optive_dependence=rate,
                )
                continue
            dependence = min(
                1.0, float(existing.attributes.get("co_optive_dependence", 0.0)) + rate
            )
            graph.update_edge(
                org_id,
                apex,
                EdgeType.TRANSACTIONAL,
                edge_mode=EdgeMode.CO_OPTIVE.value,
                co_optive_dependence=dependence,
            )

    def _defended_apex(self, graph: GraphProtocol) -> str | None:
        """The claims-dominant apex sovereign (no ADMINISTERS parent)."""
        apexes = [
            node.id
            for node in graph.query_nodes(node_type=NodeType.SOVEREIGN)
            if self._administers_parent(graph, node.id) is None
        ]
        if not apexes:
            return None
        claim_counts: dict[str, int] = dict.fromkeys(apexes, 0)
        for edge in graph.query_edges(edge_type=EdgeType.CLAIMS):
            if edge.source_id in claim_counts:
                claim_counts[edge.source_id] += 1
        return max(sorted(apexes), key=lambda sid: claim_counts[sid])

    # ------------------------------------------------------------------
    # Derecognition counter-play (§3.2 stance 3, U12 — terrain half)
    # ------------------------------------------------------------------

    def _evaluate_derecognition(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        tick: int,
        parties: list[GraphNode],
        classes: list[GraphNode],
    ) -> None:
        """Expel entryist blocs past the host's threat threshold (terrain).

        For every org holding the ``entryism`` stance and not already
        expelled, intra-host influence = its allegiance mass over the sum of
        its own and its host's mass, the host being the highest-mass
        NON-entryist party on the same ideology pole (``_SPOILER_POLES``;
        an ideology outside the map faces the highest-mass non-entryist
        party regardless of pole). Mass is the raw per-class ``allegiance``
        sum at national grain, mirroring the count's proportionality.

        A crossing is ABSORBING: the org enters the
        :data:`ELECTORAL_DERECOGNIZED_ATTR` register (sorted tuple, stamped
        only on the first crossing — absence, never a neutral empty tuple,
        TRAP 3) and ``HOST_DERECOGNIZED`` fires once per org. Expulsion is
        terminal; there is no re-recognition path.

        The host's ACTIVE punishment verbs (the OODA counter-play family —
        superdelegates as INCORPORATE, primary purges as DIVIDE) are a cited
        blocking dependency: the ``ooda/`` surface belongs to the
        interface/adversary train (ADR139). What lands here is the
        deterministic terrain half §3.2 prices.
        """
        register = tuple(graph.get_graph_attr(ELECTORAL_DERECOGNIZED_ATTR, ()) or ())
        expelled = set(register)
        entryists = [
            party
            for party in parties
            if _ENTRYISM_STANCE in tuple(party.attributes.get("acquired_doctrine_ids") or ())
            and party.id not in expelled
        ]
        if not entryists:
            return
        hosts = [
            party
            for party in parties
            if _ENTRYISM_STANCE not in tuple(party.attributes.get("acquired_doctrine_ids") or ())
        ]
        if not hosts:
            return
        masses = self._allegiance_masses(parties, classes)
        threshold = float(services.defines.politics.host_threat_threshold)
        newly: list[str] = []
        for entryist in entryists:
            pole = _SPOILER_POLES.get(str(entryist.attributes.get("ideology", "")))
            candidates = hosts
            if pole is not None:
                same_pole = [
                    party
                    for party in hosts
                    if _SPOILER_POLES.get(str(party.attributes.get("ideology", ""))) == pole
                ]
                if same_pole:
                    candidates = same_pole
            host = max(candidates, key=lambda p: (masses.get(p.id, 0.0), p.id))
            own = masses.get(entryist.id, 0.0)
            denom = own + masses.get(host.id, 0.0)
            if denom <= 0.0:
                continue
            influence = own / denom
            if influence <= threshold:
                continue
            newly.append(entryist.id)
            self._emit(
                services,
                tick,
                EventType.HOST_DERECOGNIZED,
                {
                    "org_id": entryist.id,
                    "host_id": host.id,
                    "influence": influence,
                    "threshold": threshold,
                },
            )
        if newly:
            graph.set_graph_attr(ELECTORAL_DERECOGNIZED_ATTR, tuple(sorted([*register, *newly])))

    @staticmethod
    def _allegiance_masses(parties: list[GraphNode], classes: list[GraphNode]) -> dict[str, float]:
        """party_id -> Σ per-class ``allegiance`` mass (national grain)."""
        masses: dict[str, float] = {party.id: 0.0 for party in parties}
        for node in classes:
            allegiance = dict(node.attributes.get("allegiance") or {})
            for party_id, mass in allegiance.items():
                if party_id in masses:
                    masses[party_id] += float(mass)
        return masses

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
        spoiler = self._apply_spoiler_arithmetic(
            parties,
            votes,
            frozenset(graph.get_graph_attr(ELECTORAL_DERECOGNIZED_ATTR, ()) or ()),
        )
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
                "spoiler_target": spoiler.get("target", ""),
                "spoiler_shift": spoiler.get("shift", 0.0),
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

    def _apply_spoiler_arithmetic(
        self,
        parties: list[GraphNode],
        votes: dict[str, float],
        derecognized: frozenset[str] = frozenset(),
    ) -> dict[str, object]:
        """Price an independent ballot line into the count (§3.2 stance 4;
        ADR137 deferral landed U12).

        Every vote an independent line casts is a vote its pole's duopoly
        machine does not receive: the independent's tally subtracts from the
        ideologically-nearest machine BEFORE winner resolution, so the
        lesser-evil arithmetic can seat the greater evil — "heightening the
        contradictions" as a mechanical loop the player owns. The
        independent keeps its own share (its votes are real; they simply
        come out of the machine's pile).

        The independent set is the union of orgs holding the
        ``independent_ballot_line`` stance and orgs in the
        :data:`ELECTORAL_DERECOGNIZED_ATTR` register — an expelled entryist
        faces the machine as an outsider and pays the same tax (§3.2 stance
        3's terminal case).

        Target selection (deterministic): the independent's ``ideology``
        maps to a pole via ``_SPOILER_POLES``; the target is the
        highest-vote party on the same pole (ties break to the highest id).
        An ideology outside the map spoils the highest-vote non-independent
        party regardless of pole. The subtraction floors at zero — a
        spoiler larger than its target's pile removes only what exists.

        When several independents run, each applies in id order against the
        already-mutated tally; the returned payload names the LAST
        application (the one whose price is printed on the election event).

        Args:
            parties: The sovereign's contesting party orgs (id-sorted, as
                :meth:`_political_factions` returns them).
            votes: The FPTP tally, MUTATED in place (target loses
                ``min(spoiler, target)``).
            derecognized: The derecognition register's membership.

        Returns:
            ``{"target": <party id or "">, "shift": <votes removed>}`` —
            the empty/zero pair when no independent line contests.
        """
        empty: dict[str, object] = {"target": "", "shift": 0.0}
        independents = [
            party
            for party in parties
            if _INDEPENDENT_LINE_STANCE
            in tuple(party.attributes.get("acquired_doctrine_ids") or ())
            or party.id in derecognized
        ]
        if not independents:
            return empty
        applied = empty
        for independent in independents:
            spoiler_votes = float(votes.get(independent.id, 0.0))
            if spoiler_votes <= 0.0:
                continue
            pole = _SPOILER_POLES.get(str(independent.attributes.get("ideology", "")))
            candidates = [
                party
                for party in parties
                if party.id != independent.id and float(votes.get(party.id, 0.0)) > 0.0
            ]
            if pole is not None:
                same_pole = [
                    party
                    for party in candidates
                    if _SPOILER_POLES.get(str(party.attributes.get("ideology", ""))) == pole
                ]
                if same_pole:
                    candidates = same_pole
            if not candidates:
                continue
            target = max(
                candidates,
                key=lambda party: (float(votes.get(party.id, 0.0)), party.id),
            )
            shift = min(spoiler_votes, float(votes.get(target.id, 0.0)))
            votes[target.id] = float(votes.get(target.id, 0.0)) - shift
            applied = {"target": target.id, "shift": shift}
        return applied

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
    "POPULAR_FRONT_ATTR",
    "ElectoralSystem",
]
