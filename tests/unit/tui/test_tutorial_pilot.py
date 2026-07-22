"""The headless Pilot executor for the tutorial-as-BDD suite (Program v1.0.0
T6, Unit U2).

Per ``ai/_inbox/t6-tutorial-bdd-ruling.md``: the same
:data:`~babylon.game.tutorial.WAYNE_OPENING_ARC` step script the (future)
player overlay renders is executed here headlessly — drive each step's
``when`` through a real Textual ``Pilot``, then hard-assert its ``then``
via its own closed-vocabulary completion predicate. Assertion tiers strictly
ordered per the ruling: semantic TEXT first (rendered dossier content, the
status line), structural Pilot state second (``nav.current``, the paced
driver's own ``awaiting_ack``) only where a string alone would be ambiguous,
never a visual/pixel comparison.

**Review fix pass**: ``OnPage`` alone (nav.current + non-emptiness) is a
navigation-only check — it cannot distinguish a step whose ``then`` merely
advertises "the dossier pane shows/returns to X" from one whose ``then``
advertises specific rendered CONTENT ("the wage balance ... render as real
numbers", "Wayne's own material state, not a fixture"). Two steps
(``read_the_county_dossier``, ``read_the_theorem_verdict``) are the latter
kind; :func:`drive_step` layers a distinctive-token check onto those two
(:data:`_EXTRA_CONTENT_CHECK_BY_STEP_ID`) rather than widening ``OnPage``
itself or adding a new :data:`~babylon.game.tutorial.CompletionPredicate`
kind in U1 — a reviewer-specified, minimally-scoped fix over U2's own
assertion path.

Runs against a REAL :class:`~babylon.game.session.GameSession` — the real
30-system engine, the real :class:`~babylon.game.pacing.PacedTickDriver` +
:class:`~babylon.engine.observers.endgame_detector.EndgameDetector`, and a
real vault bake (:class:`~babylon.projection.vault.tick_baker.
ArchiveTickBaker` over a ``dulwich``-backed temp directory), so
``county/26163``/``economy/USA`` are REAL rendered pages, never a fixture
lookalike (the T3 idiom, ``test_t3_live_reachability.py``). The ONE thing
faked is Postgres itself (:class:`_InMemoryGameStore`, structurally
satisfying :class:`~babylon.game.session.GameRuntimeStore` — the SAME
WO-37 trick :mod:`babylon.game.session` itself documents), which is what
keeps this whole module at the UNIT tier per the T6 ruling's own tier
split ("pure-Pilot steps with a fake handle can stay unit-tier") — the
PG-reachable tier law belongs to ``tests/integration/game/
test_session_integration.py``, which this module never needs to duplicate
since nothing here talks to a real database.

**Wayne's own material state autopauses on TICK 1** (verified empirically
against this exact composition: ``ECOLOGICAL_OVERSHOOT``/``PERIPHERAL_
REVOLT`` fire critical-tier every single tick under
:func:`~babylon.game.session.default_pause_predicate` — not a rare event
this scenario's coefficients eventually cross into, but its steady state
from tick 0 onward). This is an HONEST GAP in the authored arc, surfaced
by running it for real (exactly what the ruling promises BDD-as-truth
would do — "a step that stops being true goes red ... before a player ever
sees the lie"): ``advance_a_tick``'s own ``t`` press already leaves the
driver ``awaiting_ack``, so ``run_until_autopause``'s ``r`` press is
observably a NO-OP refusal ("autopause pending ... press 'a' to
acknowledge"), never a genuine multi-tick auto-run through "uneventful"
ticks — there are none to run through. ``PausePending()``'s own
completion predicate still holds (the STOP-state the step's ``then``
names), so this suite does not fail, but the "auto-advances through
uneventful ticks" prose is not exercised by this concrete scenario; the
real multi-tick auto-run behavior is separately proven by
``tests/unit/tui/test_app_pacing_driver.py::TestRunUntilPaused`` (a
scripted fake driver) and ``tests/unit/game/test_pacing.py`` (the driver's
own unit tests). Flagged here for a future scenario-tuning/BD review, not
silently smoothed over (Constitution III.11) — see
``TestRunUntilAutopauseHonestGap`` below, which pins the no-op finding as
a durable regression rather than a one-time comment.
"""

from __future__ import annotations

import io
import re
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Final, cast
from unittest import mock
from uuid import UUID

import pytest
from rich.console import Console
from textual.content import Content
from textual.pilot import Pilot
from textual.widgets import Label, OptionList

