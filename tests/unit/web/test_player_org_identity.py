"""Track 1 / Task 1 (2026-07-18): ``WorldState.player_org_id`` is canonical.

Two conflicting "is this the player org" definitions used to coexist with
nothing enforcing they agreed:

(a) ``WorldState.player_org_id`` (``src/babylon/models/world_state.py:461``)
    — explicit, already relied on engine-side by
    ``EpistemicHorizonSystem``/``DoctrineSystem``.
(b) A structural heuristic (``class_character == "proletarian" and
    org_type == "civil_society"``), duplicated verbatim in
    ``_serialize_organization`` and ``get_inspector_org``
    (``web/game/engine_bridge.py``, prior to this fix) — a stopgap for the
    missing engine-side ``controlling_player_id`` link.

These tests construct the exact divergence the fix closes: a "player org"
that does NOT match the retired heuristic, and an org that DOES match the
heuristic but is NOT the player org. Only ``player_org_id`` may win.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


class _StubOrg:
    """Quacks like an Organization — exposes only what
    ``_serialize_organization`` reads."""

    def __init__(
        self,
        *,
        id: str,
        class_character: str,
        org_type: str,
        name: str = "Stub Org",
        cohesion: float = 0.5,
        cadre_level: float = 0.5,
        budget: float = 100.0,
        heat: float = 0.1,
        territory_ids: list[str] | None = None,
        consciousness_tendency: str = "liberal",
    ) -> None:
        self.id = id
        self.name = name
        self.class_character = class_character
        self.org_type = org_type
        self.cohesion = cohesion
        self.cadre_level = cadre_level
        self.budget = budget
        self.heat = heat
        self.territory_ids = territory_ids or []
        self.consciousness_tendency = consciousness_tendency


class TestSerializeOrganizationUsesPlayerOrgId:
    """``_serialize_organization`` must key off ``player_org_id``, never the
    retired structural heuristic."""

    def test_player_org_id_wins_even_when_it_does_not_match_heuristic(self) -> None:
        """The canonical player org here is bourgeois/business — it would
        FAIL the retired heuristic — yet must still resolve as player-
        controlled because it is named by ``player_org_id``."""
        from game.engine_bridge import _serialize_organization

        org = _StubOrg(id="ORG-PLAYER", class_character="bourgeois", org_type="business")

        out = _serialize_organization(org, player_org_id="ORG-PLAYER")

        assert out["player_controlled"] is True
        assert out["vanguard"] is not None

    def test_heuristic_match_alone_is_not_enough(self) -> None:
        """This org matches the retired heuristic exactly
        (proletarian/civil_society) but is NOT ``player_org_id`` — it must
        NOT be treated as player-controlled. This is the exact divergence
        nothing used to prevent."""
        from game.engine_bridge import _serialize_organization

        org = _StubOrg(id="ORG-HEURISTIC", class_character="proletarian", org_type="civil_society")

        out = _serialize_organization(org, player_org_id="ORG-PLAYER")

        assert out["player_controlled"] is False
        assert out["vanguard"] is None

    def test_absent_player_org_id_is_not_a_fallback_to_the_heuristic(self) -> None:
        """``player_org_id=None`` is a legitimate sentinel (synthetic
        scenarios, headless sweeps — world_state.py:467-469), not a signal
        to fall back on the structural guess. Every org resolves to
        non-player-controlled, even one that matches the heuristic."""
        from game.engine_bridge import _serialize_organization

        org = _StubOrg(id="ORG-HEURISTIC", class_character="proletarian", org_type="civil_society")

        out = _serialize_organization(org, player_org_id=None)

        assert out["player_controlled"] is False
        assert out["vanguard"] is None


class TestGetInspectorOrgUsesPlayerOrgId:
    """``get_inspector_org`` must resolve player-org status from graph
    metadata (``WorldState.player_org_id``), never the retired heuristic."""

    def _bridge_with_divergent_orgs(self, *, set_player_org_id: bool) -> tuple[Any, Any]:
        from babylon.models.enums import NodeType
        from babylon.topology.graph import BabylonGraph
        from game.engine_bridge import EngineBridge

        graph = BabylonGraph()
        # The canonical player org — does NOT match the retired heuristic
        # (bourgeois/business, not proletarian/civil_society).
        graph.add_node(
            "ORG-PLAYER",
            NodeType.ORGANIZATION,
            id="ORG-PLAYER",
            name="Player Org",
            class_character="bourgeois",
            org_type="business",
            legal_standing="registered",
            consciousness_tendency="liberal",
            cohesion=0.5,
            cadre_level=0.5,
            budget=100.0,
            heat=0.1,
            territory_ids=[],
            sector="stub-sector",
        )
        # Matches the retired heuristic exactly but is NOT the player org.
        graph.add_node(
            "ORG-HEURISTIC",
            NodeType.ORGANIZATION,
            id="ORG-HEURISTIC",
            name="Heuristic-Matching Org",
            class_character="proletarian",
            org_type="civil_society",
            legal_standing="registered",
            consciousness_tendency="revolutionary",
            cohesion=0.5,
            cadre_level=0.5,
            budget=100.0,
            heat=0.1,
            territory_ids=[],
            service_type="labor",
        )
        if set_player_org_id:
            graph.set_graph_attr("player_org_id", "ORG-PLAYER")

        mock_persistence = MagicMock()
        mock_persistence.hydrate_graph.return_value = graph
        return EngineBridge(mock_persistence), graph

    def test_player_org_id_wins_even_when_it_does_not_match_heuristic(self) -> None:
        bridge, _graph = self._bridge_with_divergent_orgs(set_player_org_id=True)

        result = bridge.get_inspector_org(uuid.uuid4(), "ORG-PLAYER")

        assert result["vanguard"] is not None

    def test_heuristic_match_alone_is_not_enough(self) -> None:
        bridge, _graph = self._bridge_with_divergent_orgs(set_player_org_id=True)

        result = bridge.get_inspector_org(uuid.uuid4(), "ORG-HEURISTIC")

        assert result["vanguard"] is None
        assert result["traps"] is None

    def test_absent_player_org_id_is_not_a_fallback_to_the_heuristic(self) -> None:
        """No ``player_org_id`` set at all (legitimate no-player session,
        world_state.py:467-469) — the heuristic-matching org must still
        resolve as non-player-controlled."""
        bridge, _graph = self._bridge_with_divergent_orgs(set_player_org_id=False)

        result = bridge.get_inspector_org(uuid.uuid4(), "ORG-HEURISTIC")

        assert result["vanguard"] is None
        assert result["traps"] is None
