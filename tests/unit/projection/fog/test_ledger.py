"""Track 1 / Task 3 (2026-07-18): the intel ledger.

The ledger is session-scoped, event-sourced from INVESTIGATE resolutions,
and append-only. Visibility (``read_intel``) is a PURE FUNCTION of
``(ledger, tick)`` — no decay simulation, no feedback into the engine, no
mutation. This is deliberately distinct from the engine-side
``investigation_intel`` scalar (``territory.py:221-233``), which lives in
the tick hash; nothing here touches that.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

STALENESS_TICKS = 5
UNKNOWN_TICKS = 20


def _entry(node_id: str = "T1", field_group: str = "political", tick_observed: int = 10):
    from babylon.projection.fog.ledger import IntelEntry

    return IntelEntry(
        node_id=node_id,
        field_group=field_group,
        tick_observed=tick_observed,
        value_snapshot={"heat": 0.734, "dominant_class": "core_proletariat"},
    )


class TestFreshEntryIsExact:
    def test_fresh_entry_reads_exact(self) -> None:
        from babylon.projection.fog.ledger import IntelLedger, read_intel

        ledger = IntelLedger().append(_entry(tick_observed=10))

        reading = read_intel(
            ledger,
            node_id="T1",
            field_group="political",
            tick=12,  # age 2 <= STALENESS_TICKS
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert reading.tier == "exact"
        assert reading.value_snapshot == {"heat": 0.734, "dominant_class": "core_proletariat"}
        assert reading.tick_observed == 10

    def test_exact_at_the_staleness_boundary_inclusive(self) -> None:
        """age == staleness_ticks is still exact (boundary is inclusive on
        the fresh side, per the plan's 'fresher than' / 'older' split)."""
        from babylon.projection.fog.ledger import IntelLedger, read_intel

        ledger = IntelLedger().append(_entry(tick_observed=10))

        reading = read_intel(
            ledger,
            node_id="T1",
            field_group="political",
            tick=10 + STALENESS_TICKS,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert reading.tier == "exact"


class TestAgedEntryIsApproximate:
    def test_aged_entry_reads_approximate_and_quantizes_numeric_fields(self) -> None:
        from babylon.projection.fog.ledger import IntelLedger, read_intel

        ledger = IntelLedger().append(_entry(tick_observed=10))

        reading = read_intel(
            ledger,
            node_id="T1",
            field_group="political",
            tick=10 + STALENESS_TICKS + 1,  # just past fresh, still <= unknown
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert reading.tier == "approximate"
        assert reading.value_snapshot is not None
        # Numeric field quantized onto a coarser grid, not the raw value.
        assert reading.value_snapshot["heat"] != 0.734
        assert isinstance(reading.value_snapshot["heat"], float)
        # Non-numeric fields pass through untouched.
        assert reading.value_snapshot["dominant_class"] == "core_proletariat"

    def test_approximate_at_the_unknown_boundary_inclusive(self) -> None:
        from babylon.projection.fog.ledger import IntelLedger, read_intel

        ledger = IntelLedger().append(_entry(tick_observed=10))

        reading = read_intel(
            ledger,
            node_id="T1",
            field_group="political",
            tick=10 + UNKNOWN_TICKS,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert reading.tier == "approximate"


class TestStaleEntryIsUnknown:
    def test_stale_entry_reads_unknown(self) -> None:
        from babylon.projection.fog.ledger import IntelLedger, read_intel

        ledger = IntelLedger().append(_entry(tick_observed=10))

        reading = read_intel(
            ledger,
            node_id="T1",
            field_group="political",
            tick=10 + UNKNOWN_TICKS + 1,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert reading.tier == "unknown"
        assert reading.value_snapshot is None
        assert reading.tick_observed is None

    def test_never_observed_is_unknown(self) -> None:
        """No entry at all for this (node_id, field_group) — honest unknown,
        never a fabricated default (Constitution III.11)."""
        from babylon.projection.fog.ledger import IntelLedger, read_intel

        reading = read_intel(
            IntelLedger(),
            node_id="T-NEVER-SEEN",
            field_group="political",
            tick=100,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert reading.tier == "unknown"
        assert reading.value_snapshot is None


class TestPureFunctionOfLedgerAndTick:
    def test_same_ledger_and_tick_yields_byte_identical_reading(self) -> None:
        """Same (ledger, tick) in => same reading out, every time — no
        hidden state, no clock reads, no randomness."""
        from babylon.projection.fog.ledger import IntelLedger, read_intel

        ledger = IntelLedger().append(_entry(tick_observed=10))

        first = read_intel(
            ledger,
            node_id="T1",
            field_group="political",
            tick=15,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )
        second = read_intel(
            ledger,
            node_id="T1",
            field_group="political",
            tick=15,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert first == second

    def test_most_recent_entry_wins_when_multiple_observations_exist(self) -> None:
        from babylon.projection.fog.ledger import IntelLedger, read_intel

        ledger = IntelLedger().append(_entry(tick_observed=1)).append(_entry(tick_observed=10))

        reading = read_intel(
            ledger,
            node_id="T1",
            field_group="political",
            tick=12,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )

        assert reading.tick_observed == 10


class TestAppendOnlyNoMutation:
    def test_append_returns_a_new_ledger_and_leaves_the_original_untouched(self) -> None:
        from babylon.projection.fog.ledger import IntelLedger

        original = IntelLedger()
        appended = original.append(_entry())

        assert original.entries == ()
        assert len(appended.entries) == 1
        assert appended is not original

    def test_entry_is_frozen(self) -> None:
        from pydantic import ValidationError

        entry = _entry()
        with pytest.raises(ValidationError):
            entry.tick_observed = 99  # type: ignore[misc]

    def test_ledger_is_frozen(self) -> None:
        from pydantic import ValidationError

        from babylon.projection.fog.ledger import IntelLedger

        ledger = IntelLedger()
        with pytest.raises(ValidationError):
            ledger.entries = (_entry(),)  # type: ignore[misc]


class TestLedgerFromEvents:
    """Track 1 / Task 3 (2026-07-18): :func:`~babylon.projection.fog.ledger.ledger_from_events`
    — the ledger's actual writer. Folds persisted, ALREADY-FILTERED
    INVESTIGATE-resolution rows (the caller, ``engine_bridge.py``, owns the
    ``action_type == ActionType.MAP_NETWORK`` filter and every ``babylon.*``
    import that requires) into an :class:`~babylon.projection.fog.ledger.IntelLedger`.
    Pure — no I/O, no globals — so these rows are plain dicts, never a real
    persistence handle."""

    def _row(
        self,
        tick: int = 10,
        target_id: str = "T1",
        field_group: str = "territory:political",
        value_snapshot: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return {
            "tick": tick,
            "target_id": target_id,
            "field_group": field_group,
            "value_snapshot": value_snapshot or {"heat": 0.734},
        }

    def test_one_row_becomes_one_reachable_entry(self) -> None:
        from babylon.projection.fog.ledger import ledger_from_events, read_intel

        ledger = ledger_from_events([self._row()])

        reading = read_intel(
            ledger,
            node_id="T1",
            field_group="territory:political",
            tick=12,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )
        assert reading.tier == "exact"
        assert reading.value_snapshot == {"heat": 0.734}
        assert reading.tick_observed == 10

    def test_empty_rows_yields_an_empty_ledger(self) -> None:
        from babylon.projection.fog.ledger import IntelLedger, ledger_from_events

        assert ledger_from_events([]) == IntelLedger()

    def test_most_recent_row_wins_on_read(self) -> None:
        from babylon.projection.fog.ledger import ledger_from_events, read_intel

        rows = [
            self._row(tick=1, value_snapshot={"heat": 0.1}),
            self._row(tick=10, value_snapshot={"heat": 0.9}),
        ]
        ledger = ledger_from_events(rows)

        reading = read_intel(
            ledger,
            node_id="T1",
            field_group="territory:political",
            tick=12,
            staleness_ticks=STALENESS_TICKS,
            unknown_ticks=UNKNOWN_TICKS,
        )
        assert reading.tick_observed == 10
        assert reading.value_snapshot == {"heat": 0.9}

    def test_row_missing_target_id_is_skipped(self) -> None:
        """A partial row never fabricates a fake entry (Constitution III.11)."""
        from babylon.projection.fog.ledger import ledger_from_events

        row = self._row()
        del row["target_id"]
        ledger = ledger_from_events([row])

        assert ledger.entries == ()

    def test_row_missing_value_snapshot_is_skipped(self) -> None:
        from babylon.projection.fog.ledger import ledger_from_events

        row = self._row()
        row["value_snapshot"] = {}
        ledger = ledger_from_events([row])

        assert ledger.entries == ()

    def test_row_missing_field_group_is_skipped(self) -> None:
        from babylon.projection.fog.ledger import ledger_from_events

        row = self._row()
        del row["field_group"]
        ledger = ledger_from_events([row])

        assert ledger.entries == ()

    def test_distinct_targets_produce_distinct_entries(self) -> None:
        from babylon.projection.fog.ledger import ledger_from_events

        rows = [
            self._row(target_id="T1", value_snapshot={"heat": 0.1}),
            self._row(target_id="T2", value_snapshot={"heat": 0.2}),
        ]
        ledger = ledger_from_events(rows)

        assert ledger.latest("T1", "territory:political") is not None
        assert ledger.latest("T2", "territory:political") is not None
        assert ledger.latest("T1", "territory:political") != ledger.latest(
            "T2", "territory:political"
        )


class TestFutureDatedEntryFailsLoud:
    def test_tick_before_observation_raises(self) -> None:
        """An entry observed AFTER the query tick is a determinism bug (or
        clock skew) — fail loud rather than silently misclassify it."""
        from babylon.projection.fog.ledger import IntelLedger, read_intel

        ledger = IntelLedger().append(_entry(tick_observed=50))

        with pytest.raises(ValueError):
            read_intel(
                ledger,
                node_id="T1",
                field_group="political",
                tick=10,
                staleness_ticks=STALENESS_TICKS,
                unknown_ticks=UNKNOWN_TICKS,
            )
