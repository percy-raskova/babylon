"""The declared-view registry — Constitution II.11's table-ownership contract.

This module discharges the II.11 follow-up TODO (``CONSTITUTION.md``): a
single, enumerable registry of every SQL view through which a client may read
engine-computed state. Each :class:`DeclaredView` names one Postgres view, the
subsystem that owns the tables it reads, the explicit ``ORDER BY`` that makes
the projection deterministic (Constitution III.13), the columns exposed to
full-text search, and the frozen Pydantic row-model that hydrates its rows.

The registry is **data, not a connection**: nothing here opens a database. It
generalizes the already-II.11-branded facade in
:mod:`babylon.persistence.postgres_aggregation` (whose row models it reuses
verbatim rather than reinventing) from four ad-hoc query helpers into one
declared interface every projection consumer can introspect.

See ``docs/reference/projection-registry.rst`` for the human-readable
ownership table and the contract pattern.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.persistence.hex_state import DynamicHexState
from babylon.persistence.postgres_aggregation import (
    CountyValueAggregate,
    GlobalPhiBalance,
    NationalValueAggregate,
    StateValueAggregate,
)
from babylon.projection.view_models import NationalTrendView

#: Sentinel prefix stamped on :attr:`DeclaredView.owning_subsystem` when a view
#: reads tables from more than one subsystem and no single owner is declared by
#: the governing spec. Recorded explicitly rather than guessed (II.11).
AMBIGUOUS_OWNER_PREFIX: Final[str] = "AMBIGUOUS:"


class DeclaredView(BaseModel):
    """One declared cross-subsystem read interface (Constitution II.11).

    A ``DeclaredView`` is the registry record for a single Postgres view. It
    is pure metadata — it carries the view's name, its owning subsystem, the
    deterministic ordering its rows must be read in, the full-text-searchable
    columns, and the frozen row-model type that validates a raw row into a
    Pydantic object. It never holds a connection or executes SQL.

    :param name: The logical registry key (identical to :attr:`sql_view` for
        every current entry, kept distinct so a future logical view may front
        a differently-named SQL object).
    :param owning_subsystem: The subsystem that owns the underlying tables. If
        the view spans tables owned by more than one subsystem with no single
        declared owner, this string starts with :data:`AMBIGUOUS_OWNER_PREFIX`
        and :attr:`ownership_ambiguous` is ``True``.
    :param sql_view: The Postgres view name as it appears in
        ``migrations/0030_views_current.sql``.
    :param order_by: The explicit ``ORDER BY`` clause (column list, without the
        ``ORDER BY`` keyword) that makes reads of this view deterministic. Must
        be non-empty — an unordered projection violates Constitution III.13.
    :param columns: Every column the view's ``SELECT`` projects, in order.
    :param fts_columns: The subset of :attr:`columns` exposed to full-text
        search. Must be a subset of :attr:`columns`; may be empty for a view
        with no text-searchable column.
    :param view_model: The frozen Pydantic model that hydrates one row of this
        view. Reused from :mod:`babylon.persistence` — the registry does not
        redefine row shapes.
    :param ownership_ambiguous: ``True`` iff ownership could not be resolved to
        a single subsystem and is recorded as ambiguous rather than guessed.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    name: str = Field(min_length=1)
    owning_subsystem: str = Field(min_length=1)
    sql_view: str = Field(min_length=1)
    order_by: str = Field(min_length=1)
    columns: tuple[str, ...] = Field(min_length=1)
    fts_columns: tuple[str, ...] = ()
    view_model: type[BaseModel]
    ownership_ambiguous: bool = False

    @model_validator(mode="after")
    def _validate_contract(self) -> DeclaredView:
        """Enforce the two structural invariants every declared view must hold.

        :raises ValueError: if any full-text-search column is not among the
            declared columns, or if the ambiguity flag disagrees with the
            :data:`AMBIGUOUS_OWNER_PREFIX` marker on the owner string.
        :returns: The validated model (unchanged).
        """
        unknown = tuple(c for c in self.fts_columns if c not in self.columns)
        if unknown:
            msg = (
                f"DeclaredView {self.name!r}: FTS columns {unknown} are not "
                f"declared columns {self.columns}"
            )
            raise ValueError(msg)
        marked = self.owning_subsystem.startswith(AMBIGUOUS_OWNER_PREFIX)
        if marked != self.ownership_ambiguous:
            msg = (
                f"DeclaredView {self.name!r}: ownership_ambiguous="
                f"{self.ownership_ambiguous} disagrees with owner string "
                f"{self.owning_subsystem!r}"
            )
            raise ValueError(msg)
        return self


_HEX_STATE_ASOF = DeclaredView(
    name="v_hex_state_asof",
    owning_subsystem=(
        "hex_substrate (spec-089 delta persistence; hex res-7 is the only "
        "persisted source of truth, FR-019)"
    ),
    sql_view="v_hex_state_asof",
    order_by="session_id, tick, h3_index",
    columns=(
        "session_id",
        "tick",
        "h3_index",
        "county_fips",
        "state_fips",
        "region_id",
        "c",
        "v",
        "s",
        "k",
        "biocapacity_stock",
        "energy_stock",
        "raw_material_stock",
        "internet_access_pct",
        "surveillance_coupling",
        "written_at_tick",
    ),
    fts_columns=("h3_index", "county_fips", "state_fips", "region_id"),
    view_model=DynamicHexState,
)

