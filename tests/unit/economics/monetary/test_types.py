"""Tests for monetary type definitions (MonetaryAdjustment).

Feature: 024-capital-volume-iii (US7, FR-013)
TDD Red Phase: Tests define expected behavior for the MonetaryAdjustment model.

MonetaryAdjustment: conversion factors between value bases for a given year.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.economics.monetary.types import MonetaryAdjustment

# =============================================================================
# MonetaryAdjustment
# =============================================================================


@pytest.mark.unit
class TestMonetaryAdjustmentFrozen:
    """MonetaryAdjustment must be immutable (frozen Pydantic model)."""

    def test_frozen_model_rejects_mutation(self) -> None:
        """Attempting to mutate a field raises ValidationError."""
        adj = MonetaryAdjustment(
            year=2020,
            cpi_index=258.81,
            gdp_deflator=113.648,
            snlt_per_dollar=1.11e-5,
            base_year=2010,
        )
        with pytest.raises(ValidationError):
            adj.cpi_index = 300.0  # type: ignore[misc]


@pytest.mark.unit
class TestMonetaryAdjustmentFields:
    """MonetaryAdjustment field validation."""

    def test_valid_construction(self) -> None:
        """Normal construction with all required fields succeeds."""
        adj = MonetaryAdjustment(
            year=2020,
            cpi_index=258.81,
            gdp_deflator=113.648,
            snlt_per_dollar=1.11e-5,
            base_year=2010,
        )
        assert adj.year == 2020
        assert adj.cpi_index == pytest.approx(258.81)
        assert adj.gdp_deflator == pytest.approx(113.648)
        assert adj.snlt_per_dollar == pytest.approx(1.11e-5)
        assert adj.base_year == 2010

    def test_zero_cpi_rejected(self) -> None:
        """CPI index of zero is rejected by gt=0 constraint."""
        with pytest.raises(ValidationError, match="cpi_index"):
            MonetaryAdjustment(
                year=2020,
                cpi_index=0.0,
                gdp_deflator=113.648,
                snlt_per_dollar=1.11e-5,
                base_year=2010,
            )

    def test_negative_cpi_rejected(self) -> None:
        """Negative CPI index is rejected by gt=0 constraint."""
        with pytest.raises(ValidationError, match="cpi_index"):
            MonetaryAdjustment(
                year=2020,
                cpi_index=-10.0,
                gdp_deflator=113.648,
                snlt_per_dollar=1.11e-5,
                base_year=2010,
            )

    def test_zero_deflator_rejected(self) -> None:
        """GDP deflator of zero is rejected by gt=0 constraint."""
        with pytest.raises(ValidationError, match="gdp_deflator"):
            MonetaryAdjustment(
                year=2020,
                cpi_index=258.81,
                gdp_deflator=0.0,
                snlt_per_dollar=1.11e-5,
                base_year=2010,
            )

    def test_negative_deflator_rejected(self) -> None:
        """Negative GDP deflator is rejected by gt=0 constraint."""
        with pytest.raises(ValidationError, match="gdp_deflator"):
            MonetaryAdjustment(
                year=2020,
                cpi_index=258.81,
                gdp_deflator=-5.0,
                snlt_per_dollar=1.11e-5,
                base_year=2010,
            )

    def test_zero_snlt_rejected(self) -> None:
        """SNLT per dollar of zero is rejected by gt=0 constraint."""
        with pytest.raises(ValidationError, match="snlt_per_dollar"):
            MonetaryAdjustment(
                year=2020,
                cpi_index=258.81,
                gdp_deflator=113.648,
                snlt_per_dollar=0.0,
                base_year=2010,
            )

    def test_negative_snlt_rejected(self) -> None:
        """Negative SNLT per dollar is rejected by gt=0 constraint."""
        with pytest.raises(ValidationError, match="snlt_per_dollar"):
            MonetaryAdjustment(
                year=2020,
                cpi_index=258.81,
                gdp_deflator=113.648,
                snlt_per_dollar=-0.001,
                base_year=2010,
            )

    def test_year_below_minimum_rejected(self) -> None:
        """Year below 2007 is rejected by ge constraint."""
        with pytest.raises(ValidationError, match="year"):
            MonetaryAdjustment(
                year=2006,
                cpi_index=258.81,
                gdp_deflator=113.648,
                snlt_per_dollar=1.11e-5,
                base_year=2010,
            )

    def test_base_year_above_maximum_rejected(self) -> None:
        """Base year above 2040 is rejected by le constraint."""
        with pytest.raises(ValidationError, match="base_year"):
            MonetaryAdjustment(
                year=2020,
                cpi_index=258.81,
                gdp_deflator=113.648,
                snlt_per_dollar=1.11e-5,
                base_year=2041,
            )
