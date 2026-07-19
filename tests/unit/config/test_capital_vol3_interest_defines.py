"""U9.2: the four endogenous-interest coefficients and their base<ceiling<1
invariant (Capital Vol. III ch. 22 — interest is a share of profit)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.config.defines.capital_vol3 import CapitalVolumeIIIDefines


@pytest.mark.unit
class TestInterestDefines:
    def test_defaults_are_the_calibrated_values(self) -> None:
        d = CapitalVolumeIIIDefines()
        assert d.interest_profit_share_base == pytest.approx(0.30)
        assert d.interest_profit_share_ceiling == pytest.approx(0.95)
        assert d.interest_reserve_demand_gain == pytest.approx(1.0)
        assert d.interest_reserve_reference == pytest.approx(0.08)

    def test_base_must_be_below_ceiling(self) -> None:
        with pytest.raises(ValidationError, match="interest_profit_share_base"):
            CapitalVolumeIIIDefines(
                interest_profit_share_base=0.96,
                interest_profit_share_ceiling=0.95,
            )
