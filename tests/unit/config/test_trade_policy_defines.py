"""GameDefines.trade_policy contract — tariff/duty/tax START values.

P26 U5f (ADR165 Director directive): tariff rates, import duties, and trade
taxes are instruments of the international trade system, adjusted via the
Policy system (LEGISLATE @17.47) and electoral outcomes post-init. Every
field here defaults to 0.0/``{}`` so a fresh campaign with no tariff
LEGISLATE motions ever drafted is byte-identical to pre-U5f behavior
(default-inert law).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.config.defines import GameDefines, TradePolicyDefines

pytestmark = pytest.mark.unit


class TestTradePolicyDefaults:
    def test_tariff_rates_default_to_empty(self) -> None:
        d = TradePolicyDefines()
        assert d.tariff_rates == {}

    def test_national_scalars_default_to_zero(self) -> None:
        d = TradePolicyDefines()
        assert d.import_duty_rate == 0.0
        assert d.trade_tax_rate == 0.0

    def test_dampening_coefficient_default_is_bounded(self) -> None:
        d = TradePolicyDefines()
        assert 0.0 <= d.tariff_dampening_coefficient <= 1.0

    def test_reachable_from_game_defines(self) -> None:
        defines = GameDefines.load_default()
        assert defines.trade_policy.tariff_rates == {}
        assert defines.trade_policy.import_duty_rate == 0.0
        assert defines.trade_policy.trade_tax_rate == 0.0


class TestTradePolicyBounds:
    @pytest.mark.parametrize(
        "field", ["import_duty_rate", "trade_tax_rate", "tariff_dampening_coefficient"]
    )
    def test_negative_is_rejected(self, field: str) -> None:
        with pytest.raises(ValidationError, match=field):
            TradePolicyDefines(**{field: -0.1})

    @pytest.mark.parametrize(
        "field", ["import_duty_rate", "trade_tax_rate", "tariff_dampening_coefficient"]
    )
    def test_above_one_is_rejected(self, field: str) -> None:
        with pytest.raises(ValidationError, match=field):
            TradePolicyDefines(**{field: 1.5})

    def test_tariff_rates_reject_out_of_range_values(self) -> None:
        with pytest.raises(ValidationError, match="tariff_rates"):
            TradePolicyDefines(tariff_rates={"china": 1.5})

    def test_tariff_rates_reject_negative_values(self) -> None:
        with pytest.raises(ValidationError, match="tariff_rates"):
            TradePolicyDefines(tariff_rates={"canada": -0.01})

    def test_tariff_rates_accept_valid_map(self) -> None:
        d = TradePolicyDefines(tariff_rates={"china": 0.25, "eu": 0.1})
        assert d.tariff_rates == {"china": 0.25, "eu": 0.1}


class TestTradePolicyFrozen:
    def test_model_is_frozen(self) -> None:
        d = TradePolicyDefines()
        with pytest.raises(ValidationError):
            d.import_duty_rate = 0.5  # type: ignore[misc]
