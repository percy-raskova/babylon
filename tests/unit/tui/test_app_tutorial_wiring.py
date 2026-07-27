"""``ArchiveApp``'s tutorial-overlay wiring seam (Program v1.0.0 T6, Unit U4).

Complements ``tests/unit/tui/test_tutorial_overlay.py`` (which drives the
BARE :class:`~babylon.tui.tutorial_overlay.TutorialOverlay` widget with no
``ArchiveApp`` at all): this file exercises the composition-root seam itself
— :class:`~babylon.tui.app.ArchiveApp`'s ``tutorial_steps``/
``tutorial_progress_factory`` constructor params — with fake
``CampaignHandle``/``PacedDriverHandle`` doubles, following the exact
``TestSeams``/lobby-flow idiom ``tests/unit/tui/test_app_pacing_driver.py``
already established for :class:`~babylon.tui.app.PacedDriverHandle`.

Per this unit's own mandate: "demo path and resumed campaigns never show
it" — the demo (no ``campaign_menu``) boot path never reaches a campaign at
all, so no tutorial wiring can fire; a REAL ``babylon play`` boot's own
new-vs-resumed gating lives in ``babylon.cli.play``'s
``_tutorial_progress_factory`` (tested separately in
``tests/unit/cli/test_play.py``) — here, that gating is exercised at the
``ArchiveApp`` seam by a factory double that itself returns ``None``
(standing in for "the composition root decided this campaign is resumed").
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

import pytest
from textual.widgets import ContentSwitcher, Label, OptionList

from babylon.projection.endgame import EndgameStatus
from babylon.projection.verbs.view_models import VerbPlateView, VerbPreview, VerbRow
from babylon.projection.view_models import EconomyView, ProjectionRecord
from babylon.tui.app import ArchiveApp, CampaignHandle, PacedDriverHandle
from babylon.tui.campaign_menu import CampaignMenu, InMemoryCampaign, InMemoryCampaignCatalog
from babylon.tui.tutorial_overlay import TutorialOverlay, TutorialProgress

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class _FakeStep:
    scenario_name: str
    overlay_text: str


_STEPS: tuple[_FakeStep, ...] = (
    _FakeStep(scenario_name="a lone step.", overlay_text="GIVEN/WHEN/THEN"),
)


class _FakeCampaign:
    """A minimal ``CampaignHandle`` double — mirrors ``test_app_lobby_flow.
    py``'s own fixture, with a caller-set ``tick`` (this campaign's own
    stand-in for "freshly minted" vs. "already progressed")."""

    def __init__(self, session_id: UUID, pages: dict[str, str], *, tick: int = 0) -> None:
        self.session_id = session_id
        self.tick = tick
        self._pages = pages

    def read_page(self, subject: str) -> str | None:
        return self._pages.get(subject)

    def known_subjects(self) -> frozenset[str]:
        return frozenset(self._pages)

    def dashboard_view(self) -> EconomyView | None:
        """No live projection wired for this double — honest ``None``
        (Program 24 P2's ``CampaignHandle.dashboard_view`` seam)."""
        return None

    def endgame_status(self) -> EndgameStatus | None:
        """No live endgame-progress projection wired for this double — honest ``None``
        (Program 24 P4's ``CampaignHandle.endgame_status`` seam)."""
        return None

    def verb_plate_view(self) -> VerbPlateView | None:
        """No live verb plate wired for this double — honest ``None``
        (Program 24 P5's ``CampaignHandle.verb_plate_view`` seam), unrelated
        to this unit's own concern."""
        return None

    def subject_view(self, subject_id: str) -> ProjectionRecord | None:
        """No live per-subject projection wired for this double — honest
        ``None`` (unit "live-subject-view", shell-interconnect's own
        ``CampaignHandle.subject_view`` seam), unrelated to this unit's own
        concern."""
        return None

    def issue_verb(self, action_id: str) -> int:  # pragma: no cover - unused by these tests
        raise AssertionError("issue_verb should not be called by these wiring tests")

    def advance_tick(self) -> object:  # pragma: no cover - unused by these tests
        raise AssertionError("advance_tick should not be called by these wiring tests")


class _VerbIssuingCampaign(_FakeCampaign):
    """Extends ``_FakeCampaign`` with a real, eligible ``aid`` verb-plate row
    and a working ``issue_verb`` — for ``TestWasVerbIssuedWiring`` only
    (every other test in this file keeps ``_FakeCampaign``'s own
    ``issue_verb``, which raises if ever called, unaffected)."""

    def __init__(self, session_id: UUID, pages: dict[str, str], *, tick: int = 0) -> None:
        super().__init__(session_id, pages, tick=tick)
        self.issued: list[str] = []

    def verb_plate_view(self) -> VerbPlateView | None:
        preview = VerbPreview(
            estimated_consciousness_delta=0.0,
            estimated_heat_delta=0.0,
            action_point_cost=1.0,
            success_probability=1.0,
            affected_territory_ids=(),
            warnings=(),
        )
        row = VerbRow(
            verb="aid",
            eligible=True,
            reason=None,
            remedy=None,
            can_afford=True,
            afford_note=None,
            preview=preview,
            candidate_target_ids=(),
        )
        return VerbPlateView(org_id="rev_workers", tick=self.tick, verbs=(row,))

    def issue_verb(
        self,
        action_id: str,
        *,
        target_id: str | None = None,
        target_community: str | None = None,
    ) -> int:
        self.issued.append(action_id)
        return 1


class _FakeLoader:
    def __init__(self, campaign: _FakeCampaign) -> None:
        self._campaign = campaign

    def __call__(self, campaign_id: UUID) -> _FakeCampaign:
        return self._campaign


def _seeded_menu() -> tuple[CampaignMenu, UUID]:
    campaign_id = UUID(int=1)
    catalog = InMemoryCampaignCatalog(
        seed=(
            InMemoryCampaign(
                campaign_id=campaign_id,
                slug="campaign-one",
                engine_version="0.1.0",
                defines_hash="d" * 16,
            ),
        )
    )
    return CampaignMenu(catalog, engine_version="0.1.0", defines_hash="d" * 16), campaign_id


def _campaign_for(campaign_id: UUID, *, tick: int = 0) -> _FakeCampaign:
    briefing_subject = f"briefing/{campaign_id}"
    return _FakeCampaign(
        campaign_id, {briefing_subject: "# OP\n", "county/26163": "# Wayne\n"}, tick=tick
    )


def _verb_issuing_campaign_for(campaign_id: UUID, *, tick: int = 0) -> _VerbIssuingCampaign:
    briefing_subject = f"briefing/{campaign_id}"
    return _VerbIssuingCampaign(
        campaign_id, {briefing_subject: "# OP\n", "county/26163": "# Wayne\n"}, tick=tick
    )


async def _boot_into_campaign_shell(pilot: object, app: ArchiveApp) -> None:
    """Walk the lobby -> briefing -> shell flow (mirrors ``test_app_pacing_
    driver.py``'s own repeated sequence)."""
    await pilot.pause()  # type: ignore[attr-defined]
    app.screen.query_one("#campaigns", OptionList).focus()
    await pilot.press("enter")  # type: ignore[attr-defined]
    await pilot.pause()  # type: ignore[attr-defined]
    await pilot.press("enter")  # type: ignore[attr-defined]
    await pilot.pause()  # type: ignore[attr-defined]


class TestConstructorValidation:
    def test_tutorial_progress_factory_without_tutorial_steps_raises(self) -> None:
        with pytest.raises(ValueError, match="tutorial_steps"):
            ArchiveApp(tutorial_progress_factory=lambda _c, _d, _s, _p, _i, _v: None)

    def test_tutorial_steps_alone_is_a_valid_inert_configuration(self) -> None:
        """The reverse pairing is NOT required to raise (unlike
        ``campaign_menu``/``campaign_loader``): steps with no factory can
        never activate anything, which is harmless, not a misconfiguration."""
        app = ArchiveApp(tutorial_steps=_STEPS)
        assert app.driver is None  # constructs cleanly, nothing crashes


class TestDemoPathNeverShowsTutorial:
    @pytest.mark.asyncio
    async def test_the_bare_demo_app_never_mounts_an_overlay(self) -> None:
        """``ArchiveApp()`` — no ``campaign_menu`` at all, the pre-existing
        sample-page demo boot — never reaches ``_on_briefing_dismissed``,
        so no tutorial wiring can ever fire."""
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert len(app.query(TutorialOverlay)) == 0

    @pytest.mark.asyncio
    async def test_a_real_campaign_boot_with_no_factory_wired_never_shows_it(self) -> None:
        """Every pre-Unit-U4 caller/test: a real lobby->briefing->shell boot
        with NEITHER ``tutorial_steps`` nor ``tutorial_progress_factory``
        given — unaffected by this unit."""
        menu, campaign_id = _seeded_menu()
        app = ArchiveApp(
            campaign_menu=menu, campaign_loader=_FakeLoader(_campaign_for(campaign_id))
        )
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            assert len(app.query(TutorialOverlay)) == 0


class TestCompositionRootGating:
    """The T6 ruling's "resumed campaigns default OFF" — exercised here at
    the ``ArchiveApp`` seam via a factory double (the real new-vs-resumed
    DECISION is ``babylon.cli.play``'s own job, tested in
    ``tests/unit/cli/test_play.py``)."""

    @pytest.mark.asyncio
    async def test_a_factory_returning_none_never_mounts_the_overlay(self) -> None:
        menu, campaign_id = _seeded_menu()
        app = ArchiveApp(
            campaign_menu=menu,
            campaign_loader=_FakeLoader(_campaign_for(campaign_id, tick=5)),
            tutorial_steps=_STEPS,
            tutorial_progress_factory=lambda _c, _d, _s, _p, _i, _v: None,
        )
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            assert len(app.query(TutorialOverlay)) == 0
            assert app._tutorial_progress is None  # noqa: SLF001 - white-box wiring check

    @pytest.mark.asyncio
    async def test_a_factory_returning_a_seam_mounts_the_overlay(self) -> None:
        menu, campaign_id = _seeded_menu()

        @dataclass
        class _StubProgress:
            def is_step_complete(self, step_index: int) -> bool:
                return False

        app = ArchiveApp(
            campaign_menu=menu,
            campaign_loader=_FakeLoader(_campaign_for(campaign_id, tick=0)),
            tutorial_steps=_STEPS,
            tutorial_progress_factory=lambda _c, _d, _s, _p, _i, _v: _StubProgress(),
        )
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            assert len(app.query(TutorialOverlay)) == 1
            overlay = app.query_one(TutorialOverlay)
            heading = str(overlay.query_one("#tutorial-heading", Label).content)
            assert _STEPS[0].scenario_name in heading

    @pytest.mark.asyncio
    async def test_the_factory_is_called_with_the_booted_campaign_and_driver(self) -> None:
        menu, campaign_id = _seeded_menu()
        campaign = _campaign_for(campaign_id)
        seen: list[tuple[CampaignHandle, PacedDriverHandle | None]] = []

        def _factory(
            booted: CampaignHandle,
            driver: PacedDriverHandle | None,
            _current_subject: Callable[[], str | None],
            _current_pane: Callable[[], str | None],
            _is_pinned: Callable[[str], bool],
            _was_verb_issued: Callable[[str], bool],
        ) -> TutorialProgress | None:
            seen.append((booted, driver))
            return None

        app = ArchiveApp(
            campaign_menu=menu,
            campaign_loader=_FakeLoader(campaign),
            tutorial_steps=_STEPS,
            tutorial_progress_factory=_factory,
        )
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            assert seen == [(campaign, None)]


class TestExistingSnapshotBootUnaffected:
    """The default-constructed module-level ``app`` (``babylon.tui.app.app``,
    which ``tests/unit/tui/test_snapshot.py``'s golden renders) never sets
    any tutorial param — this pins that the golden's own boot path stays
    byte-for-byte untouched by this unit (no overlay, no CSS collision)."""

    def test_default_constructed_app_has_no_tutorial_wiring(self) -> None:
        from babylon.tui.app import app as sample_app

        assert sample_app._tutorial_steps is None  # noqa: SLF001
        assert sample_app._tutorial_progress_factory is None  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_default_constructed_app_mounts_no_overlay_when_run(self) -> None:
        from babylon.tui.app import ArchiveApp

        # A FRESH instance (not the shared module-level ``app``, which other
        # test modules may already have driven) constructed exactly the same
        # way — the demo boot path never even reaches ``_on_briefing_
        # dismissed``, so no overlay can mount.
        app = ArchiveApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert len(app.query(TutorialOverlay)) == 0


class TestFocusModelDoesNotFightTheOverlaysGrab:
    """Known risk (unit "focus-model", shell-interconnect): the overlay's own
    ``on_mount`` deliberately grabs focus for itself so its ``escape``
    binding stays reachable (:mod:`~babylon.tui.tutorial_overlay`'s own
    module docstring). ``ArchiveApp._focus_current_surface`` — the new
    focus-model machinery ``action_switch_view``/``_navigate`` now call on
    every pane switch/navigation — must never fight that grab back off
    while the overlay is still mounted and undismissed."""

    @pytest.mark.asyncio
    async def test_switching_panes_while_the_overlay_is_up_leaves_it_focused(self) -> None:
        menu, campaign_id = _seeded_menu()

        @dataclass
        class _StubProgress:
            def is_step_complete(self, step_index: int) -> bool:
                return False  # never finishes, so the overlay never dismisses itself

        app = ArchiveApp(
            campaign_menu=menu,
            campaign_loader=_FakeLoader(_campaign_for(campaign_id)),
            tutorial_steps=_STEPS,
            tutorial_progress_factory=lambda _c, _d, _s, _p, _i, _v: _StubProgress(),
        )
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            overlay = app.query_one(TutorialOverlay)
            assert app.focused is overlay  # the overlay's own on_mount grab

            await pilot.press("2")  # a deliberate pane switch — action_switch_view
            await pilot.pause()
            assert app.query_one("#main", ContentSwitcher).current == "map"
            assert app.focused is overlay  # NOT stolen onto the newly-current pane

    @pytest.mark.asyncio
    async def test_once_dismissed_a_pane_switch_focuses_the_pane_normally(self) -> None:
        """The guard is scoped to "overlay mounted and undismissed" — once
        the player dismisses it (``escape``), the focus model resumes its
        normal behavior."""
        menu, campaign_id = _seeded_menu()

        @dataclass
        class _StubProgress:
            def is_step_complete(self, step_index: int) -> bool:
                return False

        app = ArchiveApp(
            campaign_menu=menu,
            campaign_loader=_FakeLoader(_campaign_for(campaign_id)),
            tutorial_steps=_STEPS,
            tutorial_progress_factory=lambda _c, _d, _s, _p, _i, _v: _StubProgress(),
        )
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            overlay = app.query_one(TutorialOverlay)
            assert app.focused is overlay

            await pilot.press("escape")  # TutorialOverlay.action_dismiss_tutorial
            await pilot.pause()
            assert len(app.query(TutorialOverlay)) == 0

            await pilot.press("2")
            await pilot.pause()
            assert app.focused is app.query_one("#map")


class TestWasVerbIssuedWiring:
    """Defect fix (M3 contract §0, the ``VerbIssued`` live-crash fix, shared
    by both clients): ``ArchiveApp`` records dispatch-proof verb names into
    a ``set[str]`` fed to the tutorial_progress_factory's NEW 6th
    ``was_verb_issued`` argument — ``action_issue_verb`` records the verb
    string, ``action_peek_wikilink`` records ``"peek_wikilink"`` —
    dispatch-proof, outcome-independent, matching ``VerbIssued``'s own
    documented meaning (mirrors ``RustClientHost``'s own host-verb-log
    recording, M3 seam contract §1)."""

    @pytest.mark.asyncio
    async def test_issuing_a_verb_records_it_for_was_verb_issued(self) -> None:
        menu, campaign_id = _seeded_menu()
        campaign = _verb_issuing_campaign_for(campaign_id)
        seen: list[Callable[[str], bool]] = []

        def _factory(
            _c: CampaignHandle,
            _d: PacedDriverHandle | None,
            _s: Callable[[], str | None],
            _p: Callable[[], str | None],
            _i: Callable[[str], bool],
            was_verb_issued: Callable[[str], bool],
        ) -> TutorialProgress | None:
            seen.append(was_verb_issued)
            return None

        app = ArchiveApp(
            campaign_menu=menu,
            campaign_loader=_FakeLoader(campaign),
            tutorial_steps=_STEPS,
            tutorial_progress_factory=_factory,
        )
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            was_verb_issued = seen[0]
            assert was_verb_issued("aid") is False

            await pilot.press("f6")  # F6 == aid (_VERB_ACTION_KEYS zip)
            await pilot.pause()

            assert was_verb_issued("aid") is True
            assert campaign.issued == ["aid"]

    @pytest.mark.asyncio
    async def test_peeking_a_wikilink_records_peek_wikilink(self) -> None:
        menu, campaign_id = _seeded_menu()
        campaign = _campaign_for(campaign_id)
        seen: list[Callable[[str], bool]] = []

        def _factory(
            _c: CampaignHandle,
            _d: PacedDriverHandle | None,
            _s: Callable[[], str | None],
            _p: Callable[[], str | None],
            _i: Callable[[str], bool],
            was_verb_issued: Callable[[str], bool],
        ) -> TutorialProgress | None:
            seen.append(was_verb_issued)
            return None

        app = ArchiveApp(
            campaign_menu=menu,
            campaign_loader=_FakeLoader(campaign),
            tutorial_steps=_STEPS,
            tutorial_progress_factory=_factory,
        )
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot, app)
            was_verb_issued = seen[0]
            assert was_verb_issued("peek_wikilink") is False

            # The Wiki pane is current by default right after boot
            # (ContentSwitcher's own "wiki" initial) — this dispatch's own
            # precondition, so no pane switch is needed first.
            await pilot.press("K")  # ArchiveApp.action_peek_wikilink
            await pilot.pause()

            assert was_verb_issued("peek_wikilink") is True
