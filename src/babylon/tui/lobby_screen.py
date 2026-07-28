"""The Textual lobby screen (WO-49) — split from ``campaign_menu`` at the M7
cutover decoupling so the menu/catalog logic the Rust host needs stays
textual-free. This module dies with the Textual estate at the ceremony.
"""

from __future__ import annotations

from uuid import UUID

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Label, OptionList
from textual.widgets.option_list import Option

from babylon.tui.campaign_menu import CampaignMenu, LobbyRow

__all__ = ["LobbyScreen"]


#: The lobby's idle key-hint line.
_LOBBY_HINTS = "n new · a archive/restore · d d delete · enter load"


class LobbyScreen(Screen[UUID | None]):
    """The load/new campaign menu (design canon local-first §3.2).

    Renders the catalog as an :class:`~textual.widgets.OptionList` of
    lobby rows and dismisses with the chosen campaign's UUID (or ``None``
    on escape). Lifecycle keys act on the highlighted row: ``n`` mints,
    ``a`` archives/restores (reversible), ``d`` arms deletion and a second
    ``d`` on the same row confirms it — any other lifecycle action
    disarms. Session boot for the chosen campaign is the composition
    root's job (WO-50), not this screen's.

    :param menu: the lobby controller over the catalog seam.
    """

    BINDINGS = [
        Binding("n", "new_campaign", "New"),
        Binding("a", "toggle_archive", "Archive"),
        Binding("d", "delete_step", "Delete"),
        Binding("escape", "leave", "Back"),
    ]

    def __init__(self, menu: CampaignMenu) -> None:
        super().__init__()
        self._menu = menu

    def compose(self) -> ComposeResult:
        yield Label("THE ARCHIVE — CAMPAIGNS", id="lobby-title")
        yield OptionList(id="campaigns")
        yield Label(_LOBBY_HINTS, id="lobby-status")
        yield Footer()

    def on_mount(self) -> None:
        self._reload()

    def _reload(self, *, status: str | None = None) -> None:
        """Rebuild the option rows from the catalog; keep the highlight sane.

        :param status: a one-line outcome to show, or ``None`` for hints.
        """
        campaigns = self.query_one("#campaigns", OptionList)
        previous = campaigns.highlighted
        campaigns.clear_options()
        for row in self._menu.rows():
            campaigns.add_option(Option(row.label, id=str(row.campaign_id)))
        if campaigns.option_count:
            campaigns.highlighted = min(previous or 0, campaigns.option_count - 1)
        self.query_one("#lobby-status", Label).update(status or _LOBBY_HINTS)

    def _highlighted_row(self) -> LobbyRow | None:
        """The lobby row under the highlight, or ``None`` for an empty list."""
        campaigns = self.query_one("#campaigns", OptionList)
        if campaigns.highlighted is None:
            return None
        option_id = campaigns.get_option_at_index(campaigns.highlighted).id
        return next((row for row in self._menu.rows() if str(row.campaign_id) == option_id), None)

    def action_new_campaign(self) -> None:
        """``n``: mint a campaign and show its codename."""
        row = self._menu.new_campaign()
        self._reload(status=f"minted {row.codename}")

    def action_toggle_archive(self) -> None:
        """``a``: archive/restore the highlighted campaign (reversible)."""
        row = self._highlighted_row()
        if row is None:
            return
        status = self._menu.toggle_archive(row.campaign_id)
        self._reload(status=f"{row.codename} → {status}")

    def action_delete_step(self) -> None:
        """``d``: arm the highlighted campaign; a second ``d`` confirms."""
        row = self._highlighted_row()
        if row is None:
            return
        if self._menu.armed_delete == row.campaign_id:
            deleted = self._menu.confirm_delete(row.campaign_id)
            self._reload(status=f"deleted {row.codename}" if deleted else None)
            return
        self._menu.arm_delete(row.campaign_id)
        self.query_one("#lobby-status", Label).update(
            f"press d again to DELETE {row.codename} (any other action cancels)"
        )

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Enter on a row: choose that campaign.

        :param event: the selection; its option id is the campaign UUID.
        """
        if event.option.id is not None:
            self.dismiss(UUID(event.option.id))

    def action_leave(self) -> None:
        """Escape: leave the lobby without choosing."""
        self.dismiss(None)
