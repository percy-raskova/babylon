"""Formula/metric provenance manifest backing ``GET .../explain/`` (spec-113 Lane D).

InspectionStack's recursive drill-down (architecture.md §2.4, DESIGN_BIBLE.md §4)
needs a terminal "FormulaCard" frame for any metric row: expression, real
per-scope input values, and constants with their provenance. This module is
that manifest — ``METRIC_PROVENANCE`` — plus the small pure functions that
resolve one ``(metric, scope)`` pair against an already-hydrated
``(WorldState, BabylonGraph)`` pair into an :class:`ExplainResult`.

Constitution III.11 (Loud Failure) governs every extractor here: a value the
engine has no live source for is ``None``, never a fabricated plausible
number. Two concrete gaps this manifest is honest about:

* ``profit_rate``/``occ`` — no wired System computes a per-territory or
  global c/v/s decomposition anywhere in the engine (matches
  ``EngineBridge.get_economy``/``get_economy_dashboard``'s own permanent
  ``None`` for these fields, and ``_hex_state_row``'s docstring).
* ``steepness_k``/``sensitivity_k``/``decay_lambda`` (the
  ``acquiescence_probability``/``consciousness_drift`` formula constants) —
  these live in ``GameDefines`` (``services.defines.survival.steepness_k``
  et al. in ``babylon.engine.systems.survival``), which is out of this
  module's import surface (spec-113 Lane D is restricted to
  ``FormulaRegistry.default()``/``list_formulas()``/``babylon.formulas``
  constants — see the lane's ownership note). Their provenance entries
  report ``value=None, kind="constant"`` with a doc note naming the real
  source, rather than a duplicated/staled copy of the coefficient.

Every entry whose ``formula_name`` is set names a real
``FormulaRegistry.default().list_formulas()`` entry (pinned by
``tests/unit/web/test_provenance.py::TestManifestContract``); entries with
no live engine formula (``profit_rate``/``occ``/``imperial_rent``/
``value_extraction_ratio``) leave it ``None`` rather than pointing at an
unrelated registered name.

``FormulaRegistry`` is imported from ``.engine_bridge`` (a re-export), not
directly from ``babylon.engine.formula_registry`` —
``tests/unit/web/test_import_boundary.py`` enforces ``engine_bridge.py`` as
the *only* file in ``web/`` allowed to import ``babylon.engine`` (and
``babylon.models``/``babylon.config``/``babylon.ooda``/``babylon.persistence``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .engine_bridge import FormulaRegistry, _aggregate_graph_economy

# ---------------------------------------------------------------------- #
# Scope grammar: "global" | "hex:<h3>" | "org:<id>"
# ---------------------------------------------------------------------- #

SUPPORTED_SCOPE_KINDS: frozenset[str] = frozenset({"global", "hex", "org"})


@dataclass(frozen=True)
class ExplainScope:
    """One parsed ``scope`` query-param value."""

    kind: str
    entity_id: str | None = None


def parse_scope(raw: str) -> ExplainScope:
    """Parse ``"global"`` / ``"hex:<h3>"`` / ``"org:<id>"`` into an :class:`ExplainScope`.

    Args:
        raw: The raw ``scope`` query-param value.

    Returns:
        An :class:`ExplainScope`. ``kind`` is whatever precedes the first
        ``":"`` (or the whole string when there is none) — callers must
        still check ``kind in SUPPORTED_SCOPE_KINDS`` (this function never
        raises; an unrecognized kind is loud-failed by the caller, not
        here, per III.11 — "which stage failed" stays visible).
    """
    if ":" in raw:
        kind, _, entity_id = raw.partition(":")
        return ExplainScope(kind=kind, entity_id=entity_id or None)
    return ExplainScope(kind=raw, entity_id=None)


def format_scope(scope: ExplainScope) -> str:
    """Inverse of :func:`parse_scope` — canonical string form for the response body."""
    if scope.entity_id is None:
        return scope.kind
    return f"{scope.kind}:{scope.entity_id}"


# ---------------------------------------------------------------------- #
# Explain context + result shapes
# ---------------------------------------------------------------------- #


@dataclass(frozen=True)
class ExplainContext:
    """Everything an extractor needs: hydrated state/graph plus the requested scope.

    ``state``/``graph`` are intentionally untyped (``Any``): this module's
    import surface is restricted to ``FormulaRegistry``/``babylon.formulas``
    (see the module docstring), so it never imports
    ``babylon.models.world_state.WorldState`` or
    ``babylon.topology.graph.BabylonGraph`` for a type-only reference —
    matching ``engine_bridge.py``'s own ``graph: Any`` convention on
    similar graph-reading helpers (e.g. ``_territory_graph_attr``).
    """

    state: Any
    graph: Any
    scope: ExplainScope


@dataclass(frozen=True)
class ProvenanceInputValue:
    """One resolved formula input, ready for the response body.

    Args:
        name: Must equal the backing formula callable's parameter name
            exactly when ``MetricProvenance.formula_name`` is set (pinned
            by the manifest contract test).
        label: Human-readable description for the InspectionStack row.
        value: The live value, or ``None`` when the engine has no source
            for it (never a fabricated default).
        kind: ``"metric"`` (itself explainable — see ``ref``),
            ``"constant"`` (a coefficient, possibly out-of-reach — see
            the module docstring), or ``"state"`` (a plain hydrated
            state/graph read).
        ref: When ``kind == "metric"``, the ``METRIC_PROVENANCE`` key this
            input recurses into.
    """

    name: str
    label: str
    value: float | str | None
    kind: str
    ref: str | None = None


@dataclass(frozen=True)
class ExplainResult:
    """The fully-resolved response body for one ``(metric, scope)`` request."""

    metric: str
    scope: str
    value: float | None
    formula_name: str | None
    expression: str
    doc: str
    inputs: tuple[ProvenanceInputValue, ...]


class UnknownMetricError(Exception):
    """``metric`` is not a key of :data:`METRIC_PROVENANCE`."""

    def __init__(self, metric: str) -> None:
        self.metric = metric
        super().__init__(f"Unknown metric {metric!r}")


class UnsupportedScopeError(Exception):
    """``scope``'s kind is not one this metric supports (III.11 loud failure)."""

    def __init__(self, metric: str, kind: str, supported: frozenset[str]) -> None:
        self.metric = metric
        self.kind = kind
        self.supported = supported
        super().__init__(
            f"metric {metric!r} does not support scope kind {kind!r}; "
            f"supported: {sorted(supported)}"
        )


