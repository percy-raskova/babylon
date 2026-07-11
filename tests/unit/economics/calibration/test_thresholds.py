"""Unit tests for threshold calibration.

Feature: 003-hydrator-temporal-validation
Phase 6: Report Generation & Calibration

Tests cover:
- T045: Threshold calibration persistence
- T048: ThresholdCalibratorImpl

TDD: These tests are written FIRST and should FAIL until implementation.
"""

import json
import tempfile
from pathlib import Path

import pytest


class TestThresholdCalibratorImpl:
    """Test ThresholdCalibratorImpl class (T048)."""

    def test_threshold_calibrator_impl_exists(self) -> None:
        """ThresholdCalibratorImpl can be imported and instantiated."""
        from babylon.domain.economics.calibration.thresholds import ThresholdCalibratorImpl

        # Create with temp directory for persistence
        with tempfile.TemporaryDirectory() as tmpdir:
            calibrator = ThresholdCalibratorImpl(
                calibration_dir=Path(tmpdir),
                hydrator=None,  # type: ignore[arg-type]
            )
            assert hasattr(calibrator, "calibrate_national_threshold")
            assert hasattr(calibrator, "persist_threshold")
            assert hasattr(calibrator, "load_threshold")


class TestThresholdPersistence:
    """Test threshold persistence to JSON file (T045)."""

    def test_persist_threshold_creates_file(self) -> None:
        """persist_threshold creates calibration artifact JSON file."""
        from babylon.domain.economics.calibration.thresholds import ThresholdCalibratorImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            calibration_dir = Path(tmpdir)
            calibrator = ThresholdCalibratorImpl(
                calibration_dir=calibration_dir,
                hydrator=None,  # type: ignore[arg-type]
            )

            calibrator.persist_threshold(threshold=0.127, year=2022)

            # Check file exists
            artifact_path = calibration_dir / "threshold_calibration.json"
            assert artifact_path.exists()

            # Check content
            with open(artifact_path) as f:
                data = json.load(f)
            assert data["threshold"] == 0.127
            assert data["year"] == 2022

    def test_load_threshold_returns_persisted_value(self) -> None:
        """load_threshold returns previously persisted threshold."""
        from babylon.domain.economics.calibration.thresholds import ThresholdCalibratorImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            calibration_dir = Path(tmpdir)
            calibrator = ThresholdCalibratorImpl(
                calibration_dir=calibration_dir,
                hydrator=None,  # type: ignore[arg-type]
            )

            # Persist a threshold
            calibrator.persist_threshold(threshold=0.142, year=2023)

            # Load it back
            loaded = calibrator.load_threshold()
            assert loaded == pytest.approx(0.142, abs=0.001)

    def test_load_threshold_returns_none_when_not_calibrated(self) -> None:
        """load_threshold returns None if no calibration artifact exists."""
        from babylon.domain.economics.calibration.thresholds import ThresholdCalibratorImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            calibration_dir = Path(tmpdir)
            calibrator = ThresholdCalibratorImpl(
                calibration_dir=calibration_dir,
                hydrator=None,  # type: ignore[arg-type]
            )

            # No persist_threshold called
            loaded = calibrator.load_threshold()
            assert loaded is None

    def test_persist_overwrites_previous_calibration(self) -> None:
        """Persisting a new threshold overwrites the previous one."""
        from babylon.domain.economics.calibration.thresholds import ThresholdCalibratorImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            calibration_dir = Path(tmpdir)
            calibrator = ThresholdCalibratorImpl(
                calibration_dir=calibration_dir,
                hydrator=None,  # type: ignore[arg-type]
            )

            # Persist first threshold
            calibrator.persist_threshold(threshold=0.10, year=2021)
            assert calibrator.load_threshold() == pytest.approx(0.10, abs=0.001)

            # Persist second threshold
            calibrator.persist_threshold(threshold=0.15, year=2022)
            assert calibrator.load_threshold() == pytest.approx(0.15, abs=0.001)


class TestCalibrationArtifactFormat:
    """Test calibration artifact JSON format."""

    def test_artifact_contains_metadata(self) -> None:
        """Calibration artifact includes metadata fields."""
        from babylon.domain.economics.calibration.thresholds import ThresholdCalibratorImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            calibration_dir = Path(tmpdir)
            calibrator = ThresholdCalibratorImpl(
                calibration_dir=calibration_dir,
                hydrator=None,  # type: ignore[arg-type]
            )

            calibrator.persist_threshold(threshold=0.127, year=2022)

            artifact_path = calibration_dir / "threshold_calibration.json"
            with open(artifact_path) as f:
                data = json.load(f)

            # Required fields
            assert "threshold" in data
            assert "year" in data
            assert "percentile" in data
            assert "calibrated_at" in data

            # Expected values
            assert data["percentile"] == 95
            assert isinstance(data["calibrated_at"], str)  # ISO timestamp


class TestCalibrateNationalThreshold:
    """Test national threshold calibration computation."""

    def test_calibrate_requires_hydrator(self) -> None:
        """calibrate_national_threshold requires functional hydrator."""
        from babylon.domain.economics.calibration.thresholds import ThresholdCalibratorImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            calibrator = ThresholdCalibratorImpl(
                calibration_dir=Path(tmpdir),
                hydrator=None,  # type: ignore[arg-type]
            )

            # Should raise when hydrator is None
            with pytest.raises((TypeError, AttributeError)):
                calibrator.calibrate_national_threshold(years=[2020, 2021, 2022])

    def test_calibrate_requires_minimum_counties(self) -> None:
        """calibrate_national_threshold raises if insufficient counties."""
        from babylon.domain.economics.calibration.thresholds import ThresholdCalibratorImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            calibrator = ThresholdCalibratorImpl(
                calibration_dir=Path(tmpdir),
                hydrator=None,  # type: ignore[arg-type]
            )

            # min_counties validation should happen before hydrator access
            with pytest.raises(ValueError, match="min_counties"):
                calibrator.calibrate_national_threshold(
                    years=[2020, 2021],
                    min_counties=0,  # Invalid
                )


class TestThresholdValues:
    """Test threshold value constraints."""

    def test_threshold_must_be_positive(self) -> None:
        """persist_threshold rejects negative thresholds."""
        from babylon.domain.economics.calibration.thresholds import ThresholdCalibratorImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            calibrator = ThresholdCalibratorImpl(
                calibration_dir=Path(tmpdir),
                hydrator=None,  # type: ignore[arg-type]
            )

            with pytest.raises(ValueError, match="positive"):
                calibrator.persist_threshold(threshold=-0.1, year=2022)

    def test_threshold_must_be_reasonable(self) -> None:
        """persist_threshold rejects unreasonably large thresholds."""
        from babylon.domain.economics.calibration.thresholds import ThresholdCalibratorImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            calibrator = ThresholdCalibratorImpl(
                calibration_dir=Path(tmpdir),
                hydrator=None,  # type: ignore[arg-type]
            )

            with pytest.raises(ValueError, match="threshold"):
                calibrator.persist_threshold(threshold=5.0, year=2022)  # 500% is unreasonable
