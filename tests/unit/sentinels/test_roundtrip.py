"""Round-Trip sentinel (#3) — core-field conservation across ``to_graph`` cycle.

Asserts that ``WorldState.from_graph(state.to_graph())`` conserves every field
declared in :data:`babylon.sentinels.roundtrip.registry.ROUNDTRIP_REGISTRY`
value-for-value, exercised over the shared tick artifact's live ``final_state``
(52 ticks of ``imperial_circuit``). This is the mechanical guard against the
tick-52 ``county_fips``-dropped crash class and any future core field that
silently stops surviving reconstruction.

The round-trip *logic* lives here (not in the layer-0.5 package) because it needs
a live ``WorldState`` and its ``to_graph`` bridge — above the sentinels' import
boundary. Only the declared registry is in the package.

Honesty (Amendment Q / III.12): the check is scoped to a curated CORE field set
because ``from_graph`` is intentionally lossy for transient / metadata fields;
scoping avoids false-alarming on that pre-existing, by-design loss. Empirically
(this scenario) ALL ``SocialClass`` and ``Territory`` *model* fields survive;
the registry names the material subset whose conservation is load-bearing.
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.models.world_state import WorldState
from babylon.sentinels.dynamic import DynamicArtifact
from babylon.sentinels.roundtrip.registry import (
    ROUNDTRIP_REGISTRY,
    RoundTripField,
    RoundTripNodeType,
)

pytestmark = pytest.mark.unit


def _nodes_for(state: WorldState, node_type: RoundTripNodeType) -> dict[str, Any]:
    """Return the ``WorldState`` node collection for a declared node type.

    :param state: The world state to read from.
    :param node_type: Which node collection the declared field lives on.
    :returns: The ``id -> node model`` mapping (``entities`` or ``territories``).
    """
    if node_type is RoundTripNodeType.SOCIAL_CLASS:
        return state.entities
    return state.territories


def _field_mismatches(
    before: WorldState,
    after: WorldState,
    registry: tuple[RoundTripField, ...],
) -> list[str]:
    """Collect every declared core field whose value changed across the round trip.

    The comparison helper the efficacy proof plants a mismatch into: for each
    declared row it reads the field off the matching node in ``before`` and
    ``after`` and records a loud, located message on any inequality (or a
    missing / added node).

    :param before: The pre-round-trip state (the live final state).
    :param after: The post-round-trip state (``from_graph(before.to_graph())``).
    :param registry: The declared core-field contract to enforce.
    :returns: One human-readable message per violation; empty when conserved.
    """
    violations: list[str] = []
    for row in registry:
        before_nodes = _nodes_for(before, row.node_type)
        after_nodes = _nodes_for(after, row.node_type)
        if before_nodes.keys() != after_nodes.keys():
            missing = before_nodes.keys() - after_nodes.keys()
            added = after_nodes.keys() - before_nodes.keys()
            violations.append(
                f"{row.node_type.value}: node set changed across round trip "
                f"(dropped={sorted(missing)}, added={sorted(added)})"
            )
            continue
        for node_id in before_nodes:
            v0 = getattr(before_nodes[node_id], row.field)
            v1 = getattr(after_nodes[node_id], row.field)
            if v0 != v1:
                violations.append(
                    f"{row.node_type.value}[{node_id}].{row.field}: "
                    f"{v0!r} -> {v1!r} (not conserved; {row.rationale})"
                )
    return violations


def test_registry_is_non_empty_and_well_formed() -> None:
    """The declared contract exists and every row names a field on a real model.

    Guards against a vacuously-green check: an empty or mistyped registry would
    let the round-trip assertion pass trivially (Amendment Q).
    """
    assert ROUNDTRIP_REGISTRY, "ROUNDTRIP_REGISTRY must declare at least one core field"
    sc_fields = set(SocialClassFields())
    terr_fields = set(TerritoryFields())
    for row in ROUNDTRIP_REGISTRY:
        if row.node_type is RoundTripNodeType.SOCIAL_CLASS:
            assert row.field in sc_fields, f"{row.field} is not a SocialClass model field"
        else:
            assert row.field in terr_fields, f"{row.field} is not a Territory model field"


def SocialClassFields() -> list[str]:
    """Return the ``SocialClass`` model field names (for the well-formedness check).

    :returns: The declared field names of the ``SocialClass`` node model.
    """
    from babylon.models.entities.social_class import SocialClass

    return list(SocialClass.model_fields.keys())


def TerritoryFields() -> list[str]:
    """Return the ``Territory`` model field names (for the well-formedness check).

    :returns: The declared field names of the ``Territory`` node model.
    """
    from babylon.models.entities.territory import Territory

    return list(Territory.model_fields.keys())


def test_core_fields_survive_round_trip(shared_tick: DynamicArtifact) -> None:
    """Every declared core field is conserved across ``to_graph`` → ``from_graph``.

    The invariant proper: round-trips the live final ``WorldState`` and asserts
    the declared core-field contract holds value-for-value. A red here is a real
    conservation bug (the tick-52 crash class), not a false alarm on the known,
    by-design loss of transient/metadata fields (which the registry excludes).
    """
    before: WorldState = shared_tick.final_state
    after = WorldState.from_graph(before.to_graph(), tick=before.tick)

    violations = _field_mismatches(before, after, ROUNDTRIP_REGISTRY)

    assert not violations, "Round-trip dropped/altered declared core fields:\n" + "\n".join(
        violations
    )


def test_sentinel_reds_on_a_dropped_core_field(shared_tick: DynamicArtifact) -> None:
    """EFFICACY: the check REDS when a declared core field fails to round-trip.

    A green invariant that cannot fail is worthless (Amendment Q). This plants a
    real defect — a ``from_graph`` output with one declared field mutated on a
    single node — and proves the comparison helper flags exactly that field.
    Without this, the sentinel could silently rot into a vacuous pass.
    """
    before: WorldState = shared_tick.final_state
    after = WorldState.from_graph(before.to_graph(), tick=before.tick)

    # Sanity: the honest round trip is clean, so any violation below is planted.
    assert not _field_mismatches(before, after, ROUNDTRIP_REGISTRY)

    # Plant a defect: drop/alter ``county_fips`` on one territory of the
    # reconstructed state — the exact tick-52 crash-class regression.
    victim_id = next(iter(after.territories))
    row = next(
        r
        for r in ROUNDTRIP_REGISTRY
        if r.node_type is RoundTripNodeType.TERRITORY and r.field == "county_fips"
    )
    original = after.territories[victim_id].county_fips
    broken_territory = after.territories[victim_id].model_copy(
        update={"county_fips": (original or "") + "_TAMPERED"}
    )
    broken_after = after.model_copy(
        update={"territories": {**after.territories, victim_id: broken_territory}}
    )

    violations = _field_mismatches(before, broken_after, ROUNDTRIP_REGISTRY)

    assert violations, "sentinel FAILED to detect a dropped/altered core field"
    assert any(f"territory[{victim_id}].county_fips" in v for v in violations), (
        f"sentinel flagged the wrong field(s): {violations}"
    )
    # And it names the material relation it protects, per the declared row.
    assert any(row.rationale in v for v in violations)


def test_sentinel_reds_when_a_node_is_dropped(shared_tick: DynamicArtifact) -> None:
    """EFFICACY: the check REDS when a whole node vanishes across the round trip.

    Complements the value-mismatch proof: a reconstruction that loses an entity
    entirely (not just a field) must also be caught loudly, not silently ignored.
    """
    before: WorldState = shared_tick.final_state
    after = WorldState.from_graph(before.to_graph(), tick=before.tick)

    victim_id = next(iter(after.entities))
    dropped = {k: v for k, v in after.entities.items() if k != victim_id}
    broken_after = after.model_copy(update={"entities": dropped})

    violations = _field_mismatches(before, broken_after, ROUNDTRIP_REGISTRY)

    assert violations, "sentinel FAILED to detect a dropped node"
    assert any("node set changed" in v for v in violations)