class ScopeEntityNotFoundError(Exception):
    """``scope``'s id names no real hex/org in this game."""

    def __init__(self, kind: str, entity_id: str | None) -> None:
        self.kind = kind
        self.entity_id = entity_id
        super().__init__(f"No {kind} found for id {entity_id!r} in this game")


# ---------------------------------------------------------------------- #
# Shared read helpers (small, self-contained — this module does not import
# engine_bridge's private graph-walk helpers beyond _aggregate_graph_economy,
# to keep the two additive properties' builder and this endpoint decoupled).
# ---------------------------------------------------------------------- #


def _find_territory_by_h3(state: Any, h3_index: str) -> Any | None:
    """Locate a Territory by its ``h3_index`` (the ``hex:<h3>`` scope key)."""
    for territory in state.territories.values():
        if territory.h3_index == h3_index:
            return territory
    return None


def _find_entity(state: Any, entity_id: str) -> Any | None:
    """Locate a SocialClass entity by id (the ``org:<id>`` scope key)."""
    return state.entities.get(entity_id)


def _incoming_wages_flow(graph: Any, entity_id: str) -> float:
    """Sum ``value_flow`` over live WAGES edges targeting ``entity_id``.

    WAGES is the engine's Employer -> Worker edge
    (:class:`~babylon.models.enums.EdgeType`); this is the real per-entity
    "core wages" source ``ProductionSystem``/``ImperialRentSystem`` write.
    """
    total = 0.0
    for source, target in graph.edges:
        if target != entity_id:
            continue
        edge_data = graph.edges[(source, target)]
        etype = str(edge_data.get("edge_type", edge_data.get("_edge_type", ""))).lower()
        if etype == "wages":
            total += float(edge_data.get("value_flow", 0.0))
    return total


def _resolve_org_entity(ctx: ExplainContext) -> Any | None:
    """``org``-scope entity lookup shared by every per-class extractor."""
    if ctx.scope.entity_id is None:
        return None
    return _find_entity(ctx.state, ctx.scope.entity_id)


# ---------------------------------------------------------------------- #
# Manifest entry shape
# ---------------------------------------------------------------------- #

