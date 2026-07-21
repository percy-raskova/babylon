"""Launcher for the state-dossier-page TUI snapshot test (Program 24 P2 WO-16).

Mirrors ``tests/unit/tui/snapshot_app.py`` exactly for the state nesting
tier. ``pytest-textual-snapshot``'s ``snap_compare`` fixture resolves a
string app path relative to the *calling test file*, then executes that
file via ``runpy.run_path`` with no package context — so the launched
module must use absolute imports (relative imports have no ``__package__``
to resolve against). Colocating this launcher next to
``test_state_page.py`` keeps the path argument a trivial, stable relative
reference.

A FRESH ``ArchiveApp`` is constructed here rather than re-exporting any
cached module-level instance: ``runpy`` re-executes this file per snapshot
run, but an ``import`` of an already-run ``App`` would hand back stale
mounted state — an order-dependent snapshot flake (the same reasoning the
keel launcher documents).

Fixture-fed, no engine, no database (Program 24 P2's global invariant): the
page rendered here is the REAL ``render_state`` output for the committed
``tests/fixtures/projection/state_26.json`` fixture — the BAKED page a
player would actually see (S1 vault-as-contract; S3 bake-at-tick-commit),
not a live-provider demo. ``state_statblocks`` is still wired as the
fallback live provider for API completeness, though the baked fence body
below takes precedence per ``BabylonFence._directive_statblock``.
"""

from pathlib import Path

from babylon.projection.fixtures.recorder import load_state_fixture
from babylon.projection.state import state_statblocks
from babylon.projection.vault.render_state import render_state
from babylon.tui.app import ArchiveApp
from babylon.tui.wikilinks import known_target_resolver

_FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "fixtures"
    / "projection"
    / "state_26.json"
)

_view = load_state_fixture(_FIXTURE_PATH)
_page = render_state(_view, verified_tick=_view.verified_tick)

app = ArchiveApp(
    page=_page,
    resolver=known_target_resolver(frozenset({f"state/{_view.state_fips}"})),
    statblocks=state_statblocks,
)

__all__ = ["app"]
