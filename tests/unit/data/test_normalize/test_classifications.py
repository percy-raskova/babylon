"""Unit tests for Marxian classification logic.

Tests the classification functions used during ETL to assign
world-system tiers, class composition, Marxian class, and labor type.
"""

from __future__ import annotations

from babylon.data.normalize.classifications import (
    CORE_COUNTRIES,
    SEMI_PERIPHERY_COUNTRIES,
    classify_class_composition,
    classify_labor_type,
    classify_marxian_class,
    classify_ownership,
    classify_rent_burden,
    classify_world_system_tier,
    get_sector_code,
)


class TestWorldSystemTierClassification:
    """Tests for world-system tier assignment."""

    def test_core_country_classification(self) -> None:
        """G7 and major imperialist powers should be classified as core."""
        core_examples = [
            "United States",
            "Germany",
            "Japan",
            "France",
            "United Kingdom",
            "Canada",
            "Italy",
            "Australia",
            "Switzerland",
        ]
        for country in core_examples:
            assert classify_world_system_tier(country) == "core", f"{country} should be core"

    def test_semi_periphery_classification(self) -> None:
        """BRICS and emerging economies should be semi-periphery."""
        semi_periphery_examples = [
            "Brazil",
            "Russia",
            "India",
            "China",
            "South Africa",
            "Mexico",
            "Turkey",
            "Indonesia",
        ]
        for country in semi_periphery_examples:
            assert classify_world_system_tier(country) == "semi_periphery", (
                f"{country} should be semi_periphery"
            )

    def test_periphery_classification(self) -> None:
        """Countries not in core or semi-periphery should be periphery."""
        # Pure periphery: countries with minimal industrialization,
        # primary commodity exporters, highest exploitation rates
        periphery_examples = [
            "Haiti",
            "Ethiopia",
            "Bolivia",
            "Cambodia",
            "Laos",
            "Nepal",
            "Mali",
            "Niger",
        ]
        for country in periphery_examples:
            tier = classify_world_system_tier(country)
            assert tier == "periphery", f"{country} should be periphery, got {tier}"

    def test_aggregate_regions_return_none(self) -> None:
        """Aggregate regions and trade blocs should return None."""
        # These are actual aggregate names from trade_countries WHERE is_region = 1
        aggregates = [
            "World",
            "World Total",
            "Africa",
            "Asia",
            "Europe",
            "European Union",
            "North America",
            "Pacific Rim",
            "South and Central America",
            "Advanced Technology Products",
            # NAFTA appears as substring in composite names
            "NAFTA with Mexico",
            "OPEC Countries",
        ]
        for region in aggregates:
            assert classify_world_system_tier(region) is None, f"{region} should be None"

    def test_empty_country_returns_none(self) -> None:
        """Empty string should return None."""
        assert classify_world_system_tier("") is None
        assert classify_world_system_tier(None) is None  # type: ignore[arg-type]

    def test_tax_havens_are_core(self) -> None:
        """Tax havens that facilitate imperial rent extraction are core."""
        tax_havens = ["Bermuda", "Cayman Islands", "Luxembourg", "Monaco"]
        for haven in tax_havens:
            assert classify_world_system_tier(haven) == "core", f"{haven} should be core"

    def test_core_and_semi_periphery_sets_are_disjoint(self) -> None:
        """Core and semi-periphery sets should have no overlap."""
        overlap = CORE_COUNTRIES & SEMI_PERIPHERY_COUNTRIES
        assert len(overlap) == 0, f"Overlap found: {overlap}"


