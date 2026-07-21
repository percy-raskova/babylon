"""Launcher for the national-dossier-page ``ArchiveApp`` snapshot test (WO-17).

Same rationale as ``tests/unit/tui/snapshot_app.py``: ``pytest-textual-
snapshot``'s ``snap_compare`` fixture executes this file via
``runpy.run_path`` with no package context, so absolute imports only, and a
FRESH ``ArchiveApp`` is constructed here rather than re-exporting a shared
module-level singleton (a Textual ``App`` any earlier in-process test already
ran renders with stale mounted state — an order-dependent snapshot flake).

Renders a fully-baked national dossier page — ``render_national``'s own
output, numbers already embedded in the ``{statblock}`` fence body exactly as
the vault materializer would write it (Constitution III.13: a materialized
view renders from its own bytes, never a live provider) — through the same
``ArchiveApp``/``BabylonMarkdown`` shell the county sample page uses.
"""

from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.enums import SocialRole
from babylon.models.enums.topology import EdgeType, NodeType
from babylon.models.world_state import WorldState
from babylon.projection.national import project_national
from babylon.projection.vault.render_national import render_national
from babylon.topology import BabylonGraph
from babylon.tui.app import ArchiveApp
from babylon.tui.wikilinks import known_target_resolver

_WAYNE = "26163"

_graph = BabylonGraph()
_graph.add_node(
    "T001",
    NodeType.TERRITORY,
    county_fips=_WAYNE,
    tick_median_wage=19.85,
    tick_bifurcation_score=-0.14,
    tick_class_distribution={
        "bourgeoisie": 0.077,
        "petit_bourgeoisie": 0.191,
        "labor_aristocracy": 0.226,
        "proletariat": 0.382,
        "lumpenproletariat": 0.124,
    },
    legitimation_index=0.71,
)
_graph.add_node("SOV_USA", NodeType.SOVEREIGN, name="United States")
_graph.add_edge("SOV_USA", "T001", EdgeType.CLAIMS)

_entity = SocialClass(
    id="C001",
    name="Test C001",
    role=SocialRole.PERIPHERY_PROLETARIAT,
    wealth=1.0,
    ideology=IdeologicalProfile(class_consciousness=0.5, national_identity=0.2),
    p_acquiescence=0.65,
    p_revolution=0.30,
    population=1_749_343,
    county_fips=_WAYNE,
)
_world = WorldState(entities={_entity.id: _entity})

_view = project_national("USA", graph=_graph, world=_world, tick=847)
_page = render_national(_view, verified_tick=847)

app = ArchiveApp(
    page=_page,
    resolver=known_target_resolver(frozenset({"national/USA", "sovereign/SOV_USA"})),
)

__all__ = ["app"]
