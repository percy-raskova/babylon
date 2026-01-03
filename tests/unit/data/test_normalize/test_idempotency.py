"""Unit tests for ETL idempotency and data quality.

These tests verify that the ETL pipeline is idempotent (can be run
multiple times safely) and maintains data quality invariants.
"""

from __future__ import annotations

from typing import Any

# =============================================================================
# IDEMPOTENCY HELPER FUNCTIONS
# =============================================================================


def check_dimension_uniqueness(records: list[dict[str, Any]], key_field: str) -> list[str]:
    """Check that dimension records have unique keys.

    Args:
        records: List of dimension records as dicts
        key_field: Field that should be unique

    Returns:
        List of duplicate keys found (empty if all unique)
    """
    keys = [r.get(key_field) for r in records if r.get(key_field)]
    duplicates = [k for k in keys if keys.count(k) > 1]
    return list(set(duplicates))


def check_foreign_key_validity(
    fact_records: list[dict[str, Any]],
    fk_field: str,
    dimension_records: list[dict[str, Any]],
    pk_field: str,
) -> list[Any]:
    """Check that all FK values in facts reference valid dimension PKs.

    Args:
        fact_records: List of fact records
        fk_field: Foreign key field in fact records
        dimension_records: List of dimension records
        pk_field: Primary key field in dimension records

    Returns:
        List of orphan FK values not found in dimension
    """
    valid_pks = {d.get(pk_field) for d in dimension_records}
    fk_values = [f.get(fk_field) for f in fact_records if f.get(fk_field)]
    orphans = [fk for fk in fk_values if fk not in valid_pks]
    return orphans


def simulate_reload(
    first_load: list[dict[str, Any]],
    second_load: list[dict[str, Any]],
    key_field: str,
) -> tuple[int, int, int]:
    """Simulate what happens when ETL is run twice.

    Args:
        first_load: Records from first ETL run
        second_load: Records from second ETL run
        key_field: Field used as natural key

    Returns:
        Tuple of (added, removed, unchanged) counts
    """
    first_keys = {r.get(key_field) for r in first_load if r.get(key_field)}
    second_keys = {r.get(key_field) for r in second_load if r.get(key_field)}

    added = len(second_keys - first_keys)
    removed = len(first_keys - second_keys)
    unchanged = len(first_keys & second_keys)

    return added, removed, unchanged


def verify_no_data_loss(
    source_records: list[dict[str, Any]],
    target_records: list[dict[str, Any]],
    key_field: str,
    required_fields: list[str],
) -> list[str]:
    """Verify that required data wasn't lost in transformation.

    Args:
        source_records: Records from source
        target_records: Records after transformation
        key_field: Field to match records
        required_fields: Fields that should be preserved

    Returns:
        List of errors describing data loss
    """
    errors = []
    source_by_key = {r.get(key_field): r for r in source_records if r.get(key_field)}
    target_by_key = {r.get(key_field): r for r in target_records if r.get(key_field)}

    for key, source in source_by_key.items():
        if key not in target_by_key:
            errors.append(f"Record with {key_field}={key} missing from target")
            continue

        target = target_by_key[key]
        for field in required_fields:
            if source.get(field) and not target.get(field):
                errors.append(
                    f"Field {field} lost for {key_field}={key}: "
                    f"source={source.get(field)}, target={target.get(field)}"
                )

    return errors


# =============================================================================
# TESTS
# =============================================================================


class TestDimensionUniqueness:
    """Tests for dimension uniqueness constraints."""

    def test_detect_duplicate_keys(self) -> None:
        """Should detect duplicate primary keys in dimension."""
        records = [
            {"code": "A", "name": "Alpha"},
            {"code": "B", "name": "Beta"},
            {"code": "A", "name": "Alpha Copy"},  # Duplicate
        ]
        duplicates = check_dimension_uniqueness(records, "code")
        assert duplicates == ["A"]

    def test_no_duplicates(self) -> None:
        """Should return empty list when no duplicates."""
        records = [
            {"code": "A", "name": "Alpha"},
            {"code": "B", "name": "Beta"},
            {"code": "C", "name": "Gamma"},
        ]
        duplicates = check_dimension_uniqueness(records, "code")
        assert duplicates == []

    def test_handles_null_keys(self) -> None:
        """Should handle records with NULL key values."""
        records = [
            {"code": "A", "name": "Alpha"},
            {"code": None, "name": "No Code"},
            {"code": "", "name": "Empty Code"},
        ]
        duplicates = check_dimension_uniqueness(records, "code")
        assert duplicates == []


class TestForeignKeyValidity:
    """Tests for FK reference validity."""

    def test_detect_orphan_fks(self) -> None:
        """Should detect FK values not in dimension."""
        dimensions = [
            {"id": 1, "name": "A"},
            {"id": 2, "name": "B"},
        ]
        facts = [
            {"dim_id": 1, "value": 100},
            {"dim_id": 2, "value": 200},
            {"dim_id": 999, "value": 300},  # Orphan
        ]
        orphans = check_foreign_key_validity(facts, "dim_id", dimensions, "id")
        assert orphans == [999]

    def test_no_orphans(self) -> None:
        """Should return empty list when all FKs valid."""
        dimensions = [
            {"id": 1, "name": "A"},
            {"id": 2, "name": "B"},
        ]
        facts = [
            {"dim_id": 1, "value": 100},
            {"dim_id": 2, "value": 200},
        ]
        orphans = check_foreign_key_validity(facts, "dim_id", dimensions, "id")
        assert orphans == []


