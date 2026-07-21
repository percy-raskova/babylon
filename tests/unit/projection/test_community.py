"""Contract tests for :func:`babylon.projection.community.project_community`.

The community read-model's behavioral contract: deterministic roster
ordering, honest ``None`` for an unattributed community (never a fabricated
empty-looking roster), a distinct empty-tuple for "attributed but zero
overlap," and a loud failure for an unrecognized ``community_id``.
Fixture-fed — no engine tick, no database, no graph at all (community is
never a graph node) — per the keel's fixture-first discipline.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.entities.community import CommunityMembership
from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.enums import CommunityType, MembershipRole, SocialRole
from babylon.models.world_state import WorldState
from babylon.projection.community import project_community
from babylon.projection.view_models import CommunityOverlap


def _entity(
    eid: str,
    *,
    memberships: list[CommunityMembership] | None = None,
    active: bool = True,
) -> SocialClass:
    """Build a SocialClass with community_memberships set (Feature 022 field)."""
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
    """Wrap entities in a minimal WorldState."""
    return WorldState(entities={entity.id: entity for entity in entities})


class TestFullDossier:
    """Every field populated when producers have attributed data."""

    def test_roster_is_the_sorted_member_id_tuple(self) -> None:
        """Membership in the queried community yields a sorted roster."""
        world = _world(
            _entity("C002", memberships=[_membership("C002", CommunityType.SETTLER)]),
            _entity("C001", memberships=[_membership("C001", CommunityType.SETTLER)]),
            _entity("C003", memberships=[_membership("C003", CommunityType.WOMEN)]),
        )
        view = project_community(CommunityType.SETTLER.value, world=world, tick=5)

        assert view.kind == "community"
        assert view.community_id == CommunityType.SETTLER
        assert view.verified_tick == 5
        assert view.roster == ("C001", "C002")

    def test_overlaps_count_shared_members_per_other_community_sorted(self) -> None:
        """Overlaps name every other community the roster also belongs to."""
        world = _world(
            _entity(
                "C001",
                memberships=[
                    _membership("C001", CommunityType.SETTLER),
                    _membership("C001", CommunityType.PATRIARCHAL),
                ],
            ),
            _entity(
                "C002",
                memberships=[
                    _membership("C002", CommunityType.SETTLER),
                    _membership("C002", CommunityType.PATRIARCHAL),
                ],
            ),
            _entity(
                "C003",
                memberships=[
                    _membership("C003", CommunityType.SETTLER),
                    _membership("C003", CommunityType.WOMEN),
                ],
            ),
        )
        view = project_community(CommunityType.SETTLER.value, world=world, tick=5)

        assert view.roster == ("C001", "C002", "C003")
        assert view.overlaps == (
            CommunityOverlap(community_id=CommunityType.PATRIARCHAL, shared_member_count=2),
            CommunityOverlap(community_id=CommunityType.WOMEN, shared_member_count=1),
        )

    def test_dict_shaped_membership_entries_are_accepted(self) -> None:
        """Graph-round-tripped (dict, not object) membership entries hydrate fine."""
        entity = _entity("C001")
        # Simulate the shape WorldState.from_graph() reconstructs after a
        # to_graph()/from_graph() round-trip: model_dump() flattens the
        # nested CommunityMembership to a plain dict.
        object.__setattr__(
            entity,
            "community_memberships",
            [{"agent_id": "C001", "community_type": "settler", "role": "active"}],
        )
        world = _world(entity)

        view = project_community("settler", world=world, tick=5)

        assert view.roster == ("C001",)

    def test_membership_in_other_communities_is_irrelevant_to_roster(self) -> None:
        """Only entities carrying the QUERIED community's membership are counted."""
        world = _world(
            _entity("C001", memberships=[_membership("C001", CommunityType.WOMEN)]),
        )
        view = project_community(CommunityType.SETTLER.value, world=world, tick=5)

        assert view.roster is None


class TestHonestAbsence:
    """Missing producers project as None — never a fabricated default (III.11)."""

    def test_no_memberships_anywhere_yields_all_none(self) -> None:
        """An entity with no community_memberships never appears in any roster."""
        world = _world(_entity("C001"))
        view = project_community(CommunityType.SETTLER.value, world=world, tick=5)

        assert view.roster is None
        assert view.formation_tick is None
        assert view.overlaps is None

    def test_empty_world_yields_all_none(self) -> None:
        """No entities at all is the same honest absence as no attribution."""
        view = project_community(CommunityType.SETTLER.value, world=_world(), tick=5)

        assert view.roster is None
        assert view.overlaps is None

    def test_inactive_entities_are_excluded_from_roster(self) -> None:
        """A deactivated (starved) entity's membership does not count.

        Mirrors ``CommunitySystem._collect_memberships``'s own
        ``if not node.attributes.get("active", True): continue`` filter.
        """
        world = _world(
            _entity(
                "C001",
                memberships=[_membership("C001", CommunityType.SETTLER)],
                active=False,
            ),
        )
        view = project_community(CommunityType.SETTLER.value, world=world, tick=5)

        assert view.roster is None

    def test_formation_tick_is_always_none_even_when_fully_attributed(self) -> None:
        """No producer exists anywhere — formation_tick is never populated."""
        world = _world(
            _entity("C001", memberships=[_membership("C001", CommunityType.SETTLER)]),
        )
        view = project_community(CommunityType.SETTLER.value, world=world, tick=5)

        assert view.formation_tick is None

    def test_attributed_roster_with_no_cross_membership_is_empty_not_none(self) -> None:
        """Zero overlap is a computed fact — distinct from an uncomputed one."""
        world = _world(
            _entity("C001", memberships=[_membership("C001", CommunityType.SETTLER)]),
        )
        view = project_community(CommunityType.SETTLER.value, world=world, tick=5)

        assert view.roster == ("C001",)
        assert view.overlaps == ()


class TestLoudFailure:
    """A present-but-wrong value raises; only a missing one is absence."""

    def test_unrecognized_community_id_raises(self) -> None:
        """An identifier outside the 14-member CommunityType taxonomy is a caller error."""
        with pytest.raises(ValueError):
            project_community("not-a-real-community", world=_world(), tick=1)

    def test_malformed_dict_membership_raises(self) -> None:
        """A dict-shaped membership missing required keys fails validation loudly."""
        entity = _entity("C001")
        object.__setattr__(
            entity,
            "community_memberships",
            [{"agent_id": "C001"}],  # missing required community_type
        )
        world = _world(entity)

        with pytest.raises(ValidationError):
            project_community(CommunityType.SETTLER.value, world=world, tick=1)


class TestDeterminism:
    """Identical inputs yield identical frozen dossiers."""

    def test_double_projection_is_identical(self) -> None:
        """Two projections of the same state compare equal."""
        world = _world(
            _entity("C001", memberships=[_membership("C001", CommunityType.SETTLER)]),
        )

        first = project_community(CommunityType.SETTLER.value, world=world, tick=5)
        second = project_community(CommunityType.SETTLER.value, world=world, tick=5)

        assert first == second
        assert first.model_dump() == second.model_dump()
