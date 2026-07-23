"""Behavioral contract for ElectoralSystem @17.45 (P25 U10, ADR136).

THE clocked ambient machine: the per-sovereign election clock, the turnout
law over the allegiance masses, FPTP with ξ_t only at recount grain,
government formation (the governments register + FactionBalance perturbation),
legitimation refresh, L-SUSPEND (bonapartist + floor ⟹ suspension), and the
T-7 disillusion routing. Byte-safety is the parties-exist guard (§U10(d)): a
graph with no PoliticalFaction orgs never fires a clock — the qa:regression
six are byte-identical because nothing ever runs.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.scenarios.electoral_fixture import create_electoral_fixture_scenario
from babylon.engine.systems.allegiance import AllegianceSystem
from babylon.engine.systems.electoral import (
    ELECTORAL_DISILLUSION_ATTR,
    ELECTORAL_GOVERNMENTS_ATTR,
    POPULAR_FRONT_ATTR,
    ElectoralSystem,
)
from babylon.kernel.tick_partition import TickPartition
from babylon.models.enums import EdgeType, EventType

pytestmark = pytest.mark.unit

_FEDERAL_TICK = 104  # politics.cycle_ticks["federal"], the apex clock interval


class _RecordingBus:
    def __init__(self) -> None:
        self.events: list = []

    def publish(self, event, context=None) -> None:  # noqa: ANN001
        self.events.append(event)


class _Services:
    def __init__(self, defines: GameDefines, bus: _RecordingBus) -> None:
        self.defines = defines
        self.event_bus = bus


class _Context:
    def __init__(self, tick: int) -> None:
        self.tick = tick
        self.persistent_data: dict = {}


def _electoral_graph():
    state, _config, defines = create_electoral_fixture_scenario()
    return state.to_graph(), defines


def _stamp_allegiance(graph, class_id: str, masses: dict[str, float], hope: float = 0.6) -> None:
    graph.update_node(class_id, allegiance=dict(masses), hope=hope)


def _stamp_voter(
    graph,
    class_id: str,
    masses: dict[str, float],
    *,
    hope: float = 0.8,
    population: int = 1,
) -> None:
    """A voter with deterministic turnout inputs (no suppression noise)."""
    graph.update_node(
        class_id,
        allegiance=dict(masses),
        hope=hope,
        population=population,
        repression_faced=0.0,
    )


def _run_allegiance(graph, defines) -> None:
    """Populate real allegiance + hope via the U8 producer (parties-gated)."""
    AllegianceSystem().step(graph, _Services(defines, _RecordingBus()), _Context(1))


def _step(graph, defines, tick: int) -> _RecordingBus:
    bus = _RecordingBus()
    ElectoralSystem().step(graph, _Services(defines, bus), _Context(tick))
    return bus


def _events_of(bus, event_type: EventType) -> list:
    return [e for e in bus.events if e.type == event_type]


class TestSystemIdentity:
    def test_position_and_partition(self) -> None:
        assert ElectoralSystem.position == 17.45
        assert ElectoralSystem.partition is TickPartition.CONSEQUENCE
        assert ElectoralSystem.creates_value is False


class TestPartiesGuard:
    """§U10(d): no parties ⟹ no clock, no ξ_t, byte-unchanged."""

    def test_party_less_graph_is_untouched(self) -> None:
        from babylon.engine.scenarios._legacy import create_two_node_scenario

        state, _config, defines = create_two_node_scenario()
        graph = state.to_graph()
        before = {n.id: dict(n.attributes) for n in graph.query_nodes()}
        bus = _step(graph, defines, _FEDERAL_TICK)
        after = {n.id: dict(n.attributes) for n in graph.query_nodes()}
        assert after == before
        assert bus.events == []
        assert graph.get_graph_attr(ELECTORAL_GOVERNMENTS_ATTR, None) is None

    def test_off_cycle_tick_holds_no_election(self) -> None:
        graph, defines = _electoral_graph()
        _run_allegiance(graph, defines)
        bus = _step(graph, defines, _FEDERAL_TICK + 1)  # not a clock multiple
        assert _events_of(bus, EventType.ELECTION_HELD) == []


class TestTheClock:
    def test_election_fires_on_the_federal_clock(self) -> None:
        graph, defines = _electoral_graph()
        _run_allegiance(graph, defines)
        bus = _step(graph, defines, _FEDERAL_TICK)
        held = _events_of(bus, EventType.ELECTION_HELD)
        assert len(held) == 1
        assert held[0].payload["sovereign_id"] == "SOV_USA_FED"
        assert held[0].payload["jurisdiction_level"] == "federal"
        assert 0.0 <= held[0].payload["turnout"] <= 1.0
        assert 0.0 <= held[0].payload["competitiveness"] <= 1.0
        assert held[0].payload["winning_coalition"].startswith("org/party-")


class TestTurnoutAndWinner:
    def test_winner_is_the_plurality_party(self) -> None:
        graph, defines = _electoral_graph()
        # The whole electorate (apex = both classes) breaks for socdem, with a
        # liberal minority — socdem wins the national tally unambiguously.
        _stamp_voter(graph, "C001", {"org/party-socdem": 0.9})
        _stamp_voter(graph, "C002", {"org/party-socdem": 0.6, "org/party-liberal": 0.3})
        bus = _step(graph, defines, _FEDERAL_TICK)
        held = _events_of(bus, EventType.ELECTION_HELD)
        assert held[0].payload["winning_coalition"] == "org/party-socdem"

    def test_no_hope_no_turnout_no_winner_votes(self) -> None:
        """Collapsed hope collapses turnout — no votes are cast at all."""
        graph, defines = _electoral_graph()
        _stamp_allegiance(graph, "C001", {"org/party-socdem": 0.9}, hope=0.0)
        _stamp_allegiance(graph, "C002", {"org/party-liberal": 0.8}, hope=0.0)
        bus = _step(graph, defines, _FEDERAL_TICK)
        held = _events_of(bus, EventType.ELECTION_HELD)
        assert held[0].payload["turnout"] == pytest.approx(0.0)


class TestGovernmentFormation:
    def test_governments_register_records_the_winner(self) -> None:
        graph, defines = _electoral_graph()
        _stamp_allegiance(graph, "C001", {"org/party-socdem": 0.9})
        _step(graph, defines, _FEDERAL_TICK)
        governments = graph.get_graph_attr(ELECTORAL_GOVERNMENTS_ATTR, None)
        assert governments["SOV_USA_FED"]["party_id"] == "org/party-socdem"
        assert governments["SOV_USA_FED"]["formed_tick"] == _FEDERAL_TICK

    def test_faction_balance_perturbs_toward_the_winner(self) -> None:
        """A restorationist win nudges every state apparatus toward the
        settler-populist faction, bounded by max_faction_shift_per_tick."""
        graph, defines = _electoral_graph()
        graph.add_node(
            "org/state",
            _node_type="organization",
            org_type="state_apparatus",
            faction_balance={
                "finance_capital": 0.5,
                "security_state": 0.3,
                "settler_populist": 0.2,
                "stability": 0.5,
                "legitimacy": 0.5,
            },
        )
        _stamp_voter(graph, "C001", {"org/party-restorationist": 0.9})
        _stamp_voter(graph, "C002", {"org/party-restorationist": 0.8})
        bus = _step(graph, defines, _FEDERAL_TICK)
        formed = _events_of(bus, EventType.GOVERNMENT_FORMED)
        assert formed[0].payload["governing_coalition"] == "org/party-restorationist"
        shift = formed[0].payload["faction_balance_shift"]
        max_shift = defines.state_ai.max_faction_shift_per_tick
        # Bounded by max_shift, allowing the renormalizer's small overshoot.
        assert 0.0 < shift <= max_shift * 1.2
        new_balance = graph.get_node("org/state").attributes["faction_balance"]
        assert new_balance["settler_populist"] > 0.2  # rose toward the winner


class TestLegitimationRefresh:
    def test_refresh_moves_the_index_and_publishes(self) -> None:
        graph, defines = _electoral_graph()
        _stamp_allegiance(graph, "C001", {"org/party-socdem": 0.9})
        graph.update_node("T001", legitimation_index=0.2, population=1000)
        bus = _step(graph, defines, _FEDERAL_TICK)
        refreshes = _events_of(bus, EventType.LEGITIMATION_REFRESH)
        assert len(refreshes) == 1
        assert refreshes[0].payload["territory_id"] == "T001"
        new_index = graph.get_node("T001").attributes["legitimation_index"]
        assert new_index != pytest.approx(0.2)  # the ritual moved consent


class TestLSuspend:
    def test_bonapartist_below_floor_suspends_the_clock(self) -> None:
        """L-SUSPEND: a bonapartist institution + legitimation below the
        floor ⟹ ELECTIONS_SUSPENDED, no election counted."""
        graph, defines = _electoral_graph()
        _stamp_allegiance(graph, "C001", {"org/party-socdem": 0.9})
        graph.update_node("T001", legitimation_index=0.1, population=1000)
        graph.update_node(
            "INST_FED_JUDICIARY",
            internal_balance={
                "liberal_technocratic": 0.1,
                "revanchist_fascist": 0.1,
                "institutionalist_bonapartist": 0.8,
                "internal_contestation": 0.2,
            },
        )
        bus = _step(graph, defines, _FEDERAL_TICK)
        assert len(_events_of(bus, EventType.ELECTIONS_SUSPENDED)) == 1
        assert _events_of(bus, EventType.ELECTION_HELD) == []
        # Suspension is a rupture: the loyal worker enters a disillusion window.
        windows = graph.get_graph_attr(ELECTORAL_DISILLUSION_ATTR, None)
        assert "C001" in windows

    def test_high_legitimation_holds_the_election_despite_bonapartism(self) -> None:
        graph, defines = _electoral_graph()
        _stamp_allegiance(graph, "C001", {"org/party-socdem": 0.9})
        graph.update_node("T001", legitimation_index=0.9, population=1000)
        graph.update_node(
            "INST_FED_JUDICIARY",
            internal_balance={
                "liberal_technocratic": 0.1,
                "revanchist_fascist": 0.1,
                "institutionalist_bonapartist": 0.8,
                "internal_contestation": 0.2,
            },
        )
        bus = _step(graph, defines, _FEDERAL_TICK)
        assert len(_events_of(bus, EventType.ELECTION_HELD)) == 1
        assert _events_of(bus, EventType.ELECTIONS_SUSPENDED) == []


class TestDisillusionRouting:
    def test_losers_open_windows_with_bridge_detection(self) -> None:
        graph, defines = _electoral_graph()
        # A big socdem worker bloc beats a small liberal owner bloc; the
        # owner's plurality party (liberal) lost ⟹ its base is disillusioned.
        _stamp_voter(graph, "C001", {"org/party-socdem": 0.9}, population=100)
        _stamp_voter(graph, "C002", {"org/party-liberal": 0.9}, population=1)
        bus = _step(graph, defines, _FEDERAL_TICK)
        assert (
            _events_of(bus, EventType.ELECTION_HELD)[0].payload["winning_coalition"]
            == "org/party-socdem"
        )
        windows = graph.get_graph_attr(ELECTORAL_DISILLUSION_ATTR, None) or {}
        assert "C002" in windows  # the liberal-plurality loser
        assert "C001" not in windows  # the winner's base is not disillusioned
        assert "bridges_present" in windows["C002"]
        assert _events_of(bus, EventType.DISILLUSION_WINDOW_OPEN)

    def test_bridges_route_the_boost_into_organization(self) -> None:
        """T-7: a disillusion window with SOLIDARITY bridges boosts the
        AllegianceSystem conversion into organization (Bernie→DSA)."""
        graph, defines = _electoral_graph()
        graph.set_graph_attr(
            ELECTORAL_DISILLUSION_ATTR,
            {"C001": {"opened_tick": 1, "window_ticks": 26, "bridges_present": True}},
        )
        self._agitate(graph, "C001", 0.5)
        org_before = float(graph.get_node("C001").attributes.get("organization", 0.0))
        AllegianceSystem().step(graph, _Services(defines, _RecordingBus()), _Context(2))
        org_after = float(graph.get_node("C001").attributes["organization"])

        graph2, _ = _electoral_graph()
        self._agitate(graph2, "C001", 0.5)
        base_before = float(graph2.get_node("C001").attributes.get("organization", 0.0))
        AllegianceSystem().step(graph2, _Services(defines, _RecordingBus()), _Context(2))
        base_after = float(graph2.get_node("C001").attributes["organization"])
        assert (org_after - org_before) > (base_after - base_before)

    def test_no_bridges_route_the_excess_into_fascist_alignment(self) -> None:
        """T-7: a bridgeless window routes the boost into fascist_alignment
        (Obama→Trump) instead of organization."""
        graph, defines = _electoral_graph()
        graph.set_graph_attr(
            ELECTORAL_DISILLUSION_ATTR,
            {"C001": {"opened_tick": 1, "window_ticks": 26, "bridges_present": False}},
        )
        self._agitate(graph, "C001", 0.5)
        fascist_before = float(graph.get_node("C001").attributes.get("fascist_alignment", 0.0))
        AllegianceSystem().step(graph, _Services(defines, _RecordingBus()), _Context(2))
        fascist_after = float(graph.get_node("C001").attributes.get("fascist_alignment", 0.0))
        assert fascist_after > fascist_before

    @staticmethod
    def _agitate(graph, class_id: str, agitation: float) -> None:
        node = graph.get_node(class_id)
        ideology = dict(node.attributes.get("ideology") or {})
        ideology["agitation"] = agitation
        graph.update_node(class_id, ideology=ideology)


class TestPolicyIncumbentSeam:
    def test_governing_party_becomes_the_delivery_incumbent(self) -> None:
        """The governments register (this system) makes PolicySystem stamp
        the governing PARTY as the delivery incumbent — lighting U9's
        θ.betrayal term on a party id (ADR135)."""
        from babylon.domain.politics.policy import PolicyAgendaItem
        from babylon.engine.systems.policy import (
            POLICY_DELIVERY_ATTR,
            PolicySystem,
            enqueue_agenda_item,
        )
        from babylon.models.enums import PolicyAxis

        graph, defines = _electoral_graph()
        graph.set_graph_attr(
            ELECTORAL_GOVERNMENTS_ATTR,
            {"SOV_USA_FED": {"party_id": "org/party-socdem", "formed_tick": 1, "share": 0.6}},
        )
        graph.update_node("T001", tick_taxes_on_surplus=10.0, tick_total_surplus=1000.0)
        enqueue_agenda_item(
            graph,
            PolicyAgendaItem(
                sovereign_id="SOV_USA_FED",
                axis=PolicyAxis.SOCIAL_WAGE,
                magnitude=0.1,
                promised=100.0,
                drafted_tick=1,
            ),
        )
        bus = _RecordingBus()
        PolicySystem().step(graph, _Services(defines, bus), _Context(2))
        ledger = graph.get_graph_attr(POLICY_DELIVERY_ATTR, None) or {}
        assert ledger
        assert all(row["incumbent_id"] == "org/party-socdem" for row in ledger.values())


class TestStruggleBackfireCoupling:
    def test_low_legitimation_amplifies_backfire_only_with_a_government(self) -> None:
        """The legitimation→backfire coupling is gated on a seated government
        (byte-safety) and fires below the floor."""
        from babylon.engine.systems.struggle import StruggleSystem

        defines = GameDefines()
        graph, _ = _electoral_graph()
        graph.update_node("T001", legitimation_index=0.05, population=1000)
        system = StruggleSystem()
        services = _Services(defines, _RecordingBus())
        # No government register ⟹ multiplier is exactly 1.0 (byte-safe).
        assert system._legitimation_backfire_multiplier(graph, services) == pytest.approx(1.0)
        # A seated government below the floor ⟹ amplified (> 1.0).
        graph.set_graph_attr(
            ELECTORAL_GOVERNMENTS_ATTR,
            {"SOV_USA_FED": {"party_id": "org/party-socdem", "formed_tick": 1, "share": 0.6}},
        )
        assert system._legitimation_backfire_multiplier(graph, services) > 1.0


class TestFullEngineTick:
    """The 33-system engine runs a real election on the electoral terrain."""

    def test_engine_tick_on_the_federal_clock(self) -> None:
        from babylon.engine.context import TickContext
        from babylon.engine.services import ServiceContainer
        from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS, SimulationEngine
        from babylon.models.world_state import WorldState

        state, _config, _defines = create_electoral_fixture_scenario()
        graph = state.to_graph()
        services = ServiceContainer.create()

        SimulationEngine(list(_DEFAULT_SYSTEMS)).run_tick(
            graph, services, TickContext(tick=_FEDERAL_TICK)
        )

        governments = graph.get_graph_attr(ELECTORAL_GOVERNMENTS_ATTR, None)
        assert governments and "SOV_USA_FED" in governments
        # The full state survives reconstruction (observer path).
        restored = WorldState.from_graph(graph, tick=_FEDERAL_TICK)
        assert restored.entities["C001"].allegiance


class TestPopularFrontConjuncture:
    """§3.4: the conjuncture machine (P25 U12, ADR139).

    The stock fixture's federal sovereign is RESTORATIONIST/UPHOLD/INTENSIFY
    (the violence route reads 2/3) and the two_node classes lean fascist
    (ni=0.5 > cc=0.1 — the false-consciousness route saturates), so tests
    stamp the material signals they mean to control: class ideologies for
    the false-consciousness route, extraction/stance for the violence route.
    """

    @staticmethod
    def _pacify(graph) -> None:
        """Drive BOTH routes below the 0.6 trigger: classes class-conscious
        (fc fraction 0) and extraction CONTINUE (violence route 1/3)."""
        for class_id in ("C001", "C002"):
            graph.update_node(
                class_id,
                ideology={
                    "class_consciousness": 0.9,
                    "national_identity": 0.1,
                    "agitation": 0.0,
                },
            )
        graph.update_node("SOV_USA_FED", extraction_policy="continue")

    @staticmethod
    def _fascisize(graph) -> None:
        """Saturate the false-consciousness route: every class ni > cc."""
        for class_id in ("C001", "C002"):
            graph.update_node(
                class_id,
                ideology={
                    "class_consciousness": 0.0,
                    "national_identity": 1.0,
                    "agitation": 0.0,
                },
            )

    def test_below_trigger_no_event_no_register(self) -> None:
        graph, defines = _electoral_graph()
        self._pacify(graph)
        bus = _step(graph, defines, 1)
        assert _events_of(bus, EventType.POPULAR_FRONT_CALLED) == []
        assert graph.get_graph_attr(POPULAR_FRONT_ATTR, None) is None

    def test_crossing_fires_once_and_resolves_every_line(self) -> None:
        graph, defines = _electoral_graph()
        self._fascisize(graph)
        graph.update_node("org/party-liberal", acquired_doctrine_ids=("entryism",))
        graph.update_node("org/party-socdem", acquired_doctrine_ids=("independent_ballot_line",))
        bus = _step(graph, defines, 1)
        called = _events_of(bus, EventType.POPULAR_FRONT_CALLED)
        assert len(called) == 1
        assert called[0].payload["axis_progress"] >= defines.politics.popular_front_trigger
        assert called[0].payload["trigger"] == defines.politics.popular_front_trigger
        register = graph.get_graph_attr(POPULAR_FRONT_ATTR, None)
        assert register["active"] is True
        # Every party org faces the forced choice — incl. the stance-less.
        assert set(register["arms"]) == {
            "org/party-liberal",
            "org/party-restorationist",
            "org/party-socdem",
            "org/party-fascist",
        }
        assert register["arms"]["org/party-liberal"] == "commit"
        assert register["arms"]["org/party-socdem"] == "autonomy"
        assert register["arms"]["org/party-restorationist"] == "autonomy"
        # Still above the trigger next tick: no re-fire (the conjuncture is
        # an event, not a condition report).
        bus2 = _step(graph, defines, 2)
        assert _events_of(bus2, EventType.POPULAR_FRONT_CALLED) == []

    def test_deactivation_when_pressure_recedes_then_refire(self) -> None:
        graph, defines = _electoral_graph()
        self._fascisize(graph)
        _step(graph, defines, 1)
        self._pacify(graph)
        _step(graph, defines, 2)
        register = graph.get_graph_attr(POPULAR_FRONT_ATTR, None)
        assert register["active"] is False
        # A second crossing is a new conjuncture: it fires again.
        self._fascisize(graph)
        bus = _step(graph, defines, 3)
        assert len(_events_of(bus, EventType.POPULAR_FRONT_CALLED)) == 1

    def test_commit_writes_co_optive_debt_to_the_defended_state(self) -> None:
        """Commit ⟹ org→apex-sovereign CO_OPTIVE edge accruing dependence at
        popular_front_cooptation_rate per active tick (§3.4: raised co-optive
        coupling). Autonomous orgs accrue nothing."""
        graph, defines = _electoral_graph()
        self._fascisize(graph)
        graph.update_node("org/party-liberal", acquired_doctrine_ids=("entryism",))
        _step(graph, defines, 1)
        edge = graph.get_edge("org/party-liberal", "SOV_USA_FED", EdgeType.TRANSACTIONAL)
        assert edge is not None
        assert edge.attributes["edge_mode"] == "co_optive"
        rate = defines.politics.popular_front_cooptation_rate
        assert edge.attributes["co_optive_dependence"] == pytest.approx(rate)
        # A second active tick accrues again.
        _step(graph, defines, 2)
        edge = graph.get_edge("org/party-liberal", "SOV_USA_FED", EdgeType.TRANSACTIONAL)
        assert edge.attributes["co_optive_dependence"] == pytest.approx(min(1.0, 2 * rate))
        # The autonomous socdem current owes nothing to the state.
        assert graph.get_edge("org/party-socdem", "SOV_USA_FED", EdgeType.TRANSACTIONAL) is None

    def test_suppression_is_the_committed_share_of_loyal_mass(self) -> None:
        graph, defines = _electoral_graph()
        self._fascisize(graph)
        graph.update_node("org/party-liberal", acquired_doctrine_ids=("entryism",))
        _stamp_allegiance(graph, "C001", {"org/party-liberal": 0.6, "org/party-socdem": 0.4})
        _stamp_allegiance(graph, "C002", {"org/party-liberal": 0.2})
        _step(graph, defines, 1)
        register = graph.get_graph_attr(POPULAR_FRONT_ATTR, None)
        assert register["suppression"] == pytest.approx(0.8 / 1.2)


class TestPopularFrontConsumers:
    """The commit arm's downstream exposures (P25 U12 §3.4)."""

    @staticmethod
    def _committed_register(*party_ids: str) -> dict:
        return {
            "active": True,
            "since_tick": 1,
            "arms": dict.fromkeys(party_ids, "commit"),
            "suppression": 0.0,
        }

    def test_valve_exposure_committed_party_has_full_viability(self) -> None:
        """Valve exposure: the org vouched for the state, so its base's hope
        in it is no longer viability-discounted (§3.4) — H rises and the
        valve (1 − v·H) bites harder on its own organizing."""
        graph, defines = _electoral_graph()
        graph.set_graph_attr(POPULAR_FRONT_ATTR, self._committed_register("org/party-socdem"))
        system = AllegianceSystem()
        parties = system._political_factions(graph)
        viability = system._viability(parties, {}, {}, graph)
        assert viability["org/party-socdem"] == pytest.approx(1.0)
        assert viability["org/party-liberal"] < 1.0

    def test_entanglement_committed_org_eats_the_incumbents_gap(self) -> None:
        """Legitimation entanglement (§3.4): the state's delivery failure
        repels the COMMITTED org's base too, not just the incumbent's."""
        from babylon.engine.systems.policy import POLICY_DELIVERY_ATTR

        gap_row = {
            "incumbent_id": "org/party-socdem",
            "promised": 10.0,
            "delivered": 0.0,
            "gap": 10.0,
            "integral": 10.0,
            "tick": 1,
        }
        results = {}
        for committed in (False, True):
            graph, defines = _electoral_graph()
            graph.set_graph_attr(POLICY_DELIVERY_ATTR, {"C001": dict(gap_row)})
            if committed:
                graph.set_graph_attr(
                    POPULAR_FRONT_ATTR, self._committed_register("org/party-liberal")
                )
            _stamp_allegiance(graph, "C001", {"org/party-liberal": 0.5, "org/party-socdem": 0.5})
            AllegianceSystem().step(graph, _Services(defines, _RecordingBus()), _Context(2))
            results[committed] = float(
                graph.get_node("C001").attributes["allegiance"]["org/party-liberal"]
            )
        assert results[True] < results[False]