class TestClassCompositionClassification:
    """Tests for industry class composition assignment."""

    def test_goods_producing_sectors(self) -> None:
        """Manufacturing and construction should be goods-producing."""
        goods_producing = [
            ("11", "Agriculture"),
            ("23", "Construction"),
            ("31", "Food Manufacturing"),
            ("32", "Chemical Manufacturing"),
            ("33", "Machinery Manufacturing"),
        ]
        for code, _name in goods_producing:
            result = classify_class_composition(code)
            assert result == "goods_producing", (
                f"NAICS {code} should be goods_producing, got {result}"
            )

    def test_extraction_sectors(self) -> None:
        """Mining and oil/gas should be extraction (subset of goods-producing)."""
        extraction = [
            ("21", "Mining"),
            ("211", "Oil and Gas Extraction"),
            ("212", "Mining except Oil and Gas"),
            ("213", "Support Activities for Mining"),
        ]
        for code, _name in extraction:
            result = classify_class_composition(code)
            assert result == "extraction", f"NAICS {code} should be extraction, got {result}"

    def test_circulation_sectors(self) -> None:
        """Finance, real estate, and management should be circulation."""
        circulation = [
            ("52", "Finance and Insurance"),
            ("53", "Real Estate"),
            ("55", "Management of Companies"),
        ]
        for code, _name in circulation:
            result = classify_class_composition(code)
            assert result == "circulation", f"NAICS {code} should be circulation, got {result}"

    def test_government_sectors(self) -> None:
        """Public administration should be government."""
        assert classify_class_composition("92") == "government"

    def test_service_producing_sectors(self) -> None:
        """Retail, healthcare, etc. should be service-producing."""
        services = [
            ("44", "Retail Trade"),
            ("54", "Professional Services"),
            ("62", "Healthcare"),
            ("72", "Food Service"),
            ("81", "Other Services"),
        ]
        for code, _name in services:
            result = classify_class_composition(code)
            assert result == "service_producing", (
                f"NAICS {code} should be service_producing, got {result}"
            )

    def test_bls_aggregates(self) -> None:
        """BLS aggregate codes should return appropriate values or None."""
        assert classify_class_composition("10") is None  # Total, all industries
        assert classify_class_composition("101") == "goods_producing"
        assert classify_class_composition("102") == "service_producing"

    def test_empty_code_returns_none(self) -> None:
        """Empty or None code should return None."""
        assert classify_class_composition("") is None

    def test_longer_naics_codes(self) -> None:
        """Longer NAICS codes should use first 2 digits for classification."""
        # 311 is Food Manufacturing (subset of 31)
        assert classify_class_composition("311") == "goods_producing"
        # 5221 is Depository Credit Intermediation (subset of 52)
        assert classify_class_composition("5221") == "circulation"


class TestSectorCodeExtraction:
    """Tests for extracting 2-digit sector codes."""

    def test_extract_from_naics(self) -> None:
        """Should extract first 2 digits from NAICS codes."""
        assert get_sector_code("311") == "31"
        assert get_sector_code("5221") == "52"
        assert get_sector_code("62") == "62"
        assert get_sector_code("921") == "92"

    def test_bls_aggregates_return_none(self) -> None:
        """BLS aggregate codes should return None."""
        assert get_sector_code("10") is None
        assert get_sector_code("101") is None
        assert get_sector_code("102") is None

    def test_empty_code_returns_none(self) -> None:
        """Empty code should return None."""
        assert get_sector_code("") is None

    def test_naics_prefix_stripped(self) -> None:
        """NAICS prefix should be stripped before extraction."""
        assert get_sector_code("NAICS 311") == "31"


class TestMarxianClassClassification:
    """Tests for Marxian class assignment based on Census B24080 codes."""

    def test_proletariat_codes(self) -> None:
        """Private wage workers should be proletariat."""
        proletariat_codes = [
            "B24080_003",  # Private for-profit wage workers
            "B24080_004",  # Employee of private company
            "B24080_006",  # Private not-for-profit
            "B24080_013",  # Private for-profit (Female)
        ]
        for code in proletariat_codes:
            assert classify_marxian_class(code) == "proletariat", f"{code} should be proletariat"

    def test_petty_bourgeois_codes(self) -> None:
        """Self-employed should be petty bourgeois."""
        petty_bourgeois_codes = [
            "B24080_005",  # Self-employed incorporated
            "B24080_010",  # Self-employed not incorporated
        ]
        for code in petty_bourgeois_codes:
            assert classify_marxian_class(code) == "petty_bourgeois", (
                f"{code} should be petty_bourgeois"
            )

    def test_state_worker_codes(self) -> None:
        """Government workers should be state workers."""
        state_worker_codes = [
            "B24080_007",  # Local government
            "B24080_008",  # State government
            "B24080_009",  # Federal government
        ]
        for code in state_worker_codes:
            assert classify_marxian_class(code) == "state_worker", f"{code} should be state_worker"

    def test_unpaid_labor_codes(self) -> None:
        """Unpaid family workers should be unpaid labor."""
        assert classify_marxian_class("B24080_011") == "unpaid_labor"
        assert classify_marxian_class("B24080_021") == "unpaid_labor"

    def test_total_codes_return_none(self) -> None:
        """Total/aggregate codes should return None."""
        assert classify_marxian_class("B24080_001") is None  # Total
        assert classify_marxian_class("B24080_002") is None  # Male
        assert classify_marxian_class("B24080_012") is None  # Female

    def test_label_fallback_for_unknown_codes(self) -> None:
        """Should fall back to label-based classification for unknown codes."""
        # Private wage worker
        assert classify_marxian_class("UNKNOWN", "Private wage and salary workers") == "proletariat"
        # Self-employed
        assert (
            classify_marxian_class("UNKNOWN", "Self-employed in own business") == "petty_bourgeois"
        )
        # Government
        assert classify_marxian_class("UNKNOWN", "Federal government workers") == "state_worker"
        # Unpaid
        assert classify_marxian_class("UNKNOWN", "Unpaid family workers") == "unpaid_labor"


