"""The tutorial step script — the T6 unification (Program v1.0.0, Unit U1).

Per ``ai/_inbox/t6-tutorial-bdd-ruling.md`` (BD, 2026-07-21): the opening-arc
tutorial IS the BDD acceptance suite. ONE data artifact —
:class:`TutorialScript` — is meant to be consumed three ways: the player
overlay renders each :class:`TutorialStep`'s Given/When/Then as instruction
text over the live campaign; a headless Textual-Pilot executor drives the
When and hard-asserts the Then; the developer-facing docs read the same
steps as living specification. Because all three consumers read the SAME
fields, "the strings the player reads ARE the scenario definitions CI
runs" — there is no second, separately-authored copy of this prose anywhere
(:attr:`TutorialStep.scenario_name` / :attr:`TutorialStep.overlay_text`
below both derive verbatim from ``given``/``when``/``then``; nothing else
in this module, or any future consumer, is licensed to hardcode a parallel
description).

This unit ships ONLY the model + the authored opening-arc script (the
ruling's own placement note: the overlay consumer, the Pilot executor, the
option-coverage sentinel, and the transcript emitter are separate T6 units
building on this one).

Completion predicates are DATA, never callables (the ruling: "no prose
duplication anywhere, ever" generalizes to "no hidden behavior anywhere
either" — a lambda could not serialize into the overlay/docs the way a
Pydantic model does). The closed vocabulary was five kinds through Unit U1;
Program 24 P8 ("the tutorial learns the shell") adds two more, for exactly
the seven kinds an opening-arc teaching script needs today:

* :class:`OnPage` — the player is viewing a named dossier subject.
* :class:`TickAtLeast` — the campaign has resolved at least a given tick.
* :class:`PausePending` — an autopause has become pending — the paced
  driver actually STOPPED, not merely that a run was requested. The
  load-bearing symmetric counterpart to :class:`EventAcked` below,
  grounded on the live :attr:`~babylon.game.pacing.PacedTickDriver.
  awaiting_ack`/:attr:`~babylon.game.pacing.PacedTickDriver.
  pending_pause` state (the same primitives
  :class:`~babylon.tui.app.PacedDriverHandle` already crosses the
  tui/game seam with). Added in this unit's fix pass: a step whose
  ``then`` advertises "the driver ... stops" must be verified by a
  predicate that actually checks the stop — :class:`VerbIssued` alone
  cannot distinguish "ran and stopped as designed" from "ran and kept
  going".
* :class:`EventAcked` — a pending autopause has been acknowledged.
* :class:`VerbIssued` — a named verb/binding action has been issued (this
  covers BOTH a TUI keybinding's action name — ``"advance_tick"``,
  ``"run_until_paused"`` — and, in a future script, an Article-V player
  verb string; the ruling's own anchor phrasing, "the page/binding/verb it
  exercises", already treats bindings and verbs as one family). This is
  the HONEST FLOOR only where no outcome-shaped predicate is queryable
  yet (e.g. ``boot_into_lobby`` below, pre-campaign — there is no page or
  tick to read FROM yet); it proves dispatch, never the advertised
  outcome, and must not stand in for an outcome predicate where one is
  available (the fix pass's ``begin_the_operation`` correction).
* :class:`PaneShowing` — Program 24 P8 addition: the hybrid shell's
  ``ContentSwitcher`` (:class:`~babylon.tui.app.ArchiveApp`'s ``#main``) is
  currently showing a named domain pane (``"dashboard"``/``"map"``/
  ``"wiki"``/``"topology"``). Grounded on the SAME
  :attr:`~textual.widgets.ContentSwitcher.current` attribute
  :meth:`~babylon.tui.app.ArchiveApp.action_switch_view` itself sets — never
  a rendered-text guess about which pane is visible.
* :class:`PinnedInWatchlist` — Program 24 P8 addition: a named subject
  currently holds a pin on the right rail's watchlist. Grounded on
  :meth:`~babylon.tui.watchlist.WatchlistState.is_pinned`, the same real
  domain-state query :meth:`~babylon.tui.app.ArchiveApp.action_toggle_pin`
  itself consults — never a "the rail's text contains the id" guess.

:data:`CompletionPredicateAdapter` validates against exactly this closed set
— an unrecognized ``kind`` raises :class:`pydantic.ValidationError` loudly
(Constitution III.11), never a silently-ignored predicate.

**Anchor grammar** (a plain string field, not its own typed union — the
ruling names anchor as a single field; the option-coverage sentinel, a
later unit, is where matching anchors against live registries belongs, not
here). Three prefixes, used consistently by the authored script below:

* ``"binding:<ClassName>:<key>"`` — a :class:`~textual.binding.Binding`
  entry's key on that Textual class's own ``BINDINGS`` (qualified by class
  name because the same key means different things on different
  screens — ``"a"`` is ``LobbyScreen``'s archive-toggle but
  ``ArchiveApp``'s acknowledge-pause).
* ``"page:<subject>"`` — a vault-baked dossier subject id (the
  ``babylon.tui.app.PageSource``/``CampaignHandle.read_page`` convention).
* ``"palette:<subject>"`` — a command-palette
  (:class:`~babylon.tui.palette.EntityNavigatorProvider`) pick of that
  known subject.

Every anchor below was verified against the LIVE registries before
authoring (Constitution: no fiction) — ``babylon.tui.app.ArchiveApp.
BINDINGS`` (``t``/``r``/``a``/``ctrl+o``/``ctrl+i``, and — Program 24 P8 —
``1``/``2``/``3``/``4`` (:meth:`~babylon.tui.app.ArchiveApp.action_switch_view`)
and ``p`` (:meth:`~babylon.tui.app.ArchiveApp.action_toggle_pin`)),
``babylon.tui.
app.BriefingScreen.BINDINGS`` (``enter``), ``babylon.tui.campaign_menu.
LobbyScreen.BINDINGS`` (``n``/``a``/``d``/``escape``), and the real baked
subjects ``county/26163`` (Wayne — ruling 3, "Wayne stays in lobby"),
``economy/USA`` (:mod:`babylon.projection.vault.tick_baker`'s singleton
economy dossier, carrying the real Fundamental Theorem verdict —
:attr:`~babylon.projection.view_models.EconomyView.labor_aristocracy_verdict`)
via ``tests/unit/tui/test_t3_live_reachability.py``'s own
``TestCommandPaletteSurfacesT3Pages`` (a palette search for ``"economy"``
finds ``"economy/USA"`` on a live campaign, proving the ``palette:``
anchor below is real, not aspirational).

**Deviation from the task brief's literal beat list** ("... advance a tick
-> read the chronicle -> run to autopause -> ..."): there is today no live
Chronicle screen wired into :class:`~babylon.tui.app.ArchiveApp` —
:mod:`babylon.tui.chronicle`'s ``render_chronicle``/``chronicle_stream`` are
real, tested, and fed real per-tick content by
:func:`~babylon.game.chronicle_adapter.chronicle_events_from_bus`, but no
production caller mounts them as a screen or widget yet (verified by
grepping every non-test caller). Authoring a "read the chronicle" STEP
would be exactly the fiction the ruling forbids ("do NOT author steps for
verbs/options that do not exist in the shell today"). The tick's real
outcome — what the chronicle would show — is instead folded into
``advance_a_tick``'s own Then-clause (the status line reports it); wiring a
live Chronicle screen and giving it its own step is a future unit's honest
gap to close, not this one's to fabricate.
"""

