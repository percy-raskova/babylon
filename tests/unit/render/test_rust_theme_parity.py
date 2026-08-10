"""Cross-language ksbc palette parity: the Rust client's palette constants
must track :data:`babylon.render.tiers.TRUECOLOR_PALETTE` (the §9b SSOT).

Re-created for Program 28 B0 (Amendment AF, ADR186 sentinel disposition
table: this guard PORTS, it does not retire). The Ratatui client's
``rust/crates/babylon-tui/src/theme.rs`` is gone with the rest of that
estate; the guard now re-points at the Bevy client's
``rust/crates/babylon-client/src/palette.rs``, which restates the same §9b
role colors as ``Color::srgb_u8(r, g, b)`` literals — an FFI boundary no
import can cross, so this guard PARSES the Rust source instead (the same
drift class the Program 24 P7 palette-SSOT pass eliminated Python-side via
``test_design_bible_parity.py``: theme-local literals silently diverging
from §9b). A §9b revision that moves a token now turns this red instead of
leaving the Rust plates painting the stale color forever.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from babylon.render.tiers import TRUECOLOR_PALETTE, RoleToken

_PALETTE_RS = (
    Path(__file__).resolve().parents[3]
    / "rust"
    / "crates"
    / "babylon-client"
    / "src"
    / "palette.rs"
)

_CONST_RE = re.compile(
    r"pub const (?P<name>[A-Z_]+): Color = Color::srgb_u8\("
    r"(?P<r>\d+), (?P<g>\d+), (?P<b>\d+)\);"
)

#: Rust constant name -> the §9b role token it mirrors.
_ROLE_BY_CONSTANT: dict[str, RoleToken] = {
    "FIELD": RoleToken.FIELD,
    "BONE": RoleToken.TEXT,
    "CRIMSON": RoleToken.ACCENT_CRIMSON,
    "GOLD": RoleToken.ACCENT_GOLD,
    "DIM": RoleToken.MUTED_DIM,
    "MUTED_DARK": RoleToken.MUTED_DARK,
    "ROYAL": RoleToken.ROYAL,
    "GREEN_DARK": RoleToken.GREEN_DARK,
}


def _rust_constants() -> dict[str, tuple[int, int, int]]:
    """Parse ``palette.rs``'s one-line ``Color::srgb_u8`` constants."""
    source = _PALETTE_RS.read_text(encoding="utf-8")
    found = {m["name"]: (int(m["r"]), int(m["g"]), int(m["b"])) for m in _CONST_RE.finditer(source)}
    assert found, f"no Color::srgb_u8 constants parsed from {_PALETTE_RS}"
    return found


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


@pytest.mark.parametrize(("constant", "token"), sorted(_ROLE_BY_CONSTANT.items()))
def test_rust_constant_matches_truecolor_palette(constant: str, token: RoleToken) -> None:
    """Each Rust palette constant equals its §9b token's truecolor value."""
    rust = _rust_constants()
    assert constant in rust, (
        f"{constant} missing from palette.rs — keep each constant on one line "
        f"(the guard's regex contract, stated in palette.rs's module docs)"
    )
    expected = _hex_to_rgb(TRUECOLOR_PALETTE[token])
    assert rust[constant] == expected, (
        f"palette.rs {constant} = {rust[constant]} but §9b {token} = "
        f"{expected} — update the Rust side (tiers.py is the SSOT)"
    )


def test_every_rust_constant_is_mapped() -> None:
    """A new palette.rs constant must be added to the mapping here — an
    unmapped constant is an unguarded literal, the exact drift class this
    file exists to prevent."""
    unmapped = set(_rust_constants()) - set(_ROLE_BY_CONSTANT)
    assert not unmapped, f"unmapped palette.rs constants: {sorted(unmapped)}"
