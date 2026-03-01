"""Simulation database module (ephemeral per-run state).

The simulation database stores ephemeral state during simulation runs:
- Agent state snapshots per tick
- Production events (c/v/s tensor)
- Network graph edges
- Territorial control and heat dynamics
- Aggregate metrics per tick

This database is separate from the reference database (immutable federal
statistical data) and is created fresh for each simulation run.

Implements ADR030 (Unified SQLite Runtime Architecture) - uses SQLite
instead of the previous DuckDB implementation.

Usage:
    from babylon.engine.simdb import SimulationDB

    # In-memory for testing
    with SimulationDB(in_memory=True) as sim:
        sim.record_tick_summary(tick=0, total_c=100, total_v=50, ...)

    # File-based for production (persists to data/runs/)
    with SimulationDB(run_id="experiment_001") as sim:
        # Record simulation state
        sim.con.execute("INSERT INTO agent_state VALUES (...)")

Architecture:
    Reference DB (SQLite) ── Immutable federal data (3NF)
                            (census, QCEW, geography)

    Simulation DB (SQLite) ── Ephemeral per-run state
                             Created fresh, discarded after analysis
"""

from babylon.engine.simdb.database import SimulationDB

__all__ = ["SimulationDB"]
