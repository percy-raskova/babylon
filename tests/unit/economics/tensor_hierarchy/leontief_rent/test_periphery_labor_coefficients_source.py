"""Tests for Spec 057 / US2 — DefaultPeripheryLaborCoefficientsSource.

Acceptance criteria from
``specs/057-leontief-rent-integration/contracts/periphery_labor_coefficients_source.md``:

  AC1 — Returns valid PeripheryLaborCoefficients for a year present in
        Hickel ERDI series (2015 Intensive → ERDI 8.25 broadcast across
        BEA Summary industries)
  AC2 — Returns NoDataSentinel for years outside the 1960-2017 window
  AC3 — Pass-through with structured warning on ratio < 1.0 (source layer
        does NOT clamp; warning fires via EventBus)
  AC4 — Determinism across two consecutive get_coefficients(year) calls
  AC5 — Metadata round-trips to PeripheryWageMetadata with the expected
        publication, base_year, units strings
"""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pytest
from sqlalchemy.orm import Session

from babylon.economics.tensor import NoDataSentinel
from babylon.economics.tensor_hierarchy.leontief_rent.periphery_labor_coefficients import (
    DefaultPeripheryLaborCoefficientsSource,
    PeripheryLaborCoefficientsSource,
    PeripheryWageMetadata,
)
from babylon.economics.tensor_hierarchy.types import PeripheryLaborCoefficients
from babylon.reference.schema import DimTime, FactHickelERDIAnnual
from tests.unit.economics.tensor_hierarchy.leontief_rent.conftest import FakeEventBus

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def in_memory_db_with_erdi(reference_sqlite_session_factory) -> Iterator[Session]:
    """In-memory SQLite seeded with Hickel ERDI fixtures matching the
    real CSV (2015 Intensive = 8.25, plus a synthetic axiom-violation
    row for AC3).

    Schema comes from the shared ``reference_sqlite_session_factory``
    (full ``NormalizedBase`` schema; unused tables are harmless).
    """
    with reference_sqlite_session_factory() as session:
        # Real 2015 Intensive ERDI value from babylon_hickel_final.csv
        t2015 = DimTime(year=2015, is_annual=True)
        session.add(t2015)
        session.flush()
        session.add(
            FactHickelERDIAnnual(
                time_id=t2015.time_id,
                scale_type="Intensive",
                erdi=8.25,
                annual_drain_usd_billions=9750.0,
                alpha=0.98,
                core_gain_per_capita_usd=9570.0,
                is_anchor_year=False,
                china_inflection=False,
                cumulative_drain=310126.67,
                source="Hickel_Sullivan_Zoomkawala_2021",
            )
        )

        # Synthetic axiom-violation row for AC3
        t2050 = DimTime(year=2050, is_annual=True)
        session.add(t2050)
        session.flush()
        session.add(
            FactHickelERDIAnnual(
                time_id=t2050.time_id,
                scale_type="Intensive",
                erdi=0.95,
                annual_drain_usd_billions=0.0,
                alpha=None,
                core_gain_per_capita_usd=None,
                is_anchor_year=False,
                china_inflection=False,
                cumulative_drain=None,
                source="synthetic_axiom_violation_fixture",
            )
        )
        session.commit()
        yield session


def _bea_industries() -> list[str]:
    """Synthetic BEA Summary list (matches the conftest fixture)."""
    return ["111", "211", "311", "423", "541"]


# =============================================================================
# AC1 — Returns valid coefficients for a year in the Hickel series
# =============================================================================


@pytest.mark.unit
def test_get_coefficients_present_year(
    in_memory_db_with_erdi: Session, fake_event_bus: FakeEventBus
) -> None:
    industries = _bea_industries()
    source = DefaultPeripheryLaborCoefficientsSource(
        db_session=in_memory_db_with_erdi,
        event_bus=fake_event_bus,
        bea_industries=industries,
        scale_type="Intensive",
    )

    result = source.get_coefficients(2015)
    assert isinstance(result, PeripheryLaborCoefficients), (
        f"Expected PeripheryLaborCoefficients, got {type(result).__name__}"
    )
    assert result.year == 2015
    assert result.industries == industries
    assert result.wage_ratios.shape == (len(industries),)
    assert result.wage_ratios.dtype == np.float64
    assert np.all(np.isfinite(result.wage_ratios))
    # Per Spec 057 R1: uniform broadcast of ERDI value across BEA industries.
    np.testing.assert_array_equal(result.wage_ratios, np.full(len(industries), 8.25))


# =============================================================================
# AC2 — NoDataSentinel for years outside the Hickel series window
# =============================================================================


