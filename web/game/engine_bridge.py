"""Engine bridge — the sole translation layer between Django and the simulation engine.

This is the **ONLY** file in ``web/`` that imports from ``babylon.engine``,
``babylon.models``, ``babylon.config``, ``babylon.ooda``, or
``babylon.persistence``.  Django views and serializers call this bridge;
they never see engine internals.

All methods return plain Python dicts / lists / scalars that are
JSON-serializable, suitable for DRF serializer consumption.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from babylon.config.defines import GameDefines
from babylon.engine.graph import BabylonGraph
from babylon.engine.scenarios import get_scenario, list_scenarios
from babylon.engine.simulation_engine import step
from babylon.engine.trap_detection import TrapDetectionResult, detect_traps
from babylon.formulas.unequal_exchange import calculate_unequal_exchange_rate
from babylon.models.config import SimulationConfig
from babylon.models.enums import ActionType
from babylon.models.vanguard_resources import VanguardResources, check_can_afford
from babylon.models.world_state import WorldState
from babylon.ooda.npc_stub import select_npc_actions
from babylon.persistence.protocols import RuntimePersistence, TickAlreadyResolved

from .map_contract import MAP_METRIC_PROPERTIES

if TYPE_CHECKING:
    from game.narrator import NarratorProvider

logger = logging.getLogger(__name__)

# Per-session action history for trap detection (in-memory, not persisted).
# Maps session_id -> list of recent action dicts (capped at 50).
_session_action_history: dict[UUID, list[dict[str, Any]]] = {}

# Per-session trap state for severity persistence across ticks.
_session_trap_state: dict[UUID, TrapDetectionResult] = {}

_ACTION_HISTORY_CAP = 50

# Spec 092: journal/alerts dashboards.
# Max rows returned by get_journal_dashboard (newest tick first).
_JOURNAL_LIMIT = 200
# Severities surfaced by get_alerts_dashboard — "informational" is routine
# flow, not an alert (matches _EVENT_SEVERITY's three-bucket taxonomy).
_ALERT_SEVERITIES = frozenset({"critical", "warning"})

# Spec 095: all 5 terminal GameOutcome event types (FR-095-02). The previous
# bridge layer only recognized 3 of 5 (the Slice 1.6 set), so RED_OGV and
# FRAGMENTED_COLLAPSE endgames never surfaced in the snapshot's ``endgame``
# block. This set is the authoritative source for both ``resolve_tick`` and
# ``get_endgame_state``. Matches ``babylon.models.enums.GameOutcome`` minus
# ``IN_PROGRESS`` (the non-terminal sentinel).
_TERMINAL_OUTCOMES: frozenset[str] = frozenset(
    {
        "REVOLUTIONARY_VICTORY",
        "ECOLOGICAL_COLLAPSE",
        "FASCIST_CONSOLIDATION",
        "RED_OGV",
        "FRAGMENTED_COLLAPSE",
    }
)

# Spec 095: canonical headlines for the chronicle end-screen (FR-095-09).
# REVOLUTIONARY_VICTORY → rupture palette ("BABYLON FALLS"); all others →
# defeat palette ("THE BUNKER FAILS"). Matches the EndState.jsx mockup.
_OUTCOME_HEADLINES: dict[str, str] = {
    "REVOLUTIONARY_VICTORY": "BABYLON FALLS",
    "ECOLOGICAL_COLLAPSE": "THE BUNKER FAILS",
    "FASCIST_CONSOLIDATION": "THE BUNKER FAILS",
    "RED_OGV": "THE BUNKER FAILS",
    "FRAGMENTED_COLLAPSE": "THE BUNKER FAILS",
}

# ---------------------------------------------------------------------- #
# Verb-to-ActionType mapping (9 canonical player verbs → engine ActionType)
# See: specs/041-mvp-nationwide-sim/research.md §2
# ---------------------------------------------------------------------- #

# Verb-dispatch engine: all 9 canonical player verbs now have a real engine
# resolver (``babylon.engine.actions.VERB_RESOLVERS``). This map is the sole
# translation of player verb strings to engine ActionTypes; its values must
# equal the resolver registry's keys (pinned by
# ``tests/contract/verbs/test_registry.py``). ``get_available_actions()``
# derives its output from this map, so every mapped verb is exposed.
VERB_TO_ACTION_TYPE: dict[str, ActionType] = {
    "educate": ActionType.EDUCATE,
    "reproduce": ActionType.RECRUIT,
    "attack": ActionType.ATTACK_INFRASTRUCTURE,
    "mobilize": ActionType.PROTEST,
    "campaign": ActionType.PROPAGANDIZE,
    "aid": ActionType.PROVIDE_SERVICE,
    "investigate": ActionType.MAP_NETWORK,
    "move": ActionType.MOVE,
    "negotiate": ActionType.PROPOSE_ALLIANCE,
}

CANONICAL_VERBS: frozenset[str] = frozenset(VERB_TO_ACTION_TYPE.keys())


def _fetch_session_rng_seed_from_pool(pool: Any, session_id: UUID) -> int:
    """Read ``rng_seed`` from ``game_session`` (T080 / FR-024).

    Falls back to 0 when the connection fails or the row is missing —
    determinism is best-effort during transient outages.
    """
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT rng_seed FROM game_session WHERE id = %s",
                (session_id,),
            )
            row = cur.fetchone()
            if row and row[0] is not None:
                return int(row[0])
    except Exception:  # noqa: BLE001 — non-fatal; defaults to 0
        logger.exception("Failed to read rng_seed for session %s", session_id)
    return 0


def _fetch_session_game_defines(persistence: Any, session_id: UUID) -> GameDefines:
    """Read this session's GameDefines from its ``game_session`` row (C.13).

    Defines are stored per-session in ``game_session.game_defines_json``
    at creation (see :meth:`EngineBridge.create_game`). The old code read
    the GLOBAL ``get_metadata("game_defines_json")`` blob — a key nothing
    ever wrote, and one shared by every session in the database — so
    per-session defines were silently ignored. Falls back to library
    defaults when the persistence layer has no session store
    (StubEngineBridge / SQLite dev) or the row is missing.
    """
    session_getter = getattr(persistence, "get_session", None)
    if not callable(session_getter):
        return GameDefines()
    try:
        row = session_getter(session_id)
    except Exception:  # noqa: BLE001 — non-fatal; defaults are safe
        logger.exception("Failed to read game_defines_json for session %s", session_id)
        return GameDefines()
    if not isinstance(row, dict):
        return GameDefines()
    raw = row.get("game_defines_json")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            logger.exception("Malformed game_defines_json for session %s", session_id)
            return GameDefines()
    if isinstance(raw, dict) and raw:
        return GameDefines(**raw)
    return GameDefines()


# ---------------------------------------------------------------------- #
# Spec 095: contradiction snapshot + endgame + objectives helpers.
# Pure reads over persisted state — Constitution III (AI observes).
# ---------------------------------------------------------------------- #


def _fetch_contradiction_field_rows(pool: Any, session_id: UUID) -> list[dict[str, Any]]:
    """Read ``contradiction_field`` rows for the latest tick (FR-095-01).

    Mirrors :func:`_fetch_session_rng_seed_from_pool`'s SQL-read pattern.
    Returns one row per opposition key at the latest tick, with
    ``field_name``, ``value`` (gap), ``dt`` (rate). Degrades to an empty
    list when the pool is unavailable (SQLite dev/test) or the query fails.
    """
    if pool is None:
        return []
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT tick, field_name, value, dt
                FROM contradiction_field
                WHERE session_id = %s
                  AND tick = (
                      SELECT MAX(tick) FROM contradiction_field WHERE session_id = %s
                  )
                """,
                (session_id, session_id),
            )
            rows = cur.fetchall()
            result: list[dict[str, Any]] = []
            for row in rows:
                if isinstance(row, dict):
                    result.append(row)
                elif isinstance(row, (tuple, list)) and len(row) >= 4:
                    result.append(
                        {
                            "tick": row[0],
                            "field_name": row[1],
                            "value": row[2],
                            "dt": row[3],
                        }
                    )
            return result
    except Exception:  # noqa: BLE001 — non-fatal; degrades to empty list
        logger.exception("Failed to read contradiction_field rows for session %s", session_id)
        return []


def _aspect_to_frame_entry(aspect: Any) -> dict[str, Any]:
    """Normalize a contradiction aspect dict for the frame block."""
    if not isinstance(aspect, dict):
        return {}
    return {
        "id": str(aspect.get("id", "")),
        "aspect_a": str(aspect.get("aspect_a", "")),
        "aspect_b": str(aspect.get("aspect_b", "")),
        "principal_aspect": str(aspect.get("principal_aspect", "")),
        "intensity": float(aspect.get("intensity", 0.0)),
        "aspect_balance": float(aspect.get("aspect_balance", 0.0)),
        "is_antagonistic": bool(aspect.get("is_antagonistic", False)),
    }


# ---------------------------------------------------------------------- #
# Spec 103: Trade surfaces — helpers for boundary_flow_register +
# dynamic_external_node_state + county_exposure_by_external reads.
# Pure reads over persisted engine state — Constitution III.
# ---------------------------------------------------------------------- #

_BLOC_LABELS: dict[str, str] = {
    "canada": "Canada",
    "china": "China",
    "eu": "EU",
    "india": "India",
    "sub_saharan_africa": "Sub-Saharan Africa",
    "latin_america": "Latin America",
    "russia_csi": "Russia/CSI",
    "southeast_asia": "Southeast Asia",
    "rest_of_usa": "Rest of USA",
}

# Canonical citation provenance for the exposure breakdown's terminal leaves.
# These describe the reference-data lineage the spec-100 weights trace to.
_EXPOSURE_CITATIONS: list[dict[str, Any]] = [
    {
        "id": "bea-io-2023",
        "source": "BEA I-O imports",
        "table": "fact_bea_io_coefficient",
        "year": 2023,
        "notes": "Import coefficients per industry — the import exposure numerator.",
    },
    {
        "id": "qcew-2023q2",
        "source": "QCEW county industry shares",
        "table": "fact_qcew",
        "year": "2023Q2",
        "notes": "County-level industry employment shares — the exposure allocation key.",
    },
    {
        "id": "hickel-drain",
        "source": "Hickel drain",
        "table": "immutable_reference_hickel_drain",
        "notes": "Annual Φ (drain) inflow per external bloc.",
    },
]


def _fetch_boundary_flow_series(pool: Any, session_id: UUID) -> list[dict[str, Any]]:
    """Read ``boundary_flow_register`` per-tick rows grouped by source + flow_type.

    Returns one dict per ``(tick, source_node_id, flow_type)`` with the summed
    magnitude. Degrades to an empty list when the pool is unavailable or the
    query fails (SQLite dev/test, SIM DB absent).
    """
    if pool is None:
        return []
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT tick, source_node_id, flow_type, SUM(magnitude) AS magnitude
                FROM boundary_flow_register
                WHERE session_id = %s
                  AND source_kind = 'external'
                GROUP BY tick, source_node_id, flow_type
                ORDER BY tick, source_node_id, flow_type
                """,
                (session_id,),
            )
            rows = cur.fetchall()
            result: list[dict[str, Any]] = []
            for row in rows:
                if isinstance(row, dict):
                    result.append(
                        {
                            "tick": int(row["tick"]),
                            "source_node_id": str(row["source_node_id"]),
                            "flow_type": str(row["flow_type"]),
                            "magnitude": float(row["magnitude"] or 0.0),
                        }
                    )
                elif isinstance(row, (tuple, list)) and len(row) >= 4:
                    result.append(
                        {
                            "tick": int(row[0]),
                            "source_node_id": str(row[1]),
                            "flow_type": str(row[2]),
                            "magnitude": float(row[3] or 0.0),
                        }
                    )
            return result
    except Exception:  # noqa: BLE001 — non-fatal; degrades to empty list
        logger.exception("Failed to read boundary_flow_register for session %s", session_id)
        return []


def _fetch_county_boundary_flows(
    pool: Any, session_id: UUID, county_fips: str
) -> list[dict[str, Any]]:
    """Read ``boundary_flow_register`` rows where ``dest_node_id = county_fips``.

    Returns one dict per ``(tick, source_node_id, flow_type, magnitude)``.
    Degrades to an empty list when the pool is unavailable or the query fails.
    """
    if pool is None:
        return []
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT tick, source_node_id, flow_type, magnitude
                FROM boundary_flow_register
                WHERE session_id = %s
                  AND dest_node_id = %s
                ORDER BY source_node_id, tick
                """,
                (session_id, county_fips),
            )
            rows = cur.fetchall()
            result: list[dict[str, Any]] = []
            for row in rows:
                if isinstance(row, dict):
                    result.append(
                        {
                            "tick": int(row["tick"]),
                            "source_node_id": str(row["source_node_id"]),
                            "flow_type": str(row["flow_type"]),
                            "magnitude": float(row["magnitude"] or 0.0),
                        }
                    )
                elif isinstance(row, (tuple, list)) and len(row) >= 4:
                    result.append(
                        {
                            "tick": int(row[0]),
                            "source_node_id": str(row[1]),
                            "flow_type": str(row[2]),
                            "magnitude": float(row[3] or 0.0),
                        }
                    )
            return result
    except Exception:  # noqa: BLE001 — non-fatal; degrades to empty list
        logger.exception("Failed to read county boundary flows for %s/%s", session_id, county_fips)
        return []


def _fetch_external_node_latest(pool: Any, session_id: UUID) -> dict[str, dict[str, Any]]:
    """Read the latest ``dynamic_external_node_state`` row per node_id.

    Returns ``{node_id: {kind, phi_year_inflow, bilateral_trade_value,
    bilateral_trade_tons, erdi_ratio, tick}}``. Degrades to an empty dict
    when the pool is unavailable or the query fails.
    """
    if pool is None:
        return {}
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT node_id, kind, phi_year_inflow, bilateral_trade_value,
                       bilateral_trade_tons, erdi_ratio, tick
                FROM dynamic_external_node_state e
                WHERE session_id = %s
                  AND tick = (
                      SELECT MAX(tick) FROM dynamic_external_node_state
                      WHERE session_id = %s AND node_id = e.node_id
                  )
                ORDER BY node_id
                """,
                (session_id, session_id),
            )
            rows = cur.fetchall()
            result: dict[str, dict[str, Any]] = {}
            for row in rows:
                if isinstance(row, dict):
                    nid = str(row["node_id"])
                    result[nid] = {
                        "kind": str(row.get("kind", "international")),
                        "phi_year_inflow": float(row.get("phi_year_inflow", 0.0)),
                        "bilateral_trade_value": float(row.get("bilateral_trade_value", 0.0)),
                        "bilateral_trade_tons": float(row.get("bilateral_trade_tons", 0.0)),
                        "erdi_ratio": float(row.get("erdi_ratio", 1.0)),
                        "tick": int(row.get("tick", 0)),
                    }
                elif isinstance(row, (tuple, list)) and len(row) >= 7:
                    nid = str(row[0])
                    result[nid] = {
                        "kind": str(row[1]),
                        "phi_year_inflow": float(row[2]),
                        "bilateral_trade_value": float(row[3]),
                        "bilateral_trade_tons": float(row[4]),
                        "erdi_ratio": float(row[5]),
                        "tick": int(row[6]),
                    }
            return result
    except Exception:  # noqa: BLE001 — non-fatal; degrades to empty dict
        logger.exception("Failed to read external_node_state for session %s", session_id)
        return {}


def _fetch_county_exposure_weights(pool: Any, county_fips: str) -> dict[str, float]:
    """Read spec-100's ``county_exposure_by_external`` weights for a county.

    Returns ``{bloc_node_id: weight}``. The table is not yet built (spec-100
    is Lane D, unbuilt) — this degrades to an empty dict when the table is
    absent or the query fails. Forward-compatible: when spec-100 lands, the
    weights populate without a frontend change.
    """
    if pool is None:
        return {}
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT bloc_node_id, weight
                FROM county_exposure_by_external
                WHERE county_fips = %s
                ORDER BY bloc_node_id
                """,
                (county_fips,),
            )
            rows = cur.fetchall()
            result: dict[str, float] = {}
            for row in rows:
                if isinstance(row, dict):
                    result[str(row["bloc_node_id"])] = float(row.get("weight", 0.0))
                elif isinstance(row, (tuple, list)) and len(row) >= 2:
                    result[str(row[0])] = float(row[1])
            return result
    except Exception:  # noqa: BLE001 — non-fatal; spec-100 table may be absent
        logger.debug("county_exposure_by_external not available for %s", county_fips)
        return {}


def _fetch_flow_type_totals(pool: Any, session_id: UUID) -> list[dict[str, Any]]:
    """Read session-cumulative ``boundary_flow_register`` totals per flow_type.

    Returns one dict per ``flow_type`` with ``total`` (SUM magnitude) and
    ``tick_count`` (distinct ticks). Degrades to an empty list.
    """
    if pool is None:
        return []
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT flow_type,
                       COALESCE(SUM(magnitude), 0) AS total,
                       COUNT(DISTINCT tick) AS tick_count
                FROM boundary_flow_register
                WHERE session_id = %s
                GROUP BY flow_type
                ORDER BY flow_type
                """,
                (session_id,),
            )
            rows = cur.fetchall()
            result: list[dict[str, Any]] = []
            for row in rows:
                if isinstance(row, dict):
                    result.append(
                        {
                            "flow_type": str(row["flow_type"]),
                            "total": float(row.get("total", 0.0)),
                            "tick_count": int(row.get("tick_count", 0)),
                        }
                    )
                elif isinstance(row, (tuple, list)) and len(row) >= 3:
                    result.append(
                        {
                            "flow_type": str(row[0]),
                            "total": float(row[1]),
                            "tick_count": int(row[2]),
                        }
                    )
            return result
    except Exception:  # noqa: BLE001 — non-fatal; degrades to empty list
        logger.exception("Failed to read flow_type totals for session %s", session_id)
        return []


def _extract_event_type(event: Any) -> str:
    """Extract a normalized event_type string from a dict or object event."""
    if isinstance(event, dict):
        return str(event.get("event_type", ""))
    et = getattr(event, "event_type", None)
    if et is None:
        return ""
    if hasattr(et, "value"):
        return str(et.value)
    return str(et)


def _extract_event_data(event: Any, key: str, default: Any = None) -> Any:
    """Extract a field from an event's ``data`` block (dict or object)."""
    data: Any = event.get("data") if isinstance(event, dict) else getattr(event, "data", None)
    if isinstance(data, dict):
        return data.get(key, default)
    return default


