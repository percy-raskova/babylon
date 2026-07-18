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
