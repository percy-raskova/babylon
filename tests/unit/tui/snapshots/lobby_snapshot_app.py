"""Launcher for the campaign-lobby snapshot test (Program 24 P3 WO-49).

Mirrors the other snapshot launchers' discipline: a FRESH app built here,
never a re-exported singleton. The catalog is seeded with FIXED UUIDs so
the derived operation codenames (a pure function of the UUID, spec-116)
are byte-stable — no ``uuid4`` anywhere in the snapshot path. Shows both
lifecycle states: an ACTIVE mid-campaign row and an ABANDONED one.
"""

from __future__ import annotations

from uuid import UUID

from textual.app import App

from babylon.tui.campaign_menu import (
    CampaignMenu,
    InMemoryCampaign,
    InMemoryCampaignCatalog,
    LobbyScreen,
)
from babylon.tui.theme import KSBC

_CATALOG = InMemoryCampaignCatalog(
    seed=(
        InMemoryCampaign(
            campaign_id=UUID(int=0x49),
            slug="campaign-fixed-one",
            engine_version="0.24.0",
            defines_hash="d" * 16,
            last_tick=52,
        ),
        InMemoryCampaign(
            campaign_id=UUID(int=0x24),
            slug="campaign-fixed-two",
            engine_version="0.24.0",
            defines_hash="d" * 16,
            status="ABANDONED",
        ),
    )
)

_MENU = CampaignMenu(_CATALOG, engine_version="0.24.0", defines_hash="d" * 16)


class LobbyHostApp(App[None]):
    """Bare host that boots straight into the lobby screen."""

    def on_mount(self) -> None:
        self.register_theme(KSBC)
        self.theme = "ksbc"
        self.push_screen(LobbyScreen(_MENU))


app = LobbyHostApp()
