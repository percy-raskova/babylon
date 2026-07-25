"""Sandboxed deterministic field-state-page rendering (Constitution III.13).

Mirrors :mod:`babylon.projection.vault.render`'s county pipeline exactly —
same :class:`~jinja2.sandbox.ImmutableSandboxedEnvironment` construction (no
custom filters/globals/finalizers, templates loaded only from this package's
own ``templates/`` directory, :class:`~jinja2.StrictUndefined`), same
precompute-then-hand-to-template discipline for
:class:`~babylon.projection.view_models.FieldStateView`'s ``Optional``
fields (Jinja renders a defined-but-``None`` attribute as the literal text
``"None"`` rather than raising, so the template never dereferences an
``Optional`` field directly).

``principal_field``/``dialectical_regime`` and each node's ``fields``/
``laplacian``/``df_dt``/``fascist_alignment`` readings render as dotted
statblock rows keyed by class id (small N — a handful of social classes
per run) — unlike :mod:`~babylon.projection.vault.render_economy`'s
``class_phi_readings``, this collection is shallow enough that flattening it
into the statblock (matching :mod:`~babylon.projection.national`'s
``class_composition.<field>``/``consciousness.<field>`` nesting convention)
reads better than a dedicated prose section. ``edges`` gets its own section
instead — a gradient reading names TWO subjects (source/target), which a
single-subject statblock row cannot express.

Lives in its own module rather than appending to ``render.py``, matching
the sanctioned per-kind pattern (``render_national.py``, ``render_
economy.py``, ...): a dedicated module per kind keeps each unit's diff
collision-free.

jinja2 is imported lazily (function-local), matching ``render.py``, so
importing this module never pulls jinja2 into ``sys.modules`` merely by
being on the import path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from babylon.projection.view_models import FieldStateView

if TYPE_CHECKING:
    from jinja2.sandbox import ImmutableSandboxedEnvironment

#: FieldStateView fields that are always present (identity/provenance) —
#: every other declared field is walked for statblock/absence resolution.
_IDENTITY_FIELDS: Final[frozenset[str]] = frozenset({"kind", "field_state_id", "verified_tick"})

#: Remedy text for each optional FieldStateView field, in the "Verb(Noun) to
#: <goal>" register the county spike established for {absence} blocks.
#: Keyed by the exact FieldStateView field name so a field added without a
#: remedy entry fails loudly in :func:`_absent_fields` rather than silently
#: rendering no block.
_REMEDY_BY_FIELD: Final[dict[str, str]] = {
    "nodes": "Step(ContradictionFieldSystem) to attribute per-class field readings",
    "edges": "Step(FieldDerivativeSystem) to attribute field gradients",
    "principal_field": "Step(FieldDerivativeSystem) to identify the principal field",
    "dialectical_regime": "Step(ContradictionSystem) to classify the dialectical regime",
}


def _optional_field_names() -> tuple[str, ...]:
    """Return FieldStateView's optional (non-identity) field names, in declared order.

    :returns: field names in :class:`~babylon.projection.view_models.
        FieldStateView` declaration order, excluding the always-present
        identity fields.
    """
    return tuple(name for name in FieldStateView.model_fields if name not in _IDENTITY_FIELDS)


def _statblock_rows(view: FieldStateView) -> tuple[tuple[str, str], ...]:
    """Resolve principal_field/dialectical_regime/per-node readings into rows.

    A present-but-``None`` sub-field (``principal_field.field_name`` before
    any principal is identified) renders as the deliberate, controlled
    literal ``"n/a"`` — never the bare text ``"None"`` — the same convention
    :mod:`~babylon.projection.vault.render_economy`'s per-class Φ rows use.

    :param view: the field-state projection to walk.
    :returns: ``(label, value)`` pairs: principal_field's three sub-fields,
        dialectical_regime's three sub-fields, then each node's name/
        fields.*/laplacian.*/df_dt.*/fascist_alignment, in that order.
    """
    rows: list[tuple[str, str]] = []

    principal = view.principal_field
    if principal is not None:
        field_name = "n/a" if principal.field_name is None else principal.field_name
        rows.append(("principal_field.field_name", field_name))
        rows.append(("principal_field.max_abs_df_dt", f"{principal.max_abs_df_dt:.6f}"))
        rows.append(("principal_field.changed", str(principal.changed)))

    regime = view.dialectical_regime
    if regime is not None:
        rows.append(("dialectical_regime.regime", regime.regime))
        rows.append(("dialectical_regime.opposition", regime.opposition))
        rows.append(("dialectical_regime.rate", f"{regime.rate:.6f}"))

    for node in view.nodes or ():
        rows.append((f"node.{node.node_id}.name", node.name))
        node_fields = node.fields or {}
        for field_name in sorted(node_fields):
            rows.append(
                (f"node.{node.node_id}.fields.{field_name}", f"{node_fields[field_name]:.6f}")
            )
        node_laplacian = node.laplacian or {}
        for field_name in sorted(node_laplacian):
            rows.append(
                (
                    f"node.{node.node_id}.laplacian.{field_name}",
                    f"{node_laplacian[field_name]:.6f}",
                )
            )
        node_df_dt = node.df_dt or {}
        for field_name in sorted(node_df_dt):
            rows.append(
                (f"node.{node.node_id}.df_dt.{field_name}", f"{node_df_dt[field_name]:.6f}")
            )
        if node.fascist_alignment is not None:
            rows.append((f"node.{node.node_id}.fascist_alignment", f"{node.fascist_alignment:.6f}"))

    return tuple(rows)


def _edge_rows(view: FieldStateView) -> tuple[str, ...]:
    """Format each field-gradient edge entry as its own line.

    :param view: the field-state projection to walk.
    :returns: one formatted line per entry in ``edges``, or empty when
        ``edges`` is ``None`` or an attributed-but-empty tuple. An
        unresolved territory renders as the deliberate literal ``"n/a"``,
        never the bare text ``"None"``.
    """
    if not view.edges:
        return ()
    lines: list[str] = []
    for edge in view.edges:
        source_territory = "n/a" if edge.source_territory is None else edge.source_territory
        target_territory = "n/a" if edge.target_territory is None else edge.target_territory
        lines.append(
            f"{edge.source} -> {edge.target} field={edge.field} "
            f"gradient={edge.gradient:.6f} source_territory={source_territory} "
            f"target_territory={target_territory}"
        )
    return tuple(lines)


def _absent_fields(view: FieldStateView) -> tuple[tuple[str, str], ...]:
    """Resolve every ``None`` field of ``view`` into a named remedy entry.

    An attributed-but-empty ``nodes``/``edges`` never occurs today (both
    projection-side helpers return ``None`` rather than ``()`` for "nothing
    to show" — see :mod:`babylon.projection.field_state`'s own docstring),
    so both are simply walked like every other optional field here.

    :param view: the field-state projection to walk.
    :returns: ``(field_name, remedy)`` pairs, one per ``None`` optional
        field, in FieldStateView declaration order.
    :raises KeyError: if an absent field has no entry in
        :data:`_REMEDY_BY_FIELD` — a FieldStateView field added without a
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
            msg = f"no remedy text registered for absent FieldStateView field {field_name!r}"
            raise KeyError(msg) from exc
        entries.append((field_name, remedy))
    return tuple(entries)


def _build_environment() -> ImmutableSandboxedEnvironment:
    """Construct the vault's Jinja2 environment.

    Identical construction to :func:`babylon.projection.vault.render._build_environment`
    (ADR099: construction is code, never data) — duplicated rather than
    imported so this module has zero dependency on ``render.py``'s
    County-shaped internals, matching ``render_economy.py``'s precedent.

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


def render_field_state(view: FieldStateView, *, verified_tick: int) -> str:
    """Render a field-state dossier page from a projection view-model.

    Pure function of ``(view, verified_tick)`` — no wall-clock, no
    randomness, no filesystem reads inside the template — so two calls with
    identical arguments yield byte-identical output (Constitution III.13's
    determinism contract).

    :param view: the field-state projection to materialize.
    :param verified_tick: the tick stamped into the page's frontmatter as
        its staleness anchor. Passed explicitly rather than read from
        ``view.verified_tick`` so the caller (the materializer) declares
        the bake tick once and unambiguously.
    :returns: the rendered Markdown page text.
    :raises jinja2.exceptions.UndefinedError: if the template references a
        field this module does not resolve (a template/model shape drift).
    """
    environment = _build_environment()
    template = environment.get_template("field_state.md.j2")
    return template.render(
        field_state=view,
        verified_tick=verified_tick,
        statblock_rows=_statblock_rows(view),
        edge_rows=_edge_rows(view),
        absent_fields=_absent_fields(view),
    )


__all__ = ["render_field_state"]
