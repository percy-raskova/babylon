#!/usr/bin/env python3
"""Initialize the Epoch 2 KuzuDB Strategic Map.

This script creates the graph schema for continental-scale simulation:
- Sovereign nodes (Dynamic Sovereignty - v1.1.0)
- Territory nodes (OGV/OPC)
- CLAIMS edges (Sovereign -> Territory sovereignty claims)
- ADMINISTERS edges (Territory -> Territory administrative hierarchy)
- ADJACENT_TO edges (Territory -> Territory physical adjacency mesh)

Key Design (Dynamic Sovereignty):
    Sovereignty is expressed as CLAIMS edges from Sovereign nodes to Territory nodes,
    NOT as a property on Territory. This enables O(1) border changes for:
    - Civil war (multiple competing claims)
    - Secession (edge rewiring)
    - Conquest (claim transfer)

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

# -----------------------------------------------------------------------------
# NODE TABLES
# -----------------------------------------------------------------------------

# Sovereign: Political entities that claim sovereignty over territories (v1.1.0)
SOVEREIGN_NODE_SCHEMA = """
CREATE NODE TABLE IF NOT EXISTS Sovereign (
    id STRING PRIMARY KEY,
    name STRING,
    sovereignty_type STRING DEFAULT 'RECOGNIZED_STATE',
    legitimacy DOUBLE DEFAULT 1.0,
    color_hex STRING DEFAULT '#808080',
    capital_territory_id STRING,
    founded_tick INT32 DEFAULT 0,
    dissolved_tick INT32
)
"""

# Territory: Physical/political spatial units
# NOTE: 'controller' property REMOVED in v1.1.0 - use CLAIMS edges instead
TERRITORY_NODE_SCHEMA = """
CREATE NODE TABLE IF NOT EXISTS Territory (
    id STRING PRIMARY KEY,
    name STRING,
    type STRING DEFAULT 'OPC',
    area_sq_km DOUBLE DEFAULT 0.0,
    bioregion STRING DEFAULT '',
    habitability DOUBLE DEFAULT 0.5,
    heat DOUBLE DEFAULT 0.0,
    population INT64 DEFAULT 0,
    created_tick INT32 DEFAULT 0,
    last_modified_tick INT32 DEFAULT 0
)
"""

# -----------------------------------------------------------------------------
# EDGE TABLES
# -----------------------------------------------------------------------------

# CLAIMS: Sovereignty claims from Sovereign to Territory (v1.1.0)
# This is the core of Dynamic Sovereignty - enables O(1) border changes
CLAIMS_EDGE_SCHEMA = """
CREATE REL TABLE IF NOT EXISTS CLAIMS (
    FROM Sovereign TO Territory,
    control_level DOUBLE DEFAULT 1.0,
    fiscal_status STRING DEFAULT 'TAXED',
    legal_status STRING DEFAULT 'DE_JURE',
    claimed_since_tick INT32 DEFAULT 0,
    recognition_level DOUBLE DEFAULT 1.0
)
"""

# ADMINISTERS: Administrative hierarchy (Territory -> Territory)
ADMINISTERS_EDGE_SCHEMA = """
CREATE REL TABLE IF NOT EXISTS ADMINISTERS (
    FROM Territory TO Territory,
    control_level DOUBLE DEFAULT 1.0,
    legal_status STRING DEFAULT 'DE_JURE'
)
"""

# ADJACENT_TO: Physical adjacency mesh (Territory <-> Territory)
ADJACENT_TO_EDGE_SCHEMA = """
CREATE REL TABLE IF NOT EXISTS ADJACENT_TO (
    FROM Territory TO Territory,
    barrier_type STRING DEFAULT 'NONE',
    permeability DOUBLE DEFAULT 1.0,
    border_length_km DOUBLE DEFAULT 0.0
)
"""

# -----------------------------------------------------------------------------
# CHRONICLE TABLES (Historical Tracking)
# -----------------------------------------------------------------------------

TERRITORY_SNAPSHOT_SCHEMA = """
CREATE NODE TABLE IF NOT EXISTS TerritorySnapshot (
    snapshot_id INT64 PRIMARY KEY,
    territory_id STRING,
    tick INT32,
    heat DOUBLE,
    population INT64
)
"""

# Sovereignty snapshots for historical claim tracking (v1.1.0)
CLAIMS_SNAPSHOT_SCHEMA = """
CREATE NODE TABLE IF NOT EXISTS ClaimsSnapshot (
    snapshot_id INT64 PRIMARY KEY,
    sovereign_id STRING,
    territory_id STRING,
    tick INT32,
    control_level DOUBLE,
    legal_status STRING
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

    Schema order matters: Node tables must be created before Edge tables
    that reference them.

    Args:
        conn: KuzuDB connection object.

    Raises:
        RuntimeError: If schema creation fails.
    """
    schemas = [
        # Node tables first
        ("Sovereign node", SOVEREIGN_NODE_SCHEMA),
        ("Territory node", TERRITORY_NODE_SCHEMA),
        # Edge tables (depend on node tables)
        ("CLAIMS edge", CLAIMS_EDGE_SCHEMA),
        ("ADMINISTERS edge", ADMINISTERS_EDGE_SCHEMA),
        ("ADJACENT_TO edge", ADJACENT_TO_EDGE_SCHEMA),
        # Chronicle tables
        ("TerritorySnapshot node", TERRITORY_SNAPSHOT_SCHEMA),
        ("ClaimsSnapshot node", CLAIMS_SNAPSHOT_SCHEMA),
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
    """Insert test data demonstrating Dynamic Sovereignty.

    Creates:
    - 2 Sovereigns: USA Federal Government and Provisional Revolutionary Command
    - 2 Territories: California and Los Angeles
    - CLAIMS edges showing sovereignty relationships
    - ADMINISTERS edge showing administrative hierarchy

    Args:
        conn: KuzuDB connection object.
    """
    print("\nInserting test data...")

    # =========================================================================
    # SOVEREIGN NODES
    # =========================================================================

    # Create United States Federal Government sovereign
    conn.execute("""
        CREATE (s:Sovereign {
            id: 'SOV_USA_FED',
            name: 'United States Federal Government',
            sovereignty_type: 'RECOGNIZED_STATE',
            legitimacy: 1.0,
            color_hex: '#3C3B6E',
            founded_tick: 0
        })
    """)
    print("  [OK] Created Sovereign: SOV_USA_FED (United States Federal Government)")

    # Create Provisional Revolutionary Command sovereign (player faction)
    conn.execute("""
        CREATE (s:Sovereign {
            id: 'SOV_PRC',
            name: 'Provisional Revolutionary Command',
            sovereignty_type: 'INSURGENT',
            legitimacy: 0.2,
            color_hex: '#B22234',
            founded_tick: 0
        })
    """)
    print("  [OK] Created Sovereign: SOV_PRC (Provisional Revolutionary Command)")

    # =========================================================================
    # TERRITORY NODES
    # =========================================================================

    # Create California state node
    # NOTE: No 'controller' property - sovereignty via CLAIMS edge
    conn.execute("""
        CREATE (t:Territory {
            id: 'US-CA',
            name: 'California',
            type: 'OPC',
            area_sq_km: 423970.0,
            bioregion: 'Pacific Coast',
            habitability: 0.8,
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
            heat: 0.3,
            population: 3979576
        })
    """)
    print("  [OK] Created Territory: US-CA-037-LA (Los Angeles)")

    # =========================================================================
    # CLAIMS EDGES (Dynamic Sovereignty)
    # =========================================================================

    # USA Federal Government claims California (full control)
    conn.execute("""
        MATCH (sov:Sovereign {id: 'SOV_USA_FED'})
        MATCH (terr:Territory {id: 'US-CA'})
        CREATE (sov)-[:CLAIMS {
            control_level: 1.0,
            fiscal_status: 'TAXED',
            legal_status: 'DE_JURE',
            claimed_since_tick: 0,
            recognition_level: 1.0
        }]->(terr)
    """)
    print("  [OK] Created CLAIMS: SOV_USA_FED -> US-CA (control: 1.0)")

    # USA Federal Government claims Los Angeles (reduced control - unrest)
    conn.execute("""
        MATCH (sov:Sovereign {id: 'SOV_USA_FED'})
        MATCH (terr:Territory {id: 'US-CA-037-LA'})
        CREATE (sov)-[:CLAIMS {
            control_level: 0.6,
            fiscal_status: 'REVOLT',
            legal_status: 'DE_JURE',
            claimed_since_tick: 0,
            recognition_level: 1.0
        }]->(terr)
    """)
    print("  [OK] Created CLAIMS: SOV_USA_FED -> US-CA-037-LA (control: 0.6)")

    # Revolutionary Command claims Los Angeles (dual power situation!)
    conn.execute("""
        MATCH (sov:Sovereign {id: 'SOV_PRC'})
        MATCH (terr:Territory {id: 'US-CA-037-LA'})
        CREATE (sov)-[:CLAIMS {
            control_level: 0.4,
            fiscal_status: 'LIBERATED',
            legal_status: 'DE_FACTO',
            claimed_since_tick: 0,
            recognition_level: 0.1
        }]->(terr)
    """)
    print("  [OK] Created CLAIMS: SOV_PRC -> US-CA-037-LA (control: 0.4)")
    print("       ^ DUAL POWER: LA has claims from both USA and PRC!")

    # =========================================================================
    # ADMINISTERS EDGE (Administrative Hierarchy - unchanged)
    # =========================================================================

    # California administers Los Angeles (bureaucratic hierarchy)
    conn.execute("""
        MATCH (parent:Territory {id: 'US-CA'})
        MATCH (child:Territory {id: 'US-CA-037-LA'})
        CREATE (parent)-[:ADMINISTERS {
            control_level: 0.9,
            legal_status: 'DE_JURE'
        }]->(child)
    """)
    print("  [OK] Created ADMINISTERS: US-CA -> US-CA-037-LA")

    print("\nTest data insertion complete.")
    print("\n" + "=" * 70)
    print("DYNAMIC SOVEREIGNTY DEMONSTRATION")
    print("=" * 70)
    print("""
Los Angeles (US-CA-037-LA) is in a DUAL POWER situation:
  - SOV_USA_FED claims with control_level=0.6 (de jure authority)
  - SOV_PRC claims with control_level=0.4 (de facto insurgent control)

Total control = 1.0 (contested but accounted for)

This is the core of Dynamic Sovereignty: sovereignty as EDGES, not properties.
    """)


def verify_test_data(conn: kuzu.Connection) -> bool:
    """Verify test data was inserted correctly.

    Args:
        conn: KuzuDB connection object.

    Returns:
        True if verification passed, False otherwise.
    """
    print("\nVerifying test data...")

    # Count sovereigns
    result = conn.execute("MATCH (s:Sovereign) RETURN COUNT(s) AS count")
    count = result.get_next()[0]
    if count != 2:
        print(f"  [FAIL] Expected 2 sovereigns, found {count}")
        return False
    print(f"  [OK] Sovereign count: {count}")

    # Count territories
    result = conn.execute("MATCH (t:Territory) RETURN COUNT(t) AS count")
    count = result.get_next()[0]
    if count != 2:
        print(f"  [FAIL] Expected 2 territories, found {count}")
        return False
    print(f"  [OK] Territory count: {count}")

    # Verify CLAIMS edges
    result = conn.execute("""
        MATCH (sov:Sovereign)-[c:CLAIMS]->(terr:Territory)
        RETURN sov.name, terr.name, c.control_level, c.legal_status
        ORDER BY terr.name, c.control_level DESC
    """)
    claims = result.get_all()
    if len(claims) != 3:
        print(f"  [FAIL] Expected 3 CLAIMS edges, found {len(claims)}")
        return False
    print(f"  [OK] CLAIMS edge count: {len(claims)}")
    for sov_name, terr_name, control, status in claims:
        print(f"       {sov_name} -> {terr_name}: {control} ({status})")

    # Verify dual power situation (contested territory)
    result = conn.execute("""
        MATCH (terr:Territory {id: 'US-CA-037-LA'})
        MATCH (sov:Sovereign)-[c:CLAIMS]->(terr)
        RETURN COUNT(sov) AS claim_count
    """)
    claim_count = result.get_next()[0]
    if claim_count != 2:
        print(f"  [FAIL] Expected 2 claims on LA (dual power), found {claim_count}")
        return False
    print(f"  [OK] Dual power verified: LA has {claim_count} sovereignty claims")

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

    # Query: Find effective controller of each territory
    print("\n  Effective controllers (highest control_level):")
    result = conn.execute("""
        MATCH (terr:Territory)
        OPTIONAL MATCH (sov:Sovereign)-[c:CLAIMS]->(terr)
        WITH terr, sov, c
        ORDER BY c.control_level DESC
        WITH terr, COLLECT({sov: sov.name, control: c.control_level})[0] AS top_claim
        RETURN terr.name, top_claim.sov, top_claim.control
    """)
    for terr_name, sov_name, control in result.get_all():
        print(f"       {terr_name}: {sov_name} ({control})")

    print("\nAll verifications passed!")
    return True


def print_fracture_example() -> None:
    """Print example Cypher queries demonstrating the Fracture Operation.

    This shows how sovereignty transfers work via edge manipulation.
    """
    print("\n" + "=" * 70)
    print("FRACTURE OPERATION EXAMPLE (Secession)")
    print("=" * 70)
    print("""
To transfer sovereignty from USA to Revolutionary Command over Los Angeles:

STEP 1: Reduce USA control (or delete the edge entirely)
------------------------------------------------------------------------
MATCH (usa:Sovereign {id: 'SOV_USA_FED'})-[c:CLAIMS]->(la:Territory {id: 'US-CA-037-LA'})
SET c.control_level = 0.0, c.legal_status = 'CEDED'

// OR delete entirely:
// MATCH (usa:Sovereign {id: 'SOV_USA_FED'})-[c:CLAIMS]->(la:Territory {id: 'US-CA-037-LA'})
// DELETE c


STEP 2: Increase Revolutionary control (it already exists from dual power)
------------------------------------------------------------------------
MATCH (prc:Sovereign {id: 'SOV_PRC'})-[c:CLAIMS]->(la:Territory {id: 'US-CA-037-LA'})
SET c.control_level = 1.0, c.legal_status = 'DE_FACTO'


RESULT: Los Angeles is now fully under Revolutionary control!
------------------------------------------------------------------------
This is O(1) complexity - just edge property updates.
No Territory node properties need to change.
The "Land" (ADJACENT_TO edges) is completely unaffected.


ALTERNATIVE: Create new sovereign during secession
------------------------------------------------------------------------
// California declares independence:
CREATE (s:Sovereign {
    id: 'SOV_CAL_REP',
    name: 'California Republic',
    sovereignty_type: 'SECESSIONIST',
    legitimacy: 0.3,
    color_hex: '#FFD700'
})

// Transfer claim:
MATCH (usa:Sovereign {id: 'SOV_USA_FED'})-[c:CLAIMS]->(ca:Territory {id: 'US-CA'})
DELETE c

MATCH (cal:Sovereign {id: 'SOV_CAL_REP'})
MATCH (ca:Territory {id: 'US-CA'})
CREATE (cal)-[:CLAIMS {control_level: 0.8, legal_status: 'DE_FACTO'}]->(ca)
    """)


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
            # Show fracture example for educational purposes
            print_fracture_example()

        print(f"\nEpoch 2 database initialized successfully at: {args.db_path}")
        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
