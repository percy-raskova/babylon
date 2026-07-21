"""Launcher for the ``ArchiveApp`` snapshot test.

``pytest-textual-snapshot``'s ``snap_compare`` fixture resolves a string app
path relative to the *calling test file*, then executes that file via
``runpy.run_path`` with no package context — so the launched module must use
absolute imports (relative imports have no ``__package__`` to resolve
against). Colocating this launcher next to ``test_snapshot.py`` keeps the
path argument a trivial, stable relative reference.

A FRESH ``ArchiveApp`` is constructed here rather than re-exporting the
module-level singleton from ``babylon.tui.app``: ``runpy`` re-executes this
file per snapshot run, but an ``import`` of the cached module would hand
back the same shared instance — and a Textual ``App`` that any earlier
in-process test already ran renders with stale mounted state, an
order-dependent snapshot flake.
"""

from babylon.tui.app import ArchiveApp

app = ArchiveApp()

__all__ = ["app"]
