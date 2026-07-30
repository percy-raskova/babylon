"""Unit tests for the fallback-coverage sentinel (ADR176 ruling 25).

Mechanism tests run against synthetic member/coverage sets so they pin the
check contracts, not repo facts; the conformance tests prove the shipped
disposition ledger is truthful against the real tree (the sentinel's own CI
posture). The sentinel's law, over two verdict surfaces: every ``EventType``
member has a bus->pydantic builder (``engine.event_builders.EVENT_BUILDERS``)
or a cited ledger row — an absent builder drops the event to ``None`` at the
bus boundary; and every wire-reaching member has a bespoke chronicle summary
(``game.chronicle_adapter._SUMMARY_BUILDERS``) or a cited ledger row — an
absent builder renders the loud generic form. Both ledgers ratchet: a
ledgered member that gains coverage goes stale loudly, and a bespoke summary
for a member that cannot reach the wire is the crafted-but-unreachable
defect, not craft.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.models.enums.events import EventType
from babylon.sentinels._ast import eventtype_dict_keys
from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.fallback_coverage.checks import (
    ledger_violations,
    main,
    unreachable_bespoke_violations,
)
from babylon.sentinels.fallback_coverage.registry import (
    BUS_BOUNDARY_LEDGER,
    CHRONICLE_LEDGER,
    EVENT_BUILDERS_DICT,
    EVENT_BUILDERS_PATH,
    EventCoverageRow,
    Governance,
)


def _row(
    member: str,
    governance: Governance = Governance.DORMANT,
    citation: str = "cited: test evidence",
) -> EventCoverageRow:
    return EventCoverageRow(member=member, governance=governance, citation=citation)


class TestLedgerViolations:
    """The shared coverage law: covered, or ledgered-with-citation — never both."""

    def test_uncovered_unledgered_member_is_a_violation(self) -> None:
        violations = ledger_violations(
            surface="bus-boundary",
            scope=frozenset({"ALPHA"}),
            covered=frozenset(),
            rows=(),
        )
        assert len(violations) == 1
        assert "ALPHA" in violations[0]

    def test_covered_member_needs_no_row(self) -> None:
        violations = ledger_violations(
            surface="bus-boundary",
            scope=frozenset({"ALPHA"}),
            covered=frozenset({"ALPHA"}),
            rows=(),
        )
        assert violations == []

    def test_ledgered_member_with_citation_is_clean(self) -> None:
        violations = ledger_violations(
            surface="bus-boundary",
            scope=frozenset({"ALPHA"}),
            covered=frozenset(),
            rows=(_row("ALPHA"),),
        )
        assert violations == []

    def test_ledger_row_missing_citation_is_a_violation(self) -> None:
        violations = ledger_violations(
            surface="bus-boundary",
            scope=frozenset({"ALPHA"}),
            covered=frozenset(),
            rows=(_row("ALPHA", citation=""),),
        )
        assert len(violations) == 1
        assert "citation" in violations[0]

    def test_stale_row_for_covered_member_is_a_violation(self) -> None:
        """The ratchet: coverage arriving must retire the ledger row."""
        violations = ledger_violations(
            surface="bus-boundary",
            scope=frozenset({"ALPHA"}),
            covered=frozenset({"ALPHA"}),
            rows=(_row("ALPHA"),),
        )
        assert len(violations) == 1
        assert "stale" in violations[0]

    def test_row_for_unknown_member_is_a_violation(self) -> None:
        """A row naming no in-scope member is a typo or a retired member."""
        violations = ledger_violations(
            surface="chronicle",
            scope=frozenset({"ALPHA"}),
            covered=frozenset(),
            rows=(_row("ALPHA"), _row("BOGUS")),
        )
        assert len(violations) == 1
        assert "BOGUS" in violations[0]

    def test_out_of_scope_member_imposes_no_obligation(self) -> None:
        """Chronicle scope excludes bus-dropped members: an event that never
        reaches the wire owes no bespoke summary (its bus row governs it)."""
        violations = ledger_violations(
            surface="chronicle",
            scope=frozenset({"ALPHA"}),
            covered=frozenset(),
            rows=(_row("ALPHA"),),
        )
        assert violations == []


class TestUnreachableBespoke:
    """The inverse defect: crafted summaries for members that never arrive."""

    def test_bespoke_summary_for_unreachable_member_is_a_violation(self) -> None:
        violations = unreachable_bespoke_violations(
            bespoke=frozenset({"ALPHA", "GHOST"}),
            wire_reaching=frozenset({"ALPHA"}),
        )
        assert len(violations) == 1
        assert "GHOST" in violations[0]

    def test_bespoke_subset_of_wire_reaching_is_clean(self) -> None:
        violations = unreachable_bespoke_violations(
            bespoke=frozenset({"ALPHA"}),
            wire_reaching=frozenset({"ALPHA", "BETA"}),
        )
        assert violations == []


class TestEventTypeDictKeys:
    """The precise dict-key scanner both surfaces are measured with."""

    def test_reads_eventtype_keys_of_the_named_dict(self, tmp_path: Path) -> None:
        path = tmp_path / "mod.py"
        path.write_text(
            "X: dict = {EventType.ALPHA: 1}\n_OTHER = {EventType.BETA: 2}\n",
            encoding="utf-8",
        )
        assert eventtype_dict_keys(path, "X") == {"ALPHA"}

    def test_missing_dict_is_loud_never_an_empty_pass(self, tmp_path: Path) -> None:
        path = tmp_path / "mod.py"
        path.write_text("Y = 1\n", encoding="utf-8")
        with pytest.raises(SentinelCheckError):
            eventtype_dict_keys(path, "X")

    def test_reads_the_real_event_builders_registry(self) -> None:
        keys = eventtype_dict_keys(EVENT_BUILDERS_PATH, EVENT_BUILDERS_DICT)
        assert "SURPLUS_EXTRACTION" in keys
        assert "ELECTION_HELD" in keys


class TestShippedLedgers:
    """The shipped dispositions stay truthful (the sentinel's CI posture)."""

    def test_bus_ledger_members_are_real_and_cited(self) -> None:
        names = {e.name for e in EventType}
        for row in BUS_BOUNDARY_LEDGER:
            assert row.member in names
            assert row.citation

    def test_verdict_surface_drops_are_chartered_not_dormant(self) -> None:
        """The endings audit's dropped verdict events carry CHARTER rows —
        they are owed emitters by the endings train (ADR176 rulings 1-3),
        never quietly parked as dead vocabulary."""
        by_member = {row.member: row for row in BUS_BOUNDARY_LEDGER}
        for member in (
            "ENDGAME_REACHED",
            "RED_OGV_ENDGAME",
            "FRAGMENTED_COLLAPSE_ENDGAME",
            "PATTERN_SHIFT",
        ):
            assert by_member[member].governance is Governance.CHARTER

    def test_chronicle_ledger_is_empty_every_wire_event_is_bespoke(self) -> None:
        """As of the P25 bespoke widening, every wire-reaching EventType has a
        bespoke summary — a future exemption must arrive as a cited row, and
        this pin makes that a deliberate act."""
        assert CHRONICLE_LEDGER == ()

    def test_real_tree_conformance(self) -> None:
        assert main(["--check"]) == 0
