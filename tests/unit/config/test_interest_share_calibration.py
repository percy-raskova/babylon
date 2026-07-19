"""U9.9: FRED is now CALIBRATION, not a runtime input — this test is the
durable spec (Constitution III.12) that interest_profit_share_base tracks the
real net-interest / profit ratio. If the coefficient is regenerated it is
re-checked against data, not vibes."""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines


@pytest.mark.unit
def test_base_share_matches_the_fred_net_interest_to_profit_band() -> None:
    base = GameDefines.load_default().capital_vol3.interest_profit_share_base
    # FRED W273RC1 / A053RC1Q027SBEA calm-year band (design §1.3): 0.25-0.35.
    assert 0.25 <= base <= 0.35
