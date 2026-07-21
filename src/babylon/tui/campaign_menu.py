"""The campaign menu over the ``babylon_meta`` catalog (WO-49).

The lobby's honest size (design canon local-first §3.2): a load list.
Each row shows the campaign's operation codename, ``Tick N``, and its
lifecycle status; "New" mints a campaign; "archive" is the REVERSIBLE
``ABANDONED`` status (the row survives, restorable); hard delete is
arm-then-confirm — one wrong key disarms (the ported
``n-briefing.spec.ts`` lobby lifecycle, CARRIED ledger row closed here).

The catalog is a structural seam (the WO-37/WO-47 trick):
:class:`CampaignCatalog`'s method shapes mirror
:class:`babylon.persistence.babylon_meta.BabylonMetaStore` exactly, so
the composition root injects the real store while ``babylon.tui`` never
imports persistence. :class:`InMemoryCampaignCatalog` is the no-database
default and the unit-test double.

Codenames are never stored: ``operation_codename`` (spec-116 FR-116-3,
ported to ``babylon.projection.briefing``) derives them on read from the
campaign UUID, byte-stable forever. The slug persisted in the catalog is
a machine key, unique by construction.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, Protocol, runtime_checkable
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Label, OptionList
from textual.widgets.option_list import Option

from babylon.projection.briefing import operation_codename

__all__ = [
    "CampaignCatalog",
    "CampaignMenu",
    "CampaignSummary",
    "InMemoryCampaign",
    "InMemoryCampaignCatalog",
    "LobbyRow",
    "LobbyScreen",
]


@runtime_checkable
class CampaignSummary(Protocol):
    """Structural shape of one catalog row the lobby reads.

    Members are read-only properties, not plain attributes — protocol
    attributes are invariant (mutable), which a frozen Pydantic row could
    never satisfy; a read-only property is satisfied by any attribute.
    """

    @property
    def campaign_id(self) -> UUID:
        """The campaign's minted UUID."""
        ...

    @property
    def slug(self) -> str:
        """The unique machine key."""
        ...

    @property
    def last_tick(self) -> int:
        """Highest tick reached."""
        ...

    @property
    def status(self) -> str:
        """Lifecycle state (``"ACTIVE"`` / ``"ABANDONED"``)."""
        ...


@runtime_checkable
class CampaignCatalog(Protocol):
    """The seam ``BabylonMetaStore`` satisfies structurally.

    Method shapes mirror the store exactly — that correspondence IS the
    contract (pinned by ``tests/unit/tui/test_campaign_menu.py``), so
    neither module imports the other.
    """

    def list_campaigns(self) -> Sequence[CampaignSummary]:
        """Return the catalog in a stable display order.

        :returns: all campaigns, or an honestly empty sequence.
        """
        ...

    def create_campaign(
        self, *, slug: str, engine_version: str, defines_hash: str
    ) -> CampaignSummary:
        """Mint a new campaign and return its row.

        :param slug: unique machine key.
        :param engine_version: engine version to stamp.
        :param defines_hash: ``GameDefines`` hash to stamp.
        :returns: the freshly minted row.
        """
        ...

    def set_status(self, campaign_id: UUID, status: Literal["ACTIVE", "ABANDONED"]) -> None:
        """Set the campaign's lifecycle status (reversible).

        :param campaign_id: the campaign to transition.
        :param status: the new status.
        """
        ...

    def delete_campaign(self, campaign_id: UUID) -> bool:
        """Hard-delete a campaign.

        :param campaign_id: the campaign to delete.
        :returns: ``True`` if a row was deleted.
        """
        ...


class LobbyRow(BaseModel):
    """One rendered lobby row: what the load list displays.

    :param campaign_id: the campaign the row represents.
    :param codename: the derived operation codename (never stored).
    :param tick_label: ``"Tick N"`` progress text.
    :param status: lifecycle state shown on the row.
    """

    model_config = ConfigDict(frozen=True)

    campaign_id: UUID
    codename: str
    tick_label: str
    status: str

    @property
    def label(self) -> str:
        """The row's one-line display form."""
        return f"{self.codename} · {self.tick_label} · {self.status}"


class InMemoryCampaign(BaseModel):
    """The in-memory catalog's row shape (satisfies :class:`CampaignSummary`)."""

    model_config = ConfigDict(frozen=True)

    campaign_id: UUID
    slug: str
    engine_version: str
    defines_hash: str
    last_tick: int = 0
    status: str = "ACTIVE"


