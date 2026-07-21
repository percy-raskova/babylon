"""Seed widget: parity (D2) + determinism (D3) contracts for ADR097.

Parity: the plate data model is tier-independent — the pixel path exposes no data
field the glyph path lacks (asserted on the model, not screenshots). Determinism:
the committed SVG snapshot is the III.13 same-state-same-bytes contract, via
pytest-textual-snapshot (Textual's native SVG export).
"""

from __future__ import annotations

import dataclasses

from babylon.render.tiers import (
    DEGRADED_256_PALETTE,
    TRUECOLOR_PALETTE,
    PaletteTier,
    RoleToken,
)
from babylon.render.widgets.palette_plate import (
    PalettePlateApp,
    PaletteRow,
    plate_model,
    swatch_cell,
)


def test_plate_model_covers_every_role_token() -> None:
    tokens = [row.token for row in plate_model()]
    assert tokens == list(RoleToken)


def test_plate_model_rows_carry_both_representations() -> None:
    for row in plate_model():
        assert row.truecolor_hex == TRUECOLOR_PALETTE[row.token]
        assert row.xterm256 == DEGRADED_256_PALETTE[row.token]


def test_information_parity_model_is_tier_independent() -> None:
    # The parity rule (D2): the model is one object for BOTH tiers — there is no
    # tier parameter and no tier-specific field. Tier only selects which cell text
    # is drawn (swatch_cell), never which data exists.
    fields = (
        {f.name for f in dataclasses.fields(PaletteRow.__pydantic_dataclass__)}
        if hasattr(PaletteRow, "__pydantic_dataclass__")
        else set(PaletteRow.model_fields)
    )
    assert fields == {"token", "truecolor_hex", "xterm256"}
    # Same rows regardless of which palette a caller intends to display.
    assert plate_model() == plate_model()


def test_swatch_cell_selects_representation_by_palette() -> None:
    row = next(r for r in plate_model() if r.token is RoleToken.ACCENT_CRIMSON)
    truecolor = swatch_cell(row, PaletteTier.TRUECOLOR)
    degraded = swatch_cell(row, PaletteTier.DEGRADED_256)
    assert "#dc143c" in truecolor
    assert "161" in degraded  # the computed nearest index for crimson


def test_palette_plate_snapshot(snap_compare) -> None:  # type: ignore[no-untyped-def]
    # III.13 determinism: same state -> byte-identical SVG. First run generates the
    # baseline with --snapshot-update; thereafter this asserts it never drifts.
    assert snap_compare(PalettePlateApp())
