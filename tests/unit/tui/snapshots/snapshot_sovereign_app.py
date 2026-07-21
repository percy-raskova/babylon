"""Launcher for the sovereign dossier page snapshot test (WO-20).

Mirrors ``tests/unit/tui/snapshot_app.py``'s discipline exactly: a FRESH
``ArchiveApp`` is built here (never a re-exported module-level singleton) so
``pytest-textual-snapshot``'s ``runpy``-per-run execution never hands back a
stale, already-mounted instance from an earlier in-process test.

Renders a *baked* sovereign dossier page — ``render_sovereign``'s actual
output for a fully-attributed ``SovereignView`` — through the real
``ArchiveApp``/``BabylonMarkdown`` pipeline: statblock fence (baked body,
not a live provider), the "## Claims" wikilink roster, and no absence
blocks (every field is attributed in this fixture).
"""

from babylon.projection.vault.render import render_sovereign
from babylon.projection.view_models import SovereignView
from babylon.tui.app import ArchiveApp
from babylon.tui.wikilinks import known_target_resolver

_VIEW = SovereignView(
    sovereign_id="SOV_USA_FED",
    verified_tick=5,
    name="United States Federal Government",
    sovereignty_type="recognized_state",
    legitimacy=0.82,
    ruling_faction_id="FAC_RESTORATIONIST",
    extraction_policy="intensify",
    capital_territory_id="T_DC",
    capital_county_fips="11001",
    founded_tick=0,
    claimed_county_fips=("26163",),
)

_PAGE = render_sovereign(_VIEW, verified_tick=5)

_KNOWN_ENTITIES = frozenset({"sovereign/SOV_USA_FED", "county/26163"})

app = ArchiveApp(page=_PAGE, resolver=known_target_resolver(_KNOWN_ENTITIES))

__all__ = ["app"]
