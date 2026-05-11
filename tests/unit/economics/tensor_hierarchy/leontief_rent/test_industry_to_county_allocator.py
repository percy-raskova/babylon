"""Tests for Spec 057 / US4 — DefaultIndustryToCountyAllocator.

Acceptance criteria from
``specs/057-leontief-rent-integration/contracts/industry_to_county_allocator.md``:

  AC1 — Synthetic 2-county / 2-industry conservation within 1%
  AC2 — Zero-employment industry contributes zero to that county
  AC3 — Carry-forward triggered for missing (county, year=Y) when (county, Y-1) present
  AC4 — Carry-forward bounded at max_years
  AC5 — Outlier event fires for phi_hour > threshold_high
  AC6 — Window uniformly empty → NoDataSentinel
  AC7 — Determinism (dict + event order)
"""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pytest
from sqlalchemy.orm import Session
from tests.unit.economics.tensor_hierarchy.leontief_rent.conftest import FakeEventBus

from babylon.config.defines import LeontiefRentDefines
from babylon.economics.tensor import NoDataSentinel
from babylon.economics.tensor_hierarchy.leontief_rent.industry_to_county_allocator import (
    HOURS_PER_YEAR,
    DefaultIndustryToCountyAllocator,
)
from babylon.reference.schema import (
    BridgeNAICSBEA,
    DimBEAIndustry,
    DimCounty,
    DimIndustry,
    DimOwnership,
    DimState,
    DimTime,
    FactQcewAnnual,
)

# =============================================================================
# Fixture: synthetic 2-county / 2-industry / multi-year QCEW
# =============================================================================


@pytest.fixture
def fake_db(reference_sqlite_session_factory) -> Iterator[Session]:
    """In-memory SQLite seeded with a tiny synthetic QCEW + bridge fixture.

    Two counties (A, B) × two NAICS industries (N1, N2) → two BEA codes (B1, B2).
    Year 2015 has data for both counties; year 2014 also has data (used in
    carry-forward tests).

    Schema comes from the shared ``reference_sqlite_session_factory``
    (full ``NormalizedBase`` schema; unused tables are harmless).
    """
    with reference_sqlite_session_factory() as session:
        # State (required FK for dim_county)
        state = DimState(state_fips="01", state_abbrev="ZZ", state_name="Test State")
        session.add(state)
        session.flush()

        # Counties
        county_a = DimCounty(
            fips="11111",
            state_id=state.state_id,
            county_fips="111",
            county_name="County A",
        )
        county_b = DimCounty(
            fips="22222",
            state_id=state.state_id,
            county_fips="222",
            county_name="County B",
        )
        session.add_all([county_a, county_b])
        session.flush()

        # Industries (NAICS)
        ind_n1 = DimIndustry(
            naics_code="N1",
            industry_title="Industry N1",
            naics_level=2,
            has_productivity_data=False,
            has_fred_data=False,
            has_qcew_data=True,
        )
        ind_n2 = DimIndustry(
            naics_code="N2",
            industry_title="Industry N2",
            naics_level=2,
            has_productivity_data=False,
            has_fred_data=False,
            has_qcew_data=True,
        )
        session.add_all([ind_n1, ind_n2])
        session.flush()

        # BEA industries
        bea_b1 = DimBEAIndustry(bea_code="B1", industry_name="BEA B1", bea_level=3)
        bea_b2 = DimBEAIndustry(bea_code="B2", industry_name="BEA B2", bea_level=3)
        session.add_all([bea_b1, bea_b2])
        session.flush()

        # NAICS → BEA crosswalk (1-to-1 for this fixture, weight=NULL → defaults 1.0)
        session.add_all(
            [
                BridgeNAICSBEA(
                    industry_id=ind_n1.industry_id,
                    bea_industry_id=bea_b1.bea_industry_id,
                    mapping_quality="exact",
                ),
                BridgeNAICSBEA(
                    industry_id=ind_n2.industry_id,
                    bea_industry_id=bea_b2.bea_industry_id,
                    mapping_quality="exact",
                ),
            ]
        )

        # Ownership (required FK)
        ownership = DimOwnership(
            own_code="5", own_title="Private", is_government=False, is_private=True
        )
        session.add(ownership)
        session.flush()

        # Years
        t2014 = DimTime(year=2014, is_annual=True)
        t2015 = DimTime(year=2015, is_annual=True)
        session.add_all([t2014, t2015])
        session.flush()

        # 2015 QCEW: County A has 100 in N1 + 50 in N2 (national total 100/50);
        #            County B has 0 in N1 + 200 in N2 (national total now 100/250).
        # Total national 2015: B1 = 100, B2 = 250.
        for cnty, naics, emp in [
            (county_a, ind_n1, 100),
            (county_a, ind_n2, 50),
            (county_b, ind_n2, 200),
        ]:
            session.add(
                FactQcewAnnual(
                    county_id=cnty.county_id,
                    industry_id=naics.industry_id,
                    ownership_id=ownership.ownership_id,
                    time_id=t2015.time_id,
                    employment=emp,
                )
            )

        # 2014 QCEW: County A has 100/50; County B is ABSENT in 2015 N1
        # (already true above — emp=0 represented as missing row, not 0).
        # Use 2014 to set up a carry-forward scenario for year=2017 lookups.
        for cnty, naics, emp in [
            (county_a, ind_n1, 100),
            (county_a, ind_n2, 50),
            (county_b, ind_n2, 200),
        ]:
            session.add(
                FactQcewAnnual(
                    county_id=cnty.county_id,
                    industry_id=naics.industry_id,
                    ownership_id=ownership.ownership_id,
                    time_id=t2014.time_id,
                    employment=emp,
                )
            )

        session.commit()
        yield session


