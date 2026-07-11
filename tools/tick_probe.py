"""Single-county Postgres tick probe (diagnostic).

Seeds a fresh session for one county into the isolated test Postgres,
hydrates the WorldStateBridge, runs N engine ticks in-graph, and prints
the per-tick survival aggregates plus per-node deltas for the county's
social classes. Canonicalized from the inline heredoc rebuilt ~12 times
during the spec-066/dialectics sessions (see .mise.toml `sim:probe`).

Usage::

    poetry run python tools/tick_probe.py --county 26163 --ticks 3
"""

from __future__ import annotations

import argparse
import logging
import uuid
from pathlib import Path

logging.disable(logging.WARNING)


def main() -> None:
    """Run the probe: seed session, hydrate, tick N times, print deltas."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--county", default="26163", help="County FIPS (default: Wayne, MI)")
    parser.add_argument("--ticks", type=int, default=2, help="Engine ticks to run")
    parser.add_argument("--start-year", type=int, default=2010)
    parser.add_argument(
        "--dsn",
        default="host=localhost port=5433 dbname=babylon_test user=test password=test",
    )
    parser.add_argument("--sqlite", type=Path, default=Path("data/sqlite/marxist-data-3NF.sqlite"))
    args = parser.parse_args()

    from psycopg_pool import ConnectionPool

    from babylon.config.defines import GameDefines
    from babylon.domain.economics.boundary_flow_register import BoundaryFlowRegister
    from babylon.engine.context import TickContext
    from babylon.engine.headless_runner.bridge import WorldStateBridge
    from babylon.engine.headless_runner.runner import EventCapture
    from babylon.engine.services import ServiceContainer
    from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS, SimulationEngine
    from babylon.kernel.event_bus import EventBus
    from babylon.models.world_state import WorldState
    from babylon.persistence import PostgresRuntime
    from babylon.persistence.conservation_audit import ConservationAuditor
    from babylon.persistence.county_aggregation import aggregate_survival_for_county
    from babylon.persistence.postgres_initialization import initialize_session

    pool = ConnectionPool(args.dsn, min_size=1, max_size=2, open=True)
    try:
        runtime = PostgresRuntime(pool=pool)
        defines = GameDefines.load_default()
        session_id = uuid.uuid4()
        scope = {args.county}

        initialize_session(
            session_id=session_id,
            sqlite_path=args.sqlite,
            runtime=runtime,
            defines=defines,
            start_year=args.start_year,
            scenario_length_years=1,
            counties=sorted(scope),
            hex_hydration_counties=scope,
        )
        bridge = WorldStateBridge(
            runtime=runtime,
            defines=defines,
            boundary_register=BoundaryFlowRegister(),
            event_bus=EventBus(),
            auditor=ConservationAuditor(
                epsilon=defines.economy.epsilon_conservation, rng_seed=args.start_year
            ),
        )
        world = bridge.hydrate_initial(
            session_id=session_id,
            scope_fips=scope,
            event_capture=EventCapture(),
            total_ticks=args.ticks,
            start_year=args.start_year,
            sqlite_path=args.sqlite,
        )
        print(
            f"t0 survival (p_acq, p_rev, pop): {aggregate_survival_for_county(world, args.county)}"
        )

        graph = world.to_graph()
        county_nodes = [
            node_id
            for node_id, data in graph.nodes(data=True)
            if data.get("county_fips") == args.county and data.get("_node_type") == "social_class"
        ]
        print(f"county social_class nodes: {county_nodes}")
        pre = {node_id: dict(graph.nodes[node_id]) for node_id in county_nodes}

        services = ServiceContainer.create(defines=defines)
        engine = SimulationEngine(list(_DEFAULT_SYSTEMS))
        tracked = ("county_fips", "population", "wealth", "_node_type", "active")

        for tick in range(1, args.ticks + 1):
            engine.run_tick(graph, services, TickContext(tick=tick))
            world_t = WorldState.from_graph(graph, tick=tick)
            print(f"t{tick} survival: {aggregate_survival_for_county(world_t, args.county)}")
            for node_id in county_nodes:
                if node_id not in graph.nodes:
                    print(f"  {node_id} DELETED")
                    continue
                post = dict(graph.nodes[node_id])
                changed = {
                    key: (pre[node_id].get(key), post.get(key))
                    for key in tracked
                    if pre[node_id].get(key) != post.get(key)
                }
                print(f"  {node_id} changed: {changed or 'none-of-tracked'}")
                pre[node_id] = post
    finally:
        pool.close()


if __name__ == "__main__":
    main()
