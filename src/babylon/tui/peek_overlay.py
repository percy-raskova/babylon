"""``PeekOverlay`` — the transient S7 depth-1 preview widget (unit
"peek-hover-wire", shell-interconnect).

S7 (``ai/_inbox/tui/20260719archiveinterfacedesign.md``): "Keyboard peek is
first-class; mouse hover works but is never load-bearing." :mod:`babylon.tui.peek`
already ships the one ``peek(entity, depth)`` renderer; :mod:`babylon.tui.directives`
already posts :class:`~babylon.tui.directives.DirectiveHover` on mouse Enter/Leave
over a fenced directive plate; :mod:`babylon.tui.wikilinks` already colors known/
unknown wikilink spans. Before this unit nothing consumed the hover message and no
keyboard path existed at all — both were "sent into the void" (this module's own
originating unit brief). This widget is the one thing both paths were missing: a
mounted sink to actually SHOW the depth-1 plate :func:`~babylon.tui.peek.peek`
already knows how to build.

**Mount once, toggle forever — never mount/unmount per hover.** A ``DirectiveHover``
Enter/Leave pair can fire many times per session (every mouse pass over a statblock
plate); mounting a fresh widget on every Enter and awaiting its removal on every Leave
would mean this overlay's own lifecycle is an async race the "Known risks" section of
this unit's own brief explicitly flags ("New overlay lifecycle (mount/dismiss on
leave/blur)"). Composing exactly one instance up front (:class:`~babylon.tui.app.
ArchiveApp.compose`) and toggling :attr:`~textual.widget.Widget.display` sidesteps
that race entirely — showing/hiding is synchronous, no ``await``, no partial-mount
window where a Leave could race a not-yet-mounted Enter.

**Depth is always 1 here.** S7's own depth table names ``1`` as exactly "an
Obsidian-style hover preview (a small popup on a wikilink)" — the size this widget
exists to show. :class:`~babylon.tui.app.ArchiveApp` is the one that calls
:func:`~babylon.tui.peek.peek` (``depth=1``) and hands the resulting
:class:`~rich.panel.Panel`/absence :class:`~rich.text.Text` in via :meth:`show_peek`;
this widget never calls ``peek`` itself and carries no subject-resolution logic of its
own — it is a pure sink, the same "renderer vs. widget" separation
:mod:`babylon.tui.peek`'s own module docstring draws.

**No new KSBC hex literals.** :func:`~babylon.tui.peek.peek`'s own ``Panel``/``Text``
already carries the crimson-border/gold-title styling (:mod:`babylon.tui.theme`'s
``CRIMSON``/``GOLD``, at Rich-renderable granularity — that module's own docstring:
"this function's output has no widget/App context to resolve ``$theme`` variables
against"). This widget's OWN ``DEFAULT_CSS`` only positions the box (``dock``/
``margin``/sizing/``display``) — no color rule of its own, so there is nothing here
that could drift from ``theme.py``.
"""

from __future__ import annotations

from rich.console import RenderableType
from textual.widgets import Static

__all__ = ["PeekOverlay"]


class PeekOverlay(Static):
    """A transient, dockable peek-preview plate — hidden until shown.

    Composed once by :class:`~babylon.tui.app.ArchiveApp` (``display: none``
    at boot, matching every other honest-absence-by-default surface in this
    shell); :meth:`show_peek`/:meth:`hide_peek` toggle visibility and content
    together, never separately (there is no state where the overlay is
    visible but stale, or invisible but holding content a later show would
    need to overwrite first).
    """

    DEFAULT_CSS = """
    PeekOverlay {
        display: none;
        dock: top;
        height: auto;
        max-height: 40%;
        width: auto;
        max-width: 70%;
        margin: 3 2;
    }
    """

    def show_peek(self, content: RenderableType) -> None:
        """Paint ``content`` and reveal the overlay.

        :param content: the renderable to show — normally
            :func:`~babylon.tui.peek.peek`'s own ``depth=1`` return value
            (a :class:`~rich.panel.Panel`), or an honest absence
            :class:`~rich.text.Text` when the caller could not resolve a
            live view-model for whatever is being peeked (Constitution
            III.11 — never left blank, never silently skipped).
        """
        self.update(content)
        self.display = True

    def hide_peek(self) -> None:
        """Hide the overlay — idempotent (hiding an already-hidden overlay
        is not an error, mirroring :meth:`~babylon.tui.watchlist.
        WatchlistState.unpin`'s own no-op-on-redundant-call idiom)."""
        self.display = False
