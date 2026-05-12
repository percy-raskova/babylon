"""Spec 061 US4 / T058-T061: organization serializer expansion (FR-011, FR-016).

Tests the bridge ``_serialize_organization`` + ``OrganizationSerializer``
contract:

- T058: ``player_controlled`` flag correctly classifies player vs NPC.
- T059: ``ooda.phase`` enum present and matches argmax over the floats.
- T060: ``short_name`` present, non-empty, ≤16 chars.
- T061: ``hyperedge_memberships`` array present (empty until US6
  XGI-query lands, but always a list, never missing).

Unit-style tests against the bridge helpers — no live DB needed.
"""

from __future__ import annotations

from typing import Any

import pytest
from web.game.engine_bridge import (
    _derive_ooda_phase,
    _derive_short_name,
    _serialize_organization,
)


class _StubOrg:
    """Quacks like an Organization. Exposes only what the bridge reads."""

    def __init__(
        self,
        *,
        id: str = "org-x",
        name: str = "X",
        class_character: str = "proletarian",
        org_type: str = "civil_society",
        cohesion: float = 0.5,
        cadre_level: float = 0.5,
        budget: float = 100.0,
        heat: float = 0.1,
        territory_ids: list[str] | None = None,
        consciousness_tendency: str = "revolutionary",
        legitimacy: float | None = None,
        opacity: float | None = None,
        ooda_profile: Any | None = None,
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
        if legitimacy is not None:
            self.legitimacy = legitimacy
        if opacity is not None:
            self.opacity = opacity
        if ooda_profile is not None:
            self.ooda_profile = ooda_profile


class _OodaStub:
    def __init__(self, observe: float, orient: float, decide: float, act: float) -> None:
        self.observe = observe
        self.orient = orient
        self.decide = decide
        self.act = act


class TestOodaPhaseDerivation:
    """T066 / FR-011: argmax-with-deterministic-tiebreak."""

    def test_observe_dominant(self) -> None:
        assert (
            _derive_ooda_phase({"observe": 0.9, "orient": 0.1, "decide": 0.1, "act": 0.1})
            == "observe"
        )

    def test_act_dominant(self) -> None:
        assert (
            _derive_ooda_phase({"observe": 0.1, "orient": 0.1, "decide": 0.1, "act": 0.9}) == "act"
        )

    def test_tiebreak_prefers_observe(self) -> None:
        """All-equal → first-in-enum-order wins (observe)."""
        assert (
            _derive_ooda_phase({"observe": 0.5, "orient": 0.5, "decide": 0.5, "act": 0.5})
            == "observe"
        )

    def test_partial_tiebreak_prefers_earlier(self) -> None:
        # orient + act tied at 0.7; orient wins (earlier in order).
        assert (
            _derive_ooda_phase({"observe": 0.0, "orient": 0.7, "decide": 0.1, "act": 0.7})
            == "orient"
        )


class TestShortNameDerivation:
    def test_short_name_under_16_chars_passes_through(self) -> None:
        assert _derive_short_name("Wayne Workers") == "Wayne Workers"

    def test_short_name_long_name_truncates_with_ellipsis(self) -> None:
        result = _derive_short_name("The Continental Workers' Solidarity League")
        assert len(result) == 16
        assert result.endswith("…")

    def test_short_name_empty_returns_empty(self) -> None:
        assert _derive_short_name("") == ""


class TestSerializedOrgShape:
    """T058-T061: spec 061 fields present on every serialized org."""

    def test_player_controlled_flag_correct_for_player_org(self) -> None:
        org = _StubOrg(class_character="proletarian", org_type="civil_society")
        out = _serialize_organization(org)
        assert out["player_controlled"] is True
        assert out["vanguard"] is not None  # T058 corollary

    def test_player_controlled_flag_correct_for_npc_org(self) -> None:
        org = _StubOrg(class_character="bourgeois", org_type="business")
        out = _serialize_organization(org)
        assert out["player_controlled"] is False
        assert out["vanguard"] is None

    def test_ooda_phase_enum_present(self) -> None:
        org = _StubOrg(ooda_profile=_OodaStub(observe=0.1, orient=0.1, decide=0.7, act=0.1))
        out = _serialize_organization(org)
        assert out["ooda"]["phase"] == "decide"
        assert out["ooda"]["phase"] in ("observe", "orient", "decide", "act")

    def test_short_name_present_and_bounded(self) -> None:
        org = _StubOrg(name="A Reasonable Org Name")
        out = _serialize_organization(org)
        assert out["short_name"] != ""
        assert len(out["short_name"]) <= 16

    def test_hyperedge_memberships_always_a_list(self) -> None:
        org = _StubOrg()
        out = _serialize_organization(org)
        assert isinstance(out["hyperedge_memberships"], list)
        # US6 will populate; for now empty is a valid empty contract.

    def test_legitimacy_and_opacity_fields_present(self) -> None:
        org = _StubOrg(legitimacy=0.73, opacity=0.21)
        out = _serialize_organization(org)
        assert out["legitimacy"] == pytest.approx(0.73)
        assert out["opacity"] == pytest.approx(0.21)

    def test_legitimacy_defaults_to_half_when_attribute_absent(self) -> None:
        org = _StubOrg()  # no legitimacy attribute
        out = _serialize_organization(org)
        assert out["legitimacy"] == 0.5
        assert out["opacity"] == 0.5