class TestSpoilerArithmetic:
    """ADR137 deferral, landed U12 (§3.2 stance 4): an independent ballot
    line's vote share subtracts from the ideologically-nearest duopoly share
    BEFORE winner resolution — the lesser-evil arithmetic is priced into the
    count, and the resulting rightward perturbation flows through the
    EXISTING FactionBalance/policy machinery (no new write paths)."""

    @staticmethod
    def _spoiler_terrain(graph):
        """Liberal 60 / restorationist 50 / socdem 40 (up to a common
        turnout factor): the liberal machine wins a clean count; a socdem
        independent line hands it to the restorationist."""
        _stamp_voter(
            graph, "C001", {"org/party-liberal": 0.6, "org/party-socdem": 0.4}, population=100
        )
        _stamp_voter(graph, "C002", {"org/party-restorationist": 1.0}, population=50)

    def test_independent_line_subtracts_from_the_nearest_duopoly(self) -> None:
        graph, defines = _electoral_graph()
        self._spoiler_terrain(graph)
        graph.update_node("org/party-socdem", acquired_doctrine_ids=("independent_ballot_line",))
        bus = _step(graph, defines, _FEDERAL_TICK)
        held = _events_of(bus, EventType.ELECTION_HELD)
        assert held[0].payload["winning_coalition"] == "org/party-restorationist"
        # The spoiler effect is recorded on the election event.
        assert held[0].payload["spoiler_target"] == "org/party-liberal"
        assert held[0].payload["spoiler_shift"] > 0.0

    def test_same_terrain_without_the_independent_stance_holds_the_duopoly(self) -> None:
        """Control: the identical count with NO independent line seats the
        liberal machine — the flip is the spoiler arithmetic, nothing else."""
        graph, defines = _electoral_graph()
        self._spoiler_terrain(graph)
        bus = _step(graph, defines, _FEDERAL_TICK)
        held = _events_of(bus, EventType.ELECTION_HELD)
        assert held[0].payload["winning_coalition"] == "org/party-liberal"
        assert held[0].payload["spoiler_target"] == ""
        assert held[0].payload["spoiler_shift"] == 0.0

    def test_rightward_perturbation_flows_through_the_existing_machinery(self) -> None:
        """The spoiler-flipped winner perturbs FactionBalance via the
        EXISTING government-formation path (no new write paths)."""
        graph, defines = _electoral_graph()
        self._spoiler_terrain(graph)
        graph.update_node("org/party-socdem", acquired_doctrine_ids=("independent_ballot_line",))
        graph.add_node(
            "org/state",
            _node_type="organization",
            org_type="state_apparatus",
            faction_balance={
                "finance_capital": 0.5,
                "security_state": 0.3,
                "settler_populist": 0.2,
                "stability": 0.5,
                "legitimacy": 0.5,
            },
        )
        bus = _step(graph, defines, _FEDERAL_TICK)
        formed = _events_of(bus, EventType.GOVERNMENT_FORMED)
        assert formed[0].payload["governing_coalition"] == "org/party-restorationist"
        new_balance = graph.get_node("org/state").attributes["faction_balance"]
        assert new_balance["settler_populist"] > 0.2  # the rightward shove

    def test_symmetric_spoiler_on_the_right(self) -> None:
        """An independent FASCIST line eats the restorationist machine's
        votes (the pole logic is symmetric — the game prices both sides)."""
        graph, defines = _electoral_graph()
        _stamp_voter(graph, "C001", {"org/party-liberal": 1.0}, population=50)
        _stamp_voter(
            graph,
            "C002",
            {"org/party-restorationist": 0.6, "org/party-fascist": 0.4},
            population=100,
        )
        graph.update_node("org/party-fascist", acquired_doctrine_ids=("independent_ballot_line",))
        bus = _step(graph, defines, _FEDERAL_TICK)
        held = _events_of(bus, EventType.ELECTION_HELD)
        assert held[0].payload["winning_coalition"] == "org/party-liberal"
        assert held[0].payload["spoiler_target"] == "org/party-restorationist"

    def test_spoiler_votes_floor_at_zero_and_keep_their_own_share(self) -> None:
        """A spoiler larger than its target's share subtracts only what
        exists (floor 0) and still counts its own votes."""
        graph, defines = _electoral_graph()
        _stamp_voter(
            graph, "C001", {"org/party-socdem": 0.9, "org/party-liberal": 0.1}, population=100
        )
        _stamp_voter(graph, "C002", {"org/party-restorationist": 0.4}, population=50)
        graph.update_node("org/party-socdem", acquired_doctrine_ids=("independent_ballot_line",))
        bus = _step(graph, defines, _FEDERAL_TICK)
        held = _events_of(bus, EventType.ELECTION_HELD)
        assert held[0].payload["winning_coalition"] == "org/party-socdem"
        # The liberal share (10) is smaller than the spoiler's (90): only 10
        # subtracts; the target floors at zero rather than going negative.
        assert held[0].payload["spoiler_shift"] > 0.0