from babylon.engine.scenarios import WayneCountyScenario
from babylon.game.pacing import PacedTickDriver, paced_driver_for_session
from babylon.game.session import (
    GameSession,
    create_new_campaign,
    vault_known_subjects,
    vault_page_source,
)
from babylon.game.tutorial import (
    WAYNE_OPENING_ARC,
    EventAcked,
    OnPage,
    PausePending,
    TickAtLeast,
    TutorialStep,
    VerbIssued,
)
from babylon.persistence.envelope import PerTickTransactionEnvelope
from babylon.projection.briefing import project_briefing
from babylon.projection.vault.materializer import VaultMaterializer
from babylon.projection.vault.tick_baker import ArchiveTickBaker
from babylon.topology import BabylonGraph
from babylon.tui.app import ArchiveApp, BabylonMarkdown, CampaignHandle
from babylon.tui.campaign_menu import CampaignMenu, InMemoryCampaignCatalog
from babylon.tui.palette import EntityNavigated
from babylon.tui.router import parse_babylon_uri

pytestmark = pytest.mark.unit

_WAYNE_FIPS: Final = "26163"
#: Wide enough that the economy dossier's statblock rows are not truncated —
#: a deliberate choice over Textual's own ``run_test`` default (80, 24), made
#: for THIS module's own transcript readability (module docstring: the
#: transcript doubles as developer documentation).
_PILOT_SIZE: Final[tuple[int, int]] = (120, 50)
#: The lobby mints a campaign id via a bare ``uuid4()`` call
#: (``CampaignMenu.new_campaign`` -> ``InMemoryCampaignCatalog.
#: create_campaign``) with no seam to inject one — unlike
#: ``create_new_campaign``'s own ``session_id=`` parameter. Pinning this ONE
#: genuinely-random id (via ``mock.patch`` on ``campaign_menu``'s own
#: ``uuid4`` import, in :func:`_live_pilot` below) is what keeps the lobby
#: row's derived codename — real, on-screen, transcript content — identical
#: across two independent runs; it never touches the engine's own
#: ``rng_seed`` determinism (Constitution III.7), which is already fixed by
#: ``WayneCountyScenario``'s own default (``rng_seed=0``).
_PINNED_CAMPAIGN_ID: Final = UUID(int=99)


# --------------------------------------------------------------------------- #
# The in-memory GameRuntimeStore double — keeps this module at the unit tier. #
# --------------------------------------------------------------------------- #


class _InMemoryGameStore:
    """A minimal in-memory double satisfying ``GameRuntimeStore`` structurally.

    Mirrors ``tests/unit/game/test_session.py``'s own ``_FakeStore`` shape
    (not imported directly — that class is private to its own test module,
    and this one's needs are a strict subset); the WO-37 structural-Protocol
    trick means :mod:`babylon.game.session` cannot tell this apart from a
    real :class:`~babylon.persistence.postgres_runtime.PostgresRuntime`.
    """

    def __init__(self) -> None:
        self._sessions: dict[UUID, dict[str, Any]] = {}
        self._graphs: dict[tuple[UUID | None, int], BabylonGraph] = {}
        self._last_committed: dict[UUID, int] = {}

    def create_session(
        self,
        scenario: str,
        config_json: dict[str, Any],
        game_defines_json: dict[str, Any],
        rng_seed: int,
        *,
        trace_level: str = "NONE",
        player_id: int | None = None,
        session_id: UUID | None = None,
    ) -> UUID:
        """See ``GameRuntimeStore.create_session``."""
        resolved = session_id if session_id is not None else UUID(int=len(self._sessions))
        self._sessions[resolved] = {
            "id": resolved,
            "scenario": scenario,
            "config_json": config_json,
            "game_defines_json": game_defines_json,
            "rng_seed": rng_seed,
            "trace_level": trace_level,
            "player_id": player_id,
        }
        return resolved

    def get_session(self, session_id: UUID) -> dict[str, Any] | None:
        """See ``GameRuntimeStore.get_session``."""
        return self._sessions.get(session_id)

    def get_pending_turns(self, session_id: UUID, tick: int) -> list[dict[str, Any]]:
        """See ``GameRuntimeStore.get_pending_turns`` — this suite never
        submits a player verb, so this is honestly always empty."""
        return []

    def mark_turns_resolved(self, session_id: UUID, tick: int) -> int:
        """See ``GameRuntimeStore.mark_turns_resolved``."""
        return 0

    def persist_tick(
        self,
        tick: int,
        graph: BabylonGraph,
        events: list[dict[str, Any]] | None = None,
        *,
        session_id: UUID | None = None,
    ) -> None:
        """See ``GameRuntimeStore.persist_tick``."""
        self._graphs[(session_id, tick)] = graph

    def persist_tick_summary(
        self,
        tick: int,
        summary: dict[str, Any],
        *,
        session_id: UUID,
    ) -> None:
        """See ``GameRuntimeStore.persist_tick_summary``."""

    def hydrate_graph(
        self, tick: int | None = None, *, session_id: UUID | None = None
    ) -> BabylonGraph:
        """See ``GameRuntimeStore.hydrate_graph`` — unused (this suite never
        crash-resumes), kept only for structural completeness."""
        if tick is None:
            tick = max(t for sid, t in self._graphs if sid == session_id)
        return self._graphs[(session_id, tick)]

    def persist_tick_atomic(
        self, envelope: PerTickTransactionEnvelope, *, write_commit_marker: bool = True
    ) -> None:
        """See ``GameRuntimeStore.persist_tick_atomic``."""
        if write_commit_marker:
            self._last_committed[envelope.session_id] = envelope.tick

    def get_last_committed_tick(self, session_id: UUID) -> int | None:
        """See ``GameRuntimeStore.get_last_committed_tick``."""
        return self._last_committed.get(session_id)

    def submit_turn(
        self,
        session_id: UUID,
        tick: int,
        org_id: str,
        verb: str,
        *,
        action_type: str | None = None,
        target_id: str | None = None,
        target_community: str | None = None,
        params_json: dict[str, Any] | None = None,
    ) -> int:
        """See ``TurnSink.submit_turn`` — unused (this suite never submits a
        player verb), kept only for structural completeness."""
        return 0


