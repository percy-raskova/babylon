"""Unit tests for annotation management.

Feature: 003-hydrator-temporal-validation
Phase 6: Report Generation & Calibration

Tests cover:
- T060: AnnotationManager CRUD operations

TDD: These tests are written FIRST and should FAIL until implementation.
"""

from datetime import datetime

import pytest


class TestAnnotationManagerImpl:
    """Test AnnotationManagerImpl CRUD operations (T060)."""

    def test_annotation_manager_impl_exists(self) -> None:
        """AnnotationManagerImpl can be imported and instantiated."""
        from babylon.domain.economics.temporal.annotations import AnnotationManagerImpl

        manager = AnnotationManagerImpl()
        assert hasattr(manager, "annotate_transition")
        assert hasattr(manager, "get_annotations")
        assert hasattr(manager, "delete_annotation")

    def test_annotate_transition_creates_annotation(self) -> None:
        """annotate_transition creates TransitionAnnotation with correct fields."""
        from babylon.domain.economics.temporal.annotations import AnnotationManagerImpl
        from babylon.domain.economics.temporal.models import TransitionAnnotation

        manager = AnnotationManagerImpl()

        annotation = manager.annotate_transition(
            fips="26163",
            year_from=2019,
            year_to=2020,
            annotation_type="documented_shock",
            description="COVID-19 pandemic impact on employment",
            annotated_by="analyst@example.com",
        )

        assert isinstance(annotation, TransitionAnnotation)
        assert annotation.transition_key == "26163_2019_2020"
        assert annotation.annotation_type == "documented_shock"
        assert annotation.description == "COVID-19 pandemic impact on employment"
        assert annotation.annotated_by == "analyst@example.com"
        assert isinstance(annotation.annotated_at, datetime)

    def test_annotate_transition_validates_type(self) -> None:
        """annotate_transition rejects invalid annotation_type."""
        from babylon.domain.economics.temporal.annotations import AnnotationManagerImpl

        manager = AnnotationManagerImpl()

        with pytest.raises(ValueError, match="annotation_type"):
            manager.annotate_transition(
                fips="26163",
                year_from=2019,
                year_to=2020,
                annotation_type="invalid_type",  # Not in allowed types
                description="Test description",
                annotated_by="analyst@example.com",
            )

    def test_get_annotations_returns_all(self) -> None:
        """get_annotations with no filters returns all annotations."""
        from babylon.domain.economics.temporal.annotations import AnnotationManagerImpl

        manager = AnnotationManagerImpl()

        # Create multiple annotations
        manager.annotate_transition(
            fips="26163",
            year_from=2019,
            year_to=2020,
            annotation_type="documented_shock",
            description="COVID-19",
            annotated_by="analyst1",
        )
        manager.annotate_transition(
            fips="26125",
            year_from=2019,
            year_to=2020,
            annotation_type="data_quality_issue",
            description="Data revision",
            annotated_by="analyst2",
        )

        annotations = manager.get_annotations()
        assert len(annotations) == 2

    def test_get_annotations_filters_by_fips(self) -> None:
        """get_annotations filters by county FIPS code."""
        from babylon.domain.economics.temporal.annotations import AnnotationManagerImpl

        manager = AnnotationManagerImpl()

        # Create annotations for different counties
        manager.annotate_transition(
            fips="26163",
            year_from=2019,
            year_to=2020,
            annotation_type="documented_shock",
            description="Wayne County COVID",
            annotated_by="analyst",
        )
        manager.annotate_transition(
            fips="26125",
            year_from=2019,
            year_to=2020,
            annotation_type="documented_shock",
            description="Oakland County COVID",
            annotated_by="analyst",
        )

        wayne_annotations = manager.get_annotations(fips="26163")
        assert len(wayne_annotations) == 1
        assert "Wayne" in wayne_annotations[0].description

    def test_get_annotations_filters_by_year(self) -> None:
        """get_annotations filters by year_to of transition."""
        from babylon.domain.economics.temporal.annotations import AnnotationManagerImpl

        manager = AnnotationManagerImpl()

        # Create annotations for different years
        manager.annotate_transition(
            fips="26163",
            year_from=2019,
            year_to=2020,
            annotation_type="documented_shock",
            description="2020 COVID",
            annotated_by="analyst",
        )
        manager.annotate_transition(
            fips="26163",
            year_from=2020,
            year_to=2021,
            annotation_type="structural_shift",
            description="2021 recovery",
            annotated_by="analyst",
        )

        annotations_2020 = manager.get_annotations(year=2020)
        assert len(annotations_2020) == 1
        assert "2020" in annotations_2020[0].description

    def test_get_annotations_filters_by_fips_and_year(self) -> None:
        """get_annotations filters by both fips and year."""
        from babylon.domain.economics.temporal.annotations import AnnotationManagerImpl

        manager = AnnotationManagerImpl()

        # Create annotations
        manager.annotate_transition(
            fips="26163",
            year_from=2019,
            year_to=2020,
            annotation_type="documented_shock",
            description="Wayne 2020",
            annotated_by="analyst",
        )
        manager.annotate_transition(
            fips="26163",
            year_from=2020,
            year_to=2021,
            annotation_type="structural_shift",
            description="Wayne 2021",
            annotated_by="analyst",
        )
        manager.annotate_transition(
            fips="26125",
            year_from=2019,
            year_to=2020,
            annotation_type="documented_shock",
            description="Oakland 2020",
            annotated_by="analyst",
        )

        # Filter by both Wayne AND 2020
        filtered = manager.get_annotations(fips="26163", year=2020)
        assert len(filtered) == 1
        assert "Wayne 2020" in filtered[0].description

    def test_delete_annotation_removes_annotation(self) -> None:
        """delete_annotation removes annotation and returns True."""
        from babylon.domain.economics.temporal.annotations import AnnotationManagerImpl

        manager = AnnotationManagerImpl()

        manager.annotate_transition(
            fips="26163",
            year_from=2019,
            year_to=2020,
            annotation_type="documented_shock",
            description="To be deleted",
            annotated_by="analyst",
        )

        # Verify it exists
        assert len(manager.get_annotations()) == 1

        # Delete it
        result = manager.delete_annotation("26163_2019_2020")
        assert result is True

        # Verify it's gone
        assert len(manager.get_annotations()) == 0

    def test_delete_annotation_returns_false_if_not_found(self) -> None:
        """delete_annotation returns False if annotation not found."""
        from babylon.domain.economics.temporal.annotations import AnnotationManagerImpl

        manager = AnnotationManagerImpl()

        result = manager.delete_annotation("nonexistent_key")
        assert result is False