# =============================================================================
# AC1 — Synthetic 2-county / 2-industry conservation
# =============================================================================


@pytest.mark.unit
def test_synthetic_two_county_conservation(fake_db: Session, fake_event_bus: FakeEventBus) -> None:
    allocator = DefaultIndustryToCountyAllocator(db_session=fake_db, event_bus=fake_event_bus)
    bea_industries = ["B1", "B2"]
    # Per-industry rent: B1 = $100, B2 = $300 (synthetic units)
    phi_vector = np.array([100.0, 300.0], dtype=np.float64)
    result = allocator.allocate(phi_vector, bea_industries, year=2015)
    assert isinstance(result, dict)

    # Conservation check: sum_fips(phi_hour[fips] * total_emp_hours[fips])
    # should recover sum_i(phi_vector[i]) within tolerance.
    # Total emp 2015: A = 150 (100 N1 + 50 N2), B = 200 (0 N1 + 200 N2)
    # Total emp_hours: 150*2080 + 200*2080 = 350*2080
    # sum(phi_vector) = 100 + 300 = 400
    total_drain = sum(
        result[fips] * total_emp * HOURS_PER_YEAR
        for fips, total_emp in [("11111", 150), ("22222", 200)]
        if fips in result
    )
    expected = 400.0
    rel_err = abs(total_drain - expected) / expected
    assert rel_err < 0.01, (
        f"Conservation: got {total_drain:.4f}, expected {expected}, rel_err={rel_err:.4f}"
    )


# =============================================================================
# AC2 — Zero-employment industry contributes zero
# =============================================================================


@pytest.mark.unit
def test_zero_employment_zero_allocation(fake_db: Session, fake_event_bus: FakeEventBus) -> None:
    """County B has 0 employment in N1 → its allocation excludes B1's rent."""
    allocator = DefaultIndustryToCountyAllocator(db_session=fake_db, event_bus=fake_event_bus)
    # Only B1 has rent; B2 = 0
    phi_vector = np.array([100.0, 0.0], dtype=np.float64)
    result = allocator.allocate(phi_vector, ["B1", "B2"], year=2015)
    assert isinstance(result, dict)
    # County B has 0 employment in B1 → 0 contribution from B1; B2 rent = 0;
    # so County B's phi_hour should be 0.
    assert result["22222"] == pytest.approx(0.0, abs=1e-9)


# =============================================================================
# AC3 — Carry-forward triggered for (county, Y) when only (county, Y-1) present
# =============================================================================


@pytest.mark.unit
def test_carry_forward_one_year(fake_db: Session, fake_event_bus: FakeEventBus) -> None:
    """For year=2016 (no 2016 data), allocator carries forward from 2015 data."""
    allocator = DefaultIndustryToCountyAllocator(db_session=fake_db, event_bus=fake_event_bus)
    phi_vector = np.array([100.0, 300.0], dtype=np.float64)
    result = allocator.allocate(phi_vector, ["B1", "B2"], year=2016)
    assert isinstance(result, dict)
    assert "11111" in result
    # The fixture only has 2014 + 2015 data; 2015 is the most recent → distance=1
    cf_events = [
        e for e in fake_event_bus.history if e.type == "calibration_warning.qcew_carry_forward"
    ]
    assert len(cf_events) >= 1
    # County A's event should report look_back_distance=1 (2016-2015)
    a_events = [e for e in cf_events if e.payload["county_fips"] == "11111"]
    assert len(a_events) == 1
    assert a_events[0].payload["look_back_distance"] == 1
    assert a_events[0].payload["look_back_year"] == 2015


