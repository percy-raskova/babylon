"""Tests for DefaultWorkingDayClassifier (Feature 021, US3)."""

from __future__ import annotations

from babylon.config.defines import WorkingDayDefines
from babylon.domain.economics.working_day.classifier import DefaultWorkingDayClassifier
from babylon.domain.economics.working_day.types import WorkingDayState
from babylon.models.enums import ExploitationMode


def _make_state(
    hours: float = 40.0,
    intensity: float = 1.0,
) -> WorkingDayState:
    """Helper to construct a WorkingDayState with defaults."""
    return WorkingDayState(
        fips_code="26163",
        naics_sector="31",
        year=2019,
        avg_weekly_hours=hours,
        labor_intensity_index=intensity,
    )


class TestClassification:
    """Tests for exploitation mode classification logic."""

    def test_absolute_dominant(self) -> None:
        """Long hours + low intensity = ABSOLUTE_DOMINANT."""
        classifier = DefaultWorkingDayClassifier()
        state = _make_state(hours=50.0, intensity=1.0)
        assert classifier.classify(state) == ExploitationMode.ABSOLUTE_DOMINANT

    def test_relative_dominant(self) -> None:
        """Standard hours + high intensity = RELATIVE_DOMINANT."""
        classifier = DefaultWorkingDayClassifier()
        state = _make_state(hours=38.0, intensity=1.5)
        assert classifier.classify(state) == ExploitationMode.RELATIVE_DOMINANT

    def test_mixed_mode(self) -> None:
        """Hours and intensity in middle range = MIXED."""
        classifier = DefaultWorkingDayClassifier()
        state = _make_state(hours=42.0, intensity=1.15)
        assert classifier.classify(state) == ExploitationMode.MIXED

    def test_high_hours_high_intensity_is_mixed(self) -> None:
        """High hours BUT high intensity = MIXED (not absolute)."""
        classifier = DefaultWorkingDayClassifier()
        state = _make_state(hours=50.0, intensity=1.5)
        assert classifier.classify(state) == ExploitationMode.MIXED

    def test_low_hours_low_intensity_is_mixed(self) -> None:
        """Low hours BUT low intensity = MIXED (not relative)."""
        classifier = DefaultWorkingDayClassifier()
        state = _make_state(hours=38.0, intensity=1.0)
        assert classifier.classify(state) == ExploitationMode.MIXED

    def test_warehouse_scenario(self) -> None:
        """Warehouse work: long hours, low productivity growth = ABSOLUTE."""
        classifier = DefaultWorkingDayClassifier()
        state = _make_state(hours=48.0, intensity=0.95)
        assert classifier.classify(state) == ExploitationMode.ABSOLUTE_DOMINANT

    def test_software_scenario(self) -> None:
        """Software: standard hours, high productivity = RELATIVE."""
        classifier = DefaultWorkingDayClassifier()
        state = _make_state(hours=37.5, intensity=2.0)
        assert classifier.classify(state) == ExploitationMode.RELATIVE_DOMINANT

    def test_gig_economy_scenario(self) -> None:
        """Gig economy: long hours, moderate intensity = ABSOLUTE."""
        classifier = DefaultWorkingDayClassifier()
        state = _make_state(hours=55.0, intensity=0.8)
        assert classifier.classify(state) == ExploitationMode.ABSOLUTE_DOMINANT

    def test_custom_thresholds(self) -> None:
        """Custom defines change classification thresholds."""
        defines = WorkingDayDefines(
            absolute_hours_threshold=50.0,
            relative_hours_threshold=35.0,
            intensity_threshold_high=1.5,
            intensity_threshold_low=1.0,
        )
        classifier = DefaultWorkingDayClassifier(defines)
        # Under default thresholds would be ABSOLUTE (45h threshold)
        # Under custom thresholds 46h < 50h, so not absolute
        state = _make_state(hours=46.0, intensity=0.9)
        assert classifier.classify(state) == ExploitationMode.MIXED


class TestVisibilityModifier:
    """Tests for consciousness visibility modifier computation."""

    def test_absolute_full_visibility(self) -> None:
        """ABSOLUTE mode has full visibility (1.0)."""
        classifier = DefaultWorkingDayClassifier()
        state = _make_state(hours=50.0, intensity=1.0)
        assert classifier.compute_visibility_modifier(state) == 1.0

    def test_relative_low_visibility(self) -> None:
        """RELATIVE mode has low visibility (0.3)."""
        classifier = DefaultWorkingDayClassifier()
        state = _make_state(hours=38.0, intensity=1.5)
        assert classifier.compute_visibility_modifier(state) == 0.3

    def test_mixed_interpolated(self) -> None:
        """MIXED mode has interpolated visibility between 0.3 and 1.0."""
        classifier = DefaultWorkingDayClassifier()
        state = _make_state(hours=42.0, intensity=1.15)
        visibility = classifier.compute_visibility_modifier(state)
        assert 0.3 < visibility < 1.0

    def test_visibility_range(self) -> None:
        """All visibility values are in [0.3, 1.0]."""
        classifier = DefaultWorkingDayClassifier()
        for hours in [0.0, 20.0, 35.0, 40.0, 42.5, 45.0, 50.0, 60.0]:
            for intensity in [0.5, 0.8, 1.0, 1.1, 1.2, 1.5, 2.0]:
                state = _make_state(hours=min(hours, 168.0), intensity=max(intensity, 0.01))
                vis = classifier.compute_visibility_modifier(state)
                assert 0.3 <= vis <= 1.0, f"Out of range at h={hours}, i={intensity}: {vis}"

    def test_custom_visibility_values(self) -> None:
        """Custom visibility values change output."""
        defines = WorkingDayDefines(
            absolute_visibility=0.8,
            relative_visibility=0.2,
        )
        classifier = DefaultWorkingDayClassifier(defines)
        absolute_state = _make_state(hours=50.0, intensity=1.0)
        assert classifier.compute_visibility_modifier(absolute_state) == 0.8
        relative_state = _make_state(hours=38.0, intensity=1.5)
        assert classifier.compute_visibility_modifier(relative_state) == 0.2

    def test_mixed_midpoint(self) -> None:
        """At threshold midpoint (42.5h), visibility is roughly midway."""
        classifier = DefaultWorkingDayClassifier()
        # 42.5 is midpoint between 40 and 45
        state = _make_state(hours=42.5, intensity=1.15)
        visibility = classifier.compute_visibility_modifier(state)
        midpoint = (0.3 + 1.0) / 2.0  # 0.65
        assert abs(visibility - midpoint) < 0.15