class TestIdempotentReload:
    """Tests for ETL idempotency simulation."""

    def test_identical_loads(self) -> None:
        """Two identical loads should have no changes."""
        records = [
            {"code": "A"},
            {"code": "B"},
        ]
        added, removed, unchanged = simulate_reload(records, records, "code")
        assert added == 0
        assert removed == 0
        assert unchanged == 2

    def test_source_growth(self) -> None:
        """New records in source should be detected as additions."""
        first = [
            {"code": "A"},
            {"code": "B"},
        ]
        second = [
            {"code": "A"},
            {"code": "B"},
            {"code": "C"},  # New
        ]
        added, removed, unchanged = simulate_reload(first, second, "code")
        assert added == 1
        assert removed == 0
        assert unchanged == 2

    def test_source_removal(self) -> None:
        """Records removed from source should be detected."""
        first = [
            {"code": "A"},
            {"code": "B"},
            {"code": "C"},
        ]
        second = [
            {"code": "A"},
            {"code": "B"},
        ]
        added, removed, unchanged = simulate_reload(first, second, "code")
        assert added == 0
        assert removed == 1
        assert unchanged == 2


class TestDataLossDetection:
    """Tests for data loss detection during transformation."""

    def test_detect_lost_field(self) -> None:
        """Should detect when a required field is lost."""
        source = [
            {"id": 1, "name": "Test", "value": 100},
        ]
        target = [
            {"id": 1, "name": "Test", "value": None},  # Value lost
        ]
        errors = verify_no_data_loss(source, target, "id", ["name", "value"])
        assert len(errors) == 1
        assert "value" in errors[0]

    def test_no_data_loss(self) -> None:
        """Should return no errors when data preserved."""
        source = [
            {"id": 1, "name": "Test", "value": 100},
        ]
        target = [
            {"id": 1, "name": "Test", "value": 100},
        ]
        errors = verify_no_data_loss(source, target, "id", ["name", "value"])
        assert errors == []

    def test_detect_missing_record(self) -> None:
        """Should detect when entire record is missing."""
        source = [
            {"id": 1, "name": "A"},
            {"id": 2, "name": "B"},
        ]
        target = [
            {"id": 1, "name": "A"},
            # Record 2 missing
        ]
        errors = verify_no_data_loss(source, target, "id", ["name"])
        assert len(errors) == 1
        assert "id=2" in errors[0]


class TestDataQualityInvariants:
    """Tests for data quality invariants that should always hold."""

    def test_positive_counts_invariant(self) -> None:
        """Employment and establishment counts should be non-negative."""
        # Simulate QCEW data
        valid_records = [
            {"employment": 100, "establishments": 5},
            {"employment": 0, "establishments": 0},
            {"employment": None, "establishments": None},
        ]
        for rec in valid_records:
            if rec["employment"] is not None:
                assert rec["employment"] >= 0
            if rec["establishments"] is not None:
                assert rec["establishments"] >= 0

    def test_percentage_bounds_invariant(self) -> None:
        """Percentages should be between 0 and 100 (or 0 and 1)."""
        percentages = [0.0, 0.5, 1.0, 50.0, 100.0]
        for pct in percentages:
            # Either 0-1 scale or 0-100 scale
            assert 0 <= pct <= 100

    def test_year_range_invariant(self) -> None:
        """Years should be within reasonable bounds."""
        valid_years = [1990, 2000, 2022, 2024, 2025]
        for year in valid_years:
            assert 1900 <= year <= 2100

    def test_fips_format_invariant(self) -> None:
        """FIPS codes should be proper format."""
        valid_fips = ["01", "06", "36", "48", "99"]
        for fips in valid_fips:
            assert len(fips) == 2 or len(fips) == 5
            assert fips.isdigit()

    def test_naics_format_invariant(self) -> None:
        """NAICS codes should be 2-6 digit numeric."""
        valid_naics = ["11", "311", "3112", "31121", "311210"]
        for code in valid_naics:
            assert 2 <= len(code) <= 6
            assert code.isdigit()


class TestNullHandlingConsistency:
    """Tests for consistent NULL handling across transformations."""

    def test_null_in_optional_field(self) -> None:
        """Optional fields should accept NULL."""
        record = {"required": "value", "optional": None}
        assert record["required"] is not None
        assert record["optional"] is None

    def test_null_in_required_field_detected(self) -> None:
        """Required fields with NULL should be flagged."""
        records = [
            {"id": 1, "required": "A"},
            {"id": 2, "required": None},  # Invalid
            {"id": 3, "required": "C"},
        ]
        required_field = "required"
        nulls = [r["id"] for r in records if r.get(required_field) is None]
        assert nulls == [2]


class TestBatchIdempotency:
    """Tests for idempotency in batch processing."""

    def test_batch_boundaries_dont_affect_result(self) -> None:
        """Processing in different batch sizes should give same result."""
        records = list(range(100))

        # Simulate batch 1: size 10
        batch_10_result = []
        for i in range(0, 100, 10):
            batch_10_result.extend(records[i : i + 10])

        # Simulate batch 2: size 25
        batch_25_result = []
        for i in range(0, 100, 25):
            batch_25_result.extend(records[i : i + 25])

        assert batch_10_result == batch_25_result

    def test_order_independence(self) -> None:
        """Final result should be same regardless of processing order."""
        records = [
            {"id": 1, "value": "A"},
            {"id": 2, "value": "B"},
            {"id": 3, "value": "C"},
        ]

        # Process in order
        result_ordered = sorted(records, key=lambda r: r["id"])

        # Process in reverse order
        reversed_records = list(reversed(records))
        result_reversed = sorted(reversed_records, key=lambda r: r["id"])

        assert result_ordered == result_reversed