# =============================================================================
# AC4 — Carry-forward bounded at max_years
# =============================================================================


@pytest.mark.unit
def test_carry_forward_beyond_window(fake_db: Session, fake_event_bus: FakeEventBus) -> None:
    """For year=2025 with max_years=5, the 2014/2015 fixture is outside the
    [2020, 2025] window → no counties allocated → NoDataSentinel."""
    allocator = DefaultIndustryToCountyAllocator(
        db_session=fake_db,
        event_bus=fake_event_bus,
        defines=LeontiefRentDefines(qcew_carry_forward_max_years=5),
    )
    phi_vector = np.array([100.0, 300.0], dtype=np.float64)
    result = allocator.allocate(phi_vector, ["B1", "B2"], year=2025)
    assert isinstance(result, NoDataSentinel)


# =============================================================================
# AC5 — Outlier event fires for phi_hour > threshold_high
# =============================================================================


@pytest.mark.unit
def test_outlier_event_high(fake_db: Session, fake_event_bus: FakeEventBus) -> None:
    """Make total rent enormous so per-county phi_hour > 1000.

    With phi=$1e9 in B1 alone, County A (sole source of B1) should see:
      county_rent = 1e9 * (100/100) = 1e9
      phi_hour = 1e9 / (150 * 2080) ≈ 3205 → triggers outlier
    """
    allocator = DefaultIndustryToCountyAllocator(db_session=fake_db, event_bus=fake_event_bus)
    phi_vector = np.array([1e9, 0.0], dtype=np.float64)
    result = allocator.allocate(phi_vector, ["B1", "B2"], year=2015)
    assert isinstance(result, dict)
    assert result["11111"] > 1000.0
    outlier_events = [
        e for e in fake_event_bus.history if e.type == "calibration_warning.phi_hour_outlier"
    ]
    assert len(outlier_events) >= 1
    a_outliers = [e for e in outlier_events if e.payload["county_fips"] == "11111"]
    assert len(a_outliers) == 1


# =============================================================================
# AC6 — Window uniformly empty → NoDataSentinel
# =============================================================================


@pytest.mark.unit
def test_window_uniformly_empty_returns_sentinel(
    fake_db: Session, fake_event_bus: FakeEventBus
) -> None:
    allocator = DefaultIndustryToCountyAllocator(db_session=fake_db, event_bus=fake_event_bus)
    phi_vector = np.array([100.0, 300.0], dtype=np.float64)
    # Year 1900 has no data; window [1895, 1900] also empty
    result = allocator.allocate(phi_vector, ["B1", "B2"], year=1900)
    assert isinstance(result, NoDataSentinel)


# =============================================================================
# AC7 — Determinism (dict + event order)
# =============================================================================


@pytest.mark.unit
def test_determinism_dict_and_event_order(fake_db: Session) -> None:
    bus1 = FakeEventBus()
    bus2 = FakeEventBus()
    a1 = DefaultIndustryToCountyAllocator(db_session=fake_db, event_bus=bus1)
    a2 = DefaultIndustryToCountyAllocator(db_session=fake_db, event_bus=bus2)
    phi_vector = np.array([100.0, 300.0], dtype=np.float64)
    r1 = a1.allocate(phi_vector, ["B1", "B2"], year=2015)
    r2 = a2.allocate(phi_vector, ["B1", "B2"], year=2015)
    assert isinstance(r1, dict)
    assert isinstance(r2, dict)
    assert r1 == r2
    assert [(e.type, e.payload) for e in bus1.history] == [
        (e.type, e.payload) for e in bus2.history
    ]


# =============================================================================
# Bonus — Protocol compliance
# =============================================================================


@pytest.mark.unit
def test_default_implements_protocol(fake_db: Session, fake_event_bus: FakeEventBus) -> None:
    from babylon.economics.tensor_hierarchy.leontief_rent.industry_to_county_allocator import (
        IndustryToCountyAllocator,
    )

    allocator = DefaultIndustryToCountyAllocator(db_session=fake_db, event_bus=fake_event_bus)
    assert isinstance(allocator, IndustryToCountyAllocator)


# =============================================================================
# Validation — phi_vector shape mismatch raises
# =============================================================================


@pytest.mark.unit
def test_phi_vector_shape_mismatch_raises(fake_db: Session, fake_event_bus: FakeEventBus) -> None:
    allocator = DefaultIndustryToCountyAllocator(db_session=fake_db, event_bus=fake_event_bus)
    with pytest.raises(ValueError, match=r"phi_vector shape"):
        allocator.allocate(np.array([1.0, 2.0, 3.0]), ["B1", "B2"], year=2015)
