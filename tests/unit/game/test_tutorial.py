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
  ``"binding:<Surface>:<key>"`` anchor names a hint row that is REALLY on
  the Rust keybar's own tables today (no fiction — M7 cutover: the keybar
  replaced the deleted Textual ``BINDINGS`` idiom as the option universe).
* **Rendering contract** — :attr:`~babylon.game.tutorial.TutorialStep.
  scenario_name`/:attr:`~babylon.game.tutorial.TutorialStep.overlay_text`
  derive VERBATIM from ``given``/``when``/``then`` — proving there is no
  second, separately-authored copy of this prose anywhere.
"""

from __future__ import annotations

from pathlib import Path

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
from babylon.sentinels._rust import declared_keybar_hints
from babylon.tui.contract import PacedDriverHandle

pytestmark = [pytest.mark.unit]

#: The live keybar option universe every ``"binding:<Surface>:<key>"``
#: anchor below is checked against — no fiction (the ruling's own rule; the
#: same extractor the tutorial-coverage sentinel gates on).
_LIVE_KEYBAR_OPTIONS: frozenset[tuple[str, str]] = frozenset(
    (surface, key)
    for surface, key, _label, _line in declared_keybar_hints(
        Path(__file__).resolve().parents[3] / "rust/crates/babylon-tui/src/views/keybar.rs"
    )
)


def _minimal_step(step_id: str = "a_step", *, anchor: str = "page:x") -> TutorialStep:
    """One structurally-valid step, varying only what a test needs to vary."""
    return TutorialStep(
        id=step_id,
        given="a precondition",
        when="an action",
        then="a result",
        anchor=anchor,
        completion=OnPage(subject="x"),
        patches="a patches line.",
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
                patches="a patches line.",
                bogus_field="nope",  # type: ignore[call-arg]
            )

    @pytest.mark.parametrize("field", ["id", "given", "when", "then", "anchor", "patches"])
    def test_step_rejects_empty_required_strings(self, field: str) -> None:
        kwargs: dict[str, object] = {
            "id": "a",
            "given": "g",
            "when": "w",
            "then": "t",
            "anchor": "page:x",
            "completion": OnPage(subject="x"),
            "patches": "a patches line.",
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
                patches="a patches line.",
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
                patches="a patches line.",
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
                patches="a patches line.",
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
    """Split a ``"binding:<Surface>:<key>"`` anchor into ``(surface, key)``.

    :param anchor: the anchor string.
    :returns: ``(surface, key)`` if ``anchor`` is binding-shaped, else
        ``None`` (a ``page:``/``palette:``/``option:`` anchor).
    """
    if not anchor.startswith("binding:"):
        return None
    _, surface, key = anchor.split(":", 2)
    return surface, key


class TestWayneOpeningArcIntegrity:
    """The one authored script this unit ships — checked against reality."""

    def test_scenario_matches_the_real_wayne_scenario_name(self) -> None:
        assert WAYNE_OPENING_ARC.scenario == WayneCountyScenario.name == "wayne_county"

    def test_every_step_anchor_is_non_empty(self) -> None:
        for step in WAYNE_OPENING_ARC.steps:  # loop bound: len(steps) == 24
            assert step.anchor.strip() != ""

    def test_every_step_id_is_unique(self) -> None:
        ids = [step.id for step in WAYNE_OPENING_ARC.steps]
        assert len(ids) == len(set(ids))

    def test_every_predicate_parses_through_the_closed_vocabulary_adapter(self) -> None:
        for step in WAYNE_OPENING_ARC.steps:  # loop bound: len(steps) == 24
            dumped = step.completion.model_dump(mode="json")
            reloaded = CompletionPredicateAdapter.validate_python(dumped)
            assert reloaded == step.completion

    def test_every_binding_anchor_names_a_real_live_key(self) -> None:
        """Cross-checks every ``binding:`` anchor against the REAL keybar
        hint tables (M7 cutover: the Rust client's one source of truth for
        player-facing keys) — the "verify every anchor exists before
        authoring" rule, pinned as a durable regression rather than a
        one-time authoring-time check.
        """
        checked = 0
        for step in WAYNE_OPENING_ARC.steps:  # loop bound: len(steps) == 24
            parsed = _parse_binding_anchor(step.anchor)
            if parsed is None:
                continue
            surface, key = parsed
            assert (surface, key) in _LIVE_KEYBAR_OPTIONS, (
                f"{step.id}: anchor {step.anchor!r} names no live keybar hint row"
            )
            checked += 1
        assert checked > 0, "no binding: anchors were exercised by this test"

    def test_every_page_or_palette_anchor_names_a_kind_slash_id_subject(self) -> None:
        for step in WAYNE_OPENING_ARC.steps:  # loop bound: len(steps) == 24
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
        """The 24 authored beats span mint -> briefing -> dossier -> tick ->
        run -> ack -> palette -> theorem -> jump-back -> a bracket-key
        round trip (unit "jumplist-rebind"), then the adversary tail
        (adversary train W4): state-apparatus dossier -> repression
        ledger, then the shell-teaching tail (Program 24 P8): the Map/Wiki/
        Topology/Dashboard panes -> pin the Detroit Proletariat to the
        watchlist -> open that same pinned row from the watchlist rail
        (unit "watchlist-row-nav") -> issue the Aid verb on it directly
        from the action bar (unit "verb-targeting") -> keyboard-peek the
        dossier's own wikilinks (unit "peek-hover-wire") -> press Enter on
        the chronicle rail's own highlighted row (unit
        "chronicle-row-nav-salience"), in that order."""
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
            "jump_forward_with_brackets",
            "jump_back_with_brackets",
            "palette_to_the_state_apparatus_dossier",
            "read_the_state_apparatus_dossier",
            "palette_to_the_repression_ledger",
            "read_the_repression_ledger",
            "learn_the_map_pane",
            "learn_the_wiki_pane",
            "learn_the_topology_pane",
            "learn_the_dashboard_pane",
            "pin_the_proletariat_to_the_watchlist",
            "open_the_pinned_row_from_the_watchlist",
            "issue_aid_on_the_proletariat",
            "peek_a_wikilink_with_the_keyboard",
            "open_the_chronicle_rails_highlighted_row",
        ]

    def test_pin_step_subject_matches_the_arcs_own_current_subject(self) -> None:
        """Cross-reference for the honest-expectation note in
        :mod:`babylon.game.tutorial`'s own authored-script comment: no step
        between ``read_the_repression_ledger`` (which lands on
        social_class/C001) and ``pin_the_proletariat_to_the_watchlist`` ever
        calls ``_navigate`` (switching panes does not itself navigate), so
        social_class/C001 really is still the dossier's current subject by
        the time the pin fires — a hardcoded expected subject here is
        honest, not a guess."""
        pin_step = next(
            s for s in WAYNE_OPENING_ARC.steps if s.id == "pin_the_proletariat_to_the_watchlist"
        )
        assert pin_step.completion == PinnedInWatchlist(subject="social_class/C001")


class TestShellTeachingTailProgram24P8:
    """The five Program 24 P8 beats — pins the shell-teaching anchor set
    (the four pane switches sharing ``binding:Wiki:1-4`` — one keybar
    composite hint IS one option, taught four ways — plus the capital-P
    pin) as a durable regression, and that each step's own completion
    predicate matches the pane/subject its ``then`` advertises."""

    def test_the_five_shell_steps_carry_the_sentinels_required_anchors_in_order(self) -> None:
        shell_step_ids = [
            "learn_the_map_pane",
            "learn_the_wiki_pane",
            "learn_the_topology_pane",
            "learn_the_dashboard_pane",
            "pin_the_proletariat_to_the_watchlist",
        ]
        steps_by_id = {step.id: step for step in WAYNE_OPENING_ARC.steps}
        anchors = [steps_by_id[step_id].anchor for step_id in shell_step_ids]
        assert anchors == [
            "binding:Wiki:1-4",
            "binding:Wiki:1-4",
            "binding:Wiki:1-4",
            "binding:Wiki:1-4",
            "binding:Wiki:P",
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

    def test_the_five_shell_steps_appear_after_the_adversary_tail(self) -> None:
        """The shell-teaching tail follows ``read_the_repression_ledger`` —
        the player has read the county, the economy, AND the state
        apparatus's ledger before the room itself is taught, which is also
        what makes social_class/C001 the pin step's honest current subject
        (module docstring's own placement rationale)."""
        ids = [step.id for step in WAYNE_OPENING_ARC.steps]
        assert ids.index("read_the_repression_ledger") < ids.index("learn_the_map_pane")


class TestWatchlistRowNavStep:
    """The ``open_the_pinned_row_from_the_watchlist`` beat (unit
    "watchlist-row-nav", shell-interconnect): reuses the closed ``OnPage``
    predicate kind, carries a real ``option:`` anchor (never ``binding:`` —
    see the module docstring's own anchor-grammar note on why), and sits
    immediately after the pin it opens. No longer the arc's own final step
    (unit "verb-targeting" appends one more beat after it — see
    ``TestVerbTargetingStep`` below)."""

    def test_step_immediately_follows_the_pin(self) -> None:
        ids = [step.id for step in WAYNE_OPENING_ARC.steps]
        open_index = ids.index("open_the_pinned_row_from_the_watchlist")
        assert ids[open_index - 1] == "pin_the_proletariat_to_the_watchlist"

    def test_step_completion_reopens_the_same_subject_the_pin_step_pinned(self) -> None:
        step = next(
            s for s in WAYNE_OPENING_ARC.steps if s.id == "open_the_pinned_row_from_the_watchlist"
        )
        assert step.completion == OnPage(subject="social_class/C001")

    def test_step_anchor_names_the_real_watchlist_rail_and_a_real_row_open_key(self) -> None:
        """``option:<widget-id>:<key>`` (module docstring's fourth anchor
        prefix): ``watchlist-rail`` is the Rust chrome's own watchlist rail,
        and its row-open Enter is a live ``RailWatchlist`` keybar hint (M7
        cutover: the keybar replaced Textual's ``OptionList.BINDINGS`` as
        the option registry) — never a fictional pairing (no fiction)."""
        step = next(
            s for s in WAYNE_OPENING_ARC.steps if s.id == "open_the_pinned_row_from_the_watchlist"
        )
        kind, widget_id, key = step.anchor.split(":", 2)
        assert kind == "option"
        assert widget_id == "watchlist-rail"
        assert key == "enter"
        assert ("RailWatchlist", "Enter") in _LIVE_KEYBAR_OPTIONS


class TestVerbTargetingStep:
    """The ``issue_aid_on_the_proletariat`` beat (unit "verb-targeting",
    shell-interconnect): reuses the closed ``VerbIssued`` predicate kind
    (exactly as its own docstring already anticipated for "a future script"
    issuing "an Article-V player verb string"), and its own
    ``binding:ArchiveApp:f6`` anchor names a key the tutorial-coverage
    sentinel structurally cannot see (F1-F9 are generated via a
    ``*(Binding(...) for ...)`` unpacking inside ``ArchiveApp.BINDINGS`` — a
    computed, not a literal, action string — the same reason
    ``declared_bindings`` skips a computed key/action for ANY class; see
    ``babylon.sentinels._ast.declared_bindings``'s own docstring), so no
    exemption row is needed for it either. No longer the arc's own final
    step (unit "peek-hover-wire" appends one more beat after it, and unit
    "chronicle-row-nav-salience" one more after THAT — see
    ``TestPeekHoverWireStep``/``TestChronicleRowNavStep`` below)."""

    def test_step_immediately_follows_the_watchlist_open_and_precedes_the_peek_beat(
        self,
    ) -> None:
        ids = [step.id for step in WAYNE_OPENING_ARC.steps]
        assert ids[-3] == "issue_aid_on_the_proletariat"
        assert ids[-4] == "open_the_pinned_row_from_the_watchlist"
        assert ids[-2] == "peek_a_wikilink_with_the_keyboard"

    def test_step_completion_is_verb_issued_aid(self) -> None:
        step = next(s for s in WAYNE_OPENING_ARC.steps if s.id == "issue_aid_on_the_proletariat")
        assert step.completion == VerbIssued(verb="aid")

    def test_step_anchor_is_f6_the_real_aid_binding(self) -> None:
        """``aid`` is ``VERB_TO_ACTION_TYPE``'s 6th entry (educate, reproduce,
        attack, mobilize, campaign, aid, ...), zipped 1:1 onto
        ``_VERB_ACTION_KEYS`` (``babylon.tui.app``) — ``f6`` is real, not a
        guess."""
        from babylon.projection.verbs.preview import VERB_TO_ACTION_TYPE

        step = next(s for s in WAYNE_OPENING_ARC.steps if s.id == "issue_aid_on_the_proletariat")
        assert step.anchor == "binding:Wiki:F1-F9"
        assert list(VERB_TO_ACTION_TYPE)[5] == "aid"


class TestPeekHoverWireStep:
    """The ``peek_a_wikilink_with_the_keyboard`` beat (unit "peek-hover-wire",
    shell-interconnect): reuses the closed ``VerbIssued`` predicate kind as
    the documented honest floor (the same shape ``boot_into_lobby``'s own gap
    already established — no richer outcome is queryable because no baked
    page this arc reaches carries a real wikilink today), and its own
    ``binding:ArchiveApp:K`` anchor is a REAL, literal ``Binding`` on
    ``ArchiveApp.BINDINGS`` (unlike ``issue_aid_on_the_proletariat``'s
    computed F6), so authoring this step is what turns the tutorial-coverage
    sentinel's own ``K``-binding violation green — never an exemption
    (mirrors the five Program 24 P8 shell-teaching steps' own reasoning). No
    longer the arc's own final step (unit "chronicle-row-nav-salience"
    appends one more beat after it — see ``TestChronicleRowNavStep``
    below)."""

    def test_step_immediately_precedes_the_arcs_final_beat(self) -> None:
        ids = [step.id for step in WAYNE_OPENING_ARC.steps]
        assert ids[-2] == "peek_a_wikilink_with_the_keyboard"
        assert ids[-1] == "open_the_chronicle_rails_highlighted_row"

    def test_step_completion_is_the_documented_honest_floor(self) -> None:
        step = next(
            s for s in WAYNE_OPENING_ARC.steps if s.id == "peek_a_wikilink_with_the_keyboard"
        )
        assert step.completion == VerbIssued(verb="peek_wikilink")

    def test_step_anchor_is_capital_k_a_real_live_keybar_hint(self) -> None:
        step = next(
            s for s in WAYNE_OPENING_ARC.steps if s.id == "peek_a_wikilink_with_the_keyboard"
        )
        assert step.anchor == "binding:Wiki:K"
        assert ("Wiki", "K") in _LIVE_KEYBAR_OPTIONS


class TestChronicleRowNavStep:
    """The trailing ``open_the_chronicle_rails_highlighted_row`` beat (unit
    "chronicle-row-nav-salience", shell-interconnect): the arc's own new
    last step, reuses the closed ``OnPage`` predicate kind (proving the
    dossier's subject stays unchanged — the step's own VERIFIED honest-floor
    ``then``, see the module docstring's "Deviation from the task brief's
    literal beat list" section), and carries a real ``option:`` anchor
    (never ``binding:`` — mirrors ``open_the_pinned_row_from_the_watchlist``'s
    own THIRD anchor-grammar case)."""

    def test_step_is_now_the_arcs_final_beat(self) -> None:
        ids = [step.id for step in WAYNE_OPENING_ARC.steps]
        assert ids[-1] == "open_the_chronicle_rails_highlighted_row"

    def test_step_completion_proves_the_dossier_subject_stayed_unchanged(self) -> None:
        step = next(
            s for s in WAYNE_OPENING_ARC.steps if s.id == "open_the_chronicle_rails_highlighted_row"
        )
        assert step.completion == OnPage(subject="social_class/C001")

    def test_step_anchor_names_the_real_chronicle_rail_and_a_real_row_open_key(self) -> None:
        """``option:<widget-id>:<key>`` (module docstring's fourth anchor
        prefix): ``chronicle-rail`` is the Rust chrome's own chronicle rail,
        and its row-open Enter is a live ``Rail`` keybar hint (M7 cutover:
        the keybar replaced Textual's ``OptionList.BINDINGS`` as the option
        registry) — never a fictional pairing (no fiction)."""
        step = next(
            s for s in WAYNE_OPENING_ARC.steps if s.id == "open_the_chronicle_rails_highlighted_row"
        )
        kind, widget_id, key = step.anchor.split(":", 2)
        assert kind == "option"
        assert widget_id == "chronicle-rail"
        assert key == "enter"
        assert ("Rail", "Enter") in _LIVE_KEYBAR_OPTIONS


# --------------------------------------------------------------------------- #
# Rendering contract.
# --------------------------------------------------------------------------- #


class TestRenderingContract:
    """``scenario_name``/``overlay_text`` derive verbatim from the fields —
    no separately-authored prose duplicate anywhere.
    """

    def test_scenario_name_contains_every_field_verbatim(self) -> None:
        for step in WAYNE_OPENING_ARC.steps:  # loop bound: len(steps) == 24
            assert step.given in step.scenario_name
            assert step.when in step.scenario_name
            assert step.then in step.scenario_name

    def test_overlay_text_contains_every_field_verbatim(self) -> None:
        for step in WAYNE_OPENING_ARC.steps:  # loop bound: len(steps) == 24
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
        for step in WAYNE_OPENING_ARC.steps:  # loop bound: len(steps) == 24
            assert step.scenario_name.endswith(".")
            assert "\n" not in step.scenario_name


# --------------------------------------------------------------------------- #
# Patches (M3 seam contract §0/§8, Director directive): a REQUIRED           #
# `patches: str` field, min_length=1 — the guide's one dialogue line per     #
# step, DATA never a hardcoded UI string.                                    #
# --------------------------------------------------------------------------- #


class TestPatchesField:
    """`TutorialStep` gains a REQUIRED ``patches: str`` (min_length=1) —
    exactly like ``given``/``when``/``then``/``anchor``, so this class
    extends those two existing pins rather than inventing new machinery."""

    def test_patches_is_required(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            TutorialStep(
                id="a",
                given="g",
                when="w",
                then="t",
                anchor="page:x",
                completion=OnPage(subject="x"),
            )  # type: ignore[call-arg]

    def test_patches_rejects_empty_string(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            TutorialStep(
                id="a",
                given="g",
                when="w",
                then="t",
                anchor="page:x",
                completion=OnPage(subject="x"),
                patches="",
            )


class TestPatchesAuthoredTable:
    """The Director-authored §8 patches table — 24 lines, one per step, in
    arc order. Exact strings pinned for the FIRST and LAST step (content
    review of the other 22 is Gate 3's own agenda item, per the contract's
    own §6 — not re-litigated here); every step gets presence + uniqueness
    pins as a durable regression."""

    def test_every_step_has_a_non_empty_patches_line(self) -> None:
        assert len(WAYNE_OPENING_ARC.steps) == 24
        for step in WAYNE_OPENING_ARC.steps:  # loop bound: len(steps) == 24
            assert step.patches.strip() != ""

    def test_first_step_patches_line_matches_the_authored_table(self) -> None:
        step = WAYNE_OPENING_ARC.steps[0]
        assert step.id == "boot_into_lobby"
        assert step.patches == (
            "Hi — I'm Patches! That lobby's empty. Let's mint our very first campaign together."
        )

    def test_last_step_patches_line_matches_the_authored_table(self) -> None:
        step = WAYNE_OPENING_ARC.steps[-1]
        assert step.id == "open_the_chronicle_rails_highlighted_row"
        assert step.patches == (
            "The chronicle keeps the record. Today its top row is just the pause "
            "marker — but soon, the events will carry names."
        )

    def test_patches_lines_are_pairwise_distinct(self) -> None:
        """Each of the 24 steps earns its OWN line — no copy-pasted filler."""
        lines = [step.patches for step in WAYNE_OPENING_ARC.steps]
        assert len(lines) == len(set(lines))