# --------------------------------------------------------------------------- #
# The composition-root harness — mirrors babylon.cli.play's REAL wiring.      #
# --------------------------------------------------------------------------- #


def _driver_factory(campaign: CampaignHandle) -> PacedTickDriver:
    """The ``babylon.tui.app.DriverFactory`` seam.

    Mirrors ``babylon.cli.play._driver_factory`` exactly (that module's own
    docstring explains the cast): :func:`~babylon.game.pacing.
    paced_driver_for_session` needs a full ``GameSession`` (specifically
    ``session.services.defines``), strictly more than ``CampaignHandle``
    structurally promises, so mypy correctly refuses the function directly.
    The cast is sound for the same reason production's is — this harness's
    own ``campaign_loader`` (:func:`_build_harness`) always resolves to a
    real ``GameSession``.
    """
    return paced_driver_for_session(cast(GameSession, campaign))


def _build_harness(vault_root: Path) -> ArchiveApp:
    """Wire a fresh ``ArchiveApp`` against a REAL composed campaign.

    The same ``babylon.game.session``/``babylon.game.pacing`` composition
    idiom ``tests/integration/game/test_session_integration.py`` (and the
    real ``babylon.cli.play`` composition root) use, minus Postgres (see
    :class:`_InMemoryGameStore`). Real engine, real ``PacedTickDriver`` +
    ``EndgameDetector``, real vault baking (``ArchiveTickBaker`` over a
    ``dulwich``-backed ``vault_root``, plus the SAME explicit
    ``bake_briefing`` call ``babylon.cli.play._load_campaign`` makes — the
    per-tick baker never bakes the briefing itself), so ``county/26163``,
    ``economy/USA``, and the Scenario Briefing are all REAL rendered pages,
    never a fixture lookalike. Narrator OFF (``narrator=None``, never
    threaded here) and Wayne's own fixed ``rng_seed=0`` default keep the
    whole session deterministic (T6 ruling).

    :param vault_root: a fresh, empty directory (a test's own ``tmp_path``)
        for this campaign's baked vault.
    :returns: a freshly constructed ``ArchiveApp``, not yet running.
    """
    store = _InMemoryGameStore()
    # EMPTY catalog: "a fresh boot with no campaign chosen yet" — WAYNE_OPENING_ARC's
    # own boot_into_lobby.given.
    catalog = InMemoryCampaignCatalog()
    menu = CampaignMenu(catalog, engine_version="t6-tutorial-pilot", defines_hash="d" * 16)
    materializer = VaultMaterializer(vault_root)
    baker = ArchiveTickBaker(materializer, (_WAYNE_FIPS,))

    def _loader(campaign_id: UUID) -> GameSession:
        session = create_new_campaign(
            store,
            scenario=WayneCountyScenario(),
            session_id=campaign_id,
            tick_commit_observer=baker,
            pages=vault_page_source(vault_root),
            known_subjects=vault_known_subjects(vault_root),
            narrator=None,
        )
        view = project_briefing(
            session.session_id, tick=session.tick, defines=session.services.defines
        )
        materializer.bake_briefing(view, tick=session.tick)
        return session

    return ArchiveApp(campaign_menu=menu, campaign_loader=_loader, driver_factory=_driver_factory)


@asynccontextmanager
async def _live_pilot(vault_root: Path) -> AsyncIterator[Pilot[None]]:
    """Boot a fresh harness and yield its running ``Pilot`` — the one seam
    every test in this module drives through. See :data:`_PINNED_CAMPAIGN_ID`
    for why the lobby's own mint id is pinned for the duration.
    """
    app = _build_harness(vault_root)
    with mock.patch("babylon.tui.campaign_menu.uuid4", return_value=_PINNED_CAMPAIGN_ID):
        async with app.run_test(size=_PILOT_SIZE) as pilot:
            yield pilot


