"""Launcher for the ``ArchiveApp`` key-figure honest-absence dossier snapshot test.

``pytest-textual-snapshot``'s ``snap_compare`` fixture resolves a string app
path relative to the *calling test file*, then executes that file via
``runpy.run_path`` with no package context — so the launched module must use
absolute imports (relative imports have no ``__package__`` to resolve
against). Colocating this launcher next to ``test_key_figure_page.py`` keeps
the path argument a trivial, stable relative reference.

A FRESH ``ArchiveApp`` is constructed here rather than importing a
module-level singleton, mirroring ``tests/unit/tui/snapshot_app.py``'s own
documented reason: ``runpy`` re-executes this file per snapshot run, but an
``import`` of a cached module would hand back the same shared instance — and
a Textual ``App`` any earlier in-process test already ran renders with stale
mounted state, an order-dependent snapshot flake.
"""

from pathlib import Path

from babylon.projection.fixtures.recorder import load_key_figure_fixture
from babylon.projection.vault.render_key_figure import render_key_figure
from babylon.tui.app import ArchiveApp
from babylon.tui.wikilinks import known_target_resolver

_FIXTURE = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "fixtures"
    / "projection"
    / "key_figure_kf-001.json"
)

_view = load_key_figure_fixture(_FIXTURE)
_page = render_key_figure(_view, verified_tick=_view.verified_tick)

app = ArchiveApp(
    page=_page,
    resolver=known_target_resolver(frozenset({f"key_figure/{_view.key_figure_id}"})),
)

__all__ = ["app"]