@pytest.mark.unit
def test_get_coefficients_outside_window_pre(
    in_memory_db_with_erdi: Session, fake_event_bus: FakeEventBus
) -> None:
    source = DefaultPeripheryLaborCoefficientsSource(
        db_session=in_memory_db_with_erdi,
        event_bus=fake_event_bus,
        bea_industries=_bea_industries(),
        scale_type="Intensive",
    )

    result = source.get_coefficients(1900)
    assert isinstance(result, NoDataSentinel)
    # NoDataSentinel is falsy — confirm the project pattern works
    assert not result


@pytest.mark.unit
def test_get_coefficients_outside_window_post(
    in_memory_db_with_erdi: Session, fake_event_bus: FakeEventBus
) -> None:
    source = DefaultPeripheryLaborCoefficientsSource(
        db_session=in_memory_db_with_erdi,
        event_bus=fake_event_bus,
        bea_industries=_bea_industries(),
        scale_type="Intensive",
    )

    result = source.get_coefficients(2099)
    assert isinstance(result, NoDataSentinel)


# =============================================================================
# AC3 — Pass-through with structured warning on ratio < 1.0
# =============================================================================


@pytest.mark.unit
def test_axiom_violation_pass_through(
    in_memory_db_with_erdi: Session, fake_event_bus: FakeEventBus
) -> None:
    industries = _bea_industries()
    source = DefaultPeripheryLaborCoefficientsSource(
        db_session=in_memory_db_with_erdi,
        event_bus=fake_event_bus,
        bea_industries=industries,
        scale_type="Intensive",
    )

    # The 2050 fixture has erdi=0.95 — violates the structural axiom (ratio >= 1.0).
    result = source.get_coefficients(2050)
    assert isinstance(result, PeripheryLaborCoefficients)
    # Source layer does NOT clamp — value passes through unchanged.
    np.testing.assert_array_equal(result.wage_ratios, np.full(len(industries), 0.95))

    # At least one AxiomViolationEvent must fire. Per the contract (AC3),
    # the implementation MAY emit one event per industry OR a single
    # year-aggregate event for the uniform-broadcast case.
    axiom_events = [
        e for e in fake_event_bus.history if e.type == "calibration_warning.axiom_violation"
    ]
    assert len(axiom_events) >= 1, (
        f"Expected at least one AxiomViolationEvent, got {len(axiom_events)} "
        f"(history: {[e.type for e in fake_event_bus.history]})"
    )
    # Payload sanity: every event should reference year=2050 and ratio=0.95.
    for ev in axiom_events:
        assert ev.payload["year"] == 2050
        assert ev.payload["ratio"] == 0.95
        assert ev.payload["threshold"] == 1.0


# =============================================================================
# AC4 — Determinism across two consecutive get_coefficients(year) calls
# =============================================================================


@pytest.mark.unit
def test_determinism_repeat_query(
    in_memory_db_with_erdi: Session, fake_event_bus: FakeEventBus
) -> None:
    source = DefaultPeripheryLaborCoefficientsSource(
        db_session=in_memory_db_with_erdi,
        event_bus=fake_event_bus,
        bea_industries=_bea_industries(),
        scale_type="Intensive",
    )

    r1 = source.get_coefficients(2015)
    r2 = source.get_coefficients(2015)
    assert isinstance(r1, PeripheryLaborCoefficients)
    assert isinstance(r2, PeripheryLaborCoefficients)
    np.testing.assert_array_equal(r1.wage_ratios, r2.wage_ratios)
    assert r1.year == r2.year
    assert r1.industries == r2.industries


# =============================================================================
# AC5 — Metadata round-trips
# =============================================================================


@pytest.mark.unit
def test_metadata_shape(in_memory_db_with_erdi: Session, fake_event_bus: FakeEventBus) -> None:
    source = DefaultPeripheryLaborCoefficientsSource(
        db_session=in_memory_db_with_erdi,
        event_bus=fake_event_bus,
        bea_industries=_bea_industries(),
    )
    md = source.metadata
    assert isinstance(md, PeripheryWageMetadata)
    assert md.publication == "Hickel, Sullivan & Zoomkawala (2021) — ERDI time series"
    assert md.base_year == 2017
    assert md.units == "ERDI — dimensionless ratio (market exchange rate / PPP exchange rate)"
    assert "Global South" in md.periphery_definition
    assert (
        "uniformly" in md.industry_disaggregation.lower()
        or "broadcast" in md.industry_disaggregation.lower()
    )
    assert "annual_drain_usd_billions" in md.calibration_anchor


# =============================================================================
# Bonus — Protocol compliance check
# =============================================================================


@pytest.mark.unit
def test_default_implements_protocol(
    in_memory_db_with_erdi: Session, fake_event_bus: FakeEventBus
) -> None:
    """DefaultPeripheryLaborCoefficientsSource must satisfy the Protocol."""
    source = DefaultPeripheryLaborCoefficientsSource(
        db_session=in_memory_db_with_erdi,
        event_bus=fake_event_bus,
        bea_industries=_bea_industries(),
    )
    assert isinstance(source, PeripheryLaborCoefficientsSource)
