"""Spec-071: SocialClass reactionary fields + graph round-trip.

Adds entitlement / volatility / fascist_alignment / aligned_faction_id to
SocialClass with role-defaulting, and verifies the graph round-trip
preserves them (Common Gotcha: from_graph drops computed/excluded fields).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.config.defines import ReactionaryDefines
from babylon.models import SocialClass, WorldState
from babylon.models.enums import SocialRole

pytestmark = pytest.mark.unit

_R = ReactionaryDefines()


def _make(role: SocialRole, **kw: object) -> SocialClass:
    return SocialClass(id="C001", name="x", role=role, **kw)  # type: ignore[arg-type]


class TestReactionaryFieldDefaults:
    def test_fields_exist_with_zero_defaults_for_neutral_role(self) -> None:
        sc = _make(SocialRole.CORE_BOURGEOISIE)
        assert sc.entitlement == 0.0
        assert sc.volatility == 0.0
        assert sc.fascist_alignment == 0.0
        assert sc.aligned_faction_id is None

    @pytest.mark.parametrize(
        ("role", "expected"),
        [
            (SocialRole.PERIPHERY_PROLETARIAT, _R.entitlement_default_periphery_proletariat),
            (SocialRole.LABOR_ARISTOCRACY, _R.entitlement_default_labor_aristocracy),
            (SocialRole.COMPRADOR_BOURGEOISIE, _R.entitlement_default_comprador_bourgeoisie),
            (SocialRole.LUMPENPROLETARIAT, _R.entitlement_default_lumpenproletariat),
        ],
    )
    def test_entitlement_role_default(self, role: SocialRole, expected: float) -> None:
        assert _make(role).entitlement == pytest.approx(expected)

    def test_volatility_role_default(self) -> None:
        assert _make(SocialRole.LUMPENPROLETARIAT).volatility == pytest.approx(
            _R.volatility_default_lumpenproletariat
        )
        assert _make(SocialRole.LABOR_ARISTOCRACY).volatility == 0.0

    def test_explicit_value_overrides_role_default(self) -> None:
        # An explicitly-set entitlement is NOT overwritten by the role default.
        sc = _make(SocialRole.LABOR_ARISTOCRACY, entitlement=0.3)
        assert sc.entitlement == pytest.approx(0.3)

    def test_intensity_bounds_enforced(self) -> None:
        with pytest.raises(ValidationError):
            _make(SocialRole.LABOR_ARISTOCRACY, fascist_alignment=1.5)
        with pytest.raises(ValidationError):
            _make(SocialRole.LABOR_ARISTOCRACY, volatility=-0.1)


class TestModelConstantsMatchDefines:
    """The role-default maps embedded in the model MUST equal ReactionaryDefines."""

    def test_entitlement_map_matches_defines(self) -> None:
        from babylon.models.entities.social_class import _ENTITLEMENT_DEFAULTS

        assert _ENTITLEMENT_DEFAULTS[SocialRole.PERIPHERY_PROLETARIAT] == (
            _R.entitlement_default_periphery_proletariat
        )
        assert _ENTITLEMENT_DEFAULTS[SocialRole.LABOR_ARISTOCRACY] == (
            _R.entitlement_default_labor_aristocracy
        )
        assert _ENTITLEMENT_DEFAULTS[SocialRole.COMPRADOR_BOURGEOISIE] == (
            _R.entitlement_default_comprador_bourgeoisie
        )

    def test_volatility_map_matches_defines(self) -> None:
        from babylon.models.entities.social_class import _VOLATILITY_DEFAULTS

        assert _VOLATILITY_DEFAULTS[SocialRole.LUMPENPROLETARIAT] == (
            _R.volatility_default_lumpenproletariat
        )


class TestGraphRoundTrip:
    def test_reactionary_fields_survive_round_trip(self) -> None:
        sc = SocialClass(
            id="C001",
            name="la",
            role=SocialRole.LABOR_ARISTOCRACY,
            county_fips="26163",
            entitlement=0.8,
            volatility=0.6,  # non-default (LA role-default is 0.0) — asserted independently below
            fascist_alignment=0.45,
            aligned_faction_id="FAC_SETTLER",
        )
        state = WorldState(tick=0, entities={"C001": sc})
        graph = state.to_graph()
        recovered = WorldState.from_graph(graph, tick=0).entities["C001"]
        assert recovered.entitlement == pytest.approx(0.8)
        assert recovered.volatility == pytest.approx(0.6)
        assert recovered.fascist_alignment == pytest.approx(0.45)
        assert recovered.aligned_faction_id == "FAC_SETTLER"

    def test_none_faction_survives_round_trip(self) -> None:
        sc = SocialClass(id="C001", name="la", role=SocialRole.LABOR_ARISTOCRACY)
        state = WorldState(tick=0, entities={"C001": sc})
        recovered = WorldState.from_graph(state.to_graph(), tick=0).entities["C001"]
        assert recovered.aligned_faction_id is None
        assert recovered.entitlement == pytest.approx(_R.entitlement_default_labor_aristocracy)
