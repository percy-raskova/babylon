"""Program v1.0.0 Unit U2: end-to-end reachability proof for the T3 pages
(``economy/USA``, ``field_state/USA``) in the live shell.

Builds directly on Unit U1 (``babylon.tui.app._refresh_known_entities``,
``CampaignHandle.known_subjects``): U1 proved the resolver/known-set gets
rebuilt from a live campaign's vault; this unit proves the FULL integration
seam a real ``babylon play`` boot depends on, using the T3 gap-projection
singletons (ADR125) as the concrete subjects:

1. the command palette's ``EntityNavigatorProvider`` surfaces
   ``economy/USA``/``field_state/USA`` once a live campaign whose vault has
   baked them is chosen;
2. navigating to each renders through ``BabylonFence`` with no "UNKNOWN
   DIRECTIVE" refusal and no "MALFORMED STATBLOCK BODY" refusal — the real
   statblock/absence numbers show up in the rendered widget tree;
3. a wikilink to ``economy/USA`` written into another page (the campaign's
   home dossier) classifies as a known wikilink span, not a redlink.

The fixture pages are never hand-typed markdown lookalikes: both are built
by calling the REAL renderers
(:func:`~babylon.projection.vault.render_economy.render_economy`,
:func:`~babylon.projection.vault.render_field_state.render_field_state`)
over REAL, fully-hydrated view-models
(:class:`~babylon.projection.view_models.EconomyView`/
:class:`~babylon.projection.view_models.FieldStateView`), the same pipeline
:mod:`babylon.projection.vault.tick_baker` uses to bake them into a
campaign's vault — so a template/renderer regression that broke the
``{statblock}``/``{absence}`` fence shape would fail THIS test, not just
``tests/unit/projection/vault/test_render_economy.py`` in isolation.

Drives ``ArchiveApp`` with Textual's ``Pilot`` through the same
lobby -> briefing -> campaign-shell flow as
``tests/unit/tui/test_app_lobby_flow.py``'s ``TestLiveVaultKnownEntities``
(a local, minimal ``_FakeCampaign``/``_FakeLoader`` double — no engine, no
Postgres), and inspects rendered widget content the same way
``tests/unit/tui/test_directives_hardening.py`` does for fence Labels and
``tests/unit/tui/test_wikilinks.py`` does for wikilink content spans.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from textual.content import Content
from textual.pilot import Pilot
from textual.widgets import Label, OptionList

from babylon.projection.endgame import EndgameStatus
from babylon.projection.vault.render_economy import render_economy
from babylon.projection.vault.render_field_state import render_field_state
from babylon.projection.verbs.view_models import VerbPlateView
from babylon.projection.view_models import (
    EconomyView,
    ProjectionRecord,
    hydrate_economy,
    hydrate_field_state,
)
from babylon.tui.app import ArchiveApp, BabylonMarkdown, TickOutcome
from babylon.tui.campaign_menu import CampaignMenu, InMemoryCampaign, InMemoryCampaignCatalog
from babylon.tui.palette import EntityNavigated, EntityNavigatorProvider
from babylon.tui.router import parse_babylon_uri
from babylon.tui.wikilinks import REDLINK_COLOR, WIKILINK_COLOR, BabylonParagraph

pytestmark = pytest.mark.unit

_VERIFIED_TICK = 520
_HOME_SUBJECT = "county/26163"
_ECONOMY_SUBJECT = "economy/USA"
_FIELD_STATE_SUBJECT = "field_state/USA"

_HOME_PAGE = f"""\
# {_HOME_SUBJECT} — Wayne

