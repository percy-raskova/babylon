"""Launcher for the ``unresolved`` epilogue page snapshot test (WO-34).

``pytest-textual-snapshot``'s ``snap_compare`` fixture resolves a string app
path relative to the *calling test file*, then executes that file via
``runpy.run_path`` with no package context — so the launched module must use
absolute imports. Colocating this launcher next to
``test_epilogue_page.py`` keeps the path argument a trivial, stable
relative reference (mirrors ``tests/unit/tui/snapshot_app.py``).

Renders through the real ``ArchiveApp`` shell (KSBC theme, ``BabylonMarkdown``
directive dispatch, footer/status chrome) via its existing ``page=``
constructor parameter — WO-34 does not touch ``src/babylon/tui/app.py``;
this launcher only *instantiates* the class with page content ``ArchiveApp``
already supports handing in.

A FRESH ``ArchiveApp`` is constructed here rather than reusing any
module-level singleton: ``runpy`` re-executes this file per snapshot run,
but an imported cached instance would carry stale mounted state from an
earlier in-process test — an order-dependent snapshot flake.
"""

from babylon.projection.vault.render_epilogue import render_epilogue
from babylon.tui.app import ArchiveApp
from babylon.tui.wikilinks import known_target_resolver

app = ArchiveApp(
    page=render_epilogue("unresolved"),
    resolver=known_target_resolver(frozenset()),
    statblocks=lambda _subject: None,
)

__all__ = ["app"]
