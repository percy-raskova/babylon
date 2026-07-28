"""GameDefines.transport contract — Transport Substrate coefficients.

Spec-108 (Constitution II.13/Amendment O) slice 1, T5. Program-11's own
constraint governs ``enabled``: "defines-gated... default OFF -> baselines
byte-identical." Every other field is inert while ``enabled`` is ``False``
(engine-side: :class:`~babylon.engine.systems.transport.TransportSystem`
no-ops on the master gate).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.config.defines import GameDefines, TransportDefines

pytestmark = pytest.mark.unit


class TestTransportDefaults:
    def test_master_gate_defaults_off(self) -> None:
        d = TransportDefines()
        assert d.enabled is False

    def test_defaults_are_present_and_positive(self) -> None:
        d = TransportDefines()
        assert d.condition_decay_rate_per_tick > 0.0
        assert d.condition_decay_flux_coefficient > 0.0
        assert d.maintenance_condition_restore_rate > 0.0
        assert d.construction_base_condition == pytest.approx(1.0)
        assert 0.0 < d.state_maintenance_budget_share < 1.0
        assert 0.0 < d.conductivity_ema_alpha <= 1.0
        assert d.demand_signal_threshold >= 0.0
        assert d.attack_splash_condition_damage > 0.0
        assert d.build_splash_condition_repair > 0.0

    def test_reachable_from_game_defines(self) -> None:
        defines = GameDefines.load_default()
        assert defines.transport.enabled is False


class TestTransportBounds:
    @pytest.mark.parametrize(
        "field",
        [
            "condition_decay_rate_per_tick",
            "condition_decay_flux_coefficient",
            "maintenance_condition_restore_rate",
            "attack_splash_condition_damage",
            "build_splash_condition_repair",
        ],
    )
    def test_negative_is_rejected(self, field: str) -> None:
        with pytest.raises(ValidationError, match=field):
            TransportDefines(**{field: -0.1})

    @pytest.mark.parametrize(
        "field",
        ["construction_base_condition", "state_maintenance_budget_share", "conductivity_ema_alpha"],
    )
    def test_fractions_reject_above_one(self, field: str) -> None:
        with pytest.raises(ValidationError, match=field):
            TransportDefines(**{field: 1.5})

    def test_condition_decay_rate_alone_cannot_exceed_one_per_tick(self) -> None:
        """A rate >= 1.0 would zero condition in a single tick regardless of
        flux -- a config footgun caught at construction (III.11), not
        discovered mid-campaign."""
        with pytest.raises(ValidationError, match="condition_decay_rate_per_tick"):
            TransportDefines(condition_decay_rate_per_tick=1.0)
