"""The wikilink grammar — the pure, textual-free core of ``[[target]]``.

Split from :mod:`babylon.tui.wikilinks` at the M7 cutover decoupling:
:mod:`babylon.tui.shell.backlinks` (a real runtime dependency of the Rust
host's backlink index) needs :data:`WIKILINK_RE` without dragging Textual
in. The markdown-it rule and the Textual content mixin stay in
``wikilinks.py`` (deleted with the Textual estate at the ceremony).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from typing import Final

__all__ = ["WIKILINK_RE", "WikilinkResolver", "known_target_resolver"]

WIKILINK_RE: Final = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
"""Matches ``[[target]]`` or ``[[target|alias]]``; ``|`` and ``]`` cannot
appear inside ``target`` so aliasing is unambiguous."""

WikilinkResolver = Callable[[str], bool]
"""A callable returning ``True`` when ``target`` is a known Archive entity id."""


def known_target_resolver(known: Iterable[str]) -> WikilinkResolver:
    """Build a :data:`WikilinkResolver` from a fixed collection of ids.

    :param known: entity ids considered resolvable.
    :returns: a resolver closing over a frozen copy of ``known``.
    """
    known_ids = frozenset(known)
    return lambda target: target in known_ids
