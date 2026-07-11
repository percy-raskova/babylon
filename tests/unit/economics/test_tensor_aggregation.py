"""Unit tests for tensor geographic aggregation accuracy.

Feature: 011-fundamental-tensor-primitive
Implements: T060, T063 from tasks.md

These tests verify:
1. Sum of individual county tensors matches get_aggregate() result
2. Aggregation preserves accounting identities within 0.01% tolerance
3. Multi-state and nation-level aggregation works correctly
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.tensor import DepartmentRow, NoDataSentinel, ValueTensor4x3
from babylon.domain.economics.tensor_registry import GeoLevel, TensorRegistry


class TestAggregationFormulaValidation:
    """Tests that sum(counties) matches get_aggregate() within tolerance."""

    @pytest.fixture
    def registry_michigan(self) -> TensorRegistry:
        """Registry with Michigan counties."""
        reg = TensorRegistry()
        # Wayne County (Detroit)
        reg.put(
            "26163",
            2022,
            ValueTensor4x3(
                fips_code="26163",
                year=2022,
                dept_I=DepartmentRow(c=10000.0, v=5000.0, s=3000.0),
                dept_IIa=DepartmentRow(c=8000.0, v=4000.0, s=2400.0),
                dept_IIb=DepartmentRow(c=6000.0, v=3000.0, s=1800.0),
                dept_III=DepartmentRow(c=4000.0, v=2000.0, s=1200.0),
                naics_granularity=0.92,
                excluded_wages=50000.0,
            ),
        )
        # Oakland County
        reg.put(
            "26125",
            2022,
            ValueTensor4x3(
                fips_code="26125",
                year=2022,
                dept_I=DepartmentRow(c=5000.0, v=2500.0, s=1500.0),
                dept_IIa=DepartmentRow(c=4000.0, v=2000.0, s=1200.0),
                dept_IIb=DepartmentRow(c=3000.0, v=1500.0, s=900.0),
                dept_III=DepartmentRow(c=2000.0, v=1000.0, s=600.0),
                naics_granularity=0.88,
                excluded_wages=25000.0,
            ),
        )
        # Macomb County
        reg.put(
            "26099",
            2022,
            ValueTensor4x3(
                fips_code="26099",
                year=2022,
                dept_I=DepartmentRow(c=3000.0, v=1500.0, s=900.0),
                dept_IIa=DepartmentRow(c=2400.0, v=1200.0, s=720.0),
                dept_IIb=DepartmentRow(c=1800.0, v=900.0, s=540.0),
                dept_III=DepartmentRow(c=1200.0, v=600.0, s=360.0),
                naics_granularity=0.85,
                excluded_wages=15000.0,
            ),
        )
        return reg

    def test_state_aggregate_matches_manual_sum(self, registry_michigan: TensorRegistry) -> None:
        """State aggregate should match sum of individual county get() calls."""
        # Get individual counties
        wayne = registry_michigan.get("26163", 2022)
        oakland = registry_michigan.get("26125", 2022)
        macomb = registry_michigan.get("26099", 2022)

        assert isinstance(wayne, ValueTensor4x3)
        assert isinstance(oakland, ValueTensor4x3)
        assert isinstance(macomb, ValueTensor4x3)

        # Manual sum
        manual_total_c = wayne.total_c + oakland.total_c + macomb.total_c
        manual_total_v = wayne.total_v + oakland.total_v + macomb.total_v
        manual_total_s = wayne.total_s + oakland.total_s + macomb.total_s
        manual_total_value = wayne.total_value + oakland.total_value + macomb.total_value
        manual_excluded = wayne.excluded_wages + oakland.excluded_wages + macomb.excluded_wages

        # Get aggregate
        michigan = registry_michigan.get_aggregate(GeoLevel.STATE, "26", 2022)
        assert isinstance(michigan, ValueTensor4x3)

        # Verify within 0.01% relative tolerance
        assert michigan.total_c == pytest.approx(manual_total_c, rel=0.0001)
        assert michigan.total_v == pytest.approx(manual_total_v, rel=0.0001)
        assert michigan.total_s == pytest.approx(manual_total_s, rel=0.0001)
        assert michigan.total_value == pytest.approx(manual_total_value, rel=0.0001)
        assert michigan.excluded_wages == pytest.approx(manual_excluded, rel=0.0001)

    def test_department_values_sum_correctly(self, registry_michigan: TensorRegistry) -> None:
        """Each department's c, v, s should sum correctly across counties."""
        wayne = registry_michigan.get("26163", 2022)
        oakland = registry_michigan.get("26125", 2022)
        macomb = registry_michigan.get("26099", 2022)
        michigan = registry_michigan.get_aggregate(GeoLevel.STATE, "26", 2022)

        assert isinstance(wayne, ValueTensor4x3)
        assert isinstance(oakland, ValueTensor4x3)
        assert isinstance(macomb, ValueTensor4x3)
        assert isinstance(michigan, ValueTensor4x3)

        # Dept I
        assert michigan.dept_I.c == pytest.approx(
            wayne.dept_I.c + oakland.dept_I.c + macomb.dept_I.c, rel=0.0001
        )
        assert michigan.dept_I.v == pytest.approx(
            wayne.dept_I.v + oakland.dept_I.v + macomb.dept_I.v, rel=0.0001
        )
        assert michigan.dept_I.s == pytest.approx(
            wayne.dept_I.s + oakland.dept_I.s + macomb.dept_I.s, rel=0.0001
        )

        # Dept IIa
        assert michigan.dept_IIa.c == pytest.approx(
            wayne.dept_IIa.c + oakland.dept_IIa.c + macomb.dept_IIa.c, rel=0.0001
        )

        # Dept IIb
        assert michigan.dept_IIb.v == pytest.approx(
            wayne.dept_IIb.v + oakland.dept_IIb.v + macomb.dept_IIb.v, rel=0.0001
        )

        # Dept III
        assert michigan.dept_III.s == pytest.approx(
            wayne.dept_III.s + oakland.dept_III.s + macomb.dept_III.s, rel=0.0001
        )


