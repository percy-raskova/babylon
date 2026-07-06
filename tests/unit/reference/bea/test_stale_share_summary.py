"""T058: Unit tests for the stale-share fallback summary computation (SC-008).

Verifies that ``compute_stale_share_fallback_summary`` correctly
classifies employment by concordance-coverage status:

  - When all BEA industries have data → affected_employment_fraction = 0.0
  - When some BEA industries lack data → affected_employment_fraction > 0.0
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from babylon.reference.bea.ingest.audit_report import StaleShareFallbackSummary
from babylon.reference.bea.ingest.stale_share_summary import (
    compute_stale_share_fallback_summary,
)
from babylon.reference.schema import (
    BridgeNAICSBEA,
    DimBEAIndustry,
    DimCounty,
    DimIndustry,
    DimTime,
    FactBEANationalIndustry,
    FactQcewAnnual,
    NormalizedBase,
)


@pytest.fixture
def session_with_coverage() -> Session:
    """In-memory SQLite: 2 BEA industries, 1 with data, 1 without."""
    engine = create_engine("sqlite:///:memory:")
    NormalizedBase.metadata.create_all(
        engine,
        tables=[
            DimBEAIndustry.__table__,
            DimCounty.__table__,
            DimIndustry.__table__,
            DimTime.__table__,
            BridgeNAICSBEA.__table__,
            FactBEANationalIndustry.__table__,
            FactQcewAnnual.__table__,
        ],
    )
    session = Session(engine)
    session.execute(
        text(
            "INSERT INTO dim_bea_industry (bea_industry_id, bea_code, industry_name, bea_level, line_number) "
            "VALUES (10, '111CA', 'Farms', 3, 1), (20, '54', 'Services', 3, 2)"
        )
    )
    session.execute(
        text(
            "INSERT INTO dim_industry (industry_id, naics_code, industry_title, naics_level, "
            "has_productivity_data, has_fred_data, has_qcew_data) "
            "VALUES (100, '111110', 'Soybean Farming', 6, 0, 0, 1), "
            "       (200, '541110', 'Law Firms', 6, 0, 0, 1)"
        )
    )
    session.execute(
        text(
            "INSERT INTO bridge_naics_bea (industry_id, bea_industry_id, mapping_quality) "
            "VALUES (100, 10, 'exact'), (200, 20, 'exact')"
        )
    )
    session.execute(
        text(
            "INSERT INTO dim_county (county_id, fips, county_fips, state_id, county_name) VALUES (1, '26163', '163', 1, 'Wayne')"
        )
    )
    session.execute(text("INSERT INTO dim_time (time_id, year, is_annual) VALUES (2010, 2010, 1)"))
    # BEA national: Farms has data, Services does NOT (no row for bea_id=20)
    session.execute(
        text(
            "INSERT INTO fact_bea_national_industry "
            "(bea_industry_id, time_id, gross_output_millions, intermediate_inputs_millions, "
            " value_added_millions, vintage_published_date) "
            "VALUES (10, 2010, 1000.00, 600.00, 400.00, '2025-01-01')"
        )
    )
    # QCEW: Wayne has 800 farm workers (covered) + 200 services workers (uncovered)
    session.execute(
        text(
            "INSERT INTO fact_qcew_annual (county_id, industry_id, ownership_id, time_id, employment) "
            "VALUES (1, 100, 1, 2010, 800), (1, 200, 1, 2010, 200)"
        )
    )
    session.commit()
    yield session
    session.close()


@pytest.fixture
def session_full_coverage() -> Session:
    """In-memory SQLite: both BEA industries have data → 0% fallback."""
    engine = create_engine("sqlite:///:memory:")
    NormalizedBase.metadata.create_all(
        engine,
        tables=[
            DimBEAIndustry.__table__,
            DimCounty.__table__,
            DimIndustry.__table__,
            DimTime.__table__,
            BridgeNAICSBEA.__table__,
            FactBEANationalIndustry.__table__,
            FactQcewAnnual.__table__,
        ],
    )
    session = Session(engine)
    session.execute(
        text(
            "INSERT INTO dim_bea_industry (bea_industry_id, bea_code, industry_name, bea_level, line_number) "
            "VALUES (10, '111CA', 'Farms', 3, 1), (20, '54', 'Services', 3, 2)"
        )
    )
    session.execute(
        text(
            "INSERT INTO dim_industry (industry_id, naics_code, industry_title, naics_level, "
            "has_productivity_data, has_fred_data, has_qcew_data) "
            "VALUES (100, '111110', 'Soybean Farming', 6, 0, 0, 1), "
            "       (200, '541110', 'Law Firms', 6, 0, 0, 1)"
        )
    )
    session.execute(
        text(
            "INSERT INTO bridge_naics_bea (industry_id, bea_industry_id, mapping_quality) "
            "VALUES (100, 10, 'exact'), (200, 20, 'exact')"
        )
    )
    session.execute(
        text(
            "INSERT INTO dim_county (county_id, fips, county_fips, state_id, county_name) VALUES (1, '26163', '163', 1, 'Wayne')"
        )
    )
    session.execute(text("INSERT INTO dim_time (time_id, year, is_annual) VALUES (2010, 2010, 1)"))
    # Both industries have data
    session.execute(
        text(
            "INSERT INTO fact_bea_national_industry "
            "(bea_industry_id, time_id, gross_output_millions, intermediate_inputs_millions, "
            " value_added_millions, vintage_published_date) "
            "VALUES (10, 2010, 1000.00, 600.00, 400.00, '2025-01-01'), "
            "       (20, 2010, 1000.00, 300.00, 700.00, '2025-01-01')"
        )
    )
    # QCEW: 800 farm + 200 services
    session.execute(
        text(
            "INSERT INTO fact_qcew_annual (county_id, industry_id, ownership_id, time_id, employment) "
            "VALUES (1, 100, 1, 2010, 800), (1, 200, 1, 2010, 200)"
        )
    )
    session.commit()
    yield session
    session.close()


@pytest.mark.unit
class TestComputeStaleShareFallbackSummary:
    """T058: SC-008 stale-share fallback summary computation."""

    def test_full_coverage_yields_zero_affected_fraction(
        self, session_full_coverage: Session
    ) -> None:
        """When all BEA industries have data, affected_employment_fraction = 0.0."""
        summary = compute_stale_share_fallback_summary(session_full_coverage, range(2010, 2011))
        assert isinstance(summary, StaleShareFallbackSummary)
        assert summary.affected_employment_fraction == pytest.approx(0.0)
        assert summary.global_default_lookups == 0
        assert summary.total_county_year_lookups == 1

    def test_partial_coverage_yields_nonzero_affected_fraction(
        self, session_with_coverage: Session
    ) -> None:
        """When some BEA industries lack data, affected_employment_fraction > 0.0.

        Services (bea_id=20) has 200 workers but no fact_bea_national_industry
        row → those 200/1000 = 20% of employment is uncovered.
        """
        summary = compute_stale_share_fallback_summary(session_with_coverage, range(2010, 2011))
        assert summary.affected_employment_fraction == pytest.approx(0.2, abs=0.01)
        assert summary.total_county_year_lookups == 1

    def test_sc008_pass_threshold(
        self, session_with_coverage: Session, session_full_coverage: Session
    ) -> None:
        """SC-008: affected_employment_fraction < 0.01 to pass."""
        summary = compute_stale_share_fallback_summary(session_with_coverage, range(2010, 2011))
        # 20% uncovered → SC-008 FAIL
        assert not (summary.affected_employment_fraction < 0.01)

        summary_full = compute_stale_share_fallback_summary(
            session_full_coverage, range(2010, 2011)
        )
        # 0% uncovered → SC-008 PASS
        assert summary_full.affected_employment_fraction < 0.01
