"""Contract tests for WO-44 part 4: the per-kind Archive tick baker.

``ArchiveTickBaker`` generalizes the keel's county-only baker: at every
committed tick it composes ONE pages dict across every bakeable kind —
counties from the configured scope, states derived from the scope's FIPS
prefixes, the national dossier, graph-enumerated organizations /
institutions / sovereigns / industries / social classes, and
membership-enumerated communities — and lands them as ONE
content-hash-skipped commit (the WO-44 vault-at-scale contract).
Key figures are deliberately absent: the kind has no producer, so there
are no ids to enumerate (honest absence, not an oversight).
"""

from __future__ import annotations

from pathlib import Path

from babylon.models.entities.community import CommunityMembership
from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.enums import CommunityType, SocialRole
from babylon.models.enums.topology import NodeType
from babylon.models.world_state import WorldState
from babylon.projection.vault.materializer import VaultMaterializer
from babylon.projection.vault.tick_baker import ArchiveTickBaker

WAYNE = "26163"


def _world() -> WorldState:
    entity = SocialClass(
        id="C001",
        name="Test C001",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=1.0,
        ideology=IdeologicalProfile(class_consciousness=0.5, national_identity=0.5),
        p_acquiescence=0.6,
        p_revolution=0.4,
        population=100,
        county_fips=WAYNE,
        community_memberships=[
            CommunityMembership(agent_id="C001", community_type=CommunityType.SETTLER)
        ],
    )
    return WorldState(entities={entity.id: entity})


def _graph(world: WorldState):  # type: ignore[no-untyped-def]
    graph = world.to_graph()
    graph.add_node(
        "T001",
        NodeType.TERRITORY,
        county_fips=WAYNE,
        tick_median_wage=19.85,
        legitimation_index=0.71,
    )
    graph.add_node("ORG1", NodeType.ORGANIZATION, name="Rev Workers Party")
    return graph


def _bake(root: Path, tick: int = 7) -> Path:
    world = _world()
    baker = ArchiveTickBaker(VaultMaterializer(root), (WAYNE,))
    baker.on_tick_committed(tick=tick, world=world, graph=_graph(world))
    return root


class TestArchiveTickBaker:
    def test_bakes_every_enumerable_kind_in_one_tick(self, tmp_path: Path) -> None:
        root = _bake(tmp_path / "vault")
        for page in (
            f"county/{WAYNE}.md",
            "state/26.md",
            "national/USA.md",
            "economy/USA.md",
            "organization/ORG1.md",
            "social_class/C001.md",
            "community/settler.md",
        ):
            assert (root / page).is_file(), f"{page} not baked"

    def test_no_key_figure_pages_without_a_producer(self, tmp_path: Path) -> None:
        root = _bake(tmp_path / "vault")
        assert not (root / "key_figure").exists()

    def test_the_whole_tick_is_one_commit(self, tmp_path: Path) -> None:
        from dulwich.repo import Repo

        root = _bake(tmp_path / "vault")
        repo = Repo(str(root))
        try:
            assert sum(1 for _ in repo.get_walker()) == 1
        finally:
            repo.close()

    def test_two_independent_bakes_are_byte_identical_commits(self, tmp_path: Path) -> None:
        from dulwich.repo import Repo

        heads: list[bytes] = []
        for name in ("a", "b"):
            root = _bake(tmp_path / name)
            repo = Repo(str(root))
            try:
                heads.append(repo.head())
            finally:
                repo.close()
        assert heads[0] == heads[1]

    def test_a_quiet_second_tick_costs_no_commit(self, tmp_path: Path) -> None:
        """Same state re-baked at the same tick → content-hash skip."""
        from dulwich.repo import Repo

        root = tmp_path / "vault"
        world = _world()
        graph = _graph(world)
        baker = ArchiveTickBaker(VaultMaterializer(root), (WAYNE,))
        baker.on_tick_committed(tick=7, world=world, graph=graph)
        baker.on_tick_committed(tick=7, world=world, graph=graph)
        repo = Repo(str(root))
        try:
            assert sum(1 for _ in repo.get_walker()) == 1
        finally:
            repo.close()