class TestMultiStateAggregation:
    """Tests for aggregation across multiple states."""

    @pytest.fixture
    def registry_multi_state(self) -> TensorRegistry:
        """Registry with counties from multiple states."""
        reg = TensorRegistry()

        # Michigan counties (state 26)
        reg.put(
            "26163",
            2022,
            ValueTensor4x3(
                fips_code="26163",
                year=2022,
                dept_I=DepartmentRow(c=1000.0, v=500.0, s=300.0),
                dept_IIa=DepartmentRow(c=800.0, v=400.0, s=240.0),
                dept_IIb=DepartmentRow(c=600.0, v=300.0, s=180.0),
                dept_III=DepartmentRow(c=400.0, v=200.0, s=120.0),
                naics_granularity=0.9,
                excluded_wages=5000.0,
            ),
        )

        # California counties (state 06)
        reg.put(
            "06037",  # Los Angeles
            2022,
            ValueTensor4x3(
                fips_code="06037",
                year=2022,
                dept_I=DepartmentRow(c=2000.0, v=1000.0, s=600.0),
                dept_IIa=DepartmentRow(c=1600.0, v=800.0, s=480.0),
                dept_IIb=DepartmentRow(c=1200.0, v=600.0, s=360.0),
                dept_III=DepartmentRow(c=800.0, v=400.0, s=240.0),
                naics_granularity=0.95,
                excluded_wages=10000.0,
            ),
        )
        reg.put(
            "06085",  # Santa Clara
            2022,
            ValueTensor4x3(
                fips_code="06085",
                year=2022,
                dept_I=DepartmentRow(c=1500.0, v=750.0, s=450.0),
                dept_IIa=DepartmentRow(c=1200.0, v=600.0, s=360.0),
                dept_IIb=DepartmentRow(c=900.0, v=450.0, s=270.0),
                dept_III=DepartmentRow(c=600.0, v=300.0, s=180.0),
                naics_granularity=0.93,
                excluded_wages=7500.0,
            ),
        )

        return reg

    def test_state_aggregates_are_independent(self, registry_multi_state: TensorRegistry) -> None:
        """Each state's aggregate only includes its counties."""
        michigan = registry_multi_state.get_aggregate(GeoLevel.STATE, "26", 2022)
        california = registry_multi_state.get_aggregate(GeoLevel.STATE, "06", 2022)

        assert isinstance(michigan, ValueTensor4x3)
        assert isinstance(california, ValueTensor4x3)

        # Michigan should only have Wayne County
        wayne = registry_multi_state.get("26163", 2022)
        assert isinstance(wayne, ValueTensor4x3)
        assert michigan.total_value == pytest.approx(wayne.total_value, rel=0.0001)

        # California should have LA + Santa Clara
        la = registry_multi_state.get("06037", 2022)
        sc = registry_multi_state.get("06085", 2022)
        assert isinstance(la, ValueTensor4x3)
        assert isinstance(sc, ValueTensor4x3)
        assert california.total_value == pytest.approx(la.total_value + sc.total_value, rel=0.0001)

    def test_nation_aggregate_includes_all_states(
        self, registry_multi_state: TensorRegistry
    ) -> None:
        """Nation aggregate includes all states."""
        nation = registry_multi_state.get_aggregate(GeoLevel.NATION, "US", 2022)
        michigan = registry_multi_state.get_aggregate(GeoLevel.STATE, "26", 2022)
        california = registry_multi_state.get_aggregate(GeoLevel.STATE, "06", 2022)

        assert isinstance(nation, ValueTensor4x3)
        assert isinstance(michigan, ValueTensor4x3)
        assert isinstance(california, ValueTensor4x3)

        # Nation should equal sum of states
        assert nation.total_value == pytest.approx(
            michigan.total_value + california.total_value, rel=0.0001
        )
        assert nation.total_c == pytest.approx(michigan.total_c + california.total_c, rel=0.0001)
        assert nation.total_v == pytest.approx(michigan.total_v + california.total_v, rel=0.0001)
        assert nation.total_s == pytest.approx(michigan.total_s + california.total_s, rel=0.0001)


