"""Unit tests for delta-persistence selection (spec-089 S1b, FR-004/FR-005).

Pure logic: which hex rows enter the envelope. The bridge feeds the full
candidate frame (auditor + determinism inputs stay frame-level); only
changed value-tuples — or the whole frame on checkpoint ticks — persist.
"""

from __future__ import annotations

from uuid import UUID

from babylon.persistence.delta import (
    CHECKPOINT_EVERY_TICKS,
    hex_value_key,
    is_checkpoint_tick,
    select_hex_rows_for_emission,
)
from babylon.persistence.hex_state import DynamicHexState

_SESSION = UUID("01234567-89ab-cdef-0123-456789abcdef")


def _row(h3: str = "872a91055ffffff", tick: int = 0, v: float = 2.0) -> DynamicHexState:
    return DynamicHexState(
        session_id=_SESSION,
        tick=tick,
        h3_index=h3,
        county_fips="26163",
        state_fips="26",
        region_id="midwest",
        c=1.0,
        v=v,
        s=3.0,
        k=4.0,
        biocapacity_stock=5.0,
        energy_stock=6.0,
        raw_material_stock=7.0,
        internet_access_pct=0.5,
        surveillance_coupling=0.25,
    )


class TestCheckpointPredicate:
    def test_cadence_is_52(self) -> None:
        assert CHECKPOINT_EVERY_TICKS == 52

    def test_year_boundaries_are_checkpoints(self) -> None:
        assert is_checkpoint_tick(0)
        assert is_checkpoint_tick(52)
        assert is_checkpoint_tick(104)
        assert not is_checkpoint_tick(1)
        assert not is_checkpoint_tick(51)
        assert not is_checkpoint_tick(53)


class TestHexValueKey:
    def test_key_covers_the_nine_value_fields(self) -> None:
        assert hex_value_key(_row()) == (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 0.5, 0.25)

    def test_key_ignores_spatial_and_tick_fields(self) -> None:
        """Spatial keys are immutable (hex_spatial_map) and tick re-stamps."""
        assert hex_value_key(_row(tick=0)) == hex_value_key(_row(tick=7))


class TestSelectHexRowsForEmission:
    def test_first_tick_emits_full_frame(self) -> None:
        last: dict[str, tuple[float, ...]] = {}
        rows = [_row("872a91055ffffff"), _row("872a9105bffffff")]
        emitted = select_hex_rows_for_emission(tick=0, candidate_rows=rows, last_emitted=last)
        assert emitted == rows
        assert len(last) == 2

    def test_unchanged_frame_emits_nothing(self) -> None:
        last: dict[str, tuple[float, ...]] = {}
        rows_t0 = [_row(tick=0)]
        select_hex_rows_for_emission(tick=0, candidate_rows=rows_t0, last_emitted=last)
        rows_t1 = [_row(tick=1)]
        assert select_hex_rows_for_emission(tick=1, candidate_rows=rows_t1, last_emitted=last) == []

    def test_changed_value_emits_that_row_only(self) -> None:
        last: dict[str, tuple[float, ...]] = {}
        select_hex_rows_for_emission(
            tick=0,
            candidate_rows=[_row("872a91055ffffff"), _row("872a9105bffffff")],
            last_emitted=last,
        )
        changed = _row("872a91055ffffff", tick=1, v=99.0)
        same = _row("872a9105bffffff", tick=1)
        emitted = select_hex_rows_for_emission(
            tick=1, candidate_rows=[changed, same], last_emitted=last
        )
        assert emitted == [changed]
        # Emitting updates the memory: re-presenting the same value is quiet.
        assert (
            select_hex_rows_for_emission(
                tick=2,
                candidate_rows=[
                    _row("872a91055ffffff", tick=2, v=99.0),
                    _row("872a9105bffffff", tick=2),
                ],
                last_emitted=last,
            )
            == []
        )

    def test_checkpoint_tick_emits_full_frame_even_if_unchanged(self) -> None:
        last: dict[str, tuple[float, ...]] = {}
        select_hex_rows_for_emission(tick=0, candidate_rows=[_row(tick=0)], last_emitted=last)
        rows_t52 = [_row(tick=52)]
        assert (
            select_hex_rows_for_emission(tick=52, candidate_rows=rows_t52, last_emitted=last)
            == rows_t52
        )
