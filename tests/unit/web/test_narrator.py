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
    {
        "id": "evt-004",
        "type": "mass_awakening",
        "tick": 39,
        "severity": "warning",
        "title": "Mass Awakening",
        "body": "Consciousness crossed the mass-awakening threshold",
        "data": {
            "target_id": "C001",
            "old_consciousness": 0.58,
            "new_consciousness": 0.63,
            "triggering_source": "C004",
        },
    },
    {
        "id": "evt-005",
        "type": "fascist_drift",
        "tick": 38,
        "severity": "warning",
        "title": "Fascist Drift",
        "body": "Class drifted fascist under entitlement pressure",
        "data": {
            "node_id": "C004",
            "fascist_pull": 0.71,
            "fascist_alignment": 0.42,
            "entitlement": 0.66,
            "solidarity": 0.12,
            "regime": "crisis",
        },
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


# -- W1.7: MASS_AWAKENING / FASCIST_DRIFT bespoke templates -------------------


class TestClassScopedBespokeTemplates:
    """MASS_AWAKENING and FASCIST_DRIFT are class-scoped, not place-scoped.

    They must render through their own bespoke templates (not
    ``_generic_template``) and must never fabricate a location — these
    events carry a social-class node id (``target_id``/``node_id``), not a
    territory, so the narrator must resolve a class subject instead of
    falling back to the hardcoded "Wayne County" default.
    """

    _MASS_AWAKENING_EVENT: dict[str, Any] = {
        "id": "evt-awakening",
        "type": "mass_awakening",
        "tick": 50,
        "severity": "warning",
        "title": "Mass Awakening",
        "body": "Consciousness crossed the mass-awakening threshold",
        "data": {
            "target_id": "C001",
            "old_consciousness": 0.58,
            "new_consciousness": 0.63,
            "triggering_source": "C004",
        },
    }

    _FASCIST_DRIFT_EVENT: dict[str, Any] = {
        "id": "evt-drift",
        "type": "fascist_drift",
        "tick": 51,
        "severity": "warning",
        "title": "Fascist Drift",
        "body": "Class drifted fascist under entitlement pressure",
        "data": {
            "node_id": "C004",
            "fascist_pull": 0.71,
            "fascist_alignment": 0.42,
            "entitlement": 0.66,
            "solidarity": 0.12,
            "regime": "crisis",
        },
    }

    def test_meta_class_names_override_the_canonical_fallback_map(
        self, meta: dict[str, Any]
    ) -> None:
        """The bridge passes real per-scenario entity names via
        ``meta["class_names"]`` — wayne_county reuses class ids with
        different names than the canonical registry (its labor-aristocracy
        class is C002 "Suburban Petty Bourgeoisie"). The narrator must
        prefer the real name: a confidently wrong canonical name is exactly
        the fabrication class these bespoke templates exist to kill."""
        from game.narrator import DeterministicNarrator

        meta["class_names"] = {"C004": "the Suburban Petty Bourgeoisie"}
        narrator = DeterministicNarrator()
        feed = narrator.narrate([self._FASCIST_DRIFT_EVENT], meta)

        assert "Suburban Petty Bourgeoisie" in feed["index"][0]["hed"]["c"]
        assert "Labor Aristocracy" not in json.dumps(feed)

    def test_class_names_meta_key_never_leaks_into_the_wire_feed(
        self, meta: dict[str, Any]
    ) -> None:
        """``class_names`` is a narrator input channel, not part of the
        wire.yaml contract — ``_build_meta``'s allowlist must drop it."""
        from game.narrator import DeterministicNarrator

        meta["class_names"] = {"C004": "the Suburban Petty Bourgeoisie"}
        narrator = DeterministicNarrator()
        feed = narrator.narrate([self._FASCIST_DRIFT_EVENT], meta)

        assert "class_names" not in feed["meta"]

    def test_mass_awakening_index_entry_uses_bespoke_slug(self, meta: dict[str, Any]) -> None:
        """The generic-template slug is f"{TITLE} · {LOCATION}"; the bespoke
        mass_awakening template uses its own AWAKENING-prefixed slug."""
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        feed = narrator.narrate([self._MASS_AWAKENING_EVENT], meta)

        assert len(feed["index"]) == 1
        assert feed["index"][0]["slug"].startswith("AWAKENING")

    def test_fascist_drift_index_entry_uses_bespoke_slug(self, meta: dict[str, Any]) -> None:
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        feed = narrator.narrate([self._FASCIST_DRIFT_EVENT], meta)

        assert len(feed["index"]) == 1
        assert feed["index"][0]["slug"].startswith("DRIFT")

    def test_mass_awakening_never_fabricates_a_location(self, meta: dict[str, Any]) -> None:
        """No rendered string may claim the fabricated default "Wayne
        County" — MASS_AWAKENING is class-scoped (target_id is a
        social-class node id), it has no territory to report."""
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        feed = narrator.narrate([self._MASS_AWAKENING_EVENT], meta)

        feed_json = json.dumps(feed)
        assert "Wayne County" not in feed_json
        assert "WAYNE COUNTY" not in feed_json.upper().replace("WAYNE CO / GRID EN82", "")

    def test_fascist_drift_never_fabricates_a_location(self, meta: dict[str, Any]) -> None:
        """FASCIST_DRIFT's node_id is not in _location_from_event's checked
        key tuple, so pre-fix every drift story fell straight to the
        "Wayne County" default — this is the bug this template fixes."""
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        feed = narrator.narrate([self._FASCIST_DRIFT_EVENT], meta)

        feed_json = json.dumps(feed)
        assert "Wayne County" not in feed_json
        assert "WAYNE COUNTY" not in feed_json.upper().replace("WAYNE CO / GRID EN82", "")

    def test_mass_awakening_resolves_class_subject_and_bespoke_euphemism(
        self, meta: dict[str, Any]
    ) -> None:
        """The story is written around the affected class (Periphery
        Proletariat, C001), and the bespoke template contributes its own
        euphemism (proof the generic template was NOT used, since
        _generic_template always produces an empty euphemisms dict)."""
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        feed = narrator.narrate([self._MASS_AWAKENING_EVENT], meta)

        assert feed["euphemisms"], "bespoke template must contribute a euphemism"
        feed_json = json.dumps(feed)
        assert "Periphery Proletariat" in feed_json

    def test_fascist_drift_resolves_class_subject_and_bespoke_euphemism(
        self, meta: dict[str, Any]
    ) -> None:
        """The story is written around the affected class (Labor
        Aristocracy, C004)."""
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        feed = narrator.narrate([self._FASCIST_DRIFT_EVENT], meta)

        assert feed["euphemisms"], "bespoke template must contribute a euphemism"
        feed_json = json.dumps(feed)
        assert "Labor Aristocracy" in feed_json

    def test_mass_awakening_intel_cites_real_payload_numbers(self, meta: dict[str, Any]) -> None:
        """Intel gives the numbers: old/new consciousness + triggering
        source, not static flavor text (contrast with the crafted-but-
        unreachable consciousness_shift template's hardcoded "+0.022")."""
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        feed = narrator.narrate([self._MASS_AWAKENING_EVENT], meta)

        intel_json = json.dumps(feed["story"]["intel"])
        assert "0.580" in intel_json
        assert "0.630" in intel_json
        assert "Labor Aristocracy" in intel_json  # triggering_source == C004

    def test_fascist_drift_intel_cites_real_payload_numbers(self, meta: dict[str, Any]) -> None:
        """Intel gives the numbers: fascist_pull/entitlement/solidarity/regime."""
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        feed = narrator.narrate([self._FASCIST_DRIFT_EVENT], meta)

        intel_json = json.dumps(feed["story"]["intel"])
        assert "0.710" in intel_json  # fascist_pull
        assert "0.420" in intel_json  # fascist_alignment
        assert "0.660" in intel_json  # entitlement
        assert "0.120" in intel_json  # solidarity
        assert "CRISIS" in intel_json  # regime

    def test_other_templates_still_use_location_not_subject(
        self, events: list[dict[str, Any]], meta: dict[str, Any]
    ) -> None:
        """Surgical check: place-scoped templates (e.g. uprising) are
        untouched — they still resolve a real location, not a class
        subject, proving the class-scoped resolution path is additive."""
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        feed = narrator.narrate(events, meta)

        uprising_entry = next(e for e in feed["index"] if e["slug"].startswith("UPRISING"))
        assert "HAMTRAMCK" in uprising_entry["slug"]


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

    def test_bridge_injects_narrator_provider(
        self, events: list[dict[str, Any]], meta: dict[str, Any]
    ) -> None:
        """The EngineBridge must honor an injected NarratorProvider (FR-094-03).

        Constructs a bridge with a MockNarrator and verifies get_wire_feed
        uses the injected provider's output, not the default DeterministicNarrator.
        """
        from unittest.mock import MagicMock

        from game.engine_bridge import EngineBridge

        canned_feed: dict[str, Any] = {
            "meta": meta,
            "index": [],
            "euphemisms": {},
            "story": {"id": "MOCK-STORY"},
            "filters": [],
        }

        class MockNarrator:
            def narrate(
                self,
                events: list[dict[str, Any]],
                meta: dict[str, Any],
                visibility: dict[str, Any] | None = None,
            ) -> dict[str, Any]:
                return dict(canned_feed)

        # Inject the mock narrator into the bridge
        persistence = MagicMock()
        bridge = EngineBridge(persistence=persistence, narrator=MockNarrator())

        # Verify the bridge uses the injected narrator
        assert isinstance(bridge._narrator, MockNarrator)

        # get_wire_feed should produce the mock's canned output
        # (we mock hydrate_state and get_journal_dashboard to avoid DB access)
        bridge._persistence = persistence
        bridge.hydrate_state = MagicMock(return_value=(MagicMock(tick=42), None))
        bridge.get_journal_dashboard = MagicMock(return_value={"events": events})

        feed = bridge.get_wire_feed(session_id=MagicMock())
        assert feed["story"] == {"id": "MOCK-STORY"}
        assert feed["meta"] == meta

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


# -- Spec-111: get_wire_feed() + NarrativeService (flag parity + augmentation) -


class TestWireFeedNarrativeServiceIntegration:
    """Spec-111: EngineBridge.get_wire_feed's narrative_service augmentation.

    Constitution II.5 (AI narrates, never adjudicates) + III.11 (loud failure).
    """

    @staticmethod
    def _expected_bridge_meta(session_id: Any, tick: int) -> dict[str, Any]:
        """Reconstruct the meta dict EngineBridge.get_wire_feed builds internally.

        get_wire_feed derives its own presentation meta from the session +
        hydrated tick (not from a caller-supplied meta) — see its docstring.
        """
        return {
            "tick": tick,
            "session": str(session_id),
            "operator": "RASKOVA-2",
            "freq": "88.7 MHz",
            "qth": "WAYNE CO / GRID EN82",
            "classification": "TS//SI//NOFORN",
            "cable_id": f"{tick:04d}-A",
            "page_of": "001/001",
            "timestamp_utc": "2026-05-12T08:47:22Z",
        }

    def test_flag_off_wire_feed_is_byte_identical_to_pre_spec_111(
        self, events: list[dict[str, Any]]
    ) -> None:
        """With BABYLON_LLM_NARRATOR off (the default), get_wire_feed's output
        must be exactly what DeterministicNarrator.narrate() produces —
        the NarrativeService augmentation must be a true no-op."""
        import uuid
        from unittest.mock import MagicMock

        from game.engine_bridge import EngineBridge
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        session_id = uuid.uuid4()
        tick = 42
        expected_meta = self._expected_bridge_meta(session_id, tick)
        direct = narrator.narrate(events, expected_meta)

        persistence = MagicMock()
        bridge = EngineBridge(persistence=persistence, narrator=narrator)
        bridge.hydrate_state = MagicMock(return_value=(MagicMock(tick=tick), None))
        bridge.get_journal_dashboard = MagicMock(return_value={"events": events})

        feed = bridge.get_wire_feed(session_id=session_id)

        assert json.dumps(feed, sort_keys=True) == json.dumps(direct, sort_keys=True)

    def test_flag_on_with_landed_result_augments_wire_feed(
        self, events: list[dict[str, Any]]
    ) -> None:
        """With the flag on and a healthy NarrativeResult already cached for
        this tick, get_wire_feed carries an ``llm_narrative`` key alongside
        the (untouched) deterministic feed."""
        import uuid
        from unittest.mock import MagicMock

        from game.engine_bridge import EngineBridge
        from game.narrative_service import NarrativeResult, NarrativeService
        from game.narrator import DeterministicNarrator

        narrator = DeterministicNarrator()
        session_id = uuid.uuid4()
        tick = 42
        expected_meta = self._expected_bridge_meta(session_id, tick)

        service = NarrativeService()
        service._results[(session_id, tick)] = NarrativeResult(
            tick=tick,
            model_id="deepseek-chat",
            prompt_version="v1",
            degraded=False,
            corporate="corp text",
            liberated="lib text",
        )

        persistence = MagicMock()
        bridge = EngineBridge(persistence=persistence, narrator=narrator, narrative_service=service)
        bridge.hydrate_state = MagicMock(return_value=(MagicMock(tick=tick), None))
        bridge.get_journal_dashboard = MagicMock(return_value={"events": events})

        with pytest.MonkeyPatch.context() as mp:
            from django.conf import settings as django_settings

            mp.setattr(django_settings, "BABYLON_LLM_NARRATOR", True, raising=False)
            feed = bridge.get_wire_feed(session_id=session_id)

        direct = narrator.narrate(events, expected_meta)
        assert feed["llm_narrative"]["degraded"] is False
        assert feed["llm_narrative"]["corporate"] == "corp text"
        # Deterministic keys are byte-identical to the un-augmented feed.
        for key in direct:
            assert feed[key] == direct[key]
