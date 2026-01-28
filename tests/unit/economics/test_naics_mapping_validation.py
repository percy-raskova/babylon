"""Unit tests for NAICS-to-Department mapping coherence.

Tests validating that our NAICS-to-Marxian-department mappings are
internally consistent and theoretically plausible.

Test Categories:
    - Pure Allocations: 100% allocations to correct departments
    - Plausible Ratios: Aggregate department shares are reasonable
    - Mapping Coherence: Related industries have consistent mappings

See Also:
    :mod:`babylon.economics.department_mapper`: DepartmentMapper implementation.
    :mod:`src.babylon.economics.data.naics_to_dept`: YAML configuration.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from babylon.economics.department_mapper import (
    Department,
    DepartmentMapper,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def production_yaml_path() -> Path:
    """Path to the production naics_to_dept.yaml file."""
    return (
        Path(__file__).parent.parent.parent.parent
        / "src"
        / "babylon"
        / "economics"
        / "data"
        / "naics_to_dept.yaml"
    )


@pytest.fixture
def production_mapper(production_yaml_path: Path) -> DepartmentMapper:
    """Load the production DepartmentMapper from YAML."""
    if not production_yaml_path.exists():
        pytest.skip(f"Production config not found at {production_yaml_path}")
    return DepartmentMapper.from_yaml(production_yaml_path)


@pytest.fixture
def yaml_config(production_yaml_path: Path) -> dict:
    """Load raw YAML config for direct inspection."""
    if not production_yaml_path.exists():
        pytest.skip(f"Production config not found at {production_yaml_path}")
    with production_yaml_path.open() as f:
        return yaml.safe_load(f)


# =============================================================================
# PURE ALLOCATION TESTS
# =============================================================================


class TestPureAllocations:
    """Tests for industries with 100% allocation to a single department.

    These are the clearest cases where end-use destination is unambiguous.
    """

    @pytest.mark.theory
    def test_pure_capital_goods_map_to_dept_I(self, production_mapper: DepartmentMapper) -> None:
        """Iron ore mining (21221) should be 100% Dept I.

        Iron ore is purely intermediate input for steel production.
        It has no direct consumer use.
        """
        alloc = production_mapper.get_allocation("21221")
        assert alloc is not None, "Iron ore mining should have an allocation"
        assert alloc.dept_I == pytest.approx(1.0), (
            f"Iron ore mining should be 100% Dept I, got {alloc.dept_I}"
        )
        assert alloc.dept_IIa == pytest.approx(0.0)
        assert alloc.dept_IIb == pytest.approx(0.0)
        assert alloc.dept_III == pytest.approx(0.0)

    @pytest.mark.theory
    def test_pure_luxury_goods_map_to_dept_IIb(self, production_mapper: DepartmentMapper) -> None:
        """Jewelry stores (44831) should be 100% Dept IIb.

        Jewelry retail is pure luxury consumption by definition.
        """
        alloc = production_mapper.get_allocation("44831")
        assert alloc is not None, "Jewelry stores should have an allocation"
        assert alloc.dept_IIb == pytest.approx(1.0), (
            f"Jewelry stores should be 100% Dept IIb, got {alloc.dept_IIb}"
        )
        assert alloc.dept_I == pytest.approx(0.0)
        assert alloc.dept_IIa == pytest.approx(0.0)
        assert alloc.dept_III == pytest.approx(0.0)

    @pytest.mark.theory
    def test_pure_care_work_maps_to_dept_III(self, production_mapper: DepartmentMapper) -> None:
        """Child day care (6244) should be 100% Dept III.

        Childcare is pure social reproduction - producing future labor power.
        """
        alloc = production_mapper.get_allocation("6244")
        assert alloc is not None, "Child day care should have an allocation"
        assert alloc.dept_III == pytest.approx(1.0), (
            f"Child day care should be 100% Dept III, got {alloc.dept_III}"
        )
        assert alloc.dept_I == pytest.approx(0.0)
        assert alloc.dept_IIa == pytest.approx(0.0)
        assert alloc.dept_IIb == pytest.approx(0.0)

    @pytest.mark.theory
    def test_private_households_map_to_dept_III(self, production_mapper: DepartmentMapper) -> None:
        """Private households (814) should be 100% Dept III.

        Domestic workers (nannies, housekeepers) perform social reproduction.
        """
        alloc = production_mapper.get_allocation("814")
        assert alloc is not None, "Private households should have an allocation"
        assert alloc.dept_III == pytest.approx(1.0), (
            f"Private households should be 100% Dept III, got {alloc.dept_III}"
        )

    @pytest.mark.theory
    def test_golf_courses_map_to_dept_IIb(self, production_mapper: DepartmentMapper) -> None:
        """Golf courses (71391) should be 100% Dept IIb.

        Golf is pure luxury leisure consumption.
        """
        alloc = production_mapper.get_allocation("71391")
        assert alloc is not None, "Golf courses should have an allocation"
        assert alloc.dept_IIb == pytest.approx(1.0), (
            f"Golf courses should be 100% Dept IIb, got {alloc.dept_IIb}"
        )

    @pytest.mark.theory
    def test_government_is_excluded(self, production_mapper: DepartmentMapper) -> None:
        """Public administration (92) should return None (excluded).

        Government operates outside the M-C-M' commodity circuit.
        """
        alloc = production_mapper.get_allocation("92")
        assert alloc is None, "Government sector should be excluded"

        # Also test 6-digit government codes
        alloc_federal = production_mapper.get_allocation("921110")
        assert alloc_federal is None, "Federal government should be excluded"


# =============================================================================
# PLAUSIBLE RATIO TESTS
# =============================================================================


def _get_config_value(config: dict, key: str, default: dict | None = None) -> dict:
    """Get config value handling both string and integer keys from YAML."""
    if default is None:
        default = {}
    # PyYAML may parse numeric keys as integers
    return config.get(key, config.get(int(key) if key.isdigit() else key, default))


class TestPlausibleRatios:
    """Tests that aggregate department ratios are economically plausible."""

    @pytest.mark.theory
    def test_luxury_share_of_consumption_is_plausible(self, yaml_config: dict) -> None:
        """IIb should be reasonable proportion of consumption sectors.

        Marx's example: IIb = 20% of total II (600/3000)
        Modern estimates: 20-30% of consumer spending is discretionary

        We test that explicit luxury allocations (dept_IIb weights in
        retail/services) are in a plausible range.
        """
        # Count sectors with significant IIb allocation
        luxury_weighted_sectors = 0
        total_retail_service_sectors = 0

        defaults = yaml_config.get("defaults", {})

        # Check 2-digit retail and service defaults (44-45, 71-72)
        consumer_facing = ["44", "45", "71", "72"]
        for sector in consumer_facing:
            # Handle both string and integer keys from YAML
            sector_config = _get_config_value(defaults, sector)
            if sector_config:
                total_retail_service_sectors += 1
                iib = sector_config.get("dept_IIb", 0.0)
                if iib > 0.2:  # Significant luxury component
                    luxury_weighted_sectors += 1

        # At least some consumer sectors should have luxury components
        assert luxury_weighted_sectors > 0, (
            "At least some retail/service sectors should have IIb allocation"
        )

    @pytest.mark.theory
    def test_dept_I_sectors_exist(self, yaml_config: dict) -> None:
        """Some sectors should be primarily Dept I (means of production).

        Mining (21), some manufacturing (32-33), professional services (54)
        should have significant Dept I allocations.
        """
        defaults = yaml_config.get("defaults", {})
        overrides = yaml_config.get("overrides", {})

        # Mining should be primarily Dept I
        mining = _get_config_value(defaults, "21")
        mining_i = mining.get("dept_I", 0.0)
        assert mining_i >= 0.80, f"Mining sector (21) should be >=80% Dept I, got {mining_i}"

        # Industrial machinery should be primarily Dept I
        machinery = _get_config_value(overrides, "3332")
        if machinery:
            machinery_i = machinery.get("dept_I", 0.0)
            assert machinery_i >= 0.90, (
                f"Industrial machinery (3332) should be >=90% Dept I, got {machinery_i}"
            )

    @pytest.mark.theory
    def test_dept_III_sectors_exist(self, yaml_config: dict) -> None:
        """Social reproduction sectors should have significant Dept III.

        Education (61) and healthcare (62) should have substantial
        Dept III allocations as they reproduce labor power.
        """
        defaults = yaml_config.get("defaults", {})

        # Education should have high Dept III
        education = _get_config_value(defaults, "61")
        education_iii = education.get("dept_III", 0.0)
        assert education_iii >= 0.70, (
            f"Education sector (61) should be >=70% Dept III, got {education_iii}"
        )

        # Healthcare should have significant Dept III
        healthcare = _get_config_value(defaults, "62")
        healthcare_iii = healthcare.get("dept_III", 0.0)
        assert healthcare_iii >= 0.50, (
            f"Healthcare sector (62) should be >=50% Dept III, got {healthcare_iii}"
        )


# =============================================================================
# MAPPING COHERENCE TESTS
# =============================================================================


class TestMappingCoherence:
    """Tests that mappings are internally consistent and logically ordered."""

    @pytest.mark.theory
    def test_all_weights_sum_to_one(self, yaml_config: dict) -> None:
        """Every NAICS allocation in YAML must sum to exactly 1.0."""
        defaults = yaml_config.get("defaults", {})
        overrides = yaml_config.get("overrides", {})

        tolerance = 0.001

        for code, weights in defaults.items():
            total = sum(weights.values())
            assert abs(total - 1.0) < tolerance, (
                f"Default NAICS {code} weights sum to {total}, expected 1.0"
            )

        for code, weights in overrides.items():
            total = sum(weights.values())
            assert abs(total - 1.0) < tolerance, (
                f"Override NAICS {code} weights sum to {total}, expected 1.0"
            )

    @pytest.mark.theory
    def test_fast_food_is_more_necessary_than_fine_dining(
        self, production_mapper: DepartmentMapper
    ) -> None:
        """722513 (fast food) should have higher IIa than 722511 (fine dining).

        Fast food is wage-good consumption; fine dining is luxury.
        """
        fast_food = production_mapper.get_allocation("722513")
        fine_dining = production_mapper.get_allocation("722511")

        assert fast_food is not None and fine_dining is not None

        # Fast food should be more "necessary" (higher IIa)
        assert fast_food.dept_IIa > fine_dining.dept_IIa, (
            f"Fast food IIa ({fast_food.dept_IIa}) should > fine dining IIa ({fine_dining.dept_IIa})"
        )

        # Fine dining should be more "luxury" (higher IIb)
        assert fine_dining.dept_IIb > fast_food.dept_IIb, (
            f"Fine dining IIb ({fine_dining.dept_IIb}) should > fast food IIb ({fast_food.dept_IIb})"
        )

    @pytest.mark.theory
    def test_grocery_stores_are_primarily_necessary(
        self, production_mapper: DepartmentMapper
    ) -> None:
        """4451 (grocery stores) should be 90%+ Dept IIa.

        Grocery stores primarily sell wage goods (food staples).
        """
        grocery = production_mapper.get_allocation("4451")
        assert grocery is not None, "Grocery stores should have an allocation"
        assert grocery.dept_IIa >= 0.90, (
            f"Grocery stores should be >=90% Dept IIa, got {grocery.dept_IIa}"
        )

    @pytest.mark.theory
    def test_sporting_goods_more_luxury_than_grocery(
        self, production_mapper: DepartmentMapper
    ) -> None:
        """45111 (sporting goods) should have higher IIb than grocery stores.

        Sporting goods are discretionary; groceries are essential.
        """
        sporting = production_mapper.get_allocation("45111")
        grocery = production_mapper.get_allocation("4451")

        assert sporting is not None and grocery is not None

        assert sporting.dept_IIb > grocery.dept_IIb, (
            f"Sporting goods IIb ({sporting.dept_IIb}) should > grocery IIb ({grocery.dept_IIb})"
        )

    @pytest.mark.theory
    def test_industrial_machinery_more_capital_goods_than_consumer_goods(
        self, production_mapper: DepartmentMapper
    ) -> None:
        """3332 (industrial machinery) should have higher Dept I than auto mfg.

        Industrial machinery is purely intermediate; autos are consumer goods.
        """
        machinery = production_mapper.get_allocation("3332")
        auto = production_mapper.get_allocation("336111")

        assert machinery is not None and auto is not None

        assert machinery.dept_I > auto.dept_I, (
            f"Industrial machinery Dept I ({machinery.dept_I}) should > "
            f"auto manufacturing Dept I ({auto.dept_I})"
        )

    @pytest.mark.theory
    def test_pharmaceutical_is_necessary_consumption(
        self, production_mapper: DepartmentMapper
    ) -> None:
        """3254 (pharmaceutical mfg) should be primarily Dept IIa.

        Pharmaceuticals are essential for labor power reproduction.
        """
        pharma = production_mapper.get_allocation("3254")
        assert pharma is not None, "Pharmaceutical manufacturing should have an allocation"
        assert pharma.dept_IIa >= 0.80, (
            f"Pharmaceutical mfg should be >=80% Dept IIa, got {pharma.dept_IIa}"
        )

    @pytest.mark.theory
    def test_hierarchy_consistency(self, production_mapper: DepartmentMapper) -> None:
        """6-digit overrides should be consistent with 4-digit and 2-digit.

        If 336111 (automobile) is 35% luxury, then 3361 (motor vehicles)
        should have some luxury component, and 33 (manufacturing) should
        have a plausible default.
        """
        auto_6 = production_mapper.get_allocation("336111")
        motor_4 = production_mapper.get_allocation("3361")
        mfg_2 = production_mapper.get_allocation("33")

        assert auto_6 is not None, "Auto manufacturing should have allocation"
        assert motor_4 is not None, "Motor vehicles should have allocation"
        assert mfg_2 is not None, "Manufacturing sector should have default"

        # Auto and motor vehicles should both have some luxury component
        assert auto_6.dept_IIb > 0.0, "Auto mfg should have some IIb"
        assert motor_4.dept_IIb > 0.0, "Motor vehicles should have some IIb"


# =============================================================================
# DEFAULT RATIOS VALIDATION
# =============================================================================


class TestDefaultRatiosValidation:
    """Tests for default c/v and s/v ratios coherence."""

    @pytest.mark.theory
    def test_all_departments_have_default_ratios(self, production_mapper: DepartmentMapper) -> None:
        """Every department should have defined default ratios."""
        for dept in Department:
            cv = production_mapper.get_default_cv_ratio(dept)
            sv = production_mapper.get_default_sv_ratio(dept)

            assert cv > 0.0, f"Dept {dept.name} should have positive c/v ratio"
            assert sv > 0.0, f"Dept {dept.name} should have positive s/v ratio"

    @pytest.mark.theory
    def test_cv_ratios_are_economically_plausible(
        self, production_mapper: DepartmentMapper
    ) -> None:
        """c/v ratios should be in reasonable range (0.1 to 10.0).

        Historical estimates range from ~0.5 (care work) to ~5+ (mining).
        """
        for dept in Department:
            cv = production_mapper.get_default_cv_ratio(dept)
            assert 0.1 <= cv <= 10.0, (
                f"Dept {dept.name} c/v ratio {cv} outside plausible range [0.1, 10.0]"
            )

    @pytest.mark.theory
    def test_sv_ratios_are_economically_plausible(
        self, production_mapper: DepartmentMapper
    ) -> None:
        """s/v ratios should be in reasonable range (0.1 to 5.0).

        Typical exploitation rates range from 50% to 400%.
        """
        for dept in Department:
            sv = production_mapper.get_default_sv_ratio(dept)
            assert 0.1 <= sv <= 5.0, (
                f"Dept {dept.name} s/v ratio {sv} outside plausible range [0.1, 5.0]"
            )
