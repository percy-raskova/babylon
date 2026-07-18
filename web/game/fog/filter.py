"""Track 1 / Task 4 (2026-07-18): ``apply_fog`` — the fog filter itself.

The two-layer model from the spec (spec-117 §5a): the MATERIAL layer
(production, wages, rent, demographics, territory) is public record —
always visible, never gated. The POLITICAL layer (:data:`POLITICAL_FIELDS`)
is visible only within organizing reach, or through a session
:class:`~game.fog.ledger.IntelLedger` entry, which itself ages exact ->
approximate -> unknown per :func:`game.fog.ledger.read_intel` — this module
calls that function rather than re-deriving its aging rule.

Mirrors ``engine_bridge._apply_class_vision_gate``'s three-tier shape
(desert/mud/water -> masked/approximate/exact) generalized to any node
type/payload, rather than social_class specifically. Deliberately kept as a
SEPARATE gate for now (not folded into ``_apply_class_vision_gate``) — see
this module's own assessment in the Track 1 Task 4 report; running both
gates on one payload is flagged as a future correctness hazard, not
resolved here.

**Signature note.** The plan's stub reads
``apply_fog(payload, node_type, node_id, reach, ledger, tick) -> dict``.
This implementation adds two REQUIRED keyword-only parameters,
``staleness_ticks``/``unknown_ticks`` — :func:`~game.fog.ledger.read_intel`
needs them, and the "no hardcoded coefficients" constraint means they must
come from the caller (``GameDefines.epistemic_horizon.intel_staleness_ticks``/
``intel_unknown_ticks``), not be invented here. Everything else about the
six-argument shape (and the purity/determinism contract it implies) is
unchanged.

**Import-boundary note.** Like :mod:`game.fog.reach` and
:mod:`game.fog.ledger`, this module imports nothing from ``babylon.*`` and
nothing from ``game.engine_bridge`` — ``engine_bridge.py`` imports THIS
module, never the reverse (``tests/unit/web/test_import_boundary.py``).
"""

from __future__ import annotations

from typing import Any

from .ledger import IntelLedger, read_intel

#: The political field set gated by this filter, from the Track 1 grounding
#: audit. ``heat``/``consciousness``/``solidarity``/``dominant_community``
#: are the four verified against ``_serialize_territory`` (the last three
#: hardcoded ``None`` TODAY — see ``TestAccidentalNullFieldsGetGatedOnceReal``
#: in ``tests/unit/web/fog/test_filter.py``, which pins that this gate
#: already covers them once a real value arrives, so nobody has to
#: remember to add the gate later). ``agitation``/``solidarity_index``/
#: ``dominant_class`` are the same names Task 5's hex-rollup pipeline
#: (``_hex_feature_properties``/``_aggregate_hex_features``) will reuse this
#: constant for — not exercised on any Task-4 surface today, since they
#: appear there only inside that pipeline or inside the already-gated
#: class-vision payload, never on ``_serialize_territory``/``get_inspector_*``
#: directly (see the Task 4 report for the grep evidence). ``colonial_stance``
#: is this module's resolved reading of the plan's "faction stances" entry —
#: the only literal stance-shaped field found on an in-scope surface
#: (``get_inspector_node``'s generic/raw-dump branch, for ``_node_type ==
#: "faction"`` nodes); flagged in the report as an interpretation call, not
#: a certainty.
POLITICAL_FIELDS: tuple[str, ...] = (
    "heat",
    "agitation",
    "solidarity_index",
    "dominant_class",
    "consciousness",
    "solidarity",
    "dominant_community",
    "colonial_stance",
)

#: Track 1 / Task 5 §B (owner-level ruling, 2026-07-18): an organization's
#: EXISTENCE, public activity, and territorial presence are material (public
#: record — always visible, never gated: not touched by this module at
#: all). Its INTERNAL state is political, gated for every NON-PLAYER org
#: (the player's own org stays fully visible — see ``engine_bridge``'s
#: explicit ``is_player_org`` bypass at each org-payload call site, not a
#: rule enforced here). These three are net-new; ``heat`` (already in
#: :data:`POLITICAL_FIELDS`) is the fourth org-internal field the ruling
#: names — shared with territory heat, not duplicated.
ORG_INTERNAL_STATE_FIELDS: tuple[str, ...] = (
    "consciousness_tendency",
    "cohesion",
    "cadre_level",
)

#: The full political field set for an ORGANIZATION payload: the shared
#: :data:`POLITICAL_FIELDS` union :data:`ORG_INTERNAL_STATE_FIELDS`. ONE
#: source of truth — an org composer passes THIS to :func:`apply_fog`'s
#: ``political_fields`` argument, never a second, independently-copied
#: field list.
ORG_POLITICAL_FIELDS: tuple[str, ...] = POLITICAL_FIELDS + ORG_INTERNAL_STATE_FIELDS


