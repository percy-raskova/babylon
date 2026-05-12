"""Spec 061 T086 / FR-018: communities dashboard returns canonical envelope.

``EngineBridge.get_communities_dashboard()`` is currently a stub that
emits ``{"communities": []}`` until the deeper XGI-membership query
lands in a follow-up spec (see ADR039 ``follow_up_specs``).

This test pins the *contract envelope shape* — the returned object is a
dict with a ``communities`` key whose value is a list. Each list entry,
when present, must match ``contracts/communities.yaml``:

    {
        "hyperedge_id": str,
        "category": str,
        "member_count": int,
        "ternary": {"reformist": float, "revolutionary": float, "fascist": float},
    }

Because the current implementation returns an empty list, the entry-shape
assertion is conditional. The contract test still catches regressions
where the *envelope* would drift (e.g., key renamed, list replaced with
dict, list of strings instead of objects).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

pytestmark = pytest.mark.integration


def _make_bridge() -> Any:
    """Create an EngineBridge with a mocked persistence layer.

    The communities dashboard does not currently call into persistence,
    so a bare mock is sufficient.
    """
    from web.game.engine_bridge import EngineBridge

    persistence = MagicMock()
    return EngineBridge(persistence=persistence)


class TestCommunitiesEnvelope:
    """FR-018: dashboard envelope is stable across the v2 → live cutover."""

    def test_returns_dict_with_communities_key(self) -> None:
        bridge = _make_bridge()
        payload = bridge.get_communities_dashboard(uuid4())
        assert isinstance(payload, dict), f"expected dict, got {type(payload).__name__}"
        assert "communities" in payload, (
            f"envelope must expose 'communities' key; got keys={sorted(payload)}"
        )

    def test_communities_value_is_list(self) -> None:
        bridge = _make_bridge()
        payload = bridge.get_communities_dashboard(uuid4())
        assert isinstance(payload["communities"], list), (
            f"'communities' must be a list, got {type(payload['communities']).__name__}"
        )

    def test_empty_list_is_acceptable_for_stub(self) -> None:
        """The stub may return an empty list; an empty list is valid per
        the contract — frontends render a "no communities surfaced"
        empty state. This test pins the current behavior; replace the
        assertion when the deeper XGI-membership query lands."""
        bridge = _make_bridge()
        payload = bridge.get_communities_dashboard(uuid4())
        assert payload["communities"] == [], (
            "stub currently returns []; if this fails, "
            "the deeper community query has landed and "
            "test_each_entry_matches_contract_shape below should be "
            "promoted to an unconditional check"
        )

    def test_each_entry_matches_contract_shape(self) -> None:
        """If the stub is replaced and returns real entries, each must
        match the OpenAPI shape in contracts/communities.yaml."""
        bridge = _make_bridge()
        payload = bridge.get_communities_dashboard(uuid4())
        for entry in payload["communities"]:
            assert isinstance(entry, dict), "each community entry must be a dict"
            assert "hyperedge_id" in entry, f"entry missing hyperedge_id: {entry!r}"
            assert "category" in entry, f"entry missing category: {entry!r}"
            assert "member_count" in entry, f"entry missing member_count: {entry!r}"
            assert "ternary" in entry, f"entry missing ternary: {entry!r}"
            ternary = entry["ternary"]
            assert isinstance(ternary, dict)
            for key in ("reformist", "revolutionary", "fascist"):
                assert key in ternary, f"ternary missing {key}: {ternary!r}"
                assert isinstance(ternary[key], (int, float)), (
                    f"ternary.{key} must be numeric, got {type(ternary[key]).__name__}"
                )
