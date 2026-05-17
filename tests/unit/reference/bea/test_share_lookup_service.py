"""T040-T046: Unit tests for ``BEAShareLookupService`` (spec-068 US3).

Validates the II.11 cross-subsystem contract:

* Protocol structural compliance.
* lookup_industry_share happy path + forward-fill + global default.
* lookup_county_share accounting identity + per-industry breakdown sum.
* lookup_io_coefficient returns ``None`` on miss.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from babylon.reference.bea.lookup_results import (
    CountyShareLookupResult,
    IndustryShareLookupResult,
)
from babylon.reference.bea.share_lookup_service import (
    BEAShareLookupService,
    DefaultBEAShareLookupService,
)
from babylon.reference.schema import (
    BridgeNAICSBEA,
    DimBEAIndustry,
    DimBEAIOTableType,
    DimCounty,
    DimIndustry,
    DimTime,
    FactBEAIOCoefficient,
    FactBEANationalIndustry,
    FactQcewAnnual,
    NormalizedBase,
)


@pytest.fixture
def transient_session() -> Session:
    """In-memory SQLite with the full schema needed for lookup service tests."""
    engine = create_engine("sqlite:///:memory:")
    NormalizedBase.metadata.create_all(
        engine,
        tables=[
            DimBEAIndustry.__table__,
            DimBEAIOTableType.__table__,
            DimCounty.__table__,
            DimIndustry.__table__,
            DimTime.__table__,
            BridgeNAICSBEA.__table__,
            FactBEAIOCoefficient.__table__,
            FactBEANationalIndustry.__table__,
            FactQcewAnnual.__table__,
        ],
    )
    session = Session(engine)
    # Seed minimal dimensions: 2 BEA industries, 1 NAICS, 1 county, 2 years.
    session.execute(
        text(
            "INSERT INTO dim_bea_industry "
            "(bea_industry_id, bea_code, industry_name, bea_level, line_number) "
            "VALUES (10, '111CA', 'Farms', 3, 1), "
            "       (20, '54', 'Services', 3, 2)"
        )
    )
    session.execute(
        text(
            "INSERT INTO dim_industry "
            "(industry_id, naics_code, industry_title, naics_level, "
            " has_productivity_data, has_fred_data, has_qcew_data) "
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
            "INSERT INTO dim_county (county_id, fips, county_fips, state_id, county_name) "
            "VALUES (1000, '26163', '163', 1, 'Wayne')"
        )
    )
    session.execute(
        text(
            "INSERT INTO dim_time (time_id, year, is_annual) VALUES "
            "(2010, 2010, 1), (2015, 2015, 1)"
        )
    )
    session.execute(
        text(
            "INSERT INTO dim_bea_io_table_type (id, table_type, description) "
            "VALUES (1, 'USE', 'Direct-requirements coefficients')"
        )
    )
    # National BEA: Farms 2010 — II/GO = 600/1000 = 0.6
    session.execute(
        text(
            "INSERT INTO fact_bea_national_industry "
            "(bea_industry_id, time_id, gross_output_millions, "
            " intermediate_inputs_millions, value_added_millions, vintage_published_date) "
            "VALUES (10, 2010, 1000.00, 600.00, 400.00, '2025-01-01')"
        )
    )
    # Services 2010 — II/GO = 300/1000 = 0.3
    session.execute(
        text(
            "INSERT INTO fact_bea_national_industry "
            "(bea_industry_id, time_id, gross_output_millions, "
            " intermediate_inputs_millions, value_added_millions, vintage_published_date) "
            "VALUES (20, 2010, 1000.00, 300.00, 700.00, '2025-01-01')"
        )
    )
    # QCEW: Wayne 2010 — 800 farm workers, 200 services workers
    session.execute(
        text(
            "INSERT INTO fact_qcew_annual "
            "(county_id, industry_id, ownership_id, time_id, employment) "
            "VALUES (1000, 100, 1, 2010, 800), "
            "       (1000, 200, 1, 2010, 200)"
        )
    )
    session.commit()
    yield session
    session.close()


def _make_service(session: Session) -> DefaultBEAShareLookupService:
    return DefaultBEAShareLookupService(session)


@pytest.mark.unit
class TestProtocolCompliance:
    """T040: DefaultBEAShareLookupService satisfies the Protocol structurally."""

    def test_default_implements_protocol(self, transient_session: Session) -> None:
        svc: BEAShareLookupService = _make_service(transient_session)
        # If the structural subtype check passes at runtime, the assert is trivially true.
        assert callable(svc.lookup_industry_share)
        assert callable(svc.lookup_county_share)
        assert callable(svc.lookup_io_coefficient)


@pytest.mark.unit
class TestLookupIndustryShare:
    """T041-T043: industry-share happy path, forward-fill, global default."""

    def test_present_year_direct_hit(self, transient_session: Session) -> None:
        svc = _make_service(transient_session)
        result = svc.lookup_industry_share(bea_industry_id=10, year=2010)
        assert isinstance(result, IndustryShareLookupResult)
        assert result.intermediate_inputs_share == pytest.approx(0.6)
        assert result.value_added_share == pytest.approx(0.4)
        assert result.used_fallback is False
        assert result.fallback_reason == "none"
        assert result.vintage_published_date == date(2025, 1, 1)

    def test_forward_fill_within_5_years(self, transient_session: Session) -> None:
        svc = _make_service(transient_session)
        # 2015 has no row for Farms; should walk back 5 years to 2010.
        result = svc.lookup_industry_share(bea_industry_id=10, year=2015)
        assert result.intermediate_inputs_share == pytest.approx(0.6)
        assert result.used_fallback is True
        assert result.fallback_reason == "forward_fill"

    def test_global_default_when_no_data(self, transient_session: Session) -> None:
        svc = _make_service(transient_session)
        # bea_industry_id=999 has no fact rows — global default.
        result = svc.lookup_industry_share(bea_industry_id=999, year=2010)
        assert result.intermediate_inputs_share == 0.5
        assert result.value_added_share == 0.5
        assert result.used_fallback is True
        assert result.fallback_reason == "global_default"

    def test_global_default_constant_is_spec_066_baseline(self) -> None:
        """FR-010: the fallback share preserves the spec-066 0.5 hardcode."""
        assert DefaultBEAShareLookupService.GLOBAL_FALLBACK_SHARE == 0.5


@pytest.mark.unit
class TestLookupCountyShare:
    """T044-T046: county-share accounting identity + breakdown."""

    def test_county_accounting_identity(self, transient_session: Session) -> None:
        svc = _make_service(transient_session)
        result = svc.lookup_county_share(county_fips="26163", year=2010)
        assert isinstance(result, CountyShareLookupResult)
        # Expected = weighted avg: 0.8 * 0.6 (Farms) + 0.2 * 0.3 (Services) = 0.54
        assert result.intermediate_inputs_share == pytest.approx(0.54)
        # FR-002 identity must hold (within ±0.01 of unity).
        assert abs(result.intermediate_inputs_share + result.value_added_share - 1.0) < 0.01

    def test_per_industry_breakdown_sums_to_one(self, transient_session: Session) -> None:
        svc = _make_service(transient_session)
        result = svc.lookup_county_share(county_fips="26163", year=2010)
        breakdown_sum = sum(result.per_industry_breakdown.values())
        assert abs(breakdown_sum - 1.0) < 1e-9
        assert set(result.per_industry_breakdown.keys()) == {10, 20}

    def test_unknown_county_falls_back_globally(self, transient_session: Session) -> None:
        svc = _make_service(transient_session)
        result = svc.lookup_county_share(county_fips="99999", year=2010)
        assert result.intermediate_inputs_share == 0.5
        assert result.fallback_employment_fraction == 1.0


@pytest.mark.unit
class TestLookupIOCoefficient:
    """Lookup misses return None per the contract."""

    def test_missing_returns_none(self, transient_session: Session) -> None:
        svc = _make_service(transient_session)
        # No FactBEAIOCoefficient rows in the fixture — every lookup misses.
        coef = svc.lookup_io_coefficient(source_industry_id=10, target_industry_id=20, year=2010)
        assert coef is None


def _verify_decimal_unused() -> Decimal:
    # Silence unused-import warning if Decimal is referenced lazily.
    return Decimal("0")


_ = _verify_decimal_unused