def apply_fog(
    payload: dict[str, Any],
    node_type: str,
    node_id: str,
    reach: frozenset[str],
    ledger: IntelLedger,
    tick: int,
    *,
    staleness_ticks: int,
    unknown_ticks: int,
    political_fields: tuple[str, ...] = POLITICAL_FIELDS,
) -> dict[str, Any]:
    """Redact the political layer of ``payload`` outside organizing reach.

    A NEW dict is always returned — ``payload`` is never mutated (callers
    that need the original untouched, e.g. internal persistence paths that
    must keep writing TRUE state, simply don't call this function on that
    copy). Only names in :data:`POLITICAL_FIELDS` that are actually present
    as keys in ``payload`` are ever touched — a field the caller's composer
    never produced is never invented (Constitution III.11), and the whole
    MATERIAL remainder of ``payload`` passes through byte-identical.

    Precedence, evaluated per call (not per field — one ``node_id`` gets
    one verdict):

    1. **Reach wins outright.** ``node_id in reach`` -> every political
       field already in ``payload`` is left exact, ``vision_masked``/
       ``vision_approx`` are both set to ``[]`` (present but empty, not
       omitted — unlike ``_apply_class_vision_gate``'s "water" tier, which
       leaves them off entirely; this filter always emits both keys so a
       caller never has to branch on their absence).
    2. **Otherwise, read the ledger once** — ``field_group=f"{node_type}:
       political"`` (one aging clock for this node's whole political
       family, mirroring :class:`~game.fog.ledger.IntelEntry`'s own
       "several related fields, one clock" design) via
       :func:`~game.fog.ledger.read_intel`. Its tier governs each field
       INDIVIDUALLY:

       * ``"exact"`` or ``"approximate"`` AND the field is a key in the
         reading's ``value_snapshot`` -> use that snapshot value verbatim
         (exact) or as :func:`~game.fog.ledger.read_intel` already
         quantized it (approximate, appended to ``vision_approx``). This
         is the ledger's OWN recorded observation, which may differ from
         ``payload``'s live value — that is correct: it is what the
         player org actually knows, not the current truth.
       * Any other case (tier ``"unknown"``, or a tier that doesn't cover
         this particular field — one INVESTIGATE resolution need not
         observe every political field at once) -> masked to ``None`` and
         appended to ``vision_masked``, UNLESS the field already held
         ``None`` in ``payload`` (honest pre-existing absence is not the
         same as data this filter withheld — mirrors
         ``_apply_class_vision_gate``'s identical rule).

    Args:
        payload: The composer's built dict (e.g. ``_serialize_territory``'s
            or ``get_inspector_org``'s return value).
        node_type: The node's ``_node_type`` string (e.g. ``"territory"``,
            ``"organization"``) — scopes the ledger's ``field_group`` so
            different node types never collide on one aging clock.
        node_id: The node's graph id.
        reach: :func:`game.fog.reach.organizing_reach`'s result for this
            session.
        ledger: The session's :class:`~game.fog.ledger.IntelLedger`.
        tick: The current simulation tick (fed to
            :func:`~game.fog.ledger.read_intel`).
        staleness_ticks: ``GameDefines.epistemic_horizon.intel_staleness_ticks``.
        unknown_ticks: ``GameDefines.epistemic_horizon.intel_unknown_ticks``.
        political_fields: The field set this call gates — defaults to
            :data:`POLITICAL_FIELDS` (territory/generic-node shape). Track 1
            / Task 5 §B: an organization composer passes
            :data:`ORG_POLITICAL_FIELDS` instead, so an org's internal-state
            fields (``consciousness_tendency``/``cohesion``/``cadre_level``,
            plus the shared ``heat``) are gated the same way, through the
            SAME gate, rather than a forked field list or a second function.

    Returns:
        A new dict — ``payload`` plus a gated political layer plus
        ``vision_masked``/``vision_approx`` (always both present).
    """
    result = dict(payload)

    if node_id in reach:
        result["vision_masked"] = []
        result["vision_approx"] = []
        return result

    reading = read_intel(
        ledger,
        node_id,
        f"{node_type}:political",
        tick,
        staleness_ticks=staleness_ticks,
        unknown_ticks=unknown_ticks,
    )

    masked: list[str] = []
    approx: list[str] = []
    for field in political_fields:
        if field not in result:
            continue

        snapshot = reading.value_snapshot
        if reading.tier == "exact" and snapshot is not None and field in snapshot:
            result[field] = snapshot[field]
            continue
        if reading.tier == "approximate" and snapshot is not None and field in snapshot:
            result[field] = snapshot[field]
            approx.append(field)
            continue

        if result[field] is not None:
            result[field] = None
            masked.append(field)

    result["vision_masked"] = masked
    result["vision_approx"] = approx
    return result


__all__ = [
    "ORG_INTERNAL_STATE_FIELDS",
    "ORG_POLITICAL_FIELDS",
    "POLITICAL_FIELDS",
    "apply_fog",
]
