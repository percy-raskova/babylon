"""Unit tests for economic institution scenarios (Feature 040, US4).

Validates:
- SC-008: ECONOMIC_PRODUCTIVE (Ford Motor Company) with EMPLOYMENT function
- ECONOMIC_FINANCIAL and ECONOMIC_EXTRACTIVE subtypes
- Class inscription BOURGEOIS for economic institutions
"""

from __future__ import annotations

import pytest

from babylon.models.enums import (
    ApparatusType,
    ClassInscription,
    SocialFunction,
)

from .conftest import make_institution, make_reproduction


class TestEconomicProductive:
    """SC-008: Ford Motor Company as ECONOMIC_PRODUCTIVE."""

    def test_apparatus_type(self) -> None:
        """Ford should be ECONOMIC_PRODUCTIVE."""
        ford = make_institution(
            id="ford_motor",
            name="Ford Motor Company",
            apparatus_type=ApparatusType.ECONOMIC_PRODUCTIVE,
            social_function=SocialFunction.EMPLOYMENT,
            class_inscription=ClassInscription.BOURGEOIS,
            jurisdiction=None,
            territory_ids=["T001"],
        )
        assert ford.apparatus_type == ApparatusType.ECONOMIC_PRODUCTIVE

    def test_social_function_employment(self) -> None:
        """Ford should have EMPLOYMENT social function."""
        ford = make_institution(
            id="ford_motor",
            name="Ford Motor Company",
            apparatus_type=ApparatusType.ECONOMIC_PRODUCTIVE,
            social_function=SocialFunction.EMPLOYMENT,
            class_inscription=ClassInscription.BOURGEOIS,
            jurisdiction=None,
        )
        assert ford.social_function == SocialFunction.EMPLOYMENT

    def test_class_inscription_bourgeois(self) -> None:
        """Economic productive should be BOURGEOIS inscription."""
        ford = make_institution(
            id="ford_motor",
            name="Ford Motor Company",
            apparatus_type=ApparatusType.ECONOMIC_PRODUCTIVE,
            social_function=SocialFunction.EMPLOYMENT,
            class_inscription=ClassInscription.BOURGEOIS,
            jurisdiction=None,
        )
        assert ford.class_inscription == ClassInscription.BOURGEOIS

    def test_no_jurisdiction(self) -> None:
        """Economic institution should not have jurisdiction."""
        ford = make_institution(
            id="ford_motor",
            name="Ford Motor Company",
            apparatus_type=ApparatusType.ECONOMIC_PRODUCTIVE,
            social_function=SocialFunction.EMPLOYMENT,
            class_inscription=ClassInscription.BOURGEOIS,
            jurisdiction=None,
        )
        assert ford.jurisdiction is None


class TestEconomicFinancial:
    """ECONOMIC_FINANCIAL subtype."""

    def test_financial_apparatus_type(self) -> None:
        """Bank should be ECONOMIC_FINANCIAL."""
        bank = make_institution(
            id="jpmorgan",
            name="JPMorgan Chase",
            apparatus_type=ApparatusType.ECONOMIC_FINANCIAL,
            social_function=SocialFunction.FINANCIAL_INTERMEDIATION,
            class_inscription=ClassInscription.BOURGEOIS,
            jurisdiction=None,
        )
        assert bank.apparatus_type == ApparatusType.ECONOMIC_FINANCIAL

    def test_financial_social_function(self) -> None:
        """Bank should have FINANCIAL_INTERMEDIATION social function."""
        bank = make_institution(
            id="jpmorgan",
            name="JPMorgan Chase",
            apparatus_type=ApparatusType.ECONOMIC_FINANCIAL,
            social_function=SocialFunction.FINANCIAL_INTERMEDIATION,
            class_inscription=ClassInscription.BOURGEOIS,
            jurisdiction=None,
        )
        assert bank.social_function == SocialFunction.FINANCIAL_INTERMEDIATION


class TestEconomicExtractive:
    """ECONOMIC_EXTRACTIVE subtype."""

    def test_extractive_apparatus_type(self) -> None:
        """Mining company should be ECONOMIC_EXTRACTIVE."""
        mine = make_institution(
            id="chevron",
            name="Chevron",
            apparatus_type=ApparatusType.ECONOMIC_EXTRACTIVE,
            social_function=SocialFunction.EMPLOYMENT,
            class_inscription=ClassInscription.BOURGEOIS,
            jurisdiction=None,
            territory_ids=["T001", "T002"],
        )
        assert mine.apparatus_type == ApparatusType.ECONOMIC_EXTRACTIVE

    def test_extractive_multi_territory(self) -> None:
        """Extractive firms can span multiple territories."""
        mine = make_institution(
            id="chevron",
            name="Chevron",
            apparatus_type=ApparatusType.ECONOMIC_EXTRACTIVE,
            social_function=SocialFunction.EMPLOYMENT,
            class_inscription=ClassInscription.BOURGEOIS,
            jurisdiction=None,
            territory_ids=["T001", "T002", "T003"],
        )
        assert len(mine.territory_ids) == 3


class TestEconomicReproduction:
    """Economic institutions have reproduction characteristics."""

    @pytest.mark.math
    def test_high_budget_independence(self) -> None:
        """Private economic institutions have high budget independence."""
        repro = make_reproduction(budget_independence=0.95)
        assert repro.budget_independence == 0.95
        assert repro.reproduction_capacity > 0.9

    @pytest.mark.math
    def test_low_succession_protocol(self) -> None:
        """Startup may lack succession protocol."""
        repro = make_reproduction(
            succession_protocol=False,
            budget_independence=0.9,
        )
        # 3/4 bools = 0.75, * 0.7 + 0.9 * 0.3 = 0.525 + 0.27 = 0.795
        expected = 0.75 * 0.7 + 0.9 * 0.3
        assert abs(repro.reproduction_capacity - expected) < 1e-6
