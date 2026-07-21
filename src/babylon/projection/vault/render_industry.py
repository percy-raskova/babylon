"""Sandboxed deterministic industry-page rendering (Constitution III.13).

Mirrors :mod:`babylon.projection.vault.render` exactly, reusing its
:func:`~babylon.projection.vault.render._build_environment` factory (one
sandboxed Jinja2 environment for the whole vault package — construction is
code, never data, ADR099) rather than duplicating it. A separate module
(not a new function inside ``render.py``) so parallel Lane-P work orders
never collide on the same file — WO-16's note that ``render_<kind>`` may
live "in ``vault/render.py`` (or ``vault/render_state.py``)" is exercised
here as the latter.

See :mod:`babylon.projection.vault.render` for the shared rationale: a
present-but-``None`` :class:`~babylon.projection.view_models.IndustryView`
field renders as the literal text ``"None"`` unless pre-resolved, so this
module walks the view once into ``statblock_rows``/``absent_fields`` and
hands the template only those already-``str`` structures.
"""

from __future__ import annotations

from typing import Final

from babylon.projection.vault.render import _build_environment
from babylon.projection.view_models import DepartmentComposition, IndustryView

#: IndustryView fields that are always present (identity/provenance) — every
#: other declared field is walked for statblock/absence resolution.
_IDENTITY_FIELDS: Final[frozenset[str]] = frozenset({"kind", "industry_id", "verified_tick"})

#: Remedy verb for each optional IndustryView field, in the "Verb(Noun) to
#: <goal>" register the spike established for {absence} blocks. Keyed by the
#: exact IndustryView field name so a field added without a remedy entry
#: fails loudly in :func:`_absent_fields` rather than silently rendering no
#: block.
_REMEDY_BY_FIELD: Final[dict[str, str]] = {
    "naics_2digit": "Classify(Industry) to attribute its 2-digit NAICS code",
    "naics_label": "Classify(Industry) to attribute its sector label",
    "total_employment": "Survey(Workforce) to attribute total employment",
    "total_wages": "Assess(LaborMarket) to attribute total wages (variable capital v)",
    "profit_rate": "Audit(ProfitRate) to attribute the BEA/QCEW-derived profit rate",
    "occ": "Audit(OrganicComposition) to attribute the sector's c/v ratio",
    "department_weights": "Allocate(Departments) to attribute the Vol II department split",
    "member_business_count": "Survey(Membership) to attribute member businesses",
    "member_worker_block_count": "Survey(Membership) to attribute member worker blocks",
    "county_fips": "Locate(Industry) to attribute the counties it spans",
}


def _optional_field_names() -> tuple[str, ...]:
    """Return IndustryView's optional (non-identity) field names, in declared order.

    :returns: field names in
        :class:`~babylon.projection.view_models.IndustryView` declaration
        order, excluding the always-present identity fields.
    """
    return tuple(name for name in IndustryView.model_fields if name not in _IDENTITY_FIELDS)


def _statblock_rows(view: IndustryView) -> tuple[tuple[str, str], ...]:
    """Resolve every present field of ``view`` into a formatted statblock row.

    :class:`~babylon.projection.view_models.DepartmentComposition` flattens
    into one dotted row per department; scalars format floats to six decimal
    places for a stable, deterministic textual form.

    :param view: the industry projection to walk.
    :returns: ``(label, value)`` pairs in IndustryView declaration order.
    """
    rows: list[tuple[str, str]] = []
    if view.naics_2digit is not None:
        rows.append(("naics_2digit", view.naics_2digit))
    if view.naics_label is not None:
        rows.append(("naics_label", view.naics_label))
    if view.total_employment is not None:
        rows.append(("total_employment", str(view.total_employment)))
    if view.total_wages is not None:
        rows.append(("total_wages", f"{view.total_wages:.6f}"))
    if view.profit_rate is not None:
        rows.append(("profit_rate", f"{view.profit_rate:.6f}"))
    if view.occ is not None:
        rows.append(("occ", f"{view.occ:.6f}"))
    if view.department_weights is not None:
        for field_name in DepartmentComposition.model_fields:
            value = getattr(view.department_weights, field_name)
            rows.append((f"department_weights.{field_name}", f"{value:.6f}"))
    if view.member_business_count is not None:
        rows.append(("member_business_count", str(view.member_business_count)))
    if view.member_worker_block_count is not None:
        rows.append(("member_worker_block_count", str(view.member_worker_block_count)))
    if view.county_fips is not None:
        rows.append(("county_fips", ", ".join(view.county_fips)))
    return tuple(rows)


def _absent_fields(view: IndustryView) -> tuple[tuple[str, str], ...]:
    """Resolve every ``None`` field of ``view`` into a named remedy entry.

    :param view: the industry projection to walk.
    :returns: ``(field_name, remedy)`` pairs, one per absent optional field,
        in IndustryView declaration order.
    :raises KeyError: if an absent field has no entry in
        :data:`_REMEDY_BY_FIELD` — an IndustryView field added without a
        registered remedy is a loud failure, never a silently-skipped
        absence block.
    """
    entries: list[tuple[str, str]] = []
    for field_name in _optional_field_names():
        if getattr(view, field_name) is not None:
            continue
        try:
            remedy = _REMEDY_BY_FIELD[field_name]
        except KeyError as exc:
            msg = f"no remedy text registered for absent IndustryView field {field_name!r}"
            raise KeyError(msg) from exc
        entries.append((field_name, remedy))
    return tuple(entries)


def render_industry(view: IndustryView, *, verified_tick: int) -> str:
    """Render an industry dossier page from a projection view-model.

    Pure function of ``(view, verified_tick)`` — no wall-clock, no
    randomness, no filesystem reads inside the template — so two calls with
    identical arguments yield byte-identical output (Constitution III.13's
    determinism contract).

    :param view: the industry projection to materialize.
    :param verified_tick: the tick stamped into the page's frontmatter as
        its staleness anchor. Passed explicitly rather than read from
        ``view.verified_tick`` so the caller (the materializer) declares
        the bake tick once and unambiguously.
    :returns: the rendered Markdown page text.
    :raises jinja2.exceptions.UndefinedError: if the template references a
        field this module does not resolve (a template/model shape drift).
    """
    environment = _build_environment()
    template = environment.get_template("industry.md.j2")
    return template.render(
        industry=view,
        verified_tick=verified_tick,
        statblock_rows=_statblock_rows(view),
        absent_fields=_absent_fields(view),
    )


__all__ = ["render_industry"]
