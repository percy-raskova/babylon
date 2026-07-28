"""P26 U6 phase 2 — end-to-end reachability proof for ``trade/*`` pages in
the live Textual shell (contract: ``specs/103-trade-surfaces/
u6-archive-trade-surfaces-contracts.md`` Contract 3).

Mirrors :mod:`tests.unit.tui.test_t3_live_reachability`'s three
requirements for the ``economy``/``field_state`` singletons, adapted to
trade's LIVE-not-baked posture (Contract 2's vault-baking deferral still
stands in phase 2 — see :mod:`babylon.tui.trade_dossier`'s own module
docstring): a live campaign's ``known_subjects()``/``read_page()`` are what
:meth:`~babylon.game.session.GameSession` actually implements
(:mod:`tests.unit.game.test_session_trade` pins that seam directly), so this
module's own ``_FakeCampaign`` mirrors T3's — precomputed pages, built via
the REAL :func:`~babylon.tui.trade_dossier.render_trade_page` over REAL
:class:`~babylon.projection.view_models.TradeBlocView` instances — rather
than re-driving a full engine tick, exactly as T3's double built its pages
via the real ``render_economy``/``render_field_state``.

1. the command palette's ``EntityNavigatorProvider`` surfaces
   ``trade/overview``/``trade/canada`` once a live campaign whose
   ``known_subjects()`` carries them is chosen;
2. navigating to each renders through ``BabylonFence`` with no "UNKNOWN
   DIRECTIVE" refusal and no "MALFORMED STATBLOCK BODY" refusal — the real
   Φ numbers show up in the rendered widget tree;
3. a wikilink to ``trade/overview`` written into another page (the
   campaign's home dossier) classifies as a known wikilink span, not a
   redlink;
4. a campaign with NO trade wiring (``known_subjects()``/``read_page()``
   carry no ``trade/*`` id) renders the client's existing "ABSENT" page for
   ``trade/overview`` — honest absence, never a fabricated dossier.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from textual.content import Content
from textual.pilot import Pilot
from textual.widgets import Label, OptionList

from babylon.projection.endgame import EndgameStatus
from babylon.projection.trade import project_trade_bloc, project_trade_overview
from babylon.projection.verbs.view_models import VerbPlateView
from babylon.projection.view_models import EconomyView, ProjectionRecord
from babylon.tui.app import ArchiveApp, BabylonMarkdown, TickOutcome
from babylon.tui.campaign_menu import CampaignMenu, InMemoryCampaign, InMemoryCampaignCatalog
from babylon.tui.palette import EntityNavigated, EntityNavigatorProvider
from babylon.tui.router import parse_babylon_uri
from babylon.tui.trade_dossier import render_trade_page
from babylon.tui.wikilinks import REDLINK_COLOR, WIKILINK_COLOR, BabylonParagraph

pytestmark = pytest.mark.unit

_VERIFIED_TICK = 7
_HOME_SUBJECT = "county/26163"
_OVERVIEW_SUBJECT = "trade/overview"
_CANADA_SUBJECT = "trade/canada"

_PHI = {"canada": 100_000_000.0, "china": 300_000_000.0}
_EXPOSURE = {"canada": {"26163": 1.0}}

_HOME_PAGE = f"""\
# {_HOME_SUBJECT} — Wayne

