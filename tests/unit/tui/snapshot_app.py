"""Launcher for the ``ArchiveApp`` snapshot test.

``pytest-textual-snapshot``'s ``snap_compare`` fixture resolves a string app
path relative to the *calling test file*, then executes that file via
``runpy.run_path`` with no package context — so the launched module must use
absolute imports (relative imports have no ``__package__`` to resolve
against). Colocating this launcher next to ``test_snapshot.py`` keeps the
path argument a trivial, stable relative reference; it just re-exports the
module-level ``app`` instance ``import_app`` looks for by default.
"""

from babylon.tui.app import app

__all__ = ["app"]
