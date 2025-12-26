#!/usr/bin/env python3
"""Initialize the Epoch 2 KuzuDB Strategic Map.

This script creates the graph schema for continental-scale simulation:
- Sovereign nodes (Dynamic Sovereignty - v1.1.0)
- Faction nodes (Balkanization System - v1.2.0)
- Territory nodes (OGV/OPC)
- CLAIMS edges (Sovereign -> Territory sovereignty claims)
- INFLUENCES edges (Faction -> Territory political influence)
- ADMINISTERS edges (Territory -> Territory administrative hierarchy)
- ADJACENT_TO edges (Territory -> Territory physical adjacency mesh)

Key Design (Dynamic Sovereignty):
    Sovereignty is expressed as CLAIMS edges from Sovereign nodes to Territory nodes,
    NOT as a property on Territory. This enables O(1) border changes for:
    - Civil war (multiple competing claims)
    - Secession (edge rewiring)
    - Conquest (claim transfer)

Key Design (Balkanization System - v1.2.0):
    Factions have colonial_stance (UPHOLD/IGNORE/ABOLISH) determining their relationship
    to settler colonialism. When a Sovereign collapses, the Faction with highest
    INFLUENCES edges wins and creates a new Sovereign with:
    - UPHOLD -> extraction_policy: INTENSIFY
    - IGNORE -> extraction_policy: CONTINUE (THE RED SETTLER TRAP)
    - ABOLISH -> extraction_policy: CEASE (the only path to healing)

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

# Sovereign: Political entities that claim sovereignty over territories (v1.1.0 + v1.2.0)
SOVEREIGN_NODE_SCHEMA = """
CREATE NODE TABLE IF NOT EXISTS Sovereign (
    id STRING PRIMARY KEY,
    name STRING,
    sovereignty_type STRING DEFAULT 'RECOGNIZED_STATE',
    legitimacy DOUBLE DEFAULT 1.0,
    color_hex STRING DEFAULT '#808080',
    capital_territory_id STRING,
    founded_tick INT32 DEFAULT 0,
    dissolved_tick INT32,
    ruling_faction_id STRING,
    extraction_policy STRING DEFAULT 'CONTINUE'
)
"""

# Faction: Political formations that contest sovereignty (v1.2.0 - Balkanization)
# colonial_stance determines extraction_policy when ruling: UPHOLD->INTENSIFY, IGNORE->CONTINUE, ABOLISH->CEASE
FACTION_NODE_SCHEMA = """
CREATE NODE TABLE IF NOT EXISTS Faction (
    id STRING PRIMARY KEY,
    name STRING,
    ideology STRING,
    colonial_stance STRING,
    is_settler_formation BOOLEAN DEFAULT true,
    extraction_modifier DOUBLE DEFAULT 1.0,
    violence_modifier DOUBLE DEFAULT 1.0,
    class_reduction DOUBLE DEFAULT 0.0,
    metabolic_reduction DOUBLE DEFAULT 0.0,
    color_hex STRING DEFAULT '#808080',
    founded_tick INT32 DEFAULT 0
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

# INFLUENCES: Faction influence over territories (v1.2.0 - Balkanization)
# When a Sovereign collapses, faction with highest SUM(influence_level) wins
INFLUENCES_EDGE_SCHEMA = """
CREATE REL TABLE IF NOT EXISTS INFLUENCES (
    FROM Faction TO Territory,
    influence_level DOUBLE DEFAULT 0.0,
    support_type STRING DEFAULT 'IDEOLOGICAL',
    cadre_count INT32 DEFAULT 0,
    sympathizer_count INT64 DEFAULT 0,
    established_tick INT32 DEFAULT 0
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
        ("Faction node", FACTION_NODE_SCHEMA),
        ("Territory node", TERRITORY_NODE_SCHEMA),
        # Edge tables (depend on node tables)
        ("CLAIMS edge", CLAIMS_EDGE_SCHEMA),
        ("INFLUENCES edge", INFLUENCES_EDGE_SCHEMA),
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
    """Insert test data demonstrating Dynamic Sovereignty and Balkanization.

    Creates:
    - 2 Sovereigns: USA Federal Government and Provisional Revolutionary Command
    - 3 Factions: Restorationist Front, Workers' Congress, Decolonial Front
    - 2 Territories: California and Los Angeles
    - CLAIMS edges showing sovereignty relationships
    - INFLUENCES edges showing faction influence (demonstrates THE RED SETTLER TRAP)
    - ADMINISTERS edge showing administrative hierarchy

    THE RED SETTLER TRAP Demonstration:
        In LA County, Workers' Congress (IGNORE stance) has higher influence (0.7)
        than Decolonial Front (ABOLISH stance, 0.3). If USA collapses in LA,
        Workers' Congress wins -> extraction_policy: CONTINUE -> planet still dies.

    Args:
        conn: KuzuDB connection object.
    """
    print("\nInserting test data...")

    # =========================================================================
    # SOVEREIGN NODES
    # =========================================================================

    # Create United States Federal Government sovereign
    # NOTE: No ruling_faction_id - the "neutral" state that maintains extraction
    conn.execute("""
        CREATE (s:Sovereign {
            id: 'SOV_USA_FED',
            name: 'United States Federal Government',
            sovereignty_type: 'RECOGNIZED_STATE',
            legitimacy: 1.0,
            color_hex: '#3C3B6E',
            founded_tick: 0,
            extraction_policy: 'CONTINUE'
        })
    """)
    print("  [OK] Created Sovereign: SOV_USA_FED (extraction_policy: CONTINUE)")

    # Create Provisional Revolutionary Command sovereign (player faction)
    # This sovereign is controlled by Workers' Congress - THE TRAP
    conn.execute("""
        CREATE (s:Sovereign {
            id: 'SOV_PRC',
            name: 'Provisional Revolutionary Command',
            sovereignty_type: 'INSURGENT',
            legitimacy: 0.2,
            color_hex: '#B22234',
            founded_tick: 0,
            ruling_faction_id: 'FAC_WORKERS_CONGRESS',
            extraction_policy: 'CONTINUE'
        })
    """)
    print("  [OK] Created Sovereign: SOV_PRC (ruled by Workers' Congress)")
    print("       ^ THE TRAP: extraction_policy is CONTINUE despite red flag!")

    # =========================================================================
    # FACTION NODES (Balkanization v1.2.0)
    # =========================================================================

    # Restorationist Front - Fascist (UPHOLD stance)
    conn.execute("""
        CREATE (f:Faction {
            id: 'FAC_RESTORATIONIST',
            name: 'Restorationist Front',
            ideology: 'FASCISM',
            colonial_stance: 'UPHOLD',
            is_settler_formation: true,
            extraction_modifier: 1.5,
            violence_modifier: 1.5,
            class_reduction: 0.0,
            metabolic_reduction: -0.5,
            color_hex: '#000000',
            founded_tick: 0
        })
    """)
    print("  [OK] Created Faction: FAC_RESTORATIONIST (UPHOLD - accelerates extraction)")

    # Workers' Congress - Settler-Socialist (IGNORE stance) - THE TRAP
    conn.execute("""
        CREATE (f:Faction {
            id: 'FAC_WORKERS_CONGRESS',
            name: 'Workers Congress',
            ideology: 'SETTLER_SOCIALISM',
            colonial_stance: 'IGNORE',
            is_settler_formation: true,
            extraction_modifier: 0.8,
            violence_modifier: 0.6,
            class_reduction: 0.8,
            metabolic_reduction: 0.0,
            color_hex: '#FF0000',
            founded_tick: 0
        })
    """)
    print("  [OK] Created Faction: FAC_WORKERS_CONGRESS (IGNORE - THE RED SETTLER TRAP)")
    print("       ^ High class_reduction but ZERO metabolic_reduction!")

    # Decolonial Front - Anti-Colonial Communist (ABOLISH stance) - Correct Path
    conn.execute("""
        CREATE (f:Faction {
            id: 'FAC_DECOLONIAL',
            name: 'Decolonial Front',
            ideology: 'ANTI_COLONIAL_COMMUNISM',
            colonial_stance: 'ABOLISH',
            is_settler_formation: false,
            extraction_modifier: 0.0,
            violence_modifier: 0.3,
            class_reduction: 0.5,
            metabolic_reduction: 0.8,
            color_hex: '#008000',
            founded_tick: 0
        })
    """)
    print("  [OK] Created Faction: FAC_DECOLONIAL (ABOLISH - only path to healing)")

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
    # INFLUENCES EDGES (Balkanization v1.2.0)
    # =========================================================================

    # Workers' Congress has highest influence in LA - THE TRAP
    conn.execute("""
        MATCH (fac:Faction {id: 'FAC_WORKERS_CONGRESS'})
        MATCH (terr:Territory {id: 'US-CA-037-LA'})
        CREATE (fac)-[:INFLUENCES {
            influence_level: 0.7,
            support_type: 'LABOR',
            cadre_count: 200,
            sympathizer_count: 500000,
            established_tick: 0
        }]->(terr)
    """)
    print("  [OK] Created INFLUENCES: FAC_WORKERS_CONGRESS -> US-CA-037-LA (0.7)")
    print("       ^ THE TRAP: Highest influence in LA! If collapse, they win.")

    # Decolonial Front has lower influence - the harder path
    conn.execute("""
        MATCH (fac:Faction {id: 'FAC_DECOLONIAL'})
        MATCH (terr:Territory {id: 'US-CA-037-LA'})
        CREATE (fac)-[:INFLUENCES {
            influence_level: 0.3,
            support_type: 'IDEOLOGICAL',
            cadre_count: 80,
            sympathizer_count: 150000,
            established_tick: 0
        }]->(terr)
    """)
    print("  [OK] Created INFLUENCES: FAC_DECOLONIAL -> US-CA-037-LA (0.3)")
    print("       ^ Player must actively build this to flip LA!")

    # Workers' Congress also in California statewide
    conn.execute("""
        MATCH (fac:Faction {id: 'FAC_WORKERS_CONGRESS'})
        MATCH (terr:Territory {id: 'US-CA'})
        CREATE (fac)-[:INFLUENCES {
            influence_level: 0.4,
            support_type: 'ELECTORAL',
            cadre_count: 100,
            sympathizer_count: 2000000,
            established_tick: 0
        }]->(terr)
    """)
    print("  [OK] Created INFLUENCES: FAC_WORKERS_CONGRESS -> US-CA (0.4)")

    # Restorationist has no influence in California (coastal elite territory)
    # They dominate rural areas (not in this test set)

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
    print("=" * 70)
    print("THE RED SETTLER TRAP DEMONSTRATION")
    print("=" * 70)
    print("""
Los Angeles has competing FACTION influences:
  - FAC_WORKERS_CONGRESS (IGNORE stance): influence_level=0.7
  - FAC_DECOLONIAL (ABOLISH stance): influence_level=0.3

THE TRAP: If USA collapses in LA, Workers' Congress WINS!
  - New Sovereign gets extraction_policy: CONTINUE
  - Habitability continues to degrade (-0.005/tick)
  - Player experiences "false summit" - won revolution, losing planet

THE CORRECT PATH:
  - Player must actively build FAC_DECOLONIAL influence
  - Flip LA so Decolonial has majority when collapse occurs
  - Only then: extraction_policy: CEASE, habitability can recover (+0.01/tick)

The three factions represent three relationships to settler colonialism:
  - UPHOLD (Restorationist): Explicit fascist defense of extraction
  - IGNORE (Workers' Congress): Class-only socialism, maintains extraction
  - ABOLISH (Decolonial): Only path to true liberation and ecological healing
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

    # Count factions (v1.2.0)
    result = conn.execute("MATCH (f:Faction) RETURN COUNT(f) AS count")
    count = result.get_next()[0]
    if count != 3:
        print(f"  [FAIL] Expected 3 factions, found {count}")
        return False
    print(f"  [OK] Faction count: {count}")

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

    # Verify INFLUENCES edges (v1.2.0)
    result = conn.execute("""
        MATCH (fac:Faction)-[i:INFLUENCES]->(terr:Territory)
        RETURN fac.name, terr.name, i.influence_level, i.support_type
        ORDER BY terr.name, i.influence_level DESC
    """)
    influences = result.get_all()
    if len(influences) != 3:
        print(f"  [FAIL] Expected 3 INFLUENCES edges, found {len(influences)}")
        return False
    print(f"\n  [OK] INFLUENCES edge count: {len(influences)}")
    for fac_name, terr_name, influence, support in influences:
        print(f"       {fac_name} -> {terr_name}: {influence} ({support})")

    # Verify THE RED SETTLER TRAP - Workers' Congress dominates LA
    result = conn.execute("""
        MATCH (fac:Faction)-[i:INFLUENCES]->(terr:Territory {id: 'US-CA-037-LA'})
        RETURN fac.name, fac.colonial_stance, i.influence_level
        ORDER BY i.influence_level DESC
    """)
    influences = result.get_all()
    if len(influences) != 2:
        print(f"  [FAIL] Expected 2 factions influencing LA, found {len(influences)}")
        return False
    top_faction, top_stance, top_influence = influences[0]
    if top_stance != "IGNORE":
        print(f"  [FAIL] Expected IGNORE faction to dominate LA, found {top_stance}")
        return False
    print("\n  [OK] THE RED SETTLER TRAP verified:")
    print(f"       LA dominated by {top_faction} ({top_stance} stance) at {top_influence}")
    print("       If collapse -> extraction_policy: CONTINUE -> planet dies")

    # Verify faction colonial stances
    result = conn.execute("""
        MATCH (f:Faction)
        RETURN f.name, f.colonial_stance, f.extraction_modifier, f.metabolic_reduction
        ORDER BY f.extraction_modifier DESC
    """)
    print("\n  Faction colonial stances:")
    for name, stance, extr_mod, metab_red in result.get_all():
        print(f"       {name}: {stance} (extraction: {extr_mod}x, metabolic: {metab_red})")

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
