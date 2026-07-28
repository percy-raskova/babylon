"""Rust-source extractors for sentinels (layer 0.5 — text, never a compiler).

Born at the M7 cutover (``docs/superpowers/specs/2026-07-28-m7-cutover-contracts.md``
§5.5): the Textual client's ``class X: BINDINGS = [Binding(...)]`` idiom —
what the ``declared_bindings`` AST helper read — was deleted with the Textual
estate (the helper retired with it), and the Rust client's single source of truth for
player-facing options is the keybar's hint tables
(``rust/crates/babylon-tui/src/views/keybar.rs`` — Wave 1's "one source of
truth: the keybar and the help screen cannot drift apart"). This module reads
that Rust source as TEXT (the ``tests/unit/render/test_rust_theme_parity.py``
precedent — no Rust toolchain in the sentinel lane), with a line-oriented
state machine matched to the file's own three declared shapes:

- ``const GLOBAL_TAIL: &[Hint] = &[...]`` — attributed to surface ``Global``;
- ``hints()``'s ``match surface`` arms — ``KeybarSurface::<Variant>``
  (``Rail { watchlist: true }`` → ``RailWatchlist``, ``false`` → ``Rail``);
- ``help_sections()``'s per-section extras — attributed to the section's own
  ``KeybarSurface`` token (the ``EVERYWHERE`` section deliberately rides its
  declared ``BareWiki`` placeholder surface — deterministic, never guessed).

Going dark is itself a failure here: zero parsed rows raises, and
:mod:`babylon.sentinels.tutorial_coverage.checks` additionally gates on a
declared floor (the vacuous-green dark-sentinel class — the standing
sentinel-every-error-class rule).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

from babylon.sentinels.base import SentinelCheckError

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["declared_keybar_hints"]

#: One ``hint("<key>", "<label>", ...)`` row (keys/labels carry no escapes).
_HINT_RE: Final = re.compile(r'hint\("([^"]+)",\s*"([^"]+)"')

#: A ``KeybarSurface::<Variant>`` token, with the ``Rail { watchlist: ... }``
#: struct-variant qualifier when present.
_SURFACE_RE: Final = re.compile(r"KeybarSurface::(\w+)(?:\s*\{\s*watchlist:\s*(true|false))?")

#: The global-tail block opener.
_GLOBAL_TAIL_RE: Final = re.compile(r"const GLOBAL_TAIL:")


def _surface_name(match: re.Match[str]) -> str:
    """Resolve a ``_SURFACE_RE`` match to the sentinel's surface name.

    :param match: a match carrying the variant and optional watchlist flag.
    :returns: the flat surface name (``Rail{watchlist: true}`` →
        ``RailWatchlist``).
    """
    variant, watchlist = match.group(1), match.group(2)
    if variant == "Rail":
        return "RailWatchlist" if watchlist == "true" else "Rail"
    return variant


def declared_keybar_hints(path: Path) -> tuple[tuple[str, str, str, int], ...]:
    """Every keybar hint row, as ``(surface, key, label, line)`` tuples.

    The union of the ``GLOBAL_TAIL`` cluster (surface ``Global``), every
    ``hints()`` match arm, and every ``help_sections()`` extra — deduplicated
    on ``(surface, key)`` keeping the first occurrence, in source order.

    :param path: the keybar source file
        (``rust/crates/babylon-tui/src/views/keybar.rs``).
    :returns: parsed rows, deterministically ordered.
    :raises SentinelCheckError: if the file is missing or yields zero rows —
        a dark extractor is a broken gate, never a clean one.
    """
    if not path.is_file():
        msg = f"keybar source missing: {path} — the option universe cannot be read"
        raise SentinelCheckError(msg)
    rows: list[tuple[str, str, str, int]] = []
    seen: set[tuple[str, str]] = set()
    surface: str | None = None
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if _GLOBAL_TAIL_RE.search(line):
            surface = "Global"
        else:
            surface_match = _SURFACE_RE.search(line)
            if surface_match is not None:
                surface = _surface_name(surface_match)
        if surface is None:
            continue
        for hint_match in _HINT_RE.finditer(line):
            key, label = hint_match.group(1), hint_match.group(2)
            if (surface, key) in seen:
                continue
            seen.add((surface, key))
            rows.append((surface, key, label, lineno))
    if not rows:
        msg = f"keybar extractor parsed ZERO hint rows from {path} — dark, not clean"
        raise SentinelCheckError(msg)
    return tuple(rows)
