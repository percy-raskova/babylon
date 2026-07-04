"""Spec 094: The Wire — narrator determinism, Article III, euphemism sync, provider swap.

RED-FIRST: these tests fail because ``web/game/narrator.py`` does not exist yet.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import pytest

# -- Fixtures -----------------------------------------------------------------

_META: dict[str, Any] = {
    "tick": 42,
    "session": "wayne-county-001",
    "operator": "RASKOVA-2",
    "freq": "88.7 MHz",
    "qth": "WAYNE CO / GRID EN82",
    "classification": "TS//SI//NOFORN",
    "cable_id": "1847-A",
    "page_of": "001/047",
    "timestamp_utc": "2026-05-12T08:47:22Z",
}

_EVENTS: list[dict[str, Any]] = [
    {
        "id": "evt-001",
        "type": "uprising",
        "tick": 42,
        "severity": "critical",
        "title": "Uprising",
        "body": "Workers rose up in Hamtramck",
        "data": {"org_id": "ORG001", "territory_id": "t_hamtramck"},
    },
    {
        "id": "evt-002",
        "type": "eviction_pipeline",
        "tick": 41,
        "severity": "warning",
        "title": "Eviction Pipeline",
        "body": "Eviction pipeline triggered in Dearborn",
        "data": {"territory_id": "t_dearborn"},
    },
    {
        "id": "evt-003",
        "type": "consciousness_shift",
        "tick": 40,
        "severity": "informational",
        "title": "Consciousness Shift",
        "body": "Class consciousness increased in Detroit",
        "data": {"territory_id": "t_detroit", "delta": 0.022},
    },
]


@pytest.fixture
def meta() -> dict[str, Any]:
    return dict(_META)


@pytest.fixture
def events() -> list[dict[str, Any]]:
    return [dict(e) for e in _EVENTS]


# -- US4: Narrator determinism -------------------------------------------------


class TestNarratorDeterminism:
    """Same events must produce byte-identical WireFeed output."""

    def test_two_calls_produce_identical_json(
        self, events: list[dict[str, Any]], meta: dict[str, Any]
    ) -> None:
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        out_a = narrator.narrate(events, meta)
        out_b = narrator.narrate(events, meta)

        json_a = json.dumps(out_a, sort_keys=True)
        json_b = json.dumps(out_b, sort_keys=True)
        assert json_a == json_b, "narrator output must be byte-identical for same inputs"

    def test_output_does_not_mutate_input(
        self, events: list[dict[str, Any]], meta: dict[str, Any]
    ) -> None:
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        events_before = json.dumps(events, sort_keys=True)
        meta_before = json.dumps(meta, sort_keys=True)

        narrator.narrate(events, meta)

        assert json.dumps(events, sort_keys=True) == events_before, (
            "narrator must not mutate input events"
        )
        assert json.dumps(meta, sort_keys=True) == meta_before, (
            "narrator must not mutate input meta"
        )

    def test_output_is_valid_wirefeed(
        self, events: list[dict[str, Any]], meta: dict[str, Any]
    ) -> None:
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        feed = narrator.narrate(events, meta)

        assert "meta" in feed
        assert "index" in feed
        assert "euphemisms" in feed
        assert "story" in feed
        assert "filters" in feed
        assert isinstance(feed["index"], list)
        assert isinstance(feed["euphemisms"], dict)
        assert isinstance(feed["filters"], list)
        assert len(feed["filters"]) == 5

    def test_empty_events_produces_valid_empty_feed(self, meta: dict[str, Any]) -> None:
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        feed = narrator.narrate([], meta)

        assert feed["index"] == []
        assert feed["euphemisms"] == {}
        assert feed["story"] is None
        assert len(feed["filters"]) == 5

    def test_index_has_one_entry_per_event(
        self, events: list[dict[str, Any]], meta: dict[str, Any]
    ) -> None:
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        feed = narrator.narrate(events, meta)

        assert len(feed["index"]) == len(events)

    def test_index_entries_have_three_channel_headlines(
        self, events: list[dict[str, Any]], meta: dict[str, Any]
    ) -> None:
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        feed = narrator.narrate(events, meta)

        for entry in feed["index"]:
            assert "hed" in entry
            assert "c" in entry["hed"]
            assert "l" in entry["hed"]
            assert "i" in entry["hed"]
            assert entry["hed"]["c"]
            assert entry["hed"]["l"]
            assert entry["hed"]["i"]


# -- US6: Article III structural test -----------------------------------------


class TestArticleIIIStructural:
    """The narrator must not import or use engine modules (Constitution III)."""

    def test_narrator_module_imports_no_babylon_modules(self) -> None:
        """The narrator module must not import any ``babylon.*`` modules."""
        # Force a fresh import to check what gets loaded
        mods_before = set(sys.modules.keys())
        import game.narrator  # noqa: F401

        mods_after = set(sys.modules.keys())
        new_mods = mods_after - mods_before

        babylon_imports = [m for m in new_mods if m.startswith("babylon.")]
        assert babylon_imports == [], f"narrator imported babylon modules: {babylon_imports}"

    def test_narrator_does_not_modify_global_state(
        self, events: list[dict[str, Any]], meta: dict[str, Any]
    ) -> None:
        """Running the narrator must not change any global mutable state."""
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()

        # Run twice — if there's global mutable state, the second run might differ
        out_a = narrator.narrate(events, meta)
        out_b = narrator.narrate(events, meta)

        assert json.dumps(out_a, sort_keys=True) == json.dumps(out_b, sort_keys=True)

    def test_narrator_has_no_database_access(self) -> None:
        """The narrator class must not have any DB-related attributes."""
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        # Must not have persistence, session, graph, or world_state attributes
        forbidden_attrs = ["_persistence", "_session", "_graph", "_world_state", "_db", "_pool"]
        for attr in forbidden_attrs:
            assert not hasattr(narrator, attr), f"narrator has forbidden attr: {attr}"


# -- Euphemism sync -----------------------------------------------------------


class TestEuphemismSync:
    """Every euphemism term must have c+l phrases and a valid filter."""

    VALID_FILTERS = {"ownership", "advertising", "sourcing", "flak", "ideology"}

    def test_euphemisms_have_c_and_l(
        self, events: list[dict[str, Any]], meta: dict[str, Any]
    ) -> None:
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        feed = narrator.narrate(events, meta)

        for term_id, entry in feed["euphemisms"].items():
            assert "c" in entry, f"euphemism '{term_id}' missing corporate phrase"
            assert "l" in entry, f"euphemism '{term_id}' missing liberated phrase"
            assert entry["c"], f"euphemism '{term_id}' has empty corporate phrase"
            assert entry["l"], f"euphemism '{term_id}' has empty liberated phrase"

    def test_euphemisms_have_valid_filter(
        self, events: list[dict[str, Any]], meta: dict[str, Any]
    ) -> None:
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        feed = narrator.narrate(events, meta)

        for term_id, entry in feed["euphemisms"].items():
            assert "filter" in entry, f"euphemism '{term_id}' missing filter"
            assert entry["filter"] in self.VALID_FILTERS, (
                f"euphemism '{term_id}' has invalid filter: {entry['filter']}"
            )

    def test_euphemisms_have_note(self, events: list[dict[str, Any]], meta: dict[str, Any]) -> None:
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        feed = narrator.narrate(events, meta)

        for term_id, entry in feed["euphemisms"].items():
            assert "note" in entry, f"euphemism '{term_id}' missing editorial note"
            assert entry["note"], f"euphemism '{term_id}' has empty note"

    def test_filters_have_correct_ids(
        self, events: list[dict[str, Any]], meta: dict[str, Any]
    ) -> None:
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        feed = narrator.narrate(events, meta)

        filter_ids = {f["id"] for f in feed["filters"]}
        assert filter_ids == self.VALID_FILTERS, (
            f"filter IDs must be the 5 Mfg Consent filters, got {filter_ids}"
        )

    def test_filters_have_non_negative_hits(
        self, events: list[dict[str, Any]], meta: dict[str, Any]
    ) -> None:
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        feed = narrator.narrate(events, meta)

        for f in feed["filters"]:
            assert f["hits"] >= 0, f"filter '{f['id']}' has negative hits: {f['hits']}"


# -- US5: Provider swap ------------------------------------------------------


class TestProviderSwap:
    """The NarratorProvider interface must be honored — a mock provider can be swapped in."""

    def test_narrator_provider_protocol_exists(self) -> None:
        from game.narrator import NarratorProvider

        # NarratorProvider must be a Protocol (or have the right shape)
        assert NarratorProvider is not None

    def test_deterministic_narrator_implements_protocol(self) -> None:
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        # Must have the narrate method with the right signature
        assert hasattr(narrator, "narrate")
        assert callable(narrator.narrate)

    def test_mock_provider_produces_canned_output(
        self, events: list[dict[str, Any]], meta: dict[str, Any]
    ) -> None:
        """A mock provider can be used in place of DeterministicNarrator."""

        canned_feed: dict[str, Any] = {
            "meta": meta,
            "index": [],
            "euphemisms": {},
            "story": None,
            "filters": [
                {
                    "id": "ownership",
                    "label": "Ownership",
                    "desc": "",
                    "hits": 0,
                    "color": "var(--rent)",
                },
                {
                    "id": "advertising",
                    "label": "Advertising",
                    "desc": "",
                    "hits": 0,
                    "color": "var(--heat)",
                },
                {
                    "id": "sourcing",
                    "label": "Sourcing",
                    "desc": "",
                    "hits": 0,
                    "color": "var(--cadre)",
                },
                {"id": "flak", "label": "Flak", "desc": "", "hits": 0, "color": "var(--thermal)"},
                {
                    "id": "ideology",
                    "label": "Anti-radical ideology",
                    "desc": "",
                    "hits": 0,
                    "color": "var(--laser)",
                },
            ],
        }

        class MockNarrator:
            def narrate(
                self,
                events: list[dict[str, Any]],
                meta: dict[str, Any],
                visibility: dict[str, Any] | None = None,
            ) -> dict[str, Any]:
                return dict(canned_feed)

        mock = MockNarrator()
        result = mock.narrate(events, meta)

        assert result["meta"] == meta
        assert result["story"] is None
        assert len(result["filters"]) == 5

    def test_narrator_accepts_visibility_param(
        self, events: list[dict[str, Any]], meta: dict[str, Any]
    ) -> None:
        """The narrator must accept an optional visibility parameter (no-op pass-through for spec-077)."""
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        # Must not raise when visibility is passed
        feed = narrator.narrate(events, meta, visibility={"hegemony": 0.5})
        assert "meta" in feed

    def test_visibility_param_does_not_change_output(
        self, events: list[dict[str, Any]], meta: dict[str, Any]
    ) -> None:
        """The visibility param is a no-op pass-through — same output with or without it."""
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        without_vis = narrator.narrate(events, meta)
        with_vis = narrator.narrate(events, meta, visibility={"hegemony": 0.9})

        assert json.dumps(without_vis, sort_keys=True) == json.dumps(with_vis, sort_keys=True)