Nationwide context: [[{_ECONOMY_SUBJECT}]] and [[{_FIELD_STATE_SUBJECT}]].
"""
"""The campaign's home dossier (the WO-47/Unit-C2 ``_SAMPLE_SUBJECT``): a
hand-written link source, NOT one of the T3 pages under test — only
``economy/USA``/``field_state/USA`` need come from the real renderers."""


def _economy_usa_page() -> str:
    """``economy/USA``, baked via the real T3 renderer over a fully-hydrated
    ``EconomyView`` — mirrors ``tests/unit/projection/vault/conftest.py``'s
    ``usa_economy_view`` fixture shape (``energy_beta_j`` stays the one
    field that is genuinely absent tree-wide even here)."""
    view = hydrate_economy(
        {
            "kind": "economy",
            "economy_id": "USA",
            "verified_tick": _VERIFIED_TICK,
            "wage_balance": 0.18,
            "labor_aristocracy_verdict": True,
            "class_phi_readings": [
                {
                    "entity_id": "C001",
                    "w_paid": 120.0,
                    "v_produced": 100.0,
                    "phi_absolute": 20.0,
                    "phi_relative": 0.2,
                    "labor_aristocracy_ratio": 1.2,
                    "is_labor_aristocracy": True,
                }
            ],
            "phi_unequal_exchange": 12.0,
            "phi_reproduction": 8.0,
            "phi_domestic": 5.0,
            "phi_iii_report": 2.0,
            "phi_decomposition_total": 25.0,
            "surplus_produced": 1500.0,
            "profit_of_enterprise": 600.0,
            "interest_burden": 150.0,
            "ground_rent": 450.0,
            "taxes_on_surplus": 300.0,
            "rentier_share": 0.3,
            "financialization_share": 0.1,
            "total_consumption": 900.0,
            "total_biocapacity": 1000.0,
            "overshoot_ratio": 0.9,
            "biocapacity_ceiling": 1200.0,
        }
    )
    return render_economy(view, verified_tick=_VERIFIED_TICK)


def _field_state_usa_page() -> str:
    """``field_state/USA``, baked via the real T3 renderer over a
    fully-hydrated ``FieldStateView`` — mirrors ``tests/unit/projection/
    vault/conftest.py``'s ``usa_field_state_view`` fixture shape."""
    view = hydrate_field_state(
        {
            "kind": "field_state",
            "field_state_id": "USA",
            "verified_tick": _VERIFIED_TICK,
            "nodes": [
                {
                    "node_id": "C001",
                    "name": "Periphery Proletariat",
                    "fields": {"exploitation": 0.523, "atomization": 0.1},
                    "laplacian": {"exploitation": 0.4},
                    "df_dt": {"exploitation": 0.05},
                    "fascist_alignment": 0.2,
                }
            ],
            "edges": [
                {
                    "source": "C001",
                    "target": "C002",
                    "source_territory": "T001",
                    "target_territory": "T001",
                    "field": "exploitation",
                    "gradient": 0.2,
                }
            ],
            "principal_field": {
                "field_name": "exploitation",
                "max_abs_df_dt": 0.42,
                "changed": True,
            },
            "dialectical_regime": {
                "regime": "crisis",
                "opposition": "capital_labor",
                "rate": 0.07,
            },
        }
    )
    return render_field_state(view, verified_tick=_VERIFIED_TICK)


class _FakeCampaign:
    """A minimal ``CampaignHandle`` double whose vault already carries the
    T3 singletons — no engine, no Postgres (matches ``test_app_lobby_flow.
    py``'s ``_FakeCampaign`` shape)."""

    def __init__(self, session_id: UUID, pages: dict[str, str]) -> None:
        self.session_id = session_id
        self.tick = 0
        self._pages = pages

    def read_page(self, subject: str) -> str | None:
        return self._pages.get(subject)

    def known_subjects(self) -> frozenset[str]:
        return frozenset(self._pages)

    def dashboard_view(self) -> EconomyView | None:
        """No live projection wired for this double — honest ``None``
        (Program 24 P2's ``CampaignHandle.dashboard_view`` seam); this
        unit's own concern is the vault-page wikilink/palette reachability,
        not the dashboard pane."""
        return None

    def endgame_status(self) -> EndgameStatus | None:
        """No live endgame-progress projection wired for this double — honest ``None``
        (Program 24 P4's ``CampaignHandle.endgame_status`` seam); unrelated to this
        unit's own concern."""
        return None

    def verb_plate_view(self) -> VerbPlateView | None:
        """No live verb plate wired for this double — honest ``None``
        (Program 24 P5's ``CampaignHandle.verb_plate_view`` seam); unrelated to this
        unit's own concern."""
        return None

    def subject_view(self, subject_id: str) -> ProjectionRecord | None:
        """No live per-subject projection wired for this double — honest ``None``
        (unit "live-subject-view", shell-interconnect's own ``CampaignHandle.
        subject_view`` seam); unrelated to this unit's own concern."""
        return None

    def issue_verb(self, action_id: str) -> int:  # pragma: no cover - unused by this unit
        raise AssertionError("issue_verb should not be called by this reachability unit")

    def advance_tick(self) -> TickOutcome:
        """Unused by this unit — proving the T3 pages are already
        vault-reachable never requires advancing a tick."""
        raise NotImplementedError("this unit never advances the tick")


