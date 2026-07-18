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
    from game.fog.ledger import IntelEntry

    return IntelEntry(
        node_id=node_id,
        field_group=field_group,
        tick_observed=tick_observed,
        value_snapshot={"heat": 0.734, "dominant_class": "core_proletariat"},
    )


class TestFreshEntryIsExact:
    def test_fresh_entry_reads_exact(self) -> None:
        from game.fog.ledger import IntelLedger, read_intel

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
        from game.fog.ledger import IntelLedger, read_intel

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
        from game.fog.ledger import IntelLedger, read_intel

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
        from game.fog.ledger import IntelLedger, read_intel

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
        from game.fog.ledger import IntelLedger, read_intel

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
        from game.fog.ledger import IntelLedger, read_intel

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
        from game.fog.ledger import IntelLedger, read_intel

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
        from game.fog.ledger import IntelLedger, read_intel

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
        from game.fog.ledger import IntelLedger

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

        from game.fog.ledger import IntelLedger

        ledger = IntelLedger()
        with pytest.raises(ValidationError):
            ledger.entries = (_entry(),)  # type: ignore[misc]


class TestFutureDatedEntryFailsLoud:
    def test_tick_before_observation_raises(self) -> None:
        """An entry observed AFTER the query tick is a determinism bug (or
        clock skew) — fail loud rather than silently misclassify it."""
        from game.fog.ledger import IntelLedger, read_intel

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
