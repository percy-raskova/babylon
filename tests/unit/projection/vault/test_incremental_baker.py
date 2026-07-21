"""Contract tests for the incremental dirty-entity baker (Unit T4-core/C5).

Fixture: three counties across two states (Wayne + one more Michigan county,
plus a Cook County/Illinois county — two states + one national dossier),
one organization, one social class attributed to Wayne, one community
membership. Mirrors :mod:`tests.unit.projection.vault.
test_archive_tick_baker`'s fixture shape, widened enough to exercise
state/national rollup derivation across more than one state.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import babylon.projection.vault.incremental_baker as incremental_baker_module
from babylon.models.entities.community import CommunityMembership
from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.enums import CommunityType, SocialRole
from babylon.models.enums.topology import NodeType
from babylon.models.world_state import WorldState
from babylon.projection.vault.incremental_baker import BakeBudgets, IncrementalArchiveTickBaker
from babylon.projection.vault.materializer import VaultMaterializer
from babylon.projection.vault.tick_baker import ArchiveTickBaker
from babylon.topology import BabylonGraph

WAYNE = "26163"  # Michigan
OTHER_MI = "26099"  # Michigan
COOK = "17031"  # Illinois
ALL_COUNTIES = (WAYNE, OTHER_MI, COOK)


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


def _graph(world: WorldState) -> BabylonGraph:
    graph = world.to_graph()
    graph.add_node(
        "T_WAYNE",
        NodeType.TERRITORY,
        county_fips=WAYNE,
        tick_median_wage=19.85,
        legitimation_index=0.71,
    )
    graph.add_node(
        "T_OTHER_MI",
        NodeType.TERRITORY,
        county_fips=OTHER_MI,
        tick_median_wage=20.0,
        legitimation_index=0.60,
    )
    graph.add_node(
        "T_COOK",
        NodeType.TERRITORY,
        county_fips=COOK,
        tick_median_wage=22.0,
        legitimation_index=0.55,
    )
    graph.add_node("ORG1", NodeType.ORGANIZATION, name="Rev Workers Party")
    return graph


def _all_page_paths() -> tuple[str, ...]:
    return (
        f"county/{WAYNE}.md",
        f"county/{OTHER_MI}.md",
        f"county/{COOK}.md",
        "state/26.md",
        "state/17.md",
        "national/USA.md",
        "organization/ORG1.md",
        "social_class/C001.md",
    )


class TestFirstBakeMatchesFullBakeCoverage:
    def test_first_tick_bakes_every_proactively_tracked_kind(self, tmp_path: Path) -> None:
        world = _world()
        baker = IncrementalArchiveTickBaker(VaultMaterializer(tmp_path / "vault"), ALL_COUNTIES)

        baker.on_tick_committed(tick=1, world=world, graph=_graph(world))

        for page in _all_page_paths():
            assert (tmp_path / "vault" / page).is_file(), f"{page} not baked on first tick"

    def test_community_is_not_proactively_baked(self, tmp_path: Path) -> None:
        """community has no backing node — lazy bake-on-visit only, never proactive."""
        world = _world()
        baker = IncrementalArchiveTickBaker(VaultMaterializer(tmp_path / "vault"), ALL_COUNTIES)

        baker.on_tick_committed(tick=1, world=world, graph=_graph(world))

        assert not (tmp_path / "vault" / "community").exists()

    def test_a_quiet_second_tick_costs_no_commit(self, tmp_path: Path) -> None:
        from dulwich.repo import Repo

        world = _world()
        graph = _graph(world)
        baker = IncrementalArchiveTickBaker(VaultMaterializer(tmp_path / "vault"), ALL_COUNTIES)
        baker.on_tick_committed(tick=1, world=world, graph=graph)
        baker.on_tick_committed(tick=1, world=world, graph=graph)

        repo = Repo(str(tmp_path / "vault"))
        try:
            assert sum(1 for _ in repo.get_walker()) == 1
        finally:
            repo.close()


class TestDirtyTrackingCorrectness:
    """Mutating one node re-bakes exactly its own page (plus derived rollups)."""

    def test_mutating_one_county_reprojects_only_that_county(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        world = _world()
        graph = _graph(world)
        baker = IncrementalArchiveTickBaker(VaultMaterializer(tmp_path / "vault"), ALL_COUNTIES)
        baker.on_tick_committed(tick=1, world=world, graph=graph)

        calls: list[str] = []
        real_project_county = incremental_baker_module.project_county

        def _spy(county_fips: str, **kwargs: Any) -> Any:
            calls.append(county_fips)
            return real_project_county(county_fips, **kwargs)

        monkeypatch.setattr(incremental_baker_module, "project_county", _spy)
        graph.update_node("T_WAYNE", tick_median_wage=999.0)

        baker.on_tick_committed(tick=2, world=world, graph=graph)

        assert calls == [WAYNE]

    def test_unrelated_kinds_are_not_reprojected(self, tmp_path: Path, monkeypatch: Any) -> None:
        world = _world()
        graph = _graph(world)
        baker = IncrementalArchiveTickBaker(VaultMaterializer(tmp_path / "vault"), ALL_COUNTIES)
        baker.on_tick_committed(tick=1, world=world, graph=graph)

        org_calls: list[str] = []
        real_project_organization = incremental_baker_module.project_organization

        def _org_spy(org_id: str, **kwargs: Any) -> Any:
            org_calls.append(org_id)
            return real_project_organization(org_id, **kwargs)

        monkeypatch.setattr(incremental_baker_module, "project_organization", _org_spy)
        graph.update_node("T_WAYNE", tick_median_wage=999.0)

        baker.on_tick_committed(tick=2, world=world, graph=graph)

        assert org_calls == []

    def test_state_and_national_rebake_only_via_their_own_constituent_change(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        world = _world()
        graph = _graph(world)
        baker = IncrementalArchiveTickBaker(VaultMaterializer(tmp_path / "vault"), ALL_COUNTIES)
        baker.on_tick_committed(tick=1, world=world, graph=graph)

        state_calls: list[str] = []
        national_calls: list[str] = []
        real_project_state = incremental_baker_module.project_state
        real_project_national = incremental_baker_module.project_national

        def _state_spy(state_fips: str, **kwargs: Any) -> Any:
            state_calls.append(state_fips)
            return real_project_state(state_fips, **kwargs)

        def _national_spy(national_id: str, **kwargs: Any) -> Any:
            national_calls.append(national_id)
            return real_project_national(national_id, **kwargs)

        monkeypatch.setattr(incremental_baker_module, "project_state", _state_spy)
        monkeypatch.setattr(incremental_baker_module, "project_national", _national_spy)
        graph.update_node("T_WAYNE", tick_median_wage=999.0)  # Wayne is Michigan (26)

        baker.on_tick_committed(tick=2, world=world, graph=graph)

        assert state_calls == ["26"]  # NOT "17" (Cook/Illinois untouched)
        assert national_calls == ["USA"]

    def test_social_class_rebakes_when_its_county_changes(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """social_class's county_class_composition reads its containing territory."""
        world = _world()
        graph = _graph(world)
        baker = IncrementalArchiveTickBaker(VaultMaterializer(tmp_path / "vault"), ALL_COUNTIES)
        baker.on_tick_committed(tick=1, world=world, graph=graph)

        class_calls: list[str] = []
        real_project_social_class = incremental_baker_module.project_social_class

        def _spy(class_id: str, **kwargs: Any) -> Any:
            class_calls.append(class_id)
            return real_project_social_class(class_id, **kwargs)

        monkeypatch.setattr(incremental_baker_module, "project_social_class", _spy)
        graph.update_node("T_WAYNE", tick_median_wage=999.0)  # C001's own node is untouched

        baker.on_tick_committed(tick=2, world=world, graph=graph)

        assert class_calls == ["C001"]

    def test_second_quiet_tick_reprojects_nothing(self, tmp_path: Path, monkeypatch: Any) -> None:
        world = _world()
        graph = _graph(world)
        baker = IncrementalArchiveTickBaker(VaultMaterializer(tmp_path / "vault"), ALL_COUNTIES)
        baker.on_tick_committed(tick=1, world=world, graph=graph)

        calls: list[str] = []
        real_project_county = incremental_baker_module.project_county

        def _spy(county_fips: str, **kwargs: Any) -> Any:
            calls.append(county_fips)
            return real_project_county(county_fips, **kwargs)

        monkeypatch.setattr(incremental_baker_module, "project_county", _spy)

        baker.on_tick_committed(tick=2, world=world, graph=graph)

        assert calls == []