class _FakeLoader:
    """The ``CampaignLoader`` double."""

    def __init__(self, campaign: _FakeCampaign) -> None:
        self._campaign = campaign

    def __call__(self, campaign_id: UUID) -> _FakeCampaign:
        return self._campaign


def _seeded_menu() -> tuple[CampaignMenu, UUID]:
    """One seeded ACTIVE campaign, ready for the lobby to list/choose."""
    campaign_id = UUID(int=1)
    catalog = InMemoryCampaignCatalog(
        seed=(
            InMemoryCampaign(
                campaign_id=campaign_id,
                slug="campaign-t3",
                engine_version="0.1.0",
                defines_hash="d" * 16,
            ),
        )
    )
    return CampaignMenu(catalog, engine_version="0.1.0", defines_hash="d" * 16), campaign_id


def _live_campaign_app() -> tuple[ArchiveApp, UUID]:
    """A booted ``ArchiveApp`` wired to a campaign whose vault already
    carries the briefing, the home dossier, and both T3 pages."""
    menu, campaign_id = _seeded_menu()
    briefing_subject = f"briefing/{campaign_id}"
    campaign = _FakeCampaign(
        campaign_id,
        {
            briefing_subject: "# OPERATION T3\n",
            _HOME_SUBJECT: _HOME_PAGE,
            _ECONOMY_SUBJECT: _economy_usa_page(),
            _FIELD_STATE_SUBJECT: _field_state_usa_page(),
        },
    )
    loader = _FakeLoader(campaign)
    return ArchiveApp(campaign_menu=menu, campaign_loader=loader), campaign_id


async def _boot_into_campaign_shell(pilot: Pilot[None]) -> None:
    """Walk the lobby -> briefing -> campaign-shell flow (``TestLobbyToCampaignShellFlow``'s
    own idiom, ``tests/unit/tui/test_app_lobby_flow.py``)."""
    await pilot.pause()
    pilot.app.screen.query_one("#campaigns", OptionList).focus()
    await pilot.press("enter")  # choose the seeded campaign
    await pilot.pause()
    await pilot.press("enter")  # "Begin Operation" on the briefing
    await pilot.pause()


def _dossier_text(app: ArchiveApp) -> str:
    """Every fence-rendered ``Label``'s plain text under ``#dossier``, joined.

    Runs each label back through the real ``Content`` markup parser (the
    same oracle ``test_directives_hardening.py``'s ``_plain_text`` uses) —
    checking a substring against the raw, unparsed ``label.content`` would
    pass even for a bug where markup silently ate part of the text.

    :param app: the live app, already navigated to the page under test.
    :returns: the concatenated plain text of every dossier Label.
    """
    dossier = app.query_one("#dossier", BabylonMarkdown)
    parts: list[str] = []
    for label in dossier.query(Label):
        if label._render_markup:
            parts.append(Content.from_markup(label.content).plain)
        else:
            parts.append(str(label.content))
    return "\n".join(parts)


class TestCommandPaletteSurfacesT3Pages:
    """Requirement 1: the palette's ``EntityNavigatorProvider`` offers both
    T3 singletons once the live campaign that baked them is chosen."""

    @pytest.mark.asyncio
    async def test_discover_lists_both_t3_pages(self) -> None:
        app, _campaign_id = _live_campaign_app()
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            provider = EntityNavigatorProvider(app.screen)
            hits = [hit async for hit in provider.discover()]
            texts = {hit.text for hit in hits}
            assert _ECONOMY_SUBJECT in texts
            assert _FIELD_STATE_SUBJECT in texts

    @pytest.mark.asyncio
    async def test_search_finds_economy_usa(self) -> None:
        app, _campaign_id = _live_campaign_app()
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            provider = EntityNavigatorProvider(app.screen)
            hits = [hit async for hit in provider.search("economy")]
            assert any(hit.text == _ECONOMY_SUBJECT for hit in hits)

    @pytest.mark.asyncio
    async def test_search_finds_field_state_usa(self) -> None:
        app, _campaign_id = _live_campaign_app()
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            provider = EntityNavigatorProvider(app.screen)
            hits = [hit async for hit in provider.search("field_state")]
            assert any(hit.text == _FIELD_STATE_SUBJECT for hit in hits)


