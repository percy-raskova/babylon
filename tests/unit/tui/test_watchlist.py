"""Contract tests for :mod:`babylon.tui.watchlist` (Program 24 P2b WO-37).

Pins the WO's four named behaviors: pin/unpin, capacity, deterministic
ordering, and the persistence seam being a ``Protocol`` a fake can satisfy.
Fixture-fed only — no engine, no graph, no vault, no ``babylon_meta`` (which
does not exist yet; this WO does not create it).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from rich.text import Text

from babylon.projection.view_models import ClassComposition, ConsciousnessSimplex, CountyView
from babylon.tui.watchlist import (
    DEFAULT_WATCHLIST_CAPACITY,
    InMemoryWatchlistPersistence,
    WatchlistPersistence,
    WatchlistState,
    load_watchlist,
    render_watchlist,
    save_watchlist,
    watchlist_rows,
    watchlist_title,
)

WAYNE = CountyView(
    county_fips="26163",
    verified_tick=847,
    population=1_749_343,
    class_composition=ClassComposition(
        bourgeoisie=0.01,
        petit_bourgeoisie=0.09,
        labor_aristocracy=0.4,
        proletariat=0.35,
        lumpenproletariat=0.15,
    ),
    median_wage=19.85,
    imperial_rent_phi=412.7,
    consciousness=ConsciousnessSimplex(
        revolutionary=0.148785,
        liberal=0.4375,
        fascist=0.413715,
    ),
    legitimacy=0.71,
    p_acquiescence=0.61,
    p_revolution=0.44,
    bifurcation_score=-0.32,
    sovereign_id="SOV_USA",
)
"""Wayne County (FIPS 26163) @ T0847 — the shared WO-25 fixture persona."""

OAKLAND = CountyView(county_fips="26125", verified_tick=847, population=1_270_432)
"""Oakland County — a second, lightly-attributed county for multi-pin tests."""


class TestPinAndUnpin:
    """The core pin/unpin surface: immutable, idempotent, order-preserving."""

    def test_pin_adds_the_id_to_pinned_ids(self) -> None:
        state = WatchlistState().pin("county/26163")
        assert state.pinned_ids == ("county/26163",)

    def test_pin_does_not_mutate_the_original_state(self) -> None:
        original = WatchlistState()
        original.pin("county/26163")
        assert original.pinned_ids == ()

    def test_pinning_an_already_pinned_id_is_a_no_op(self) -> None:
        state = WatchlistState().pin("county/26163")
        again = state.pin("county/26163")
        assert again is state
        assert again.pinned_ids == ("county/26163",)

    def test_is_pinned_reflects_current_state(self) -> None:
        state = WatchlistState().pin("county/26163")
        assert state.is_pinned("county/26163") is True
        assert state.is_pinned("county/26125") is False

    def test_unpin_removes_the_id(self) -> None:
        state = WatchlistState().pin("county/26163").unpin("county/26163")
        assert state.pinned_ids == ()

    def test_unpinning_an_id_that_is_not_pinned_is_a_no_op(self) -> None:
        state = WatchlistState()
        unchanged = state.unpin("county/26163")
        assert unchanged is state

    def test_unpin_preserves_the_relative_order_of_the_rest(self) -> None:
        state = WatchlistState().pin("a").pin("b").pin("c").unpin("b")
        assert state.pinned_ids == ("a", "c")


class TestCapacity:
    """A loud, explicit ceiling — never a silent eviction."""

    def test_the_documented_default_capacity_constant(self) -> None:
        assert DEFAULT_WATCHLIST_CAPACITY == 20

    def test_pinning_up_to_capacity_succeeds(self) -> None:
        state = WatchlistState(capacity=2)
        state = state.pin("a").pin("b")
        assert state.pinned_ids == ("a", "b")

    def test_pinning_past_capacity_raises(self) -> None:
        state = WatchlistState(capacity=2).pin("a").pin("b")
        with pytest.raises(ValueError, match="capacity"):
            state.pin("c")

    def test_a_no_op_repin_at_capacity_does_not_raise(self) -> None:
        state = WatchlistState(capacity=1).pin("a")
        assert state.pin("a").pinned_ids == ("a",)

    def test_unpinning_then_pinning_a_new_id_at_capacity_succeeds(self) -> None:
        state = WatchlistState(capacity=1).pin("a")
        state = state.unpin("a").pin("b")
        assert state.pinned_ids == ("b",)

    def test_constructing_a_state_already_over_capacity_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="capacity"):
            WatchlistState(capacity=1, pinned_ids=("a", "b"))


class TestDeterministicOrdering:
    """Pin order is FIFO call order — no wall-clock, no randomness."""

    def test_pin_order_matches_call_order(self) -> None:
        state = WatchlistState().pin("c").pin("a").pin("b")
        assert state.pinned_ids == ("c", "a", "b")

    def test_a_repin_after_unpin_lands_at_the_end_not_its_old_slot(self) -> None:
        state = WatchlistState().pin("a").pin("b").pin("c")
        state = state.unpin("a").pin("a")
        assert state.pinned_ids == ("b", "c", "a")

    def test_two_identical_call_sequences_produce_equal_states(self) -> None:
        first = WatchlistState().pin("a").pin("b").unpin("a").pin("c")
        second = WatchlistState().pin("a").pin("b").unpin("a").pin("c")
        assert first.pinned_ids == second.pinned_ids


class _FakePersistence:
    """A minimal test double proving :class:`WatchlistPersistence` is a
    structural ``Protocol`` — no inheritance from it anywhere in this class."""

    def __init__(self) -> None:
        self.saved: dict[str, tuple[str, ...]] = {}

    def load(self, session_id: str) -> tuple[str, ...]:
        return self.saved.get(session_id, ())

    def save(self, session_id: str, pinned_ids: tuple[str, ...]) -> None:
        self.saved[session_id] = pinned_ids


class TestPersistenceSeam:
    """The seam for P3 WO-46: a Protocol any fake (or future real store) can satisfy."""

    def test_a_fake_with_no_shared_base_class_satisfies_the_protocol(self) -> None:
        fake = _FakePersistence()
        assert isinstance(fake, WatchlistPersistence)

    def test_the_shipped_in_memory_persistence_also_satisfies_the_protocol(self) -> None:
        assert isinstance(InMemoryWatchlistPersistence(), WatchlistPersistence)

    def test_load_on_an_unknown_session_returns_an_honest_empty_tuple(self) -> None:
        fake = _FakePersistence()
        state = load_watchlist(fake, "campaign-1")
        assert state.pinned_ids == ()

    def test_save_then_load_round_trips_the_pin_order(self) -> None:
        fake = _FakePersistence()
        state = WatchlistState().pin("county/26163").pin("county/26125")
        save_watchlist(fake, "campaign-1", state)
        reloaded = load_watchlist(fake, "campaign-1")
        assert reloaded.pinned_ids == state.pinned_ids

    def test_different_sessions_do_not_share_state(self) -> None:
        fake = _FakePersistence()
        save_watchlist(fake, "campaign-1", WatchlistState().pin("a"))
        save_watchlist(fake, "campaign-2", WatchlistState().pin("b"))
        assert load_watchlist(fake, "campaign-1").pinned_ids == ("a",)
        assert load_watchlist(fake, "campaign-2").pinned_ids == ("b",)

    def test_a_persisted_pin_list_over_todays_capacity_is_a_loud_load_failure(self) -> None:
        fake = _FakePersistence()
        fake.save("campaign-1", ("a", "b", "c"))
        with pytest.raises(ValidationError, match="capacity"):
            load_watchlist(fake, "campaign-1", capacity=2)


class TestRenderWatchlist:
    """The page: ``peek(view, depth=0)`` rows stacked in pin order.

    Unit "selection-unwrap" (shell-interconnect): ``render_watchlist`` returns a bare,
    selectable ``Text`` rather than a ``Panel`` — the crimson-box/gold-title chrome moved
    to ``#watchlist-rail``'s own CSS (``babylon.tui.app``); the pin-count title that used
    to live in the Panel's ``title=`` is now :func:`watchlist_title`, a separate pure
    string function the caller (``ArchiveApp._refresh_watchlist``) assigns to the rail's
    ``border_title``.
    """

    def test_an_empty_watchlist_renders_the_honest_absence_line(self) -> None:
        result = render_watchlist((), {})
        assert isinstance(result, Text)
        assert "nothing pinned yet" in result.plain

    def test_a_pinned_entity_renders_its_depth_zero_peek_row(self) -> None:
        result = render_watchlist(("county/26163",), {"county/26163": WAYNE})
        assert isinstance(result, Text)
        plain = result.plain
        assert "population" in plain
        # depth=0 shows only the first declared field (peek's own contract).
        assert "median_wage" not in plain

    def test_rows_stack_in_pinned_id_order(self) -> None:
        result = render_watchlist(
            ("county/26125", "county/26163"),
            {"county/26163": WAYNE, "county/26125": OAKLAND},
        )
        assert isinstance(result, Text)
        lines = result.plain.splitlines()
        assert len(lines) == 2
        assert "county/26125" in lines[0]
        assert "county/26163" in lines[1]

    def test_a_pinned_id_missing_from_views_by_id_renders_a_named_absence_row(self) -> None:
        result = render_watchlist(("county/99999",), {})
        assert isinstance(result, Text)
        plain = result.plain
        assert "county/99999" in plain
        assert "no longer resolvable" in plain

    def test_two_calls_with_the_same_inputs_render_identically(self) -> None:
        pinned = ("county/26163",)
        views = {"county/26163": WAYNE}
        first = render_watchlist(pinned, views)
        second = render_watchlist(pinned, views)
        assert isinstance(first, Text)
        assert isinstance(second, Text)
        assert first.plain == second.plain


class TestWatchlistRows:
    """Unit "watchlist-row-nav" (shell-interconnect): :func:`watchlist_rows`
    is :func:`render_watchlist`'s row-addressable sibling — one
    ``(entity_id, row_text)`` pair per pinned id instead of one stacked
    ``Text``, so a caller (``ArchiveApp``'s ``#watchlist-rail`` ``OptionList``)
    can key one selectable option to each row."""

    def test_an_empty_watchlist_is_one_disabled_style_placeholder_row(self) -> None:
        rows = watchlist_rows((), {})
        assert len(rows) == 1
        entity_id, text = rows[0]
        assert entity_id is None
        assert isinstance(text, Text)
        assert "nothing pinned yet" in text.plain

    def test_a_pinned_entity_is_its_own_row_keyed_by_its_own_id(self) -> None:
        rows = watchlist_rows(("county/26163",), {"county/26163": WAYNE})
        assert len(rows) == 1
        entity_id, text = rows[0]
        assert entity_id == "county/26163"
        assert isinstance(text, Text)
        assert "population" in text.plain
        assert "median_wage" not in text.plain  # depth=0's own contract

    def test_rows_are_returned_in_pinned_id_order(self) -> None:
        rows = watchlist_rows(
            ("county/26125", "county/26163"),
            {"county/26163": WAYNE, "county/26125": OAKLAND},
        )
        assert [entity_id for entity_id, _ in rows] == ["county/26125", "county/26163"]

    def test_a_pinned_id_missing_from_views_by_id_is_still_its_own_openable_row(self) -> None:
        """Never disabled — Constitution III.11's own point: a pin with no
        resolvable peek view still names itself and stays fully openable
        (``pinned_ids`` is the exact subject-id form ``_navigate`` consumes,
        independent of whether a peek view-model exists)."""
        rows = watchlist_rows(("county/99999",), {})
        assert len(rows) == 1
        entity_id, text = rows[0]
        assert entity_id == "county/99999"
        assert "no longer resolvable" in text.plain

    def test_every_row_matches_render_watchlists_own_stacked_text(self) -> None:
        """Same per-row content as :func:`render_watchlist` — the two
        functions share :func:`~babylon.tui.watchlist._row_text`, they must
        never drift from each other."""
        pinned = ("county/26125", "county/26163")
        views = {"county/26163": WAYNE, "county/26125": OAKLAND}
        rows = watchlist_rows(pinned, views)
        stacked = render_watchlist(pinned, views).plain
        assert stacked == "\n".join(text.plain for _entity_id, text in rows)

    def test_two_calls_with_the_same_inputs_render_identically(self) -> None:
        pinned = ("county/26163",)
        views = {"county/26163": WAYNE}
        first = watchlist_rows(pinned, views)
        second = watchlist_rows(pinned, views)
        assert [text.plain for _id, text in first] == [text.plain for _id, text in second]


class TestWatchlistTitle:
    """The dynamic border-title string, split out of the old Panel's ``title=``."""

    def test_zero_pins_names_zero(self) -> None:
        assert watchlist_title(()) == "Watchlist (0 pinned)"

    def test_the_title_names_the_pin_count(self) -> None:
        assert watchlist_title(("county/26163", "county/26125")) == "Watchlist (2 pinned)"
