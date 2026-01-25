"""Simulation database module (ephemeral per-run state).

The simulation database stores ephemeral state during simulation runs:
- Agent state snapshots per tick
- Production events (c/v/s tensor)
- Network graph edges
- Territorial control and heat dynamics
- Aggregate metrics per tick

This database is separate from the reference database (immutable federal
statistical data) and is created fresh for each simulation run.

Usage:
    from babylon.data.simulation import SimulationDB

    # In-memory for testing
    with SimulationDB(in_memory=True) as sim:
        sim.record_tick_summary(tick=0, total_c=100, total_v=50, ...)

    # File-based for production (persists to data/runs/)
    with SimulationDB(run_id="experiment_001") as sim:
        # Query reference data via ATTACH
        counties = sim.con.execute("SELECT * FROM ref.dim_county").fetchdf()

        # Record simulation state
        sim.con.execute("INSERT INTO agent_state VALUES (...)")

Architecture:
    Reference DB (DuckDB) ──┬── Immutable federal data
                           │   ATTACHed as 'ref' (read-only)
                           │
    Simulation DB (DuckDB) ─┴── Ephemeral per-run state
                               Created fresh, discarded after analysis
"""

from babylon.data.simulation.database import SimulationDB

__all__ = ["SimulationDB"]
