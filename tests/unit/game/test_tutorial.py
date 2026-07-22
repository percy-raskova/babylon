"""Unit tests for the tutorial step model (Program v1.0.0 T6, Unit U1).

Three families, per the unit's own test mandate:

* **Model validation** — :class:`~babylon.game.tutorial.TutorialStep`/
  :class:`~babylon.game.tutorial.TutorialScript` are frozen, reject unknown
  fields, enforce unique step ids, and the closed completion-predicate
  vocabulary reds loudly (``pydantic.ValidationError``) on an unrecognized
  ``kind`` — never a silently-ignored predicate.
* **Script integrity** — the authored
  :data:`~babylon.game.tutorial.WAYNE_OPENING_ARC` carries a non-empty
  anchor on every step, every predicate round-trips through the closed-
  vocabulary :class:`~pydantic.TypeAdapter` (the exact shape the overlay/
  docs/Pilot-executor consumers will deserialize), and every
  ``"binding:<ClassName>:<key>"`` anchor names a key that is REALLY on
  that Textual class's own ``BINDINGS`` today (no fiction).
* **Rendering contract** — :attr:`~babylon.game.tutorial.TutorialStep.
  scenario_name`/:attr:`~babylon.game.tutorial.TutorialStep.overlay_text`
  derive VERBATIM from ``given``/``when``/``then`` — proving there is no
  second, separately-authored copy of this prose anywhere.
"""

from __future__ import annotations

import pydantic
import pytest

from babylon.engine.scenarios.wayne_county import WayneCountyScenario
from babylon.game.pacing import PacedTickDriver
from babylon.game.tutorial import (
    _MAX_SCRIPT_STEPS,
    WAYNE_OPENING_ARC,
    CompletionPredicateAdapter,
    EventAcked,
    OnPage,
    PaneShowing,
    PausePending,
    PinnedInWatchlist,
    TickAtLeast,
    TutorialScript,
    TutorialStep,
    VerbIssued,
)
from babylon.tui.app import ArchiveApp, BriefingScreen, PacedDriverHandle
from babylon.tui.campaign_menu import LobbyScreen

pytestmark = [pytest.mark.unit]

#: The live Textual ``BINDINGS`` registries every ``"binding:<Class>:<key>"``
#: anchor below is checked against — no fiction (the ruling's own rule).
_LIVE_BINDING_CLASSES: dict[str, type] = {
    "ArchiveApp": ArchiveApp,
    "BriefingScreen": BriefingScreen,
    "LobbyScreen": LobbyScreen,
}


def _minimal_step(step_id: str = "a_step", *, anchor: str = "page:x") -> TutorialStep:
    """One structurally-valid step, varying only what a test needs to vary."""
    return TutorialStep(
        id=step_id,
        given="a precondition",
        when="an action",
        then="a result",
        anchor=anchor,
        completion=OnPage(subject="x"),
    )


# --------------------------------------------------------------------------- #
# Model validation.
# --------------------------------------------------------------------------- #