def _archive_app(pilot: Pilot[None]) -> ArchiveApp:
    """``pilot.app`` narrowed back to ``ArchiveApp``.

    ``Pilot[None]`` only types ``.app`` as the generic ``App[None]`` (the
    type parameter is the app's RESULT type, not the app class itself), but
    every app this module's :func:`_live_pilot` ever boots is a concrete
    ``ArchiveApp`` — the same narrowing ``babylon.cli.play._driver_factory``
    documents for its own analogous cast.
    """
    return cast(ArchiveApp, pilot.app)


# --------------------------------------------------------------------------- #
# The step interpreter — closed dispatch over the anchor grammar and the      #
# completion-predicate union (babylon.game.tutorial's module docstring).      #
# --------------------------------------------------------------------------- #


def _binding_key(anchor: str) -> str:
    """The key portion of a ``"binding:<ClassName>:<key>"`` anchor."""
    _, _class_name, key = anchor.split(":", 2)
    return key


async def _perform_anchor(pilot: Pilot[None], anchor: str) -> None:
    """Drive exactly the UI action ``anchor`` names — closed dispatch over
    the anchor grammar (``babylon.game.tutorial``'s module docstring: the
    ``binding:``/``page:``/``palette:`` prefixes).

    :raises ValueError: ``anchor`` names no recognized prefix — never a
        silent no-op for an anchor kind the executor does not understand.
    """
    if anchor.startswith("binding:"):
        await pilot.press(_binding_key(anchor))
        return
    if anchor.startswith("page:"):
        # A pure "read" step: the arc always reaches a page: anchor already
        # navigated there by a prior step's own action — nothing to drive.
        return
    if anchor.startswith("palette:"):
        _, subject = anchor.split(":", 1)
        target = parse_babylon_uri(f"babylon://{subject}")
        # Posts the SAME production message a real palette pick posts
        # (mirrors tests/unit/tui/test_t3_live_reachability.py's own
        # navigation idiom) rather than scripting Textual's built-in
        # CommandPalette widget's own internal keystrokes — this anchor's
        # contract is "the pick landed", not "the fuzzy-search UI works"
        # (a Textual-library concern, not this game's own code).
        _archive_app(pilot).screen.post_message(EntityNavigated(target))
        return
    raise ValueError(f"unrecognized anchor grammar: {anchor!r}")


def _action_owner(app: ArchiveApp, verb: str, *, step_id: str) -> object:
    """Whichever live object (the active screen, else the app) declares
    ``action_<verb>`` — the same bubbling order Textual's own dispatcher
    uses for a ``BINDINGS``-declared action.

    :raises AssertionError: neither the screen nor the app declares it.
    """
    for candidate in (app.screen, app):
        if hasattr(candidate, f"action_{verb}"):
            return candidate
    raise AssertionError(f"{step_id}: no live action_{verb} found on {app.screen!r} or {app!r}")


async def _drive_verb_issued(pilot: Pilot[None], anchor: str, verb: str, *, step_id: str) -> None:
    """Drive ``anchor`` while spying on ``action_<verb>``, then hard-assert
    it was actually dispatched — :class:`~babylon.game.tutorial.VerbIssued`
    proves DISPATCH only (its own docstring), never an outcome, so this is
    a Pilot structural check (tier 2), never a text assertion standing in
    for one.
    """
    app = _archive_app(pilot)
    owner = _action_owner(app, verb, step_id=step_id)
    original = getattr(owner, f"action_{verb}")
    with mock.patch.object(owner, f"action_{verb}", wraps=original) as spy:
        await _perform_anchor(pilot, anchor)
        await app.workers.wait_for_complete()
        await pilot.pause()
    assert spy.called, f"{step_id}: action_{verb} was never dispatched via anchor {anchor!r}"


def _status_text(app: ArchiveApp) -> str:
    """The status line's current plain text."""
    return str(app.query_one("#status", Label).content)


def _dossier_plain_text(app: ArchiveApp) -> str:
    """Every fence-rendered ``Label``'s plain text under ``#dossier``, joined.

    Runs each label back through the real ``Content`` markup parser — the
    same oracle ``tests/unit/tui/test_directives_hardening.py``'s
    ``_plain_text`` and ``test_t3_live_reachability.py``'s ``_dossier_text``
    already use — checking a substring against the raw, unparsed
    ``label.content`` would pass even for a bug where markup silently ate
    part of the text.
    """
    dossier = app.query_one("#dossier", BabylonMarkdown)
    parts: list[str] = []
    for label in dossier.query(Label):
        if label._render_markup:
            parts.append(Content.from_markup(label.content).plain)
        else:
            parts.append(str(label.content))
    return "\n".join(parts)