Imperial rent flows in from [[{_OVERVIEW_SUBJECT}]].
"""
"""The campaign's home dossier — a hand-written link source, NOT one of the
trade pages under test (mirrors ``test_t3_live_reachability``'s own
``_HOME_PAGE``)."""


def _overview_page() -> str:
    view = project_trade_overview(
        external_nodes_phi=_PHI,
        county_exposure_by_external=_EXPOSURE,
        weeks_per_year=52,
        last_flows={"canada": 10.0},
        tick=_VERIFIED_TICK,
    )
    return render_trade_page(view)


def _canada_page() -> str:
    view = project_trade_bloc(
        "canada",
        external_nodes_phi=_PHI,
        county_exposure_by_external=_EXPOSURE,
        weeks_per_year=52,
        last_flows={"canada": 10.0},
        tick=_VERIFIED_TICK,
    )
    assert view is not None
    return render_trade_page(view)


class _FakeCampaign:
    """A minimal ``CampaignHandle`` double whose vault already carries the
    home dossier and both trade pages — no engine, no Postgres (matches
    ``test_t3_live_reachability.py``'s ``_FakeCampaign`` shape)."""

    def __init__(self, session_id: UUID, pages: dict[str, str]) -> None:
        self.session_id = session_id
        self.tick = 0
        self._pages = pages

    def read_page(self, subject: str) -> str | None:
        return self._pages.get(subject)

    def known_subjects(self) -> frozenset[str]:
        return frozenset(self._pages)

    def dashboard_view(self) -> EconomyView | None:
        return None

    def endgame_status(self) -> EndgameStatus | None:
        return None

    def verb_plate_view(self) -> VerbPlateView | None:
        return None

    def subject_view(self, subject_id: str) -> ProjectionRecord | None:
        """Unused by this unit's own requirements (peek/watchlist live-view
        reachability is :mod:`tests.unit.tui.test_peek`'s
        ``TestTradeBlocViewRealKind`` concern) — honest ``None``."""
        return None

    def issue_verb(self, action_id: str) -> int:  # pragma: no cover - unused by this unit
        raise AssertionError("issue_verb should not be called by this reachability unit")

    def advance_tick(self) -> TickOutcome:  # pragma: no cover - unused by this unit
        raise NotImplementedError("this unit never advances the tick")


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
                slug="campaign-trade",
                engine_version="0.1.0",
                defines_hash="d" * 16,
            ),
        )
    )
    return CampaignMenu(catalog, engine_version="0.1.0", defines_hash="d" * 16), campaign_id


def _live_campaign_app(*, pages: dict[str, str]) -> tuple[ArchiveApp, UUID]:
    menu, campaign_id = _seeded_menu()
    briefing_subject = f"briefing/{campaign_id}"
    campaign = _FakeCampaign(campaign_id, {briefing_subject: "# OPERATION TRADE\n", **pages})
    loader = _FakeLoader(campaign)
    return ArchiveApp(campaign_menu=menu, campaign_loader=loader), campaign_id


def _wired_campaign_app() -> tuple[ArchiveApp, UUID]:
    return _live_campaign_app(
        pages={
            _HOME_SUBJECT: _HOME_PAGE,
            _OVERVIEW_SUBJECT: _overview_page(),
            _CANADA_SUBJECT: _canada_page(),
        }
    )


def _unwired_campaign_app() -> tuple[ArchiveApp, UUID]:
    """A campaign whose vault carries no trade pages at all — the
    ``trade=None`` posture (contract: honest absence, never a fabricated
    dossier)."""
    return _live_campaign_app(pages={_HOME_SUBJECT: _HOME_PAGE})


async def _boot_into_campaign_shell(pilot: Pilot[None]) -> None:
    await pilot.pause()
    pilot.app.screen.query_one("#campaigns", OptionList).focus()
    await pilot.press("enter")  # choose the seeded campaign
    await pilot.pause()
    await pilot.press("enter")  # "Begin Operation" on the briefing
    await pilot.pause()


def _dossier_text(app: ArchiveApp) -> str:
    dossier = app.query_one("#dossier", BabylonMarkdown)
    parts: list[str] = []
    for label in dossier.query(Label):
        if label._render_markup:
            parts.append(Content.from_markup(label.content).plain)
        else:
            parts.append(str(label.content))
    return "\n".join(parts)


class TestCommandPaletteSurfacesTradePages:
    """Requirement 1: the palette offers both trade subjects once the live
    campaign that wires them is chosen."""

    @pytest.mark.asyncio
    async def test_discover_lists_both_trade_pages(self) -> None:
        app, _campaign_id = _wired_campaign_app()
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            provider = EntityNavigatorProvider(app.screen)
            hits = [hit async for hit in provider.discover()]
            texts = {hit.text for hit in hits}
            assert _OVERVIEW_SUBJECT in texts
            assert _CANADA_SUBJECT in texts

    @pytest.mark.asyncio
    async def test_search_finds_trade_overview(self) -> None:
        app, _campaign_id = _wired_campaign_app()
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            provider = EntityNavigatorProvider(app.screen)
            hits = [hit async for hit in provider.search("trade")]
            assert any(hit.text == _OVERVIEW_SUBJECT for hit in hits)
            assert any(hit.text == _CANADA_SUBJECT for hit in hits)


