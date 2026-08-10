"""Statblock row shapes — the projection-facing typing seam.

Split from ``babylon.tui.directives`` at the M7 cutover decoupling, then
relocated from ``babylon.tui.statblocks`` to this package by the Amendment
AF (ADR186) deletion ceremony: ``babylon.projection.organization``/
``institution`` type-check against these aliases (``TYPE_CHECKING``
imports), so they had to survive both the Textual estate's deletion and the
Ratatui estate's — the aliases naturally belong in ``babylon.projection``
now that no client package remains to own them. Pure typing, no rendering
technology of any kind.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

__all__ = ["StatblockProvider", "StatblockRow"]

StatblockRow = tuple[str, str]
StatblockProvider = Callable[[str], Sequence[StatblockRow] | None]
"""Looks up statblock rows for a subject id. ``None`` means "no projection
for this subject" and renders as an absence block — never a fabricated
plausible-looking default (Constitution III.11)."""