def _assert_completion(app: ArchiveApp, predicate: object, *, step_id: str) -> None:
    """Hard-assert one completion predicate against the live app — closed
    dispatch over the five-member :data:`~babylon.game.tutorial.
    CompletionPredicate` union (``VerbIssued`` is handled separately, in
    :func:`_drive_verb_issued`, since its verification must wrap the drive
    itself). Semantic text first, structural state second — never a visual
    snapshot (the T6 ruling's assertion tiers).

    :raises AssertionError: the predicate does not hold, OR is a kind
        outside the closed vocabulary — never a silent skip.
    """
    if isinstance(predicate, OnPage):
        text = _dossier_plain_text(app)
        assert "UNKNOWN DIRECTIVE" not in text, (
            f"{step_id}: dossier shows an unknown-directive refusal"
        )
        assert "MALFORMED STATBLOCK BODY" not in text, (
            f"{step_id}: dossier shows a malformed-statblock refusal"
        )
        assert text.strip(), f"{step_id}: dossier rendered no content at all"
        assert app.nav.current == predicate.subject, (
            f"{step_id}: expected nav.current == {predicate.subject!r}, got {app.nav.current!r}"
        )
        return
    if isinstance(predicate, TickAtLeast):
        assert "tick" in _status_text(app).lower(), f"{step_id}: status line never mentions a tick"
        assert app.campaign is not None, f"{step_id}: no live campaign to read a tick from"
        assert app.campaign.tick >= predicate.tick, (
            f"{step_id}: expected tick >= {predicate.tick}, campaign is at {app.campaign.tick}"
        )
        return
    if isinstance(predicate, PausePending):
        assert "paus" in _status_text(app).lower(), (
            f"{step_id}: status line never mentions a pause ('PAUSED'/'autopause')"
        )
        assert app.driver is not None, f"{step_id}: no paced driver to check for a pending pause"
        assert app.driver.awaiting_ack is True, (
            f"{step_id}: expected a pending autopause, found none"
        )
        return
    if isinstance(predicate, EventAcked):
        assert "acknowledged" in _status_text(app).lower(), (
            f"{step_id}: status line never confirms the acknowledgement"
        )
        assert app.driver is not None, f"{step_id}: no paced driver to check acknowledgement on"
        assert app.driver.awaiting_ack is False, f"{step_id}: the autopause is still pending"
        return
    raise AssertionError(f"{step_id}: unrecognized completion predicate kind {predicate!r}")


# --------------------------------------------------------------------------- #
# Step-specific content checks (review fix pass) — see module note above     #
# drive_step for why these are layered ON TOP OF _assert_completion rather   #
# than folded into it or promoted to a new CompletionPredicate kind.         #
# --------------------------------------------------------------------------- #

#: A real ``ClassComposition`` row, always present on Wayne's county
#: statblock by the time ``read_the_county_dossier`` runs (verified against
#: this exact composition's own emitted transcript). Distinguishes a REAL
#: rendered county statblock from any other non-empty page shown at the
#: same subject — unlike ``_WAYNE_FIPS`` alone, this string cannot leak in
#: from a refusal message (``_directive_statblock``'s own "no statblock
#: projection for {arg}"/"MALFORMED STATBLOCK BODY" refusals echo the
#: subject id too, so the FIPS alone is not fully distinctive; a genuine
#: class-composition row only ever comes from an actually-rendered
#: statblock body).
_WAYNE_CLASS_COMPOSITION_ROW: Final = "class_composition.labor_aristocracy"

#: ``wage_balance``'s own statblock row, rendered by
#: ``babylon.tui.directives._directive_statblock`` as
#: ``"wage_balance<padding><value>"`` (the colon from the baked
#: ``key: value`` fence body is stripped at parse time — verified against
#: this exact composition's own emitted transcript, never assumed). The
#: numeric value itself is NOT pinned (unlike ``test_t3_live_
#: reachability.py``'s fixture-backed ``"0.180000"`` literal) because this
#: suite runs the real engine through real ticks — a genuine coefficient
#: retune could shift the float without being a regression this step's own
#: Then cares about; what the Then actually advertises is "renders as a
#: real number", which a numeric-shaped regex proves without over-pinning.
_WAGE_BALANCE_ROW_PATTERN: Final = re.compile(r"wage_balance\s+-?\d+\.\d+")

#: ``labor_aristocracy_verdict``'s own statblock row — same rendering
#: contract as above, value is the literal ``str(bool)`` render
#: (``"True"``/``"False"``), verified against the emitted transcript.
_LABOR_ARISTOCRACY_VERDICT_ROW_PATTERN: Final = re.compile(
    r"labor_aristocracy_verdict\s+(True|False)"
)


def _assert_county_dossier_is_wayne_real(app: ArchiveApp, *, step_id: str) -> None:
    """``read_the_county_dossier``'s own extra Then-check (review fix pass).

    The step's own ``then`` advertises Wayne's REAL material state, "not a
    fixture" — ``OnPage`` alone (nav.current + non-emptiness) cannot tell
    that apart from any other non-empty page shown under the same subject.
    A real class-composition row is the distinctive proof.

    :raises AssertionError: no real class-composition row (or the county's
        own FIPS) appears in the rendered statblock.
    """
    text = _dossier_plain_text(app)
    assert _WAYNE_CLASS_COMPOSITION_ROW in text, (
        f"{step_id}: no real {_WAYNE_CLASS_COMPOSITION_ROW!r} row in the rendered "
        "statblock — cannot distinguish Wayne's own state from an empty/fixture page"
    )
    assert _WAYNE_FIPS in text, f"{step_id}: county/{_WAYNE_FIPS}'s own FIPS never rendered"


