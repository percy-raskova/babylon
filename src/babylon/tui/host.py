"""The Rust client's host seam (M0 lobby surface — the raster cutover, ADR150).

:class:`RustClientHost` is THE seam between the Python composition root and
the Rust/Ratatui client: Python remains the single writer, and every read
crosses the FFI as a JSON string of primitives (``model_dump_json()`` /
``json.dumps`` — no Python objects cross except the host handle itself).

Layering: like the rest of ``babylon.tui``, this module never imports
``babylon.engine``, ``babylon.persistence``, or the game session directly
(the import-linter contract) — the session and driver arrive pre-composed
through :meth:`RustClientHost.bind_session` as structural protocols.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from babylon.tui.app import CampaignHandle, PacedDriverHandle
    from babylon.tui.campaign_menu import CampaignCatalog

__all__ = ["RustClientHost"]


class RustClientHost:
    """Serve frozen view-models to the Rust client as JSON strings.

    :param catalog: The campaign catalog seam (``BabylonMetaStore`` in
        production, ``InMemoryCampaignCatalog`` in tests).
    :param defines_hash: Provenance hash of the loaded :class:`GameDefines`,
        stamped on every lobby row.
    :param engine_version: The running engine version, stamped alongside.
    """

    def __init__(
        self,
        catalog: CampaignCatalog,
        *,
        defines_hash: str,
        engine_version: str,
    ) -> None:
        self._catalog = catalog
        self._defines_hash = defines_hash
        self._engine_version = engine_version
        #: The bound campaign session (``None`` until :meth:`bind_session`).
        self.session: CampaignHandle | None = None
        #: The bound paced tick driver (``None`` until :meth:`bind_session`).
        self.driver: PacedDriverHandle | None = None

    def lobby_catalog_json(self) -> str:
        """The lobby catalog as a JSON array string.

        Each row carries the keys the Rust ``LobbyRow`` deserializer
        requires (``campaign_id``/``name``/``tick``) plus ``status`` and the
        provenance stamps. An empty catalog is ``[]`` — honest absence
        (III.11), never a fabricated row.
        """
        rows = [
            {
                "campaign_id": str(campaign.campaign_id),
                "name": campaign.slug,
                "tick": campaign.last_tick,
                "status": campaign.status,
                "defines_hash": self._defines_hash,
                "engine_version": self._engine_version,
            }
            for campaign in self._catalog.list_campaigns()
        ]
        return json.dumps(rows)

    def bind_session(self, session: CampaignHandle, driver: PacedDriverHandle) -> None:
        """Bind the booted campaign session and its paced driver.

        Called by the composition root's campaign loader once the session
        exists; M1+ read methods serve from these handles.
        """
        self.session = session
        self.driver = driver