_COUNTY_VALUE_AGGREGATE = DeclaredView(
    name="v_county_value_aggregate",
    owning_subsystem=(
        "hex_substrate (spec-062 cross-scale aggregation; SUM over "
        "dynamic_hex_state, computed on read, never stored)"
    ),
    sql_view="v_county_value_aggregate",
    order_by="session_id, tick, county_fips",
    columns=(
        "session_id",
        "tick",
        "county_fips",
        "c_sum",
        "v_sum",
        "s_sum",
        "k_sum",
        "biocapacity_sum",
        "hex_count",
    ),
    fts_columns=("county_fips",),
    view_model=CountyValueAggregate,
)

_STATE_VALUE_AGGREGATE = DeclaredView(
    name="v_state_value_aggregate",
    owning_subsystem=(
        "hex_substrate (spec-062 cross-scale aggregation; SUM over "
        "dynamic_hex_state by state_fips, computed on read)"
    ),
    sql_view="v_state_value_aggregate",
    order_by="session_id, tick, state_fips",
    columns=(
        "session_id",
        "tick",
        "state_fips",
        "c_sum",
        "v_sum",
        "s_sum",
        "k_sum",
        "biocapacity_sum",
        "hex_count",
    ),
    fts_columns=("state_fips",),
    view_model=StateValueAggregate,
)

_NATIONAL_VALUE_AGGREGATE = DeclaredView(
    name="v_national_value_aggregate",
    owning_subsystem=(
        "hex_substrate (spec-062 cross-scale aggregation; SUM over "
        "dynamic_hex_state nationwide, computed on read)"
    ),
    sql_view="v_national_value_aggregate",
    order_by="session_id, tick, national_id",
    columns=(
        "session_id",
        "tick",
        "national_id",
        "c_sum",
        "v_sum",
        "s_sum",
        "k_sum",
        "biocapacity_sum",
        "hex_count",
    ),
    fts_columns=("national_id",),
    view_model=NationalValueAggregate,
)

_GLOBAL_PHI_BALANCE = DeclaredView(
    name="v_global_phi_balance",
    owning_subsystem=(
        "AMBIGUOUS: joins dynamic_external_node_state (external-node "
        "subsystem) and boundary_flow_register (boundary-flow subsystem); no "
        "single owner is declared for the FR-044 conservation view — recorded "
        "ambiguous per II.11 rather than guessed"
    ),
    sql_view="v_global_phi_balance",
    order_by="session_id, tick",
    columns=(
        "session_id",
        "tick",
        "phi_week_outflow_total",
        "phi_week_inflow_total",
        "residual",
    ),
    fts_columns=(),
    view_model=GlobalPhiBalance,
    ownership_ambiguous=True,
)

_NATIONAL_TREND = DeclaredView(
    name="v_national_trend",
    owning_subsystem=(
        "game_session tick-summary read-model (spec-037 bootstrap + "
        "spec-061 FR-003 US4; single write path via GameSession.advance_tick's "
        "persist_tick_summary commit, T5 Unit U2 — 'the wind is blowing')"
    ),
    sql_view="v_national_trend",
    order_by="session_id, tick",
    columns=(
        "session_id",
        "tick",
        "imperial_rent",
        "imperial_rent_delta",
        "price_log",
        "price_log_delta",
        "fictitious_log",
        "fictitious_log_delta",
        "market_corrections",
        "market_corrections_delta",
    ),
    fts_columns=(),
    view_model=NationalTrendView,
)

#: The closed set of declared cross-subsystem read interfaces (Constitution
#: II.11). Immutable by being a tuple of frozen models; new views join by
#: adding an entry here and a row to the ownership table in
#: ``docs/reference/projection-registry.rst``.
REGISTRY: Final[tuple[DeclaredView, ...]] = (
    _HEX_STATE_ASOF,
    _COUNTY_VALUE_AGGREGATE,
    _STATE_VALUE_AGGREGATE,
    _NATIONAL_VALUE_AGGREGATE,
    _GLOBAL_PHI_BALANCE,
    _NATIONAL_TREND,
)


def declared_view(name: str) -> DeclaredView:
    """Look up a declared view by its registry name.

    :param name: The :attr:`DeclaredView.name` to find.
    :returns: The matching :class:`DeclaredView`.
    :raises KeyError: if no declared view carries that name — a loud failure
        (Constitution III.11) preferred to a silent ``None`` a caller might
        treat as an ungated read.
    """
    for view in REGISTRY:
        if view.name == name:
            return view
    raise KeyError(f"no declared view named {name!r}")


__all__ = [
    "AMBIGUOUS_OWNER_PREFIX",
    "REGISTRY",
    "DeclaredView",
    "declared_view",
]
