#!/usr/bin/env python3
"""Initialize the Epoch 2 KuzuDB Strategic Map.

This script creates the graph schema for continental-scale simulation:
- Territory nodes (OGV/OPC)
- ADMINISTERS edges (administrative hierarchy DAG)
- ADJACENT_TO edges (physical adjacency mesh)

Related: ADR029_hybrid_graph_architecture, ai-docs/epoch2-persistence.yaml

Usage:
    poetry run python tools/init_epoch2_db.py [--db-path PATH]

Example:
    poetry run python tools/init_epoch2_db.py --db-path data/epoch2_world.kuzu
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Defer kuzu import to allow script to show help even if kuzu not installed
try:
    import kuzu
except ImportError:
    kuzu = None  # type: ignore[assignment]


# =============================================================================
# SCHEMA DEFINITIONS
# =============================================================================

TERRITORY_NODE_SCHEMA = """
CREATE NODE TABLE IF NOT EXISTS Territory (
    id STRING PRIMARY KEY,
    name STRING,
    type STRING DEFAULT 'OPC',
    area_sq_km DOUBLE DEFAULT 0.0,
    bioregion STRING DEFAULT '',
    habitability DOUBLE DEFAULT 0.5,
    controller STRING DEFAULT 'STATE',
    heat DOUBLE DEFAULT 0.0,
    population INT64 DEFAULT 0,
    created_tick INT32 DEFAULT 0,
    last_modified_tick INT32 DEFAULT 0
)
"""

ADMINISTERS_EDGE_SCHEMA = """
CREATE REL TABLE IF NOT EXISTS ADMINISTERS (
    FROM Territory TO Territory,
    control_level DOUBLE DEFAULT 1.0,
    legal_status STRING DEFAULT 'DE_JURE'
)
"""

ADJACENT_TO_EDGE_SCHEMA = """
CREATE REL TABLE IF NOT EXISTS ADJACENT_TO (
    FROM Territory TO Territory,
    barrier_type STRING DEFAULT 'NONE',
    permeability DOUBLE DEFAULT 1.0,
    border_length_km DOUBLE DEFAULT 0.0
)
"""

# Chronicle tables for historical tracking
TERRITORY_SNAPSHOT_SCHEMA = """
CREATE NODE TABLE IF NOT EXISTS TerritorySnapshot (
    snapshot_id INT64 PRIMARY KEY,
    territory_id STRING,
    tick INT32,
    controller STRING,
    heat DOUBLE,
    population INT64
)
"""

SIMULATION_EVENT_SCHEMA = """
CREATE NODE TABLE IF NOT EXISTS SimulationEvent (
    event_id INT64 PRIMARY KEY,
    tick INT32,
    event_type STRING,
    territory_id STRING,
    payload STRING
)
"""


# =============================================================================
# INITIALIZATION FUNCTIONS
# =============================================================================


def init_schema(conn: kuzu.Connection) -> None:
    """Create all node and edge tables for Epoch 2.

    Args:
        conn: KuzuDB connection object.

    Raises:
        RuntimeError: If schema creation fails.
    """
    schemas = [
        ("Territory node", TERRITORY_NODE_SCHEMA),
        ("ADMINISTERS edge", ADMINISTERS_EDGE_SCHEMA),
        ("ADJACENT_TO edge", ADJACENT_TO_EDGE_SCHEMA),
        ("TerritorySnapshot node", TERRITORY_SNAPSHOT_SCHEMA),
        ("SimulationEvent node", SIMULATION_EVENT_SCHEMA),
    ]

    for name, schema in schemas:
        try:
            conn.execute(schema)
            print(f"  [OK] Created {name} table")
        except Exception as e:
            raise RuntimeError(f"Failed to create {name}: {e}") from e


def init_db(db_path: str | Path) -> kuzu.Connection:
    """Initialize KuzuDB database with Epoch 2 schema.

    Args:
        db_path: Path to the database directory.

    Returns:
        KuzuDB connection object.

    Raises:
        ImportError: If kuzu package is not installed.
        RuntimeError: If database initialization fails.
    """
    if kuzu is None:
        raise ImportError("kuzu package not installed. Run: poetry add kuzu")

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Initializing Epoch 2 database at: {db_path}")

    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)

    init_schema(conn)

    print("Schema creation complete.")
    return conn


def insert_test_data(conn: kuzu.Connection) -> None:
    """Insert minimal test data: 1 State, 1 City, connected by ADMINISTERS.

    This validates that the schema works correctly.

    Args:
        conn: KuzuDB connection object.
    """
    print("\nInserting test data...")

    # Create California state node
    conn.execute("""
        CREATE (t:Territory {
            id: 'US-CA',
            name: 'California',
            type: 'OPC',
            area_sq_km: 423970.0,
            bioregion: 'Pacific Coast',
            habitability: 0.8,
            controller: 'STATE',
            heat: 0.0,
            population: 39538223
        })
    """)
    print("  [OK] Created Territory: US-CA (California)")

    # Create Los Angeles city node
    conn.execute("""
        CREATE (t:Territory {
            id: 'US-CA-037-LA',
            name: 'Los Angeles',
            type: 'OPC',
            area_sq_km: 1302.0,
            bioregion: 'Pacific Coast',
            habitability: 0.7,
            controller: 'STATE',
            heat: 0.1,
            population: 3979576
        })
    """)
    print("  [OK] Created Territory: US-CA-037-LA (Los Angeles)")

    # Create ADMINISTERS edge: California administers Los Angeles
    conn.execute("""
        MATCH (parent:Territory {id: 'US-CA'})
        MATCH (child:Territory {id: 'US-CA-037-LA'})
        CREATE (parent)-[:ADMINISTERS {
            control_level: 0.9,
            legal_status: 'DE_JURE'
        }]->(child)
    """)
    print("  [OK] Created ADMINISTERS edge: US-CA -> US-CA-037-LA")

    print("\nTest data insertion complete.")


def verify_test_data(conn: kuzu.Connection) -> bool:
    """Verify test data was inserted correctly.

    Args:
        conn: KuzuDB connection object.

    Returns:
        True if verification passed, False otherwise.
    """
    print("\nVerifying test data...")

    # Count territories
    result = conn.execute("MATCH (t:Territory) RETURN COUNT(t) AS count")
    count = result.get_next()[0]
    if count != 2:
        print(f"  [FAIL] Expected 2 territories, found {count}")
        return False
    print(f"  [OK] Territory count: {count}")

    # Verify ADMINISTERS edge
    result = conn.execute("""
        MATCH (parent:Territory)-[a:ADMINISTERS]->(child:Territory)
        RETURN parent.name, child.name, a.control_level
    """)
    row = result.get_next()
    if row is None:
        print("  [FAIL] No ADMINISTERS edge found")
        return False

    parent_name, child_name, control_level = row
    print(f"  [OK] ADMINISTERS: {parent_name} -> {child_name} (control: {control_level})")

    # Verify query capability
    result = conn.execute("""
        MATCH (t:Territory)
        WHERE t.controller = 'STATE'
        RETURN t.name
        ORDER BY t.population DESC
    """)
    territories = [row[0] for row in result.get_all()]
    print(f"  [OK] STATE-controlled territories: {territories}")

    print("\nAll verifications passed!")
    return True


# =============================================================================
# CLI ENTRY POINT
# =============================================================================


def main() -> int:
    """Main entry point for the script.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    parser = argparse.ArgumentParser(
        description="Initialize Epoch 2 KuzuDB Strategic Map",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("data/epoch2_world.kuzu"),
        help="Path to KuzuDB database directory (default: data/epoch2_world.kuzu)",
    )
    parser.add_argument(
        "--skip-test-data",
        action="store_true",
        help="Skip inserting test data",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing database",
    )

    args = parser.parse_args()

    # Check if kuzu is installed
    if kuzu is None:
        print("ERROR: kuzu package not installed.", file=sys.stderr)
        print("Install with: poetry add kuzu", file=sys.stderr)
        return 1

    # Check for existing database
    if args.db_path.exists() and not args.force:
        print(f"ERROR: Database already exists at {args.db_path}", file=sys.stderr)
        print("Use --force to overwrite", file=sys.stderr)
        return 1

    try:
        # Initialize database and schema
        conn = init_db(args.db_path)

        # Insert and verify test data
        if not args.skip_test_data:
            insert_test_data(conn)
            if not verify_test_data(conn):
                return 1

        print(f"\nEpoch 2 database initialized successfully at: {args.db_path}")
        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
