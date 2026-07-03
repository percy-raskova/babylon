"""Delta-persistence selection for per-tick hex state.

Spec: 089-delta-persistence (S1b, FR-004/FR-005).

Measured basis (2026-07-03): zero of 1,045 hex rows change any value
across consecutive ticks — hex economics are static-per-year by design
(`project/02-engine-truths.md`), so full-frame-every-tick persistence is
~98% duplicate rows (7 GB per canonical Michigan run; ~450 GB projected
at national res-7).

The bridge builds the full candidate frame every tick (the conservation
auditor and determinism inputs stay frame-level) and calls
:func:`select_hex_rows_for_emission` to decide what actually persists:

* rows whose **value tuple** changed since last emission, and
* the entire frame on checkpoint ticks (every 52 ticks = yearly, where
  changes cluster anyway) — bounding as-of reconstruction depth to one
  year of deltas.

Spatial keys are excluded from the value tuple: they are immutable per
hex and live in ``hex_spatial_map`` (spec-088 S3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from babylon.persistence.hex_state import DynamicHexState

#: Full-frame cadence: one checkpoint per simulated year (52 weekly ticks).
CHECKPOINT_EVERY_TICKS = 52


def is_checkpoint_tick(tick: int) -> bool:
    """True when ``tick`` persists a full checkpoint frame (0, 52, 104…)."""
    return tick % CHECKPOINT_EVERY_TICKS == 0


def hex_value_key(row: DynamicHexState) -> tuple[float, ...]:
    """The 9-field value tuple whose change makes a hex row worth persisting.

    Excludes ``tick`` (re-stamped every tick) and the spatial keys
    (immutable; stored once in ``hex_spatial_map``).
    """
    return (
        row.c,
        row.v,
        row.s,
        row.k,
        row.biocapacity_stock,
        row.energy_stock,
        row.raw_material_stock,
        row.internet_access_pct,
        row.surveillance_coupling,
    )


def select_hex_rows_for_emission(
    *,
    tick: int,
    candidate_rows: list[DynamicHexState],
    last_emitted: dict[str, tuple[float, ...]],
) -> list[DynamicHexState]:
    """Choose which candidate rows enter the tick's envelope.

    Args:
        tick: Tick being persisted.
        candidate_rows: The full frame the bridge would previously have
            emitted verbatim.
        last_emitted: Per-hex value tuples as of the last emission;
            **mutated in place** so the caller carries state across ticks.

    Returns:
        The rows to persist — the full frame on checkpoint ticks,
        otherwise only rows whose value tuple changed. Deterministic in
        the candidate order, so re-running a tick re-emits identical rows
        (idempotent under ``ON CONFLICT DO NOTHING``, FR-006).
    """
    if is_checkpoint_tick(tick):
        for row in candidate_rows:
            last_emitted[row.h3_index] = hex_value_key(row)
        return list(candidate_rows)

    changed: list[DynamicHexState] = []
    for row in candidate_rows:
        key = hex_value_key(row)
        if last_emitted.get(row.h3_index) != key:
            changed.append(row)
            last_emitted[row.h3_index] = key
    return changed


__all__ = [
    "CHECKPOINT_EVERY_TICKS",
    "hex_value_key",
    "is_checkpoint_tick",
    "select_hex_rows_for_emission",
]
