"""Tests for Spec 057 / US3 — DefaultFinalDemandSource.

Acceptance criteria from
``specs/057-leontief-rent-integration/contracts/final_demand_source.md``:

  AC1 — Returns shape-correct vector for a year with data
  AC2 — _fetch returns NoDataSentinel for missing year
  AC3 — get_final_demand raises ValueError for missing year
        (Protocol legacy adapter pattern)
  AC4 — National total within tolerance (synthetic fixture: exact equality)
  AC5 — Industry order matches the configured BEA industry list
  AC6 — Determinism across repeat queries
"""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from babylon.economics.tensor import NoDataSentinel
from babylon.economics.tensor_hierarchy.leontief_rent.final_demand import (
    DefaultFinalDemandSource,
)
from babylon.economics.tensor_hierarchy.production_chain_rent import (
    FinalDemandSource as FinalDemandSourceProtocol,
)
from babylon.reference.schema import (
    DimBEAIndustry,
    DimTime,
    FactBEAFinalDemandAnnual,
    NormalizedBase,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def in_memory_db_with_final_demand() -> Iterator[Session]:
    """In-memory SQLite seeded with synthetic 3-industry final-demand fixture."""
    engine = create_engine("sqlite:///:memory:")
    NormalizedBase.metadata.create_all(
        engine,
        tables=[
            DimTime.__table__,
            DimBEAIndustry.__table__,
            FactBEAFinalDemandAnnual.__table__,
        ],
    )
    with Session(engine) as session:
        t2015 = DimTime(year=2015, is_annual=True)
        session.add(t2015)
        session.flush()

        industries = [
            DimBEAIndustry(bea_code="111", industry_name="Farms", bea_level=3),
            DimBEAIndustry(bea_code="211", industry_name="Oil", bea_level=3),
            DimBEAIndustry(bea_code="311", industry_name="Food mfg", bea_level=3),
        ]
        for ind in industries:
            session.add(ind)
        session.flush()

        values = [100_000.0, 50_000.0, 200_000.0]
        for ind, value in zip(industries, values, strict=True):
            session.add(
                FactBEAFinalDemandAnnual(
                    time_id=t2015.time_id,
                    bea_industry_id=ind.bea_industry_id,
                    total_final_uses_millions=value,
                )
            )
        session.commit()
        yield session


def _bea_industries() -> list[str]:
    return ["111", "211", "311"]


@pytest.mark.unit
def test_get_final_demand_shape(in_memory_db_with_final_demand: Session) -> None:
    industries = _bea_industries()
    source = DefaultFinalDemandSource(
        db_session=in_memory_db_with_final_demand,
        bea_industries=industries,
    )
    result = source.get_final_demand(2015)
    assert isinstance(result, np.ndarray)
    assert result.shape == (len(industries),)
    assert result.dtype == np.float64
    assert np.all(result >= 0.0)
    np.testing.assert_array_equal(result, np.array([100_000.0, 50_000.0, 200_000.0]))


@pytest.mark.unit
def test_fetch_missing_year_sentinel(in_memory_db_with_final_demand: Session) -> None:
    source = DefaultFinalDemandSource(
        db_session=in_memory_db_with_final_demand,
        bea_industries=_bea_industries(),
    )
    result = source._fetch(1900)
    assert isinstance(result, NoDataSentinel)


@pytest.mark.unit
def test_get_final_demand_missing_year_raises(in_memory_db_with_final_demand: Session) -> None:
    source = DefaultFinalDemandSource(
        db_session=in_memory_db_with_final_demand,
        bea_industries=_bea_industries(),
    )
    with pytest.raises(ValueError, match=r"No final-demand data for year 1900"):
        source.get_final_demand(1900)


@pytest.mark.unit
def test_national_total_within_tolerance(in_memory_db_with_final_demand: Session) -> None:
    source = DefaultFinalDemandSource(
        db_session=in_memory_db_with_final_demand,
        bea_industries=_bea_industries(),
    )
    result = source.get_final_demand(2015)
    expected_total = 100_000.0 + 50_000.0 + 200_000.0
    assert abs(result.sum() - expected_total) < 1e-6


@pytest.mark.unit
def test_industry_order_matches_configured_list(in_memory_db_with_final_demand: Session) -> None:
    reversed_industries = ["311", "211", "111"]
    source = DefaultFinalDemandSource(
        db_session=in_memory_db_with_final_demand,
        bea_industries=reversed_industries,
    )
    result = source.get_final_demand(2015)
    np.testing.assert_array_equal(result, np.array([200_000.0, 50_000.0, 100_000.0]))


@pytest.mark.unit
def test_determinism_repeat_query(in_memory_db_with_final_demand: Session) -> None:
    source = DefaultFinalDemandSource(
        db_session=in_memory_db_with_final_demand,
        bea_industries=_bea_industries(),
    )
    r1 = source.get_final_demand(2015)
    r2 = source.get_final_demand(2015)
    np.testing.assert_array_equal(r1, r2)


@pytest.mark.unit
def test_default_implements_protocol(in_memory_db_with_final_demand: Session) -> None:
    source = DefaultFinalDemandSource(
        db_session=in_memory_db_with_final_demand,
        bea_industries=_bea_industries(),
    )
    assert hasattr(source, "get_final_demand")
    _: FinalDemandSourceProtocol = source  # type: ignore[assignment]
    assert isinstance(source.get_final_demand(2015), np.ndarray)


@pytest.mark.unit
def test_industry_missing_from_fixture_returns_zero(
    in_memory_db_with_final_demand: Session,
) -> None:
    """Configured industry without a fact_bea_final_demand_annual row gets 0.0
    (gap-fill at source layer; FR-006 list-alignment failures are caught
    later at the pipeline level)."""
    source = DefaultFinalDemandSource(
        db_session=in_memory_db_with_final_demand,
        bea_industries=["111", "211", "311", "999_not_in_fixture"],
    )
    result = source.get_final_demand(2015)
    assert result.shape == (4,)
    assert result[3] == 0.0
