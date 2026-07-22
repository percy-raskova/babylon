"""Behavioral contract for AllegianceSystem @17.42 (P25 U8, ADR134).

THE VALVE unit: allegiance drift over the party terrain, the hope field
H(c), and the first production Agitation→Organization conversion pathway —
throttled by ``(1 − v·H)`` (L-VALVE bound to the live quantity), guarded by
parties-exist (TRAP 3: a scenario with zero PoliticalFaction orgs sees ZERO
reads-into-writes — the qa:regression six are byte-identical because the
write never happens, not because it is filtered).
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.scenarios.electoral_fixture import create_electoral_fixture_scenario
from babylon.engine.systems.allegiance import AllegianceSystem
from babylon.kernel.tick_partition import TickPartition
from babylon.models.enums import EventType

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


def _two_node_graph():
    from babylon.engine.scenarios._legacy import create_two_node_scenario

    state, _config, defines = create_two_node_scenario()
    return state.to_graph(), defines


def _class_attrs(graph, class_id: str) -> dict:
    return graph.get_node(class_id).attributes


def _step(graph, defines, tick: int = 1, context=None):
    bus = _RecordingBus()
    system = AllegianceSystem()
    ctx = context or _Context(tick)
    system.step(graph, _Services(defines, bus), ctx)
    return bus, ctx


class TestSystemIdentity:
    def test_position_and_partition(self) -> None:
        assert AllegianceSystem.position == 17.42
        assert AllegianceSystem.partition is TickPartition.CONSEQUENCE
        assert AllegianceSystem.creates_value is False


class TestPartiesExistGuard:
    """TRAP 3 / charter §U8(d): org-less ⟹ H=0 ⟹ valve 1.0 ⟹ ZERO writes.
    Proved, not asserted: the party-less graph is byte-unchanged."""

    def test_party_less_graph_is_untouched(self) -> None:
        graph, defines = _two_node_graph()
        before = {
            node.id: dict(node.attributes) for node in graph.query_nodes(node_type="social_class")
        }
        bus, ctx = _step(graph, defines)
        after = {
            node.id: dict(node.attributes) for node in graph.query_nodes(node_type="social_class")
        }
        assert after == before
        assert bus.events == []
        assert graph.get_graph_attr("political_labor_share", None) is None
        assert ctx.persistent_data == {}


class TestAllegianceDrift:
    def test_allegiance_masses_appear_on_class_nodes(self) -> None:
        graph, defines = _electoral_graph()
        _step(graph, defines)
        for class_id in ("C001", "C002"):
            allegiance = _class_attrs(graph, class_id).get("allegiance")
            assert isinstance(allegiance, dict) and allegiance, class_id
            assert set(allegiance) <= {
                "org/party-liberal",
                "org/party-restorationist",
                "org/party-socdem",
                "org/party-fascist",
            }
            total = sum(allegiance.values())
            assert 0.0 <= total <= 1.0 + 1e-9  # abstention is the implicit residual
            assert all(mass >= 0.0 for mass in allegiance.values())

    def test_contact_pulls_the_base_toward_its_party(self) -> None:
        """The socdem current is worker-concentrated (MEMBERSHIP C001 only):
        the worker's socdem allegiance must exceed the owner's."""
        graph, defines = _electoral_graph()
        _step(graph, defines)
        worker = _class_attrs(graph, "C001")["allegiance"]
        owner = _class_attrs(graph, "C002")["allegiance"]
        assert worker.get("org/party-socdem", 0.0) > owner.get("org/party-socdem", 0.0)

    def test_drift_is_deterministic(self) -> None:
        graph_a, defines = _electoral_graph()
        graph_b, _ = _electoral_graph()
        _step(graph_a, defines)
        _step(graph_b, defines)
        assert _class_attrs(graph_a, "C001")["allegiance"] == pytest.approx(
            _class_attrs(graph_b, "C001")["allegiance"]
        )


class TestHopeFieldAndValve:
    def test_hope_is_stamped_and_bounded(self) -> None:
        graph, defines = _electoral_graph()
        _step(graph, defines)
        for class_id in ("C001", "C002"):
            hope = _class_attrs(graph, class_id).get("hope")
            assert hope is not None
            assert 0.0 <= hope <= 1.0

    def test_valve_throttles_the_conversion(self) -> None:
        """L-VALVE bound to the live quantity: with agitation present, the
        organization gain under maximum valve strength is <= the gain with
        the valve disabled (monotone in valve_strength)."""
        gains = {}
        for strength in (0.0, 1.0):
            graph, defines = _electoral_graph()
            worker = graph.get_node("C001")
            ideology = dict(worker.attributes.get("ideology") or {})
            ideology["agitation"] = 0.8
            graph.update_node("C001", ideology=ideology)
            org_before = float(graph.get_node("C001").attributes.get("organization", 0.0))
            politics = defines.politics.model_copy(update={"valve_strength": strength})
            defines_variant = defines.model_copy(update={"politics": politics})
            _step(graph, defines_variant)
            org_after = float(graph.get_node("C001").attributes.get("organization", 0.0))
            gains[strength] = org_after - org_before
        assert gains[0.0] > 0.0, "agitation must convert to organization when unvalved"
        assert gains[1.0] <= gains[0.0], "hope must suppress, never amplify (L-VALVE)"

    def test_conversion_is_the_first_organization_increase_pathway(self) -> None:
        """TRAP 1 discharged: organization (the P(S|R) numerator, seed-static
        before U8) rises through the real conversion quantity."""
        graph, defines = _electoral_graph()
        worker = graph.get_node("C001")
        ideology = dict(worker.attributes.get("ideology") or {})
        ideology["agitation"] = 0.5
        graph.update_node("C001", ideology=ideology)
        org_before = float(graph.get_node("C001").attributes.get("organization", 0.0))
        _step(graph, defines)
        org_after = float(graph.get_node("C001").attributes.get("organization", 0.0))
        assert org_after > org_before
        assert org_after <= 1.0

    def test_zero_agitation_means_zero_conversion(self) -> None:
        graph, defines = _electoral_graph()
        org_before = float(graph.get_node("C001").attributes.get("organization", 0.0))
        _step(graph, defines)
        org_after = float(graph.get_node("C001").attributes.get("organization", 0.0))
        assert org_after == pytest.approx(org_before)


class TestHopeSpikeEvent:
    def test_hope_spike_fires_on_first_crossing(self) -> None:
        """A hope jump past hope_spike_gain publishes HOPE_SPIKE with the
        best-fit platform in the payload."""
        graph, defines = _electoral_graph()
        politics = defines.politics.model_copy(update={"hope_spike_gain": 0.0})
        defines_variant = defines.model_copy(update={"politics": politics})
        bus, _ = _step(graph, defines_variant)
        spikes = [e for e in bus.events if e.type == EventType.HOPE_SPIKE]
        # The worker class carries positive hope on the electoral terrain.
        assert any(e.payload["class_id"] == "C001" for e in spikes)
        for event in spikes:
            assert event.payload["hope"] > 0.0
            assert event.payload["platform_id"]

    def test_no_spike_when_hope_is_flat(self) -> None:
        graph, defines = _electoral_graph()
        ctx = _Context(1)
        bus_first, ctx = _step(graph, defines, context=ctx)
        ctx.tick = 2
        bus_second, _ = _step(graph, defines, tick=2, context=ctx)
        second_spikes = [e for e in bus_second.events if e.type == EventType.HOPE_SPIKE]
        assert second_spikes == []  # hope already priced in from tick 1


class TestPoliticalLaborShareProducer:
    """U3's deferred W-C producer: the political_form measure's input."""

    def test_producer_publishes_the_signed_share(self) -> None:
        graph, defines = _electoral_graph()
        _step(graph, defines)
        share = graph.get_graph_attr("political_labor_share", None)
        assert share is not None
        assert -1.0 <= share <= 1.0


class TestRoundTrip:
    def test_allegiance_and_hope_survive_or_drop_honestly(self) -> None:
        """allegiance is a REAL SocialClass field (round-trips); hope is
        transient per-tick bookkeeping (dropped by from_graph, per the
        threat_score precedent) — and neither crashes reconstruction."""
        from babylon.models.world_state import WorldState

        graph, defines = _electoral_graph()
        _step(graph, defines)
        restored = WorldState.from_graph(graph, tick=1)
        worker = restored.entities["C001"]
        assert worker.allegiance  # persisted (real model field)
        # hope is transient: SOCIAL_CLASS_COMPUTED_FIELDS drops it before
        # reconstruction, so the model never carries it.
        assert not hasattr(worker, "hope")


class TestFullEngineTick:
    """End-to-end: the 31-system engine runs a real tick on the electoral
    terrain — the valve system fires through the production path, the
    political_form opposition receives its producer, and the state
    round-trips (no observer crash)."""

    def test_engine_tick_on_electoral_terrain(self) -> None:
        from babylon.engine.context import TickContext
        from babylon.engine.services import ServiceContainer
        from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS, SimulationEngine
        from babylon.models.world_state import WorldState

        state, _config, _defines = create_electoral_fixture_scenario()
        graph = state.to_graph()
        services = ServiceContainer.create()
        context = TickContext(tick=1)

        SimulationEngine(list(_DEFAULT_SYSTEMS)).run_tick(graph, services, context)

        worker = graph.get_node("C001").attributes
        assert isinstance(worker.get("allegiance"), dict) and worker["allegiance"]
        assert worker.get("hope") is not None
        share = graph.get_graph_attr("political_labor_share", None)
        assert share is not None and -1.0 <= share <= 1.0

        # The U3 opposition receives its producer through GraphInputs @18.
        states = graph.get_graph_attr("shadow_opposition_states", {}) or {}
        political_form = states.get("political_form")
        assert political_form is not None
        assert political_form.get("balance") == pytest.approx(share, abs=1e-9)

        # The full state survives reconstruction (observer path).
        restored = WorldState.from_graph(graph, tick=1)
        assert restored.entities["C001"].allegiance