class TestAnnotationTypes:
    """Test annotation type validation."""

    def test_valid_annotation_types(self) -> None:
        """All valid annotation types are accepted."""
        from babylon.domain.economics.temporal.annotations import AnnotationManagerImpl

        manager = AnnotationManagerImpl()
        valid_types = ["documented_shock", "data_quality_issue", "structural_shift", "other"]

        for i, ann_type in enumerate(valid_types):
            annotation = manager.annotate_transition(
                fips="26163",
                year_from=2018 + i,  # Different years to avoid key conflicts
                year_to=2019 + i,
                annotation_type=ann_type,
                description=f"Test {ann_type}",
                annotated_by="analyst",
            )
            assert annotation.annotation_type == ann_type


class TestTransitionKeyGeneration:
    """Test transition key format."""

    def test_transition_key_format(self) -> None:
        """Transition key follows format '{fips}_{year_from}_{year_to}'."""
        from babylon.domain.economics.temporal.annotations import AnnotationManagerImpl

        manager = AnnotationManagerImpl()

        annotation = manager.annotate_transition(
            fips="26163",
            year_from=2019,
            year_to=2020,
            annotation_type="documented_shock",
            description="Test",
            annotated_by="analyst",
        )

        assert annotation.transition_key == "26163_2019_2020"

    def test_transition_key_uniqueness(self) -> None:
        """Creating annotation with same key overwrites previous."""
        from babylon.domain.economics.temporal.annotations import AnnotationManagerImpl

        manager = AnnotationManagerImpl()

        # Create first annotation
        manager.annotate_transition(
            fips="26163",
            year_from=2019,
            year_to=2020,
            annotation_type="documented_shock",
            description="First annotation",
            annotated_by="analyst1",
        )

        # Create second with same key
        manager.annotate_transition(
            fips="26163",
            year_from=2019,
            year_to=2020,
            annotation_type="data_quality_issue",
            description="Second annotation",
            annotated_by="analyst2",
        )

        # Should have only one annotation (latest wins)
        annotations = manager.get_annotations()
        assert len(annotations) == 1
        assert annotations[0].description == "Second annotation"
