"""The vault materializer orchestrator skeleton (Constitution III.13).

:class:`VaultMaterializer` wires :mod:`babylon.projection.vault.render` and
:mod:`babylon.projection.vault.git_backend` together: render a
:class:`~babylon.projection.view_models.CountyView` to Markdown, write it
under the vault root, and commit it with a sim-time-pinned dulwich commit.

Explicit dependency injection only. ``vault_root`` is a constructor
parameter the caller (a future composition root) supplies — this module
reads no config file (no ``config.toml`` ``[vault]`` section) and no
:class:`~babylon.config.defines.GameDefines`. Wiring the real on-disk vault
path (``~/.local/share/babylon/vault/<slug>/`` per the design canon) and
invoking :meth:`VaultMaterializer.bake_county` from the actual
:func:`~babylon.projection.county.project_county` read-model at tick commit
are both later work (Program 24 P1 WO-7); this class is a fixture-fed
skeleton until then.
"""

from __future__ import annotations

from pathlib import Path

from babylon.projection.vault.git_backend import commit_page, init_vault
from babylon.projection.vault.render import render_county
from babylon.projection.vault.render_institution import render_institution
from babylon.projection.view_models import CountyView, InstitutionView


class VaultMaterializer:
    """Bakes projection view-models into vault pages, one commit per bake.

    :param vault_root: the vault repository root directory, supplied
        explicitly by the caller. Initialized as a dulwich repo on first
        use if it isn't one already (:func:`~babylon.projection.vault.
        git_backend.init_vault` is idempotent).
    """

    def __init__(self, vault_root: Path) -> None:
        init_vault(vault_root)
        self._vault_root = vault_root

    def bake_county(self, view: CountyView, *, tick: int) -> Path:
        """Render and commit one county dossier page.

        The page path follows the stable-ID slug ruling
        (``project/programs/24-the-archive.md``): ``county/<fips>.md``,
        never a mutable display name.

        :param view: the county projection to materialize.
        :param tick: the simulation tick driving both the page's
            ``verified_tick`` frontmatter stamp (via
            :func:`~babylon.projection.vault.render.render_county`) and the
            commit's sim-time timestamp (via
            :func:`~babylon.projection.vault.git_backend.commit_page`).
        :returns: the absolute path of the written page under the vault
            root.
        """
        relative_path = f"county/{view.county_fips}.md"
        content = render_county(view, verified_tick=tick)
        commit_page(
            self._vault_root,
            relative_path,
            content,
            tick=tick,
            message=f"bake: county/{view.county_fips} @ tick {tick}",
        )
        return self._vault_root / relative_path

    def bake_institution(self, view: InstitutionView, *, tick: int) -> Path:
        """Render and commit one institution dossier page.

        The page path follows the stable-ID slug ruling
        (``project/programs/24-the-archive.md``): ``institution/<id>.md``,
        never a mutable display name.

        :param view: the institution projection to materialize.
        :param tick: the simulation tick driving both the page's
            ``verified_tick`` frontmatter stamp (via
            :func:`~babylon.projection.vault.render_institution.
            render_institution`) and the commit's sim-time timestamp (via
            :func:`~babylon.projection.vault.git_backend.commit_page`).
        :returns: the absolute path of the written page under the vault
            root.
        """
        relative_path = f"institution/{view.institution_id}.md"
        content = render_institution(view, verified_tick=tick)
        commit_page(
            self._vault_root,
            relative_path,
            content,
            tick=tick,
            message=f"bake: institution/{view.institution_id} @ tick {tick}",
        )
        return self._vault_root / relative_path


__all__ = ["VaultMaterializer"]