InputsFn = Callable[[ExplainContext], tuple[ProvenanceInputValue, ...]]
ValueFn = Callable[[ExplainContext], float | None]


@dataclass(frozen=True)
class MetricProvenance:
    """One :data:`METRIC_PROVENANCE` entry.

    ``inputs_fn``/``value_fn`` are separate (rather than deriving value by
    auto-calling ``formula_name`` with ``inputs_fn``'s output) so that
    metrics whose value is already engine-computed and stored (none here
    yet) or is a raw ledger read (``imperial_rent``) don't need a formula
    call at all, while still sharing the exact same response shape as
    formula-backed metrics.
    """

    formula_name: str | None
    doc: str
    expression: str
    supported_scopes: frozenset[str]
    inputs_fn: InputsFn
    value_fn: ValueFn


def _no_inputs(_ctx: ExplainContext) -> tuple[ProvenanceInputValue, ...]:
    return ()


def _no_value(_ctx: ExplainContext) -> float | None:
    return None


# ---------------------------------------------------------------------- #
# value_extraction_ratio — global, terminal (raw graph aggregate, no
# FormulaRegistry entry backs this exact proxy; it is the same
# (value_produced + rent_extracted) / value_produced ratio
# EngineBridge._aggregate_graph_economy computes for /economy/'s global
# exploitation_rate — reused here via that helper for zero-drift parity).
# ---------------------------------------------------------------------- #


def _value_extraction_ratio_inputs(ctx: ExplainContext) -> tuple[ProvenanceInputValue, ...]:
    econ = _aggregate_graph_economy(ctx.graph)
    return (
        ProvenanceInputValue(
            name="value_produced",
            label="Value produced (sum of social_class/organization wealth)",
            value=econ["value_produced"],
            kind="state",
        ),
        ProvenanceInputValue(
            name="rent_extracted",
            label="Rent extracted (EXTRACTIVE/ANTAGONISTIC edge value_flow)",
            value=econ["rent_extracted"],
            kind="state",
        ),
    )


def _value_extraction_ratio_value(ctx: ExplainContext) -> float | None:
    econ = _aggregate_graph_economy(ctx.graph)
    value_produced = float(econ["value_produced"])
    rent_extracted = float(econ["rent_extracted"])
    if value_produced <= 0.0:
        return None
    return (value_produced + rent_extracted) / value_produced


# ---------------------------------------------------------------------- #
# exploitation_rate — global (FormulaRegistry "exploitation_rate",
# calculate_unequal_exchange_rate). Value is EngineBridge's own
# _aggregate_graph_economy result — the same number /economy/ shows for
# this session, guaranteed (not an independent re-derivation that could
# drift).
# ---------------------------------------------------------------------- #


def _exploitation_rate_inputs(ctx: ExplainContext) -> tuple[ProvenanceInputValue, ...]:
    return (
        ProvenanceInputValue(
            name="exchange_ratio",
            label="Exchange ratio",
            value=_value_extraction_ratio_value(ctx),
            kind="metric",
            ref="value_extraction_ratio",
        ),
    )


def _exploitation_rate_value(ctx: ExplainContext) -> float | None:
    value = _aggregate_graph_economy(ctx.graph)["exploitation_rate"]
    return float(value) if value is not None else None


# ---------------------------------------------------------------------- #
# labor_aristocracy_ratio — org:<id> (FormulaRegistry
# "labor_aristocracy_ratio", calculate_labor_aristocracy_ratio).
# ---------------------------------------------------------------------- #


def _labor_aristocracy_ratio_inputs(ctx: ExplainContext) -> tuple[ProvenanceInputValue, ...]:
    entity = _resolve_org_entity(ctx)
    core_wages = (
        _incoming_wages_flow(ctx.graph, ctx.scope.entity_id)
        if entity is not None and ctx.scope.entity_id is not None
        else None
    )
    value_produced = float(entity.wealth) if entity is not None else None
    return (
        ProvenanceInputValue(
            name="core_wages",
            label="Core wages (incoming WAGES edge flow)",
            value=core_wages,
            kind="state",
        ),
        ProvenanceInputValue(
            name="value_produced",
            label="Value produced (entity wealth)",
            value=value_produced,
            kind="state",
        ),
    )


