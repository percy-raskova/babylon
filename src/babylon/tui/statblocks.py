"""Statblock row shapes — the projection-facing typing seam.

Split from :mod:`babylon.tui.directives` at the M7 cutover decoupling:
``babylon.projection.organization``/``institution`` type-check against these
aliases (``TYPE_CHECKING`` imports), so they must survive the Textual
estate's deletion. Pure typing, no Textual.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

__all__ = ["StatblockProvider", "StatblockRow"]

StatblockRow = tuple[str, str]
StatblockProvider = Callable[[str], Sequence[StatblockRow] | None]
"""Looks up statblock rows for a subject id. ``None`` means "no projection
for this subject" and renders as an absence block — never a fabricated
plausible-looking default (Constitution III.11)."""
