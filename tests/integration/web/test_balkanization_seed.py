"""Spec-109 A6: the balkanization layer seeds into web sessions (owner item 8).

Before this, no scenario seeded spec-070 data: web session graphs had zero
faction/sovereign nodes and zero INFLUENCES edges, so
``_build_balkanization_block`` returned empty arrays and every political map
lens rendered "no data". The seed artifacts existed all along
(``src/babylon/data/game/balkanization/``) — nothing loaded them at runtime.

The second test is the load-bearing one: the layer must survive a REAL
engine step (hydrate → ``WorldState.from_graph`` → systems → ``to_graph`` →
persist). Pre-A6 that round-trip crashed on faction nodes (owner item 12)
and dropped INFLUENCES payload attrs.

Requires a running PostgreSQL instance. Skip with:
``pytest -m "not requires_postgres"``.
"""

from __future__ import annotations

import os

import pytest

pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(
        not os.environ.get("POSTGRES_HOST"),
        reason="PostgreSQL not configured (set POSTGRES_HOST)",
    ),
]


def _balkanization(bridge: object, session_id: object) -> dict:
    """Build the balkanization block from the session's hydrated graph.

    Same code path ``get_map_snapshot`` uses for ``metadata.balkanization``
    (hydrate the raw graph → ``_build_balkanization_block``), minus the
    Django-ORM ``GameSession``/``HexState`` reads this psycopg-only harness
    cannot serve; the full endpoint is covered by the Playwright e2e leg.
    """
    from game.engine_bridge import _build_balkanization_block

    _state, graph = bridge.hydrate_state(session_id)
    return _build_balkanization_block(graph)


class TestBalkanizationSeed:
    """A6 gate: factions/sovereigns/influences present from tick 0 onward."""

    def test_new_session_seeds_the_political_layer(self, bridge: object) -> None:
        """A fresh wayne_county session carries the full spec-070 seed set."""
        session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)
        block = _balkanization(bridge, session_id)

        assert len(block["factions"]) == 4
        assert {f["id"] for f in block["factions"]} == {
            "FAC_RESTORATIONIST",
            "FAC_WORKERS_CONGRESS",
            "FAC_DECOLONIAL",
            "FAC_LIBERAL_IMPERIAL",
        }
        assert len(block["sovereigns"]) == 3

        influence = block["territory_influence"]
        assert len(influence) == 81, "every wayne cell gets aggregated influence"
        for row in influence:
            assert row["influences"], row
            assert row["influences"][0]["influence_level"] > 0.0
            assert row["dominant_faction_id"] in {f["id"] for f in block["factions"]}

    def test_political_layer_survives_a_real_engine_step(self, bridge: object) -> None:
        """Resolve one tick: faction nodes + INFLUENCES payloads round-trip.

        This is the item-12 regression gate — from_graph must reconstruct
        faction nodes (not crash as strict SocialClass) and the influence
        levels must not zero out through Relationship serialization.
        """
        session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)
        result = bridge.resolve_tick(session_id)
        assert result["tick"] == 1

        block = _balkanization(bridge, session_id)
        assert len(block["factions"]) == 4
        influence = block["territory_influence"]
        assert influence, "INFLUENCES edges vanished across the engine step"
        assert all(row["influences"][0]["influence_level"] > 0.0 for row in influence)
