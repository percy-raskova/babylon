"""Contract tests for :mod:`babylon.projection.briefing` (WO-35).

The briefing dossier's behavioral contract: a deterministic two-word
codename, exactly five recognized-pattern rows with honest tick-0 progress,
and a campaign horizon reused verbatim from :mod:`babylon.projection.
endgame`. Fixture-fed in the loosest sense — every input here is a plain
Python value (UUID, ``GameDefines()``), so there is no engine/database in
this module's path at all, satisfying the fixture-first discipline trivially.
"""

from __future__ import annotations

import re
from uuid import UUID

import pytest
from pydantic import ValidationError

from babylon.config.defines import GameDefines
from babylon.models.enums.events import GameOutcome
from babylon.projection.briefing import (
    WIN_OBJECTIVE_ID,
    BriefingObjective,
    BriefingView,
    journal_objectives,
    operation_codename,
    project_briefing,
)
from babylon.projection.endgame import campaign_horizon_tick

_SESSION = UUID("12345678-1234-5678-1234-567812345678")
_CODENAME_RE = re.compile(r"^[A-Z]+ [A-Z]+$")


def _defines() -> GameDefines:
    return GameDefines()


class TestOperationCodename:
    """Deterministic, byte-stable two-word codenames (spec-116 FR-116-3)."""

    def test_matches_the_two_uppercase_word_shape(self) -> None:
        codename = operation_codename(_SESSION)
        assert _CODENAME_RE.match(codename), codename
        # The frontend acceptance prefixes "OPERATION " at render time —
        # confirm the combined string still matches the e2e regex.
        assert re.match(r"^OPERATION [A-Z]+ [A-Z]+$", f"OPERATION {codename}")

    def test_is_a_pure_function_of_the_session_id(self) -> None:
        first = operation_codename(_SESSION)
        second = operation_codename(_SESSION)
        assert first == second

    def test_different_sessions_can_yield_different_codenames(self) -> None:
        other = UUID("00000000-0000-0000-0001-000000000000")
        assert operation_codename(_SESSION) != operation_codename(other)

    def test_is_not_derived_from_an_all_zero_uuid_collision_trap(self) -> None:
        """Two distinct UUIDs differing only after byte 4 still collide on
        codename by construction (only the first 4 bytes are read) — this
        pins that documented behavior rather than asserting global
        uniqueness, which the function never promises."""
        a = UUID("aaaaaaaa-bbbb-cccc-dddd-000000000001")
        b = UUID("aaaaaaaa-bbbb-cccc-dddd-000000000002")
        assert operation_codename(a) == operation_codename(b)


class TestJournalObjectives:
    """The five-axis fold (port of ``get_journal_objectives``)."""

    def test_yields_exactly_five_objectives_in_canonical_order(self) -> None:
        objectives = journal_objectives()
        assert [o.id for o in objectives] == [
            "revolution",
            "ecological_collapse",
            "fascist_consolidation",
            "red_ogv",
            "fragmented_collapse",
        ]

    def test_win_condition_is_flagged_on_exactly_the_revolution_row(self) -> None:
        objectives = journal_objectives()
        flagged = [o.id for o in objectives if o.is_win_condition]
        assert flagged == [WIN_OBJECTIVE_ID] == ["revolution"]

    def test_progress_is_honestly_zero_with_no_axes_snapshot_yet(self) -> None:
        """Before any tick has run there is no endgame_progress block —
        every axis reads 0.0, the genuine tick-0 value, not a fabricated
        placeholder (matches the ported bridge helper's documented ruling)."""
        objectives = journal_objectives(axes=None, outcome=None)
        assert all(o.progress == pytest.approx(0.0) for o in objectives)
        assert all(o.status == "active" for o in objectives)

    def test_progress_reads_the_supplied_axes_block_by_key(self) -> None:
        objectives = journal_objectives(
            axes={
                "revolutionary_victory": 0.42,
                "ecological_collapse": 0.10,
                "fascist_consolidation": 0.05,
                "red_ogv": 0.0,
                "fragmented_collapse": 0.9,
            }
        )
        by_id = {o.id: o.progress for o in objectives}
        assert by_id["revolution"] == pytest.approx(0.42)
        assert by_id["ecological_collapse"] == pytest.approx(0.10)
        assert by_id["fragmented_collapse"] == pytest.approx(0.9)

    def test_a_non_numeric_axis_value_reads_as_zero_not_a_crash(self) -> None:
        objectives = journal_objectives(axes={"revolutionary_victory": "not-a-number"})
        by_id = {o.id: o.progress for o in objectives}
        assert by_id["revolution"] == pytest.approx(0.0)

    def test_held_outcome_completes_its_own_pattern_and_fails_the_rest(self) -> None:
        objectives = journal_objectives(outcome=GameOutcome.RED_OGV)
        by_id = {o.id: o.status for o in objectives}
        assert by_id["red_ogv"] == "complete"
        assert by_id["revolution"] == "failed"
        assert by_id["ecological_collapse"] == "failed"
        assert by_id["fascist_consolidation"] == "failed"
        assert by_id["fragmented_collapse"] == "failed"

    def test_unresolved_outcome_fails_every_pattern(self) -> None:
        """UNRESOLVED matches no category in the status table — every
        objective reports failed, never a spurious 'complete'."""
        objectives = journal_objectives(outcome=GameOutcome.UNRESOLVED)
        assert all(o.status == "failed" for o in objectives)