from __future__ import annotations

from typing import Annotated, Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from babylon.engine.scenarios.wayne_county import WayneCountyScenario

__all__ = [
    "EventAcked",
    "OnPage",
    "PaneShowing",
    "PausePending",
    "PinnedInWatchlist",
    "TickAtLeast",
    "VerbIssued",
    "CompletionPredicate",
    "CompletionPredicateAdapter",
    "TutorialStep",
    "TutorialScript",
    "WAYNE_OPENING_ARC",
]

#: Shared id-slug shape for both a step's own id and a script's id: lowercase,
#: starts with a letter, ``[a-z0-9_]`` after — a stable machine key, never a
#: free-text title (that lives in ``given``/``when``/``then`` instead).
_ID_PATTERN: Final[str] = r"^[a-z][a-z0-9_]*$"


class OnPage(BaseModel):
    """Then: the player is viewing ``subject``'s dossier page.

    :param subject: the vault-relative subject id (e.g. ``"county/26163"``),
        matching :data:`babylon.tui.app.PageSource`'s own convention.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["on_page"] = "on_page"
    subject: str = Field(min_length=1)


class TickAtLeast(BaseModel):
    """Then: the campaign has resolved at least tick ``tick``.

    :param tick: the minimum committed tick this predicate is satisfied by.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["tick_at_least"] = "tick_at_least"
    tick: int = Field(ge=0)


