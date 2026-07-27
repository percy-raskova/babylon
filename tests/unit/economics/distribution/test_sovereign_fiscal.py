"""Behavioral contract for the sovereign fiscal ledger (P25 U9, ADR135).

``debt_service`` is the BUILD half of the funding identity: the endogenous
interest RATE was live (Vol III, ADR089) but no sovereign debt STOCK existed
anywhere — ``DebtAccumulation`` is the county-ENTERPRISE deficit model and is
never constructed in production. These laws are pure: rate × stock service,
the bond-discipline serviceability tightener, and deficit financing of the
unfunded social-wage shortfall (O'Connor's fiscal crisis as arithmetic).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.domain.economics.distribution.sovereign_fiscal import (
    SovereignFiscalState,
    bond_discipline_binds,
    borrow,
    finance_shortfall,
    sovereign_debt_service,
)

pytestmark = pytest.mark.unit


class TestSovereignDebtService:
    def test_service_is_rate_times_stock(self) -> None:
        assert sovereign_debt_service(1000.0, 0.05) == pytest.approx(50.0)

    def test_zero_stock_means_zero_service(self) -> None:
        assert sovereign_debt_service(0.0, 0.08) == 0.0

    def test_negative_inputs_floor_to_zero(self) -> None:
        assert sovereign_debt_service(-100.0, 0.05) == 0.0
        assert sovereign_debt_service(100.0, -0.05) == 0.0


class TestBondDiscipline:
    def test_binds_when_service_ratio_exceeds_threshold(self) -> None:
        assert bond_discipline_binds(30.0, 100.0, threshold=0.25) is True

    def test_slack_below_threshold(self) -> None:
        assert bond_discipline_binds(10.0, 100.0, threshold=0.25) is False

    def test_zero_service_never_binds(self) -> None:
        assert bond_discipline_binds(0.0, 0.0, threshold=0.25) is False

    def test_no_tax_base_with_live_service_binds(self) -> None:
        """A sovereign with debt service and no tax claim cannot borrow —
        the ratio is undefined, the discipline is total."""
        assert bond_discipline_binds(5.0, 0.0, threshold=0.25) is True


class TestFinanceShortfall:
    def test_disciplined_borrowing_is_zero(self) -> None:
        assert finance_shortfall(40.0, 0.5, disciplined=True) == 0.0

    def test_undisciplined_borrows_the_share(self) -> None:
        assert finance_shortfall(40.0, 0.5, disciplined=False) == pytest.approx(20.0)

    def test_negative_shortfall_floors_to_zero(self) -> None:
        assert finance_shortfall(-10.0, 0.5, disciplined=False) == 0.0


class TestSovereignFiscalState:
    def test_borrow_accumulates_the_stock(self) -> None:
        state = SovereignFiscalState(sovereign_id="SOV_USA_FED")
        grown = borrow(state, 20.0)
        assert grown.debt_stock == pytest.approx(20.0)
        assert grown.last_borrowed == pytest.approx(20.0)
        again = borrow(grown, 5.0)
        assert again.debt_stock == pytest.approx(25.0)
        assert again.last_borrowed == pytest.approx(5.0)

    def test_state_is_frozen_and_bounded(self) -> None:
        state = SovereignFiscalState(sovereign_id="SOV_USA_FED", debt_stock=1.0)
        with pytest.raises(ValidationError):
            state.debt_stock = 2.0  # type: ignore[misc]
        with pytest.raises(ValidationError):
            SovereignFiscalState(sovereign_id="SOV_USA_FED", debt_stock=-1.0)

    def test_round_trips_through_model_dump(self) -> None:
        """The state is carried in a graph-attr register (the
        opposition_states durability class) — dict round-trip is the
        serialization contract."""
        state = SovereignFiscalState(sovereign_id="SOV_USA_FED", debt_stock=7.5, last_borrowed=2.5)
        assert SovereignFiscalState.model_validate(state.model_dump()) == state
