"""Unit tests for ReproductionRequirements computation and stub loader.

Feature: 025-tensor-hierarchy
TDD Phase: GREEN (implementation is complete)
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.tensor import NoDataSentinel
from babylon.domain.economics.tensor_hierarchy.reproduction import (
    DefaultReproductionRequirementsComputer,
    DefaultReproductionSource,
)
from babylon.domain.economics.tensor_hierarchy.types import ReproductionRequirements

# =============================================================================
# Helpers
# =============================================================================


def _make_requirements(
    year: int = 2020,
    consumption: dict[str, dict[str, dict[str, float]]] | None = None,
    reproductive_labor: dict[str, dict[str, dict[str, float]]] | None = None,
) -> ReproductionRequirements:
    """Build a synthetic ReproductionRequirements for testing.

    Args:
        year: Data year.
        consumption: Consumption by class/dept/item. Defaults to a simple
            proletariat structure with housing=5, food=8, clothing=3.
        reproductive_labor: Labor by class pair/type. Defaults to
            proletariat childcare=2 + domestic=4.

    Returns:
        ReproductionRequirements with specified data.
    """
    if consumption is None:
        consumption = {
            "proletariat": {
                "I": {"housing": 5.0, "food": 8.0},
                "IIA": {"clothing": 3.0},
            }
        }
    if reproductive_labor is None:
        reproductive_labor = {
            "proletariat": {
                "proletariat": {"childcare": 2.0, "domestic": 4.0},
            }
        }
    return ReproductionRequirements(
        year=year,
        consumption=consumption,
        reproductive_labor=reproductive_labor,
    )


# =============================================================================
# DefaultReproductionRequirementsComputer tests
# =============================================================================


class TestDefaultReproductionRequirementsComputer:
    """Tests for DefaultReproductionRequirementsComputer."""

    @pytest.fixture()
    def computer(self) -> DefaultReproductionRequirementsComputer:
        """Provide a DefaultReproductionRequirementsComputer instance."""
        return DefaultReproductionRequirementsComputer()

    @pytest.fixture()
    def sample_req(self) -> ReproductionRequirements:
        """Simple single-class ReproductionRequirements fixture."""
        return _make_requirements()

    def test_returns_float(
        self,
        computer: DefaultReproductionRequirementsComputer,
        sample_req: ReproductionRequirements,
    ) -> None:
        """total_reproduction_cost returns a float."""
        result = computer.total_reproduction_cost(sample_req, "proletariat", snlt=0.5)
        assert isinstance(result, float)

    @pytest.mark.math
    def test_hand_calculation(self, computer: DefaultReproductionRequirementsComputer) -> None:
        """total_reproduction_cost matches hand calculation.

        consumption items: housing=5, food=8, clothing=3 → total=16.0 use-value units
        reproductive_labor: childcare=2, domestic=4 → total=6.0 hours
        snlt=0.5 → cost = 16.0 * 0.5 + 6.0 = 8.0 + 6.0 = 14.0
        """
        req = _make_requirements()
        result = computer.total_reproduction_cost(req, "proletariat", snlt=0.5)
        assert result == pytest.approx(14.0)

    @pytest.mark.math
    def test_zero_snlt_only_labor_contributes(
        self, computer: DefaultReproductionRequirementsComputer
    ) -> None:
        """With snlt=0, only reproductive labor hours remain.

        consumption * 0.0 = 0, so only labor hours (2+4=6) count.
        """
        req = _make_requirements()
        result = computer.total_reproduction_cost(req, "proletariat", snlt=0.0)
        assert result == pytest.approx(6.0)

    @pytest.mark.math
    def test_higher_snlt_increases_cost(
        self,
        computer: DefaultReproductionRequirementsComputer,
        sample_req: ReproductionRequirements,
    ) -> None:
        """Higher SNLT increases total cost (consumption costs more)."""
        low = computer.total_reproduction_cost(sample_req, "proletariat", snlt=0.1)
        high = computer.total_reproduction_cost(sample_req, "proletariat", snlt=1.0)
        assert high > low

    def test_unknown_class_returns_zero(
        self,
        computer: DefaultReproductionRequirementsComputer,
        sample_req: ReproductionRequirements,
    ) -> None:
        """Unknown class returns 0.0 (absent from data)."""
        result = computer.total_reproduction_cost(sample_req, "lumpenproletariat", snlt=0.5)
        assert result == pytest.approx(0.0)

    @pytest.mark.math
    def test_multiple_classes_independent(
        self, computer: DefaultReproductionRequirementsComputer
    ) -> None:
        """Each class's cost is computed independently."""
        req = ReproductionRequirements(
            year=2020,
            consumption={
                "proletariat": {"I": {"food": 10.0}},
                "petit_bourgeois": {"IIB": {"luxury": 20.0}},
            },
            reproductive_labor={
                "proletariat": {"proletariat": {"domestic": 5.0}},
                "petit_bourgeois": {},
            },
        )
        # proletariat: 10 * 1.0 + 5 = 15.0
        cost_p = computer.total_reproduction_cost(req, "proletariat", snlt=1.0)
        # petit_bourgeois: 20 * 1.0 + 0 = 20.0
        cost_pb = computer.total_reproduction_cost(req, "petit_bourgeois", snlt=1.0)

        assert cost_p == pytest.approx(15.0)
        assert cost_pb == pytest.approx(20.0)


# =============================================================================
# DefaultReproductionSource stub tests
# =============================================================================


class TestDefaultReproductionSource:
    """Tests for DefaultReproductionSource stub implementation (deferred loader)."""

    @pytest.fixture()
    def source(self) -> DefaultReproductionSource:
        """Provide a DefaultReproductionSource stub instance."""
        return DefaultReproductionSource()

    def test_get_requirements_returns_sentinel(self, source: DefaultReproductionSource) -> None:
        """get_requirements returns NoDataSentinel (CEX loader deferred)."""
        result = source.get_requirements(2022)
        assert isinstance(result, NoDataSentinel)

    def test_sentinel_year_matches_request(self, source: DefaultReproductionSource) -> None:
        """Sentinel year matches requested year."""
        result = source.get_requirements(2019)
        assert isinstance(result, NoDataSentinel)
        assert result.year == 2019

    def test_sentinel_is_falsy(self, source: DefaultReproductionSource) -> None:
        """NoDataSentinel is falsy (bool == False)."""
        result = source.get_requirements(2022)
        assert not result

    def test_sentinel_reason_mentions_cex(self, source: DefaultReproductionSource) -> None:
        """Sentinel reason references CEX data source."""
        result = source.get_requirements(2022)
        assert isinstance(result, NoDataSentinel)
        assert "CEX" in result.reason or "constitutional" in result.reason.lower()

    def test_total_cost_returns_sentinel(self, source: DefaultReproductionSource) -> None:
        """total_reproduction_cost returns NoDataSentinel when data is unavailable."""
        result = source.total_reproduction_cost("proletariat", 2022, snlt=0.5)
        assert isinstance(result, NoDataSentinel)

    def test_total_cost_sentinel_year(self, source: DefaultReproductionSource) -> None:
        """total_reproduction_cost sentinel year matches request."""
        result = source.total_reproduction_cost("proletariat", 2018, snlt=0.5)
        assert isinstance(result, NoDataSentinel)
        assert result.year == 2018