class TestTradePagesRenderCleanly:
    """Requirement 2: navigating to each trade page renders through
    ``BabylonFence`` with no loud-refusal directive and the real
    projector-produced Φ numbers visible in the mounted widget tree."""

    @pytest.mark.asyncio
    async def test_overview_renders_its_real_numbers_with_no_refusal(self) -> None:
        app, _campaign_id = _wired_campaign_app()
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            app.post_message(EntityNavigated(parse_babylon_uri(f"babylon://{_OVERVIEW_SUBJECT}")))
            await pilot.pause()

            assert app.nav.current == _OVERVIEW_SUBJECT
            text = _dossier_text(app)
            assert "UNKNOWN DIRECTIVE" not in text
            assert "MALFORMED STATBLOCK BODY" not in text
            assert "phi_year_inflow" in text
            assert "400000000.000000" in text

    @pytest.mark.asyncio
    async def test_canada_bloc_renders_its_real_numbers_with_no_refusal(self) -> None:
        app, _campaign_id = _wired_campaign_app()
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            app.post_message(EntityNavigated(parse_babylon_uri(f"babylon://{_CANADA_SUBJECT}")))
            await pilot.pause()

            assert app.nav.current == _CANADA_SUBJECT
            text = _dossier_text(app)
            assert "UNKNOWN DIRECTIVE" not in text
            assert "MALFORMED STATBLOCK BODY" not in text
            assert "phi_year_inflow" in text
            assert "100000000.000000" in text
            # The absent-in-phase-1/2 fields render as named absences, not a refusal.
            assert "ABSENT" in text
            assert "erdi_ratio" in text


class TestWikilinkToTradeOverviewClassifiesAsKnown:
    """Requirement 3: a wikilink to ``trade/overview`` written into another
    page classifies as known — a gold wikilink span, never a crimson
    redlink."""

    @pytest.mark.asyncio
    async def test_home_page_wikilink_to_trade_overview_is_known(self) -> None:
        app, _campaign_id = _wired_campaign_app()
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            assert app.nav.current == _HOME_SUBJECT
            dossier = app.query_one("#dossier", BabylonMarkdown)
            paragraph = next(
                p for p in dossier.query(BabylonParagraph) if _OVERVIEW_SUBJECT in p.content.plain
            )
            span = next(
                s
                for s in paragraph.content.spans
                if s.style.meta.get("@click") == f"link('babylon://{_OVERVIEW_SUBJECT}')"
            )
            assert span.style.foreground == WIKILINK_COLOR
            assert span.style.foreground != REDLINK_COLOR


class TestUnwiredCampaignRendersHonestAbsence:
    """Requirement 4: a campaign with no trade wiring shows the client's
    EXISTING absence page for ``trade/overview`` — never a fabricated
    dossier (Constitution III.11)."""

    @pytest.mark.asyncio
    async def test_trade_overview_is_absent_not_fabricated(self) -> None:
        app, _campaign_id = _unwired_campaign_app()
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            app.post_message(EntityNavigated(parse_babylon_uri(f"babylon://{_OVERVIEW_SUBJECT}")))
            await pilot.pause()

            assert app.nav.current == _OVERVIEW_SUBJECT
            # The client's EXISTING absence page (``_navigate``'s own
            # ``_absence_page``/status-marker convention, matching
            # ``tests/unit/tui/test_nav_shell.py``'s own assertion shape) —
            # never a fabricated dossier.
            status = app.query_one("#status", Label)
            assert f"{_OVERVIEW_SUBJECT} [ABSENT]" in str(status.content)
            text = _dossier_text(app)
            assert "phi_year_inflow" not in text

    @pytest.mark.asyncio
    async def test_command_palette_does_not_offer_trade_pages(self) -> None:
        app, _campaign_id = _unwired_campaign_app()
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            provider = EntityNavigatorProvider(app.screen)
            hits = [hit async for hit in provider.discover()]
            texts = {hit.text for hit in hits}
            assert _OVERVIEW_SUBJECT not in texts
            assert _CANADA_SUBJECT not in texts
