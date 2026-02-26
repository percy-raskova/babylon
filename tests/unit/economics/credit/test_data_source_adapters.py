"""Tests for concrete FRED data source adapters (Feature 024, T077).

Verifies FredInterestRateAdapter and FredCreditAggregateAdapter
correctly route dict-based lookups and satisfy their respective protocols.
"""

from __future__ import annotations

import pytest

from babylon.economics.credit.data_sources import (
    CreditAggregateSource,
    FredCreditAggregateAdapter,
    FredInterestRateAdapter,
    InterestRateSource,
)


@pytest.mark.unit
class TestFredInterestRateAdapter:
    """Tests for FredInterestRateAdapter."""

    def test_get_federal_funds_rate(self) -> None:
        """Returns fed funds rate from series data."""
        data: dict[str, dict[int, float]] = {"FEDFUNDS": {2020: 0.0036}}
        adapter = FredInterestRateAdapter(data)
        assert adapter.get_federal_funds_rate(2020) == 0.0036

    def test_get_treasury_10y(self) -> None:
        """Returns 10Y treasury rate from series data."""
        data: dict[str, dict[int, float]] = {"DGS10": {2022: 0.0295}}
        adapter = FredInterestRateAdapter(data)
        assert adapter.get_treasury_10y(2022) == 0.0295

    def test_get_baa_spread(self) -> None:
        """Returns Baa spread from series data."""
        data: dict[str, dict[int, float]] = {"BAA10Y": {2008: 0.0349}}
        adapter = FredInterestRateAdapter(data)
        assert adapter.get_baa_spread(2008) == 0.0349

    def test_unknown_year_returns_none(self) -> None:
        """Returns None for year not in series data."""
        data: dict[str, dict[int, float]] = {"FEDFUNDS": {2020: 0.0036}}
        adapter = FredInterestRateAdapter(data)
        assert adapter.get_federal_funds_rate(1999) is None

    def test_missing_series_returns_none(self) -> None:
        """Returns None when series key not in data."""
        adapter = FredInterestRateAdapter({})
        assert adapter.get_federal_funds_rate(2020) is None
        assert adapter.get_treasury_10y(2020) is None
        assert adapter.get_baa_spread(2020) is None

    def test_satisfies_protocol_structurally(self) -> None:
        """Adapter satisfies InterestRateSource protocol structurally.

        Uses static type annotation assignment (same pattern as conftest.py)
        to verify structural protocol compliance without runtime_checkable.
        """
        source: InterestRateSource = FredInterestRateAdapter({})
        assert source.get_federal_funds_rate(2020) is None


@pytest.mark.unit
class TestFredCreditAggregateAdapter:
    """Tests for FredCreditAggregateAdapter."""

    def test_get_total_credit(self) -> None:
        """Returns total credit from series data."""
        data: dict[str, dict[int, float]] = {"TCMDO": {2020: 83_000_000_000_000.0}}
        adapter = FredCreditAggregateAdapter(data)
        assert adapter.get_total_credit(2020) == 83_000_000_000_000.0

    def test_get_government_debt(self) -> None:
        """Returns government debt from series data."""
        data: dict[str, dict[int, float]] = {"GFDEBTN": {2022: 31_000_000_000_000.0}}
        adapter = FredCreditAggregateAdapter(data)
        assert adapter.get_government_debt(2022) == 31_000_000_000_000.0

    def test_get_equity_market_cap(self) -> None:
        """Returns equity market cap from series data."""
        data: dict[str, dict[int, float]] = {"NCBEILQ027S": {2007: 15_000_000_000_000.0}}
        adapter = FredCreditAggregateAdapter(data)
        assert adapter.get_equity_market_cap(2007) == 15_000_000_000_000.0

    def test_unknown_year_returns_none(self) -> None:
        """Returns None for year not in series data."""
        data: dict[str, dict[int, float]] = {"TCMDO": {2020: 83_000_000_000_000.0}}
        adapter = FredCreditAggregateAdapter(data)
        assert adapter.get_total_credit(1999) is None

    def test_missing_series_returns_none(self) -> None:
        """Returns None when series key not in data."""
        adapter = FredCreditAggregateAdapter({})
        assert adapter.get_total_credit(2020) is None
        assert adapter.get_government_debt(2020) is None
        assert adapter.get_equity_market_cap(2020) is None

    def test_satisfies_protocol_structurally(self) -> None:
        """Adapter satisfies CreditAggregateSource protocol structurally.

        Uses static type annotation assignment (same pattern as conftest.py)
        to verify structural protocol compliance without runtime_checkable.
        """
        source: CreditAggregateSource = FredCreditAggregateAdapter({})
        assert source.get_total_credit(2020) is None

    def test_multiple_series_and_years(self) -> None:
        """Adapter handles multiple series with multiple years."""
        data: dict[str, dict[int, float]] = {
            "TCMDO": {2020: 83e12, 2022: 92e12},
            "GFDEBTN": {2020: 27e12, 2022: 31e12},
            "NCBEILQ027S": {2020: 36e12, 2022: 33e12},
        }
        adapter = FredCreditAggregateAdapter(data)
        assert adapter.get_total_credit(2020) == 83e12
        assert adapter.get_total_credit(2022) == 92e12
        assert adapter.get_government_debt(2020) == 27e12
        assert adapter.get_equity_market_cap(2022) == 33e12