class InMemoryCampaignCatalog:
    """Dict-backed :class:`CampaignCatalog` — no database, no disk.

    The honest no-persistence default (campaigns die with the process)
    and the unit-test double for the lobby's catalog choreography.

    :param seed: campaigns present from the start — deterministic
        fixtures (snapshot apps) construct their rows with fixed UUIDs
        here instead of minting random ones through ``create_campaign``.
    """

    def __init__(self, seed: Sequence[InMemoryCampaign] = ()) -> None:
        self._campaigns: dict[UUID, InMemoryCampaign] = {
            campaign.campaign_id: campaign for campaign in seed
        }

    def list_campaigns(self) -> Sequence[CampaignSummary]:
        """See :meth:`CampaignCatalog.list_campaigns` (insertion order)."""
        return tuple(self._campaigns.values())

    def create_campaign(
        self, *, slug: str, engine_version: str, defines_hash: str
    ) -> CampaignSummary:
        """See :meth:`CampaignCatalog.create_campaign`.

        :raises ValueError: on a duplicate slug (the in-memory analogue of
            the store's ``UniqueViolation`` — loud, not renamed).
        """
        if any(campaign.slug == slug for campaign in self._campaigns.values()):
            msg = f"duplicate campaign slug: {slug!r}"
            raise ValueError(msg)
        campaign = InMemoryCampaign(
            campaign_id=uuid4(),
            slug=slug,
            engine_version=engine_version,
            defines_hash=defines_hash,
        )
        self._campaigns[campaign.campaign_id] = campaign
        return campaign

    def set_status(self, campaign_id: UUID, status: Literal["ACTIVE", "ABANDONED"]) -> None:
        """See :meth:`CampaignCatalog.set_status`.

        :raises LookupError: if the campaign does not exist.
        """
        campaign = self._campaigns.get(campaign_id)
        if campaign is None:
            msg = f"no campaign {campaign_id} to set status on"
            raise LookupError(msg)
        self._campaigns[campaign_id] = campaign.model_copy(update={"status": status})

    def delete_campaign(self, campaign_id: UUID) -> bool:
        """See :meth:`CampaignCatalog.delete_campaign`."""
        return self._campaigns.pop(campaign_id, None) is not None


class CampaignMenu:
    """The lobby controller: rows, minting, lifecycle, arm-then-confirm.

    :param catalog: where campaigns live (the structural seam).
    :param engine_version: stamped on campaigns minted here.
    :param defines_hash: stamped on campaigns minted here.
    """

    def __init__(self, catalog: CampaignCatalog, *, engine_version: str, defines_hash: str) -> None:
        self._catalog = catalog
        self._engine_version = engine_version
        self._defines_hash = defines_hash
        self._armed_delete: UUID | None = None

    @property
    def armed_delete(self) -> UUID | None:
        """The campaign currently armed for deletion, if any."""
        return self._armed_delete

    def rows(self) -> tuple[LobbyRow, ...]:
        """Render the catalog as display rows (codename · Tick N · status).

        :returns: one row per campaign, in the catalog's order.
        """
        return tuple(
            LobbyRow(
                campaign_id=campaign.campaign_id,
                codename=operation_codename(campaign.campaign_id),
                tick_label=f"Tick {campaign.last_tick}",
                status=campaign.status,
            )
            for campaign in self._catalog.list_campaigns()
        )

    def new_campaign(self) -> LobbyRow:
        """Mint a campaign; its codename derives from the minted UUID.

        The slug is a machine key unique by construction; the codename is
        computed on read (spec-116 FR-116-3), never persisted.

        :returns: the freshly minted campaign's lobby row.
        """
        self.disarm()
        minted = self._catalog.create_campaign(
            slug=f"campaign-{uuid4().hex[:12]}",
            engine_version=self._engine_version,
            defines_hash=self._defines_hash,
        )
        return LobbyRow(
            campaign_id=minted.campaign_id,
            codename=operation_codename(minted.campaign_id),
            tick_label=f"Tick {minted.last_tick}",
            status=minted.status,
        )

    def toggle_archive(self, campaign_id: UUID) -> str:
        """Flip a campaign between ``ACTIVE`` and ``ABANDONED`` (reversible).

        :param campaign_id: the campaign to flip.
        :raises LookupError: if the campaign is not in the catalog.
        :returns: the new status.
        """
        self.disarm()
        current = next(
            (c for c in self._catalog.list_campaigns() if c.campaign_id == campaign_id),
            None,
        )
        if current is None:
            msg = f"no campaign {campaign_id} to archive"
            raise LookupError(msg)
        flipped: Literal["ACTIVE", "ABANDONED"] = (
            "ABANDONED" if current.status == "ACTIVE" else "ACTIVE"
        )
        self._catalog.set_status(campaign_id, flipped)
        return flipped

    def arm_delete(self, campaign_id: UUID) -> None:
        """Arm ``campaign_id`` for deletion (the first of two steps).

        :param campaign_id: the campaign to arm.
        """
        self._armed_delete = campaign_id

    def disarm(self) -> None:
        """Clear any armed deletion — every non-confirm action calls this."""
        self._armed_delete = None

    def confirm_delete(self, campaign_id: UUID) -> bool:
        """Delete ``campaign_id`` IFF it is the armed campaign; always disarm.

        A confirm against an unarmed or differently-armed campaign deletes
        nothing (the wrong-key escape hatch of arm-then-confirm).

        :param campaign_id: the campaign the confirm targets.
        :returns: ``True`` only when the armed campaign was deleted.
        """
        armed = self._armed_delete
        self.disarm()
        if armed != campaign_id:
            return False
        return self._catalog.delete_campaign(campaign_id)


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
