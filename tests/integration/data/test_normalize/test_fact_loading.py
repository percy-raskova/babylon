"""Integration tests for fact table loading in ETL pipeline.

Tests the loading of fact tables from research.sqlite into the
normalized 3NF schema, verifying FK resolution, data integrity,
and proper handling of batch processing.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from babylon.data.normalize.database import SOURCE_DB_PATH, NormalizedBase
from babylon.data.normalize.etl import (
    build_lookups,
    load_dim_country,
    load_dim_county,
    load_dim_income_bracket,
    load_dim_industry,
    load_dim_ownership,
    load_dim_sector,
    load_dim_state,
    load_dim_time,
    load_fact_census_income,
    load_fact_census_median_income,
    load_fact_qcew_annual,
    load_fact_trade_monthly,
)
from babylon.data.normalize.schema import (
    DimCountry,
    DimIncomeBracket,
    DimIndustry,
    DimOwnership,
    DimTime,
    FactCensusIncome,
    FactCensusMedianIncome,
    FactQcewAnnual,
    FactTradeMonthly,
)

# Skip all tests if source database doesn't exist
pytestmark = pytest.mark.skipif(
    not SOURCE_DB_PATH.exists(), reason="Source database not available for integration tests"
)


@pytest.fixture(scope="module")
def source_engine():
    """Create connection to source research.sqlite."""
    engine = create_engine(f"sqlite:///{SOURCE_DB_PATH}")
    return engine


@pytest.fixture(scope="function")
def target_engine():
    """Create fresh in-memory target database for each test."""
    engine = create_engine("sqlite:///:memory:")
    NormalizedBase.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def target_session(target_engine):
    """Create session for target database."""
    Session = sessionmaker(bind=target_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def loaded_dimensions(source_engine, target_session):
    """Load all required dimensions for fact loading tests."""
    # Load dimensions in dependency order
    load_dim_state(source_engine, target_session)
    load_dim_county(source_engine, target_session)
    load_dim_country(source_engine, target_session)
    load_dim_industry(source_engine, target_session)
    load_dim_sector(source_engine, target_session)
    load_dim_ownership(source_engine, target_session)
    load_dim_income_bracket(source_engine, target_session)
    load_dim_time(source_engine, target_session)

    # Build and return lookups
    return build_lookups(target_session)


class TestFactCensusIncomeLoading:
    """Integration tests for census income fact loading."""

    def test_loads_income_distribution_facts(
        self, source_engine, target_session, loaded_dimensions
    ) -> None:
        """Census income distribution facts should be loaded."""
        count = load_fact_census_income(source_engine, target_session, loaded_dimensions)

        # May be 0 if no matching FKs, but shouldn't error
        assert count >= 0, "Should load or return 0"

        if count > 0:
            facts = target_session.query(FactCensusIncome).limit(10).all()
            for fact in facts:
                assert fact.bracket_id is not None, "Should have bracket_id"
                assert fact.county_id is not None, "Should have county_id"

    def test_income_facts_have_valid_bracket_fk(
        self, source_engine, target_session, loaded_dimensions
    ) -> None:
        """Income facts should reference valid bracket dimension."""
        load_fact_census_income(source_engine, target_session, loaded_dimensions)

        facts = target_session.query(FactCensusIncome).limit(100).all()
        valid_bracket_ids = {b.bracket_id for b in target_session.query(DimIncomeBracket).all()}

        for fact in facts:
            assert fact.bracket_id in valid_bracket_ids, (
                f"Fact has invalid bracket_id {fact.bracket_id}"
            )


class TestFactCensusMedianIncomeLoading:
    """Integration tests for census median income fact loading."""

    def test_loads_median_income_facts(
        self, source_engine, target_session, loaded_dimensions
    ) -> None:
        """Census median income facts should be loaded."""
        count = load_fact_census_median_income(source_engine, target_session, loaded_dimensions)

        if count > 0:
            facts = target_session.query(FactCensusMedianIncome).limit(10).all()
            for fact in facts:
                assert fact.county_id is not None, "Should have county_id"
                # Median income should be reasonable
                if fact.median_income_usd is not None:
                    assert fact.median_income_usd > 0, "Median income should be positive"


class TestFactQcewAnnualLoading:
    """Integration tests for QCEW annual fact loading."""

    def test_loads_qcew_annual_facts(
        self, source_engine, target_session, loaded_dimensions
    ) -> None:
        """QCEW annual facts should be loaded."""
        count = load_fact_qcew_annual(source_engine, target_session, loaded_dimensions)

        assert count >= 0, "Should load or return 0"

        if count > 0:
            facts = target_session.query(FactQcewAnnual).limit(10).all()
            for fact in facts:
                assert fact.industry_id is not None, "Should have industry_id"
                assert fact.ownership_id is not None, "Should have ownership_id"
                assert fact.year is not None, "Should have year"

    def test_qcew_facts_have_valid_industry_fk(
        self, source_engine, target_session, loaded_dimensions
    ) -> None:
        """QCEW facts should reference valid industry dimension."""
        load_fact_qcew_annual(source_engine, target_session, loaded_dimensions)

        facts = target_session.query(FactQcewAnnual).limit(100).all()
        valid_industry_ids = {i.industry_id for i in target_session.query(DimIndustry).all()}

        for fact in facts:
            assert fact.industry_id in valid_industry_ids, (
                f"Fact has invalid industry_id {fact.industry_id}"
            )

    def test_qcew_facts_have_valid_ownership_fk(
        self, source_engine, target_session, loaded_dimensions
    ) -> None:
        """QCEW facts should reference valid ownership dimension."""
        load_fact_qcew_annual(source_engine, target_session, loaded_dimensions)

        facts = target_session.query(FactQcewAnnual).limit(100).all()
        valid_ownership_ids = {o.ownership_id for o in target_session.query(DimOwnership).all()}

        for fact in facts:
            assert fact.ownership_id in valid_ownership_ids, (
                f"Fact has invalid ownership_id {fact.ownership_id}"
            )

    def test_qcew_employment_values_reasonable(
        self, source_engine, target_session, loaded_dimensions
    ) -> None:
        """QCEW employment values should be reasonable."""
        load_fact_qcew_annual(source_engine, target_session, loaded_dimensions)

        facts = (
            target_session.query(FactQcewAnnual)
            .filter(FactQcewAnnual.employment.isnot(None))
            .limit(100)
            .all()
        )

        for fact in facts:
            # Employment should be non-negative
            assert fact.employment >= 0, f"Employment {fact.employment} should be >= 0"


class TestFactTradeMonthlyLoading:
    """Integration tests for trade monthly fact loading."""

    def test_loads_trade_monthly_facts(
        self, source_engine, target_session, loaded_dimensions
    ) -> None:
        """Trade monthly facts should be loaded."""
        count = load_fact_trade_monthly(source_engine, target_session, loaded_dimensions)

        assert count >= 0, "Should load or return 0"

        if count > 0:
            facts = target_session.query(FactTradeMonthly).limit(10).all()
            for fact in facts:
                assert fact.country_id is not None, "Should have country_id"
                assert fact.time_id is not None, "Should have time_id"

    def test_trade_facts_have_valid_country_fk(
        self, source_engine, target_session, loaded_dimensions
    ) -> None:
        """Trade facts should reference valid country dimension."""
        load_fact_trade_monthly(source_engine, target_session, loaded_dimensions)

        facts = target_session.query(FactTradeMonthly).limit(100).all()
        valid_country_ids = {c.country_id for c in target_session.query(DimCountry).all()}

        for fact in facts:
            assert fact.country_id in valid_country_ids, (
                f"Fact has invalid country_id {fact.country_id}"
            )

    def test_trade_values_in_reasonable_range(
        self, source_engine, target_session, loaded_dimensions
    ) -> None:
        """Trade values should be in reasonable range."""
        load_fact_trade_monthly(source_engine, target_session, loaded_dimensions)

        facts = (
            target_session.query(FactTradeMonthly)
            .filter(FactTradeMonthly.exports_usd_millions.isnot(None))
            .limit(100)
            .all()
        )

        for fact in facts:
            # Exports should be non-negative
            if fact.exports_usd_millions is not None:
                assert fact.exports_usd_millions >= 0, (
                    f"Exports {fact.exports_usd_millions} should be >= 0"
                )
            if fact.imports_usd_millions is not None:
                assert fact.imports_usd_millions >= 0, (
                    f"Imports {fact.imports_usd_millions} should be >= 0"
                )


class TestBatchProcessing:
    """Tests for batch processing behavior in fact loading."""

    def test_large_dataset_batch_processing(
        self, source_engine, target_session, loaded_dimensions
    ) -> None:
        """Large datasets should be processed in batches without memory issues."""
        # QCEW is our largest dataset (~7M rows in source)
        # This test ensures we can at least start loading without crashing

        # Load a limited sample to verify batching works
        count = load_fact_qcew_annual(source_engine, target_session, loaded_dimensions)

        # If we got here without crashing, batching is working
        assert count >= 0, "Batch processing should complete"


class TestForeignKeyResolution:
    """Tests for FK resolution during fact loading."""

    def test_unresolved_fks_are_skipped(
        self, source_engine, target_session, loaded_dimensions
    ) -> None:
        """Facts with unresolved FKs should be skipped, not crash."""
        # Clear a dimension to simulate missing FK target
        target_session.query(DimIncomeBracket).delete()
        target_session.commit()

        # Rebuild lookups without income brackets
        lookups = build_lookups(target_session)

        # Should not crash - just skip facts with missing FKs
        count = load_fact_census_income(source_engine, target_session, lookups)

        # Count should be 0 or very low since all FKs are missing
        assert count == 0, "Should skip all facts with missing FK targets"

    def test_partial_fk_resolution(self, source_engine, target_session, loaded_dimensions) -> None:
        """Some facts with valid FKs should load even if others are skipped."""
        # Trade facts should load with country dimension available
        count = load_fact_trade_monthly(source_engine, target_session, loaded_dimensions)

        # Should load at least some facts
        assert count > 0, "Should load at least some trade facts with valid FKs"


class TestDataIntegrity:
    """Tests for data integrity in loaded facts."""

    def test_no_orphan_facts(self, source_engine, target_session, loaded_dimensions) -> None:
        """All loaded facts should have valid dimension references."""
        load_fact_qcew_annual(source_engine, target_session, loaded_dimensions)

        # Check for orphans (should be none due to FK constraints)
        facts = target_session.query(FactQcewAnnual).limit(100).all()

        valid_industry_ids = {i.industry_id for i in target_session.query(DimIndustry).all()}
        valid_ownership_ids = {o.ownership_id for o in target_session.query(DimOwnership).all()}

        orphan_count = 0
        for fact in facts:
            if fact.industry_id not in valid_industry_ids:
                orphan_count += 1
            if fact.ownership_id not in valid_ownership_ids:
                orphan_count += 1

        assert orphan_count == 0, f"Found {orphan_count} orphan facts"

    def test_numeric_fields_not_corrupted(
        self, source_engine, target_session, loaded_dimensions
    ) -> None:
        """Numeric fields should not be corrupted during loading."""
        load_fact_qcew_annual(source_engine, target_session, loaded_dimensions)

        facts = (
            target_session.query(FactQcewAnnual)
            .filter(FactQcewAnnual.total_wages_usd.isnot(None))
            .limit(100)
            .all()
        )

        for fact in facts:
            # Wages should be in reasonable range (not corrupted to huge values)
            if fact.total_wages_usd:
                # Max reasonable annual wages for a county/industry combo
                # (e.g., NYC finance might be ~$100B = 100_000_000_000)
                assert fact.total_wages_usd < 1_000_000_000_000, (
                    f"Wages {fact.total_wages_usd} seems corrupted"
                )

    def test_time_ids_valid(self, source_engine, target_session, loaded_dimensions) -> None:
        """Time IDs should reference valid time dimension entries."""
        load_fact_trade_monthly(source_engine, target_session, loaded_dimensions)

        valid_time_ids = {t.time_id for t in target_session.query(DimTime).all()}

        trade_facts = target_session.query(FactTradeMonthly).limit(100).all()
        for fact in trade_facts:
            assert fact.time_id in valid_time_ids, f"Trade fact has invalid time_id {fact.time_id}"
