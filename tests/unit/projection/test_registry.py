"""Contract tests for the declared-view registry (Constitution II.11)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from babylon.projection.registry import (
    AMBIGUOUS_OWNER_PREFIX,
    REGISTRY,
    DeclaredView,
    declared_view,
)

# The views II.11 / WO-2 require the registry to enumerate at minimum.
_REQUIRED_VIEWS = frozenset(
    {
        "v_county_value_aggregate",
        "v_hex_state_asof",
        "v_state_value_aggregate",
        "v_national_value_aggregate",
        "v_global_phi_balance",
        "v_national_trend",
    }
)


def test_registry_enumerates_the_required_views() -> None:
    """Every constitutionally-required declared view is present."""
    names = {view.name for view in REGISTRY}
    assert names >= _REQUIRED_VIEWS


def test_every_entry_has_a_non_empty_order_by() -> None:
    """III.13: a projection without an explicit ORDER BY is non-deterministic."""
    for view in REGISTRY:
        assert view.order_by.strip(), f"{view.name} has an empty ORDER BY"


def test_view_names_are_unique() -> None:
    """No two registry entries share a name — ``declared_view`` stays total."""
    names = [view.name for view in REGISTRY]
    assert len(names) == len(set(names))


def test_fts_columns_are_a_subset_of_declared_columns() -> None:
    """A full-text-search column that is not projected cannot be indexed."""
    for view in REGISTRY:
        assert set(view.fts_columns) <= set(view.columns), view.name


def test_registry_is_an_immutable_tuple_of_frozen_models() -> None:
    """The registry is data: a tuple of frozen models, mutated by neither."""
    assert isinstance(REGISTRY, tuple)
    with pytest.raises(ValidationError):
        REGISTRY[0].name = "mutated"  # type: ignore[misc]


def test_declared_view_looks_up_by_name() -> None:
    """``declared_view`` returns the matching entry."""
    view = declared_view("v_county_value_aggregate")
    assert view.name == "v_county_value_aggregate"
    assert view.view_model.__name__ == "CountyValueAggregate"


def test_national_trend_view_is_declared_correctly() -> None:
    """T5 Unit U2: v_national_trend's contract — deterministic order, the
    tick_summary-derived column set, and its own row-model."""
    view = declared_view("v_national_trend")
    assert view.order_by == "session_id, tick"
    assert view.view_model.__name__ == "NationalTrendView"
    assert view.columns == (
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
    )
    assert view.ownership_ambiguous is False


def test_declared_view_raises_loudly_on_unknown_name() -> None:
    """An unknown view name is a loud ``KeyError`` (III.11), not ``None``."""
    with pytest.raises(KeyError):
        declared_view("v_does_not_exist")


def test_ambiguous_ownership_is_recorded_explicitly() -> None:
    """The Φ-balance view spans subsystems and is flagged ambiguous, not guessed."""
    phi = declared_view("v_global_phi_balance")
    assert phi.ownership_ambiguous is True
    assert phi.owning_subsystem.startswith(AMBIGUOUS_OWNER_PREFIX)


def test_unambiguous_entries_carry_a_concrete_owner() -> None:
    """A non-ambiguous entry names a real subsystem, never the sentinel."""
    for view in REGISTRY:
        if view.ownership_ambiguous:
            continue
        assert not view.owning_subsystem.startswith(AMBIGUOUS_OWNER_PREFIX)
        assert view.owning_subsystem.strip()


class _Row(BaseModel):
    """Minimal row model for constructing ad-hoc ``DeclaredView`` instances."""

    value: int = 0


def test_declared_view_rejects_fts_not_in_columns() -> None:
    """The model validator rejects an FTS column absent from the declared set."""
    with pytest.raises(ValidationError):
        DeclaredView(
            name="v_bad",
            owning_subsystem="test",
            sql_view="v_bad",
            order_by="tick",
            columns=("tick",),
            fts_columns=("not_declared",),
            view_model=_Row,
        )


def test_declared_view_rejects_ambiguity_flag_mismatch() -> None:
    """The ambiguity flag must agree with the sentinel marker on the owner."""
    with pytest.raises(ValidationError):
        DeclaredView(
            name="v_bad",
            owning_subsystem="a concrete owner",
            sql_view="v_bad",
            order_by="tick",
            columns=("tick",),
            view_model=_Row,
            ownership_ambiguous=True,
        )


def test_declared_view_rejects_empty_order_by() -> None:
    """An empty ORDER BY is rejected at construction (III.13)."""
    with pytest.raises(ValidationError):
        DeclaredView(
            name="v_bad",
            owning_subsystem="test",
            sql_view="v_bad",
            order_by="",
            columns=("tick",),
            view_model=_Row,
        )