def _assert_theorem_verdict_is_real(app: ArchiveApp, *, step_id: str) -> None:
    """``read_the_theorem_verdict``'s own extra Then-check (review fix pass).

    The step's own ``then`` advertises the wage balance and the
    labor-aristocracy verdict rendering "as real numbers read off the SAME
    opposition the engine itself adjudicates" — ``OnPage`` alone cannot
    verify that distinctive content is actually on screen, only that
    *something* non-empty is showing at ``economy/USA``.

    :raises AssertionError: either row is missing, or ``wage_balance``'s
        value is not numeric-shaped.
    """
    text = _dossier_plain_text(app)
    assert _WAGE_BALANCE_ROW_PATTERN.search(text), (
        f"{step_id}: no 'wage_balance <number>' row in the rendered statblock"
    )
    assert _LABOR_ARISTOCRACY_VERDICT_ROW_PATTERN.search(text), (
        f"{step_id}: no 'labor_aristocracy_verdict <bool>' row in the rendered statblock"
    )


#: Closed, named extension keyed by step id — NOT a second predicate
#: vocabulary alongside :func:`_assert_completion` (that function alone
#: owns closed dispatch over :data:`~babylon.game.tutorial.
#: CompletionPredicate`). Every OTHER step id is a deliberate no-op here:
#: the two entries below are exactly the CONTENT-advertising ``OnPage``
#: steps the review identified (their ``then`` names specific rendered
#: numbers/rows) as opposed to the NAVIGATION-only ``OnPage`` steps
#: (``begin_the_operation``, ``palette_to_the_economy_dossier``,
#: ``jump_back_to_wayne``) whose own ``then`` only advertises "the dossier
#: pane shows/returns to/navigates to X" — already fully covered by
#: ``_assert_completion``'s nav.current + non-emptiness check.
_EXTRA_CONTENT_CHECK_BY_STEP_ID: Final[dict[str, Callable[[ArchiveApp], None]]] = {
    "read_the_county_dossier": lambda app: _assert_county_dossier_is_wayne_real(
        app, step_id="read_the_county_dossier"
    ),
    "read_the_theorem_verdict": lambda app: _assert_theorem_verdict_is_real(
        app, step_id="read_the_theorem_verdict"
    ),
}


async def drive_step(pilot: Pilot[None], step: TutorialStep) -> None:
    """The step interpreter's public entry point: drive ``step.when`` via
    its anchor, then hard-assert ``step.then`` via its completion predicate.

    Closed dispatch over the anchor grammar (:func:`_perform_anchor`) and
    the completion-predicate union (:func:`_assert_completion`) — an
    anchor prefix or predicate kind outside either closed vocabulary raises
    loudly, never skips (Constitution III.11). A second, narrow layer
    (:data:`_EXTRA_CONTENT_CHECK_BY_STEP_ID`, review fix pass) asserts the
    distinctive rendered content two CONTENT-advertising steps promise,
    on top of (never instead of) the generic ``OnPage`` check — see that
    dict's own docstring for why only those two step ids need it.
    """
    if isinstance(step.completion, VerbIssued):
        await _drive_verb_issued(pilot, step.anchor, step.completion.verb, step_id=step.id)
        return
    await _perform_anchor(pilot, step.anchor)
    await pilot.app.workers.wait_for_complete()
    await pilot.pause()
    app = _archive_app(pilot)
    _assert_completion(app, step.completion, step_id=step.id)
    extra_check = _EXTRA_CONTENT_CHECK_BY_STEP_ID.get(step.id)
    if extra_check is not None:
        extra_check(app)


async def _load_the_minted_campaign(pilot: Pilot[None]) -> None:
    """Bridging glue the authored arc itself does not script.

    After minting a campaign (``boot_into_lobby``'s own ``when``), the
    lobby's freshly-added row must be highlighted + confirmed with Enter to
    actually load it — the same two-key tail
    ``tests/unit/tui/test_app_pacing_driver.py``'s/``test_t3_live_
    reachability.py``'s own ``_boot_into_campaign_shell`` helpers already
    drive against a PRE-SEEDED row; this arc starts with an EMPTY catalog
    (``boot_into_lobby``'s own ``given``), so minting is the one extra step
    before that same sequence applies. Not itself a scripted Given/When/Then
    beat: ``LobbyScreen._reload()`` already keeps the freshly minted row
    highlighted (index 0, the only row), so this is exactly "select what is
    already highlighted, and confirm."
    """
    pilot.app.screen.query_one("#campaigns", OptionList).focus()
    await pilot.press("enter")
    await pilot.app.workers.wait_for_complete()
    await pilot.pause()