class TestBudgetEnforcement:
    def test_county_budget_clamps_to_sorted_first_n(self, tmp_path: Path) -> None:
        budgets = BakeBudgets(county=2)
        world = _world()
        graph = _graph(world)
        baker = IncrementalArchiveTickBaker(
            VaultMaterializer(tmp_path / "vault"), ALL_COUNTIES, budgets=budgets
        )

        baker.on_tick_committed(tick=1, world=world, graph=graph)

        baked = sorted(p.name for p in (tmp_path / "vault" / "county").glob("*.md"))
        assert baked == [f"{COOK}.md", f"{OTHER_MI}.md"]  # sorted(COOK, OTHER_MI, WAYNE)[:2]

    def test_overflowed_ids_are_caught_up_on_a_later_tick(self, tmp_path: Path) -> None:
        budgets = BakeBudgets(county=2)
        world = _world()
        graph = _graph(world)
        baker = IncrementalArchiveTickBaker(
            VaultMaterializer(tmp_path / "vault"), ALL_COUNTIES, budgets=budgets
        )

        baker.on_tick_committed(tick=1, world=world, graph=graph)  # bakes COOK, OTHER_MI
        baker.on_tick_committed(tick=2, world=world, graph=graph)  # nothing new dirty, but

        baked = sorted(p.name for p in (tmp_path / "vault" / "county").glob("*.md"))
        assert baked == [f"{COOK}.md", f"{OTHER_MI}.md", f"{WAYNE}.md"]

    def test_budget_enforcement_is_deterministic_across_independent_runs(
        self, tmp_path: Path
    ) -> None:
        budgets = BakeBudgets(county=2)
        baked_sets: list[list[str]] = []
        for name in ("a", "b"):
            world = _world()
            graph = _graph(world)
            baker = IncrementalArchiveTickBaker(
                VaultMaterializer(tmp_path / name), ALL_COUNTIES, budgets=budgets
            )
            baker.on_tick_committed(tick=1, world=world, graph=graph)
            baked_sets.append(sorted(p.name for p in (tmp_path / name / "county").glob("*.md")))

        assert baked_sets[0] == baked_sets[1]

    def test_zero_budget_defers_every_id_of_that_kind(self, tmp_path: Path) -> None:
        budgets = BakeBudgets(organization=0)
        world = _world()
        graph = _graph(world)
        baker = IncrementalArchiveTickBaker(
            VaultMaterializer(tmp_path / "vault"), ALL_COUNTIES, budgets=budgets
        )

        baker.on_tick_committed(tick=1, world=world, graph=graph)

        assert not (tmp_path / "vault" / "organization").exists()

    def test_a_negative_budget_is_rejected(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BakeBudgets(county=-1)


#: The one place the two bakers are EXPECTED to disagree, by design: the
#: template's own "staleness" stamp (``templates/*.md.j2``: "verified as of
#: tick N — always regenerable, never authoritative") records when a page
#: was last actually (re)computed, not a claim that nothing changed since.
#: The full baker recomputes — and re-stamps — every page every tick
#: unconditionally; the incremental baker's whole point is NOT to, so an
#: entity untouched since tick 1 legitimately still reads "verified_tick: 1"
#: at tick 3 there, honestly reporting "not recomputed since", while the
#: full bake reads "verified_tick: 3", just as honestly reporting "just
#: reconfirmed". Neither is wrong; they are different, intentional staleness
#: semantics for the same underlying (unchanged) data. Equivalence is
#: everything BUT this stamp.
_STALENESS_STAMP = re.compile(rb"verified_tick: \d+\nstaleness: verified as of tick \d+ [^\n]*\n")


def _normalize_staleness_stamp(content: bytes) -> bytes:
    return _STALENESS_STAMP.sub(b"verified_tick: <redacted>\n", content)


class TestFullVsIncrementalEquivalence:
    """The full-bake and incremental bakers converge to the same vault state."""

    def test_same_final_vault_state_over_several_ticks(self, tmp_path: Path) -> None:
        world = _world()
        graph = _graph(world)

        full_vault = tmp_path / "full"
        incr_vault = tmp_path / "incremental"
        full_baker = ArchiveTickBaker(VaultMaterializer(full_vault), ALL_COUNTIES)
        incr_baker = IncrementalArchiveTickBaker(VaultMaterializer(incr_vault), ALL_COUNTIES)

        # Tick 1: baseline.
        full_baker.on_tick_committed(tick=1, world=world, graph=graph)
        incr_baker.on_tick_committed(tick=1, world=world, graph=graph)

        # Tick 2: mutate one territory.
        graph.update_node("T_WAYNE", tick_median_wage=42.0)
        full_baker.on_tick_committed(tick=2, world=world, graph=graph)
        incr_baker.on_tick_committed(tick=2, world=world, graph=graph)

        # Tick 3: mutate a different territory + the organization.
        graph.update_node("T_COOK", legitimation_index=0.9)
        graph.update_node("ORG1", budget=500.0)
        full_baker.on_tick_committed(tick=3, world=world, graph=graph)
        incr_baker.on_tick_committed(tick=3, world=world, graph=graph)

        # community has no backing node — the incremental baker only ever
        # bakes it lazily on visit; simulate that visit to reach parity.
        incr_baker.bake_page_on_visit("community", "settler", world=world, graph=graph, tick=3)

        full_files = {
            p.relative_to(full_vault).as_posix(): p.read_bytes() for p in full_vault.rglob("*.md")
        }
        incr_files = {
            p.relative_to(incr_vault).as_posix(): p.read_bytes() for p in incr_vault.rglob("*.md")
        }
        assert full_files.keys() == incr_files.keys()
        normalized_full = {k: _normalize_staleness_stamp(v) for k, v in full_files.items()}
        normalized_incr = {k: _normalize_staleness_stamp(v) for k, v in incr_files.items()}
        assert normalized_full == normalized_incr

        # Confirm the staleness-stamp divergence is real (not a coincidence
        # of the fixture): OTHER_MI never changed after tick 1, so the full
        # bake re-stamps it "3" every tick while the incremental bake
        # honestly leaves it at "1" — proving the redaction above is doing
        # real work, not vacuously matching two already-identical strings.
        untouched_page = f"county/{OTHER_MI}.md"
        assert b"verified_tick: 3" in full_files[untouched_page]
        assert b"verified_tick: 1" in incr_files[untouched_page]


class TestLazyBakeOnVisit:
    def test_bakes_a_community_page_on_demand(self, tmp_path: Path) -> None:
        world = _world()
        graph = _graph(world)
        baker = IncrementalArchiveTickBaker(VaultMaterializer(tmp_path / "vault"), ALL_COUNTIES)

        baker.bake_page_on_visit("community", "settler", world=world, graph=graph, tick=1)

        page = tmp_path / "vault" / "community" / "settler.md"
        assert page.is_file()

    def test_rejects_a_kind_that_is_already_dirty_tracked(self, tmp_path: Path) -> None:
        import pytest

        world = _world()
        graph = _graph(world)
        baker = IncrementalArchiveTickBaker(VaultMaterializer(tmp_path / "vault"), ALL_COUNTIES)

        with pytest.raises(ValueError, match="community"):
            baker.bake_page_on_visit("organization", "ORG1", world=world, graph=graph, tick=1)