class TestAggregationAccountingIdentities:
    """Tests that aggregation preserves accounting identities."""

    @pytest.fixture
    def registry_with_data(self) -> TensorRegistry:
        """Registry with diverse county data."""
        reg = TensorRegistry()

        # Add several counties with different characteristics
        counties = [
            ("26163", 10000.0, 5000.0, 2500.0),  # Wayne
            ("26125", 8000.0, 4000.0, 2000.0),  # Oakland
            ("26099", 6000.0, 3000.0, 1500.0),  # Macomb
            ("26017", 4000.0, 2000.0, 1000.0),  # Bay
            ("26065", 3000.0, 1500.0, 750.0),  # Ingham
        ]

        for fips, c, v, s in counties:
            reg.put(
                fips,
                2022,
                ValueTensor4x3(
                    fips_code=fips,
                    year=2022,
                    dept_I=DepartmentRow(c=c * 0.4, v=v * 0.4, s=s * 0.4),
                    dept_IIa=DepartmentRow(c=c * 0.3, v=v * 0.3, s=s * 0.3),
                    dept_IIb=DepartmentRow(c=c * 0.2, v=v * 0.2, s=s * 0.2),
                    dept_III=DepartmentRow(c=c * 0.1, v=v * 0.1, s=s * 0.1),
                    naics_granularity=0.9,
                    excluded_wages=c * 0.5,
                ),
            )

        return reg

    def test_aggregate_total_value_identity(self, registry_with_data: TensorRegistry) -> None:
        """Aggregate total_value == total_c + total_v + total_s."""
        michigan = registry_with_data.get_aggregate(GeoLevel.STATE, "26", 2022)
        assert isinstance(michigan, ValueTensor4x3)

        # Accounting identity must hold
        computed = michigan.total_c + michigan.total_v + michigan.total_s
        assert michigan.total_value == pytest.approx(computed, rel=0.0001)

    def test_aggregate_departments_sum_to_totals(self, registry_with_data: TensorRegistry) -> None:
        """Sum of department values equals total values."""
        michigan = registry_with_data.get_aggregate(GeoLevel.STATE, "26", 2022)
        assert isinstance(michigan, ValueTensor4x3)

        # c across departments
        dept_c_sum = (
            michigan.dept_I.c + michigan.dept_IIa.c + michigan.dept_IIb.c + michigan.dept_III.c
        )
        assert michigan.total_c == pytest.approx(dept_c_sum, rel=0.0001)

        # v across departments
        dept_v_sum = (
            michigan.dept_I.v + michigan.dept_IIa.v + michigan.dept_IIb.v + michigan.dept_III.v
        )
        assert michigan.total_v == pytest.approx(dept_v_sum, rel=0.0001)

        # s across departments
        dept_s_sum = (
            michigan.dept_I.s + michigan.dept_IIa.s + michigan.dept_IIb.s + michigan.dept_III.s
        )
        assert michigan.total_s == pytest.approx(dept_s_sum, rel=0.0001)


