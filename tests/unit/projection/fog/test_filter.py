"""Track 1 / Task 4 (2026-07-18): ``apply_fog`` — the fog filter itself.

Two-layer model (spec-117 §5a): the MATERIAL layer (production, wages,
rent, demographics, territory) is public record, always visible, never
gated. The POLITICAL layer (:data:`babylon.projection.fog.filter.POLITICAL_FIELDS`) is
visible only within organizing ``reach``, or via a session
:class:`~babylon.projection.fog.ledger.IntelLedger` entry (which ages exact -> approximate
-> unknown per :func:`babylon.projection.fog.ledger.read_intel` — this module never
re-derives that aging, it only calls it).

Mirrors ``engine_bridge._apply_class_vision_gate``'s three-tier shape
(desert/mud/water -> masked/approximate/exact), generalized to any node
type and payload rather than social_class specifically.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

STALENESS_TICKS = 5
UNKNOWN_TICKS = 20


def _territory_payload() -> dict[str, object]:
    """A ``_serialize_territory``-shaped payload with every political field
    carrying a REAL (non-None) value — including the three fields that are
    hardcoded ``None`` in the shipped serializer today (``consciousness``/
    ``solidarity``/``dominant_community``, the "accidental null trap") —
    so masking behavior is exercised uniformly across the whole set."""
    return {
        "id": "T1",
        "name": "Home Territory",
        "population": 50_000,
        "wealth": 1234.5,
        "rent_level": 0.4,
        "heat": 0.62,
        "agitation": 0.51,
        "solidarity_index": 0.33,
        "dominant_class": "core_proletariat",
        "consciousness": 0.77,
        "solidarity": 0.44,
        "dominant_community": "detroit_proletariat",
    }


class TestInsideReachIsExact:
    def test_political_fields_untouched_and_vision_lists_empty(self) -> None:
        from babylon.projection.fog.filter import apply_fog
        from babylon.projection.fog.ledger import IntelLedger

        payload = _territory_payload()
        result = apply_fog(
            payload,
            node_type="territory",
            node_id="T1",
            reach=frozenset({"T1"}),
            ledger=IntelLedger(),
            tick=100,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert result["heat"] == 0.62
        assert result["agitation"] == 0.51
        assert result["solidarity_index"] == 0.33
        assert result["dominant_class"] == "core_proletariat"
        assert result["consciousness"] == 0.77
        assert result["solidarity"] == 0.44
        assert result["dominant_community"] == "detroit_proletariat"
        assert result["vision_masked"] == []
        assert result["vision_approx"] == []

    def test_material_fields_untouched(self) -> None:
        from babylon.projection.fog.filter import apply_fog
        from babylon.projection.fog.ledger import IntelLedger

        payload = _territory_payload()
        result = apply_fog(
            payload,
            node_type="territory",
            node_id="T1",
            reach=frozenset({"T1"}),
            ledger=IntelLedger(),
            tick=100,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert result["population"] == 50_000
        assert result["wealth"] == 1234.5
        assert result["rent_level"] == 0.4

    def test_reach_wins_even_with_a_stale_ledger_present(self) -> None:
        """Reach is checked BEFORE the ledger — a node the org can see
        directly is exact regardless of what stale intel might say."""
        from babylon.projection.fog.filter import apply_fog
        from babylon.projection.fog.ledger import IntelEntry, IntelLedger

        payload = _territory_payload()
        stale_ledger = IntelLedger().append(
            IntelEntry(
                node_id="T1",
                field_group="territory:political",
                tick_observed=0,
                value_snapshot={"heat": 0.01},
            )
        )
        result = apply_fog(
            payload,
            node_type="territory",
            node_id="T1",
            reach=frozenset({"T1"}),
            ledger=stale_ledger,
            tick=1000,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert result["heat"] == 0.62


class TestOutsideReachNoLedgerIsMasked:
    def test_every_political_field_is_null_and_listed(self) -> None:
        from babylon.projection.fog.filter import apply_fog
        from babylon.projection.fog.ledger import IntelLedger

        payload = _territory_payload()
        result = apply_fog(
            payload,
            node_type="territory",
            node_id="T1",
            reach=frozenset(),  # T1 not in reach
            ledger=IntelLedger(),
            tick=100,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        political_fields = (
            "heat",
            "agitation",
            "solidarity_index",
            "dominant_class",
            "consciousness",
            "solidarity",
            "dominant_community",
        )
        for field in political_fields:
            assert result[field] is None, field
        assert set(result["vision_masked"]) == set(political_fields)
        assert result["vision_approx"] == []

    def test_material_fields_untouched_and_exact(self) -> None:
        from babylon.projection.fog.filter import apply_fog
        from babylon.projection.fog.ledger import IntelLedger

        payload = _territory_payload()
        result = apply_fog(
            payload,
            node_type="territory",
            node_id="T1",
            reach=frozenset(),
            ledger=IntelLedger(),
            tick=100,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert result["population"] == 50_000
        assert result["wealth"] == 1234.5
        assert result["rent_level"] == 0.4
        assert result["id"] == "T1"
        assert result["name"] == "Home Territory"

    def test_already_none_political_fields_are_not_listed_as_masked(self) -> None:
        """Honest absence is not the same as withheld data (mirrors
        ``_apply_class_vision_gate``'s "already-None isn't masked" rule) —
        a field that was never populated must not be claimed as hidden."""
        from babylon.projection.fog.filter import apply_fog
        from babylon.projection.fog.ledger import IntelLedger

        payload = {"id": "T2", "heat": 0.5, "consciousness": None}
        result = apply_fog(
            payload,
            node_type="territory",
            node_id="T2",
            reach=frozenset(),
            ledger=IntelLedger(),
            tick=100,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert result["consciousness"] is None
        assert "consciousness" not in result["vision_masked"]
        assert result["vision_masked"] == ["heat"]


class TestAccidentalNullFieldsGetGatedOnceReal:
    """The trap: ``consciousness``/``solidarity``/``dominant_community`` are
    hardcoded ``None`` in ``_serialize_territory`` TODAY — honest by
    accident, not by gating. This pins that once real values arrive, the
    SAME gate already redacts them outside reach; it must not need to be
    re-added later."""

    def test_real_values_outside_reach_are_redacted(self) -> None:
        from babylon.projection.fog.filter import apply_fog
        from babylon.projection.fog.ledger import IntelLedger

        payload = {
            "id": "T1",
            "consciousness": 0.9,
            "solidarity": 0.8,
            "dominant_community": "detroit_proletariat",
        }
        result = apply_fog(
            payload,
            node_type="territory",
            node_id="T1",
            reach=frozenset(),
            ledger=IntelLedger(),
            tick=100,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert result["consciousness"] is None
        assert result["solidarity"] is None
        assert result["dominant_community"] is None
        assert set(result["vision_masked"]) == {
            "consciousness",
            "solidarity",
            "dominant_community",
        }


class TestOutsideReachWithFreshLedgerIsExact:
    def test_fresh_ledger_entry_serves_its_snapshot_verbatim(self) -> None:
        from babylon.projection.fog.filter import apply_fog
        from babylon.projection.fog.ledger import IntelEntry, IntelLedger

        payload = _territory_payload()
        ledger = IntelLedger().append(
            IntelEntry(
                node_id="T1",
                field_group="territory:political",
                tick_observed=95,  # age 5 <= STALENESS_TICKS at tick=100
                value_snapshot={
                    "heat": 0.734,
                    "agitation": 0.21,
                    "solidarity_index": 0.5,
                    "dominant_class": "lumpenproletariat",
                    "consciousness": 0.6,
                    "solidarity": 0.3,
                    "dominant_community": "dearborn_workers",
                },
            )
        )

        result = apply_fog(
            payload,
            node_type="territory",
            node_id="T1",
            reach=frozenset(),
            ledger=ledger,
            tick=100,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert result["heat"] == 0.734
        assert result["dominant_class"] == "lumpenproletariat"
        assert result["dominant_community"] == "dearborn_workers"
        assert result["vision_masked"] == []
        assert result["vision_approx"] == []

    def test_ledger_field_not_captured_by_the_snapshot_is_still_masked(self) -> None:
        """One INVESTIGATE resolution need not capture every political
        field; whatever it didn't observe stays honestly unknown even
        though the field_group's aging clock is fresh."""
        from babylon.projection.fog.filter import apply_fog
        from babylon.projection.fog.ledger import IntelEntry, IntelLedger

        payload = _territory_payload()
        ledger = IntelLedger().append(
            IntelEntry(
                node_id="T1",
                field_group="territory:political",
                tick_observed=100,
                value_snapshot={"heat": 0.734},  # only heat observed
            )
        )

        result = apply_fog(
            payload,
            node_type="territory",
            node_id="T1",
            reach=frozenset(),
            ledger=ledger,
            tick=100,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert result["heat"] == 0.734
        assert "heat" not in result["vision_masked"]
        assert result["dominant_class"] is None
        assert "dominant_class" in result["vision_masked"]


class TestOutsideReachWithAgedLedgerIsApproximate:
    def test_aged_entry_renders_quantized_and_marked_approx(self) -> None:
        from babylon.projection.fog.filter import apply_fog
        from babylon.projection.fog.ledger import IntelEntry, IntelLedger

        payload = _territory_payload()
        ledger = IntelLedger().append(
            IntelEntry(
                node_id="T1",
                field_group="territory:political",
                tick_observed=100,
                value_snapshot={"heat": 0.734, "dominant_class": "core_proletariat"},
            )
        )

        result = apply_fog(
            payload,
            node_type="territory",
            node_id="T1",
            reach=frozenset(),
            ledger=ledger,
            tick=100 + STALENESS_TICKS + 1,  # aged past exact, still <= unknown
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert result["heat"] != 0.734
        assert isinstance(result["heat"], float)
        assert result["dominant_class"] == "core_proletariat"  # non-numeric passes through
        assert "heat" in result["vision_approx"]


class TestOutsideReachWithStaleLedgerIsUnknown:
    def test_stale_entry_is_masked_like_no_entry_at_all(self) -> None:
        from babylon.projection.fog.filter import apply_fog
        from babylon.projection.fog.ledger import IntelEntry, IntelLedger

        payload = _territory_payload()
        ledger = IntelLedger().append(
            IntelEntry(
                node_id="T1",
                field_group="territory:political",
                tick_observed=0,
                value_snapshot={"heat": 0.734},
            )
        )

        result = apply_fog(
            payload,
            node_type="territory",
            node_id="T1",
            reach=frozenset(),
            ledger=ledger,
            tick=0 + UNKNOWN_TICKS + 1,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert result["heat"] is None
        assert "heat" in result["vision_masked"]


class TestPurity:
    def test_same_inputs_yield_equal_outputs_every_time(self) -> None:
        from babylon.projection.fog.filter import apply_fog
        from babylon.projection.fog.ledger import IntelEntry, IntelLedger

        payload = _territory_payload()
        ledger = IntelLedger().append(
            IntelEntry(
                node_id="T1",
                field_group="territory:political",
                tick_observed=90,
                value_snapshot={"heat": 0.5},
            )
        )
        reach = frozenset({"OTHER"})

        first = apply_fog(
            payload,
            node_type="territory",
            node_id="T1",
            reach=reach,
            ledger=ledger,
            tick=100,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )
        second = apply_fog(
            payload,
            node_type="territory",
            node_id="T1",
            reach=reach,
            ledger=ledger,
            tick=100,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert first == second

    def test_input_payload_is_never_mutated(self) -> None:
        from babylon.projection.fog.filter import apply_fog
        from babylon.projection.fog.ledger import IntelLedger

        payload = _territory_payload()
        original = dict(payload)

        result = apply_fog(
            payload,
            node_type="territory",
            node_id="T1",
            reach=frozenset(),
            ledger=IntelLedger(),
            tick=100,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert payload == original
        assert result is not payload

    def test_never_reads_module_level_session_globals(self) -> None:
        """Static sentinel: ``babylon.projection.fog.filter`` must never reference the
        four forbidden per-process session dicts
        (``_session_action_history``/``_session_trap_state``/
        ``_session_endgame_detectors``/``_session_causal_observers``) —
        determinism requires it be a pure function of its explicit args."""
        import inspect

        from babylon.projection.fog import filter as fog_filter

        source = inspect.getsource(fog_filter)
        for forbidden in (
            "_session_action_history",
            "_session_trap_state",
            "_session_endgame_detectors",
            "_session_causal_observers",
        ):
            assert forbidden not in source


class TestOrgPoliticalFields:
    """Track 1 / Task 5 §B: an organization's internal state
    (``consciousness_tendency``/``cohesion``/``cadre_level``, plus the
    shared ``heat``) gates through the SAME ``apply_fog`` primitive as
    territory political fields — just with a wider ``political_fields``
    tuple, never a forked gate or a second copied field list."""

    def _org_payload(self) -> dict[str, object]:
        return {
            "id": "ORG1",
            "name": "Rival Committee",
            "budget": 500.0,
            "territory_ids": ["T1", "T2"],
            "heat": 0.42,
            "cohesion": 0.6,
            "cadre_level": 0.3,
            "consciousness_tendency": "reformist",
        }

    def test_org_internal_fields_are_in_the_org_political_set(self) -> None:
        from babylon.projection.fog.filter import ORG_POLITICAL_FIELDS, POLITICAL_FIELDS

        for field in ("consciousness_tendency", "cohesion", "cadre_level", "heat"):
            assert field in ORG_POLITICAL_FIELDS
        # heat is shared with POLITICAL_FIELDS, not duplicated in the org-only tuple.
        assert "heat" in POLITICAL_FIELDS

    def test_default_apply_fog_call_does_not_gate_org_internal_fields(self) -> None:
        """Without political_fields=ORG_POLITICAL_FIELDS, cohesion/cadre_level/
        consciousness_tendency are outside the default POLITICAL_FIELDS set
        and pass through untouched — proving the org tuple is what does the
        gating, not some implicit behavior."""
        from babylon.projection.fog.filter import apply_fog
        from babylon.projection.fog.ledger import IntelLedger

        payload = self._org_payload()
        result = apply_fog(
            payload,
            node_type="organization",
            node_id="ORG1",
            reach=frozenset(),
            ledger=IntelLedger(),
            tick=100,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert result["cohesion"] == 0.6
        assert result["cadre_level"] == 0.3
        assert result["consciousness_tendency"] == "reformist"
        # heat IS in the default POLITICAL_FIELDS, so it's masked either way.
        assert result["heat"] is None

    def test_org_political_fields_masks_internal_state_outside_reach(self) -> None:
        from babylon.projection.fog.filter import ORG_POLITICAL_FIELDS, apply_fog
        from babylon.projection.fog.ledger import IntelLedger

        payload = self._org_payload()
        result = apply_fog(
            payload,
            node_type="organization",
            node_id="ORG1",
            reach=frozenset(),  # ORG1 not in reach -> rival org
            ledger=IntelLedger(),
            tick=100,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
            political_fields=ORG_POLITICAL_FIELDS,
        )

        assert result["heat"] is None
        assert result["cohesion"] is None
        assert result["cadre_level"] is None
        assert result["consciousness_tendency"] is None
        assert set(result["vision_masked"]) == {
            "heat",
            "cohesion",
            "cadre_level",
            "consciousness_tendency",
        }
        # Material fields untouched.
        assert result["budget"] == 500.0
        assert result["territory_ids"] == ["T1", "T2"]

    def test_org_political_fields_exact_inside_reach(self) -> None:
        from babylon.projection.fog.filter import ORG_POLITICAL_FIELDS, apply_fog
        from babylon.projection.fog.ledger import IntelLedger

        payload = self._org_payload()
        result = apply_fog(
            payload,
            node_type="organization",
            node_id="ORG1",
            reach=frozenset({"ORG1"}),  # e.g. the player's own org
            ledger=IntelLedger(),
            tick=100,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
            political_fields=ORG_POLITICAL_FIELDS,
        )

        assert result["heat"] == 0.42
        assert result["cohesion"] == 0.6
        assert result["cadre_level"] == 0.3
        assert result["consciousness_tendency"] == "reformist"
        assert result["vision_masked"] == []


class TestLedgerFromEventsEndToEnd:
    """Track 1 / Task 3 (2026-07-18): proves the APPROXIMATE tier is
    reachable through the REAL production writer
    (:func:`babylon.projection.fog.ledger.ledger_from_events`), not just via a
    hand-built :class:`~babylon.projection.fog.ledger.IntelEntry` fixture. Before this
    task ``IntelLedger`` had no writer at all, so this tier had never once
    fired in production — every prior ``apply_fog`` test that reached
    ``"approximate"`` constructed the ledger entry directly."""

    def test_a_persisted_investigate_row_aged_into_the_approximate_window_quantizes(
        self,
    ) -> None:
        from babylon.projection.fog.filter import apply_fog
        from babylon.projection.fog.ledger import ledger_from_events

        row = {
            "tick": 100,
            "target_id": "T1",
            "field_group": "territory:political",
            "value_snapshot": {"heat": 0.734, "dominant_class": "core_proletariat"},
        }
        ledger = ledger_from_events([row])

        result = apply_fog(
            _territory_payload(),
            node_type="territory",
            node_id="T1",
            reach=frozenset(),  # out of reach — the ledger is the only source
            ledger=ledger,
            tick=100 + STALENESS_TICKS + 1,  # aged past exact, still <= unknown
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert result["heat"] != 0.734  # quantized, not the raw observed value
        assert result["heat"] is not None  # not masked either
        assert isinstance(result["heat"], float)
        assert "heat" in result["vision_approx"]
        assert "heat" not in result["vision_masked"]
        assert result["dominant_class"] == "core_proletariat"  # non-numeric passes through


class TestFieldsAbsentFromPayloadAreIgnored:
    def test_a_political_field_the_composer_never_produced_is_not_invented(self) -> None:
        from babylon.projection.fog.filter import apply_fog
        from babylon.projection.fog.ledger import IntelLedger

        payload = {"id": "ORG1", "budget": 100.0, "heat": 0.4}
        result = apply_fog(
            payload,
            node_type="organization",
            node_id="ORG1",
            reach=frozenset(),
            ledger=IntelLedger(),
            tick=100,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert "dominant_class" not in result
        assert "consciousness" not in result
        assert result["heat"] is None
        assert result["vision_masked"] == ["heat"]