#: Repo loop-bound rule (Power-of-10 #2): the authored arc is fixed at 9
#: steps today and statically bounded at 64 (``TutorialScript``'s own
#: ``_MAX_SCRIPT_STEPS``) — this loop's upper bound is that same constant.
_MAX_REPLAY_STEPS: Final = 64


async def _replay_through(
    pilot: Pilot[None],
    steps: Sequence[TutorialStep],
    *,
    after_step: Callable[[int, TutorialStep], None] | None = None,
) -> None:
    """Drive + hard-assert every step in ``steps``, in order, against ONE
    live Pilot session, bridging the one gap the authored arc does not
    script (see :func:`_load_the_minted_campaign`).

    :param after_step: if given, called with ``(1-based index, step)``
        immediately after that step's own drive+assert (before any
        bridging) — the transcript capturer's own hook.
    """
    assert len(steps) <= _MAX_REPLAY_STEPS
    for index, step in enumerate(steps, start=1):  # loop bound: _MAX_REPLAY_STEPS
        await drive_step(pilot, step)
        if after_step is not None:
            after_step(index, step)
        if step.id == "boot_into_lobby":
            await _load_the_minted_campaign(pilot)


# --------------------------------------------------------------------------- #
# One pytest test per authored step — pytest ids ARE the step sentences.      #
# --------------------------------------------------------------------------- #