class PausePending(BaseModel):
    """Then: the paced driver has actually STOPPED at a pending autopause.

    Grounds on :attr:`~babylon.game.pacing.PacedTickDriver.awaiting_ack`
    being ``True`` (equivalently, :attr:`~babylon.game.pacing.
    PacedTickDriver.pending_pause` being non-``None``) — the same two
    primitives :class:`~babylon.tui.app.PacedDriverHandle` already
    exposes across the tui/game structural seam, so a later executor unit
    can check this predicate without importing ``babylon.game.pacing``
    itself. Deliberately unconditional (no ``tick`` filter), mirroring
    :class:`EventAcked`'s own YAGNI reasoning: the opening-arc script only
    ever teaches ONE run-until-autopause beat.

    Reviewer finding (T6 U1 fix pass): ``VerbIssued(verb="run_until_paused")``
    proves only that the keypress dispatched, never that the driver
    actually stopped — a step whose ``then`` advertises the STOP behavior
    needs a predicate that checks the stop, not the dispatch.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["pause_pending"] = "pause_pending"


class EventAcked(BaseModel):
    """Then: the pending autopause has been acknowledged.

    Unconditional by design (no ``event_type``/``tick`` filter): the
    opening-arc script only ever teaches ONE acknowledge beat, and a later
    script needing to distinguish which pending pause it acks can widen
    this predicate kind then — never with an ad hoc field this unit does
    not exercise (YAGNI, CLAUDE.md "no features beyond what was asked").
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["event_acked"] = "event_acked"


