"""U9.6: the endogenous interest rate rides the NationalFinancialParameters
seam and survives the graph round-trip."""

from __future__ import annotations

import pytest

from babylon.domain.economics.credit.types import EndogenousInterestRate
from babylon.domain.economics.tick.graph_bridge import (
    read_national_financial_state_from_graph,
    write_national_financial_state_to_graph,
)
from babylon.domain.economics.tick.types import NationalFinancialParameters
from babylon.topology import BabylonGraph


@pytest.mark.unit
class TestEndogenousInterestSeam:
    def test_empty_has_no_endogenous_interest(self) -> None:
        assert NationalFinancialParameters.empty().endogenous_interest is None

    def test_round_trip_preserves_the_endogenous_rate(self) -> None:
        eir = EndogenousInterestRate(
            year=2015,
            profit_rate_ceiling=0.15,
            rate=0.06,
            fragility_premium=0.015,
            tightness=0.3,
            reserve_army_signal=0.3,
        )
        params = NationalFinancialParameters(endogenous_interest=eir)
        g = BabylonGraph()
        write_national_financial_state_to_graph(g, params)
        back = read_national_financial_state_from_graph(g)
        assert back is not None
        assert back.endogenous_interest is not None
        assert back.endogenous_interest.rate == pytest.approx(0.06)
        assert back.endogenous_interest.rate < back.endogenous_interest.profit_rate_ceiling