def _compute_avg_node_attr(graph: Any, attr: str, default: float = 0.0) -> float:
    """Compute the mean of a numeric node attribute across all graph nodes.

    Constitution III: pure read over already-persisted graph state.
    """
    nodes_fn = getattr(graph, "nodes", None)
    if nodes_fn is None:
        return default
    try:
        total = 0.0
        count = 0
        for _node_id, data in nodes_fn(data=True):
            val = data.get(attr) if isinstance(data, dict) else None
            if val is not None:
                try:
                    total += float(val)
                    count += 1
                except (TypeError, ValueError):
                    continue
        return total / count if count > 0 else default
    except Exception:  # noqa: BLE001 — diagnostic; never blocks the request
        return default


def _count_edges_by_mode(graph: Any, modes: frozenset[str]) -> int:
    """Count graph edges whose ``mode`` matches the given set (case-insensitive)."""
    edges_fn = getattr(graph, "edges", None)
    if edges_fn is None:
        return 0
    try:
        modes_lower = {m.lower() for m in modes}
        iterable: Any = edges_fn(data=True) if callable(edges_fn) else []
        count = 0
        for entry in iterable:
            data = entry[2] if isinstance(entry, (tuple, list)) and len(entry) >= 3 else None
            if isinstance(data, dict):
                mode = str(data.get("mode", "")).lower()
                if mode in modes_lower:
                    count += 1
        return count
    except Exception:  # noqa: BLE001 — diagnostic; never blocks the request
        return 0


def _detect_terminal_outcome(graph_attrs: dict[str, Any]) -> str | None:
    """Scan a graph's ``events`` list for a terminal GameOutcome event."""
    events = graph_attrs.get("events", []) or []
    for event in events:
        event_type = _extract_event_type(event)
        if event_type.upper() in _TERMINAL_OUTCOMES:
            return event_type.lower()
    return None


def _objective_status(category: str, outcome: str | None) -> str:
    """Derive an objective's status from the terminal outcome.

    - The objective whose category matches the fired outcome is ``complete``.
    - All other endgame-aligned objectives are ``failed`` (their path lost).
    - When no outcome has fired, every objective is ``active``.
    """
    if outcome is None:
        return "active"
    outcome_upper = outcome.upper()
    if category == "revolution" and outcome_upper == "REVOLUTIONARY_VICTORY":
        return "complete"
    if category == "collapse" and outcome_upper == "ECOLOGICAL_COLLAPSE":
        return "complete"
    if category == "fascist" and outcome_upper == "FASCIST_CONSOLIDATION":
        return "complete"
    if category == "red_ogv" and outcome_upper == "RED_OGV":
        return "complete"
    if category == "fragmented" and outcome_upper == "FRAGMENTED_COLLAPSE":
        return "complete"
    return "failed"


# ---------------------------------------------------------------------- #
# Spec 093: real graph reads shared by get_economy, the balkanization
# map-snapshot block, and the de-fixtured verb-target methods.
# ---------------------------------------------------------------------- #

# Edge modes counted as extraction/rent for get_economy (matches EdgeMode's
# EXTRACTIVE/ANTAGONISTIC values, compared case-insensitively since graph
# edges may carry either the enum's lowercase value or an uppercase legacy
# literal depending on which System wrote them).
_EXTRACTIVE_EDGE_MODES: frozenset[str] = frozenset({"extractive", "antagonistic"})

# Contested-territory threshold, ported verbatim from the design canon's
# documented values (design/mockups/themap/map-data.jsx: `(dominant_share -
# second_share) < 0.12 || dominant_share < 0.45`) — not a new invented
# constant.
_CONTESTED_INFLUENCE_DELTA: float = 0.12
_CONTESTED_DOMINANCE_FLOOR: float = 0.45


def _nodes_in_territory(graph: BabylonGraph, territory_id: str) -> list[tuple[str, dict[str, Any]]]:
    """Return (node_id, data) for every social_class/organization node whose
    ``territory_ids`` includes ``territory_id``."""
    found: list[tuple[str, dict[str, Any]]] = []
    for node_id, data in graph.nodes(data=True):
        if data.get("_node_type") not in ("social_class", "organization"):
            continue
        if territory_id in data.get("territory_ids", []):
            found.append((node_id, data))
    return found


def _build_balkanization_block(graph: BabylonGraph) -> dict[str, Any]:
    """Build the spec-093 ``balkanization`` map-snapshot block from real
    spec-070 graph data (faction/sovereign nodes, INFLUENCES/CLAIMS edges).

    Reads the RAW graph directly (never via ``WorldState.from_graph()``,
    which reconstructs unrecognized ``_node_type`` values — ``faction``,
    ``sovereign``, ``community`` — as a strict ``SocialClass(extra=
    "forbid")`` and crashes on their real attributes; a pre-existing
    engine-layer gap outside this spec's ``web/**`` ownership). Habitability
    and contested-state have no stored field on Territory — both are
    derived at read time here rather than invented as new engine state.
    """
    factions: list[dict[str, Any]] = []
    sovereigns: list[dict[str, Any]] = []
    territory_ids: set[str] = set()

    for node_id, data in graph.nodes(data=True):
        node_type = data.get("_node_type")
        if node_type == "faction":
            factions.append(
                {
                    "id": node_id,
                    "colonial_stance": data.get("colonial_stance"),
                    "is_settler_formation": bool(data.get("is_settler_formation", False)),
                }
            )
        elif node_type == "sovereign":
            claimed = [tid for tid, _level, _status in graph.query_sovereign_claims(node_id)]
            sovereigns.append(
                {
                    "id": node_id,
                    "ruling_faction_id": data.get("ruling_faction_id"),
                    "extraction_policy": data.get("extraction_policy"),
                    "legitimacy": float(data.get("legitimacy", 0.0)),
                    "claimed_territory_ids": claimed,
                }
            )
        elif node_type == "territory":
            territory_ids.add(node_id)

    territory_influence: list[dict[str, Any]] = []
    for tid in sorted(territory_ids):
        rows = graph.query_faction_influence_by_territory(tid)
        if not rows:
            continue
        influences = [
            {"faction_id": fid, "influence_level": level, "support_type": support}
            for fid, level, support in rows
        ]
        top_share = rows[0][1]
        second_share = rows[1][1] if len(rows) > 1 else 0.0
        contested = (top_share - second_share) < _CONTESTED_INFLUENCE_DELTA or (
            top_share < _CONTESTED_DOMINANCE_FLOOR
        )
        claim_rows = graph.query_territory_claims(tid)
        current_sovereign_id = claim_rows[0][0] if claim_rows else None
        terr_data = graph.nodes[tid]
        biocapacity = float(terr_data.get("biocapacity", 0.0))
        max_biocapacity = float(terr_data.get("max_biocapacity", 0.0)) or 1.0
        habitability = max(0.0, min(1.0, biocapacity / max_biocapacity))

        territory_influence.append(
            {
                "territory_id": tid,
                "influences": influences,
                "dominant_faction_id": rows[0][0],
                "current_sovereign_id": current_sovereign_id,
                "contested": contested,
                "habitability": round(habitability, 4),
            }
        )

    return {
        "factions": factions,
        "sovereigns": sovereigns,
        "territory_influence": territory_influence,
    }


def _outgoing_extractive_edges(graph: BabylonGraph, source_id: str) -> list[dict[str, Any]]:
    """Return real EXTRACTIVE/ANTAGONISTIC edges outgoing from ``source_id``."""
    found: list[dict[str, Any]] = []
    for source, target in graph.edges:
        if source != source_id:
            continue
        data = graph.edges[(source, target)]
        mode = str(data.get("edge_mode", data.get("edge_type", data.get("_edge_type", "")))).lower()
        if mode not in _EXTRACTIVE_EDGE_MODES:
            continue
        found.append(
            {
                "edge_id": f"{source}->{target}",
                "target_name": graph.nodes.get(target, {}).get("name", target),
                "flow_type": mode.upper(),
                "s_flow_per_tick": float(data.get("value_flow", 0.0)),
            }
        )
    return found


def _edge_status_between(graph: BabylonGraph, node_a: str, node_b: str) -> dict[str, Any]:
    """Return a real edge-mode summary between two nodes (either direction),
    or an honest ``"NONE"`` status when no edge exists."""
    for source, target in ((node_a, node_b), (node_b, node_a)):
        if (source, target) in graph.edges:
            data = graph.edges[(source, target)]
            mode = str(
                data.get("edge_mode", data.get("edge_type", data.get("_edge_type", "none")))
            ).upper()
            return {
                "type": mode,
                "value_flow": float(data.get("value_flow", 0.0)),
                "tension": float(data.get("tension", 0.0)),
            }
    return {"type": "NONE", "value_flow": 0.0, "tension": 0.0}


def _empty_economy_payload(territory_id: str | None) -> dict[str, Any]:
    return {
        "territory_id": territory_id,
        "has_data": False,
        "value_produced": 0.0,
        "wage_share": None,
        "rent_extracted": 0.0,
        "exploitation_rate": None,
        "extraction_intensity": 0.0,
    }


