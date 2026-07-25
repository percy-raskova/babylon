"""Sandboxed deterministic economy-page rendering (Constitution III.13).

Mirrors :mod:`babylon.projection.vault.render`'s county pipeline exactly —
same :class:`~jinja2.sandbox.ImmutableSandboxedEnvironment` construction (no
custom filters/globals/finalizers, templates loaded only from this package's
own ``templates/`` directory, :class:`~jinja2.StrictUndefined`), same
precompute-then-hand-to-template discipline for
:class:`~babylon.projection.view_models.EconomyView`'s ``Optional`` fields
(Jinja renders a defined-but-``None`` attribute as the literal text
``"None"`` rather than raising, so the template never dereferences an
``Optional`` field directly).

``class_phi_readings`` (a tuple of :class:`~babylon.projection.view_models.
ClassPhiReadingView`) is rendered as its own section, exactly like
:mod:`~babylon.projection.vault.render_community`'s ``roster``/``overlaps``
— a collection is not flattened into dotted statblock rows the way the
scalar-composite fields (:class:`~babylon.projection.view_models.
ClassComposition`) are.

Lives in its own module rather than appending to ``render.py``, matching
the sanctioned per-kind pattern (``render_national.py``, ``render_
community.py``, ...): that module's helper names are all County-shaped, and
a dedicated module per kind keeps each WO's diff collision-free.

jinja2 is imported lazily (function-local), matching ``render.py``, so
importing this module never pulls jinja2 into ``sys.modules`` merely by
being on the import path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from babylon.projection.view_models import EconomyView

if TYPE_CHECKING:
    from jinja2.sandbox import ImmutableSandboxedEnvironment

#: EconomyView fields that are always present (identity/provenance) — every
#: other declared field is walked for statblock/absence resolution.
_IDENTITY_FIELDS: Final[frozenset[str]] = frozenset({"kind", "economy_id", "verified_tick"})

#: ``class_phi_readings`` is a collection, rendered as its own section (see
#: :func:`_class_phi_rows`) — excluded from the generic scalar statblock walk
#: the same way ``render_community.py`` excludes ``roster``/``overlaps``.
_COLLECTION_FIELDS: Final[frozenset[str]] = frozenset({"class_phi_readings"})

#: Remedy text for each optional EconomyView field, in the "Verb(Noun) to
#: <goal>" register the county spike established for {absence} blocks.
#: ``energy_beta_j`` deliberately breaks that register — no verb can ever
#: resolve it (there is no producer to invoke, not merely one this run
#: didn't attribute; the same reasoning ``render_community.py``'s
#: ``formation_tick`` entry documents). Keyed by the exact EconomyView field
#: name so a field added without a remedy entry fails loudly in
#: :func:`_absent_fields` rather than silently rendering no block.
_REMEDY_BY_FIELD: Final[dict[str, str]] = {
    "wage_balance": "Step(OppositionRegistry) to attribute the wage opposition's Balance",
    "labor_aristocracy_verdict": (
        "Step(OppositionRegistry) to attribute the wage opposition's Balance"
    ),
    "class_phi_readings": "Wire(FundamentalTheorem) to attribute per-class Φ readings",
    "phi_unequal_exchange": (
        "Meter(GammaBasket) + Track(Consumption) to attribute Φ_unequal_exchange "
        "(genuinely absent tree-wide — no producer publishes either input)"
    ),
    "phi_reproduction": (
        "Meter(ReproductionSubsidy) to attribute Φ_reproduction (genuinely absent "
        "tree-wide — no producer publishes p_g2_labor_value or wage_paid_for_d_g2)"
    ),
    "phi_domestic": (
        "Meter(DomesticLabor) to attribute Φ_domestic (genuinely absent tree-wide "
        "— no producer publishes unpaid reproductive labor-hours, though national "
        "MELT τ is itself live)"
    ),
    "phi_iii_report": (
        "Meter(GammaIII) to attribute the Φ_III report term (genuinely absent tree-wide)"
    ),
    "phi_decomposition_total": (
        "Meter(GammaBasket) + Meter(ReproductionSubsidy) + Meter(DomesticLabor) to "
        "attribute all three Φ conservation components"
    ),
    "surplus_produced": "Distribute(Surplus) to attribute the territory-wide split",
    "profit_of_enterprise": "Distribute(Surplus) to attribute the territory-wide split",
    "interest_burden": "Distribute(Surplus) to attribute the territory-wide split",
    "ground_rent": "Distribute(Surplus) to attribute the territory-wide split",
    "taxes_on_surplus": "Distribute(Surplus) to attribute the territory-wide split",
    "rentier_share": "Distribute(Surplus) to attribute the territory-wide split",
    "financialization_share": "Distribute(Surplus) to attribute the territory-wide split",
    "total_consumption": "Survey(Territory) to attribute consumption nationwide",
    "total_biocapacity": "Survey(Territory) to attribute biocapacity nationwide",
    "overshoot_ratio": "Survey(Territory) to attribute biocapacity nationwide",
    "biocapacity_ceiling": "Survey(Territory) to attribute biocapacity nationwide",
    "energy_beta_j": (
        "no producer exists — the energy vertex β_J is genuinely absent tree-wide "
        "(no EROI/joule/power-density accounting anywhere in the engine); wire the "
        "energy split first (see EconomyView docstring)"
    ),
}


def _optional_field_names() -> tuple[str, ...]:
    """Return EconomyView's optional (non-identity) field names, in declared order.

    :returns: field names in :class:`~babylon.projection.view_models.
        EconomyView` declaration order, excluding the always-present
        identity fields.
    """
    return tuple(name for name in EconomyView.model_fields if name not in _IDENTITY_FIELDS)


def _statblock_rows(view: EconomyView) -> tuple[tuple[str, str], ...]:
    """Resolve every present scalar field of ``view`` into a statblock row.

    ``class_phi_readings`` is skipped here (see :func:`_class_phi_rows`);
    every remaining optional field is either a ``float`` (formatted to six
    decimal places, matching the county/national convention) or a ``bool``
    (formatted via ``str``).

    :param view: the economy projection to walk.
    :returns: ``(label, value)`` pairs in EconomyView declaration order.
    """
    rows: list[tuple[str, str]] = []
    for name in _optional_field_names():
        if name in _COLLECTION_FIELDS:
            continue
        value = getattr(view, name)
        if value is None:
            continue
        if isinstance(value, bool):
            rows.append((name, str(value)))
        else:
            rows.append((name, f"{value:.6f}"))
    return tuple(rows)


def _class_phi_rows(view: EconomyView) -> tuple[str, ...]:
    """Format each class/county Φ reading as one line, for its own section.

    Sub-fields that are honestly absent within a *present* reading (a class
    with ``v_produced <= 0`` carries no ``phi_relative``/
    ``labor_aristocracy_ratio``/``is_labor_aristocracy``) render as ``n/a``
    — a deliberate, controlled literal chosen precisely so the page never
    carries the bare text ``"None"``.

    :param view: the economy projection to walk.
    :returns: one formatted line per reading in ``class_phi_readings``
        (already sorted by ``entity_id`` at project time), or empty when
        ``class_phi_readings`` is ``None`` or an attributed-but-empty tuple.
    """
    if not view.class_phi_readings:
        return ()
    lines: list[str] = []
    for reading in view.class_phi_readings:
        relative = "n/a" if reading.phi_relative is None else f"{reading.phi_relative:.6f}"
        ratio = (
            "n/a"
            if reading.labor_aristocracy_ratio is None
            else f"{reading.labor_aristocracy_ratio:.6f}"
        )
        aristocracy = (
            "n/a" if reading.is_labor_aristocracy is None else str(reading.is_labor_aristocracy)
        )
        lines.append(
            f"{reading.entity_id}: w_paid={reading.w_paid:.6f} v_produced={reading.v_produced:.6f} "
            f"phi_absolute={reading.phi_absolute:.6f} phi_relative={relative} "
            f"labor_aristocracy_ratio={ratio} is_labor_aristocracy={aristocracy}"
        )
    return tuple(lines)


def _surplus_identity_line(view: EconomyView) -> str | None:
    """Format the ``s = p + i + r + t`` conservation identity, numbers filled in.

    :param view: the economy projection to walk.
    :returns: the formatted identity line, or ``None`` when any one of the
        four surplus-split terms is absent (they are always co-present with
        ``surplus_produced`` by construction — see
        :func:`babylon.projection.economy._surplus_split`'s single presence
        gate — but each is checked independently here defensively).
    """
    if (
        view.surplus_produced is None
        or view.profit_of_enterprise is None
        or view.interest_burden is None
        or view.ground_rent is None
        or view.taxes_on_surplus is None
    ):
        return None
    return (
        f"s = p + i + r + t  →  {view.surplus_produced:.6f} = "
        f"{view.profit_of_enterprise:.6f} + {view.interest_burden:.6f} + "
        f"{view.ground_rent:.6f} + {view.taxes_on_surplus:.6f}"
    )


def _absent_fields(view: EconomyView) -> tuple[tuple[str, str], ...]:
    """Resolve every ``None`` field of ``view`` into a named remedy entry.

    An attributed-but-empty ``class_phi_readings`` (``()``, not ``None``) is
    NOT absent — "computed and found none" is a real, different fact from
    "not computed" (mirrors ``CommunityView``'s ``roster``/``overlaps``
    discipline).

    :param view: the economy projection to walk.
    :returns: ``(field_name, remedy)`` pairs, one per ``None`` optional
        field, in EconomyView declaration order.
    :raises KeyError: if an absent field has no entry in
        :data:`_REMEDY_BY_FIELD` — an EconomyView field added without a
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
            msg = f"no remedy text registered for absent EconomyView field {field_name!r}"
            raise KeyError(msg) from exc
        entries.append((field_name, remedy))
    return tuple(entries)


