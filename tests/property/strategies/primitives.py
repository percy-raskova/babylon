"""Hypothesis strategies for generating valid simulation primitives.

Spec 040 Layer 2: Generates SocialClass, Territory, and Relationship
instances constrained to their Pydantic domain types.
"""

from __future__ import annotations

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.entities.territory import Territory
from babylon.models.enums import (
    EdgeType,
    OperationalProfile,
    SectorType,
    SocialRole,
    TerritoryType,
)


def _entity_id_strategy() -> SearchStrategy[str]:
    """Generate valid entity IDs matching ^C[0-9]{3}$."""
    return st.from_regex(r"^C[0-9]{3}$", fullmatch=True)


def _territory_id_strategy() -> SearchStrategy[str]:
    """Generate valid territory IDs matching ^T[0-9]{3}$."""
    return st.from_regex(r"^T[0-9]{3}$", fullmatch=True)


def _probability() -> SearchStrategy[float]:
    """Float in [0.0, 1.0]."""
    return st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


def _currency() -> SearchStrategy[float]:
    """Float in [0.0, 10000.0] (non-negative, bounded for sanity)."""
    return st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False)


def _ideology_profile_strategy() -> SearchStrategy[IdeologicalProfile]:
    """Generate valid IdeologicalProfile instances."""
    return st.builds(
        IdeologicalProfile,
        class_consciousness=_probability(),
        national_identity=_probability(),
        agitation=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    )


def social_class_strategy() -> SearchStrategy[SocialClass]:
    """Generate valid SocialClass instances with constrained domain types.

    Returns:
        Hypothesis strategy producing SocialClass instances.
    """
    return st.builds(
        SocialClass,
        id=_entity_id_strategy(),
        name=st.text(min_size=1, max_size=30, alphabet=st.characters(categories=("L", "N", "Zs"))),
        role=st.sampled_from(list(SocialRole)),
        wealth=_currency(),
        ideology=_ideology_profile_strategy(),
        p_acquiescence=_probability(),
        p_revolution=_probability(),
        subsistence_threshold=_currency(),
        organization=_probability(),
        repression_faced=_probability(),
        population=st.integers(min_value=1, max_value=100_000),
        s_bio=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        s_class=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        active=st.booleans(),
    )


def territory_strategy() -> SearchStrategy[Territory]:
    """Generate valid Territory instances with constrained domain types.

    Returns:
        Hypothesis strategy producing Territory instances.
    """
    return st.builds(
        Territory,
        id=_territory_id_strategy(),
        name=st.text(min_size=1, max_size=30, alphabet=st.characters(categories=("L", "N", "Zs"))),
        sector_type=st.sampled_from(list(SectorType)),
        territory_type=st.sampled_from(list(TerritoryType)),
        profile=st.sampled_from(list(OperationalProfile)),
        heat=_probability(),
        rent_level=_currency(),
        population=st.integers(min_value=0, max_value=100_000),
        biocapacity=_currency(),
        max_biocapacity=_currency(),
        regeneration_rate=st.floats(
            min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
        extraction_intensity=st.floats(
            min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
    )


def relationship_strategy(
    source_ids: SearchStrategy[str] | None = None,
    target_ids: SearchStrategy[str] | None = None,
) -> SearchStrategy[Relationship]:
    """Generate valid Relationship instances.

    Args:
        source_ids: Strategy for source IDs (default: entity IDs).
        target_ids: Strategy for target IDs (default: entity IDs).

    Returns:
        Hypothesis strategy producing Relationship instances.
    """
    if source_ids is None:
        source_ids = _entity_id_strategy()
    if target_ids is None:
        target_ids = _entity_id_strategy()

    # Ensure no self-loops by drawing two distinct IDs
    return (
        st.tuples(source_ids, target_ids)
        .filter(lambda pair: pair[0] != pair[1])
        .flatmap(
            lambda pair: st.builds(
                Relationship,
                source_id=st.just(pair[0]),
                target_id=st.just(pair[1]),
                edge_type=st.sampled_from(list(EdgeType)),
                value_flow=_currency(),
                tension=_probability(),
            )
        )
    )
