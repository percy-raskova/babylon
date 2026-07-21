"""Launcher for the social-class page snapshot test (Program 24 P2 WO-23).

Mirrors ``tests/integration/archive/e2e_snapshot_app.py``'s pattern for the
county keel golden: builds the ``ArchiveApp`` over the page BAKED from the
COMMITTED projection fixture (``tests/fixtures/projection/social_class_C004.json``)
so the golden certifies the fixture -> baked page -> rendered chain.

``pytest-textual-snapshot``'s ``snap_compare`` fixture resolves a string app
path relative to the *calling test file*, then executes that file via
``runpy.run_path`` with no package context — so this launcher uses absolute
imports and builds a FRESH ``ArchiveApp`` here rather than importing a cached
module-level singleton (module-singleton reuse is a known snapshot-flake
class — see ``babylon.tui.app``'s own snapshot launcher docstring).
"""

from __future__ import annotations

from pathlib import Path

from babylon.projection.fixtures.recorder import load_social_class_fixture
from babylon.projection.social_class import social_class_statblocks
from babylon.projection.vault.render_social_class import render_social_class
from babylon.tui.app import ArchiveApp
from babylon.tui.wikilinks import known_target_resolver

_REPO_ROOT = Path(__file__).resolve().parents[4]
_FIXTURE = _REPO_ROOT / "tests" / "fixtures" / "projection" / "social_class_C004.json"

_view = load_social_class_fixture(_FIXTURE)
_page = render_social_class(_view, verified_tick=_view.verified_tick)

app = ArchiveApp(
    page=_page,
    resolver=known_target_resolver(frozenset({"social_class/C004", "county/26163"})),
    statblocks=social_class_statblocks(_view),
)

__all__ = ["app"]