def _build_environment() -> ImmutableSandboxedEnvironment:
    """Construct the vault's Jinja2 environment.

    Identical construction to :func:`babylon.projection.vault.render._build_environment`
    (ADR099: construction is code, never data) — duplicated rather than
    imported so this module has zero dependency on ``render.py``'s
    County-shaped internals, matching ``render_community.py``'s precedent.

    :returns: a sandboxed environment with StrictUndefined, autoescape off
        (the output is Markdown, not HTML), and templates resolved from this
        package's ``templates/`` directory only.
    """
    from jinja2 import PackageLoader, StrictUndefined
    from jinja2.sandbox import ImmutableSandboxedEnvironment

    return ImmutableSandboxedEnvironment(
        loader=PackageLoader("babylon.projection.vault", "templates"),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )


def render_economy(view: EconomyView, *, verified_tick: int) -> str:
    """Render an economy dossier page from a projection view-model.

    Pure function of ``(view, verified_tick)`` — no wall-clock, no
    randomness, no filesystem reads inside the template — so two calls with
    identical arguments yield byte-identical output (Constitution III.13's
    determinism contract).

    :param view: the economy projection to materialize.
    :param verified_tick: the tick stamped into the page's frontmatter as
        its staleness anchor. Passed explicitly rather than read from
        ``view.verified_tick`` so the caller (the materializer) declares
        the bake tick once and unambiguously.
    :returns: the rendered Markdown page text.
    :raises jinja2.exceptions.UndefinedError: if the template references a
        field this module does not resolve (a template/model shape drift).
    """
    environment = _build_environment()
    template = environment.get_template("economy.md.j2")
    return template.render(
        economy=view,
        verified_tick=verified_tick,
        statblock_rows=_statblock_rows(view),
        class_phi_rows=_class_phi_rows(view),
        surplus_identity_line=_surplus_identity_line(view),
        absent_fields=_absent_fields(view),
    )


__all__ = ["render_economy"]
