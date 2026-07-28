"""Behavioral contract for PolicySystem @17.47 (P25 U9, ADR135).

THE LEGISLATE unit: the agenda register drains through the §2.4 pipeline —
preemption on the ADMINISTERS DAG, judicial strike-down off the live
Institution bench, the funding identity with deficit financing under bond
discipline, overlay writes, the per-class delivery ledger, and the
capital-strike application of the equalization operator at county grain.
Byte-safety is the empty-register guard (charter §U9(d)): a graph with no
agenda AND no fiscal register sees ZERO reads-into-writes.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines
from babylon.domain.politics.policy import PolicyAgendaItem
from babylon.engine.scenarios.electoral_fixture import create_electoral_fixture_scenario
from babylon.engine.systems.policy import (
    GOVERNANCE_ENDGAME_ATTR,
    POLICY_AGENDA_ATTR,
    POLICY_DELIVERY_ATTR,
    POLICY_OVERLAYS_ATTR,
    SOVEREIGN_FISCAL_ATTR,
    PolicySystem,
    enqueue_agenda_item,
)
from babylon.kernel.tick_partition import TickPartition
from babylon.models.enums import EdgeType, EventType, PolicyAxis

pytestmark = pytest.mark.unit


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
    def __init__(self, tick: int = 1) -> None:
        self.tick = tick
        self.persistent_data: dict = {}


def _electoral_graph():
    state, _config, defines = create_electoral_fixture_scenario()
    return state.to_graph(), defines


def _step(graph, defines, tick: int = 1):
    bus = _RecordingBus()
    PolicySystem().step(graph, _Services(defines, bus), _Context(tick))
    return bus


def _events_of(bus, event_type: EventType) -> list:
    return [e for e in bus.events if e.type == event_type]


def _stamp_fiscal_base(
    graph,
    territory_id: str = "T001",
    taxes: float = 100.0,
    surplus: float = 1000.0,
    phi_hour: float | None = None,
) -> None:
    """Stamp the fiscal facts; ``tick_phi_hour`` only when the test ASKS
    (U12 E: a stamped 0.0 is a MEASURED zero — starved/peripheral — while
    absence keeps the fixture on the core's plain bars, III.11)."""
    attrs: dict = {"tick_taxes_on_surplus": taxes, "tick_total_surplus": surplus}
    if phi_hour is not None:
        attrs["tick_phi_hour"] = phi_hour
    graph.update_node(territory_id, **attrs)


def _item(
    axis: PolicyAxis = PolicyAxis.SOCIAL_WAGE,
    magnitude: float = 0.1,
    promised: float = 0.0,
    sovereign_id: str = "SOV_USA_FED",
    source_org_id: str = "",
) -> PolicyAgendaItem:
    return PolicyAgendaItem(
        sovereign_id=sovereign_id,
        axis=axis,
        magnitude=magnitude,
        promised=promised,
        drafted_tick=1,
        source_org_id=source_org_id,
    )


class TestSystemIdentity:
    def test_position_and_partition(self) -> None:
        assert PolicySystem.position == 17.47
        assert PolicySystem.partition is TickPartition.CONSEQUENCE
        assert PolicySystem.creates_value is False


class TestEmptyRegisterGuard:
    """Charter §U9(d): no agenda + no fiscal register ⟹ byte-unchanged.
    Proved, not asserted — the qa six live here permanently."""

    def test_register_less_graph_is_untouched(self) -> None:
        graph, defines = _electoral_graph()
        before_nodes = {n.id: dict(n.attributes) for n in graph.query_nodes()}
        bus = _step(graph, defines)
        after_nodes = {n.id: dict(n.attributes) for n in graph.query_nodes()}
        assert after_nodes == before_nodes
        assert bus.events == []
        for attr in (
            POLICY_AGENDA_ATTR,
            POLICY_OVERLAYS_ATTR,
            SOVEREIGN_FISCAL_ATTR,
            POLICY_DELIVERY_ATTR,
        ):
            assert graph.get_graph_attr(attr, None) is None


class TestAgendaMechanics:
    def test_enqueue_and_fifo_drain_at_bounded_rate(self) -> None:
        graph, defines = _electoral_graph()
        first = _item(axis=PolicyAxis.WAGE_FLOOR, magnitude=0.05)
        second = _item(axis=PolicyAxis.LABOR_LAW, magnitude=0.05)
        enqueue_agenda_item(graph, first)
        enqueue_agenda_item(graph, second)
        assert defines.politics.policy_agenda_rate == 1
        bus = _step(graph, defines)
        enacted = _events_of(bus, EventType.POLICY_ENACTED)
        assert [e.payload["policy_axis"] for e in enacted] == ["wage_floor"]
        remaining = graph.get_graph_attr(POLICY_AGENDA_ATTR, None)
        assert [row["axis"] for row in remaining] == ["labor_law"]

    def test_enactment_writes_the_overlay(self) -> None:
        graph, defines = _electoral_graph()
        enqueue_agenda_item(graph, _item(axis=PolicyAxis.WAGE_FLOOR, magnitude=0.05))
        _step(graph, defines, tick=7)
        overlays = graph.get_graph_attr(POLICY_OVERLAYS_ATTR, None)
        row = overlays["SOV_USA_FED"]["wage_floor"]
        assert row["magnitude"] == pytest.approx(0.05)
        assert row["enacted_tick"] == 7


class TestTradeTariffOverlay:
    """P26 U5f (ADR165): the trade_tariff axis writes/reads through the
    SAME overlay register as every other regulatory-redistributive axis —
    no new system position, no new register."""

    def test_enactment_writes_the_overlay(self) -> None:
        graph, defines = _electoral_graph()
        enqueue_agenda_item(graph, _item(axis=PolicyAxis.TRADE_TARIFF, magnitude=0.08))
        _step(graph, defines, tick=3)
        overlays = graph.get_graph_attr(POLICY_OVERLAYS_ATTR, None)
        row = overlays["SOV_USA_FED"]["trade_tariff"]
        assert row["magnitude"] == pytest.approx(0.08)
        assert row["enacted_tick"] == 3

    def test_default_inert_no_motion_drafted_is_the_empty_register_no_op(self) -> None:
        """The end-to-end default-inert pin (charter §U9(d) generalized to
        this unit): with GameDefines().trade_policy at its shipped
        defaults (0.0/{}) and NO trade_tariff LEGISLATE motion ever
        queued, the Policy path is the existing empty-register guard —
        zero reads, zero writes, zero events."""
        graph, defines = _electoral_graph()
        assert defines.trade_policy.tariff_rates == {}
        assert defines.trade_policy.import_duty_rate == 0.0
        assert defines.trade_policy.trade_tax_rate == 0.0
        before_nodes = {n.id: dict(n.attributes) for n in graph.query_nodes()}
        bus = _step(graph, defines)
        after_nodes = {n.id: dict(n.attributes) for n in graph.query_nodes()}
        assert after_nodes == before_nodes
        assert bus.events == []
        assert graph.get_graph_attr(POLICY_OVERLAYS_ATTR, None) is None


class TestVetoGauntletOnTerrain:
    def test_unfundable_promise_is_struck_by_the_live_bench(self) -> None:
        """The fixture territory carries NO tick_ fiscal attrs — a funded
        promise against zero measured surplus has incidence 1.0 and the
        fixture's liberal bench (tolerance 0.6 × 0.5 = 0.3) voids it."""
        graph, defines = _electoral_graph()
        enqueue_agenda_item(graph, _item(promised=50.0))
        bus = _step(graph, defines)
        struck = _events_of(bus, EventType.POLICY_STRUCK)
        assert len(struck) == 1
        assert struck[0].payload["striking_institution"] == "INST_FED_JUDICIARY"
        assert graph.get_graph_attr(POLICY_OVERLAYS_ATTR, None) is None

    def test_lower_sovereign_is_preempted_past_the_envelope(self) -> None:
        """SOV_MI_STATE sits under SOV_USA_FED on the fixture's ADMINISTERS
        DAG — the municipal-socialism ceiling (§2.4 arm 4)."""
        graph, defines = _electoral_graph()
        assert defines.politics.preemption_envelope < 0.9
        enqueue_agenda_item(
            graph,
            _item(axis=PolicyAxis.WAGE_FLOOR, magnitude=0.9, sovereign_id="SOV_MI_STATE"),
        )
        bus = _step(graph, defines)
        preempted = _events_of(bus, EventType.POLICY_PREEMPTED)
        assert len(preempted) == 1
        assert preempted[0].payload["preempting_sovereign"] == "SOV_USA_FED"
        assert _events_of(bus, EventType.POLICY_ENACTED) == []


class TestFundingIdentityOnTerrain:
    def test_funded_promise_delivers_and_ledgers_per_class(self) -> None:
        graph, defines = _electoral_graph()
        _stamp_fiscal_base(graph, taxes=100.0, surplus=1000.0)
        enqueue_agenda_item(graph, _item(promised=80.0))  # incidence 0.08 < all bars
        bus = _step(graph, defines)
        enacted = _events_of(bus, EventType.POLICY_ENACTED)
        assert len(enacted) == 1
        assert enacted[0].payload["delivery_ratio"] == pytest.approx(1.0)
        ledger = graph.get_graph_attr(POLICY_DELIVERY_ATTR, None)
        assert set(ledger) == {"C001", "C002"}
        assert sum(row["delivered"] for row in ledger.values()) == pytest.approx(80.0)
        assert all(row["gap"] == pytest.approx(0.0) for row in ledger.values())
        assert _events_of(bus, EventType.DELIVERY_GAP_CROSSED) == []

    def test_unfunded_shortfall_borrows_and_opens_the_gap(self) -> None:
        """Deficit financing compounds the sovereign fiscal register; the
        residual gap ledgers per class and publishes DELIVERY_GAP_CROSSED."""
        graph, defines = _electoral_graph()
        _stamp_fiscal_base(graph, taxes=40.0, surplus=2000.0)
        enqueue_agenda_item(graph, _item(promised=100.0))  # incidence 0.05
        bus = _step(graph, defines)
        assert len(_events_of(bus, EventType.POLICY_ENACTED)) == 1
        fiscal = graph.get_graph_attr(SOVEREIGN_FISCAL_ATTR, None)
        borrowed = 0.5 * (100.0 - 40.0)  # debt_finance_share × shortfall
        assert fiscal["SOV_USA_FED"]["debt_stock"] == pytest.approx(borrowed)
        gaps = _events_of(bus, EventType.DELIVERY_GAP_CROSSED)
        assert {e.payload["class_id"] for e in gaps} == {"C001", "C002"}
        assert sum(e.payload["gap"] for e in gaps) == pytest.approx(100.0 - 40.0 - borrowed)

    def test_debt_service_shrinks_next_enactments_ceiling(self) -> None:
        """The O'Connor spiral: tick-1 borrowing raises tick-2 debt service
        (via the live endogenous rate), shrinking the funded ceiling."""
        graph, defines = _electoral_graph()
        _stamp_fiscal_base(graph, taxes=40.0, surplus=2000.0)
        graph.set_graph_attr(
            "national_financial", {"endogenous_interest": {"rate": 0.10, "year": 2024}}
        )
        enqueue_agenda_item(graph, _item(promised=100.0))
        first = _step(graph, defines, tick=1)
        stock = graph.get_graph_attr(SOVEREIGN_FISCAL_ATTR)["SOV_USA_FED"]["debt_stock"]
        assert stock > 0.0
        enqueue_agenda_item(graph, _item(promised=100.0))
        second = _step(graph, defines, tick=2)
        first_gap = sum(e.payload["gap"] for e in _events_of(first, EventType.DELIVERY_GAP_CROSSED))
        second_gap = sum(
            e.payload["gap"] for e in _events_of(second, EventType.DELIVERY_GAP_CROSSED)
        )
        assert second_gap > first_gap  # service ate part of the ceiling


class TestCapitalStrike:
    def test_strike_migrates_capital_out_of_the_claimed_county(self) -> None:
        """Arm 1: incidence past tolerance enters the claimed county's
        profit rate as a penalty; the equalization operator moves capital
        toward the unclaimed geography, conserving Σc (§2.4)."""
        from babylon.models.world_state import WorldState

        state, _config, defines = create_electoral_fixture_scenario()
        second = state.territories["T001"].model_copy(update={"id": "T002", "county_fips": None})
        state = state.model_copy(update={"territories": {**state.territories, "T002": second}})
        graph = state.to_graph()
        _stamp_fiscal_base(graph, "T001", taxes=100.0, surplus=1000.0)
        graph.update_node("T001", tick_capital_stock=100.0, tick_profit_rate=0.05)
        graph.update_node("T002", tick_capital_stock=100.0, tick_profit_rate=0.05)

        # incidence 0.2: past capital_tolerance 0.15, under the bench's 0.3.
        enqueue_agenda_item(graph, _item(promised=200.0))
        bus = _step(graph, defines)

        strikes = _events_of(bus, EventType.CAPITAL_STRIKE)
        assert len(strikes) == 1
        outflow = strikes[0].payload["outflow"]
        assert outflow > 0.0
        claimed = graph.get_node("T001").attributes["tick_capital_stock"]
        refuge = graph.get_node("T002").attributes["tick_capital_stock"]
        assert claimed == pytest.approx(100.0 - outflow)
        assert refuge == pytest.approx(100.0 + outflow)  # ΣΔc = 0
        assert WorldState.from_graph(graph, tick=1) is not None  # observer path survives

    def test_national_policy_has_nowhere_to_flee(self) -> None:
        """Every capital-bearing territory claimed ⟹ uniform penalty ⟹
        zero migration; the event still fires with outflow 0.0."""
        graph, defines = _electoral_graph()
        _stamp_fiscal_base(graph, taxes=100.0, surplus=1000.0)
        graph.update_node("T001", tick_capital_stock=100.0, tick_profit_rate=0.05)
        enqueue_agenda_item(graph, _item(promised=200.0))
        bus = _step(graph, defines)
        strikes = _events_of(bus, EventType.CAPITAL_STRIKE)
        assert len(strikes) == 1
        assert strikes[0].payload["outflow"] == pytest.approx(0.0)
        assert graph.get_node("T001").attributes["tick_capital_stock"] == pytest.approx(100.0)


class TestLegislateSeam:
    def test_state_ai_legislate_selection_reaches_the_agenda(self) -> None:
        """The OODA enqueue seam: a LEGISLATE-marked action drafts onto the
        register under the territory's top claims-holder (before ADR135
        the npc_stub conversion stamped REPRESS on every StateAction)."""
        from babylon.engine.systems.ooda import OODASystem
        from babylon.models.enums import ActionType, StateActionType
        from babylon.ooda.types import Action

        graph, defines = _electoral_graph()
        action = Action(
            org_id="org/party-liberal",
            action_type=ActionType.ORGANIZE,
            target_id="T001",
            params={
                "state_sub_verb": StateActionType.LEGISLATE.value,
                "policy_axis": "police_budget",
            },
        )
        bus = _RecordingBus()
        result = OODASystem()._enqueue_legislate(
            action,
            {"territory_ids": ["T001"]},
            graph,
            _Services(GameDefines(), bus),
            tick=3,
        )
        assert result.success is True
        agenda = graph.get_graph_attr(POLICY_AGENDA_ATTR, None)
        assert len(agenda) == 1
        assert agenda[0]["sovereign_id"] == "SOV_USA_FED"
        assert agenda[0]["axis"] == "police_budget"
        assert agenda[0]["drafted_tick"] == 3

    def test_npc_stub_no_longer_misclassifies_legislate_as_repress(self) -> None:
        """The StateAction→Action boundary keeps the sub-verb identity."""
        from unittest.mock import patch

        from babylon.models.entities.state_apparatus_ai import StateAction
        from babylon.models.enums import ActionType, StateActionType, StateFaction
        from babylon.ooda import npc_stub

        legislate = StateAction(
            verb=StateActionType.ADMINISTER,
            sub_verb=StateActionType.LEGISLATE,
            target_id="T001",
            budget_cost=3.0,
            thread_cost=0,
            legitimacy_cost=0.0,
            faction_alignment=StateFaction.FINANCE_CAPITAL,
        )
        with patch(
            "babylon.ooda.state_ai.decision.RuleBasedStateAI.select_action",
            return_value=[legislate],
        ):
            actions = npc_stub._try_state_ai_dispatch(
                org_id="org/state-apparatus",
                org_attrs={
                    "faction_balance": {
                        "finance_capital": 0.5,
                        "security_state": 0.3,
                        "settler_populist": 0.2,
                        "stability": 0.8,
                        "legitimacy": 0.7,
                    }
                },
            )
        assert actions is not None and len(actions) == 1
        converted = actions[0]
        assert converted.action_type is not ActionType.REPRESS
        assert converted.params["state_sub_verb"] == "legislate"
        assert converted.params["policy_axis"] == "war_posture"  # FC's apparatus axis


class TestOverlayConsumers:
    def test_social_wage_delivery_relieves_subsistence_in_survival(self) -> None:
        """§2.4 read-side: the delivered social wage covers subsistence in
        P(S|A) — read-time relief, never a wealth write (A4-safe)."""
        from babylon.engine.services import ServiceContainer
        from babylon.engine.systems.survival import SurvivalSystem

        services = ServiceContainer.create()
        graph_dry, _ = _electoral_graph()
        graph_wet, _ = _electoral_graph()
        graph_wet.set_graph_attr(
            POLICY_DELIVERY_ATTR,
            {"C001": {"incumbent_id": "SOV_USA_FED", "delivered": 50.0, "gap": 0.0}},
        )
        SurvivalSystem().step(graph_dry, services, _Context(1))
        SurvivalSystem().step(graph_wet, services, _Context(1))
        dry = graph_dry.get_node("C001").attributes["p_acquiescence"]
        wet = graph_wet.get_node("C001").attributes["p_acquiescence"]
        assert wet > dry  # covered subsistence raises the acquiescence branch

    def test_border_regime_throttles_the_reserve_army_valve(self) -> None:
        from babylon.engine.services import ServiceContainer
        from babylon.engine.systems.reserve_army import ReserveArmySystem

        services = ServiceContainer.create()
        graph_open, _ = _electoral_graph()
        graph_closed, _ = _electoral_graph()
        for graph in (graph_open, graph_closed):
            graph.update_node("T001", reserve_ratio=0.4, median_wage=1000.0)
        graph_closed.set_graph_attr(
            POLICY_OVERLAYS_ATTR,
            {"SOV_USA_FED": {"border_regime": {"magnitude": 0.5, "enacted_tick": 0}}},
        )
        ReserveArmySystem().step(graph_open, services, _Context(1))
        ReserveArmySystem().step(graph_closed, services, _Context(1))
        open_wage = graph_open.get_node("T001").attributes["median_wage"]
        closed_wage = graph_closed.get_node("T001").attributes["median_wage"]
        # A tighter border shrinks the reserve army ⟹ less wage pressure.
        assert closed_wage > open_wage

    def test_betrayal_term_repels_allegiance_from_the_incumbent(self) -> None:
        """θ.betrayal (ADR134 §5 → ADR135): a prior-tick delivery gap under
        an incumbent party bleeds that party's allegiance mass."""
        from babylon.engine.systems.allegiance import AllegianceSystem

        defines = GameDefines()
        graph_kept, _ = _electoral_graph()
        graph_betrayed, _ = _electoral_graph()
        graph_betrayed.set_graph_attr(
            POLICY_DELIVERY_ATTR,
            {
                "C001": {
                    "incumbent_id": "org/party-liberal",
                    "promised": 100.0,
                    "delivered": 20.0,
                    "gap": 80.0,
                    "integral": 80.0,
                    "tick": 0,
                }
            },
        )
        bus = _RecordingBus()
        AllegianceSystem().step(graph_kept, _Services(defines, bus), _Context(1))
        AllegianceSystem().step(graph_betrayed, _Services(defines, bus), _Context(1))
        kept = graph_kept.get_node("C001").attributes["allegiance"]["org/party-liberal"]
        betrayed = (
            graph_betrayed.get_node("C001").attributes["allegiance"].get("org/party-liberal", 0.0)
        )
        assert betrayed < kept


class TestFullEngineTick:
    """End-to-end: the 32-system engine runs a real tick on the electoral
    terrain with a seeded agenda — the resolver fires through the
    production path and the state round-trips (no observer crash)."""

    def test_engine_tick_with_a_live_agenda(self) -> None:
        from babylon.engine.context import TickContext
        from babylon.engine.services import ServiceContainer
        from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS, SimulationEngine
        from babylon.models.world_state import WorldState

        state, _config, _defines = create_electoral_fixture_scenario()
        graph = state.to_graph()
        enqueue_agenda_item(graph, _item(axis=PolicyAxis.WAGE_FLOOR, magnitude=0.05))
        services = ServiceContainer.create()

        SimulationEngine(list(_DEFAULT_SYSTEMS)).run_tick(graph, services, TickContext(tick=1))

        overlays = graph.get_graph_attr(POLICY_OVERLAYS_ATTR, None)
        assert overlays["SOV_USA_FED"]["wage_floor"]["magnitude"] == pytest.approx(0.05)
        assert graph.get_graph_attr(POLICY_AGENDA_ATTR) == []
        restored = WorldState.from_graph(graph, tick=1)
        assert restored.entities["C001"].allegiance  # U8 still live alongside


class TestHostDisciplineClamp:
    """ADR137 deferral, landed U12 (§3.2 stance 3): an entryist org's
    EFFECTIVE platform is clamped toward the host median at ENACTMENT — a
    projection operator, never a campaign-time edit. The standing overlay on
    the axis IS the machine's median (the duopoly governs through the status
    quo ante); the entryist enacts only ``1 - host_discipline_clamp_share``
    of the distance it demanded. The clamp delta is charged to the
    entryist's own delivery ledger through the funded channel."""

    @staticmethod
    def _entryist(graph, org_id: str = "org/party-liberal") -> None:
        graph.update_node(org_id, acquired_doctrine_ids=("entryism",))

    def test_regulatory_enactment_clamps_toward_zero_standing(self) -> None:
        graph, defines = _electoral_graph()
        self._entryist(graph)
        enqueue_agenda_item(
            graph,
            _item(axis=PolicyAxis.WAGE_FLOOR, magnitude=0.08, source_org_id="org/party-liberal"),
        )
        bus = _step(graph, defines)
        enacted = _events_of(bus, EventType.POLICY_ENACTED)
        assert len(enacted) == 1
        # standing 0.0 + (0.08 - 0.0) x (1 - 0.5 clamp share)
        assert enacted[0].payload["magnitude"] == pytest.approx(0.04)

    def test_funded_clamp_scales_delivered_and_charges_the_gap(self) -> None:
        """The gap between what you ran on and what you may enact is a
        delivery gap charged to YOU — it flows the existing betrayal ledger."""
        graph, defines = _electoral_graph()
        self._entryist(graph)
        _stamp_fiscal_base(graph, taxes=100.0, surplus=1000.0)
        enqueue_agenda_item(
            graph,
            _item(magnitude=0.08, promised=80.0, source_org_id="org/party-liberal"),
        )
        bus = _step(graph, defines)
        ledger = graph.get_graph_attr(POLICY_DELIVERY_ATTR, None)
        assert sum(row["delivered"] for row in ledger.values()) == pytest.approx(40.0)
        gaps = _events_of(bus, EventType.DELIVERY_GAP_CROSSED)
        assert sum(e.payload["gap"] for e in gaps) == pytest.approx(40.0)

    def test_clamp_projects_toward_the_standing_overlay(self) -> None:
        """With a standing 0.2 already enacted, a 0.8 demand enacts at
        0.04 + (0.08 - 0.04) x 0.5 = 0.06 — the host median pulls, not zero."""
        graph, defines = _electoral_graph()
        self._entryist(graph)
        enqueue_agenda_item(
            graph,
            _item(axis=PolicyAxis.WAGE_FLOOR, magnitude=0.04, source_org_id="org/party-socdem"),
        )
        _step(graph, defines, tick=1)
        enqueue_agenda_item(
            graph,
            _item(axis=PolicyAxis.WAGE_FLOOR, magnitude=0.08, source_org_id="org/party-liberal"),
        )
        bus = _step(graph, defines, tick=2)
        enacted = _events_of(bus, EventType.POLICY_ENACTED)
        assert enacted[0].payload["magnitude"] == pytest.approx(0.06)

    def test_non_entryist_control_is_unclamped(self) -> None:
        graph, defines = _electoral_graph()
        enqueue_agenda_item(
            graph,
            _item(axis=PolicyAxis.WAGE_FLOOR, magnitude=0.08, source_org_id="org/party-liberal"),
        )
        bus = _step(graph, defines)
        enacted = _events_of(bus, EventType.POLICY_ENACTED)
        assert enacted[0].payload["magnitude"] == pytest.approx(0.08)

    def test_derecognized_entryist_faces_the_plain_gauntlet(self) -> None:
        """The expelled are out of the host's discipline AND its shelter —
        no clamp, no fold; the plain veto terrain applies."""
        graph, defines = _electoral_graph()
        self._entryist(graph)
        graph.set_graph_attr("electoral_derecognized", ("org/party-liberal",))
        enqueue_agenda_item(
            graph,
            _item(axis=PolicyAxis.WAGE_FLOOR, magnitude=0.08, source_org_id="org/party-liberal"),
        )
        bus = _step(graph, defines)
        enacted = _events_of(bus, EventType.POLICY_ENACTED)
        assert enacted[0].payload["magnitude"] == pytest.approx(0.08)


def _stamp_government(
    graph, party: str = "org/party-socdem", sovereign: str = "SOV_USA_FED"
) -> None:
    """A seated government — the raw register literal, the U10 test idiom."""
    governments = dict(graph.get_graph_attr("electoral_governments", None) or {})
    governments[sovereign] = {"party_id": party, "formed_tick": 1, "share": 0.6}
    graph.set_graph_attr("electoral_governments", governments)


class TestBetrayalCrossing:
    """U12 D: b(c) = Σ gap crossing ``betrayal_threshold`` fires
    BETRAYAL_INTEGRAL_CROSSED once per class — an edge trigger on the
    integral, not a per-gap repeat (the SYRIZA-voter curve is durable)."""

    def test_crossing_fires_once_per_class_then_stays_silent(self) -> None:
        graph, defines = _electoral_graph()
        _stamp_fiscal_base(graph, taxes=40.0, surplus=2000.0)
        _stamp_government(graph)
        enqueue_agenda_item(graph, _item(promised=100.0))
        first = _step(graph, defines, tick=1)
        crossed = _events_of(first, EventType.BETRAYAL_INTEGRAL_CROSSED)
        assert {e.payload["class_id"] for e in crossed} == {"C001", "C002"}
        assert all(e.payload["incumbent_id"] == "org/party-socdem" for e in crossed)
        assert all(e.payload["integral"] >= e.payload["threshold"] > 0.0 for e in crossed)
        # Second gap tick: the integral grows but the crossing already
        # happened — no repeat (DELIVERY_GAP_CROSSED still reports the flow).
        enqueue_agenda_item(graph, _item(promised=100.0))
        second = _step(graph, defines, tick=2)
        assert _events_of(second, EventType.BETRAYAL_INTEGRAL_CROSSED) == []
        assert _events_of(second, EventType.DELIVERY_GAP_CROSSED) != []

    def test_no_crossing_below_threshold(self) -> None:
        graph, defines = _electoral_graph()
        _stamp_fiscal_base(graph, taxes=100.0, surplus=1000.0)
        _stamp_government(graph)
        enqueue_agenda_item(graph, _item(promised=80.0))  # fully funded, gap 0
        bus = _step(graph, defines)
        assert _events_of(bus, EventType.BETRAYAL_INTEGRAL_CROSSED) == []


class TestGovernanceFork:
    """U12 D (§3.5): first ceiling contact IN OFFICE resolves the SYRIZA
    fork — arm and geometry are standing math over already-measured
    quantities; the register is absorbing; org-less/government-less graphs
    never open it."""

    def test_fiscal_ceiling_contact_capitulates_when_captured(self) -> None:
        graph, defines = _electoral_graph()
        _stamp_fiscal_base(graph, taxes=40.0, surplus=2000.0)
        _stamp_government(graph)
        graph.update_node("org/party-socdem", institutional_pull=0.9)
        enqueue_agenda_item(graph, _item(promised=100.0))
        bus = _step(graph, defines)
        forks = _events_of(bus, EventType.GOVERNANCE_FORK_RESOLVED)
        assert len(forks) == 1
        assert forks[0].payload["arm"] == "capitulate"
        assert forks[0].payload["geometry"] == ""
        assert forks[0].payload["contact"] == "fiscal"
        register = graph.get_graph_attr(GOVERNANCE_ENDGAME_ATTR, None)
        assert register["org/party-socdem"]["arm"] == "capitulate"
        assert register["org/party-socdem"]["sovereign_id"] == "SOV_USA_FED"

    def test_fork_is_absorbing(self) -> None:
        graph, defines = _electoral_graph()
        _stamp_fiscal_base(graph, taxes=40.0, surplus=2000.0)
        _stamp_government(graph)
        enqueue_agenda_item(graph, _item(promised=100.0))
        _step(graph, defines, tick=1)
        enqueue_agenda_item(graph, _item(promised=100.0))
        second = _step(graph, defines, tick=2)
        assert _events_of(second, EventType.GOVERNANCE_FORK_RESOLVED) == []

    def test_no_government_means_no_fork(self) -> None:
        """The (d) guard's engine half: without a seated party the incumbent
        is the sovereign itself — no fork, no register."""
        graph, defines = _electoral_graph()
        _stamp_fiscal_base(graph, taxes=40.0, surplus=2000.0)
        enqueue_agenda_item(graph, _item(promised=100.0))
        bus = _step(graph, defines)
        assert _events_of(bus, EventType.GOVERNANCE_FORK_RESOLVED) == []
        assert graph.get_graph_attr(GOVERNANCE_ENDGAME_ATTR, None) is None

    def test_rupture_requires_organs_on_the_claimed_terrain(self) -> None:
        """The DUAL_POWER read path (charter §U12(c)): the fork reads the
        same >= 2-active-claimants structure SovereigntySystem @17.5 emits
        DUAL_POWER_ACTIVE for, live over the governing sovereign's claimed
        territories. Without a second claimant even an uncaptured party
        capitulates (SYRIZA held no organs)."""
        graph, defines = _electoral_graph()
        _stamp_fiscal_base(graph, taxes=40.0, surplus=2000.0)
        _stamp_government(graph)  # institutional_pull defaults 0.0 — uncaptured
        enqueue_agenda_item(graph, _item(promised=100.0))
        bus = _step(graph, defines, tick=1)
        [fork] = _events_of(bus, EventType.GOVERNANCE_FORK_RESOLVED)
        assert fork.payload["arm"] == "capitulate"

        # Same terrain plus a second active claimant on T001: organs live.
        graph2, defines2 = _electoral_graph()
        _stamp_fiscal_base(graph2, taxes=40.0, surplus=2000.0)
        _stamp_government(graph2)
        graph2.add_edge(
            "SOV_MI_STATE",
            "T001",
            edge_type=EdgeType.CLAIMS,
            control_level=0.3,
            legal_status="de_facto",
        )
        enqueue_agenda_item(graph2, _item(promised=100.0))
        bus2 = _step(graph2, defines2, tick=1)
        [fork2] = _events_of(bus2, EventType.GOVERNANCE_FORK_RESOLVED)
        assert fork2.payload["arm"] == "rupture"

    def test_rupture_geometry_synthesis_needs_bridges_and_starved_state(self) -> None:
        def rupture_fixture(*, bridges: bool, phi_hour: float):
            graph, defines = _electoral_graph()
            _stamp_fiscal_base(graph, taxes=40.0, surplus=2000.0, phi_hour=phi_hour)
            _stamp_government(graph)
            graph.add_edge(
                "SOV_MI_STATE",
                "T001",
                edge_type=EdgeType.CLAIMS,
                control_level=0.3,
                legal_status="de_facto",
            )
            if bridges:
                graph.add_edge(
                    "org/party-socdem",
                    "C001",
                    edge_type=EdgeType.SOLIDARITY,
                    solidarity_strength=0.5,
                )
            enqueue_agenda_item(graph, _item(promised=100.0))
            return _step(graph, defines, tick=1)

        # Bridges + Φ-starved state (phi_share 0 < floor): the synthesis window.
        [synth] = _events_of(
            rupture_fixture(bridges=True, phi_hour=0.0),
            EventType.GOVERNANCE_FORK_RESOLVED,
        )
        assert synth.payload["arm"] == "rupture"
        assert synth.payload["geometry"] == "synthesis"

        # No bridges: the Allende geometry.
        [allende] = _events_of(
            rupture_fixture(bridges=False, phi_hour=0.0),
            EventType.GOVERNANCE_FORK_RESOLVED,
        )
        assert allende.payload["geometry"] == "allende"

        # Rent-cushioned state (phi_share = 5.0*40/2000 = 0.10 >= 0.05 floor):
        # the state can afford its own repression — Allende even with bridges.
        [cushioned] = _events_of(
            rupture_fixture(bridges=True, phi_hour=5.0),
            EventType.GOVERNANCE_FORK_RESOLVED,
        )
        assert cushioned.payload["geometry"] == "allende"

    def test_struck_contact_opens_the_fork_too(self) -> None:
        """The judicial arm is a ceiling contact (the gauntlet's §2.4 arm 2)."""
        graph, defines = _electoral_graph()
        _stamp_government(graph)
        enqueue_agenda_item(graph, _item(promised=50.0))  # unfundable -> STRUCK
        bus = _step(graph, defines)
        assert len(_events_of(bus, EventType.POLICY_STRUCK)) == 1
        [fork] = _events_of(bus, EventType.GOVERNANCE_FORK_RESOLVED)
        assert fork.payload["contact"] == "struck"
