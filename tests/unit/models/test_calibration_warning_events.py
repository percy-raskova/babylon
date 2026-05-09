"""Tests for Spec 057 CalibrationWarning event family.

Spec 057: tasks T011–T017 (RED → GREEN). Contracts:
``specs/057-leontief-rent-integration/contracts/calibration_warning.md``.

The three event types are subclasses of ``SimulationEvent`` (NOT
``EconomicEvent`` — calibration warnings carry no Currency ``amount``
and are infrastructural, not value-transfer events). Discriminator
strings follow the ``"calibration_warning.<subtype>"`` pattern per
research.md §R6.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.engine.event_bus import Event
from babylon.models.enums import EventType
from babylon.models.events import (
    AxiomViolationEvent,
    PhiHourOutlierEvent,
    QcewCarryForwardEvent,
)

# =============================================================================
# AC1 — AxiomViolationEvent round-trip through EventBus
# =============================================================================


@pytest.mark.unit
class TestAxiomViolationEvent:
    def test_roundtrip_via_event_bus(self) -> None:
        typed = AxiomViolationEvent(
            tick=5,
            industry="111",
            year=2015,
            ratio=0.95,
        )
        bus_event = Event(
            type=EventType.CALIBRATION_AXIOM_VIOLATION.value,
            tick=typed.tick,
            payload=typed.model_dump(),
        )
        # Round-trip the payload back into the typed class.
        recovered = AxiomViolationEvent.model_validate(bus_event.payload)
        assert recovered.industry == "111"
        assert recovered.year == 2015
        assert recovered.ratio == 0.95
        assert recovered.threshold == 1.0

    def test_default_threshold(self) -> None:
        ev = AxiomViolationEvent(tick=0, industry="X", year=2010, ratio=0.5)
        assert ev.threshold == 1.0

    def test_default_event_type(self) -> None:
        ev = AxiomViolationEvent(tick=0, industry="X", year=2010, ratio=0.5)
        assert ev.event_type == EventType.CALIBRATION_AXIOM_VIOLATION

    def test_year_validation(self) -> None:
        with pytest.raises(ValidationError):
            AxiomViolationEvent(tick=0, industry="X", year=1899, ratio=0.5)
        with pytest.raises(ValidationError):
            AxiomViolationEvent(tick=0, industry="X", year=2101, ratio=0.5)


# =============================================================================
# AC2 + AC4 — QcewCarryForwardEvent boundary values
# =============================================================================


@pytest.mark.unit
class TestQcewCarryForwardEvent:
    def test_zero_distance_accepted(self) -> None:
        ev = QcewCarryForwardEvent(
            tick=1,
            county_fips="26163",
            year=2015,
            look_back_year=2015,
            look_back_distance=0,
        )
        assert ev.look_back_distance == 0

    def test_max_distance_accepted(self) -> None:
        ev = QcewCarryForwardEvent(
            tick=1,
            county_fips="26163",
            year=2015,
            look_back_year=1995,
            look_back_distance=20,
        )
        assert ev.look_back_distance == 20

    def test_distance_too_large_rejected(self) -> None:
        with pytest.raises(ValidationError):
            QcewCarryForwardEvent(
                tick=1,
                county_fips="26163",
                year=2015,
                look_back_year=1994,
                look_back_distance=21,
            )

    def test_default_event_type(self) -> None:
        ev = QcewCarryForwardEvent(
            tick=1, county_fips="26163", year=2015, look_back_year=2014, look_back_distance=1
        )
        assert ev.event_type == EventType.CALIBRATION_QCEW_CARRY_FORWARD


# =============================================================================
# AC3 — PhiHourOutlierEvent default thresholds
# =============================================================================


@pytest.mark.unit
class TestPhiHourOutlierEvent:
    def test_default_thresholds(self) -> None:
        ev = PhiHourOutlierEvent(tick=2, county_fips="26163", phi_hour=1500.0)
        assert ev.threshold_low == -1000.0
        assert ev.threshold_high == 1000.0

    def test_custom_thresholds(self) -> None:
        ev = PhiHourOutlierEvent(
            tick=2,
            county_fips="26163",
            phi_hour=42.0,
            threshold_low=0.0,
            threshold_high=100.0,
        )
        assert ev.threshold_low == 0.0
        assert ev.threshold_high == 100.0

    def test_default_event_type(self) -> None:
        ev = PhiHourOutlierEvent(tick=2, county_fips="26163", phi_hour=2000.0)
        assert ev.event_type == EventType.CALIBRATION_PHI_HOUR_OUTLIER


# =============================================================================
# AC5 — Discriminator string format "calibration_warning.<subtype>"
# =============================================================================


@pytest.mark.unit
class TestEventTypeDiscriminators:
    def test_axiom_violation_string(self) -> None:
        assert EventType.CALIBRATION_AXIOM_VIOLATION.value == "calibration_warning.axiom_violation"

    def test_qcew_carry_forward_string(self) -> None:
        assert (
            EventType.CALIBRATION_QCEW_CARRY_FORWARD.value
            == "calibration_warning.qcew_carry_forward"
        )

    def test_phi_hour_outlier_string(self) -> None:
        assert (
            EventType.CALIBRATION_PHI_HOUR_OUTLIER.value == "calibration_warning.phi_hour_outlier"
        )

    def test_all_three_share_calibration_warning_prefix(self) -> None:
        for member in (
            EventType.CALIBRATION_AXIOM_VIOLATION,
            EventType.CALIBRATION_QCEW_CARRY_FORWARD,
            EventType.CALIBRATION_PHI_HOUR_OUTLIER,
        ):
            assert member.value.startswith("calibration_warning.")
