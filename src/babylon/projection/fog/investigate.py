"""INVESTIGATE intel wiring — snapshot writer + ledger reader (WO-40).

The engine's ``resolve_investigate`` names WHICH fields were revealed
(``direct_effects["revealed"]`` — field names only) but carries no VALUES.
The write side here supplies them: reading the live post-tick graph at the
moment the resolver's result is in scope, so the captured snapshot is the
TRUE value as of this tick, frozen forever after — never recomputed at a
later fog read (that distinction is the whole point of the staleness /
quantization tiers, see :class:`~babylon.projection.fog.ledger.IntelEntry`).

The read side folds persisted ``action_result`` rows back into an
:class:`~babylon.projection.fog.ledger.IntelLedger` — deterministic and
replayable: a worker restart reconstructs the exact same ledger a live
process would have. Rows lacking the intel detail keys are skipped, never
fabricated into entries (Constitution III.11).

Ported from the legacy bridge's ``_investigate_field_snapshot`` /
``_derive_intel_ledger`` (WO-40); the persisted detail-key names are a
cross-process contract with rows the legacy bridge already wrote.
"""

from __future__ import annotations

from typing import Any

from babylon.models.enums import ActionType
from babylon.projection.fog.filter import political_field_group
from babylon.projection.fog.ledger import IntelLedger, ledger_from_events
from babylon.topology import BabylonGraph

#: Persisted ``action_result.details`` keys — a cross-process contract:
#: the legacy bridge wrote these exact names; the Archive reader folds rows
#: either side wrote.
INTEL_FIELD_GROUP_KEY: str = "intel_field_group"
INTEL_VALUE_SNAPSHOT_KEY: str = "intel_value_snapshot"


def investigate_field_snapshot(
    action_type_enum: ActionType | None,
    target_id: str | None,
    direct_effects: dict[str, Any],
    graph: BabylonGraph,
) -> dict[str, Any] | None:
    """Freeze the true post-tick values a successful INVESTIGATE revealed.

    :param action_type_enum: The resolved action's type, or ``None``
        (unrecognized verb).
    :param target_id: The action's target node id.
    :param direct_effects: ``ActionResult.direct_effects``
        (``{"scan_type": ..., "revealed": {target_id: [...]}}`` on success).
    :param graph: The post-tick graph.
    :returns: ``{"field_group": ..., "value_snapshot": ...}`` ready to
        stash onto the persisted row, or ``None`` for any other action, a
        failed INVESTIGATE, a since-removed target, or revealed fields the
        node does not carry — no fabricated entry, ever (III.11).
    """
    if action_type_enum is not ActionType.MAP_NETWORK or not target_id:
        return None
    revealed_by_target = direct_effects.get("revealed")
    if not isinstance(revealed_by_target, dict):
        return None
    fields = revealed_by_target.get(target_id)
    if not fields or target_id not in graph.nodes:
        return None
    node_data = graph.nodes[target_id]
    node_type = node_data.get("_node_type")
    if not node_type:
        return None
    value_snapshot = {field: node_data[field] for field in fields if field in node_data}
    if not value_snapshot:
        return None
    return {
        "field_group": political_field_group(str(node_type)),
        "value_snapshot": value_snapshot,
    }


def stash_intel_details(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Map a snapshot onto the persisted ``details`` keys.

    :param snapshot: A non-``None`` :func:`investigate_field_snapshot` result.
    :returns: The details fragment to merge onto the ``action_result`` row.
    """
    return {
        INTEL_FIELD_GROUP_KEY: snapshot["field_group"],
        INTEL_VALUE_SNAPSHOT_KEY: snapshot["value_snapshot"],
    }


def derive_intel_ledger(rows: list[dict[str, Any]]) -> IntelLedger:
    """Fold persisted ``action_result`` rows into the session's ledger.

    :param rows: INVESTIGATE ``action_result`` rows (each carrying ``tick``,
        ``target_id`` and a ``details`` dict) — the caller owns the query;
        this fold owns the shape.
    :returns: The reconstructed ledger — zero entries for a fresh session
        or one with no recoverable INVESTIGATE history.
    """
    ledger_rows: list[dict[str, Any]] = []
    for row in rows:
        details = row.get("details") or {}
        field_group = details.get(INTEL_FIELD_GROUP_KEY)
        value_snapshot = details.get(INTEL_VALUE_SNAPSHOT_KEY)
        if not field_group or not value_snapshot:
            continue
        ledger_rows.append(
            {
                "tick": row.get("tick"),
                "target_id": row.get("target_id"),
                "field_group": field_group,
                "value_snapshot": value_snapshot,
            }
        )
    return ledger_from_events(ledger_rows)
