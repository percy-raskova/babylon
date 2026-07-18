"""Unit tests for ``_seed_balkanization_layer`` CLAIMS-edge seeding.

Wave-1 item W1.5 (spine goal): the shipped ``seed_sovereigns.json``
initial_claims reference ExternalNode IDs ("canada" / "rest_of_usa"),
never real ``state.territories`` keys, so the literal ``territory_id in
state.territories`` join at ``_seed_balkanization_layer`` rejected every
claim in every scenario, unconditionally — CLAIMS edges never seeded and
``SOV_EXTERIOR_NULL`` (the documented FR-040b fallback sovereign, spec-070)
never claimed anything either.

These tests pin the FR-040b coverage invariant against production code
(the SC-017 integration test at
``tests/integration/balkanization/test_seed_coverage_invariant.py``
hand-fabricates the same shape but never exercises
``_seed_balkanization_layer`` itself).
"""

from __future__ import annotations

import pytest

from babylon.engine.scenarios._legacy_wayne import create_wayne_county_scenario
from babylon.models.enums import EdgeType
from game.engine_bridge import _seed_balkanization_layer

pytestmark = pytest.mark.unit


def _build_state():
    # wayne_county: a real, entirely domestic-interior H3 scenario (no
    # exterior nodes) — the shape the FR-040b domestic fallback assumes.
    state, _config, _defines = create_wayne_county_scenario()
    return state


@pytest.mark.unit
class TestSeedBalkanizationLayerClaims:
    """FR-040b: CLAIMS edges must actually seed."""

    def test_claims_edges_are_seeded(self) -> None:
        state = _build_state()

        seeded = _seed_balkanization_layer(state)

        claims = [r for r in seeded.relationships if r.edge_type == EdgeType.CLAIMS]
        assert len(claims) > 0

    def test_every_territory_is_claimed_by_exactly_one_sovereign(self) -> None:
        state = _build_state()

        seeded = _seed_balkanization_layer(state)

        claims = [r for r in seeded.relationships if r.edge_type == EdgeType.CLAIMS]
        claimants_by_territory: dict[str, list[str]] = {}
        for claim in claims:
            claimants_by_territory.setdefault(claim.target_id, []).append(claim.source_id)

        for territory_id in seeded.territories:
            claimants = claimants_by_territory.get(territory_id, [])
            assert len(claimants) == 1, (
                f"territory {territory_id!r} claimed by {len(claimants)} "
                f"sovereigns (expected exactly 1): {claimants}"
            )

    def test_otherwise_unclaimed_territories_go_to_sov_usa_fed(self) -> None:
        """Task R / ADR080: neither ``canada`` nor ``rest_of_usa`` (the seed
        file's literal initial_claims territory_ids) are real territory
        keys in this scenario, so every territory falls to the FR-040b
        fallback — which now routes to the domestic federal sovereign
        ``SOV_USA_FED`` (every Territory in ``state.territories`` is a
        domestic interior H3 cell), never the provisional exterior-null
        sovereign. Zero CLAIMS may source from SOV_EXTERIOR_NULL, and
        SOV_USA_FED must hold a CLAIMS majority (in this all-fallback
        scenario, all of it) of the interior Territories."""
        state = _build_state()

        seeded = _seed_balkanization_layer(state)

        claims = [r for r in seeded.relationships if r.edge_type == EdgeType.CLAIMS]
        null_claims = [r for r in claims if r.source_id == "SOV_EXTERIOR_NULL"]
        assert null_claims == [], (
            f"SOV_EXTERIOR_NULL must not claim domestic interior Territories: {null_claims}"
        )

        usa_fed_claims = [r for r in claims if r.source_id == "SOV_USA_FED"]
        assert len(usa_fed_claims) / len(seeded.territories) >= 0.5