class VerbIssued(BaseModel):
    """Then: the named verb/binding action has been issued.

    :param verb: an action name — either a TUI binding's own
        ``Binding(key, action, ...)`` action string (e.g.
        ``"advance_tick"``, ``"run_until_paused"``, ``"begin"``,
        ``"new_campaign"``) or, in a future script, an Article-V player
        verb string (e.g. ``"educate"``). Never the raw KEY (``"t"``) —
        the action name is what a remapped keybinding would still share.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["verb_issued"] = "verb_issued"
    verb: str = Field(min_length=1)


class PaneShowing(BaseModel):
    """Then: the hybrid shell's ``ContentSwitcher`` is currently showing ``pane``.

    Program 24 P8 addition ("the tutorial learns the shell"): teaches the
    four-pane hybrid layout's own domain switcher
    (:meth:`~babylon.tui.app.ArchiveApp.action_switch_view`, bound to keys
    ``1``-``4``).

    :param pane: one of the four live domain-pane ids —
        ``"dashboard"``/``"map"``/``"wiki"``/``"topology"`` — matching
        :meth:`~babylon.tui.app.ArchiveApp.action_switch_view`'s own ``view``
        parameter verbatim (a plain string, not a narrower
        :class:`~typing.Literal`, for the same reason that method's own
        parameter is one: a future fifth pane needs no change to this
        predicate's shape, only a new authored step).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["pane_showing"] = "pane_showing"
    pane: str = Field(min_length=1)


class PinnedInWatchlist(BaseModel):
    """Then: ``subject`` currently holds a pin on the right rail's watchlist.

    Program 24 P8 addition ("the tutorial learns the shell"): teaches the
    watchlist pin/unpin action
    (:meth:`~babylon.tui.app.ArchiveApp.action_toggle_pin`, bound to ``p``).
    Grounded on :meth:`~babylon.tui.watchlist.WatchlistState.is_pinned` —
    the same real domain-state query the action itself consults before
    deciding to pin or unpin — never a "the rendered rail's text contains
    the id" guess (a pinned subject absent from the app's own
    ``_subject_views`` map still renders its own honest "no longer
    resolvable" row, which would make a text-only check ambiguous about
    whether the PIN itself succeeded).

    :param subject: the vault-relative subject id (:class:`OnPage`'s own
        convention) expected to be pinned.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["pinned_in_watchlist"] = "pinned_in_watchlist"
    subject: str = Field(min_length=1)


CompletionPredicate = Annotated[
    OnPage | TickAtLeast | PausePending | EventAcked | VerbIssued | PaneShowing | PinnedInWatchlist,
    Field(discriminator="kind"),
]
"""The closed completion-predicate vocabulary (module docstring). Every
:class:`TutorialStep` carries exactly one — DATA, never a callable, so the
same script serializes for the overlay, the Pilot executor, and the docs."""

CompletionPredicateAdapter: TypeAdapter[
    OnPage | TickAtLeast | PausePending | EventAcked | VerbIssued | PaneShowing | PinnedInWatchlist
] = TypeAdapter(CompletionPredicate)
"""Validates a raw ``{"kind": ..., ...}`` payload against the closed set
above. An unrecognized ``kind`` (or one missing it) raises
:class:`pydantic.ValidationError` loudly (Constitution III.11) — there is
no silent fallback predicate kind."""

#: Generous static bound on ``anchor``'s length (Power-of-10 rule: every
#: bounded thing gets a named, provable ceiling, not an implicit one) —
#: anchors are short identifiers (``"binding:ArchiveApp:ctrl+o"``), never
#: prose; this sits far above any real anchor string.
_MAX_ANCHOR_LEN: Final[int] = 256


class TutorialStep(BaseModel):
    """One Given/When/Then teaching beat, keyed to one real UI anchor.

    :param id: a stable machine key, unique within its
        :class:`TutorialScript` (validated there, not here — uniqueness is
        a property of the SET of steps, not of one step in isolation).
    :param given: the precondition sentence fragment.
    :param when: the player's action sentence fragment.
    :param then: the observable-result sentence fragment.
    :param anchor: the page/binding/verb this step exercises (module
        docstring's anchor grammar).
    :param completion: the DATA predicate (:data:`CompletionPredicate`)
        proving ``then`` actually happened.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1, pattern=_ID_PATTERN)
    given: str = Field(min_length=1)
    when: str = Field(min_length=1)
    then: str = Field(min_length=1)
    anchor: str = Field(min_length=1, max_length=_MAX_ANCHOR_LEN)
    completion: CompletionPredicate

    @property
    def scenario_name(self) -> str:
        """The step's scenario-name sentence — the developer-docs title.

        Derives VERBATIM from :attr:`given`/:attr:`when`/:attr:`then` (the
        rendering contract this module's docstring names): there is no
        second, separately-authored title string anywhere for this step.
        Mirrors :class:`~babylon.tui.campaign_menu.LobbyRow`'s own
        ``label`` property — a frozen model's derived display string.
        """
        return f"Given {self.given}, when {self.when}, then {self.then}."

    @property
    def overlay_text(self) -> str:
        """The player-facing overlay block — the SAME fields,
        :attr:`scenario_name`'s sibling rendering (module docstring: "no
        prose duplication anywhere, ever"). A future opening-arc overlay
        consumer renders exactly this, never a separately-authored copy.
        """
        return f"GIVEN: {self.given}\nWHEN: {self.when}\nTHEN: {self.then}"


#: Generous static bound on a script's step count (Power-of-10 rule 2): the
#: authored Wayne arc below has 9; this sits far above any teaching arc a
#: single opening session would plausibly need.
_MAX_SCRIPT_STEPS: Final[int] = 64


class TutorialScript(BaseModel):
    """An ordered, uniquely-keyed sequence of :class:`TutorialStep`\\ s.

    :param id: the script's own stable machine key.
    :param scenario: the engine scenario this script is authored against
        (e.g. ``"wayne_county"`` — :attr:`~babylon.engine.scenarios.
        wayne_county.WayneCountyScenario.name`, reused rather than
        re-typed, so the two never drift). The headless Pilot executor
        (a later T6 unit) boots exactly this scenario before driving the
        script — never an unstated implicit one.
    :param steps: the ordered beats; length bounded by
        :data:`_MAX_SCRIPT_STEPS` (Power-of-10 rule 2).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1, pattern=_ID_PATTERN)
    scenario: str = Field(min_length=1)
    steps: tuple[TutorialStep, ...] = Field(min_length=1, max_length=_MAX_SCRIPT_STEPS)

    @model_validator(mode="after")
    def _unique_step_ids(self) -> Self:
        """Reject a script whose steps do not carry pairwise-distinct ids.

        :raises ValueError: on the first duplicate id found (loud, not a
            silently-deduplicated script — Constitution III.11).
        """
        seen: set[str] = set()
        for step in self.steps:  # loop bound: len(self.steps) <= _MAX_SCRIPT_STEPS
            if step.id in seen:
                msg = f"TutorialScript {self.id!r}: duplicate step id {step.id!r}"
                raise ValueError(msg)
            seen.add(step.id)
        return self


WAYNE_OPENING_ARC: Final[TutorialScript] = TutorialScript(
    id="wayne_opening_arc",
    scenario=WayneCountyScenario.name,
    steps=(
        TutorialStep(
            id="boot_into_lobby",
            given="a fresh boot with no campaign chosen yet, the campaign lobby showing",
            when="the player presses 'n' to mint a new campaign",
            then="a freshly minted campaign row appears in the lobby, ready to be loaded",
            anchor="binding:LobbyScreen:n",
            # Honest gap (reviewer finding, T6 U1 fix pass): no page/tick
            # outcome predicate is queryable pre-campaign — there is no
            # campaign yet to read a page or a tick FROM — so VerbIssued
            # is the honest floor here, not a shortcut. This proves ONLY
            # that the keypress dispatched; the advertised "row appears"
            # outcome is left unverified by this step. A future
            # rendered-text predicate (module docstring's OBSERVATION on
            # the closed vocabulary) is the eventual fix; until then the
            # executor must not over-certify this step's `then` from a
            # green run of this predicate alone.
            completion=VerbIssued(verb="new_campaign"),
        ),
        TutorialStep(
            id="begin_the_operation",
            given="the freshly minted campaign is chosen and its Scenario Briefing dossier is showing",
            when="the player presses Enter to begin the operation",
            then="the campaign shell reveals Wayne County's own home dossier",
            anchor="binding:BriefingScreen:enter",
            # Verifies the advertised OUTCOME (the dossier reveal), not
            # merely the keypress dispatch — unlike boot_into_lobby above,
            # an outcome predicate IS queryable here (reviewer finding,
            # T6 U1 fix pass): self-contained rather than relying on the
            # next step's OnPage to cover it after the fact.
            completion=OnPage(subject="county/26163"),
        ),
        TutorialStep(
            id="read_the_county_dossier",
            given="the campaign shell has just revealed Wayne County's home dossier at tick 0",
            when="the player reads county/26163's page",
            then="the county dossier's statblock renders Wayne's own material state, not a fixture",
            anchor="page:county/26163",
            completion=OnPage(subject="county/26163"),
        ),
        TutorialStep(
            id="advance_a_tick",
            given="Wayne County's dossier is showing at tick 0",
            when="the player presses 't' to advance one tick",
            then=(
                "the campaign resolves tick 1 through the full 30-system engine and "
                "the status line reports the tick just committed"
            ),
            anchor="binding:ArchiveApp:t",
            completion=TickAtLeast(tick=1),
        ),
        TutorialStep(
            id="run_until_autopause",
            given="the campaign has resolved at least one tick",
            when="the player presses 'r' to run until an autopause or the endgame lock",
            then=(
                "the paced driver auto-advances through uneventful ticks and stops the "
                "instant a critical event or the endgame pattern fires"
            ),
            anchor="binding:ArchiveApp:r",
            # Verifies the advertised STOP itself (reviewer finding, T6 U1
            # fix pass) — VerbIssued would prove only that the keypress
            # dispatched, not that the driver actually stopped, which is
            # the whole point of this Then. See PausePending's own
            # docstring for the grounding (PacedTickDriver.awaiting_ack /
            # .pending_pause).
            completion=PausePending(),
        ),
        TutorialStep(
            id="acknowledge_the_pause",
            given="an autopause is pending after a run",
            when="the player presses 'a' to acknowledge it",
            then="the pending autopause clears and further 't'/'r' presses are permitted again",
            anchor="binding:ArchiveApp:a",
            completion=EventAcked(),
        ),
        TutorialStep(
            id="palette_to_the_economy_dossier",
            given="the campaign shell is showing any dossier page",
            when="the player opens the command palette with Ctrl-P and picks economy/USA",
            then="the dossier pane navigates to the national economy dossier",
            anchor="palette:economy/USA",
            completion=OnPage(subject="economy/USA"),
        ),
        TutorialStep(
            id="read_the_theorem_verdict",
            given="the economy dossier is showing",
            when="the player reads its Fundamental Theorem verdict",
            then=(
                "the wage balance and the labor-aristocracy verdict render as real numbers "
                "read off the SAME opposition the engine itself adjudicates, never a "
                "fabricated parallel feed"
            ),
            anchor="page:economy/USA",
            completion=OnPage(subject="economy/USA"),
        ),
        TutorialStep(
            id="jump_back_to_wayne",
            given="the player has navigated away from Wayne County's dossier to economy/USA",
            when="the player presses Ctrl-O to walk back one jumplist step",
            then="the dossier pane returns to county/26163, the campaign's own home page",
            anchor="binding:ArchiveApp:ctrl+o",
            completion=OnPage(subject="county/26163"),
        ),
        # Program 24 P8 ("the tutorial learns the shell") — five more beats,
        # placed here because the player has just finished reading both
        # dossiers (Wayne's own, the economy's) and walking back: the core
        # single-pane loop is taught, so now the room itself — the hybrid
        # shell's other three panes plus the watchlist rail — is. Wayne's
        # own dossier (county/26163) is still the dossier's current subject
        # throughout this whole tail (switching panes never itself
        # navigates), which is what makes pin_wayne_to_the_watchlist's own
        # hardcoded expected subject an HONEST expectation rather than a
        # guess (see this step's own docstring cross-reference in
        # tests/unit/game/test_tutorial.py).
        TutorialStep(
            id="learn_the_map_pane",
            given="the player has walked back to Wayne County's own home dossier in the Wiki pane",
            when="the player presses '2' to switch to the Map pane",
            then="the main region switches to the Map pane, the hybrid shell's own choropleth view",
            anchor="binding:ArchiveApp:2",
            completion=PaneShowing(pane="map"),
        ),
        TutorialStep(
            id="learn_the_wiki_pane",
            given="the Map pane is showing",
            when="the player presses '3' to switch back to the Wiki pane",
            then=(
                "the main region switches back to the Wiki pane, Wayne County's own "
                "dossier still showing beneath it"
            ),
            anchor="binding:ArchiveApp:3",
            completion=PaneShowing(pane="wiki"),
        ),
        TutorialStep(
            id="learn_the_topology_pane",
            given="the Wiki pane is showing",
            when="the player presses '4' to switch to the Topology pane",
            then="the main region switches to the Topology pane, the hybrid shell's own graph view",
            anchor="binding:ArchiveApp:4",
            completion=PaneShowing(pane="topology"),
        ),
        TutorialStep(
            id="learn_the_dashboard_pane",
            given="the Topology pane is showing",
            when="the player presses '1' to switch to the Dashboard pane",
            then=(
                "the main region switches to the Dashboard pane, the hybrid shell's own "
                "live HUD and economy view"
            ),
            anchor="binding:ArchiveApp:1",
            completion=PaneShowing(pane="dashboard"),
        ),
        TutorialStep(
            id="pin_wayne_to_the_watchlist",
            given="the Dashboard pane is showing and county/26163 is still the dossier's own current subject",
            when="the player presses 'p' to pin the current subject",
            then="county/26163 is pinned onto the right rail's watchlist",
            anchor="binding:ArchiveApp:p",
            completion=PinnedInWatchlist(subject="county/26163"),
        ),
    ),
)
"""The Wayne first-session opening arc (Program v1.0.0 T6, Unit U1; extended by
Program 24 P8 with the shell-teaching tail) — the core loop end-to-end over
what the shell actually does today: lobby -> briefing -> the county dossier ->
a tick -> a run to autopause -> acknowledge -> the command palette -> the
economy dossier's theorem verdict -> jump back -> the Map/Wiki/Topology/
Dashboard panes -> pin Wayne to the watchlist. Every anchor and subject id above was checked against the
live registries before authoring (module docstring)."""
