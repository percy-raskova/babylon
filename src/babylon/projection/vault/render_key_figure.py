"""Sandboxed deterministic key-figure-page rendering (Constitution III.13).

Kept in its own module rather than appended to
:mod:`babylon.projection.vault.render` — the work-order recipe's explicit
escape hatch ("``render_<kind>`` in ``vault/render.py`` (or
``vault/render_state.py``)") — because every Program 24 P2 Lane P work order
is executed worktree-isolated in parallel; a shared tail-append to
``render.py`` would put every kind's WO in direct collision on the same
file, unlike the four files the shared-file discipline table names as
genuinely append-only zippers. This module still reuses
:func:`babylon.projection.vault.render._build_environment` rather than
constructing a second sandboxed Jinja environment — ADR099's contract is
"this is the *only* place the environment is built," and that is honored by
importing the one factory, not by re-implementing it.

Unlike :func:`~babylon.projection.vault.render.render_county`, this renderer
has no per-field statblock/absence walk to do:
:class:`~babylon.projection.view_models.KeyFigureView` declares no field
beyond identity, so the page is unconditionally the honest-absence page —
see :mod:`babylon.projection.key_figure`'s module docstring for why (ADR084).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.projection.key_figure import DEAD_PRODUCER_REMEDY
from babylon.projection.vault.render import _build_environment

if TYPE_CHECKING:
    from babylon.projection.view_models import KeyFigureView

__all__ = ["render_key_figure"]


def render_key_figure(view: KeyFigureView, *, verified_tick: int) -> str:
    """Render a key-figure dossier page from a projection view-model.

    Pure function of ``(view, verified_tick)`` — no wall-clock, no
    randomness, no filesystem reads inside the template — so two calls with
    identical arguments yield byte-identical output (Constitution III.13's
    determinism contract).

    :param view: the key-figure projection to materialize.
    :param verified_tick: the tick stamped into the page's frontmatter as
        its staleness anchor. Passed explicitly rather than read from
        ``view.verified_tick`` so the caller (the materializer) declares the
        bake tick once and unambiguously (mirrors ``render_county``).
    :returns: the rendered Markdown page text — always the honest-absence
        page (see the module docstring).
    :raises jinja2.exceptions.UndefinedError: if the template references a
        field this module does not pass in (a template/model shape drift).
    """
    environment = _build_environment()
    template = environment.get_template("key_figure.md.j2")
    return template.render(
        key_figure=view,
        verified_tick=verified_tick,
        dead_producer_remedy=DEAD_PRODUCER_REMEDY,
    )
