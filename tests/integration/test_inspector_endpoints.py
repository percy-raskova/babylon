"""Spec 061 T087 / FR-019: five inspector endpoints return canonical envelopes.

``EngineBridge`` exposes five inspector methods that frontend pages use
for drill-down detail panels:

- ``inspect_node(session_id, node_id)`` → ``{"node": ..., "collection": ...}``
- ``inspect_org(session_id, org_id)`` → ``{"org": ..., "recent_actions": [...]}``
- ``inspect_community(session_id, community_id)`` → ``{"community": ..., "members": [...]}``
- ``inspect_edge(session_id, source, target, mode)`` → ``{"edge": ..., "history": [...]}``
- ``inspect_hex(session_id, h3_index)`` → ``{"hex": ...}``

Each method currently composes from existing snapshot serializers. The
deeper queries (``query_org_recent_actions``, ``query_edge_history``,
XGI community membership) are stubs returning empty lists — those are
tracked in ``ADR039_spec_061_real_backend_wireup.yaml#follow_up_specs``.

This test pins the *contract envelope shape* — the keys each method
returns. Once the deeper queries land, the inner shapes (``recent_actions``,
``history``, ``members``) will be populated; this test will continue to
pass because it only asserts key presence and rough types.

Gated behind ``mise run test:int`` via ``pytest.mark.integration``
because Django + the engine bridge module are loaded.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import networkx as nx
import pytest

from babylon.engine.graph import BabylonGraph

pytestmark = pytest.mark.integration


def _stub_state_and_graph() -> tuple[Any, nx.DiGraph]:
    """Build a tuple compatible with ``EngineBridge.hydrate_state``'s return.

    The graph is intentionally empty so ``_state_to_snapshot`` produces
    empty collections — this is enough to exercise the inspector envelope
    code paths since the lookups will miss and return None / [].
    """
    from babylon.models.world_state import WorldState

    graph: nx.DiGraph = BabylonGraph()
    graph.graph["tick"] = 0
    state = WorldState.from_graph(graph, tick=0)
    return state, graph


def _make_bridge(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Build an EngineBridge with hydrate_state stubbed to a tiny state."""
    from web.game.engine_bridge import EngineBridge

    persistence = MagicMock()
    bridge = EngineBridge(persistence=persistence)
    monkeypatch.setattr(
        bridge,
        "hydrate_state",
        lambda _session_id, tick=None: _stub_state_and_graph(),  # noqa: ARG005
    )
    return bridge


class TestInspectNode:
    """T087 / FR-019: ``inspect_node`` envelope shape."""

    def test_returns_dict_with_node_and_collection_keys(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        bridge = _make_bridge(monkeypatch)
        payload = bridge.inspect_node(uuid4(), node_id="nonexistent-node")

        assert isinstance(payload, dict)
        assert "node" in payload, f"envelope missing 'node' key: {sorted(payload)}"
        assert "collection" in payload, f"envelope missing 'collection' key: {sorted(payload)}"

    def test_unknown_node_id_returns_null_node(self, monkeypatch: pytest.MonkeyPatch) -> None:
        bridge = _make_bridge(monkeypatch)
        payload = bridge.inspect_node(uuid4(), node_id="ghost-node-xyz")
        assert payload["node"] is None
        assert payload["collection"] is None


class TestInspectOrg:
    """T087 / FR-019: ``inspect_org`` envelope shape."""

    def test_returns_dict_with_org_and_recent_actions(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        bridge = _make_bridge(monkeypatch)
        payload = bridge.inspect_org(uuid4(), org_id="org-doesnt-exist")
        assert isinstance(payload, dict)
        assert "org" in payload, f"envelope missing 'org' key: {sorted(payload)}"
        assert "recent_actions" in payload, (
            f"envelope missing 'recent_actions' key: {sorted(payload)}"
        )

    def test_recent_actions_is_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        bridge = _make_bridge(monkeypatch)
        payload = bridge.inspect_org(uuid4(), org_id="org-xyz")
        assert isinstance(payload["recent_actions"], list), (
            "recent_actions must be a list (currently empty until T092 lands)"
        )


class TestInspectCommunity:
    """T087 / FR-019: ``inspect_community`` envelope shape (no DB call needed)."""

    def test_returns_dict_with_community_and_members(self) -> None:
        from web.game.engine_bridge import EngineBridge

        bridge = EngineBridge(persistence=MagicMock())
        payload = bridge.inspect_community(uuid4(), _community_id="some-community")
        assert isinstance(payload, dict)
        assert "community" in payload
        assert "members" in payload
        assert isinstance(payload["members"], list)


class TestInspectEdge:
    """T087 / FR-019: ``inspect_edge`` envelope shape."""

    def test_returns_dict_with_edge_and_history(self, monkeypatch: pytest.MonkeyPatch) -> None:
        bridge = _make_bridge(monkeypatch)
        payload = bridge.inspect_edge(
            uuid4(),
            source_id="src-x",
            target_id="tgt-y",
            edge_type="EXPLOITATION",
        )
        assert isinstance(payload, dict)
        assert "edge" in payload, f"envelope missing 'edge' key: {sorted(payload)}"
        assert "history" in payload, f"envelope missing 'history' key: {sorted(payload)}"
        assert isinstance(payload["history"], list)


class TestInspectHex:
    """T087 / FR-019: ``inspect_hex`` envelope shape."""

    def test_returns_dict_with_hex_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        bridge = _make_bridge(monkeypatch)
        payload = bridge.inspect_hex(uuid4(), h3_index="8a1fb46622dffff")
        assert isinstance(payload, dict)
        assert "hex" in payload, f"envelope missing 'hex' key: {sorted(payload)}"

    def test_unknown_h3_index_returns_null_hex(self, monkeypatch: pytest.MonkeyPatch) -> None:
        bridge = _make_bridge(monkeypatch)
        payload = bridge.inspect_hex(uuid4(), h3_index="89283082c2bffff")
        assert payload["hex"] is None