class TestTutorialStepModel:
    """Frozen, constrained, closed-vocabulary — never a loose dict."""

    def test_step_is_frozen(self) -> None:
        step = _minimal_step()
        with pytest.raises(pydantic.ValidationError):
            step.given = "mutated"  # type: ignore[misc]

    def test_step_rejects_unknown_field(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            TutorialStep(
                id="a",
                given="g",
                when="w",
                then="t",
                anchor="page:x",
                completion=OnPage(subject="x"),
                bogus_field="nope",  # type: ignore[call-arg]
            )

    @pytest.mark.parametrize("field", ["id", "given", "when", "then", "anchor"])
    def test_step_rejects_empty_required_strings(self, field: str) -> None:
        kwargs: dict[str, object] = {
            "id": "a",
            "given": "g",
            "when": "w",
            "then": "t",
            "anchor": "page:x",
            "completion": OnPage(subject="x"),
        }
        kwargs[field] = ""
        with pytest.raises(pydantic.ValidationError):
            TutorialStep(**kwargs)  # type: ignore[arg-type]

    @pytest.mark.parametrize("bad_id", ["Not_Lower", "1leading_digit", "has space", ""])
    def test_step_id_pattern_rejects_non_slug_ids(self, bad_id: str) -> None:
        with pytest.raises(pydantic.ValidationError):
            TutorialStep(
                id=bad_id,
                given="g",
                when="w",
                then="t",
                anchor="page:x",
                completion=OnPage(subject="x"),
            )

    def test_completion_accepts_every_closed_vocabulary_kind(self) -> None:
        for predicate in (
            OnPage(subject="county/26163"),
            TickAtLeast(tick=1),
            PausePending(),
            EventAcked(),
            VerbIssued(verb="advance_tick"),
            PaneShowing(pane="map"),
            PinnedInWatchlist(subject="county/26163"),
        ):
            step = _minimal_step()
            step = step.model_copy(update={"completion": predicate})
            assert step.completion == predicate

    def test_completion_rejects_unknown_kind(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            TutorialStep(
                id="a",
                given="g",
                when="w",
                then="t",
                anchor="page:x",
                completion={"kind": "teleports_the_player"},
            )

    def test_completion_rejects_payload_missing_kind(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            TutorialStep(
                id="a",
                given="g",
                when="w",
                then="t",
                anchor="page:x",
                completion={"subject": "x"},
            )


class TestCompletionPredicateAdapter:
    """The standalone adapter the overlay/docs/Pilot-executor consumers use."""

    def test_adapter_round_trips_every_kind(self) -> None:
        for predicate in (
            OnPage(subject="county/26163"),
            TickAtLeast(tick=52),
            PausePending(),
            EventAcked(),
            VerbIssued(verb="run_until_paused"),
            PaneShowing(pane="dashboard"),
            PinnedInWatchlist(subject="county/26163"),
        ):
            dumped = predicate.model_dump(mode="json")
            reloaded = CompletionPredicateAdapter.validate_python(dumped)
            assert reloaded == predicate

    def test_adapter_reds_loudly_on_unknown_kind(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            CompletionPredicateAdapter.validate_python({"kind": "bogus_kind"})

    def test_adapter_reds_loudly_on_missing_kind(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            CompletionPredicateAdapter.validate_python({"subject": "county/26163"})


class TestTutorialScriptModel:
    """Ordered, uniquely-keyed, bounded — never an unbounded/duplicated script."""

    def test_script_is_frozen(self) -> None:
        script = TutorialScript(id="s", scenario="wayne_county", steps=(_minimal_step(),))
        with pytest.raises(pydantic.ValidationError):
            script.id = "mutated"  # type: ignore[misc]

    def test_script_rejects_empty_steps(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            TutorialScript(id="s", scenario="wayne_county", steps=())

    def test_script_rejects_duplicate_step_ids(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="duplicate step id"):
            TutorialScript(
                id="s",
                scenario="wayne_county",
                steps=(
                    _minimal_step("same_id", anchor="page:x"),
                    _minimal_step("same_id", anchor="page:y"),
                ),
            )

    def test_script_accepts_pairwise_distinct_ids(self) -> None:
        script = TutorialScript(
            id="s",
            scenario="wayne_county",
            steps=(_minimal_step("first"), _minimal_step("second")),
        )
        assert [step.id for step in script.steps] == ["first", "second"]

    def test_script_enforces_a_static_step_count_ceiling(self) -> None:
        # Power-of-10 rule 2: the ceiling itself must be a fixed, provable
        # bound — proven here by actually exceeding it by one.
        too_many = tuple(_minimal_step(f"step_{i}") for i in range(_MAX_SCRIPT_STEPS + 1))
        with pytest.raises(pydantic.ValidationError):
            TutorialScript(id="s", scenario="wayne_county", steps=too_many)


# --------------------------------------------------------------------------- #
# Script integrity — the AUTHORED Wayne opening arc.
# --------------------------------------------------------------------------- #


def _parse_binding_anchor(anchor: str) -> tuple[str, str] | None:
    """Split a ``"binding:<ClassName>:<key>"`` anchor into ``(class, key)``.

    :param anchor: the anchor string.
    :returns: ``(class_name, key)`` if ``anchor`` is binding-shaped, else
        ``None`` (a ``page:``/``palette:`` anchor).
    """
    if not anchor.startswith("binding:"):
        return None
    _, class_name, key = anchor.split(":", 2)
    return class_name, key


class TestWayneOpeningArcIntegrity:
    """The one authored script this unit ships — checked against reality."""

    def test_scenario_matches_the_real_wayne_scenario_name(self) -> None:
        assert WAYNE_OPENING_ARC.scenario == WayneCountyScenario.name == "wayne_county"

    def test_every_step_anchor_is_non_empty(self) -> None:
        for step in WAYNE_OPENING_ARC.steps:  # loop bound: len(steps) == 14
            assert step.anchor.strip() != ""

    def test_every_step_id_is_unique(self) -> None:
        ids = [step.id for step in WAYNE_OPENING_ARC.steps]
        assert len(ids) == len(set(ids))

    def test_every_predicate_parses_through_the_closed_vocabulary_adapter(self) -> None:
        for step in WAYNE_OPENING_ARC.steps:  # loop bound: len(steps) == 14
            dumped = step.completion.model_dump(mode="json")
            reloaded = CompletionPredicateAdapter.validate_python(dumped)
            assert reloaded == step.completion

    def test_every_binding_anchor_names_a_real_live_key(self) -> None:
        """Cross-checks every ``binding:`` anchor against the REAL
        ``BINDINGS`` on the named Textual class — the "verify every anchor
        exists before authoring" rule, pinned as a durable regression
        rather than a one-time authoring-time check.
        """
        checked = 0
        for step in WAYNE_OPENING_ARC.steps:  # loop bound: len(steps) == 14
            parsed = _parse_binding_anchor(step.anchor)
            if parsed is None:
                continue
            class_name, key = parsed
            assert class_name in _LIVE_BINDING_CLASSES, (
                f"{step.id}: anchor names unknown class {class_name!r}"
            )
            live_keys = {binding.key for binding in _LIVE_BINDING_CLASSES[class_name].BINDINGS}
            assert key in live_keys, (
                f"{step.id}: anchor key {key!r} is not a real binding on {class_name}"
            )
            checked += 1
        assert checked > 0, "no binding: anchors were exercised by this test"

    def test_every_page_or_palette_anchor_names_a_kind_slash_id_subject(self) -> None:
        for step in WAYNE_OPENING_ARC.steps:  # loop bound: len(steps) == 14
            if step.anchor.startswith(("page:", "palette:")):
                _, subject = step.anchor.split(":", 1)
                assert "/" in subject, f"{step.id}: {subject!r} is not a kind/id subject"

    def test_run_until_autopause_verifies_the_stop_not_just_the_dispatch(self) -> None:
        """Reviewer finding (T6 U1 fix pass): a step whose ``then`` advertises
        the paced driver STOPPING must carry a completion predicate that
        checks the stop, not merely that the keypress dispatched."""
        step = next(s for s in WAYNE_OPENING_ARC.steps if s.id == "run_until_autopause")
        assert step.completion == PausePending()

    def test_pause_pending_predicate_is_grounded_in_the_live_pacing_seam(self) -> None:
        """``PausePending`` is not fiction: the two primitives its own
        docstring names (``awaiting_ack``/``pending_pause``) are real,
        live attributes on both the concrete driver and the structural
        seam ``babylon.tui`` crosses with it — never an invented surface.
        """
        assert hasattr(PacedTickDriver, "awaiting_ack")
        assert hasattr(PacedTickDriver, "pending_pause")
        assert hasattr(PacedDriverHandle, "awaiting_ack")

    def test_begin_the_operation_verifies_the_outcome_not_just_the_dispatch(self) -> None:
        """Reviewer finding (T6 U1 fix pass): the dossier-reveal OUTCOME is
        queryable here (unlike ``boot_into_lobby``, pre-campaign), so this
        step is made self-contained rather than relying on the next
        step's ``OnPage`` to cover it after the fact."""
        step = next(s for s in WAYNE_OPENING_ARC.steps if s.id == "begin_the_operation")
        assert step.completion == OnPage(subject="county/26163")

    def test_boot_into_lobby_completion_is_the_documented_honest_floor(self) -> None:
        """No page/tick outcome predicate is queryable pre-campaign, so
        ``VerbIssued`` (dispatch-only) is the deliberate, documented gap —
        never silently upgraded without also removing the honest-gap
        comment in the authored script."""
        step = next(s for s in WAYNE_OPENING_ARC.steps if s.id == "boot_into_lobby")
        assert step.completion == VerbIssued(verb="new_campaign")

    def test_arc_covers_the_advertised_core_loop_beats(self) -> None:
        """The 14 authored beats span mint -> briefing -> dossier -> tick ->
        run -> ack -> palette -> theorem -> jump-back -> the Map/Wiki/
        Topology/Dashboard panes -> pin Wayne to the watchlist, in that order
        (Program 24 P8 extends the original 9-beat core loop with the last
        five)."""
        assert [step.id for step in WAYNE_OPENING_ARC.steps] == [
            "boot_into_lobby",
            "begin_the_operation",
            "read_the_county_dossier",
            "advance_a_tick",
            "run_until_autopause",
            "acknowledge_the_pause",
            "palette_to_the_economy_dossier",
            "read_the_theorem_verdict",
            "jump_back_to_wayne",
            "learn_the_map_pane",
            "learn_the_wiki_pane",
            "learn_the_topology_pane",
            "learn_the_dashboard_pane",
            "pin_wayne_to_the_watchlist",
        ]

    def test_pin_wayne_to_the_watchlist_subject_matches_the_arcs_own_current_subject(self) -> None:
        """Cross-reference for the honest-expectation note in
        :mod:`babylon.game.tutorial`'s own authored-script comment: no step
        between ``jump_back_to_wayne`` (which lands on county/26163) and
        ``pin_wayne_to_the_watchlist`` ever calls ``_navigate`` (switching
        panes does not itself navigate), so county/26163 really is still the
        dossier's current subject by the time the pin fires — a hardcoded
        expected subject here is honest, not a guess."""
        pin_step = next(s for s in WAYNE_OPENING_ARC.steps if s.id == "pin_wayne_to_the_watchlist")
        assert pin_step.completion == PinnedInWatchlist(subject="county/26163")


class TestShellTeachingTailProgram24P8:
    """The five Program 24 P8 beats — pins the coverage sentinel's own
    required anchor set (``binding:ArchiveApp:1``/``:2``/``:3``/``:4``/``:p``
    exactly) as a durable regression, and that each step's own completion
    predicate matches the pane/subject its ``then`` advertises."""

    def test_the_five_shell_steps_carry_the_sentinels_required_anchors_in_order(self) -> None:
        shell_step_ids = [
            "learn_the_map_pane",
            "learn_the_wiki_pane",
            "learn_the_topology_pane",
            "learn_the_dashboard_pane",
            "pin_wayne_to_the_watchlist",
        ]
        steps_by_id = {step.id: step for step in WAYNE_OPENING_ARC.steps}
        anchors = [steps_by_id[step_id].anchor for step_id in shell_step_ids]
        assert anchors == [
            "binding:ArchiveApp:2",
            "binding:ArchiveApp:3",
            "binding:ArchiveApp:4",
            "binding:ArchiveApp:1",
            "binding:ArchiveApp:p",
        ]

    @pytest.mark.parametrize(
        ("step_id", "expected_pane"),
        [
            ("learn_the_map_pane", "map"),
            ("learn_the_wiki_pane", "wiki"),
            ("learn_the_topology_pane", "topology"),
            ("learn_the_dashboard_pane", "dashboard"),
        ],
    )
    def test_each_pane_step_completion_names_its_own_advertised_pane(
        self, step_id: str, expected_pane: str
    ) -> None:
        step = next(s for s in WAYNE_OPENING_ARC.steps if s.id == step_id)
        assert step.completion == PaneShowing(pane=expected_pane)

    def test_the_five_shell_steps_appear_after_the_original_nine_beat_core_loop(self) -> None:
        """The shell-teaching tail follows ``jump_back_to_wayne`` — the
        player has read both dossiers and walked back before the room
        itself is taught (module docstring's own placement rationale)."""
        ids = [step.id for step in WAYNE_OPENING_ARC.steps]
        assert ids.index("jump_back_to_wayne") < ids.index("learn_the_map_pane")


# --------------------------------------------------------------------------- #
# Rendering contract.
# --------------------------------------------------------------------------- #


class TestRenderingContract:
    """``scenario_name``/``overlay_text`` derive verbatim from the fields —
    no separately-authored prose duplicate anywhere.
    """

    def test_scenario_name_contains_every_field_verbatim(self) -> None:
        for step in WAYNE_OPENING_ARC.steps:  # loop bound: len(steps) == 14
            assert step.given in step.scenario_name
            assert step.when in step.scenario_name
            assert step.then in step.scenario_name

    def test_overlay_text_contains_every_field_verbatim(self) -> None:
        for step in WAYNE_OPENING_ARC.steps:  # loop bound: len(steps) == 14
            assert step.given in step.overlay_text
            assert step.when in step.overlay_text
            assert step.then in step.overlay_text

    def test_scenario_name_and_overlay_text_are_pure_functions_of_the_fields(self) -> None:
        """Two steps differing ONLY in ``given`` render different strings
        that each carry their OWN ``given`` verbatim — proving derivation,
        not a shared hardcoded template ignoring the field's actual value.
        """
        step_one = _minimal_step("one").model_copy(update={"given": "the FIRST precondition"})
        step_two = _minimal_step("two").model_copy(update={"given": "the SECOND precondition"})

        assert "the FIRST precondition" in step_one.scenario_name
        assert "the SECOND precondition" not in step_one.scenario_name
        assert "the SECOND precondition" in step_two.scenario_name
        assert "the FIRST precondition" not in step_two.scenario_name

        assert "the FIRST precondition" in step_one.overlay_text
        assert "the SECOND precondition" in step_two.overlay_text

    def test_scenario_name_is_a_single_sentence(self) -> None:
        """The ruling: "scenario names are sentences" — one, ending in a
        period, not a multi-line block (that's what ``overlay_text`` is
        for)."""
        for step in WAYNE_OPENING_ARC.steps:  # loop bound: len(steps) == 14
            assert step.scenario_name.endswith(".")
            assert "\n" not in step.scenario_name
