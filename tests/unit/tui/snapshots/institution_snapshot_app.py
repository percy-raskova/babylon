"""Launcher for the institution-page snapshot test (Program 24 P2 WO-19).

See ``tests/unit/tui/snapshot_app.py`` for why this launcher builds a FRESH
``ArchiveApp`` from its own module-level construction rather than importing a
shared instance: ``pytest-textual-snapshot`` executes this file via
``runpy.run_path`` per snapshot run, and a cached import would hand back a
stale, already-mounted instance from an earlier in-process test.

Uses ``ArchiveApp``'s existing ``page``/``resolver``/``statblocks``
constructor injection points (public keel API since WO-5) rather than
touching ``babylon.tui.app`` itself — the shared-file discipline reserves
``KNOWN_ENTITIES``/``StatblockProvider`` *composition into the app's
defaults* for the serial Wave-2 WO-45; a Wave-1 page WO exercises the
provider seam directly instead, exactly as this launcher does.

Renders the real ``institution/doj`` dossier through the real
``project_institution`` -> ``render_institution`` pipeline. The fixture
graph is honestly all-attributed (unlike the committed, engine-harvested
``tests/fixtures/projection/institution_doj.json``, which is honestly
all-absent because no current scenario seeds an institution — see
``babylon.projection.institution``'s module docstring) so the golden shows
the full-dossier rendering path, not just the absence path (already the
subject of the committed fixture's own contract test).
"""

from babylon.models.enums.topology import NodeType
from babylon.projection.institution import project_institution
from babylon.projection.vault.render_institution import render_institution
from babylon.topology import BabylonGraph
from babylon.tui.app import ArchiveApp
from babylon.tui.wikilinks import known_target_resolver


def _doj_graph() -> BabylonGraph:
    graph = BabylonGraph()
    graph.add_node(
        "doj",
        NodeType.INSTITUTION,
        name="Department of Justice",
        apparatus_type="rsa_judicial",
        social_function="adjudication",
        class_inscription="bourgeois",
        legitimacy=0.7,
        budget=1_000_000.0,
        housed_org_ids=["fbi"],
        territory_ids=["us_national"],
        internal_balance={
            "liberal_technocratic": 0.5,
            "revanchist_fascist": 0.3,
            "institutionalist_bonapartist": 0.2,
        },
    )
    return graph


_VIEW = project_institution("doj", graph=_doj_graph(), tick=847)
_PAGE = render_institution(_VIEW, verified_tick=847)

app = ArchiveApp(
    page=_PAGE,
    resolver=known_target_resolver({"institution/doj"}),
)

__all__ = ["app"]
