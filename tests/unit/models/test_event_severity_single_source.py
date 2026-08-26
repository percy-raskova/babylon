"""Archive Chronicle severity remains single-sourced from the generated table."""

from __future__ import annotations

import pytest

from babylon.models.enums.events import EventType
from babylon.models.event_severity import resolve_severity
from babylon.projection.chronicle_salience import classify_event_salience

pytestmark = pytest.mark.unit


def test_archive_chronicle_matches_the_generated_table() -> None:
    for event_type in EventType:
        expected = resolve_severity(event_type)
        actual = classify_event_salience(event_type)
        assert actual.tier == expected.tier
        assert actual.unclassified == expected.unclassified


def test_unclassified_event_uses_the_loud_warning_floor() -> None:
    salience = classify_event_salience(EventType.POPULATION_DEATH)
    assert salience.tier == "warning"
    assert salience.unclassified is True
