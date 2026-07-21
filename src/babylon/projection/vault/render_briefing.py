"""Sandboxed deterministic briefing-page rendering (WO-35; Constitution III.13).

Reuses the vault's canonical sandboxed Jinja2 environment factory
(:func:`babylon.projection.vault.render._build_environment`) rather than
constructing a second one — that module's docstring states it is "the only
place the environment is built," and ``briefing.md.j2`` lives alongside
``county.md.j2`` under the same ``PackageLoader("babylon.projection.vault",
"templates")`` root, so no new loader wiring is needed either.

Split into its own module — not appended to :mod:`babylon.projection.vault.
render` directly — to stay collision-free with sibling Lane P/content
work-orders that are also adding a ``render_<kind>`` during this P2 fan-out
(the work-order doc explicitly sanctions "``render_<kind>`` in
``vault/render.py`` *or* ``vault/render_<kind>.py``" for exactly this
reason).

:class:`~babylon.projection.briefing.BriefingView` has no honestly-absent
field (see that module's docstring), so — unlike :func:`~babylon.projection.
vault.render.render_county` — this renderer needs no absence-block
resolution pass; every field is always present, and every string is
precomputed here so the template stays a prose-free scaffold reading only
already-``str`` values (matching the county renderer's determinism
discipline).
"""

from __future__ import annotations

from babylon.projection.briefing import BriefingView
from babylon.projection.vault.render import _build_environment

__all__ = ["render_briefing"]


def _statblock_rows(view: BriefingView) -> tuple[tuple[str, str], ...]:
    """Flatten the briefing's identity/coefficient fields to statblock rows.

    :param view: the briefing dossier to walk.
    :returns: ``(label, value)`` pairs, in :class:`BriefingView` declaration
        order (excluding ``kind``/``session_id``/``verified_tick``/
        ``objectives``, which the frontmatter and the pattern sections
        below carry instead).
    """
    return (
        ("codename", view.codename),
        ("horizon_years", str(view.horizon_years)),
        ("horizon_ticks", str(view.horizon_ticks)),
        ("win_objective_id", view.win_objective_id),
    )


def _objective_rows(view: BriefingView) -> tuple[dict[str, str], ...]:
    """Flatten every objective to already-formatted display strings.

    :param view: the briefing dossier to walk.
    :returns: one dict per objective, in :attr:`BriefingView.objectives`
        order (win-condition-first). ``progress`` is formatted to two
        decimal places (frontend parity: ``BriefingRoute.tsx``'s
        ``obj.progress.toFixed(2)``); ``win_badge`` is the literal badge
        text when :attr:`~babylon.projection.briefing.BriefingObjective.
        is_win_condition` holds, else the empty string.
    """
    return tuple(
        {
            "id": objective.id,
            "title": objective.title,
            "description": objective.description,
            "progress": f"{objective.progress:.2f}",
            "status": objective.status,
            "win_badge": "THE WIN CONDITION" if objective.is_win_condition else "",
        }
        for objective in view.objectives
    )


def render_briefing(view: BriefingView) -> str:
    """Render a Scenario Briefing dossier page from a projection view-model.

    Pure function of ``view`` — no wall-clock, no randomness, no filesystem
    reads inside the template (Constitution III.13's determinism contract),
    so two calls with an identical ``view`` yield byte-identical output.

    :param view: the briefing projection to materialize.
    :returns: the rendered Markdown page text.
    :raises jinja2.exceptions.UndefinedError: if the template references a
        field this module does not resolve (a template/model shape drift).
    """
    environment = _build_environment()
    template = environment.get_template("briefing.md.j2")
    return template.render(
        briefing=view,
        statblock_rows=_statblock_rows(view),
        objective_rows=_objective_rows(view),
    )