class TestEachStepOfTheWayneOpeningArc:
    """One test per authored step (the T6 ruling: "scenario names are
    sentences; the suite is the game-loop's behavioral contract"). Each
    test replays the arc from a fresh boot through this step, inclusive —
    a step's own ``given`` is the state the PRECEDING steps' actions left
    behind (one continuous first session, not independently fixtured
    scenarios), so replaying is how its precondition is actually reached.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "target_index",
        range(len(WAYNE_OPENING_ARC.steps)),
        ids=[step.scenario_name for step in WAYNE_OPENING_ARC.steps],
    )
    async def test_step_resolves_its_own_then(self, tmp_path: Path, target_index: int) -> None:
        steps = WAYNE_OPENING_ARC.steps[: target_index + 1]
        async with _live_pilot(tmp_path / "vault") as pilot:
            await _replay_through(pilot, steps)


class TestWholeOpeningArcInOneSession:
    """The whole-arc proof: every step, in order, in a single session — the
    complete first-session flow ``WAYNE_OPENING_ARC`` advertises, verified
    end to end (redundant with the last parametrized case above by
    construction, kept separately named because it is itself the
    documentation artifact a developer skimming test names would want).
    """

    @pytest.mark.asyncio
    async def test_every_step_resolves_in_order(self, tmp_path: Path) -> None:
        async with _live_pilot(tmp_path / "vault") as pilot:
            await _replay_through(pilot, WAYNE_OPENING_ARC.steps)


class TestRunUntilAutopauseHonestGap:
    """Pins the module docstring's HONEST GAP finding as a durable
    regression: Wayne's own material state is critical-tier from tick 1
    onward, so ``run_until_autopause``'s ``r`` press is a no-op refusal
    (the driver already paused from ``advance_a_tick``'s own tick), never a
    genuine multi-tick auto-run. If a future scenario/coefficient change
    ever gives Wayne even one genuinely quiet tick, THIS test goes red
    first — the signal that the honest-gap comments above (and the
    module docstring) need updating, not silently stale.
    """

    @pytest.mark.asyncio
    async def test_r_is_a_no_op_refusal_because_advance_a_tick_already_paused(
        self, tmp_path: Path
    ) -> None:
        run_until_autopause = next(
            s for s in WAYNE_OPENING_ARC.steps if s.id == "run_until_autopause"
        )
        prior = WAYNE_OPENING_ARC.steps[: WAYNE_OPENING_ARC.steps.index(run_until_autopause)]

        async with _live_pilot(tmp_path / "vault") as pilot:
            await _replay_through(pilot, prior)
            # Given: advance_a_tick already left the driver awaiting ack.
            app = _archive_app(pilot)
            assert app.driver is not None
            assert app.driver.awaiting_ack is True

            await drive_step(pilot, run_until_autopause)

            # Then: still awaiting ack (PausePending holds, as asserted inside
            # drive_step) — AND the status line shows the REFUSAL phrasing
            # ("... press 'a' to acknowledge"), never the success phrasing
            # ("ran to tick N ...") a genuine auto-run would report.
            status = _status_text(app)
            assert "press 'a' to acknowledge" in status
            assert "ran to tick" not in status


# --------------------------------------------------------------------------- #
# The transcript artifact — every screen, at every step, as plain text.       #
# --------------------------------------------------------------------------- #

#: GENERATED, not committed: mirrors the EXISTING ``reports/sim-runs/``
#: convention (``.gitignore``: "Ingest audit reports + per-run sim artifacts
#: (regenerable byproducts)") rather than ``tests/baselines/**``'s
#: ceremony-gated goldens. This transcript is a build BYPRODUCT of a run,
#: regenerated fresh every time the suite executes — never hand-edited,
#: never diffed against a committed reference requiring a
#: ``Baselines: blessed(...)`` ceremony (§6.5). The determinism test below
#: is what makes it trustworthy, not a committed golden copy.
_ARTIFACT_PATH: Final = (
    Path(__file__).resolve().parents[3] / "reports" / "sim-runs" / "tutorial-transcript.txt"
)


def _export_screen_text(app: ArchiveApp) -> str:
    """A literal plain-text capture of the CURRENTLY rendered screen.

    Mirrors ``textual.app.App.export_screenshot``'s own internals exactly
    (the same ``Console``/``screen._compositor.render_update`` setup that
    method uses to build its SVG), swapping Rich's ``Console.export_svg``
    for ``Console.export_text`` — the T6 ruling's own words: "the terminal
    grid IS a text buffer." ``styles=False`` strips every color/style code,
    so this capture is untouched by the ``NO_COLOR`` grayscale-vs-truecolor
    lane split that otherwise plagues the SVG snapshot goldens
    (``tests/unit/tui/conftest.py``) — one plain, assertable text buffer
    either way.

    HONEST GAP, surfaced by this literal capture (not by this unit's own
    behavioral assertions, which read ``#status``'s widget content directly
    and are unaffected): ``ArchiveApp``'s ``#status`` ``Label`` and its
    ``Footer`` are BOTH docked ``bottom`` at the same row, and the wider
    ``Footer`` paints over ``#status`` in every capture this module took —
    the string ``"status:"`` never appears anywhere in the transcript this
    module writes, at ANY step, in the actual rendered screen, even though
    the widget's own content is always correct (proven by every passing
    ``TickAtLeast``/``PausePending``/``EventAcked`` assertion above, and by
    grepping the ALREADY-COMMITTED ``test_archive_app_renders_the_sample_
    dossier`` SVG golden, which shows the identical collision — this is
    PRE-EXISTING production layout behavior, not something this unit's
    harness introduces). Filed here as a finding for a future ``babylon.tui.
    app`` CSS fix (give ``#status`` its own reserved row above the Footer);
    not fixed by this unit — a UI layout change is out of this executor
    unit's scope and would need its own review against the existing SVG
    snapshot goldens (a controller-owned re-bake decision per this repo's
    own golden-drift rule).
    """
    assert app._driver is not None, "app must be running to export its screen"
    width, height = app.size
    console = Console(
        width=width,
        height=height,
        file=io.StringIO(),
        force_terminal=True,
        color_system="truecolor",
        record=True,
        legacy_windows=False,
        safe_box=False,
    )
    screen_render = app.screen._compositor.render_update(
        full=True, screen_stack=app._background_screens, simplify=False
    )
    console.print(screen_render)
    return console.export_text(styles=False)


async def _capture_whole_arc_transcript(vault_root: Path) -> str:
    """Boot a fresh harness, replay the whole arc, and return the
    transcript — every screen, at every step, as plain text, headed by
    that step's own ``scenario_name`` sentence (the developer-education
    document the T6 ruling promises).
    """
    blocks: list[str] = []
    total = len(WAYNE_OPENING_ARC.steps)

    async with _live_pilot(vault_root) as pilot:

        def _record(index: int, step: TutorialStep) -> None:
            blocks.append(f"=== step {index}/{total}: {step.id} ===")
            blocks.append(step.scenario_name)
            blocks.append("")
            blocks.append(_export_screen_text(_archive_app(pilot)))
            blocks.append("")

        await _replay_through(pilot, WAYNE_OPENING_ARC.steps, after_step=_record)

    return "\n".join(blocks)


class TestTranscriptArtifact:
    """The T6 ruling's playthrough-transcript artifact."""

    @pytest.mark.asyncio
    async def test_two_independent_runs_produce_a_byte_identical_transcript(
        self, tmp_path: Path
    ) -> None:
        """Deterministic under narrator-OFF + Wayne's fixed seed: two
        independently-booted runs of the whole arc must be byte-identical —
        transcript drift IS behavior drift (module docstring)."""
        transcript_a = await _capture_whole_arc_transcript(tmp_path / "vault-a")
        transcript_b = await _capture_whole_arc_transcript(tmp_path / "vault-b")
        assert transcript_a, "the transcript must not be empty"
        assert transcript_a == transcript_b

    @pytest.mark.asyncio
    async def test_transcript_names_every_step_and_is_written_to_the_artifact_path(
        self, tmp_path: Path
    ) -> None:
        transcript = await _capture_whole_arc_transcript(tmp_path / "vault")
        for step in WAYNE_OPENING_ARC.steps:  # loop bound: len(steps) <= _MAX_REPLAY_STEPS
            assert step.id in transcript
            assert step.scenario_name in transcript

        _ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
        _ARTIFACT_PATH.write_text(transcript)
        assert _ARTIFACT_PATH.read_text() == transcript
