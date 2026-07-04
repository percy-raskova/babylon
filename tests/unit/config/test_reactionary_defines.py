"""Spec-071: ReactionaryDefines contract tests.

Verifies the new reactionary coefficient category is wired into GameDefines
with all theory-derived defaults (Constitution III.1 — no magic numbers in
systems; every numeric traces to project/03-next-spec-071.md).
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines, ReactionaryDefines

pytestmark = pytest.mark.unit


class TestReactionaryDefinesWiring:
    def test_gamedefines_exposes_reactionary(self) -> None:
        defines = GameDefines()
        assert isinstance(defines.reactionary, ReactionaryDefines)

    def test_defaults_match_catalog(self) -> None:
        r = ReactionaryDefines()
        assert r.fascist_pull_threshold == 1.0
        assert r.fascist_drift_step == 0.05
        assert r.fascist_recruitment_threshold == 1.0
        assert r.solidarity_pull_epsilon == 0.1
        assert r.chauvinism_base_rate == 0.01
        assert r.chauvinism_superwage_bonus == 0.02
        assert r.red_brown_coup_fraction == 0.5

    def test_entitlement_and_volatility_defaults(self) -> None:
        r = ReactionaryDefines()
        assert r.entitlement_default_periphery_proletariat == 0.2
        assert r.entitlement_default_labor_aristocracy == 0.8
        assert r.entitlement_default_comprador_bourgeoisie == 0.7
        assert r.entitlement_default_lumpenproletariat == 0.0
        assert r.volatility_default_lumpenproletariat == 0.8

    def test_frozen(self) -> None:
        r = ReactionaryDefines()
        with pytest.raises((TypeError, ValueError)):
            r.fascist_drift_step = 0.9  # type: ignore[misc]

    def test_yaml_override_roundtrips(self) -> None:
        # ReactionaryDefines must accept an override dict like every other category.
        r = ReactionaryDefines(fascist_drift_step=0.1)
        assert r.fascist_drift_step == 0.1
