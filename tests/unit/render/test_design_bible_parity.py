"""DESIGN_BIBLE §9b degraded row must equal the code constant (ADR097 D5).

The doc cites ``DEGRADED_256_PALETTE`` as the single source of truth; this test is
the enforcement — a drift in either side fails here.
"""

from __future__ import annotations

import re
from pathlib import Path

from babylon.render.tiers import DEGRADED_256_PALETTE, TRUECOLOR_PALETTE, RoleToken

DESIGN_BIBLE = (
    Path(__file__).resolve().parents[3]
    / "project"
    / "research"
    / "16-living-map"
    / "DESIGN_BIBLE.md"
)
_ROW = re.compile(r"^\|\s*`([a-z_]+)`\s*\|\s*(#[0-9a-fA-F]{6})\s*\|\s*(\d+)\s*\|")


def _parse_degraded_rows() -> dict[str, tuple[str, int]]:
    text = DESIGN_BIBLE.read_text(encoding="utf-8")
    marker = "Degraded palette (256-color, ADR097 D5)"
    assert marker in text, f"missing §9b subsection heading: {marker!r}"
    section = text.split(marker, 1)[1]
    rows: dict[str, tuple[str, int]] = {}
    for line in section.splitlines():
        match = _ROW.match(line.strip())
        if match:
            rows[match.group(1)] = (match.group(2).lower(), int(match.group(3)))
    return rows


def test_design_bible_degraded_row_matches_code() -> None:
    rows = _parse_degraded_rows()
    expected = {
        token.value: (TRUECOLOR_PALETTE[token], DEGRADED_256_PALETTE[token]) for token in RoleToken
    }
    assert rows == expected