class TestT3PagesRenderCleanly:
    """Requirement 2: navigating to each T3 page renders through
    ``BabylonFence`` with no loud-refusal directive and the real
    renderer-produced numbers visible in the mounted widget tree."""

    @pytest.mark.asyncio
    async def test_economy_usa_renders_its_real_numbers_with_no_refusal(self) -> None:
        app, _campaign_id = _live_campaign_app()
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            app.post_message(EntityNavigated(parse_babylon_uri(f"babylon://{_ECONOMY_SUBJECT}")))
            await pilot.pause()

            assert app.nav.current == _ECONOMY_SUBJECT
            text = _dossier_text(app)
            assert "UNKNOWN DIRECTIVE" not in text
            assert "MALFORMED STATBLOCK BODY" not in text
            # Real EconomyView-derived numbers, not a fixture lookalike.
            assert "wage_balance" in text
            assert "0.180000" in text
            assert "phi_decomposition_total" in text
            assert "25.000000" in text
            # The one field genuinely absent tree-wide renders as an honest
            # absence block, not a refusal.
            assert "energy_beta_j" in text
            assert "ABSENT" in text

    @pytest.mark.asyncio
    async def test_field_state_usa_renders_its_real_numbers_with_no_refusal(self) -> None:
        app, _campaign_id = _live_campaign_app()
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            app.post_message(
                EntityNavigated(parse_babylon_uri(f"babylon://{_FIELD_STATE_SUBJECT}"))
            )
            await pilot.pause()

            assert app.nav.current == _FIELD_STATE_SUBJECT
            text = _dossier_text(app)
            assert "UNKNOWN DIRECTIVE" not in text
            assert "MALFORMED STATBLOCK BODY" not in text
            # Real FieldStateView-derived numbers, not a fixture lookalike.
            assert "dialectical_regime.regime" in text
            assert "crisis" in text
            assert "node.C001.fields.exploitation" in text
            assert "0.523000" in text


class TestWikilinkToEconomyUsaClassifiesAsKnown:
    """Requirement 3: a wikilink to ``economy/USA`` written into another
    page (the campaign's home dossier) classifies as known — a gold
    wikilink span, never a crimson redlink."""

    @pytest.mark.asyncio
    async def test_home_page_wikilink_to_economy_usa_is_known(self) -> None:
        app, _campaign_id = _live_campaign_app()
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            assert app.nav.current == _HOME_SUBJECT
            dossier = app.query_one("#dossier", BabylonMarkdown)
            paragraph = next(
                p for p in dossier.query(BabylonParagraph) if _ECONOMY_SUBJECT in p.content.plain
            )
            span = next(
                s
                for s in paragraph.content.spans
                if s.style.meta.get("@click") == f"link('babylon://{_ECONOMY_SUBJECT}')"
            )
            assert span.style.foreground == WIKILINK_COLOR
            assert span.style.foreground != REDLINK_COLOR

    @pytest.mark.asyncio
    async def test_home_page_wikilink_to_field_state_usa_is_known(self) -> None:
        app, _campaign_id = _live_campaign_app()
        async with app.run_test() as pilot:
            await _boot_into_campaign_shell(pilot)

            dossier = app.query_one("#dossier", BabylonMarkdown)
            paragraph = next(
                p
                for p in dossier.query(BabylonParagraph)
                if _FIELD_STATE_SUBJECT in p.content.plain
            )
            span = next(
                s
                for s in paragraph.content.spans
                if s.style.meta.get("@click") == f"link('babylon://{_FIELD_STATE_SUBJECT}')"
            )
            assert span.style.foreground == WIKILINK_COLOR
