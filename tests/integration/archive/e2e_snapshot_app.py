"""Snapshot launcher for the county end-to-end golden (P1 exit).

Builds the ArchiveApp over the page baked from the COMMITTED projection
fixture (``tests/fixtures/projection/county_26163.json``) — the same bytes
the live tick→projection equality test pins against the engine — so the SVG
golden certifies the fixture → baked page → rendered chain, and the equality
test certifies tick → projection ≡ fixture. Together: the full P1 exit
pipeline.

``pytest-textual-snapshot`` executes this file via ``runpy`` with no package
context: absolute imports only, and a module-level ``app`` built fresh per
run (the singleton-reuse flake class fixed earlier tonight).
"""

from __future__ import annotations

from pathlib import Path

from babylon.projection.fixtures.recorder import load_county_fixture
from babylon.projection.vault.render import render_county
from babylon.tui.app import ArchiveApp
from babylon.tui.wikilinks import known_target_resolver

_REPO_ROOT = Path(__file__).resolve().parents[3]
_FIXTURE = _REPO_ROOT / "tests" / "fixtures" / "projection" / "county_26163.json"

_view = load_county_fixture(_FIXTURE)
_page = render_county(_view, verified_tick=_view.verified_tick)

app = ArchiveApp(
    page=_page,
    resolver=known_target_resolver(frozenset({"county/26163"})),
)