class TestLaborTypeClassification:
    """Tests for labor type classification based on occupation category."""

    def test_productive_labor(self) -> None:
        """Production and construction workers should be productive labor."""
        productive_categories = [
            "Natural resources, construction, and maintenance occupations",
            "Production, transportation, and material moving occupations",
        ]
        for category in productive_categories:
            assert classify_labor_type(category) == "productive", f"{category} should be productive"

    def test_unproductive_labor(self) -> None:
        """Sales and office workers should be unproductive labor."""
        assert classify_labor_type("Sales and office occupations") == "unproductive"

    def test_reproductive_labor(self) -> None:
        """Service workers should be reproductive labor."""
        assert classify_labor_type("Service occupations") == "reproductive"

    def test_managerial_labor(self) -> None:
        """Management occupations should be managerial."""
        assert (
            classify_labor_type("Management, business, science, and arts occupations")
            == "managerial"
        )

    def test_unknown_category_returns_none(self) -> None:
        """Unknown categories should return None."""
        assert classify_labor_type("Unknown Category") is None
        assert classify_labor_type(None) is None


class TestOwnershipClassification:
    """Tests for QCEW ownership code classification."""

    def test_government_codes(self) -> None:
        """Government ownership codes should return (True, False)."""
        assert classify_ownership("1") == (True, False)  # Federal
        assert classify_ownership("2") == (True, False)  # State
        assert classify_ownership("3") == (True, False)  # Local
        assert classify_ownership("4") == (True, False)  # International

    def test_private_code(self) -> None:
        """Private ownership code should return (False, True)."""
        assert classify_ownership("5") == (False, True)

    def test_total_code(self) -> None:
        """Total covered code should return (False, False)."""
        assert classify_ownership("0") == (False, False)


class TestRentBurdenClassification:
    """Tests for rent burden bracket classification."""

    def test_severely_burdened(self) -> None:
        """50%+ rent burden should be severely burdened."""
        is_burdened, is_severely = classify_rent_burden("50.0 percent or more")
        assert is_burdened is True
        assert is_severely is True

    def test_cost_burdened(self) -> None:
        """30-49% rent burden should be cost burdened but not severely."""
        test_cases = [
            "30.0 to 34.9 percent",
            "35.0 to 39.9 percent",
            "40.0 to 49.9 percent",
        ]
        for bracket in test_cases:
            is_burdened, is_severely = classify_rent_burden(bracket)
            assert is_burdened is True, f"{bracket} should be cost burdened"
            assert is_severely is False, f"{bracket} should not be severely burdened"

    def test_not_burdened(self) -> None:
        """Under 30% rent burden should not be cost burdened."""
        test_cases = [
            "Less than 10.0 percent",
            "10.0 to 14.9 percent",
            "15.0 to 19.9 percent",
            "20.0 to 24.9 percent",
            "25.0 to 29.9 percent",
        ]
        for bracket in test_cases:
            is_burdened, is_severely = classify_rent_burden(bracket)
            assert is_burdened is False, f"{bracket} should not be cost burdened"
            assert is_severely is False, f"{bracket} should not be severely burdened"

    def test_not_computed(self) -> None:
        """Not computed or zero income should return (None, None)."""
        is_burdened, is_severely = classify_rent_burden("Not computed")
        assert is_burdened is None
        assert is_severely is None

        is_burdened, is_severely = classify_rent_burden("Zero or negative income")
        assert is_burdened is None
        assert is_severely is None

    def test_empty_bracket(self) -> None:
        """Empty bracket should return (None, None)."""
        assert classify_rent_burden("") == (None, None)
        assert classify_rent_burden(None) == (None, None)  # type: ignore[arg-type]
