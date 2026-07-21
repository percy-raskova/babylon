"""Sandboxed deterministic national-page rendering (Constitution III.13).

Mirrors :mod:`babylon.projection.vault.render`'s county renderer exactly,
reusing its :func:`~babylon.projection.vault.render._build_environment`
factory rather than constructing a second sandboxed Jinja2 environment — that
module's own docstring names itself "the *only* place the environment is
built," so a national-specific environment would violate that single-source
contract for no benefit (the sandbox/``StrictUndefined`` behavior is
kind-agnostic).

As with the county renderer: a present-but-``None``
:class:`~babylon.projection.view_models.NationalView` field is walked once
here into precomputed ``str`` statblock rows and absence blocks, so the
template only ever touches those and the always-present identity fields
(``national_id``, ``verified_tick``, ``imperial_rent_pool`` — see
:class:`~babylon.projection.view_models.NationalView`'s docstring for why the
Gas Tank stock is never withheld) — never a raw ``Optional`` field Jinja
could render as the literal text ``"None"``.
"""

from __future__ import annotations

from typing import Final

from babylon.projection.vault.render import _build_environment
from babylon.projection.view_models import ClassComposition, ConsciousnessSimplex, NationalView

#: NationalView fields that are always present (identity/provenance, plus the
#: always-materialized ``imperial_rent_pool``) — every other declared field
#: is walked for statblock/absence resolution.
_IDENTITY_FIELDS: Final[frozenset[str]] = frozenset(
    {"kind", "national_id", "verified_tick", "imperial_rent_pool"}
)

#: Remedy verb for each optional NationalView field, in the same "Verb(Noun)
#: to <goal>" register :mod:`babylon.projection.vault.render` established.
#: Keyed by the exact NationalView field name so a field added without a
#: remedy entry fails loudly in :func:`_absent_fields` rather than silently
#: rendering no block. The six value-composition fields share one remedy —
#: they share one producer (the ``v_national_value_aggregate`` row).
_REMEDY_BY_FIELD: Final[dict[str, str]] = {
    "population": "Survey(Territory) to attribute population nationwide",
    "class_composition": "Census(Territory) to attribute class shares nationwide",
    "median_wage": "Assess(LaborMarket) to attribute median wage nationwide",
    "consciousness": "Poll(Consciousness) to attribute the ternary simplex nationwide",
    "legitimacy": "Survey(Legitimation) to attribute the legitimacy index nationwide",
    "p_acquiescence": "Assess(SurvivalCalculus) to attribute P(S|A) nationwide",
    "p_revolution": "Assess(SurvivalCalculus) to attribute P(S|R) nationwide",
    "bifurcation_score": "Observe(Bifurcation) to attribute the axis nationwide",
    "sovereign_id": "Claim(Sovereignty) to attribute a single national CLAIMS edge",
    "c_sum": "Query(v_national_value_aggregate) to read c_sum",
    "v_sum": "Query(v_national_value_aggregate) to read v_sum",
    "s_sum": "Query(v_national_value_aggregate) to read s_sum",
    "k_sum": "Query(v_national_value_aggregate) to read k_sum",
    "biocapacity_sum": "Query(v_national_value_aggregate) to read biocapacity_sum",
    "hex_count": "Query(v_national_value_aggregate) to read hex_count",
}


def _optional_field_names() -> tuple[str, ...]:
    """Return NationalView's optional (non-identity) field names, in declared order.

    :returns: field names in :class:`~babylon.projection.view_models.
        NationalView` declaration order, excluding :data:`_IDENTITY_FIELDS`.
    """
    return tuple(name for name in NationalView.model_fields if name not in _IDENTITY_FIELDS)


#: NationalView optional scalar fields formatted as six-decimal floats — every
#: optional field except the two composites (:class:`ClassComposition`,
#: :class:`ConsciousnessSimplex`, handled separately below) and the two
#: non-float scalars (``sovereign_id`` is a string, ``hex_count`` an int).
_FLOAT_SCALAR_FIELDS: Final[tuple[str, ...]] = (
    "median_wage",
    "legitimacy",
    "p_acquiescence",
    "p_revolution",
    "bifurcation_score",
    "c_sum",
    "v_sum",
    "s_sum",
    "k_sum",
    "biocapacity_sum",
)


