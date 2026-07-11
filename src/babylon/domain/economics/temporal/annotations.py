"""Analyst annotation management for flagged transitions.

Feature: 003-hydrator-temporal-validation
Phase 6: Report Generation & Calibration

This module implements FR-006: Allow analysts to annotate flagged
transitions as "documented shock", "data quality issue", or other
categories.

See Also:
    :mod:`babylon.domain.economics.temporal.protocols`: AnnotationManager protocol
    :mod:`babylon.domain.economics.temporal.models`: TransitionAnnotation model
"""

from __future__ import annotations

from datetime import datetime

from babylon.domain.economics.temporal.models import TransitionAnnotation

VALID_ANNOTATION_TYPES: set[str] = {
    "documented_shock",
    "data_quality_issue",
    "structural_shift",
    "other",
}


class AnnotationManagerImpl:
    """Implementation of analyst annotation management.

    Manages CRUD operations for analyst annotations on flagged
    transitions. Annotations are stored in memory by default.

    Attributes:
        _annotations: Dict mapping transition_key to TransitionAnnotation.
    """

    def __init__(self) -> None:
        """Initialize annotation manager with empty storage."""
        self._annotations: dict[str, TransitionAnnotation] = {}

    def annotate_transition(
        self,
        fips: str,
        year_from: int,
        year_to: int,
        annotation_type: str,
        description: str,
        annotated_by: str,
    ) -> TransitionAnnotation:
        """Create annotation for a flagged transition.

        Args:
            fips: 5-digit county FIPS code.
            year_from: Starting year of the transition.
            year_to: Ending year of the transition.
            annotation_type: One of "documented_shock", "data_quality_issue",
                           "structural_shift", or "other".
            description: Analyst's explanation of the flag.
            annotated_by: Identifier of the analyst.

        Returns:
            TransitionAnnotation with generated transition_key and timestamp.

        Raises:
            ValueError: If annotation_type is not valid.
        """
        if annotation_type not in VALID_ANNOTATION_TYPES:
            msg = (
                f"Invalid annotation_type: {annotation_type}. "
                f"Must be one of: {VALID_ANNOTATION_TYPES}"
            )
            raise ValueError(msg)

        transition_key = f"{fips}_{year_from}_{year_to}"

        annotation = TransitionAnnotation(
            transition_key=transition_key,
            annotation_type=annotation_type,  # type: ignore[arg-type]
            description=description,
            annotated_by=annotated_by,
            annotated_at=datetime.now(),
        )

        # Store (overwrites if key exists)
        self._annotations[transition_key] = annotation

        return annotation

    def get_annotations(
        self,
        fips: str | None = None,
        year: int | None = None,
    ) -> list[TransitionAnnotation]:
        """Retrieve annotations, optionally filtered by county or year.

        Args:
            fips: Optional filter by county FIPS code.
            year: Optional filter by year_to of transition.

        Returns:
            List of matching TransitionAnnotation objects.
        """
        result: list[TransitionAnnotation] = []

        for key, annotation in self._annotations.items():
            # Parse key to extract components: {fips}_{year_from}_{year_to}
            parts = key.split("_")
            key_fips = parts[0]
            key_year_to = int(parts[2])

            # Apply filters
            if fips is not None and key_fips != fips:
                continue
            if year is not None and key_year_to != year:
                continue

            result.append(annotation)

        return result

    def delete_annotation(self, transition_key: str) -> bool:
        """Remove an annotation by its transition key.

        Args:
            transition_key: Unique key '{fips}_{year_from}_{year_to}'.

        Returns:
            True if annotation was deleted, False if not found.
        """
        if transition_key in self._annotations:
            del self._annotations[transition_key]
            return True
        return False