class EngineBridge:
    """Translates between Django request/response and simulation engine.

    Holds a reference to the persistence layer and provides methods
    that orchestrate create → hydrate → step → persist → snapshot cycles.
    """

    def __init__(
        self, persistence: RuntimePersistence, narrator: NarratorProvider | None = None
    ) -> None:
        self._persistence = persistence
        if narrator is None:
            from game.narrator import DeterministicNarrator

            narrator = DeterministicNarrator()
        self._narrator = narrator
        logger.info("EngineBridge initialized with %s", type(persistence).__name__)

    # ------------------------------------------------------------------ #
    # Game lifecycle
    # ------------------------------------------------------------------ #

    def create_game(
        self,
        scenario: str,
        config: dict[str, Any] | None = None,
        defines: dict[str, Any] | None = None,
        rng_seed: int = 0,
        player_id: int | None = None,
    ) -> UUID:
        """Create a new game session and persist the initial state.

        Args:
            scenario: Scenario identifier string.
            config: Optional dict of SimulationConfig overrides.
            defines: Optional dict of GameDefines overrides.
            rng_seed: RNG seed for reproducibility.
            player_id: Django auth user ID, if authenticated.

        Returns:
            The UUID of the newly created session.

        Raises:
            ValueError: If ``scenario`` is not a registered scenario or alias.
        """
        # Fail loud on unknown scenarios BEFORE creating the session row, so a
        # typo cannot leave an orphaned session silently seeded as 'us'.
        resolve_scenario(scenario)

        # Validate configs via Pydantic (raises on bad input)
        sim_config = SimulationConfig(**(config or {}))
        game_defines = GameDefines(**(defines or {}))

        # Delegate to persistence layer (PostgresRuntime.create_session)
        session_id: UUID = self._persistence.create_session(  # type: ignore[attr-defined]
            scenario=scenario,
            config_json=sim_config.model_dump(),
            game_defines_json=game_defines.model_dump(),
            rng_seed=rng_seed,
            player_id=player_id,
        )

        # Seed initial world graph for tick 0 so snapshot/state endpoints
        # have material data immediately after game creation.
        initial_state = _build_initial_state_for_scenario(scenario)
        self._persistence.persist_tick(
            tick=initial_state.tick,
            graph=initial_state.to_graph(),
            events=[event.model_dump(mode="json") for event in initial_state.events] or None,
            session_id=session_id,
        )

        # P0 #7: project the tick-0 territories into hex_latest so the map
        # endpoint has features immediately after game creation.
        _persist_hex_state_safe(
            session_id,
            initial_state.tick,
            [_serialize_territory(t) for t in initial_state.territories.values()],
        )
        # Spec-109 A1: seed the tick-0 snapshot tables + summary row so
        # timeseries/history surfaces have a baseline point from creation.
        _persist_snapshots_safe(self._persistence, session_id, initial_state)

        logger.info("Created game session=%s scenario=%s seed=%d", session_id, scenario, rng_seed)
        return session_id

    # ------------------------------------------------------------------ #
    # State access
    # ------------------------------------------------------------------ #

    def hydrate_state(
        self, session_id: UUID, tick: int | None = None
    ) -> tuple[WorldState, BabylonGraph]:
        """Load a session's graph from persistence and reconstruct WorldState.

        Args:
            session_id: The game session UUID.
            tick: Specific tick to load, or ``None`` for latest.

        Returns:
            Tuple of (WorldState, BabylonGraph) at the requested tick.

        Raises:
            ValueError: If an unseeded legacy session row stores a scenario
                name that is not a registered scenario or alias (fail loud
                on corrupt data instead of silently reseeding as ``us``).
        """
        graph = self._persistence.hydrate_graph(tick=tick, session_id=session_id)

        # Backward-compatible bootstrap: if a legacy/new session has no persisted
        # tick-0 graph yet, seed it from the stored scenario and retry hydrate.
        if tick is None and _is_unseeded_graph(graph):
            session_getter = getattr(self._persistence, "get_session", None)
            if callable(session_getter):
                session_row = session_getter(session_id)
                scenario = (
                    str(session_row.get("scenario", "default"))
                    if isinstance(session_row, dict)
                    else "default"
                )
                seeded_state = _build_initial_state_for_scenario(scenario)
                self._persistence.persist_tick(
                    tick=seeded_state.tick,
                    graph=seeded_state.to_graph(),
                    events=[event.model_dump(mode="json") for event in seeded_state.events] or None,
                    session_id=session_id,
                )
                # P0 #7: backfill hex_latest for legacy/unseeded sessions so
                # pre-fix games gain a map on first hydrate.
                _persist_hex_state_safe(
                    session_id,
                    seeded_state.tick,
                    [_serialize_territory(t) for t in seeded_state.territories.values()],
                )
                # Spec-109 A1: same backfill for the snapshot/summary tables.
                _persist_snapshots_safe(self._persistence, session_id, seeded_state)
                graph = self._persistence.hydrate_graph(tick=tick, session_id=session_id)

        # Determine the tick from the graph metadata
        resolved_tick = tick if tick is not None else _graph_tick(graph)
        world_state = WorldState.from_graph(graph, tick=resolved_tick)
        return world_state, graph

    def get_snapshot(self, session_id: UUID) -> dict[str, Any]:
        """Return a JSON-serializable snapshot of the current game state.

        Args:
            session_id: The game session UUID.

        Returns:
            Dict with keys: session_id, tick, entities, territories,
            organizations, institutions, economy, events.
        """
        state, _graph = self.hydrate_state(session_id)
        return _state_to_snapshot(state, session_id)

    def get_map_snapshot(
        self,
        session_id: UUID,
        tick: int | None = None,
        _layer: str | None = None,
        zoom: str = "county",
    ) -> dict[str, Any]:
        """Return a GeoJSON FeatureCollection of hex states for a given tick.

        Args:
            session_id: The game session UUID.
            tick: The tick to query data for. If None, uses current tick.
            layer: Optional layer filter (unused here, filtering done in API).
            zoom: Spatial aggregation level (state/bea/msa/county/hex).

        Returns:
            GeoJSON dict matching the HexMap frontend contract.
        """
        import h3

        from game.models import GameSession, HexState

        try:
            session = GameSession.objects.get(id=session_id)
        except GameSession.DoesNotExist:
            return {"type": "FeatureCollection", "metadata": {}, "features": []}

        target_tick = tick if tick is not None else session.current_tick

        hex_states = HexState.objects.filter(game=session, tick=target_tick)

        if zoom == "hex":
            # Full hex-level detail — no aggregation
            features = []
            for state in hex_states:
                boundary = h3.cell_to_boundary(state.h3_index)
                coordinates = [[lng, lat] for lat, lng in boundary]
                coordinates.append(coordinates[0])

                feature = {
                    "type": "Feature",
                    "id": state.h3_index,
                    "geometry": {"type": "Polygon", "coordinates": [coordinates]},
                    "properties": _hex_feature_properties(state),
                }
                features.append(feature)
        else:
            # Aggregated zoom level — group by dimension column
            features = self._aggregate_hex_features(hex_states, zoom)

        metadata: dict[str, Any] = {
            "tick": target_tick,
            "scenario": session.scenario,
            "h3_resolution": 7,
            "zoom": zoom,
            "available_metrics": list(MAP_METRIC_PROPERTIES),
        }

        # Spec 093 US3: balkanization block for the map lens set. Reads the
        # raw graph directly (see _build_balkanization_block docstring for
        # why WorldState.from_graph() must be avoided here). Best-effort —
        # a hydration failure must not break the rest of the map snapshot.
        try:
            graph = self._persistence.hydrate_graph(tick=target_tick, session_id=session_id)
            metadata["balkanization"] = _build_balkanization_block(graph)
        except Exception:  # noqa: BLE001 — optional block, never fails the map
            logger.exception("Failed to build balkanization block for session %s", session_id)

        return {
            "type": "FeatureCollection",
            "metadata": metadata,
            "features": features,
        }

    @staticmethod
    def _aggregate_hex_features(
        hex_states: Any,
        zoom: str,
    ) -> list[dict[str, Any]]:
        """Aggregate hex-level data to a higher zoom tier.

        Groups hex states by the dimension column matching the zoom level,
        then computes weighted averages (by population) for numeric metrics
        and sums for additive metrics.
        """
        from collections import defaultdict

        # Map zoom level to the grouping key
        group_key_map = {
            "state": "state_fips",
            "bea": "bea_ea_code",
            "msa": "msa_code",
            "county": "county_fips",
        }
        group_attr = group_key_map.get(zoom, "county_fips")

        # Accumulators: group_value → {metric sums}
        groups: dict[str, dict[str, float]] = defaultdict(
            lambda: {
                "profit_rate_sum": 0.0,
                "exploitation_rate_sum": 0.0,
                "occ_sum": 0.0,
                "imperial_rent_sum": 0.0,
                "heat_sum": 0.0,
                "org_presence_sum": 0,
                "population_sum": 0,
                "count": 0,
            }
        )
        group_names: dict[str, str] = {}

        for state in hex_states:
            key = getattr(state, group_attr, None)
            if key is None:
                key = "unknown"
            acc = groups[key]
            pop = state.pop_total or 0
            acc["profit_rate_sum"] += (state.profit_rate or 0) * pop
            acc["exploitation_rate_sum"] += (state.exploitation_rate or 0) * pop
            acc["occ_sum"] += (state.occ or 0) * pop
            acc["imperial_rent_sum"] += state.imperial_rent or 0
            acc["heat_sum"] += (state.heat or 0) * pop
            acc["org_presence_sum"] += state.org_count or 0
            acc["population_sum"] += pop
            acc["count"] += 1

            # Capture a name for the group
            if key not in group_names:
                group_names[key] = state.county_name or key

        features: list[dict[str, Any]] = []
        for key, acc in groups.items():
            total_pop = acc["population_sum"] or 1  # avoid div-by-zero
            features.append(
                {
                    "type": "Feature",
                    "id": key,
                    "geometry": None,  # Geometry deferred — frontend uses reference polygons
                    "properties": {
                        "group_key": key,
                        "group_name": group_names.get(key, key),
                        "zoom": zoom,
                        "hex_count": acc["count"],
                        "profit_rate": round(acc["profit_rate_sum"] / total_pop, 6),
                        "exploitation_rate": round(acc["exploitation_rate_sum"] / total_pop, 4),
                        "occ": round(acc["occ_sum"] / total_pop, 4),
                        "imperial_rent": round(acc["imperial_rent_sum"], 2),
                        "heat": round(acc["heat_sum"] / total_pop, 4),
                        "org_presence": acc["org_presence_sum"],
                        "population": acc["population_sum"],
                    },
                }
            )

        return features

    # ------------------------------------------------------------------ #
    # Domain Dashboards (Scaffolding for full UI requirements)
    # ------------------------------------------------------------------ #

    def get_game_summary(self, _session_id: UUID) -> dict[str, Any]:
        """Return the top-bar summary data: tick, profit rate, phi, state faction, alerts."""
        return {}

    def get_game_timeseries(self, session_id: UUID) -> dict[str, Any]:
        """Return historical timeseries data for charting (spec 061 US3, FR-026).

        Reads the per-tick aggregates from the ``tick_summary`` table and
        emits the six named arrays the v2 Briefing/Analysis pages chart:
        ``imperial_rent``, ``consciousness``, ``solidarity``, ``heat``,
        ``wealth``, ``biocapacity``. Each array is parallel-indexed with
        the ``ticks`` array (oldest tick first). Missing values become
        ``None`` so the frontend can interpolate / hide gaps without a
        backend round-trip.

        The persistence layer fronts this via
        :meth:`PostgresRuntime.query_tick_summary_series`. SQLite-backed
        ``RuntimeDatabase`` returns an empty list (the v2 pages are only
        ever consumed against a live Postgres deployment).
        """
        rows: list[dict[str, Any]] = []
        query = getattr(self._persistence, "query_tick_summary_series", None)
        if callable(query):
            try:
                rows = query(session_id)
            except Exception:  # noqa: BLE001 — diagnostic; never blocks request
                logger.exception("get_game_timeseries: query_tick_summary_series failed")
                rows = []

        ticks: list[int] = []
        imperial_rent: list[float | None] = []
        consciousness: list[float | None] = []
        solidarity: list[float | None] = []
        heat: list[float | None] = []
        wealth: list[float | None] = []
        biocapacity: list[float | None] = []
        for row in rows:
            ticks.append(int(row.get("tick", 0)))
            imperial_rent.append(_optional_float(row.get("imperial_rent")))
            consciousness.append(_optional_float(row.get("avg_consciousness")))
            # No dedicated columns yet — these fields fall back gracefully.
            solidarity.append(_optional_float(row.get("solidarity_edge_count")))
            heat.append(_optional_float(row.get("total_heat")))
            wealth.append(_optional_float(row.get("total_wealth")))
            biocapacity.append(_optional_float(row.get("total_biocapacity")))
        return {
            "ticks": ticks,
            "imperial_rent": imperial_rent,
            "consciousness": consciousness,
            "solidarity": solidarity,
            "heat": heat,
            "wealth": wealth,
            "biocapacity": biocapacity,
        }

    def get_economy_dashboard(self, _session_id: UUID) -> dict[str, Any]:
        """Return the economy left-panel dashboard data."""
        return {}

    def get_economy(self, session_id: UUID, territory_id: str | None = None) -> dict[str, Any]:
        """Return a per-territory economic summary (spec 093 US5).

        Aggregates real ``wealth``/``extraction_intensity`` from
        social_class/organization nodes located in ``territory_id`` and
        real ``value_flow`` from incident EXTRACTIVE/ANTAGONISTIC edges.
        Returns ``has_data: False`` with honest zeros when the territory
        has no such nodes/edges yet — never a fabricated nonzero value.

        Without ``territory_id``, delegates to the (still-stub)
        dashboard-wide :meth:`get_economy_dashboard` for backward
        compatibility with the existing ``/economy/`` route.
        """
        if territory_id is None:
            return self.get_economy_dashboard(session_id)

        _state, graph = self.hydrate_state(session_id)
        if territory_id not in graph.nodes:
            return _empty_economy_payload(territory_id)

        econ_nodes = _nodes_in_territory(graph, territory_id)
        node_ids = {node_id for node_id, _ in econ_nodes}
        value_produced = sum(float(data.get("wealth", 0.0)) for _, data in econ_nodes)
        terr_data = graph.nodes.get(territory_id, {})
        terr_extraction_intensity = terr_data.get("extraction_intensity")
        extraction_values = (
            [float(terr_extraction_intensity)] if terr_extraction_intensity is not None else []
        )

        rent_extracted = 0.0
        tension_values: list[float] = []
        for source, target in graph.edges:
            # Both endpoints must be local to this territory — an org
            # operating across multiple territories shouldn't bleed one
            # territory's edge activity into another's summary.
            if source not in node_ids or target not in node_ids:
                continue
            edge_data = graph.edges[(source, target)]
            mode = str(
                edge_data.get(
                    "edge_mode", edge_data.get("edge_type", edge_data.get("_edge_type", ""))
                )
            ).lower()
            if mode not in _EXTRACTIVE_EDGE_MODES:
                continue
            rent_extracted += float(edge_data.get("value_flow", 0.0))
            tension = edge_data.get("tension")
            if tension is not None:
                tension_values.append(float(tension))

        has_data = value_produced > 0.0 or rent_extracted > 0.0 or bool(extraction_values)
        exploitation_rate: float | None = None
        if has_data and value_produced > 0.0:
            # Real, locally-derivable exchange-ratio proxy: how much extra
            # value was extracted relative to what this territory produced
            # (epsilon > 1 == giving away more than receiving, matching
            # unequal_exchange's semantics), fed through the existing
            # calculate_unequal_exchange_rate formula rather than a new one.
            exchange_ratio = (value_produced + rent_extracted) / value_produced
            exploitation_rate = round(calculate_unequal_exchange_rate(exchange_ratio) / 100.0, 4)

        return {
            "territory_id": territory_id,
            "has_data": has_data,
            "value_produced": round(value_produced, 4),
            "wage_share": None,
            "rent_extracted": round(rent_extracted, 4),
            "exploitation_rate": exploitation_rate,
            "extraction_intensity": (
                round(sum(extraction_values) / len(extraction_values), 4)
                if extraction_values
                else 0.0
            ),
        }

    def get_communities_dashboard(self, _session_id: UUID) -> dict[str, Any]:
        """Return communities dashboard (spec 061 US6 T089, FR-018).

        Returns ``{"communities": [...]}`` where each entry has the
        canonical shape from ``contracts/communities.yaml``. The engine
        Community model is not yet wired through the bridge; until that
        lands (US6 follow-up), this method emits an empty list — the
        frontend can render a "no communities surfaced" empty state.
        """
        return {"communities": []}

    # ------------------------------------------------------------------ #
    # Spec 061 US6 T091: inspector endpoints (FR-019)
    #
    # Each inspector returns a populated detail object matching
    # contracts/inspectors.yaml. The current implementations look up the
    # entity in the existing snapshot helpers and wrap the result in the
    # standard envelope. Recent-activity / history tails (which require
    # query_org_recent_actions, query_edge_history per T092/T093) are
    # left as empty lists until the deeper persistence wiring lands.
    # ------------------------------------------------------------------ #

    def inspect_node(self, session_id: UUID, node_id: str) -> dict[str, Any]:
        """Generic node lookup — dispatches by node type (FR-019)."""
        state, _ = self.hydrate_state(session_id)
        snap = _state_to_snapshot(state, session_id)
        for collection in ("organizations", "institutions", "territories"):
            for entry in snap.get(collection, []):
                if entry.get("id") == node_id:
                    return {"node": entry, "collection": collection}
        return {"node": None, "collection": None}

    def inspect_org(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        state, _ = self.hydrate_state(session_id)
        snap = _state_to_snapshot(state, session_id)
        org = next((o for o in snap.get("organizations", []) if o.get("id") == org_id), None)
        return {
            "org": org,
            "recent_actions": [],  # T092: populated when query_org_recent_actions lands
        }

    def inspect_community(self, _session_id: UUID, _community_id: str) -> dict[str, Any]:
        return {"community": None, "members": []}

    def inspect_edge(
        self, session_id: UUID, source_id: str, target_id: str, edge_type: str
    ) -> dict[str, Any]:
        state, _ = self.hydrate_state(session_id)
        snap = _state_to_snapshot(state, session_id)
        edge = next(
            (
                e
                for e in snap.get("edges", [])
                if e.get("source_id") == source_id
                and e.get("target_id") == target_id
                and e.get("mode") == edge_type
            ),
            None,
        )
        return {
            "edge": edge,
            "history": [],  # T093: populated when query_edge_history lands
        }

    def inspect_hex(self, session_id: UUID, h3_index: str) -> dict[str, Any]:
        state, _ = self.hydrate_state(session_id)
        snap = _state_to_snapshot(state, session_id)
        territory = next(
            (t for t in snap.get("territories", []) if t.get("h3_index") == h3_index),
            None,
        )
        return {"hex": territory}

    def get_organizations_dashboard(
        self, session_id: UUID, player_only: bool = False
    ) -> dict[str, Any]:
        """Return the organizations left-panel dashboard data."""
        state, _ = self.hydrate_state(session_id)
        snap = _state_to_snapshot(state, session_id)
        orgs = snap.get("organizations", [])
        if player_only:
            orgs = [o for o in orgs if o.get("vanguard") is not None]
        return {"organizations": orgs}

    def get_edges_dashboard(self, _session_id: UUID) -> dict[str, Any]:
        """Return the edges/relations left-panel dashboard data."""
        return {}

    def get_state_apparatus_dashboard(self, _session_id: UUID) -> dict[str, Any]:
        """Return the state-apparatus intelligence screen data."""
        return {}

    def get_journal_dashboard(self, session_id: UUID) -> dict[str, Any]:
        """Return the historical event log data (spec 092 — Event Log page).

        Sources ``tick_event`` rows written by :func:`_persist_tick_events_safe`
        during :meth:`resolve_tick`, via the persistence layer's optional
        ``query_session_events(session_id, limit=...)`` capability. Ordered
        newest-tick-first, capped at :data:`_JOURNAL_LIMIT` rows.

        SQLite-backed ``RuntimeDatabase`` (dev/test) has no
        ``query_session_events`` method and degrades to an empty list —
        the same optional-capability pattern as :meth:`get_game_timeseries`.

        Args:
            session_id: The game session UUID.

        Returns:
            ``{"events": [GameEvent, ...]}`` in the same shape as
            ``snapshot.events`` (id/type/tick/severity/title/body/data).
        """
        rows: list[dict[str, Any]] = []
        query = getattr(self._persistence, "query_session_events", None)
        if callable(query):
            try:
                rows = query(session_id, limit=_JOURNAL_LIMIT)
            except Exception:  # noqa: BLE001 — diagnostic; never blocks request
                logger.exception("get_journal_dashboard: query_session_events failed")
                rows = []
        return {"events": [_game_event_from_tick_event_row(row) for row in rows]}

    def get_alerts_dashboard(self, session_id: UUID) -> dict[str, Any]:
        """Return active alerts — critical/warning events from the latest tick.

        Sources the same ``tick_event`` rows as the journal but scoped to
        the most recently resolved tick and filtered to non-informational
        severities: the "threshold crossings" the Tick Resolution screen
        surfaces immediately after :meth:`resolve_tick` (spec 092).

        Args:
            session_id: The game session UUID.

        Returns:
            ``{"alerts": [GameEvent, ...]}`` in the same shape as
            ``snapshot.events``, filtered to critical/warning severity.
        """
        state, _graph = self.hydrate_state(session_id)
        rows: list[dict[str, Any]] = []
        query = getattr(self._persistence, "query_tick_events", None)
        if callable(query):
            try:
                rows = query(session_id, state.tick)
            except Exception:  # noqa: BLE001 — diagnostic; never blocks request
                logger.exception("get_alerts_dashboard: query_tick_events failed")
                rows = []
        alerts = [
            _game_event_from_tick_event_row(row)
            for row in rows
            if row.get("severity") in _ALERT_SEVERITIES
        ]
        return {"alerts": alerts}

    def get_wire_feed(self, session_id: UUID) -> dict[str, Any]:
        """Return the Wire feed (spec 094) — a WireFeed dict produced by the
        DeterministicNarrator over the session's journal events.

        Sources the same ``tick_event`` rows as :meth:`get_journal_dashboard`,
        builds presentation metadata from the session, and passes both through
        a :class:`~game.narrator.DeterministicNarrator` (pure function, no
        engine state writes — Constitution III). The narrator is deterministic:
        same events produce byte-identical output (R-NARR).

        Args:
            session_id: The game session UUID.

        Returns:
            WireFeed dict matching ``specs/094-the-wire/contracts/wire.yaml``.
        """

        journal = self.get_journal_dashboard(session_id)
        events = journal.get("events", [])

        # Build meta from session + events
        state, _graph = self.hydrate_state(session_id)
        tick = state.tick
        meta = {
            "tick": tick,
            "session": str(session_id),
            "operator": "RASKOVA-2",
            "freq": "88.7 MHz",
            "qth": "WAYNE CO / GRID EN82",
            "classification": "TS//SI//NOFORN",
            "cable_id": f"{tick:04d}-A",
            "page_of": "001/001",
            "timestamp_utc": "2026-05-12T08:47:22Z",
        }

        return self._narrator.narrate(events, meta)

    # ------------------------------------------------------------------ #
    # Spec 095: Endgame Chronicle + Journal + Dialectic screen
    # ------------------------------------------------------------------ #

    def get_contradiction_snapshot(self, session_id: UUID) -> dict[str, Any]:
        """Return the live contradiction snapshot — the Dialectic screen feed.

        Spec 095 FR-095-01. Reads ``contradiction_field`` rows (the
        OppositionRegistry's per-tick gap + rate) via the persistence pool's
        SQL (same pattern as :func:`_fetch_session_rng_seed_from_pool`), and
        graph attributes (``contradiction_frames``, ``dialectical_regime``)
        via :meth:`hydrate_graph`. Constitution III: pure read — never
        computes dialectical state.

        Args:
            session_id: The game session UUID.

        Returns:
            ``ContradictionSnapshot`` dict matching
            ``specs/095-endgame-chronicle/contracts/contradiction.yaml``.
        """
        graph = self._persistence.hydrate_graph(tick=None, session_id=session_id)
        graph_attrs: dict[str, Any] = getattr(graph, "graph", {}) or {}
        tick = int(graph_attrs.get("tick", 0))
        regime = str(graph_attrs.get("dialectical_regime", "reproduction") or "reproduction")

        frames_raw = graph_attrs.get("contradiction_frames", {}) or {}
        global_frame = frames_raw.get("global", {}) if isinstance(frames_raw, dict) else {}
        principal_aspect = (
            global_frame.get("principal", {}) if isinstance(global_frame, dict) else {}
        )
        principal_key = (
            str(principal_aspect.get("id", "")) if isinstance(principal_aspect, dict) else ""
        )

        rows = _fetch_contradiction_field_rows(
            getattr(self._persistence, "_pool", None), session_id
        )

        oppositions: list[dict[str, Any]] = []
        for row in rows:
            key = str(row.get("field_name", ""))
            gap = float(row.get("value", 0.0))
            rate = float(row.get("dt") or 0.0)
            is_principal = bool(key and key == principal_key) if principal_key else False
            leading_pole = ""
            if isinstance(principal_aspect, dict) and key == principal_key:
                leading_pole = str(principal_aspect.get("principal_aspect", ""))
            oppositions.append(
                {
                    "key": key,
                    "gap": gap,
                    "rate": rate,
                    "is_principal": is_principal,
                    "leading_pole": leading_pole,
                }
            )

        if not oppositions and isinstance(principal_aspect, dict) and principal_aspect:
            oppositions.append(
                {
                    "key": principal_key,
                    "gap": float(principal_aspect.get("intensity", 0.0)),
                    "rate": float(principal_aspect.get("aspect_balance", 0.0)),
                    "is_principal": True,
                    "leading_pole": str(principal_aspect.get("principal_aspect", "")),
                }
            )

        for opp in oppositions:
            opp["is_principal"] = (
                bool(opp.get("key") and opp["key"] == principal_key)
                if principal_key
                else opp.get("is_principal", False)
            )

        frame_block = {
            "principal": _aspect_to_frame_entry(global_frame.get("principal", {}))
            if isinstance(global_frame, dict)
            else {},
            "secondary": _aspect_to_frame_entry(global_frame.get("secondary", {}))
            if isinstance(global_frame, dict)
            else {},
        }

        return {
            "tick": tick,
            "regime": regime,
            "oppositions": oppositions,
            "principal_key": principal_key,
            "frame": frame_block,
        }

    def get_endgame_state(self, session_id: UUID) -> dict[str, Any]:
        """Return the terminal outcome + chronicle stat cards.

        Spec 095 FR-095-02. Reads the latest snapshot's endgame block. All 5
        GameOutcome terminal types are recognized (FR-095-02 fix). Returns
        ``outcome: None`` when the game is still in progress.

        Args:
            session_id: The game session UUID.

        Returns:
            ``EndgameState`` dict matching
            ``specs/095-endgame-chronicle/contracts/endgame.yaml``.
        """
        graph = self._persistence.hydrate_graph(tick=None, session_id=session_id)
        graph_attrs: dict[str, Any] = getattr(graph, "graph", {}) or {}
        tick = int(graph_attrs.get("tick", 0))

        outcome: str | None = None
        summary = ""
        events_raw = graph_attrs.get("events", []) or []
        for event in events_raw:
            event_type = _extract_event_type(event)
            if event_type.upper() in _TERMINAL_OUTCOMES:
                outcome = event_type.lower()
                summary = str(_extract_event_data(event, "summary", ""))
                break

        headline = _OUTCOME_HEADLINES.get((outcome or "").upper(), "") if outcome else ""

        consciousness_avg = _compute_avg_node_attr(graph, "class_consciousness", 0.0)
        heat_avg = _compute_avg_node_attr(graph, "heat", 0.0)
        solidarity_edges = _count_edges_by_mode(graph, frozenset({"solidarity"}))

        return {
            "tick": tick,
            "outcome": outcome,
            "headline": headline,
            "summary": summary,
            "stats": {
                "final_tick": tick,
                "consciousness": consciousness_avg,
                "solidarity_edges": solidarity_edges,
                "heat": heat_avg,
            },
        }

    def get_journal_objectives(self, session_id: UUID) -> dict[str, Any]:
        """Return Vic3-style objectives derived from the current game state.

        Spec 095 FR-095-03. Each objective maps to one of the 5 endgame
        conditions, with a progress bar (0–1) and status
        (active/complete/failed). Progress is derived from material state
        (class consciousness, contradiction gap, regime) — never invented.

        Args:
            session_id: The game session UUID.

        Returns:
            ``ObjectivesTracker`` dict matching
            ``specs/095-endgame-chronicle/contracts/objectives.yaml``.
        """
        graph = self._persistence.hydrate_graph(tick=None, session_id=session_id)
        graph_attrs: dict[str, Any] = getattr(graph, "graph", {}) or {}
        tick = int(graph_attrs.get("tick", 0))
        regime = str(graph_attrs.get("dialectical_regime", "reproduction") or "reproduction")

        consciousness_avg = _compute_avg_node_attr(graph, "class_consciousness", 0.0)
        heat_avg = _compute_avg_node_attr(graph, "heat", 0.0)

        frames_raw = graph_attrs.get("contradiction_frames", {}) or {}
        global_frame = frames_raw.get("global", {}) if isinstance(frames_raw, dict) else {}
        principal_aspect = (
            global_frame.get("principal", {}) if isinstance(global_frame, dict) else {}
        )
        principal_gap = (
            float(principal_aspect.get("intensity", 0.0))
            if isinstance(principal_aspect, dict)
            else 0.0
        )

        outcome = _detect_terminal_outcome(graph_attrs)

        objectives: list[dict[str, Any]] = [
            {
                "id": "revolution",
                "title": "Revolutionary Victory",
                "description": "Build mass class consciousness and solidarity edges to overthrow the empire.",
                "progress": min(1.0, consciousness_avg),
                "status": _objective_status("revolution", outcome),
                "category": "revolution",
            },
            {
                "id": "ecological_collapse",
                "title": "Ecological Collapse",
                "description": "Biocapacity depletion forces a terminal retreat from extraction.",
                "progress": min(1.0, heat_avg),
                "status": _objective_status("collapse", outcome),
                "category": "collapse",
            },
            {
                "id": "fascist_consolidation",
                "title": "Fascist Consolidation",
                "description": "False-consciousness bloc achieves a sovereign grip on the state.",
                "progress": min(1.0, principal_gap),
                "status": _objective_status("fascist", outcome),
                "category": "fascist",
            },
            {
                "id": "red_ogv",
                "title": "Red OGV Trap",
                "description": "Settler-socialist formation captures the movement without abolishing empire.",
                "progress": min(1.0, principal_gap * 0.5),
                "status": _objective_status("red_ogv", outcome),
                "category": "red_ogv",
            },
            {
                "id": "fragmented_collapse",
                "title": "Fragmented Collapse",
                "description": "Balkanization — sovereign fragmentation outpaces solidarity.",
                "progress": min(1.0, principal_gap * 0.7)
                if regime == "crisis"
                else min(1.0, heat_avg * 0.5),
                "status": _objective_status("fragmented", outcome),
                "category": "fragmented",
            },
        ]

        return {
            "tick": tick,
            "objectives": objectives,
        }

    # ------------------------------------------------------------------ #
    # Spec 103: Trade surfaces — Wire INDEX per-bloc lines, Territory
    # Detail import-exposure breakdown, Analysis trade panel.
    # ------------------------------------------------------------------ #

    def get_trade_flows(self, session_id: UUID) -> dict[str, Any]:
        """Return per-bloc price/flow lines for the Wire INDEX tab.

        Spec 103 FR-103-01. Reads ``boundary_flow_register`` rows (per-tick,
        grouped by source_node_id + flow_type) and
        ``dynamic_external_node_state`` rows (latest per node) via the
        persistence pool's SQL. Constitution III: pure read — never computes
        trade state.

        Degrades to ``has_data: False`` with an empty ``blocs`` list when the
        pool is unavailable or both tables are empty/absent.

        Args:
            session_id: The game session UUID.

        Returns:
            ``TradeFlowsPayload`` dict matching
            ``specs/103-trade-surfaces/contracts/trade-flows.yaml``.
        """
        pool = getattr(self._persistence, "_pool", None)
        graph = self._persistence.hydrate_graph(tick=None, session_id=session_id)
        graph_attrs: dict[str, Any] = getattr(graph, "graph", {}) or {}
        tick = int(graph_attrs.get("tick", 0))

        series_rows = _fetch_boundary_flow_series(pool, session_id)
        node_latest = _fetch_external_node_latest(pool, session_id)

        # Collect all node_ids from both sources (series may have nodes not in
        # latest, and vice versa).
        all_node_ids = sorted(set(node_latest.keys()) | {r["source_node_id"] for r in series_rows})
        if not all_node_ids:
            return {"tick": tick, "has_data": False, "blocs": []}

        blocs: list[dict[str, Any]] = []
        for nid in all_node_ids:
            latest = node_latest.get(
                nid,
                {
                    "kind": "international",
                    "phi_year_inflow": 0.0,
                    "bilateral_trade_value": 0.0,
                    "bilateral_trade_tons": 0.0,
                    "erdi_ratio": 1.0,
                    "tick": tick,
                },
            )
            phi_series = [
                {"tick": r["tick"], "magnitude": r["magnitude"]}
                for r in series_rows
                if r["source_node_id"] == nid and r["flow_type"] == "drain_edge"
            ]
            trade_series = [
                {"tick": r["tick"], "magnitude": r["magnitude"]}
                for r in series_rows
                if r["source_node_id"] == nid
                and r["flow_type"] in ("trade_inbound", "trade_outbound")
            ]
            blocs.append(
                {
                    "node_id": nid,
                    "label": _BLOC_LABELS.get(nid, nid.replace("_", " ").title()),
                    "kind": latest["kind"],
                    "latest": {
                        "phi_year_inflow": latest["phi_year_inflow"],
                        "bilateral_trade_value": latest["bilateral_trade_value"],
                        "bilateral_trade_tons": latest["bilateral_trade_tons"],
                        "erdi_ratio": latest["erdi_ratio"],
                    },
                    "phi_series": phi_series,
                    "trade_series": trade_series,
                }
            )

        return {"tick": tick, "has_data": True, "blocs": blocs}

    def get_county_import_exposure(self, session_id: UUID, county_fips: str) -> dict[str, Any]:
        """Return an import-exposure provenance breakdown for a county.

        Spec 103 FR-103-02. A BabylonScriptValue-style ``{value, breakdown}``
        over spec-100 ``county_exposure_by_external`` weights + live
        ``boundary_flow_register`` flows. The breakdown's per-bloc contributors
        each drill down to (a) the spec-100 weight (source: reference_table)
        and (b) the live DRAIN_EDGE/TRADE_EDGE flow (source: dynamic_table).
        The ``citations`` array carries the terminal reference-data
        provenance.

        Degrades to ``has_data: False`` with honest zeros when no data is
        available (spec-100 table absent + boundary_flow_register empty).

        Args:
            session_id: The game session UUID.
            county_fips: 5-digit county FIPS code.

        Returns:
            ``ExposurePayload`` dict matching
            ``specs/103-trade-surfaces/contracts/county-exposure.yaml``.
        """
        pool = getattr(self._persistence, "_pool", None)
        # hydrate_graph is called for its side-effect of ensuring the session
        # is bootstrapped; the exposure payload itself carries no tick field.
        self._persistence.hydrate_graph(tick=None, session_id=session_id)

        weights = _fetch_county_exposure_weights(pool, county_fips)
        flow_rows = _fetch_county_boundary_flows(pool, session_id, county_fips)

        # Sum flows per bloc (DRAIN_EDGE + TRADE_EDGE).
        flow_by_bloc: dict[str, float] = {}
        for r in flow_rows:
            if r["flow_type"] in ("drain_edge", "trade_inbound", "trade_outbound"):
                flow_by_bloc[r["source_node_id"]] = (
                    flow_by_bloc.get(r["source_node_id"], 0.0) + r["magnitude"]
                )

        all_blocs = sorted(set(weights.keys()) | set(flow_by_bloc.keys()))
        if not all_blocs:
            return {
                "county_fips": county_fips,
                "has_data": False,
                "total_exposure": 0.0,
                "breakdown": {"total": 0.0, "contributors": []},
                "citations": _EXPOSURE_CITATIONS,
            }

        contributors: list[dict[str, Any]] = []
        total = 0.0
        for nid in all_blocs:
            weight = weights.get(nid, 0.0)
            flow = flow_by_bloc.get(nid, 0.0)
            value = weight * flow
            total += value
            contributors.append(
                {
                    "label": _BLOC_LABELS.get(nid, nid.replace("_", " ").title()),
                    "value": round(value, 4),
                    "share": 0.0,  # filled after total is known
                    "source": {
                        "kind": "derived",
                        "path": f"exposure[{county_fips}][{nid}]",
                    },
                    "children": [
                        {
                            "label": "spec-100 exposure weight",
                            "value": weight,
                            "share": 1.0 if weight > 0 else 0.0,
                            "source": {
                                "kind": "reference_table",
                                "path": f"county_exposure_by_external[{nid}][{county_fips}]",
                            },
                            "children": [],
                        },
                        {
                            "label": f"live flow ({'+'.join(sorted({r['flow_type'] for r in flow_rows if r['source_node_id'] == nid}))})"
                            if any(r["source_node_id"] == nid for r in flow_rows)
                            else "live flow (none)",
                            "value": flow,
                            "share": 1.0 if flow > 0 else 0.0,
                            "source": {
                                "kind": "dynamic_table",
                                "path": f"boundary_flow_register[{nid}→{county_fips}]",
                            },
                            "children": [],
                        },
                    ],
                }
            )

        # Fill shares now that total is known.
        if total > 0:
            for c in contributors:
                c["share"] = round(c["value"] / total, 4)
        else:
            # When total is zero but we have data (weights or flows present),
            # distribute share equally among blocs with any signal.
            nonzero = [
                c
                for c in contributors
                if c["value"] > 0 or c["children"][0]["value"] > 0 or c["children"][1]["value"] > 0
            ]
            share = round(1.0 / len(nonzero), 4) if nonzero else 0.0
            for c in contributors:
                c["share"] = share

        return {
            "county_fips": county_fips,
            "has_data": True,
            "total_exposure": round(total, 4),
            "breakdown": {"total": round(total, 4), "contributors": contributors},
            "citations": _EXPOSURE_CITATIONS,
        }

    def get_trade_panel(self, session_id: UUID) -> dict[str, Any]:
        """Return the aggregate trade panel for the Analysis page.

        Spec 103 FR-103-03. Session-cumulative Φ inflow, per-bloc breakdown,
        and flow-type summary from ``boundary_flow_register`` aggregates +
        ``dynamic_external_node_state``. Constitution III: pure read.

        Degrades to ``has_data: False`` with honest zeros when no data is
        available.

        Args:
            session_id: The game session UUID.

        Returns:
            ``TradePanelPayload`` dict matching
            ``specs/103-trade-surfaces/contracts/trade-panel.yaml``.
        """
        pool = getattr(self._persistence, "_pool", None)
        graph = self._persistence.hydrate_graph(tick=None, session_id=session_id)
        graph_attrs: dict[str, Any] = getattr(graph, "graph", {}) or {}
        tick = int(graph_attrs.get("tick", 0))

        series_rows = _fetch_boundary_flow_series(pool, session_id)
        node_latest = _fetch_external_node_latest(pool, session_id)
        flow_type_rows = _fetch_flow_type_totals(pool, session_id)

        if not series_rows and not node_latest:
            return {
                "tick": tick,
                "has_data": False,
                "total_phi_inflow": 0.0,
                "total_trade": 0.0,
                "blocs": [],
                "flow_types": [],
            }

        # Per-bloc cumulative totals.
        all_node_ids = sorted(set(node_latest.keys()) | {r["source_node_id"] for r in series_rows})
        blocs: list[dict[str, Any]] = []
        total_phi = 0.0
        total_trade = 0.0
        for nid in all_node_ids:
            phi = sum(
                r["magnitude"]
                for r in series_rows
                if r["source_node_id"] == nid and r["flow_type"] == "drain_edge"
            )
            trade = sum(
                r["magnitude"]
                for r in series_rows
                if r["source_node_id"] == nid
                and r["flow_type"] in ("trade_inbound", "trade_outbound")
            )
            total_phi += phi
            total_trade += trade
            latest = node_latest.get(nid, {})
            blocs.append(
                {
                    "node_id": nid,
                    "label": _BLOC_LABELS.get(nid, nid.replace("_", " ").title()),
                    "phi_inflow": round(phi, 4),
                    "trade": round(trade, 4),
                    "erdi_ratio": float(latest.get("erdi_ratio", 1.0)),
                }
            )

        flow_types = [
            {
                "flow_type": r["flow_type"],
                "total": round(r["total"], 4),
                "tick_count": r["tick_count"],
            }
            for r in flow_type_rows
        ]

        return {
            "tick": tick,
            "has_data": True,
            "total_phi_inflow": round(total_phi, 4),
            "total_trade": round(total_trade, 4),
            "blocs": blocs,
            "flow_types": flow_types,
        }

    # ------------------------------------------------------------------ #
    # Inspector Views
    # ------------------------------------------------------------------ #

    def get_inspector_node(self, _session_id: UUID, _node_id: str) -> dict[str, Any]:
        """Return detailed stats for a generic node click."""
        return {}

    def get_inspector_org(self, _session_id: UUID, _org_id: str) -> dict[str, Any]:
        """Return detailed drill-down data for a specific organization."""
        return {}

    def get_inspector_community(self, _session_id: UUID, _hyperedge_id: str) -> dict[str, Any]:
        """Return detailed drill-down data for a community hyperedge."""
        return {}

    def get_inspector_edge(self, _session_id: UUID, _edge_id: str) -> dict[str, Any]:
        """Return detailed drill-down data for an edge."""
        return {}

    def get_inspector_hex(self, _session_id: UUID, _h3_index: str) -> dict[str, Any]:
        """Return detailed drill-down data for a map hex."""
        return {}

    # ------------------------------------------------------------------ #
    # Tick resolution
    # ------------------------------------------------------------------ #

    def resolve_tick(
        self,
        session_id: UUID,
        persistent_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Advance the simulation one tick: hydrate → step → persist → snapshot.

        Reads pending player actions, injects them into the engine via
        ``persistent_context["player_actions"]``, captures pre-step state
        for delta computation, runs the engine step, persists ActionResult
        rows, and checks for endgame conditions.

        Args:
            session_id: The game session UUID.
            persistent_context: Optional cross-tick context dict.

        Returns:
            JSON-serializable snapshot of the new state after stepping.
        """
        state, graph = self.hydrate_state(session_id)

        # Load defines from the session's own stored config (session-scoped;
        # the old global metadata key both leaked across sessions and was
        # never written, so stored defines were silently ignored)
        game_defines = _fetch_session_game_defines(self._persistence, session_id)

        # Spec 061 US5 T080 (FR-024): thread the session's rng_seed
        # into the engine config so action resolution is byte-deterministic
        # across replays of the same seed + action sequence.
        rng_seed = _fetch_session_rng_seed_from_pool(
            getattr(self._persistence, "_pool", None), session_id
        )
        sim_config = SimulationConfig(rng_seed=rng_seed)

        # T014: Read pending player actions and format for engine injection
        pending = self.get_pending_actions(session_id, state.tick)
        if persistent_context is None:
            persistent_context = {}

        if pending:
            player_actions: dict[str, list[dict[str, Any]]] = {}
            for action in pending:
                org_id = action["org_id"]
                verb = action.get("verb", "")
                action_type_enum = VERB_TO_ACTION_TYPE.get(verb)
                action_type_val = action_type_enum.value if action_type_enum else verb

                player_actions.setdefault(org_id, []).append(
                    {
                        "action_type": action_type_val,
                        "target_id": action.get("target_id", org_id),
                        "org_id": org_id,
                        "action_point_cost": 1,
                        "params": action.get("params_json", {}),
                    }
                )
            persistent_context["player_actions"] = player_actions

        # T015: Snapshot pre-step heat for delta computation. (The old
        # `class_consciousness` read was dead — that attr never exists at the
        # node top level; CI now comes from the engine's real result below.)
        pre_step: dict[str, dict[str, float]] = {}
        for action in pending:
            tid = action.get("target_id")
            if tid and tid in graph.nodes:
                pre_step[tid] = {"heat": float(graph.nodes[tid].get("heat", 0.0))}

        # Step the engine
        logger.debug("Stepping engine session=%s tick=%d", session_id, state.tick)
        new_state = step(
            state,
            sim_config,
            persistent_context=persistent_context,
            defines=game_defines,
        )
        logger.info(
            "Engine step complete session=%s tick=%d->%d entities=%d events=%d",
            session_id,
            state.tick,
            new_state.tick,
            len(new_state.entities),
            len(new_state.events),
        )

        # Persist the new tick
        new_graph = new_state.to_graph()
        events_as_dicts: list[dict[str, Any]] = [
            e.model_dump(mode="json") for e in new_state.events
        ]
        self._persistence.persist_tick(
            tick=new_state.tick,
            graph=new_graph,
            events=events_as_dicts if events_as_dicts else None,
            session_id=session_id,
        )

        # T016: Persist REAL per-action results from the engine's TurnResolution
        # (published by OODASystem into persistent_context["turn_resolution"];
        # replaces the old pre/post-diff fakery that hardcoded success=True and
        # diffed a never-present class_consciousness attr).
        results_by_org = _index_engine_action_results(persistent_context)
        for action in pending:
            tid = action.get("target_id")
            pre = pre_step.get(tid or "", {})
            post_heat = 0.0
            if tid and tid in new_graph.nodes:
                post_heat = float(new_graph.nodes[tid].get("heat", 0.0))

            verb = action.get("verb", "")
            action_type_enum = VERB_TO_ACTION_TYPE.get(verb)
            action_type_val = action_type_enum.value if action_type_enum else verb

            engine_result = _pop_engine_result(results_by_org, action["org_id"])
            success, failure_reason, ci_delta, direct_effects = _engine_result_fields(engine_result)

            result_data = {
                "session_id": session_id,
                "tick": new_state.tick,
                "org_id": action["org_id"],
                "action_type": action_type_val,
                "target_id": tid,
                "target_community": action.get("target_community"),
                "initiative_score": 0.0,
                "action_cost": 1.0,
                "success": success,
                "consciousness_delta": ci_delta,
                "heat_delta": post_heat - pre.get("heat", 0.0),
                "details": {"direct_effects": direct_effects, "failure_reason": failure_reason},
            }
            _persist_action_result(self._persistence, result_data)

        # T019: Check for endgame conditions in events
        snapshot = _state_to_snapshot(new_state, session_id)

        # Spec 092 R-CONS: persist this tick's events into tick_event so the
        # journal/alerts dashboards (get_journal_dashboard/get_alerts_dashboard)
        # have real history to read back. Best-effort — a journal-write
        # failure must never fail tick resolution.
        _persist_tick_events_safe(self._persistence, session_id, new_state.tick, snapshot["events"])
        # P0 #7: refresh the hex_latest map cache from this tick's territories
        # (sibling of the tick_event write above; best-effort, never raises).
        _persist_hex_state_safe(session_id, new_state.tick, snapshot["territories"])
        # Spec-109 A1: fill the spec-037 snapshot tables + the tick_summary
        # aggregates that back get_game_timeseries (spec-061 FR-003 wire-up).
        _persist_snapshots_safe(self._persistence, session_id, new_state)
        # Spec 095 FR-095-02: recognize ALL 5 terminal GameOutcome event types
        # (was 3-of-5 — RED_OGV and FRAGMENTED_COLLAPSE were missing, so those
        # endgames never surfaced in the snapshot's ``endgame`` block). The
        # _TERMINAL_OUTCOMES constant is the authoritative set, matching
        # ``babylon.models.enums.GameOutcome`` minus IN_PROGRESS.
        endgame_types = _TERMINAL_OUTCOMES
        for event in new_state.events:
            event_type = (
                event.event_type.value
                if hasattr(event.event_type, "value")
                else str(event.event_type)
            )
            if event_type in endgame_types:
                snapshot["endgame"] = {
                    "outcome": event_type,
                    "tick": new_state.tick,
                    "summary": event.data.get("summary", "")
                    if hasattr(event, "data") and isinstance(event.data, dict)
                    else "",
                }
                break

        # Mark submitted turns as resolved
        _mark_resolved_safe(self._persistence, session_id, state.tick)

        return snapshot

    # ------------------------------------------------------------------ #
    # Action management
    # ------------------------------------------------------------------ #

    def get_available_actions(self, session_id: UUID) -> dict[str, Any]:
        """Return available NPC actions for the current tick.

        Uses the OODA npc_stub to compute what actions each org can take.

        Args:
            session_id: The game session UUID.

        Returns:
            Dict with session_id, tick, and per-org action lists.
        """
        state, graph = self.hydrate_state(session_id)
        game_defines = GameDefines()

        org_actions: dict[str, list[dict[str, Any]]] = {}

        for node_id, data in graph.nodes(data=True):
            if data.get("_node_type") != "organization":
                continue
            # Find a default target (first territory the org is present in)
            target_id = ""
            territory_ids = data.get("territory_ids")
            if territory_ids:
                if isinstance(territory_ids, (list, tuple, frozenset, set)):
                    target_id = next(iter(territory_ids), "")
                else:
                    target_id = str(territory_ids)

            actions = select_npc_actions(
                org_id=node_id,
                org_attrs=dict(data),
                target_id=target_id,
                defines=game_defines.ooda,
            )
            org_actions[node_id] = [
                {
                    "org_id": a.org_id,
                    "action_type": a.action_type.value
                    if hasattr(a.action_type, "value")
                    else str(a.action_type),
                    "target_id": a.target_id,
                    "action_point_cost": a.action_point_cost,
                }
                for a in actions
            ]

        return {
            "session_id": str(session_id),
            "tick": state.tick,
            "actions": org_actions,
        }

    def submit_action(
        self,
        session_id: UUID,
        tick: int,
        org_id: str,
        verb: str,
        *,
        action_type: str | None = None,
        target_id: str | None = None,
        target_community: str | None = None,
        params_json: dict[str, Any] | None = None,
    ) -> int:
        """Submit a player action for the given tick.

        Performs affordability checks using VanguardResources before
        persisting the action. Raises ValueError if the org cannot
        afford the action.

        Args:
            session_id: The game session UUID.
            tick: The tick this action applies to.
            org_id: The organization taking the action.
            verb: Action verb string.
            action_type: Optional action type classification.
            target_id: Optional target node ID.
            target_community: Optional target community.
            params_json: Optional action parameters.

        Returns:
            The integer turn ID from the database.

        Raises:
            ValueError: If the org cannot afford the action.
        """
        # Affordability check: compute vanguard resources and verify
        state, _graph = self.hydrate_state(session_id)
        org = state.organizations.get(org_id)
        if org is not None:
            resources = VanguardResources.from_organization(
                cadre_level=float(org.cadre_level),
                cohesion=float(org.cohesion),
                budget=float(org.budget),
                heat=float(org.heat),
                territory_count=len(org.territory_ids),
            )
            if verb == "attack":
                # Special handling for ATTACK verb mode-specific costs
                mode = (params_json or {}).get("mode", "targeted")
                if mode == "targeted":
                    if resources.cadre_labor < 4.0:
                        raise ValueError(
                            f"Cannot afford 'attack' (targeted): Need 4.0 CL, have {resources.cadre_labor:.1f}"
                        )
                else:  # mass
                    if resources.sympathizer_labor < 15.0:
                        raise ValueError(
                            f"Cannot afford 'attack' (mass): Need 15.0 SL, have {resources.sympathizer_labor:.1f}"
                        )
                # AP check is bypassed here since over-budget AP resolves with degraded effectiveness
            else:
                can_afford, reason = check_can_afford(resources, verb)
                if not can_afford:
                    msg = f"Cannot afford '{verb}': {reason}"
                    raise ValueError(msg)

        # Record in action history for trap detection
        history = _session_action_history.setdefault(session_id, [])
        history.append({"verb": verb, "org_id": org_id, "target_id": target_id, "tick": tick})
        if len(history) > _ACTION_HISTORY_CAP:
            _session_action_history[session_id] = history[-_ACTION_HISTORY_CAP:]

        result: int = self._persistence.submit_turn(  # type: ignore[attr-defined]
            session_id=session_id,
            tick=tick,
            org_id=org_id,
            verb=verb,
            action_type=action_type,
            target_id=target_id,
            target_community=target_community,
            params_json=params_json,
        )
        return result

    def get_org_status(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        """Return basic status and OODA cycle information for an acting organization."""
        state, graph = self.hydrate_state(session_id)
        if org_id not in graph.nodes:
            return {}

        org_data = graph.nodes[org_id]

        # Determine resource pools
        cadre = float(org_data.get("cadre_level", 0.0))
        cohesion = float(org_data.get("cohesion", 0.0))
        budget = float(org_data.get("budget", 0.0))
        heat = float(org_data.get("heat", 0.0))

        # Territory ids can be list, set, frozenset
        territory_ids = org_data.get("territory_ids", [])
        terr_count = len(territory_ids)

        resources = VanguardResources.from_organization(
            cadre_level=cadre,
            cohesion=cohesion,
            budget=budget,
            heat=heat,
            territory_count=terr_count,
        )

        # Pending action state
        pending = self.get_pending_actions(session_id, state.tick)

        # Estimate AP
        ap_max = 3
        ap_used = len([a for a in pending if a.get("org_id") == org_id])
        ap_remaining = max(0, ap_max - ap_used)

        return {
            "id": org_id,
            "name": org_data.get("name", org_id),
            "type": str(org_data.get("org_type", "PoliticalFaction")),
            "consciousness_strategy": str(org_data.get("consciousness_strategy", "revolutionary")),
            "resources": {
                "cadre_labor": float(resources.cadre_labor),
                "sympathizer_labor": float(resources.sympathizer_labor),
                "material": float(resources.budget),
            },
            "ooda": {
                "action_points_remaining": ap_remaining,
                "action_points_max": ap_max,
                "cycle_time": 2,
            },
            "cadre_level": cadre,
            "cohesion": cohesion,
        }

    def get_educate_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        """Return available community targets for the EDUCATE verb.

        Matches the contract defined in spec 043, integrating actual
        consciousness and material readiness from the graph when available.
        """
        state, graph = self.hydrate_state(session_id)
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            # Provide an empty fallback if org not found
            return {"status": "error", "error": "Org not found"}

        # Compute cost
        cost = {
            "action_points": 1,
            "cadre_labor": 3.0,
            "sympathizer_labor": 0.0,
            "material": 0.0,
            "can_afford": org_status.get("resources", {}).get("cadre_labor", 0) >= 3.0,
            "over_budget": False,
            "over_budget_penalty": None,
        }

        targets: list[dict[str, Any]] = []
        unavailable_communities: list[dict[str, Any]] = []

        org_data = graph.nodes.get(org_id, {})
        territory_ids = org_data.get("territory_ids", [])
        for tid in territory_ids:
            if tid not in graph.nodes:
                continue
            terr_data = graph.nodes[tid]
            terr_name = terr_data.get("name", tid)

            social_classes = [
                (nid, nd)
                for nid, nd in _nodes_in_territory(graph, tid)
                if nd.get("_node_type") == "social_class"
            ]
            if not social_classes:
                unavailable_communities.append(
                    {
                        "community_id": f"community-unknown-{tid}",
                        "community_type": "UNKNOWN",
                        "territory_name": terr_name,
                        "reason": "No social_class nodes present for this territory yet.",
                    }
                )
                continue

            for sc_id, sc_data in social_classes:
                agitation = float(sc_data.get("agitation", 0.0))
                cohesion = float(org_status.get("cohesion", 0.0))

                targets.append(
                    {
                        "community_id": sc_id,
                        "community_type": str(sc_data.get("role", "UNKNOWN")).upper(),
                        "category": "social_class",
                        "territory_name": terr_name,
                        "territory_id": str(tid),
                        "credibility": cohesion,
                        "credibility_explanation": f"{int(cohesion * 100)}% org cohesion (real, not membership survey — no per-community overlap metric exists yet)",
                        "consciousness": {
                            "r": 0.0,
                            "l": 0.0,
                            "f": 0.0,
                            "dominant_tendency": "unknown",
                            "collective_identity": None,
                            "ideological_contestation": None,
                            "note": "TernaryConsciousness lives on XGI hypergraph communities, not main-graph social_class nodes; community hypergraph integration pending.",
                        },
                        "material_readiness": {
                            "avg_agitation": agitation,
                            "readiness_score": min(1.0, agitation / 0.5) if agitation else 0.0,
                            "readiness_explanation": "Derived from real SocialClass.agitation for this node.",
                        },
                        "education_pressure": {
                            "current": 0.0,
                            "projected_delta": None,
                            "projected_new": None,
                            "decay_per_tick": None,
                            "note": "education_pressure lives on XGI community hyperedges, not main-graph nodes; hypergraph integration pending.",
                        },
                        "feedforward": {
                            "note": "No per-tick routing-shift projection exists in the engine yet.",
                        },
                    }
                )

        return {
            "status": "ok",
            "tick": state.tick,
            "verb": "educate",
            "acting_org": org_status,
            "cost": cost,
            "targets": targets,
            "unavailable_communities": unavailable_communities,
        }

    def get_aid_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        """Return available targets for the AID verb.

        Matches the contract defined in spec 045, integrating actual
        material deficits and edge statuses from the graph when available.
        """
        state, graph = self.hydrate_state(session_id)
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}

        # Compute cost metrics
        cost = {
            "action_points": 1,
            "cadre_labor": 1.0,
            "sympathizer_labor": 1.0,
            "material": 0.0,
            "can_afford": org_status.get("resources", {}).get("cadre_labor", 0) >= 1.0,
            "over_budget": False,
            "over_budget_penalty": None,
        }

        population_targets: list[dict[str, Any]] = []
        org_targets: list[dict[str, Any]] = []
        unavailable_targets: list[dict[str, Any]] = []

        org_data = graph.nodes.get(org_id, {})
        territory_ids = org_data.get("territory_ids", [])

        for tid in territory_ids:
            if tid not in graph.nodes:
                continue
            terr_data = graph.nodes[tid]
            terr_name = terr_data.get("name", tid)

            econ_nodes = _nodes_in_territory(graph, tid)
            found_any = False
            for node_id, data in econ_nodes:
                node_type = data.get("_node_type")
                if node_type == "social_class":
                    found_any = True
                    population_targets.append(
                        {
                            "community_id": node_id,
                            "community_name": data.get("name", node_id),
                            "population": data.get("population"),
                            "class_name": str(data.get("role", "UNKNOWN")).upper(),
                            "material_conditions": {
                                "v_value_produced": float(data.get("wealth", 0.0)),
                                "wage_received": None,
                                "consumption_gap": None,
                                "subsistence_level": data.get("subsistence_threshold"),
                                "agitation_level": float(data.get("agitation", 0.0)),
                            },
                            "edge_status": _edge_status_between(graph, org_id, node_id),
                            "feedforward": {
                                "note": "No per-tick aid-effect projection exists in the engine yet."
                            },
                        }
                    )
                elif node_type == "organization" and node_id != org_id:
                    found_any = True
                    org_targets.append(
                        {
                            "org_id": node_id,
                            "org_name": data.get("name", node_id),
                            "org_type": str(data.get("org_type", "UNKNOWN")),
                            "material_stock": float(data.get("budget", 0.0)),
                            "edge_status": _edge_status_between(graph, org_id, node_id),
                            "feedforward": {
                                "note": "No per-tick aid-effect projection exists in the engine yet."
                            },
                        }
                    )

            if not found_any:
                unavailable_targets.append(
                    {
                        "community_id": f"community-unknown-{tid}",
                        "community_type": "UNKNOWN",
                        "territory_name": terr_name,
                        "reason": "No population or organization data present for this territory yet.",
                    }
                )

        return {
            "status": "ok",
            "tick": state.tick,
            "verb": "aid",
            "acting_org": org_status,
            "cost": cost,
            "population_targets": population_targets,
            "org_targets": org_targets,
            "unavailable_targets": unavailable_targets,
        }

    def get_mobilize_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        """Return available targets for the MOBILIZE verb.

        Matches the contract defined in spec 047, evaluating target territories
        and businesses for mass action vectors (PROTEST/STRIKE). Returns solidarity
        amplification opportunities and cost projections.
        """
        state, graph = self.hydrate_state(session_id)
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}

        org_data = graph.nodes.get(org_id, {})
        territory_ids = org_data.get("territory_ids", [])

        targets: list[dict[str, Any]] = []
        for tid in territory_ids:
            if tid not in graph.nodes:
                continue
            for node_id, data in _nodes_in_territory(graph, tid):
                if data.get("_node_type") != "organization" or node_id == org_id:
                    continue
                if str(data.get("org_type", "")) not in ("business", "civil_society"):
                    continue
                allies = [
                    {"id": ally_id, "name": graph.nodes[ally_id].get("name", ally_id)}
                    for ally_id, ally_data in _nodes_in_territory(graph, tid)
                    if ally_data.get("_node_type") == "organization"
                    and ally_id not in (org_id, node_id)
                ]
                targets.append(
                    {
                        "id": node_id,
                        "name": data.get("name", node_id),
                        "type": str(data.get("org_type", "UNKNOWN")).upper(),
                        "heat": float(data.get("heat", 0.0)),
                        "cohesion": float(data.get("cohesion", 0.0)),
                        "coordination_opportunities": [
                            {"type": "SOLIDARITY_AMPLIFICATION", "ally": ally} for ally in allies
                        ],
                    }
                )

        return {
            "entity_id": org_id,
            "name": org_status.get("name", "Unknown Org"),
            "available_sl": org_status.get("resources", {}).get("sympathizer_labor", 0.0),
            "available_cl": org_status.get("resources", {}).get("cadre_labor", 0.0),
            "mobilize_cost_cl": GameDefines().mobilize.mobilize_cl_cost,
            "targets": targets,
        }

    def get_attack_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        """Return available targets for the ATTACK verb.

        Matches the contract defined in spec 046, providing organizational,
        edge, and institutional targets with projections for constant capital
        destruction and severed flow.
        """
        state, graph = self.hydrate_state(session_id)
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}

        resources = org_status.get("resources", {})
        cost = {
            "action_points": 3,
            "cadre_labor_if_targeted": 2.5,
            "sympathizer_labor_if_mass": 25.0,
            "material": 100.0,
            "can_afford_targeted": resources.get("cadre_labor", 0) >= 2.5,
            "can_afford_mass": resources.get("sympathizer_labor", 0) >= 25.0,
            "over_budget_ap": False,
            "cost_explanation": "TARGETED attacks use dense cadre formations. MASS actions use diffused sympathizer labor. Both require AP and initial materials.",
        }

        # Real ultra-left trap status from the last resolved tick, when
        # available (spec 056 trap detection — see resolve_tick()).
        trap_state = _session_trap_state.get(session_id)
        if trap_state is not None:
            ultra_left_warning = {
                "active": trap_state.ultra_left.severity != "none",
                "trap_score": trap_state.ultra_left.score,
                "indicators": list(trap_state.ultra_left.indicators),
                "explanation": "Real ultra-left trap detection from this session's action history.",
            }
        else:
            ultra_left_warning = {
                "active": False,
                "trap_score": 0.0,
                "indicators": [],
                "explanation": "No trap detection has run yet this session (requires a resolved tick).",
            }

        org_data = graph.nodes.get(org_id, {})
        territory_ids = org_data.get("territory_ids", [])

        organizations: list[dict[str, Any]] = []
        institutions: list[dict[str, Any]] = []
        unavailable_targets: list[dict[str, Any]] = []
        p_acquiescence_values: list[float] = []

        for tid in territory_ids:
            if tid not in graph.nodes:
                continue
            terr_data = graph.nodes[tid]
            terr_name = terr_data.get("name", tid)
            found_any = False

            for node_id, data in graph.nodes(data=True):
                node_type = data.get("_node_type")
                if node_type == "social_class" and tid in data.get("territory_ids", []):
                    if "p_acquiescence" in data:
                        p_acquiescence_values.append(float(data["p_acquiescence"]))
                    continue
                if (
                    node_type == "organization"
                    and node_id != org_id
                    and tid in data.get("territory_ids", [])
                ):
                    found_any = True
                    extractive_edges = _outgoing_extractive_edges(graph, node_id)
                    organizations.append(
                        {
                            "target_id": node_id,
                            "target_type": str(data.get("org_type", "UNKNOWN")).upper(),
                            "name": data.get("name", node_id),
                            "territory_name": terr_name,
                            "territory_id": str(tid),
                            "defensive_capacity": float(data.get("budget", 0.0)),
                            "extractive_edges": extractive_edges,
                        }
                    )
                elif node_type == "institution" and tid in data.get("territory_ids", []):
                    found_any = True
                    institutions.append(
                        {
                            "target_id": node_id,
                            "target_type": "INSTITUTION",
                            "name": data.get("name", node_id),
                            "factional_control": dict(data.get("factional_composition", {})),
                        }
                    )

            if not found_any:
                unavailable_targets.append(
                    {
                        "target_id": f"unknown-{tid}",
                        "name": "No hostile organization or institution present",
                        "territory_name": terr_name,
                        "reason": "No target data present for this territory yet.",
                    }
                )

        min_p_acquiescence = min(p_acquiescence_values) if p_acquiescence_values else None
        warsaw_ghetto_flag = {
            "active": min_p_acquiescence is not None and min_p_acquiescence <= 0.05,
            "population_p_acquiescence": min_p_acquiescence,
            "threshold": 0.05,
            "explanation": "If survival probabilities reach near absolute zero, mass base will endorse desperate measures regardless of military feasibility.",
        }

        return {
            "status": "ok",
            "tick": state.tick,
            "verb": "attack",
            "acting_org": org_status,
            "cost": cost,
            "ultra_left_warning": ultra_left_warning,
            "warsaw_ghetto_flag": warsaw_ghetto_flag,
            "targets": {
                "organizations": organizations,
                "edges": [],
                "institutions": institutions,
            },
            "unavailable_targets": unavailable_targets,
        }

    def get_reproduce_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        """Return available reproduction modes for the REPRODUCE verb.

        Matches the contract defined in spec 048 for organizational reproduction.
        """
        state, graph = self.hydrate_state(session_id)
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}

        cost = {
            "action_points": 1,
            "cadre_labor": 0.0,
            "sympathizer_labor": 10.0,
            "material": 0.0,
            "can_afford": org_status.get("resources", {}).get("sympathizer_labor", 0) >= 10.0,
            "over_budget": False,
            "over_budget_penalty": None,
        }

        org_data = graph.nodes.get(org_id, {})
        territory_ids = org_data.get("territory_ids", [])
        base_population = sum(
            int(data.get("population", 0))
            for tid in territory_ids
            for node_id, data in _nodes_in_territory(graph, tid)
            if data.get("_node_type") == "social_class"
        )

        targets = [
            {
                "target_id": org_id,
                "name": org_status.get("name", org_id),
                "type": "ORGANIZATION",
                "modes": {
                    "cadre_training": {
                        "resource_cost": {"sympathizer_labor": 10.0},
                        "projected_effect": {
                            "cadre_delta": 1.0,
                            "cohesion_delta": 0.02,
                            "agitation_delta": 0.0,
                        },
                        "recruitment_pool": {
                            "sympathizers": int(
                                org_status.get("resources", {}).get("sympathizer_labor", 0)
                            )
                        },
                        "cooldown_applied": 0,
                        "explanation": "Converts 10 sympathizer labor into 1 cadre labor, increasing cohesion.",
                    },
                    "mass_recruitment": {
                        "resource_cost": {"cadre_labor": 2.0},
                        "projected_effect": {
                            "cadre_delta": 0.0,
                            "cohesion_delta": -0.05,
                            "agitation_delta": 0.1,
                        },
                        "recruitment_pool": {"base_population": base_population},
                        "cooldown_applied": 1,
                        "explanation": "Spends cadre labor to prospect among the agitated base. Dilutes cohesion but gains sympathizers.",
                    },
                },
                "state_response": {"state_visibility": "LOW", "attention_diverted": 0.0},
            }
        ]

        return {
            "status": "ok",
            "tick": state.tick,
            "verb": "reproduce",
            "acting_org": org_status,
            "cost": cost,
            "targets": targets,
        }

    def get_investigate_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        """Return available investigation targets for the INVESTIGATE verb.

        Matches the contract defined in spec 048 for intel-gathering.
        """
        state, graph = self.hydrate_state(session_id)
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}

        cost = {
            "action_points": 1,
            "cadre_labor": 2.0,
            "sympathizer_labor": 0.0,
            "material": 0.0,
            "can_afford": org_status.get("resources", {}).get("cadre_labor", 0) >= 2.0,
            "over_budget": False,
            "over_budget_penalty": None,
        }

        observe_capability = {"intel_network_strength": 0.6, "max_scan_depth": "TARGETED"}

        org_data = graph.nodes.get(org_id, {})
        territory_scans = [
            {
                "target_id": str(tid),
                "name": graph.nodes[tid].get("name", tid),
                "target_type": "TERRITORY",
                "heat": float(graph.nodes[tid].get("heat", 0.0)),
                "current_knowledge": {
                    "visibility_level": "SURFACE",
                    "known_attributes": ["population"],
                    "last_scanned_tick": None,
                },
                "resource_cost": {"sympathizer_labor": 5.0},
                "projected_reveals": {
                    "new_visibility_level": "TARGETED",
                    "likely_reveals": ["material_readiness", "hidden_factions", "state_deployment"],
                },
            }
            for tid in org_data.get("territory_ids", [])
            if tid in graph.nodes
        ]

        targeted_scans = [
            {
                "target_id": "org-police-union",
                "name": "Fraternal Order of Police",
                "target_type": "INSTITUTION",
                "current_knowledge": {
                    "visibility_level": "NONE",
                    "known_attributes": [],
                    "last_scanned_tick": None,
                },
                "resource_cost": {"cadre_labor": 4.0},
                "projected_reveals": {
                    "new_visibility_level": "SURFACE",
                    "likely_reveals": ["factional_control", "defensive_capacity"],
                },
                "detection_risk": {
                    "probability": 0.35,
                    "consequence": "Increases organization heat by 0.15",
                },
            }
        ]

        counter_intelligence = {
            "active_moles_suspected": 1,
            "resource_cost": {"cadre_labor": 5.0},
            "projected_reveals": {
                "new_visibility_level": "INTERNAL_AUDIT",
                "likely_reveals": ["mole_identities", "leaked_information_vectors"],
            },
        }

        return {
            "status": "ok",
            "tick": state.tick,
            "verb": "investigate",
            "acting_org": org_status,
            "cost": cost,
            "observe_capability": observe_capability,
            "targets": {
                "territory_scans": territory_scans,
                "targeted_scans": targeted_scans,
                "counter_intelligence": counter_intelligence,
            },
        }

    def get_move_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        """Return available destinations for the MOVE verb.

        Matches the contract defined in spec 049 for spatial presence.
        """
        state, graph = self.hydrate_state(session_id)
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}

        cost = {
            "action_points": 1,
            "cadre_labor": 10.0,
            "sympathizer_labor": 0.0,
            "material": 0.0,
            "can_afford": org_status.get("resources", {}).get("cadre_labor", 0) >= 10.0,
            "over_budget": False,
            "over_budget_penalty": None,
        }

        targets = [
            {
                "id": "territory-macomb",
                "name": "Macomb County",
                "community_reception": {"overlap_score": 0.45, "cross_community_penalty": 0.1},
                "strategic_assessment": {
                    "value_circuit_position": {"type": "logistics_hub", "s_v_ratio": 1.2},
                    "surveillance_evasion": 0.65,
                },
                "projected_outcomes": {
                    "expand": {
                        "presence_value": 0.5,
                        "edges_at_risk": 2,
                        "ticks_to_operational": 3,
                    },
                    "relocate": {
                        "presence_value": 1.0,
                        "edges_at_risk": 5,
                        "ticks_to_operational": 1,
                    },
                },
            }
        ]

        return {
            "status": "ok",
            "tick": state.tick,
            "verb": "move",
            "acting_org": org_status,
            "cost": cost,
            "current_territories": org_status.get("territory_ids", []),
            "targets": targets,
        }

    def get_negotiate_targets(self, session_id: UUID, org_id: str) -> dict[str, Any]:
        """Return available targets for the NEGOTIATE verb.

        Matches the contract defined in spec 050 for bilateral edge creation.
        """
        state, graph = self.hydrate_state(session_id)
        org_status = self.get_org_status(session_id, org_id)
        if not org_status:
            return {"status": "error", "error": "Org not found"}

        cost = {
            "action_points": 1,
            "cadre_labor": 0.0,
            "sympathizer_labor": 0.0,
            "material": 0.0,
            "can_afford": True,
            "over_budget": False,
            "over_budget_penalty": None,
        }

        targets = [
            {
                "id": "org-auto-union",
                "name": "Auto Workers Union",
                "type": "ORGANIZATION",
                "interest_alignment": {
                    "score": 0.75,
                    "shared_interests": ["wage_increases", "safety"],
                    "divergent_interests": ["systemic_change"],
                    "alliance_type": "tactical",
                },
                "negotiation_options": [
                    {
                        "proposal": "coordination_pact",
                        "success_probability": 0.65,
                        "edge_effect": "TRANSACTIONAL edge created",
                        "state_response_prediction": "State may attempt CO-OPT:DIVIDE",
                        "betrayal_risk": 0.3,
                    }
                ],
                "betrayal_risk": 0.3,
                "existing_edge_state": None,
            }
        ]

        de_escalation_targets = [
            {
                "target_id": "org-rival-faction",
                "name": "Rival Revolutionary Faction",
                "antagonism_cause": "ideological_divergence",
                "reconciliation_requirement": "joint_action_against_state",
            }
        ]

        return {
            "status": "ok",
            "tick": state.tick,
            "verb": "negotiate",
            "acting_org": org_status,
            "cost": cost,
            "org_leverage": 0.8,
            "targets": targets,
            "de_escalation_targets": de_escalation_targets,
        }

    def preview_action(
        self,
        session_id: UUID,
        org_id: str,
        verb: str,
        target_id: str | None = None,
    ) -> dict[str, Any]:
        """Compute estimated effects of a proposed action without mutating state.

        Uses the current graph state to estimate consciousness delta, heat delta,
        action cost, and success probability. Read-only — no state changes.

        Args:
            session_id: The game session UUID.
            org_id: ID of the acting organization.
            verb: One of the 9 canonical player verbs.
            target_id: Optional target territory or entity ID.

        Returns:
            Dict with estimated deltas, cost, probability, and warnings.
        """
        state, graph = self.hydrate_state(session_id)
        warnings: list[str] = []
        affected_territory_ids: list[str] = []

        # Resolve action type from verb
        action_type_enum = VERB_TO_ACTION_TYPE.get(verb)
        action_cost = 1.0  # Default AP cost

        # Check if org exists
        if org_id not in graph.nodes:
            return {
                "estimated_consciousness_delta": 0.0,
                "estimated_heat_delta": 0.0,
                "action_point_cost": action_cost,
                "success_probability": 0.0,
                "affected_territory_ids": [],
                "warnings": [f"Organization '{org_id}' not found"],
            }

        org_data = graph.nodes[org_id]
        org_budget = float(org_data.get("budget", 0.0))
        org_heat = float(org_data.get("heat", 0.0))
        org_cohesion = float(org_data.get("cohesion", 0.5))

        # Budget warning
        if org_budget < action_cost:
            warnings.append("Insufficient budget for this action")

        # Heat warning
        if org_heat > 0.7:
            warnings.append("Organization heat is already elevated")

        # Estimate effects based on target
        estimated_consciousness_delta = 0.0
        estimated_heat_delta = 0.0
        success_probability = 0.5

        resolved_target = target_id or org_id
        if resolved_target in graph.nodes:
            target_data = graph.nodes[resolved_target]

            # Check if target is under eviction
            if target_data.get("under_eviction", False):
                warnings.append("Target territory is under eviction")

            # Estimate based on verb category. Consciousness verbs (educate /
            # campaign / aid) now source their CI estimate from the SAME pure
            # helper the resolvers use (compute_consciousness_delta) so preview
            # == resolution, instead of the old 0.05*cohesion literal.
            if verb in {"educate", "campaign", "aid"} and action_type_enum is not None:
                estimated_consciousness_delta = _preview_consciousness_delta(
                    org_data, resolved_target, action_type_enum, graph
                )
                estimated_heat_delta = -0.01 if verb == "aid" else 0.01
                success_probability = min(0.95, 0.4 + org_cohesion * 0.5)
            elif verb in {"attack", "mobilize"}:
                # Aggressive actions — high heat, variable consciousness
                estimated_consciousness_delta = 0.02
                estimated_heat_delta = 0.08 * org_cohesion
                success_probability = min(0.8, 0.3 + org_cohesion * 0.4)
            elif verb == "reproduce":
                # Organizational building
                estimated_consciousness_delta = 0.01
                estimated_heat_delta = -0.01
                success_probability = min(0.95, 0.5 + org_cohesion * 0.4)
            elif verb in {"investigate", "negotiate", "move"}:
                # Lower-impact actions
                estimated_consciousness_delta = 0.0
                estimated_heat_delta = 0.0
                success_probability = min(0.9, 0.6 + org_cohesion * 0.3)

            # Collect affected territories
            territory_ids = org_data.get("territory_ids", [])
            if isinstance(territory_ids, (list, tuple)):
                affected_territory_ids = list(territory_ids)
            if target_id and target_id not in affected_territory_ids:
                affected_territory_ids.append(target_id)
        else:
            warnings.append(f"Target '{resolved_target}' not found in current state")

        # Apply action type modifier if available
        if action_type_enum is not None:
            action_cost = 1.0  # Could vary by type in future

        return {
            "estimated_consciousness_delta": round(estimated_consciousness_delta, 4),
            "estimated_heat_delta": round(estimated_heat_delta, 4),
            "action_point_cost": action_cost,
            "success_probability": round(success_probability, 4),
            "affected_territory_ids": affected_territory_ids,
            "warnings": warnings,
        }

    def get_pending_actions(self, session_id: UUID, tick: int) -> list[dict[str, Any]]:
        """Return unresolved player actions for a tick.

        Args:
            session_id: The game session UUID.
            tick: The tick to query.

        Returns:
            List of dicts, each representing a pending turn row.
        """
        result: list[dict[str, Any]] = self._persistence.get_pending_turns(  # type: ignore[attr-defined]
            session_id=session_id, tick=tick
        )
        return result


# ---------------------------------------------------------------------- #
# Private helpers
# ---------------------------------------------------------------------- #


def _graph_tick(graph: BabylonGraph) -> int:
    """Extract the tick from graph-level metadata, defaulting to 0."""
    return int(graph.graph.get("tick", 0))


# Aliases accepted at the API/CLI boundary, mapped to canonical names in the
# engine scenario registry (babylon.engine.scenarios). "us_nationwide" is the
# SCENARIO_CATALOG key served by GET /api/scenarios/ (web/game/api.py) and the
# key the React game-creation UI submits — it MUST stay resolvable.
_SCENARIO_ALIASES: dict[str, str] = {
    "default": "us",
    "us_nationwide": "us",
    "wayne": "wayne_county",
    "detroit": "wayne_county",
}


def resolve_scenario(scenario: str) -> str:
    """Resolve a scenario identifier or alias to a canonical registry name.

    Args:
        scenario: Scenario name from an API request or management command.

    Returns:
        The canonical name registered in the engine scenario registry.

    Raises:
        ValueError: If the identifier matches no registered scenario or alias.
    """
    normalized = scenario.strip().lower()
    canonical = _SCENARIO_ALIASES.get(normalized, normalized)
    if canonical not in list_scenarios():
        valid = ", ".join(sorted({*list_scenarios(), *_SCENARIO_ALIASES}))
        raise ValueError(f"Unknown scenario '{scenario}'. Valid scenarios: {valid}")
    return canonical


def _build_initial_state_for_scenario(scenario: str) -> WorldState:
    """Construct initial WorldState for a supported scenario identifier.

    Args:
        scenario: Scenario name from API request.

    Returns:
        Seeded WorldState at tick 0.

    Raises:
        ValueError: If ``scenario`` is not a registered scenario or alias.
    """
    canonical = resolve_scenario(scenario)
    state, _config, _defines = get_scenario(canonical)().build()
    return state


def _is_unseeded_graph(graph: BabylonGraph) -> bool:
    """Return True when a hydrated graph has no persisted simulation content."""
    return graph.number_of_nodes() == 0 and graph.number_of_edges() == 0


def _enum_val(obj: object) -> str:
    """Extract .value from an enum or fall back to str()."""
    return obj.value if hasattr(obj, "value") else str(obj)


def _optional_float(value: Any) -> float | None:
    """Coerce a numeric-or-None field to ``float | None`` defensively.

    Postgres ``NULL`` columns surface as ``None`` from psycopg's row
    objects; numeric ``Decimal`` results need an explicit ``float()``.
    """
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# Spec 061 US3 FR-012: event severity classification.
# Maps engine EventType strings (the canonical lowercase form) to the
# three-bucket frontend taxonomy. Default for unmapped types is
# "informational" — the safe non-alarming bucket.
_EVENT_SEVERITY: dict[str, str] = {
    # Critical: state-violation / collapse events
    "economic_crisis": "critical",
    "class_decomposition": "critical",
    "superwage_crisis": "critical",
    "imperial_collapse": "critical",
    "uprising": "critical",
    "revolution": "critical",
    "fascist_consolidation": "critical",
    # Warning: threshold-cross / bifurcation events
    "consciousness_bifurcation": "warning",
    "ideology_drift": "warning",
    "heat_threshold": "warning",
    "eviction_pipeline": "warning",
    "repression_event": "warning",
    "trap_activated": "warning",
    "excessive_force": "warning",
    # Informational: routine flow events
    "surplus_extraction": "informational",
    "imperial_subsidy": "informational",
    "wage_payment": "informational",
    "solidarity_transmission": "informational",
}


def _classify_event(event_type_str: str) -> str:
    """Map an event_type to one of {critical, warning, informational}.

    Per spec 061 FR-012. Unrecognized types default to informational so
    the frontend can render them without raising the alarm level.
    """
    return _EVENT_SEVERITY.get(event_type_str.lower(), "informational")


def _humanize_event_type(event_type_str: str) -> str:
    """Convert ``"economic_crisis"`` to ``"Economic Crisis"`` for UI titles."""
    return event_type_str.replace("_", " ").title()


def _serialize_event(event: Any, session_id: UUID) -> dict[str, Any]:
    """Serialize a single :class:`SimulationEvent` for the snapshot.

    Spec 061 US3 (FR-012): every event surfaces ``id``, ``severity``,
    ``title``, and ``body`` fields in addition to the legacy
    ``type``/``tick``/``data`` triple.

    - ``id``: deterministic UUID5 over ``(session_id, tick, event_type,
      data)`` so retries / replays produce identical IDs (Constitution
      III.7 — determinism).
    - ``severity``: one of ``{"critical", "warning", "informational"}``
      via :func:`_classify_event`.
    - ``title``: human-readable variant of ``event_type``.
    - ``body``: a short prose body derived from the event payload.
      Falls back to the empty string when no narrative is available
      (the frontend renders body-less events compactly).
    """
    import json
    import uuid

    event_type_str = _enum_val(event.event_type)
    tick = getattr(event, "tick", 0)
    data: dict[str, Any] = {}
    for attr in ("data", "payload"):
        value = getattr(event, attr, None)
        if isinstance(value, dict):
            data = value
            break
    if not data:
        try:
            data = event.model_dump(exclude={"event_type", "tick", "timestamp"})
        except Exception:  # noqa: BLE001 — defensive
            data = {}

    deterministic_seed = json.dumps(
        {
            "session": str(session_id),
            "tick": tick,
            "event_type": event_type_str,
            "data": data,
        },
        sort_keys=True,
        default=str,
    )
    event_id = str(uuid.uuid5(uuid.NAMESPACE_URL, deterministic_seed))

    narrative = getattr(event, "narrative", None) or ""
    return {
        "id": event_id,
        "type": event_type_str,
        "tick": tick,
        "severity": _classify_event(event_type_str),
        "title": _humanize_event_type(event_type_str),
        "body": narrative,
        "data": data,
    }


def _tick_event_row(serialized_event: dict[str, Any]) -> dict[str, Any]:
    """Convert a :func:`_serialize_event` dict into a ``tick_event`` row.

    Spec 092: the inverse of :func:`_game_event_from_tick_event_row`. Used
    by :func:`_persist_tick_events_safe` to shape events for
    ``persist_tick_events`` (``tick_event`` table columns: event_type,
    severity, source_id, target_id, county_fips, h3_index, summary, detail).

    Args:
        serialized_event: Output of :func:`_serialize_event`.

    Returns:
        Dict matching :meth:`PostgresRuntime.persist_tick_events`' row shape.
    """
    data = serialized_event.get("data") or {}
    source_id = data.get("source_id") or data.get("org_id") or data.get("entity_id")
    target_id = data.get("target_id") or data.get("territory_id")
    summary = (
        serialized_event.get("body") or serialized_event.get("title") or serialized_event["type"]
    )
    return {
        "event_type": serialized_event["type"],
        "severity": serialized_event.get("severity"),
        "source_id": str(source_id) if source_id is not None else None,
        "target_id": str(target_id) if target_id is not None else None,
        "county_fips": data.get("county_fips"),
        "h3_index": data.get("h3_index"),
        "summary": summary,
        "detail": data,
    }


def _territory_snapshot_rows(territories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project :func:`_serialize_territory` dicts onto ``territory_snapshot`` keys.

    ``territory_snapshot`` is county-keyed (PK includes ``county_fips``), so
    territories without county identity — every hex-resolution scenario today —
    are skipped rather than written under a fabricated key (Constitution
    III.11: no invented values). ``population`` maps onto the schema's
    ``pop_total``; ValueTensor/indicator columns stay NULL until the
    serializer carries them (spec-109 A2).

    Args:
        territories: One dict per territory, from ``_serialize_territory``.

    Returns:
        Payload dicts accepted by ``PostgresRuntime.persist_territory_snapshots``.
    """
    rows: list[dict[str, Any]] = []
    for t in territories:
        fips = t.get("county_fips")
        if not fips:
            continue
        rows.append({**t, "county_fips": str(fips), "pop_total": int(t.get("population") or 0)})
    return rows


def _org_snapshot_rows(organizations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project :func:`_serialize_organization` dicts onto ``org_snapshot`` keys.

    Field mapping (serializer -> schema): ``id -> org_id``, ``cohesion ->
    coherence``, ``budget -> material_resources`` (the org's money), the
    vanguard block's ``cadre_labor``/``sympathizer_labor``/``reputation``
    pass through, and ``player_controlled`` becomes ``owner_type``
    (``player``/``npc``). Absent engine fields stay NULL.

    Args:
        organizations: One dict per org, from ``_serialize_organization``.

    Returns:
        Payload dicts accepted by ``PostgresRuntime.persist_org_snapshots``.
    """
    rows: list[dict[str, Any]] = []
    for o in organizations:
        org_id = o.get("id")
        org_type = o.get("org_type")
        if not org_id or not org_type:
            continue
        vanguard = o.get("vanguard") or {}
        rows.append(
            {
                "org_id": str(org_id),
                "org_type": str(org_type),
                "cadre_labor": vanguard.get("cadre_labor"),
                "sympathizer_labor": vanguard.get("sympathizer_labor"),
                "material_resources": o.get("budget"),
                "coherence": o.get("cohesion"),
                "reputation": vanguard.get("reputation"),
                "owner_type": "player" if o.get("player_controlled") else "npc",
                "attributes": {
                    "heat": o.get("heat"),
                    "cadre_level": o.get("cadre_level"),
                    "class_character": o.get("class_character"),
                },
            }
        )
    return rows


def _edge_snapshot_rows(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project :func:`_serialize_edge` dicts onto ``edge_snapshot`` keys.

    ``mode`` maps onto the schema's ``edge_type``; the serializer's
    ``repression_flow`` carries the model's ``solidarity_strength`` (see
    ``_serialize_edge``'s docstring) and maps onto ``solidarity``.

    Args:
        edges: One dict per relationship, from ``_serialize_edge``.

    Returns:
        Payload dicts accepted by ``PostgresRuntime.persist_edge_snapshots``.
    """
    rows: list[dict[str, Any]] = []
    for e in edges:
        if not (e.get("source_id") and e.get("target_id") and e.get("mode")):
            continue
        rows.append(
            {
                "source_id": str(e["source_id"]),
                "target_id": str(e["target_id"]),
                "edge_type": str(e["mode"]),
                "value_flow": e.get("value_flow"),
                "tension": e.get("tension"),
                "solidarity": e.get("repression_flow"),
            }
        )
    return rows


def _build_tick_summary(state: WorldState, organizations: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate one tick's ``tick_summary`` row from live state.

    Only values the engine actually computes are aggregated; everything else
    stays ``None`` — NULL columns over invented zeros (Constitution III.11).
    Sources: ``imperial_rent`` from :class:`GlobalEconomy`'s
    ``imperial_rent_pool``; ``avg_consciousness`` over
    ``SocialClass.class_consciousness``; edge counts by ``edge_type``
    (``co_optive`` has no edge type in the model — NULL); event counts by
    exact ``EventType`` value; the player flag from the serializer's
    ``player_controlled`` (the engine model carries no such field).

    Args:
        state: The freshly stepped (or seeded) WorldState.
        organizations: ``_serialize_organization`` output for ``state``.

    Returns:
        Kwargs dict for ``PostgresRuntime.persist_tick_summary``.
    """
    consciousness_values = [
        float(sc.ideology.class_consciousness) for sc in state.entities.values()
    ]
    avg_consciousness = (
        sum(consciousness_values) / len(consciousness_values) if consciousness_values else None
    )

    edge_types = [_enum_val(rel.edge_type) for rel in state.relationships]
    event_types = [_enum_val(e.event_type) for e in state.events]

    return {
        "year": None,
        "total_c": None,
        "total_v": None,
        "total_s": None,
        "exploitation_rate": None,
        "profit_rate": None,
        "imperial_rent": float(state.economy.imperial_rent_pool) if state.economy else None,
        "avg_consciousness": avg_consciousness,
        "solidarity_edge_count": sum(1 for t in edge_types if t == "solidarity"),
        "antagonistic_edge_count": sum(1 for t in edge_types if t == "exploitation"),
        "co_optive_edge_count": None,
        "org_count": len(organizations),
        "player_org_count": sum(1 for o in organizations if o.get("player_controlled")),
        "uprising_count": sum(1 for t in event_types if t == "uprising"),
        "repression_count": sum(1 for t in event_types if t == "state_repression"),
        "conservation_check": None,
    }


def _persist_snapshots_safe(
    persistence: RuntimePersistence, session_id: UUID, state: WorldState
) -> None:
    """Persist the spec-037 read-model snapshot tables for one tick (spec-109 A1).

    The spec-061 FR-003 wire-up that never happened: fills
    ``territory_snapshot``/``org_snapshot``/``edge_snapshot`` via
    :meth:`PostgresRuntime.persist_full_tick` and the ``tick_summary``
    aggregates behind :meth:`EngineBridge.get_game_timeseries` via
    :meth:`PostgresRuntime.persist_tick_summary`.

    Best-effort like its ``_persist_*_safe`` siblings: a read-model write
    failure is logged loudly but never fails tick resolution. SQLite-backed
    ``RuntimeDatabase`` lacks both writers and no-ops here.
    :exc:`TickAlreadyResolved` is the benign idempotent-retry case — the
    snapshots for this ``(session, tick)`` already committed.

    Args:
        persistence: The RuntimePersistence instance.
        session_id: The game session UUID.
        state: The freshly stepped (or tick-0 seeded) WorldState.
    """
    full_tick_fn = getattr(persistence, "persist_full_tick", None)
    summary_fn = getattr(persistence, "persist_tick_summary", None)
    if not callable(full_tick_fn) or not callable(summary_fn):
        return

    territories = [_serialize_territory(t) for t in state.territories.values()]
    organizations = [_serialize_organization(o) for o in state.organizations.values()]
    edges = [_serialize_edge(rel) for rel in state.relationships]

    try:
        full_tick_fn(
            session_id,
            state.tick,
            territories=_territory_snapshot_rows(territories),
            orgs=_org_snapshot_rows(organizations),
            edges=_edge_snapshot_rows(edges),
        )
    except TickAlreadyResolved:
        logger.info(
            "persist_full_tick: tick %d already resolved for session=%s — retry no-op",
            state.tick,
            session_id,
        )
    except Exception:  # noqa: BLE001 — diagnostic; never blocks tick resolution
        logger.exception(
            "Failed to persist snapshot tables session=%s tick=%d", session_id, state.tick
        )

    try:
        summary_fn(state.tick, _build_tick_summary(state, organizations), session_id=session_id)
    except Exception:  # noqa: BLE001 — diagnostic; never blocks tick resolution
        logger.exception(
            "Failed to persist tick_summary session=%s tick=%d", session_id, state.tick
        )


def _persist_tick_events_safe(
    persistence: RuntimePersistence,
    session_id: UUID,
    tick: int,
    serialized_events: list[dict[str, Any]],
) -> None:
    """Best-effort write of a tick's events into the ``tick_event`` table.

    Spec 092 R-CONS: gives ``get_journal_dashboard``/``get_alerts_dashboard``
    real history to read back. Mirrors :func:`_persist_action_result`'s
    optional-capability pattern — SQLite-backed ``RuntimeDatabase``
    (dev/test) has no ``persist_tick_events`` method and this becomes a
    silent no-op there (matches :meth:`EngineBridge.get_game_timeseries`'s
    established SQLite fallback). Never raises: a journal-write failure
    must not fail tick resolution.

    Args:
        persistence: The RuntimePersistence instance.
        session_id: The game session UUID.
        tick: The tick these events belong to.
        serialized_events: Output of ``_serialize_event`` for each event
            (i.e. ``snapshot["events"]``).
    """
    if not serialized_events:
        return
    persist_fn = getattr(persistence, "persist_tick_events", None)
    if not callable(persist_fn):
        return
    rows = [_tick_event_row(e) for e in serialized_events]
    try:
        persist_fn(session_id, tick, rows)
    except Exception:  # noqa: BLE001 — diagnostic; never blocks tick resolution
        logger.exception("Failed to persist tick_event rows session=%s tick=%d", session_id, tick)


def _hex_feature_properties(state: Any) -> dict[str, Any]:
    """Project one ``hex_latest`` row onto hex-zoom ``/map/`` feature properties.

    Emits every :data:`MAP_METRIC_PROPERTIES` key (the spec-109 A3 contract —
    ``org_presence`` maps from ``org_count``, ``population`` from
    ``pop_total``) plus the identity/context columns. Extracted from the
    ``get_map_snapshot`` loop so the contract is unit-testable without a
    database.

    Args:
        state: One ``HexState`` row (or any object carrying its columns).

    Returns:
        The feature ``properties`` dict.
    """
    return {
        "h3_index": state.h3_index,
        "county_fips": state.county_fips,
        "county_name": state.county_name,
        "bea_ea_code": state.bea_ea_code,
        "msa_code": state.msa_code,
        "profit_rate": state.profit_rate,
        "exploitation_rate": state.exploitation_rate,
        "occ": state.occ,
        "imperial_rent": state.imperial_rent,
        "heat": state.heat,
        "org_presence": state.org_count,
        "dominant_class": state.dominant_class,
        "population": state.pop_total,
    }


def _hex_state_row(session_id: UUID, tick: int, territory: dict[str, Any]) -> dict[str, Any] | None:
    """Project one :func:`_serialize_territory` dict onto ``hex_latest`` columns.

    Returns ``None`` for territories without an ``h3_index`` (abstract
    scenarios such as ``two_node``) — those cannot be drawn on the map.

    Args:
        session_id: The game session UUID (``hex_latest.game_id``).
        tick: The tick this row reflects.
        territory: One entry of ``snapshot["territories"]``.

    Returns:
        Kwargs dict for the :class:`game.models.HexState` constructor, or None.
    """
    import h3

    h3_index = territory.get("h3_index")
    if not h3_index:
        return None
    try:
        center_lat, center_lng = h3.cell_to_latlng(str(h3_index))
    except (ValueError, TypeError) as exc:
        logger.warning("Skipping territory with invalid h3_index %r: %s", h3_index, exc)
        return None
    return {
        "game_id": session_id,
        "h3_index": str(h3_index),
        "tick": tick,
        "county_fips": str(territory.get("county_fips") or ""),
        "county_name": str(territory.get("name") or h3_index)[:100],
        "center_lat": float(center_lat),
        "center_lng": float(center_lng),
        "heat": float(territory.get("heat") or 0.0),
        "pop_total": int(territory.get("population") or 0),
    }


def _persist_hex_state_safe(
    session_id: UUID,
    tick: int,
    serialized_territories: list[dict[str, Any]],
) -> None:
    """Best-effort projection of a tick's territories into ``hex_latest``.

    P0 #7: :meth:`EngineBridge.get_map_snapshot` reads ``hex_latest`` but the
    game loop never wrote it, so the map rendered zero features for every
    real game (only the ``seed_hex_data`` mock-fixture command wrote rows).
    Mirrors :func:`_persist_tick_events_safe`'s never-raise contract, and
    :func:`_persist_action_result`'s Django-ORM write path — Django's
    ``default`` database is the same Postgres the persistence pool points at
    (see :func:`init_persistence`), so an ORM UPSERT lands in the exact table
    the map reader queries. Uses ``bulk_create(update_conflicts=True)`` →
    ``INSERT ... ON CONFLICT (game_id, h3_index) DO UPDATE`` against the
    composite PK (``postgres_schema.py`` ``hex_latest`` DDL); ``hex_latest``
    is a latest-tick cache, so each tick overwrites the previous one in place.

    Args:
        session_id: The game session UUID.
        tick: The tick these rows reflect.
        serialized_territories: ``snapshot["territories"]`` (output of
            :func:`_serialize_territory` per territory).
    """
    if not serialized_territories:
        return
    rows = [
        row
        for t in serialized_territories
        if (row := _hex_state_row(session_id, tick, t)) is not None
    ]
    if not rows:
        return
    try:
        from game.models import HexState

        HexState.objects.bulk_create(
            [HexState(**row) for row in rows],
            update_conflicts=True,
            unique_fields=["game", "h3_index"],
            update_fields=[
                "tick",
                "county_fips",
                "county_name",
                "center_lat",
                "center_lng",
                "heat",
                "pop_total",
            ],
        )
    except Exception:  # noqa: BLE001 — diagnostic; never blocks tick resolution
        logger.exception("Failed to persist hex_latest rows session=%s tick=%d", session_id, tick)


def _game_event_from_tick_event_row(row: dict[str, Any]) -> dict[str, Any]:
    """Convert a persisted ``tick_event`` row into frontend GameEvent shape.

    Spec 092: the inverse of :func:`_tick_event_row` — used by
    ``get_journal_dashboard``/``get_alerts_dashboard`` to present persisted
    history in the same shape the frontend already consumes from
    ``snapshot.events`` (spec 061 FR-012: id/type/tick/severity/title/body/data).

    Args:
        row: A ``tick_event`` row dict (from ``query_session_events`` or
            ``query_tick_events``).

    Returns:
        Dict matching the frontend ``GameEvent`` TypeScript interface.
    """
    event_type = str(row.get("event_type", ""))
    detail = row.get("detail")
    data = detail if isinstance(detail, dict) else {}
    severity = row.get("severity") or _classify_event(event_type)
    return {
        # Spec-092 review (cheap minor, documented not aligned): this is
        # NOT the same id as the deterministic UUID5 :func:`_serialize_event`
        # computes for the live per-tick snapshot (over session/tick/
        # event_type/data). The tick_event table has no column to persist
        # that UUID5 — only the SQL-native `event_id SERIAL` — so the
        # journal/alerts read path reconstructs a different, but still
        # stable-per-row, id from the composite PK instead. The two id
        # schemes never collide in the same render today (EventLogPage only
        # reads the journal path; TickResolutionPage renders live-snapshot
        # events and persisted alerts in separate steps keyed by step
        # label, not event id), so this is a latent inconsistency, not a
        # live bug. A real fix would add a `uuid5_id` column to tick_event
        # and thread it through `_tick_event_row`; deferred as a bigger
        # lift than this pass's scope.
        "id": f"{row.get('game_id')}-{row.get('tick')}-{row.get('event_id')}",
        "type": event_type,
        "tick": int(row.get("tick", 0)),
        "severity": severity,
        "title": _humanize_event_type(event_type),
        "body": row.get("summary") or "",
        "data": data,
    }


def _serialize_entity(e: Any) -> dict[str, Any]:
    """Serialize a SocialClass entity with all visualization-relevant fields."""
    ideology = e.ideology
    return {
        "id": e.id,
        "name": e.name,
        "role": _enum_val(e.role),
        "wealth": float(e.wealth),
        "consciousness": float(ideology.class_consciousness),
        "national_identity": float(ideology.national_identity),
        "agitation": float(ideology.agitation),
        "organization": float(e.organization),
        "repression": float(e.repression_faced),
        "p_acquiescence": float(e.p_acquiescence),
        "p_revolution": float(e.p_revolution),
        "subsistence": float(e.subsistence_threshold),
        "population": e.population,
        "inequality": float(e.inequality),
        "active": e.active,
    }


def _serialize_territory(t: Any) -> dict[str, Any]:
    """Serialize a Territory with all visualization-relevant fields.

    Spec 061 US6 FR-013 (T095): also emits ``consciousness`` /
    ``solidarity`` / ``wealth`` / ``dominant_community`` derived
    aggregates. The engine Territory model does not yet carry these
    directly; defaults are 0.0 / "" until US6-followup persistence
    queries (T095 detailed implementation) land. The frontend can
    distinguish "no data yet" (0.0/"") from "real zero" via the
    presence/absence of dominant_community.
    """
    return {
        "id": t.id,
        "name": t.name,
        "h3_index": t.h3_index,
        "h3_resolution": getattr(t, "h3_resolution", 7),
        "county_fips": getattr(t, "county_fips", ""),
        "heat": float(t.heat),
        "sector_type": _enum_val(t.sector_type),
        "territory_type": _enum_val(t.territory_type),
        "profile": _enum_val(t.profile),
        "rent_level": float(t.rent_level),
        "population": t.population,
        "under_eviction": t.under_eviction,
        "biocapacity": float(t.biocapacity),
        "host_id": t.host_id,
        "occupant_id": t.occupant_id,
        "consciousness": float(getattr(t, "consciousness", 0.0)),
        "solidarity": float(getattr(t, "solidarity", 0.0)),
        "wealth": float(getattr(t, "wealth", 0.0)),
        "dominant_community": str(getattr(t, "dominant_community", "") or ""),
    }


_OODA_PHASE_ORDER: tuple[str, ...] = ("observe", "orient", "decide", "act")


def _derive_ooda_phase(profile: dict[str, float]) -> str:
    """Argmax across the four OODA components → enum string (FR-011).

    Deterministic tiebreak by ``_OODA_PHASE_ORDER`` so the same input
    always produces the same phase across replays (Constitution III.7).
    """
    best_phase = "observe"
    best_value = float("-inf")
    for phase in _OODA_PHASE_ORDER:
        value = float(profile.get(phase, 0.0))
        if value > best_value:
            best_value = value
            best_phase = phase
    return best_phase


def _derive_short_name(name: str) -> str:
    """Truncate ``name`` to ≤16 chars for compact UI surfaces (FR-016)."""
    if not name:
        return ""
    if len(name) <= 16:
        return name
    # Truncate-with-ellipsis for visual signal that more name exists.
    return name[:15] + "…"


def _serialize_organization(o: Any) -> dict[str, Any]:
    """Serialize an Organization with all visualization-relevant fields.

    Spec 061 US4 (T067, T068): adds ``short_name`` / ``player_controlled``
    / ``legitimacy`` / ``opacity`` plus ``ooda.phase`` derived enum.

    Note on ``player_controlled``: the engine model does not yet carry an
    explicit ``controlling_player_id`` linking an Organization to a
    Django auth user. Until that link is added by a follow-up spec, we
    fall back on the existing class_character + org_type heuristic that
    also gates VanguardResources attachment — proletarian civil-society
    orgs are treated as player-controlled.

    For player organizations, computes and attaches VanguardResources
    as the ``vanguard`` field.
    """
    name = str(o.name)
    is_player_org = (
        _enum_val(o.class_character) == "proletarian" and _enum_val(o.org_type) == "civil_society"
    )

    # Spec 061 FR-011: surface OODA phase as a deterministic enum.
    ooda_profile: dict[str, float] = {
        "observe": 0.5,
        "orient": 0.5,
        "decide": 0.5,
        "act": 0.5,
        "cycle_ticks": 4,
    }
    engine_profile = getattr(o, "ooda_profile", None) or getattr(o, "ooda", None)
    if engine_profile is not None:
        for phase in _OODA_PHASE_ORDER:
            value = getattr(engine_profile, phase, None)
            if value is not None:
                ooda_profile[phase] = float(value)
    ooda_phase = _derive_ooda_phase(ooda_profile)

    result: dict[str, Any] = {
        "id": o.id,
        "name": name,
        "short_name": _derive_short_name(name),
        "player_controlled": is_player_org,
        "legitimacy": float(getattr(o, "legitimacy", 0.5)),
        "opacity": float(getattr(o, "opacity", 0.5)),
        "org_type": _enum_val(o.org_type),
        "class_character": _enum_val(o.class_character),
        "cohesion": float(o.cohesion),
        "cadre_level": float(o.cadre_level),
        "budget": float(o.budget),
        "heat": float(o.heat),
        "territory_ids": list(o.territory_ids),
        "consciousness_tendency": _enum_val(o.consciousness_tendency),
        "vanguard": None,
        # Stubs preserved from the prior bridge for Spec 052 schema compat.
        # T069 (hyperedge_memberships from XGI) is left empty until the
        # XGI persistence query lands; the frontend treats empty as
        # "no community memberships known" rather than as an error.
        "hyperedge_memberships": [],
        # Spec-109 A5 (III.11): the engine computes no org-level ideology
        # simplex — None over fabricated thirds; the UI renders a loud empty.
        # (The class-level derivation lives in persistence/county_aggregation.)
        "consciousness": None,
        "ooda": {**ooda_profile, "phase": ooda_phase},
    }

    if is_player_org:
        vanguard = VanguardResources.from_organization(
            cadre_level=float(o.cadre_level),
            cohesion=float(o.cohesion),
            budget=float(o.budget),
            heat=float(o.heat),
            territory_count=len(o.territory_ids),
        )
        result["vanguard"] = vanguard.model_dump()

    return result


def _serialize_institution(inst: Any) -> dict[str, Any]:
    """Serialize an Institution with all visualization-relevant fields."""
    balance = inst.internal_balance
    return {
        "id": inst.id,
        "name": inst.name,
        "apparatus_type": _enum_val(inst.apparatus_type),
        "social_function": _enum_val(inst.social_function),
        "class_inscription": _enum_val(inst.class_inscription),
        "legitimacy": float(inst.legitimacy),
        "budget": float(inst.budget),
        "housed_org_ids": list(inst.housed_org_ids),
        "territory_ids": list(inst.territory_ids),
        "factional_composition": {
            "liberal_technocratic": float(balance.liberal_technocratic),
            "revanchist_fascist": float(balance.revanchist_fascist),
            "institutionalist_bonapartist": float(balance.institutionalist_bonapartist),
        },
    }


def _serialize_edge(rel: Any) -> dict[str, Any]:
    """Serialize a Relationship edge.

    Spec 061 US6 FR-014 (T097): also emits ``rate_of_profit`` /
    ``rent_burden`` / ``age_ticks`` when the engine attaches them;
    otherwise emits ``None`` so the frontend can render "n/a".
    Age requires either an engine attribute or an edge_snapshot
    history query (the latter is a US6-followup task; the field
    surfaces as None for now).
    """
    rate_of_profit = getattr(rel, "rate_of_profit", None)
    rent_burden = getattr(rel, "rent_burden", None)
    age_ticks = getattr(rel, "age_ticks", None)
    return {
        "id": f"{rel.source_id}-{rel.target_id}-{_enum_val(rel.edge_type)}",
        "source_id": rel.source_id,
        "target_id": rel.target_id,
        "mode": _enum_val(rel.edge_type),
        "value_flow": float(rel.value_flow),
        "tension": float(rel.tension),
        "repression_flow": float(getattr(rel, "solidarity_strength", 0.0)),
        "rate_of_profit": float(rate_of_profit) if rate_of_profit is not None else None,
        "rent_burden": float(rent_burden) if rent_burden is not None else None,
        "age_ticks": int(age_ticks) if age_ticks is not None else None,
    }


def _state_to_snapshot(state: WorldState, session_id: UUID) -> dict[str, Any]:
    """Convert a WorldState to a JSON-serializable dict for API responses.

    Includes VanguardResources on player orgs and TrapDetection results.

    Args:
        state: The WorldState to serialize.
        session_id: The session UUID to include.

    Returns:
        Flat dict suitable for JSON encoding.
    """
    territories = [_serialize_territory(t) for t in state.territories.values()]
    organizations = [_serialize_organization(o) for o in state.organizations.values()]
    institutions = [_serialize_institution(inst) for inst in state.institutions.values()]
    edges = [_serialize_edge(rel) for rel in state.relationships]
    events_list: list[dict[str, Any]] = [_serialize_event(e, session_id) for e in state.events]

    # Compute trap detection for the session
    traps_dict = _compute_traps(state, session_id)

    snapshot: dict[str, Any] = {
        "session_id": str(session_id),
        "tick": state.tick,
        "organizations": organizations,
        "institutions": institutions,
        "territories": territories,
        "hyperedges": [],
        "edges": edges,
        "events": events_list,
        "derived": {
            "value_tensor": {},
            "imperial_rent": {},
            "dept_iii_visibility": {},
            "class_aggregates": {},
            "economy": state.economy.model_dump() if state.economy else {},
            "predictions": {},
        },
    }

    if traps_dict is not None:
        snapshot["traps"] = traps_dict

    return snapshot


def _compute_traps(state: WorldState, session_id: UUID) -> dict[str, Any] | None:
    """Run trap detection for a session, computing scores from action history.

    Returns None if no player org is found (non-Wayne County scenarios).
    """
    # Find the player org
    player_org = None
    for org in state.organizations.values():
        if (
            _enum_val(org.class_character) == "proletarian"
            and _enum_val(org.org_type) == "civil_society"
        ):
            player_org = org
            break

    if player_org is None:
        return None

    # Compute derived values for trap detection
    history = _session_action_history.get(session_id, [])
    consciousness_avg = sum(
        float(e.ideology.class_consciousness) for e in state.entities.values()
    ) / max(len(state.entities), 1)

    resources = VanguardResources.from_organization(
        cadre_level=float(player_org.cadre_level),
        cohesion=float(player_org.cohesion),
        budget=float(player_org.budget),
        heat=float(player_org.heat),
        territory_count=len(player_org.territory_ids),
    )

    # Count entities trending fascist (national_identity > 0.6)
    fascist_count = sum(
        1 for e in state.entities.values() if float(e.ideology.national_identity) > 0.6
    )

    previous_result = _session_trap_state.get(session_id)

    result = detect_traps(
        action_history=history,
        org_budget=float(player_org.budget),
        org_cadre=float(player_org.cadre_level),
        org_cohesion=float(player_org.cohesion),
        org_heat=float(player_org.heat),
        sympathizer_labor=float(resources.sympathizer_labor),
        territory_count=len(player_org.territory_ids),
        consciousness_avg=consciousness_avg,
        tick=state.tick,
        fascist_entities=fascist_count,
        total_entities=len(state.entities),
        previous_result=previous_result,
    )

    # Persist trap state for next tick
    _session_trap_state[session_id] = result

    return result.model_dump()


def _mark_resolved_safe(persistence: RuntimePersistence, session_id: UUID, tick: int) -> None:
    """Mark turns as resolved if the persistence layer supports it."""
    mark_fn = getattr(persistence, "mark_turns_resolved", None)
    if mark_fn is not None:
        mark_fn(session_id=session_id, tick=tick)


def _preview_consciousness_delta(
    org_data: dict[str, Any],
    target_id: str,
    action_type: ActionType,
    graph: BabylonGraph,
) -> float:
    """Read-only CI estimate for the preview, via the resolvers' own math.

    Calls :func:`babylon.ooda.action_effects.compute_consciousness_delta` (pure,
    no mutation) so ``preview_action`` reports the same collective-identity delta
    the EDUCATE / CAMPAIGN / AID resolvers would produce.

    Args:
        org_data: Acting org node attributes (live payload; not mutated).
        target_id: Target community/entity id.
        action_type: The mapped engine ActionType.
        graph: World graph (read-only).

    Returns:
        The estimated collective-identity delta, or 0.0 when the action has no
        consciousness effect.
    """
    from babylon.ooda.action_effects import compute_consciousness_delta

    defines = GameDefines()
    delta = compute_consciousness_delta(
        org_data, target_id, action_type, graph, defines.ooda, defines.organization
    )
    return float(delta.collective_identity_delta) if delta is not None else 0.0


def _index_engine_action_results(
    persistent_context: dict[str, Any] | None,
) -> dict[str, list[dict[str, Any]]]:
    """Group the engine's TurnResolution action results by acting org id.

    Reads ``persistent_context["turn_resolution"]["action_phase_results"]``
    (published by :class:`~babylon.engine.systems.ooda.OODASystem`) and buckets
    the per-action result dicts by ``action.org_id`` so ``resolve_tick`` can
    pair each pending player action with its real engine result.

    Args:
        persistent_context: The cross-tick context after ``step`` synced the
            engine's ``context.persistent_data`` back into it.

    Returns:
        Mapping of org id to its list of engine result dicts (execution order).
    """
    resolution = (persistent_context or {}).get("turn_resolution") or {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for result in resolution.get("action_phase_results", []):
        org_id = result.get("action", {}).get("org_id")
        if org_id is not None:
            grouped.setdefault(org_id, []).append(result)
    return grouped


def _pop_engine_result(
    results_by_org: dict[str, list[dict[str, Any]]], org_id: str
) -> dict[str, Any] | None:
    """Pop the next (FIFO) engine result for ``org_id``, or None if exhausted."""
    queue = results_by_org.get(org_id)
    if not queue:
        return None
    return queue.pop(0)


def _engine_result_fields(
    engine_result: dict[str, Any] | None,
) -> tuple[bool, str | None, float, dict[str, Any]]:
    """Extract (success, failure_reason, ci_delta, direct_effects) from a result.

    Args:
        engine_result: A single ``action_phase_results`` entry (JSON-dumped
            :class:`~babylon.ooda.types.ActionResult`), or None when the engine
            produced no result for the org (a loud, persisted failure).

    Returns:
        Tuple of success flag, failure reason (or None), the collective-identity
        delta (0.0 when there is no consciousness effect), and the direct effects.
    """
    if engine_result is None:
        return False, "action not resolved by engine", 0.0, {}
    success = bool(engine_result.get("success", False))
    failure_reason = engine_result.get("failure_reason")
    ci = engine_result.get("consciousness_delta")
    ci_delta = float(ci["collective_identity_delta"]) if ci else 0.0
    direct_effects = engine_result.get("direct_effects") or {}
    return success, failure_reason, ci_delta, direct_effects


def _persist_action_result(persistence: RuntimePersistence, result_data: dict[str, Any]) -> None:
    """Write an ActionResult record via persistence layer or Django ORM.

    Tries ``persist_action_result()`` on the persistence layer first.
    Falls back to Django ORM ``ActionResult.objects.create()`` if unavailable.

    Args:
        persistence: The RuntimePersistence instance.
        result_data: Dict with ActionResult fields.
    """
    persist_fn = getattr(persistence, "persist_action_result", None)
    if persist_fn is not None:
        persist_fn(**result_data)
    else:
        # Fallback: use Django ORM
        try:
            from game.models import ActionResult

            ActionResult.objects.create(**result_data)
        except Exception as exc:
            logger.warning("Failed to persist action result: %s", exc)


# ---------------------------------------------------------------------- #
# Persistence initialization (called from apps.py to preserve boundary)
# ---------------------------------------------------------------------- #

# Module-level pool reference to keep the connection pool alive
_pool: Any = None


def init_persistence(db_config: dict[str, Any]) -> RuntimePersistence:
    """Create a PostgresRuntime persistence layer from Django DB settings.

    This function encapsulates all engine/persistence imports so that
    ``apps.py`` never imports from ``babylon.*`` directly.

    Args:
        db_config: Django DATABASES["default"] dict with HOST, PORT, etc.

    Returns:
        A RuntimePersistence instance backed by PostgreSQL.
    """
    global _pool  # noqa: PLW0603

    from psycopg_pool import ConnectionPool

    from babylon.persistence.postgres_runtime import PostgresRuntime

    host = str(db_config.get("HOST", "localhost"))
    port = str(db_config.get("PORT", "5432"))
    name = str(db_config.get("NAME", "babylon"))
    user = str(db_config.get("USER", "babylon"))
    password = str(db_config.get("PASSWORD", "babylon"))
    conninfo = f"host={host} port={port} dbname={name} user={user} password={password}"

    _pool = ConnectionPool(conninfo=conninfo, min_size=1, max_size=4, timeout=10)
    persistence = PostgresRuntime(_pool)
    try:
        persistence.init_schema()
    except Exception as exc:
        logger.warning("PostgreSQL schema init had non-fatal error: %s", exc)

    return persistence