def _composite_rows(view: NationalView) -> list[tuple[str, str]]:
    """Flatten ``class_composition``/``consciousness`` into dotted sub-rows.

    :param view: the national projection to walk.
    :returns: one ``(label, value)`` row per present sub-field, in
        declaration order.
    """
    rows: list[tuple[str, str]] = []
    if view.class_composition is not None:
        for field_name in ClassComposition.model_fields:
            value = getattr(view.class_composition, field_name)
            rows.append((f"class_composition.{field_name}", f"{value:.6f}"))
    if view.consciousness is not None:
        for field_name in ConsciousnessSimplex.model_fields:
            value = getattr(view.consciousness, field_name)
            rows.append((f"consciousness.{field_name}", f"{value:.6f}"))
    return rows


def national_statblock_rows(view: NationalView) -> tuple[tuple[str, str], ...]:
    """Resolve every present field of ``view`` into a formatted statblock row.

    Public (unlike :mod:`babylon.projection.vault.render`'s county
    equivalent) so :mod:`babylon.projection.national`'s live statblock
    provider can reuse it without a leading-underscore cross-module import.

    Composite fields (:class:`ClassComposition`,
    :class:`ConsciousnessSimplex`) flatten into one dotted row per sub-field;
    scalars format floats to six decimal places for a stable, deterministic
    textual form — the same convention the county renderer uses.

    :param view: the national projection to walk.
    :returns: ``(label, value)`` pairs in NationalView declaration order.
    """
    rows: list[tuple[str, str]] = []
    if view.population is not None:
        rows.append(("population", str(view.population)))
    rows.extend(_composite_rows(view))
    for field_name in _FLOAT_SCALAR_FIELDS:
        value = getattr(view, field_name)
        if value is not None:
            rows.append((field_name, f"{value:.6f}"))
    if view.sovereign_id is not None:
        rows.append(("sovereign_id", view.sovereign_id))
    if view.hex_count is not None:
        rows.append(("hex_count", str(view.hex_count)))
    return tuple(rows)


def _absent_fields(view: NationalView) -> tuple[tuple[str, str], ...]:
    """Resolve every ``None`` field of ``view`` into a named remedy entry.

    :param view: the national projection to walk.
    :returns: ``(field_name, remedy)`` pairs, one per absent optional field,
        in NationalView declaration order.
    :raises KeyError: if an absent field has no entry in
        :data:`_REMEDY_BY_FIELD` — a NationalView field added without a
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
            msg = f"no remedy text registered for absent NationalView field {field_name!r}"
            raise KeyError(msg) from exc
        entries.append((field_name, remedy))
    return tuple(entries)


def render_national(view: NationalView, *, verified_tick: int) -> str:
    """Render a national dossier page from a projection view-model.

    Pure function of ``(view, verified_tick)`` — no wall-clock, no
    randomness, no filesystem reads inside the template — so two calls with
    identical arguments yield byte-identical output (Constitution III.13's
    determinism contract).

    :param view: the national projection to materialize.
    :param verified_tick: the tick stamped into the page's frontmatter as
        its staleness anchor. Passed explicitly rather than read from
        ``view.verified_tick`` so the caller (the materializer) declares
        the bake tick once and unambiguously.
    :returns: the rendered Markdown page text.
    :raises jinja2.exceptions.UndefinedError: if the template references a
        field this module does not resolve (a template/model shape drift).
    """
    environment = _build_environment()
    template = environment.get_template("national.md.j2")
    return template.render(
        national=view,
        verified_tick=verified_tick,
        imperial_rent_pool=f"{view.imperial_rent_pool:.6f}",
        statblock_rows=national_statblock_rows(view),
        absent_fields=_absent_fields(view),
    )


__all__ = ["national_statblock_rows", "render_national"]
