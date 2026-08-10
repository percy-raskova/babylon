"""Live trade-dossier markdown rendering (P26 U6 phase 2, Archive client).

Relocated from ``babylon.tui.trade_dossier`` by the Amendment AF (ADR186)
deletion ceremony: this module was always pure projection-to-markdown
formatting with no rendering-technology dependency (no Rich, no terminal
theme) — unlike its ``babylon.tui`` siblings ``chronicle``/
``chronicle_salience`` (split at the same ceremony into a durable data half
and a deleted Rich-rendering half), the whole module survives unchanged.

Renders a :class:`~babylon.projection.view_models.TradeBlocView` (the
national overview, or one external bloc) into the same
``{statblock}``/``{absence}`` fenced-directive markdown shape the vault's
baked pages use (:mod:`babylon.projection.vault.render`'s own convention:
``_statblock_rows``/``_absent_fields``/the "Verb(Noun) to <goal>" remedy
register), so the client's own fenced-directive renderer renders it
identically to a real vault page.

This module deliberately does NOT touch :mod:`babylon.projection.vault` —
baking trade pages into the *persisted* vault estate is explicitly deferred
(contract: ``specs/103-trade-surfaces/u6-archive-trade-surfaces-
contracts.md`` Contract 2 — "lands with a declared §6.5 ceremony alongside
U5's content, not as a phase-1 side effect"; still true in phase 2, nothing
in Contract 3 lifts it). Instead, :meth:`~babylon.game.session.GameSession.
read_page` calls :func:`render_trade_page` FRESH on every call — the same
"compute fresh, never cache" posture :meth:`~babylon.game.session.
GameSession.dashboard_view`/:meth:`~babylon.game.session.GameSession.
subject_view` already use, just wearing a markdown-page hat instead of a
view-model one.

Pure, deterministic formatting only — no wall-clock, no randomness, no I/O
(mirrors :mod:`babylon.projection.chronicle`/:mod:`babylon.projection.
chronicle_salience`'s own established "``babylon.game`` imports a pure
projection formatter" precedent).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from babylon.projection.view_models import TradeBlocView

__all__ = ["render_trade_page"]

_OVERVIEW_ID: Final = "overview"

#: Fields every ``TradeBlocView`` carries by construction whenever the view
#: resolves at all — walked defensively anyway (never trusting an upstream
#: invariant this module cannot itself verify), so an unexpectedly-``None``
#: reading still renders an honest absence rather than a Jinja-style
#: ``"None"`` string or a crash.
_SCALAR_FIELD_ORDER: Final[tuple[str, ...]] = (
    "phi_year_inflow",
    "phi_week_slice",
    "bilateral_trade_value",
    "bilateral_trade_tons",
    "erdi_ratio",
    "last_tick_flow",
)

#: Remedy verb for each optional ``TradeBlocView`` field, in the same
#: "Verb(Noun) to <goal>" register ``babylon.projection.vault.render``'s own
#: ``_REMEDY_BY_FIELD``/``_SOVEREIGN_REMEDY_BY_FIELD`` established for
#: county/sovereign pages. Keyed by field name so a field added to
#: ``TradeBlocView`` without a registered remedy fails loudly in
#: :func:`_absent_scalar_rows` rather than silently rendering no block.
_REMEDY_BY_FIELD: Final[dict[str, str]] = {
    "phi_year_inflow": "Wire(Trade) to attribute the bloc's annual Φ inflow",
    "phi_week_slice": "Wire(Trade) to attribute the bloc's weekly Φ slice",
    "bilateral_trade_value": (
        "Attribute(BilateralTrade) to attribute annual bilateral trade value (post-U3)"
    ),
    "bilateral_trade_tons": (
        "Attribute(FreightTons) to attribute annual freight tons (U3 FAF coverage window)"
    ),
    "erdi_ratio": "Compute(ERDI) to attribute the bloc's exchange-rate-deviation-index ratio",
    "last_tick_flow": "Advance(Tick) to record this tick's DRAIN_EDGE flow",
    "exposure_top": "Wire(CountyExposure) to attribute county exposure shares",
    "breakdown": "Wire(TradeBlocs) to attribute per-bloc Φ shares",
}


def _format_scalar(value: float) -> str:
    """Format one leaf numeric value: six decimals, the vault renderer's
    stable textual form (:func:`babylon.projection.vault.render.
    _statblock_rows`'s own convention, mirrored here for parity)."""
    return f"{value:.6f}"


def _statblock_rows(view: TradeBlocView) -> list[tuple[str, str]]:
    """Resolve every present scalar field of ``view`` into a statblock row.

    :param view: the trade dossier to walk.
    :returns: ``(label, value)`` pairs in :data:`_SCALAR_FIELD_ORDER`.
    """
    rows: list[tuple[str, str]] = []
    for name in _SCALAR_FIELD_ORDER:
        value = getattr(view, name)
        if value is not None:
            rows.append((name, _format_scalar(value)))
    return rows


def _absent_scalar_fields(view: TradeBlocView) -> list[tuple[str, str]]:
    """Resolve every absent scalar field of ``view`` into a named remedy entry.

    :param view: the trade dossier to walk.
    :returns: ``(field_name, remedy)`` pairs for each ``None`` scalar field.
    :raises KeyError: if an absent field has no entry in
        :data:`_REMEDY_BY_FIELD` — a loud failure, never a silently-skipped
        absence block (Constitution III.11).
    """
    entries: list[tuple[str, str]] = []
    for name in _SCALAR_FIELD_ORDER:
        if getattr(view, name) is not None:
            continue
        try:
            remedy = _REMEDY_BY_FIELD[name]
        except KeyError as exc:
            msg = f"no remedy text registered for absent TradeBlocView field {name!r}"
            raise KeyError(msg) from exc
        entries.append((name, remedy))
    return entries


def _statblock_fence(subject: str, rows: list[tuple[str, str]]) -> str:
    body = "".join(f"{label}: {value}\n" for label, value in rows)
    return f"```{{statblock}} {subject}\n{body}```\n"


def _absence_fence(field: str, remedy: str) -> str:
    return f"```{{absence}} {field} — {remedy}\n```\n"


def _breakdown_section(view: TradeBlocView) -> str:
    """The overview-only "per-bloc breakdown" table (Φ DESC — already the
    order :func:`~babylon.projection.trade.project_trade_overview` sorted
    ``breakdown`` into; this section only formats it).

    :param view: the national overview dossier (``node_id == "overview"``).
    :returns: a markdown ``##`` section: a table when ``breakdown`` is
        populated, an honest ``{absence}`` block otherwise.
    """
    lines = ["## Per-bloc breakdown (Φ DESC)", ""]
    if view.breakdown is None:
        lines.append(_absence_fence("breakdown", _REMEDY_BY_FIELD["breakdown"]))
        return "\n".join(lines) + "\n"
    lines.append("| bloc | phi_year_inflow |")
    lines.append("| --- | --- |")
    for share in view.breakdown:
        lines.append(f"| [[trade/{share.node_id}]] | {_format_scalar(share.phi_year_inflow)} |")
    return "\n".join(lines) + "\n"


def _exposure_section(view: TradeBlocView) -> str:
    """The per-bloc-only "top county exposure" table (weight DESC, FIPS ASC
    — already the order :func:`~babylon.projection.trade.project_trade_bloc`
    sorted ``exposure_top`` into).

    :param view: one external bloc's dossier (``node_id != "overview"``).
    :returns: a markdown ``##`` section: a table when ``exposure_top`` is
        populated, an honest ``{absence}`` block otherwise.
    """
    lines = ["## Top county exposure", ""]
    if view.exposure_top is None:
        lines.append(_absence_fence("exposure_top", _REMEDY_BY_FIELD["exposure_top"]))
        return "\n".join(lines) + "\n"
    lines.append("| county_fips | weight |")
    lines.append("| --- | --- |")
    for share in view.exposure_top:
        lines.append(f"| {share.county_fips} | {_format_scalar(share.weight)} |")
    return "\n".join(lines) + "\n"


def render_trade_page(view: TradeBlocView) -> str:
    """Render one trade dossier — the national overview or one bloc — as markdown.

    Pure function of ``view`` — no wall-clock, no randomness, no I/O — so
    two calls with an equal ``view`` yield byte-identical output, the same
    determinism contract :func:`babylon.projection.vault.render.
    render_county` documents for the (frozen, untouched-by-this-module)
    baked vault path.

    :param view: the trade projection to materialize (``node_id ==
        "overview"`` for the national fold, else one external bloc's id).
    :returns: the rendered Markdown page text.
    """
    subject = f"trade/{view.node_id}"
    is_overview = view.node_id == _OVERVIEW_ID
    title = "National Trade Overview" if is_overview else f"Bloc Dossier — {view.node_id}"

    parts = [
        "---\n"
        f"id: {subject}\n"
        f"name: Trade — {view.node_id}\n"
        f"verified_tick: {view.verified_tick}\n"
        f"staleness: verified as of tick {view.verified_tick} — always regenerable, "
        "never authoritative\n"
        "---\n",
        f"# {subject} — {title}\n",
        _statblock_fence(subject, _statblock_rows(view)),
    ]
    for field, remedy in _absent_scalar_fields(view):
        parts.append(_absence_fence(field, remedy))

    if is_overview:
        parts.append(_breakdown_section(view))
    else:
        parts.append(_exposure_section(view))
        parts.append(f"Back to [[trade/{_OVERVIEW_ID}]].\n")

    return "\n".join(parts)
