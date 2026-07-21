"""Contract tests for :class:`babylon.projection.vault.tick_baker.CountyTickBaker`."""

from __future__ import annotations

from pathlib import Path

from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.enums import SocialRole
from babylon.models.enums.topology import NodeType
from babylon.models.world_state import WorldState
from babylon.projection.vault.materializer import VaultMaterializer
from babylon.projection.vault.tick_baker import CountyTickBaker
from babylon.topology import BabylonGraph

WAYNE = "26163"


def _world() -> WorldState:
    """One Wayne-attributed entity — enough for a projectable dossier."""
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
    )
    return WorldState(entities={entity.id: entity})


def _graph() -> BabylonGraph:
    """A Wayne territory with a couple of tick attributes."""
    graph = BabylonGraph()
    graph.add_node(
        "T001",
        NodeType.TERRITORY,
        county_fips=WAYNE,
        tick_median_wage=19.85,
        legitimation_index=0.71,
    )
    return graph


class TestCountyTickBaker:
    """The observer-side composition: project then bake, per county, per tick."""

    def test_bakes_configured_county_on_commit(self, tmp_path: Path) -> None:
        """on_tick_committed writes the county's stable-slug page to the vault."""
        vault_root = tmp_path / "vault"
        baker = CountyTickBaker(VaultMaterializer(vault_root), (WAYNE,))

        baker.on_tick_committed(tick=847, world=_world(), graph=_graph())

        page = vault_root / "county" / f"{WAYNE}.md"
        assert page.exists()
        content = page.read_text(encoding="utf-8")
        assert WAYNE in content
        assert "847" in content

    def test_bakes_deterministically_across_fresh_vaults(self, tmp_path: Path) -> None:
        """Two independent bakes of the same committed state are byte-identical."""
        contents: list[bytes] = []
        for name in ("a", "b"):
            vault_root = tmp_path / name
            baker = CountyTickBaker(VaultMaterializer(vault_root), (WAYNE,))
            baker.on_tick_committed(tick=5, world=_world(), graph=_graph())
            contents.append((vault_root / "county" / f"{WAYNE}.md").read_bytes())

        assert contents[0] == contents[1]

    def test_counties_bake_in_sorted_order(self, tmp_path: Path) -> None:
        """Configuration order does not leak into vault history ordering."""
        baker = CountyTickBaker(VaultMaterializer(tmp_path / "vault"), ("26125", WAYNE, "26099"))

        assert baker._county_fips == ("26099", "26125", WAYNE)
