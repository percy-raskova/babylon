"""Contract tests for :mod:`babylon.projection.topology.levi` (WO-31).

Fixture-fed, no engine tick, no database, no graph — mirrors
``tests/unit/projection/test_community.py``'s discipline exactly (community
membership is entity-level data, never a graph node, Constitution II.7), but
independently: this module does not import
``babylon.projection.community``'s private helpers (see ``levi.py``'s module
docstring), so these tests build their own ``WorldState`` fixtures rather
than sharing ``test_community.py``'s.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.entities.community import CommunityMembership
from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.enums import CommunityType, MembershipRole, SocialRole
from babylon.models.world_state import WorldState
from babylon.projection.topology.levi import LeviEgoTree, LeviNode, levi_ego_tree


def _entity(
    eid: str,
    *,
    memberships: list[CommunityMembership] | None = None,
    active: bool = True,
) -> SocialClass:
    return SocialClass(
        id=eid,
        name=f"Test {eid}",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=1.0,
        ideology=IdeologicalProfile(class_consciousness=0.5, national_identity=0.5),
        p_acquiescence=0.5,
        p_revolution=0.3,
        population=100,
        active=active,
        community_memberships=list(memberships) if memberships else [],
    )


def _membership(agent_id: str, community_type: CommunityType) -> CommunityMembership:
    return CommunityMembership(
        agent_id=agent_id,
        community_type=community_type,
        role=MembershipRole.CORE_ORGANIZER,
    )


def _world(*entities: SocialClass) -> WorldState:
    return WorldState(entities={entity.id: entity for entity in entities})


class TestRootedAtACommunity:
    """root_side="community": children are the roster, each grandchild-listing
    its OTHER communities (mirrors CommunityView.overlaps, generalized)."""

    def test_children_are_the_sorted_roster(self) -> None:
        world = _world(
            _entity("C002", memberships=[_membership("C002", CommunityType.SETTLER)]),
            _entity("C001", memberships=[_membership("C001", CommunityType.SETTLER)]),
            _entity("C003", memberships=[_membership("C003", CommunityType.WOMEN)]),
        )
        tree = levi_ego_tree(CommunityType.SETTLER.value, world=world)

        assert tree is not None
        assert tree.root_id == "settler"
        assert tree.root_side == "community"
        assert [child.node_id for child in tree.children] == ["C001", "C002"]

    def test_grandchildren_are_each_members_other_communities_excluding_root(self) -> None:
        world = _world(
            _entity(
                "C001",
                memberships=[
                    _membership("C001", CommunityType.SETTLER),
                    _membership("C001", CommunityType.PATRIARCHAL),
                ],
            ),
        )
        tree = levi_ego_tree(CommunityType.SETTLER.value, world=world)

        assert tree is not None
        assert tree.children == (LeviNode(node_id="C001", neighbors=("patriarchal",)),)

    def test_a_member_with_only_the_queried_community_has_empty_neighbors(self) -> None:
        """Computed-and-found-none is an empty tuple, never None (mirrors
        CommunityView.overlaps' empty-vs-None discipline)."""
        world = _world(
            _entity("C001", memberships=[_membership("C001", CommunityType.SETTLER)]),
        )
        tree = levi_ego_tree(CommunityType.SETTLER.value, world=world)

        assert tree is not None
        assert tree.children == (LeviNode(node_id="C001", neighbors=()),)

    def test_unattributed_community_is_honest_absence(self) -> None:
        world = _world(_entity("C001", memberships=[_membership("C001", CommunityType.WOMEN)]))
        assert levi_ego_tree(CommunityType.SETTLER.value, world=world) is None

    def test_empty_world_is_honest_absence(self) -> None:
        assert levi_ego_tree(CommunityType.SETTLER.value, world=_world()) is None

    def test_inactive_members_are_excluded_from_the_roster(self) -> None:
        world = _world(
            _entity(
                "C001",
                memberships=[_membership("C001", CommunityType.SETTLER)],
                active=False,
            ),
        )
        assert levi_ego_tree(CommunityType.SETTLER.value, world=world) is None


class TestRootedAtAMember:
    """root_side="member": children are the member's own communities, each
    grandchild-listing that community's OTHER members excluding the root."""

    def test_children_are_the_members_sorted_communities(self) -> None:
        world = _world(
            _entity(
                "C001",
                memberships=[
                    _membership("C001", CommunityType.WOMEN),
                    _membership("C001", CommunityType.SETTLER),
                ],
            ),
        )
        tree = levi_ego_tree("C001", world=world)

        assert tree is not None
        assert tree.root_id == "C001"
        assert tree.root_side == "member"
        assert [child.node_id for child in tree.children] == ["settler", "women"]

    def test_grandchildren_are_co_members_excluding_the_root(self) -> None:
        world = _world(
            _entity("C001", memberships=[_membership("C001", CommunityType.SETTLER)]),
            _entity("C002", memberships=[_membership("C002", CommunityType.SETTLER)]),
            _entity("C003", memberships=[_membership("C003", CommunityType.SETTLER)]),
        )
        tree = levi_ego_tree("C001", world=world)

        assert tree is not None
        assert tree.children == (LeviNode(node_id="settler", neighbors=("C002", "C003")),)

    def test_sole_member_of_a_community_has_empty_neighbors(self) -> None:
        world = _world(_entity("C001", memberships=[_membership("C001", CommunityType.SETTLER)]))
        tree = levi_ego_tree("C001", world=world)

        assert tree is not None
        assert tree.children == (LeviNode(node_id="settler", neighbors=()),)

    def test_a_known_entity_with_no_memberships_is_honest_absence(self) -> None:
        world = _world(_entity("C001"))
        assert levi_ego_tree("C001", world=world) is None

    def test_an_inactive_known_entity_is_honest_absence(self) -> None:
        world = _world(
            _entity(
                "C001",
                memberships=[_membership("C001", CommunityType.SETTLER)],
                active=False,
            ),
        )
        assert levi_ego_tree("C001", world=world) is None


class TestLoudFailure:
    """An id that is neither a real CommunityType nor a known entity is a
    caller error — never absence (mirrors project_community's discipline)."""

    def test_unknown_id_raises(self) -> None:
        with pytest.raises(ValueError, match="neither a CommunityType"):
            levi_ego_tree("not-a-real-anything", world=_world())

    def test_malformed_dict_membership_raises(self) -> None:
        entity = _entity("C001")
        object.__setattr__(
            entity,
            "community_memberships",
            [{"agent_id": "C001"}],  # missing required community_type
        )
        world = _world(entity)

        with pytest.raises(ValidationError):
            levi_ego_tree("C001", world=world)


class TestDeterminism:
    def test_double_projection_is_identical(self) -> None:
        world = _world(
            _entity("C001", memberships=[_membership("C001", CommunityType.SETTLER)]),
        )

        first = levi_ego_tree(CommunityType.SETTLER.value, world=world)
        second = levi_ego_tree(CommunityType.SETTLER.value, world=world)

        assert first == second
        assert first is not None
        assert first.model_dump() == second.model_dump()  # type: ignore[union-attr]


class TestLeviEgoTreeModel:
    def test_is_frozen(self) -> None:
        tree = LeviEgoTree(root_id="settler", root_side="community")
        with pytest.raises(ValidationError):
            tree.root_id = "women"  # type: ignore[misc]

    def test_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            LeviEgoTree(root_id="settler", root_side="community", bogus=1)  # type: ignore[call-arg]

    def test_levi_node_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            LeviNode(node_id="C001", bogus=1)  # type: ignore[call-arg]
