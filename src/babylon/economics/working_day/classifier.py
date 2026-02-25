"""Working Day classifier (Feature 021, FR-007/FR-011).

Classifies territory-sector pairs by exploitation mode and computes
consciousness visibility modifiers.
"""

from __future__ import annotations

from babylon.config.defines import WorkingDayDefines
from babylon.economics.working_day.types import WorkingDayState
from babylon.models.enums import ExploitationMode


class DefaultWorkingDayClassifier:
    """Classifies exploitation mode from hours and intensity data.

    Classification logic:
    - ABSOLUTE_DOMINANT: hours > absolute_threshold AND intensity < intensity_low
    - RELATIVE_DOMINANT: hours <= relative_threshold AND intensity > intensity_high
    - MIXED: everything else

    Visibility modifier:
    - ABSOLUTE: high visibility (workers experience long hours directly)
    - RELATIVE: low visibility (productivity gains are invisible to workers)
    - MIXED: interpolated between absolute and relative visibility

    Args:
        defines: Configuration with classification thresholds and visibility values.
    """

    def __init__(self, defines: WorkingDayDefines | None = None) -> None:
        self._defines = defines if defines is not None else WorkingDayDefines()

    def classify(self, state: WorkingDayState) -> ExploitationMode:
        """Classify exploitation mode for a working day state.

        Args:
            state: Working day characteristics for a territory-sector.

        Returns:
            ExploitationMode classification.
        """
        d = self._defines
        hours = state.avg_weekly_hours
        intensity = state.labor_intensity_index

        if hours > d.absolute_hours_threshold and intensity < d.intensity_threshold_low:
            return ExploitationMode.ABSOLUTE_DOMINANT
        if hours <= d.relative_hours_threshold and intensity > d.intensity_threshold_high:
            return ExploitationMode.RELATIVE_DOMINANT
        return ExploitationMode.MIXED

    def compute_visibility_modifier(self, state: WorkingDayState) -> float:
        """Compute consciousness visibility modifier for a working day state.

        Args:
            state: Working day characteristics for a territory-sector.

        Returns:
            Visibility modifier in [relative_visibility, absolute_visibility].
        """
        mode = self.classify(state)
        d = self._defines

        if mode == ExploitationMode.ABSOLUTE_DOMINANT:
            return d.absolute_visibility
        if mode == ExploitationMode.RELATIVE_DOMINANT:
            return d.relative_visibility

        # MIXED: interpolate based on hours position between thresholds
        hours = state.avg_weekly_hours
        span = d.absolute_hours_threshold - d.relative_hours_threshold
        if span <= 0.0:
            return (d.absolute_visibility + d.relative_visibility) / 2.0

        t = (hours - d.relative_hours_threshold) / span
        t = max(0.0, min(t, 1.0))
        return d.relative_visibility + t * (d.absolute_visibility - d.relative_visibility)