def _labor_aristocracy_ratio_value(ctx: ExplainContext) -> float | None:
    inputs = {i.name: i.value for i in _labor_aristocracy_ratio_inputs(ctx)}
    value_produced = inputs["value_produced"]
    core_wages = inputs["core_wages"]
    if not isinstance(value_produced, int | float) or value_produced <= 0.0:
        return None
    if not isinstance(core_wages, int | float):
        return None
    formula = FormulaRegistry.default().get("labor_aristocracy_ratio")
    return float(formula(core_wages=core_wages, value_produced=value_produced))


# ---------------------------------------------------------------------- #
# revolution_probability — org:<id> (FormulaRegistry
# "revolution_probability", calculate_revolution_probability).
#
# "cohesion" is the entity's stored base ``organization`` field.
# SurvivalSystem's live value (``effective_organization`` — a
# SOLIDARITY-edge multiplier on top of base ``organization``, see
# ``babylon.engine.systems.survival._calculate_solidarity_multiplier``) is
# not reproduced here, so this explain value can differ slightly from the
# entity's live ``p_revolution`` field — documented, not silently claimed
# as exact.
# ---------------------------------------------------------------------- #


def _revolution_probability_inputs(ctx: ExplainContext) -> tuple[ProvenanceInputValue, ...]:
    entity = _resolve_org_entity(ctx)
    cohesion = float(entity.organization) if entity is not None else None
    repression = float(entity.repression_faced) if entity is not None else None
    return (
        ProvenanceInputValue(
            name="cohesion",
            label="Cohesion (base class organization)",
            value=cohesion,
            kind="state",
        ),
        ProvenanceInputValue(
            name="repression",
            label="Repression faced",
            value=repression,
            kind="state",
        ),
    )


def _revolution_probability_value(ctx: ExplainContext) -> float | None:
    inputs = {i.name: i.value for i in _revolution_probability_inputs(ctx)}
    cohesion = inputs["cohesion"]
    repression = inputs["repression"]
    if not isinstance(cohesion, int | float) or not isinstance(repression, int | float):
        return None
    formula = FormulaRegistry.default().get("revolution_probability")
    return float(formula(cohesion=cohesion, repression=repression))


# ---------------------------------------------------------------------- #
# acquiescence_probability — org:<id> (FormulaRegistry
# "acquiescence_probability", calculate_acquiescence_probability).
#
# ``steepness_k`` is ``services.defines.survival.steepness_k``
# (``babylon.engine.systems.survival``) — a GameDefines coefficient, out
# of this module's import surface. Value stays honestly ``None`` (never a
# duplicated/staled copy of the real coefficient).
# ---------------------------------------------------------------------- #


def _acquiescence_probability_inputs(ctx: ExplainContext) -> tuple[ProvenanceInputValue, ...]:
    entity = _resolve_org_entity(ctx)
    wealth = float(entity.wealth) if entity is not None else None
    subsistence = float(entity.subsistence_threshold) if entity is not None else None
    return (
        ProvenanceInputValue(name="wealth", label="Wealth", value=wealth, kind="state"),
        ProvenanceInputValue(
            name="subsistence_threshold",
            label="Subsistence threshold",
            value=subsistence,
            kind="state",
        ),
        ProvenanceInputValue(
            name="steepness_k",
            label="Sigmoid steepness (GameDefines survival.steepness_k)",
            value=None,
            kind="constant",
        ),
    )


def _acquiescence_probability_value(_ctx: ExplainContext) -> float | None:
    # steepness_k is unreachable from this module (see the docstring
    # above) — the formula cannot be honestly invoked without it.
    return None


# ---------------------------------------------------------------------- #
# consciousness_drift — org:<id> (FormulaRegistry "consciousness_drift",
# calculate_consciousness_drift). The architecture doc's own worked
# example: "dPsi/dt = k(1 - Wc/Vc) - lambda*Psi + bifurcation."
#
# ``sensitivity_k``/``decay_lambda`` are GameDefines coefficients, same
# out-of-reach status as ``steepness_k`` above. ``solidarity_pressure``/
# ``wage_change`` are shown at the formula's own literal defaults (0.0) —
# real values, not fabrications, just not per-tick-recomputed here.
# ---------------------------------------------------------------------- #


