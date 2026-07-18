"""Track 1 / Task 5 §B (2026-07-18, branch fix/null-play-coupling): a
non-player organization's INTERNAL state
(``consciousness_tendency``/``cohesion``/``cadre_level``/``heat``) is
political and gated the same way territory political fields are; its
EXISTENCE/``territory_ids``/``budget`` stay material — always visible.
The player's own org is exempt: full visibility of your own organization,
guaranteed by an EXPLICIT bypass (not an emergent property of always being
in its own organizing reach).
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


class _StubOrg:
    """Quacks like an Organization — exposes only what
    ``_serialize_organization`` reads (mirrors
    ``test_player_org_identity.py``'s own fixture)."""

    def __init__(
        self,
        *,
        id: str,
        cohesion: float = 0.6,
        cadre_level: float = 0.3,
        budget: float = 500.0,
        heat: float = 0.42,
        territory_ids: list[str] | None = None,
        consciousness_tendency: str = "reformist",
        class_character: str = "proletarian",
        org_type: str = "civil_society",
        name: str = "Rival Committee",
    ) -> None:
        self.id = id
        self.name = name
        self.class_character = class_character
        self.org_type = org_type
        self.cohesion = cohesion
        self.cadre_level = cadre_level
        self.budget = budget
        self.heat = heat
        self.territory_ids = territory_ids or ["T1", "T2"]
        self.consciousness_tendency = consciousness_tendency


class TestSerializeOrganizationFog:
    def test_default_no_reach_is_unfogged_backward_compat(self) -> None:
        from game.engine_bridge import _serialize_organization

        org = _StubOrg(id="ORG-RIVAL")
        out = _serialize_organization(org, player_org_id="ORG-PLAYER")

        assert out["cohesion"] == pytest.approx(0.6)
        assert out["cadre_level"] == pytest.approx(0.3)
        assert out["heat"] == pytest.approx(0.42)
        assert out["consciousness_tendency"] == "reformist"
        assert "vision_masked" not in out

    def test_non_player_org_outside_reach_has_internal_state_masked(self) -> None:
        from game.engine_bridge import _serialize_organization
        from game.fog.ledger import IntelLedger

        org = _StubOrg(id="ORG-RIVAL")
        out = _serialize_organization(
            org,
            player_org_id="ORG-PLAYER",
            reach=frozenset(),  # ORG-RIVAL not in reach
            ledger=IntelLedger(),
            tick=10,
        )

        assert out["cohesion"] is None
        assert out["cadre_level"] is None
        assert out["heat"] is None
        assert out["consciousness_tendency"] is None
        assert set(out["vision_masked"]) == {
            "cohesion",
            "cadre_level",
            "heat",
            "consciousness_tendency",
        }

    def test_non_player_org_existence_and_territory_ids_stay_material(self) -> None:
        """Existence/public activity/territorial presence are material —
        never gated, regardless of reach."""
        from game.engine_bridge import _serialize_organization
        from game.fog.ledger import IntelLedger

        org = _StubOrg(id="ORG-RIVAL", territory_ids=["T1", "T2"])
        out = _serialize_organization(
            org,
            player_org_id="ORG-PLAYER",
            reach=frozenset(),
            ledger=IntelLedger(),
            tick=10,
        )

        assert out["id"] == "ORG-RIVAL"
        assert out["name"] == "Rival Committee"
        assert out["budget"] == pytest.approx(500.0)
        assert out["territory_ids"] == ["T1", "T2"]

    def test_player_org_is_fully_visible_even_when_reach_is_empty(self) -> None:
        """The hard guarantee: the player's own org is NEVER gated, even in
        a degenerate case where ``reach`` doesn't (or can't) include it —
        this must not depend on organizing_reach's BFS always seeding
        ``{player_org_id}``; it is an explicit bypass in the composer."""
        from game.engine_bridge import _serialize_organization
        from game.fog.ledger import IntelLedger

        org = _StubOrg(id="ORG-PLAYER", cohesion=0.9, cadre_level=0.7, heat=0.55)
        out = _serialize_organization(
            org,
            player_org_id="ORG-PLAYER",
            reach=frozenset(),  # deliberately does NOT contain ORG-PLAYER
            ledger=IntelLedger(),
            tick=10,
        )

        assert out["cohesion"] == pytest.approx(0.9)
        assert out["cadre_level"] == pytest.approx(0.7)
        assert out["heat"] == pytest.approx(0.55)
        assert out["consciousness_tendency"] == "reformist"
        assert out["vision_masked"] == []

    def test_non_player_org_inside_reach_stays_exact(self) -> None:
        from game.engine_bridge import _serialize_organization
        from game.fog.ledger import IntelLedger

        org = _StubOrg(id="ORG-ALLY")
        out = _serialize_organization(
            org,
            player_org_id="ORG-PLAYER",
            reach=frozenset({"ORG-ALLY"}),
            ledger=IntelLedger(),
            tick=10,
        )

        assert out["cohesion"] == pytest.approx(0.6)
        assert out["vision_masked"] == []

    def test_ledger_entry_serves_exact_values_outside_reach(self) -> None:
        from game.engine_bridge import _serialize_organization
        from game.fog.ledger import IntelEntry, IntelLedger

        org = _StubOrg(id="ORG-RIVAL", cohesion=0.6, heat=0.42)
        ledger = IntelLedger().append(
            IntelEntry(
                node_id="ORG-RIVAL",
                field_group="organization:political",
                tick_observed=10,
                value_snapshot={"cohesion": 0.6, "heat": 0.42},
            )
        )
        out = _serialize_organization(
            org,
            player_org_id="ORG-PLAYER",
            reach=frozenset(),
            ledger=ledger,
            tick=10,
        )

        assert out["cohesion"] == pytest.approx(0.6)
        assert out["heat"] == pytest.approx(0.42)
        assert "cohesion" not in out["vision_masked"]


class TestGetInspectorOrgOrgPoliticalFields:
    def _bridge_with_two_orgs(self) -> tuple[Any, Any]:
        from babylon.models.enums import NodeType
        from babylon.topology.graph import BabylonGraph
        from game.engine_bridge import EngineBridge

        graph = BabylonGraph()
        graph.add_node(
            "ORG-PLAYER",
            NodeType.ORGANIZATION,
            id="ORG-PLAYER",
            name="Player Org",
            class_character="proletarian",
            org_type="civil_society",
            service_type="mutual_aid",
            legal_standing="informal",
            consciousness_tendency="revolutionary",
            cohesion=0.5,
            cadre_level=0.2,
            budget=100.0,
            heat=0.1,
            territory_ids=[],
        )
        graph.add_node(
            "ORG-RIVAL",
            NodeType.ORGANIZATION,
            id="ORG-RIVAL",
            name="Rival Org",
            class_character="bourgeois",
            org_type="business",
            sector="finance",
            legal_standing="registered",
            consciousness_tendency="fascist",
            cohesion=0.8,
            cadre_level=0.6,
            budget=500.0,
            heat=0.3,
            territory_ids=[],
        )
        graph.set_graph_attr("player_org_id", "ORG-PLAYER")

        mock_persistence = MagicMock()
        mock_persistence.hydrate_graph.return_value = graph
        return EngineBridge(mock_persistence), graph

    def test_rival_org_internal_state_is_masked(self) -> None:
        bridge, _graph = self._bridge_with_two_orgs()

        result = bridge.get_inspector_org(uuid.uuid4(), "ORG-RIVAL")

        assert result["cohesion"] is None
        assert result["cadre_level"] is None
        assert result["heat"] is None
        assert result["consciousness_tendency"] is None
        assert set(result["vision_masked"]) == {
            "cohesion",
            "cadre_level",
            "heat",
            "consciousness_tendency",
        }

    def test_rival_org_existence_and_budget_stay_material(self) -> None:
        bridge, _graph = self._bridge_with_two_orgs()

        result = bridge.get_inspector_org(uuid.uuid4(), "ORG-RIVAL")

        assert result["id"] == "ORG-RIVAL"
        assert result["name"] == "Rival Org"
        assert result["budget"] == pytest.approx(500.0)

    def test_player_org_is_fully_visible(self) -> None:
        bridge, _graph = self._bridge_with_two_orgs()

        result = bridge.get_inspector_org(uuid.uuid4(), "ORG-PLAYER")

        assert result["cohesion"] == pytest.approx(0.5)
        assert result["cadre_level"] == pytest.approx(0.2)
        assert result["heat"] == pytest.approx(0.1)
        assert result["consciousness_tendency"] == "revolutionary"
        assert result["vision_masked"] == []


class TestBuildStateApparatusDashboardHeatFog:
    """Task 5b (2026-07-18): ``get_state_apparatus_dashboard`` used to discard
    its hydrated graph and call ``_serialize_organization`` without ``reach``,
    leaving the whole state-apparatus screen unfogged. Once ``reach`` is
    threaded, a masked org's ``heat`` is ``None`` (key present, value
    ``None`` — the naive ``float(o.get("heat", 0.0))`` sum crashes on that).
    Owner ruling: partial aggregate + masked count — ``total_heat`` sums
    ONLY visible-heat orgs, never a fabricated 0.0 for an all-masked group
    (Constitution III.11). ``budget`` is MATERIAL, never gated, so
    ``total_repression_budget`` is unaffected in every case here.
    """

    @staticmethod
    def _state_org(
        *, org_id: str, heat: float, reach: frozenset[str], budget: float = 500.0
    ) -> dict[str, Any]:
        from game.engine_bridge import _serialize_organization
        from game.fog.ledger import IntelLedger

        org = _StubOrg(id=org_id, heat=heat, budget=budget, org_type="state_apparatus")
        return _serialize_organization(
            org,
            player_org_id="ORG-PLAYER",
            reach=reach,
            ledger=IntelLedger(),
            tick=10,
        )

    def test_masked_state_org_heat_is_none_and_counted_masked(self) -> None:
        from babylon.models.world_state import WorldState
        from game.engine_bridge import _build_state_apparatus_dashboard

        org = self._state_org(org_id="ORG-STATE", heat=0.7, reach=frozenset())
        assert org["heat"] is None

        dashboard = _build_state_apparatus_dashboard(WorldState(), [org], recent_actions=[])

        assert dashboard["heat_orgs_masked"] == 1
        assert dashboard["heat_orgs_visible"] == 0
        assert dashboard["total_heat"] is None

    def test_mixed_visible_and_masked_sums_only_visible(self) -> None:
        from babylon.models.world_state import WorldState
        from game.engine_bridge import _build_state_apparatus_dashboard

        visible = self._state_org(org_id="ORG-VISIBLE", heat=0.3, reach=frozenset({"ORG-VISIBLE"}))
        masked = self._state_org(org_id="ORG-MASKED", heat=0.9, reach=frozenset({"ORG-VISIBLE"}))
        assert visible["heat"] == pytest.approx(0.3)
        assert masked["heat"] is None

        dashboard = _build_state_apparatus_dashboard(
            WorldState(), [visible, masked], recent_actions=[]
        )

        assert dashboard["total_heat"] == pytest.approx(0.3)
        assert dashboard["heat_orgs_visible"] == 1
        assert dashboard["heat_orgs_masked"] == 1

    def test_all_masked_total_heat_is_none_not_zero(self) -> None:
        from babylon.models.world_state import WorldState
        from game.engine_bridge import _build_state_apparatus_dashboard

        org_a = self._state_org(org_id="ORG-A", heat=0.4, reach=frozenset())
        org_b = self._state_org(org_id="ORG-B", heat=0.6, reach=frozenset())

        dashboard = _build_state_apparatus_dashboard(
            WorldState(), [org_a, org_b], recent_actions=[]
        )

        assert dashboard["total_heat"] is None
        assert dashboard["heat_orgs_visible"] == 0
        assert dashboard["heat_orgs_masked"] == 2

    def test_no_reach_threaded_is_backward_compatible(self) -> None:
        """Existing/unfogged callers (``reach`` never threaded through
        ``_serialize_organization``) keep summing every state org's real
        heat, byte-identical to before this task."""
        from babylon.models.world_state import WorldState
        from game.engine_bridge import _serialize_organization

        org_a = _StubOrg(id="ORG-A", heat=0.4, org_type="state_apparatus")
        org_b = _StubOrg(id="ORG-B", heat=0.6, org_type="state_apparatus")
        organizations = [
            _serialize_organization(o, player_org_id="ORG-PLAYER") for o in (org_a, org_b)
        ]

        from game.engine_bridge import _build_state_apparatus_dashboard

        dashboard = _build_state_apparatus_dashboard(WorldState(), organizations, recent_actions=[])

        assert dashboard["total_heat"] == pytest.approx(1.0)
        assert dashboard["heat_orgs_visible"] == 2
        assert dashboard["heat_orgs_masked"] == 0

    def test_total_repression_budget_unaffected_by_fog_in_every_case(self) -> None:
        """budget is MATERIAL (never in ORG_POLITICAL_FIELDS) — every case
        above must still sum the real budget regardless of heat masking."""
        from babylon.models.world_state import WorldState
        from game.engine_bridge import _build_state_apparatus_dashboard

        all_masked = [
            self._state_org(org_id="ORG-A", heat=0.4, reach=frozenset(), budget=100.0),
            self._state_org(org_id="ORG-B", heat=0.6, reach=frozenset(), budget=200.0),
        ]
        mixed = [
            self._state_org(
                org_id="ORG-VISIBLE",
                heat=0.3,
                reach=frozenset({"ORG-VISIBLE"}),
                budget=150.0,
            ),
            self._state_org(
                org_id="ORG-MASKED",
                heat=0.9,
                reach=frozenset({"ORG-VISIBLE"}),
                budget=250.0,
            ),
        ]

        all_masked_dashboard = _build_state_apparatus_dashboard(
            WorldState(), all_masked, recent_actions=[]
        )
        mixed_dashboard = _build_state_apparatus_dashboard(WorldState(), mixed, recent_actions=[])

        assert all_masked_dashboard["total_repression_budget"] == pytest.approx(300.0)
        assert mixed_dashboard["total_repression_budget"] == pytest.approx(400.0)


class TestGetInspectorNodeOrgPoliticalFields:
    """The generic fallback branch (organization clicked via the raw graph
    dump, not through ``get_inspector_org``) must gate the same way."""

    def _bridge_with_two_orgs(self) -> tuple[Any, Any]:
        from babylon.models.enums import NodeType
        from babylon.topology.graph import BabylonGraph
        from game.engine_bridge import EngineBridge

        graph = BabylonGraph()
        graph.add_node(
            "ORG-PLAYER",
            NodeType.ORGANIZATION,
            id="ORG-PLAYER",
            name="Player Org",
            cohesion=0.5,
            cadre_level=0.2,
            heat=0.1,
            consciousness_tendency="revolutionary",
        )
        graph.add_node(
            "ORG-RIVAL",
            NodeType.ORGANIZATION,
            id="ORG-RIVAL",
            name="Rival Org",
            cohesion=0.8,
            cadre_level=0.6,
            heat=0.3,
            consciousness_tendency="reactionary",
        )
        graph.set_graph_attr("player_org_id", "ORG-PLAYER")

        mock_persistence = MagicMock()
        mock_persistence.hydrate_graph.return_value = graph
        return EngineBridge(mock_persistence), graph

    def test_rival_org_node_gates_internal_state_via_generic_fallback(self) -> None:
        bridge, _graph = self._bridge_with_two_orgs()

        result = bridge.get_inspector_node(uuid.uuid4(), "ORG-RIVAL")

        assert result["cohesion"] is None
        assert result["cadre_level"] is None
        assert result["consciousness_tendency"] is None

    def test_player_org_node_is_fully_visible_via_generic_fallback(self) -> None:
        bridge, _graph = self._bridge_with_two_orgs()

        result = bridge.get_inspector_node(uuid.uuid4(), "ORG-PLAYER")

        assert result["cohesion"] == pytest.approx(0.5)
        assert result["cadre_level"] == pytest.approx(0.2)
        assert result["consciousness_tendency"] == "revolutionary"