class TestAggregationEdgeCases:
    """Tests for edge cases in aggregation."""

    def test_single_county_aggregate_equals_county(self) -> None:
        """Aggregate of single county equals that county's tensor."""
        reg = TensorRegistry()
        tensor = ValueTensor4x3(
            fips_code="26163",
            year=2022,
            dept_I=DepartmentRow(c=1000.0, v=500.0, s=250.0),
            dept_IIa=DepartmentRow(c=800.0, v=400.0, s=200.0),
            dept_IIb=DepartmentRow(c=600.0, v=300.0, s=150.0),
            dept_III=DepartmentRow(c=400.0, v=200.0, s=100.0),
            naics_granularity=0.9,
            excluded_wages=5000.0,
        )
        reg.put("26163", 2022, tensor)

        aggregate = reg.get_aggregate(GeoLevel.STATE, "26", 2022)
        assert isinstance(aggregate, ValueTensor4x3)

        # Should match exactly (same values)
        assert aggregate.total_value == pytest.approx(tensor.total_value, rel=0.0001)
        assert aggregate.total_c == pytest.approx(tensor.total_c, rel=0.0001)
        assert aggregate.total_v == pytest.approx(tensor.total_v, rel=0.0001)
        assert aggregate.total_s == pytest.approx(tensor.total_s, rel=0.0001)

    def test_empty_state_returns_sentinel(self) -> None:
        """State with no loaded counties returns sentinel."""
        reg = TensorRegistry()
        # Add Michigan county
        reg.put(
            "26163",
            2022,
            ValueTensor4x3(
                fips_code="26163",
                year=2022,
                dept_I=DepartmentRow(c=100.0, v=50.0, s=25.0),
                dept_IIa=DepartmentRow(c=0.0, v=0.0, s=0.0),
                dept_IIb=DepartmentRow(c=0.0, v=0.0, s=0.0),
                dept_III=DepartmentRow(c=0.0, v=0.0, s=0.0),
                naics_granularity=0.5,
                excluded_wages=0.0,
            ),
        )

        # Request California aggregate (no data)
        result = reg.get_aggregate(GeoLevel.STATE, "06", 2022)
        assert isinstance(result, NoDataSentinel)

    def test_aggregate_with_zero_value_counties(self) -> None:
        """Aggregation handles counties with zero values correctly."""
        reg = TensorRegistry()

        # Normal county
        reg.put(
            "26163",
            2022,
            ValueTensor4x3(
                fips_code="26163",
                year=2022,
                dept_I=DepartmentRow(c=1000.0, v=500.0, s=250.0),
                dept_IIa=DepartmentRow(c=800.0, v=400.0, s=200.0),
                dept_IIb=DepartmentRow(c=600.0, v=300.0, s=150.0),
                dept_III=DepartmentRow(c=400.0, v=200.0, s=100.0),
                naics_granularity=0.9,
                excluded_wages=5000.0,
            ),
        )

        # Zero-value county (no economic activity)
        reg.put(
            "26001",
            2022,
            ValueTensor4x3(
                fips_code="26001",
                year=2022,
                dept_I=DepartmentRow(c=0.0, v=0.0, s=0.0),
                dept_IIa=DepartmentRow(c=0.0, v=0.0, s=0.0),
                dept_IIb=DepartmentRow(c=0.0, v=0.0, s=0.0),
                dept_III=DepartmentRow(c=0.0, v=0.0, s=0.0),
                naics_granularity=0.0,
                excluded_wages=0.0,
            ),
        )

        aggregate = reg.get_aggregate(GeoLevel.STATE, "26", 2022)
        assert isinstance(aggregate, ValueTensor4x3)

        # Should equal the non-zero county
        normal = reg.get("26163", 2022)
        assert isinstance(normal, ValueTensor4x3)
        assert aggregate.total_value == pytest.approx(normal.total_value, rel=0.0001)
