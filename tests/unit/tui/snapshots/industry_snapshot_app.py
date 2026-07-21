"""Snapshot launcher for the industry dossier page (WO-22, mirrors e2e_snapshot_app.py).

Builds the ``ArchiveApp`` over the page baked from the COMMITTED industry
projection fixture (``tests/fixtures/projection/industry_ind_31-33.json``) —
the honest-absence fixture recorded by
``tools/record_industry_fixture.py`` (the ``single_county`` scenario seeds no
``industries`` at all, so every field but identity/``verified_tick`` is
``None`` here; the page therefore renders an empty statblock and one
{absence} block per field).

``pytest-textual-snapshot`` executes this file via ``runpy`` with no package
context: absolute imports only, and a module-level ``app`` built fresh per
run (the singleton-reuse flake class the keel fixed).
"""

from __future__ import annotations

from pathlib import Path

from babylon.projection.fixtures.recorder import load_industry_fixture
from babylon.projection.vault.render_industry import render_industry
from babylon.tui.app import ArchiveApp
from babylon.tui.wikilinks import known_target_resolver

_REPO_ROOT = Path(__file__).resolve().parents[4]
_FIXTURE = _REPO_ROOT / "tests" / "fixtures" / "projection" / "industry_ind_31-33.json"

_view = load_industry_fixture(_FIXTURE)
_page = render_industry(_view, verified_tick=_view.verified_tick)

app = ArchiveApp(
    page=_page,
    resolver=known_target_resolver(frozenset({"industry/ind_31-33"})),
)
