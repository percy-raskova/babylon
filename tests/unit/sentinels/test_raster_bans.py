"""Raster-lane bans: the two verified-hole closures from the M4 contract
(``docs/superpowers/specs/2026-07-27-m4-topology-contracts.md`` §5, §7).

Two independent grep-based bans over the checked-in Rust source — no Cargo
feature can gate either out, so the guarantee has to live in source text,
not compilation (the same cross-language-boundary problem
``test_rust_theme_parity.py`` solves for the theme constants: an FFI seam no
Python ``import`` can cross):

1. **§5 (Task 32's feature-gate ruling).**
   ``hypergraph_rs::raster::instruments::*``/``::deck::*``/``ingest::*`` pull
   in the crate's DeckWorld/spectral/CSV-ingest coupling that Task 33's
   generic scene builder deliberately strips — banned anywhere under
   ``rust/crates/babylon-tui/src/``.
2. **§7 (pixel-tier kickoff ruling).**
   ``Picker::from_query_stdio``/``_with_options`` re-queries the real
   terminal at construction time, which would break the ADR097 D4
   probe-once/never-re-probe promise the instant any crate reached for it —
   banned anywhere under ``rust/crates/``.

Mutation-validation (STANDING RULE: every sentinel is mutation-validated,
mirrored from the ``babylon.sentinels.vocabulary`` family's discipline):
each check function is exercised against a synthetic ``tmp_path`` tree that
plants exactly the banned substring, proving the grep actually fires rather
than vacuously passing because the real tree happens to be clean today.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BABYLON_TUI_SRC = _REPO_ROOT / "rust" / "crates" / "babylon-tui" / "src"
_RUST_CRATES = _REPO_ROOT / "rust" / "crates"

#: §5 — hypergraph_rs::raster submodules this port must never reach into.
_HYPERGRAPH_RS_BANS: tuple[str, ...] = ("instruments::", "::deck::", "ingest::")

#: §7 — the re-probing constructor path banned by the ADR097 D4 ruling.
#: A substring, deliberately: it also catches the `_with_options` variant.
_STDIO_PROBE_BAN = "from_query_stdio"


def _rs_files(root: Path) -> list[Path]:
    """Every ``.rs`` file under ``root``, sorted for deterministic output."""
    if not root.is_dir():
        return []
    return sorted(root.rglob("*.rs"))


def hypergraph_rs_ban_violations(src_root: Path) -> list[str]:
    """Return one ``file:line: pattern`` message per banned hypergraph_rs
    submodule reference found anywhere under ``src_root`` (§5)."""
    violations: list[str] = []
    for path in _rs_files(src_root):
        lines = path.read_text(encoding="utf-8").splitlines()
        for lineno, line in enumerate(lines, start=1):
            for banned in _HYPERGRAPH_RS_BANS:
                if banned in line:
                    rel = path.relative_to(src_root)
                    violations.append(f"{rel}:{lineno}: banned {banned!r} — {line.strip()}")
    return violations


def stdio_probe_ban_violations(crates_root: Path) -> list[str]:
    """Return one ``file:line`` message per ``from_query_stdio`` reference
    found anywhere under ``crates_root`` (§7)."""
    violations: list[str] = []
    for path in _rs_files(crates_root):
        lines = path.read_text(encoding="utf-8").splitlines()
        for lineno, line in enumerate(lines, start=1):
            if _STDIO_PROBE_BAN in line:
                rel = path.relative_to(crates_root)
                violations.append(f"{rel}:{lineno}: banned {_STDIO_PROBE_BAN!r} — {line.strip()}")
    return violations


# ---------------------------------------------------------------------------
# Liveness: the real tree is clean right now.
# ---------------------------------------------------------------------------


def test_no_hypergraph_rs_deck_world_coupling_in_babylon_tui_src() -> None:
    """§5: no DeckWorld/spectral/ingest submodule reference anywhere under
    ``rust/crates/babylon-tui/src/`` — Cargo features cannot gate these out,
    so the ban is a source-text guarantee, not a compile-time one."""
    assert hypergraph_rs_ban_violations(_BABYLON_TUI_SRC) == []


def test_no_stdio_probing_picker_construction_anywhere_in_rust_crates() -> None:
    """§7: no ``from_query_stdio``/``from_query_stdio_with_options`` call
    anywhere under ``rust/crates/`` — the ADR097 D4 probe-once promise would
    break the instant a runtime re-probe path existed, regardless of which
    crate reached for it."""
    assert stdio_probe_ban_violations(_RUST_CRATES) == []


# ---------------------------------------------------------------------------
# Mutation-validation: the checks actually fire (STANDING RULE, the
# vocabulary sentinel family's convention) rather than passing vacuously.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("banned", ["instruments::", "::deck::", "ingest::"])
def test_hypergraph_rs_ban_checker_fires_on_each_banned_substring(
    tmp_path: Path, banned: str
) -> None:
    """Each of the three banned substrings, planted alone, is caught —
    proving the check is not accidentally keyed to only one of the three."""
    (tmp_path / "sample.rs").write_text(
        f"use hypergraph_rs::raster::{banned}Something;\n", encoding="utf-8"
    )
    violations = hypergraph_rs_ban_violations(tmp_path)
    assert len(violations) == 1
    assert banned in violations[0]


def test_hypergraph_rs_ban_checker_ignores_clean_source(tmp_path: Path) -> None:
    """A file that never mentions any banned submodule produces zero
    violations — the check does not over-fire on ordinary raster imports
    (`raster_bridge.rs`'s real ``hypergraph_rs::raster::{CellGrid, Rgb}``)."""
    (tmp_path / "sample.rs").write_text(
        "use hypergraph_rs::raster::{CellGrid, Rgb};\n", encoding="utf-8"
    )
    assert hypergraph_rs_ban_violations(tmp_path) == []


def test_stdio_probe_ban_checker_fires_on_from_query_stdio(tmp_path: Path) -> None:
    """The banned constructor, planted in a synthetic multi-crate tree, is
    caught regardless of which crate under ``rust/crates/`` it lives in."""
    crate_src = tmp_path / "some-crate" / "src"
    crate_src.mkdir(parents=True)
    (crate_src / "picker.rs").write_text(
        "let picker = Picker::from_query_stdio()?;\n", encoding="utf-8"
    )
    violations = stdio_probe_ban_violations(tmp_path)
    assert len(violations) == 1
    assert "from_query_stdio" in violations[0]


def test_stdio_probe_ban_checker_fires_on_the_with_options_variant(tmp_path: Path) -> None:
    """``from_query_stdio_with_options`` is a superset of the bare name, so
    the same substring check catches it too — no second pattern needed."""
    crate_src = tmp_path / "some-crate" / "src"
    crate_src.mkdir(parents=True)
    (crate_src / "picker.rs").write_text(
        "let picker = Picker::from_query_stdio_with_options(opts)?;\n", encoding="utf-8"
    )
    assert len(stdio_probe_ban_violations(tmp_path)) == 1


def test_stdio_probe_ban_checker_ignores_clean_source(tmp_path: Path) -> None:
    """Ordinary ``StatefulProtocol::new`` construction (the ADR097 D4
    sanctioned path, §7) never fires."""
    crate_src = tmp_path / "some-crate" / "src"
    crate_src.mkdir(parents=True)
    (crate_src / "picker.rs").write_text(
        "let protocol = StatefulProtocol::new(image, font_size, None, protocol_type);\n",
        encoding="utf-8",
    )
    assert stdio_probe_ban_violations(tmp_path) == []