class TestBriefingObjectiveModel:
    """Frozen, extra-forbidding, range-constrained."""

    def test_is_frozen(self) -> None:
        objective = journal_objectives()[0]
        with pytest.raises(ValidationError):
            objective.progress = 0.9  # type: ignore[misc]

    def test_rejects_an_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            BriefingObjective(
                id="revolution",
                title="t",
                description="d",
                progress=0.0,
                status="active",
                category="revolution",
                is_win_condition=True,
                bogus_field="nope",  # type: ignore[call-arg]
            )


class TestProjectBriefing:
    """The full assembled dossier."""

    def test_projects_codename_objectives_and_horizon(self) -> None:
        view = project_briefing(_SESSION, tick=0, defines=_defines())

        assert view.kind == "briefing"
        assert view.session_id == _SESSION
        assert view.verified_tick == 0
        assert _CODENAME_RE.match(view.codename)
        assert view.codename == operation_codename(_SESSION)
        assert len(view.objectives) == 5
        assert view.win_objective_id == "revolution"
        assert view.horizon_years == 100
        assert view.horizon_ticks == campaign_horizon_tick(_defines())
        assert view.horizon_ticks == 5200

    def test_horizon_tracks_defines_not_a_hardcoded_literal(self) -> None:
        """A modded 50-year horizon changes the projected view — the value
        is a coefficient read-through, never a baked-in constant."""
        defines = GameDefines(
            endgame=GameDefines().endgame.model_copy(update={"campaign_horizon_years": 50})
        )
        view = project_briefing(_SESSION, tick=0, defines=defines)
        assert view.horizon_years == 50
        assert view.horizon_ticks == 50 * defines.timescale.weeks_per_year

    def test_is_a_pure_function_of_its_inputs(self) -> None:
        first = project_briefing(_SESSION, tick=0, defines=_defines())
        second = project_briefing(_SESSION, tick=0, defines=_defines())
        assert first == second
        assert first.model_dump() == second.model_dump()


class TestBriefingViewModel:
    """Frozen, extra-forbidding, exactly-five-objectives invariant."""

    def test_is_frozen(self) -> None:
        view = project_briefing(_SESSION, tick=0, defines=_defines())
        with pytest.raises(ValidationError):
            view.codename = "NEW NAME"  # type: ignore[misc]

    def test_rejects_an_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            BriefingView(
                session_id=_SESSION,
                verified_tick=0,
                codename="CRIMSON HARVEST",
                objectives=journal_objectives(),
                horizon_years=100,
                horizon_ticks=5200,
                bogus_field="nope",  # type: ignore[call-arg]
            )

    def test_rejects_a_malformed_codename(self) -> None:
        with pytest.raises(ValidationError):
            BriefingView(
                session_id=_SESSION,
                verified_tick=0,
                codename="crimson harvest",  # lowercase — must be rejected
                objectives=journal_objectives(),
                horizon_years=100,
                horizon_ticks=5200,
            )

    def test_rejects_a_wrong_count_of_objectives(self) -> None:
        with pytest.raises(ValidationError):
            BriefingView(
                session_id=_SESSION,
                verified_tick=0,
                codename="CRIMSON HARVEST",
                objectives=journal_objectives()[:4],
                horizon_years=100,
                horizon_ticks=5200,
            )