def _consciousness_drift_inputs(ctx: ExplainContext) -> tuple[ProvenanceInputValue, ...]:
    entity = _resolve_org_entity(ctx)
    core_wages = (
        _incoming_wages_flow(ctx.graph, ctx.scope.entity_id)
        if entity is not None and ctx.scope.entity_id is not None
        else None
    )
    value_produced = float(entity.wealth) if entity is not None else None
    current_consciousness = (
        float(entity.ideology.class_consciousness) if entity is not None else None
    )
    return (
        ProvenanceInputValue(
            name="core_wages",
            label="Core wages (incoming WAGES edge flow)",
            value=core_wages,
            kind="state",
        ),
        ProvenanceInputValue(
            name="value_produced",
            label="Value produced (entity wealth)",
            value=value_produced,
            kind="state",
        ),
        ProvenanceInputValue(
            name="current_consciousness",
            label="Current class consciousness",
            value=current_consciousness,
            kind="state",
        ),
        ProvenanceInputValue(
            name="sensitivity_k",
            label="Sensitivity k (GameDefines)",
            value=None,
            kind="constant",
        ),
        ProvenanceInputValue(
            name="decay_lambda",
            label="Decay lambda (GameDefines)",
            value=None,
            kind="constant",
        ),
        ProvenanceInputValue(
            name="solidarity_pressure",
            label="Solidarity pressure (formula default)",
            value=0.0,
            kind="constant",
        ),
        ProvenanceInputValue(
            name="wage_change",
            label="Wage change (formula default)",
            value=0.0,
            kind="constant",
        ),
    )


def _consciousness_drift_value(_ctx: ExplainContext) -> float | None:
    # sensitivity_k/decay_lambda are unreachable from this module (see the
    # docstring above) — the formula cannot be honestly invoked without them.
    return None


# ---------------------------------------------------------------------- #
# The manifest.
# ---------------------------------------------------------------------- #

METRIC_PROVENANCE: dict[str, MetricProvenance] = {
    "value_extraction_ratio": MetricProvenance(
        formula_name=None,
        doc=(
            "(value_produced + rent_extracted) / value_produced over every "
            "social_class/organization node — the graph-wide proxy "
            "EngineBridge._aggregate_graph_economy computes for /economy/'s "
            "global exploitation_rate. No FormulaRegistry entry backs this "
            "exact proxy (there is a differently-scoped registered "
            "'exchange_ratio' formula for Prebisch-Singer terms-of-trade — "
            "not the same computation, so this entry deliberately leaves "
            "formula_name unset rather than pointing at it)."
        ),
        expression="exchange_ratio = (value_produced + rent_extracted) / value_produced",
        supported_scopes=frozenset({"global"}),
        inputs_fn=_value_extraction_ratio_inputs,
        value_fn=_value_extraction_ratio_value,
    ),
    "exploitation_rate": MetricProvenance(
        formula_name="exploitation_rate",
        doc=FormulaRegistry.default().get("exploitation_rate").__doc__ or "",
        expression=(FormulaRegistry.default().get("exploitation_rate").__doc__ or "")
        .strip()
        .split("\n")[0],
        supported_scopes=frozenset({"global"}),
        inputs_fn=_exploitation_rate_inputs,
        value_fn=_exploitation_rate_value,
    ),
    "profit_rate": MetricProvenance(
        formula_name=None,
        doc=(
            "No wired engine System computes a per-territory or global c/v/s "
            "decomposition yet — matches EngineBridge.get_economy's/"
            "get_economy_dashboard's own permanent None for this field."
        ),
        expression="rate of profit = s / (c + v) — not yet computed by any System",
        supported_scopes=frozenset({"global", "hex"}),
        inputs_fn=_no_inputs,
        value_fn=_no_value,
    ),
    "occ": MetricProvenance(
        formula_name=None,
        doc=(
            "Organic composition of capital — no wired engine System computes "
            "this per-territory or globally yet (same gap as profit_rate)."
        ),
        expression="occ = c / v — not yet computed by any System",
        supported_scopes=frozenset({"global", "hex"}),
        inputs_fn=_no_inputs,
        value_fn=_no_value,
    ),
    "imperial_rent": MetricProvenance(
        formula_name=None,
        doc=(
            "GlobalEconomy.imperial_rent_pool — the accumulated imperial rent "
            "pool (the 'Gas Tank'), fed by TRIBUTE inflow and depleted by "
            "WAGES/CLIENT_STATE outflow each tick. A raw ledger balance, not "
            "a derived formula — terminal (no further inputs)."
        ),
        expression="imperial_rent = state.economy.imperial_rent_pool",
        supported_scopes=frozenset({"global"}),
        inputs_fn=_no_inputs,
        value_fn=lambda ctx: (
            float(ctx.state.economy.imperial_rent_pool) if ctx.state.economy is not None else None
        ),
    ),
    "labor_aristocracy_ratio": MetricProvenance(
        formula_name="labor_aristocracy_ratio",
        doc=FormulaRegistry.default().get("labor_aristocracy_ratio").__doc__ or "",
        expression=(FormulaRegistry.default().get("labor_aristocracy_ratio").__doc__ or "")
        .strip()
        .split("\n")[0],
        supported_scopes=frozenset({"org"}),
        inputs_fn=_labor_aristocracy_ratio_inputs,
        value_fn=_labor_aristocracy_ratio_value,
    ),
    "revolution_probability": MetricProvenance(
        formula_name="revolution_probability",
        doc=FormulaRegistry.default().get("revolution_probability").__doc__ or "",
        expression=(FormulaRegistry.default().get("revolution_probability").__doc__ or "")
        .strip()
        .split("\n")[0],
        supported_scopes=frozenset({"org"}),
        inputs_fn=_revolution_probability_inputs,
        value_fn=_revolution_probability_value,
    ),
    "acquiescence_probability": MetricProvenance(
        formula_name="acquiescence_probability",
        doc=FormulaRegistry.default().get("acquiescence_probability").__doc__ or "",
        expression=(FormulaRegistry.default().get("acquiescence_probability").__doc__ or "")
        .strip()
        .split("\n")[0],
        supported_scopes=frozenset({"org"}),
        inputs_fn=_acquiescence_probability_inputs,
        value_fn=_acquiescence_probability_value,
    ),
    "consciousness_drift": MetricProvenance(
        formula_name="consciousness_drift",
        doc=FormulaRegistry.default().get("consciousness_drift").__doc__ or "",
        expression=(FormulaRegistry.default().get("consciousness_drift").__doc__ or "")
        .strip()
        .split("\n")[0],
        supported_scopes=frozenset({"org"}),
        inputs_fn=_consciousness_drift_inputs,
        value_fn=_consciousness_drift_value,
    ),
}


