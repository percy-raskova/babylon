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
from typing import TYPE_CHECKING

from babylon.projection.vault.git_backend import commit_page, commit_pages, init_vault
from babylon.projection.vault.render import render_county, render_sovereign
from babylon.projection.vault.render_industry import render_industry
from babylon.projection.vault.render_institution import render_institution
from babylon.projection.vault.render_key_figure import render_key_figure
from babylon.projection.vault.render_national import render_national
from babylon.projection.vault.render_organization import render_organization
from babylon.projection.vault.render_state import render_state
from babylon.projection.view_models import (
    CountyView,
    IndustryView,
    InstitutionView,
    KeyFigureView,
    NationalView,
    OrganizationView,
    SovereignView,
    StateView,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


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

    def bake_tick(self, pages: Mapping[str, str], *, tick: int) -> bytes | None:
        """Bake one committed tick's page set as ONE commit (WO-44).

        The vault-at-scale path: unchanged pages are skipped by content
        hash and every changed page lands in a single sim-time-pinned
        commit (see :func:`~babylon.projection.vault.git_backend.
        commit_pages`) — a quiet tick costs no commit at all.

        :param pages: relative page path → rendered page content, already
            rendered by the caller (the tick baker composes per-kind
            renderers; this method only materializes).
        :param tick: the committed tick, driving the commit timestamp.
        :returns: the commit sha, or ``None`` when nothing changed.
        """
        return commit_pages(
            self._vault_root,
            pages,
            tick=tick,
            message=f"bake: tick {tick}",
        )

    def bake_state(self, view: StateView, *, tick: int) -> Path:
        """Render and commit one state dossier page.

        The page path follows the stable-ID slug ruling
        (``project/programs/24-the-archive.md``): ``state/<fips>.md``,
        never a mutable display name — mirrors :meth:`bake_county` exactly,
        for the state nesting tier (Program 24 P2 WO-16).

        :param view: the state projection to materialize.
        :param tick: the simulation tick driving both the page's
            ``verified_tick`` frontmatter stamp (via
            :func:`~babylon.projection.vault.render_state.render_state`) and
            the commit's sim-time timestamp (via
            :func:`~babylon.projection.vault.git_backend.commit_page`).
        :returns: the absolute path of the written page under the vault
            root.
        """
        relative_path = f"state/{view.state_fips}.md"
        content = render_state(view, verified_tick=tick)
        commit_page(
            self._vault_root,
            relative_path,
            content,
            tick=tick,
            message=f"bake: state/{view.state_fips} @ tick {tick}",
        )
        return self._vault_root / relative_path

    def bake_national(self, view: NationalView, *, tick: int) -> Path:
        """Render and commit one national dossier page.

        The page path follows the same stable-ID slug ruling
        :meth:`bake_county` does: ``national/<national_id>.md``, never a
        mutable display name.

        :param view: the national projection to materialize.
        :param tick: the simulation tick driving both the page's
            ``verified_tick`` frontmatter stamp (via
            :func:`~babylon.projection.vault.render_national.
            render_national`) and the commit's sim-time timestamp (via
            :func:`~babylon.projection.vault.git_backend.commit_page`).
        :returns: the absolute path of the written page under the vault
            root.
        """
        relative_path = f"national/{view.national_id}.md"
        content = render_national(view, verified_tick=tick)
        commit_page(
            self._vault_root,
            relative_path,
            content,
            tick=tick,
            message=f"bake: national/{view.national_id} @ tick {tick}",
        )
        return self._vault_root / relative_path

    def bake_organization(self, view: OrganizationView, *, tick: int) -> Path:
        """Render and commit one organization dossier page (Program 24 P2 WO-18).

        The page path follows the same stable-ID slug ruling
        (``project/programs/24-the-archive.md``) county established:
        ``organization/<id>.md``, never a mutable display name.

        :param view: the organization projection to materialize.
        :param tick: the simulation tick driving both the page's
            ``verified_tick`` frontmatter stamp (via
            :func:`~babylon.projection.vault.render_organization.render_organization`)
            and the commit's sim-time timestamp (via
            :func:`~babylon.projection.vault.git_backend.commit_page`).
        :returns: the absolute path of the written page under the vault
            root.
        """
        relative_path = f"organization/{view.org_id}.md"
        content = render_organization(view, verified_tick=tick)
        commit_page(
            self._vault_root,
            relative_path,
            content,
            tick=tick,
            message=f"bake: organization/{view.org_id} @ tick {tick}",
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

    def bake_sovereign(self, view: SovereignView, *, tick: int) -> Path:
        """Render and commit one sovereign dossier page.

        The page path follows the same stable-ID slug ruling as
        ``bake_county``: ``sovereign/<id>.md``.

        :param view: the sovereign projection to materialize.
        :param tick: the simulation tick driving both the page's
            ``verified_tick`` frontmatter stamp (via
            :func:`~babylon.projection.vault.render.render_sovereign`) and
            the commit's sim-time timestamp (via
            :func:`~babylon.projection.vault.git_backend.commit_page`).
        :returns: the absolute path of the written page under the vault
            root.
        """
        relative_path = f"sovereign/{view.sovereign_id}.md"
        content = render_sovereign(view, verified_tick=tick)
        commit_page(
            self._vault_root,
            relative_path,
            content,
            tick=tick,
            message=f"bake: sovereign/{view.sovereign_id} @ tick {tick}",
        )
        return self._vault_root / relative_path

    def bake_key_figure(self, view: KeyFigureView, *, tick: int) -> Path:
        """Render and commit one key-figure dossier page.

        Always the honest-absence page (ADR084 — see
        :mod:`babylon.projection.key_figure`'s module docstring): this kind
        has no live producer, so the rendered content is the same for every
        ``key_figure_id`` beyond the identity stamped into it.

        :param view: the key-figure projection to materialize.
        :param tick: the simulation tick driving both the page's
            ``verified_tick`` frontmatter stamp (via
            :func:`~babylon.projection.vault.render_key_figure.render_key_figure`)
            and the commit's sim-time timestamp (via
            :func:`~babylon.projection.vault.git_backend.commit_page`).
        :returns: the absolute path of the written page under the vault
            root.
        """
        relative_path = f"key_figure/{view.key_figure_id}.md"
        content = render_key_figure(view, verified_tick=tick)
        commit_page(
            self._vault_root,
            relative_path,
            content,
            tick=tick,
            message=f"bake: key_figure/{view.key_figure_id} @ tick {tick}",
        )
        return self._vault_root / relative_path

    def bake_industry(self, view: IndustryView, *, tick: int) -> Path:
        """Render and commit one industry dossier page.

        The page path follows the stable-ID slug ruling
        (``project/programs/24-the-archive.md``): ``industry/<industry_id>.md``,
        never a mutable display name.

        :param view: the industry projection to materialize.
        :param tick: the simulation tick driving both the page's
            ``verified_tick`` frontmatter stamp (via
            :func:`~babylon.projection.vault.render_industry.render_industry`)
            and the commit's sim-time timestamp (via
            :func:`~babylon.projection.vault.git_backend.commit_page`).
        :returns: the absolute path of the written page under the vault
            root.
        """
        relative_path = f"industry/{view.industry_id}.md"
        content = render_industry(view, verified_tick=tick)
        commit_page(
            self._vault_root,
            relative_path,
            content,
            tick=tick,
            message=f"bake: industry/{view.industry_id} @ tick {tick}",
        )
        return self._vault_root / relative_path


__all__ = [
    "VaultMaterializer",
]