# ---------------------------------------------------------------------- #
# Resolution entry point
# ---------------------------------------------------------------------- #


def explain_metric(state: Any, graph: Any, metric: str, scope: ExplainScope) -> ExplainResult:
    """Resolve one ``(metric, scope)`` request against hydrated state/graph.

    Args:
        state: A hydrated ``WorldState`` (untyped — see :class:`ExplainContext`).
        graph: The matching hydrated ``BabylonGraph``.
        metric: A :data:`METRIC_PROVENANCE` key.
        scope: The parsed scope (see :func:`parse_scope`).

    Returns:
        The fully-resolved :class:`ExplainResult`.

    Raises:
        UnknownMetricError: ``metric`` is not in the manifest.
        UnsupportedScopeError: this metric does not support ``scope.kind``.
        ScopeEntityNotFoundError: ``scope`` names a hex/org that does not
            exist in this game (a valid scope *kind*, an unresolvable id).
    """
    provenance = METRIC_PROVENANCE.get(metric)
    if provenance is None:
        raise UnknownMetricError(metric)
    if scope.kind not in provenance.supported_scopes:
        raise UnsupportedScopeError(metric, scope.kind, provenance.supported_scopes)

    if scope.kind == "hex" and (
        scope.entity_id is None or _find_territory_by_h3(state, scope.entity_id) is None
    ):
        raise ScopeEntityNotFoundError("hex", scope.entity_id)
    elif scope.kind == "org" and (
        scope.entity_id is None or _find_entity(state, scope.entity_id) is None
    ):
        raise ScopeEntityNotFoundError("org", scope.entity_id)

    ctx = ExplainContext(state=state, graph=graph, scope=scope)
    inputs = provenance.inputs_fn(ctx)
    value = provenance.value_fn(ctx)
    return ExplainResult(
        metric=metric,
        scope=format_scope(scope),
        value=value,
        formula_name=provenance.formula_name,
        expression=provenance.expression,
        doc=provenance.doc,
        inputs=inputs,
    )
