#!/usr/bin/env python3
"""The Community @6.0 port train's frozen-mirror oracle (issue #667, plan
docs/superpowers/plans/2026-08-18-community-port.md §9 — the D146/ADR183
convention).

STANDALONE. No `babylon` import, no pytest, no third-party anything. It
transcribes the RULES' binding order and collect-then-apply semantics
term-for-term over the literal WORLD dict below — which matches
`community-conformance.bscn` node-for-node, hyperedge-for-hyperedge,
seed-for-seed — never the frozen engine's code (the frozen engine is
EVIDENCE, captured separately in
reports/community-frozen-corroboration-2026-08-18.md; it prints frozen's
own, sometimes-diverged answer — D-NF+3's summation order and D-NF+5's
500-org cap live there).

Per §9, this header states, for this pack specifically:

1. THE EXACT RULE ORDER: c00 → c01 → c02 → c03r → c03l → c03f → c04 → c05
   → c06 → c07 → c08 → c09 → c10 → c11. Each rule applies ALL of its
   writes before the next rule reads (§8b's D116 ledger — the cross-rule
   reads this pack relies on, fatal rows included).
2. PRE-STATE WITHIN A RULE: a rule's for-each accumulations are COLLECTED
   against the rule-entry state and APPLIED in ascending order only after
   the whole subject population has collected — so c01's `add 1`s against
   one hyperedge never observe each other mid-rule (§4.2 chapter C4).
3. THE EXACT f64 OPERATION ORDER: every accumulator sums
   subject-ascending (NodeId) outer, ascending HyperedgeId inner (D25);
   c10's PRODUCT compounds in ascending HyperedgeId order — D-NF+13's
   multiplication-order divergence lives exactly there.
4. THE FLOOR-DISPATCH ARM each seeded community takes (ADR214 provenance):
   h0 NEW_AFRIKAN → 0.136 (measured, unrestricted_3218, erratum 9);
   h1 SETTLER → 0.0 (identically zero by construction); h2 QUEER → 0.04
   (unchanged, confidence demoted per Ruling 2). In world 1 NO arm binds
   (every normalized r clears its floor) — the binding case is world 2's,
   Task 9.
5. UNWRITTEN FIELDS, PER NODE: n5 (inactive-member) holds a REAL
   membership in h0 but is inactive (frozen community.py:472-474), so c09
   never resets and c10 never accumulates its `community-cost-modifier` —
   the mirror models that field as ABSENT (the key does not exist), never
   as 1.0, so the Rust assertion reads the substrate's honest-null error
   (§1.4, C4). A mirror that defaults an unwritten field is a mirror that
   cannot catch a fabricated write.

c07/c08 are DG-2-GATED (the Director question is unresolved at authoring):
transcribed and printed here because the mirror is the oracle and the
values cost nothing — their .bsl RULES do not land while the gate holds.
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------
# The literal world — community-conformance.bscn, transcribed.
# Nodes in declaration order (id order); hyperedges in their own order.
# ---------------------------------------------------------------------

# (name → fields); active classes only drive the census/cost lanes.
NODES: list[dict[str, object]] = [
    # n0 — the §3.7a singleton carrier.
    {"name": "community-register", "type": "INSTITUTION", "community-carrier": 1},
    {"name": "na-worker", "type": "SOCIAL_CLASS", "active": 1},
    {"name": "na-organizer", "type": "SOCIAL_CLASS", "active": 1},
    {"name": "settler-la", "type": "SOCIAL_CLASS", "active": 1},
    {"name": "unaffiliated", "type": "SOCIAL_CLASS", "active": 1},
    {"name": "inactive-member", "type": "SOCIAL_CLASS", "active": 0},
    # n6 — REVOLUTIONARY; MEMBERSHIP → n1, n2.
    {
        "name": "rev-org",
        "type": "ORGANIZATION",
        "cadre-level": 0.5,
        "cohesion": 0.8,
        "tendency": "REVOLUTIONARY",
    },
    # n7 — LIBERAL; MEMBERSHIP → n1, n3.
    {
        "name": "lib-org",
        "type": "ORGANIZATION",
        "cadre-level": 0.25,
        "cohesion": 0.5,
        "tendency": "LIBERAL",
    },
    # n8 — FASCIST; MEMBERSHIP → n3.
    {
        "name": "fash-org",
        "type": "ORGANIZATION",
        "cadre-level": 0.5,
        "cohesion": 0.25,
        "tendency": "FASCIST",
    },
    # n9 — zero MEMBERSHIP edges (frozen's :421 skip).
    {
        "name": "no-member-org",
        "type": "ORGANIZATION",
        "cadre-level": 1.0,
        "cohesion": 1.0,
        "tendency": "REVOLUTIONARY",
    },
]

# (source_name, target_name) — the five MEMBERSHIP edges, declaration order.
MEMBERSHIP_EDGES: list[tuple[str, str]] = [
    ("rev-org", "na-worker"),
    ("rev-org", "na-organizer"),
    ("lib-org", "na-worker"),
    ("lib-org", "settler-la"),
    ("fash-org", "settler-la"),
]

HYPEREDGES: list[dict[str, object]] = [
    # h0 — NEW_AFRIKAN over (n1, n2, n5); n5's membership is real but inactive.
    {
        "name": "new-afrikan",
        "kind": "NEW_AFRIKAN",
        "members": ["na-worker", "na-organizer", "inactive-member"],
        "heat": 0.5,
        "cohesion": 0.75,
        "education-pressure": 0.25,
        "reproduction-cost-modifier": 0.875,
        "revolutionary": 0.5,
        "liberal": 0.25,
        "fascist": 0.25,
    },
    # h1 — SETTLER over (n3). The 0.0-floor control.
    {
        "name": "settler",
        "kind": "SETTLER",
        "members": ["settler-la"],
        "heat": 0.25,
        "cohesion": 0.5,
        "education-pressure": 0.125,
        "reproduction-cost-modifier": 1.0,
        "revolutionary": 0.0,
        "liberal": 0.75,
        "fascist": 0.25,
    },
    # h2 — QUEER over (n1).
    {
        "name": "queer",
        "kind": "QUEER",
        "members": ["na-worker"],
        "heat": 0.75,
        "cohesion": 0.625,
        "education-pressure": 0.5,
        "reproduction-cost-modifier": 1.25,
        "revolutionary": 0.25,
        "liberal": 0.5,
        "fascist": 0.25,
    },
]

# The ADR214 floor table (§6.1 verbatim; 14 rows, frozen declaration order).
FLOOR: dict[str, float] = {
    "SETTLER": 0.0,  # by construction — the settler pole IS the norm
    "PATRIARCHAL": 0.0,  # structural: hegemonic default
    "NEW_AFRIKAN": 0.136,  # measured, unrestricted_3218 (erratum 9)
    "FIRST_NATIONS": 0.155,  # measured (Ruling 3: breaks the frozen tie)
    "CHICANO": 0.113,  # measured
    "WOMEN": 0.04,  # unchanged, confidence demoted (Ruling 2)
    "TRANS": 0.06,  # unchanged, demoted
    "DISABLED": 0.03,  # unchanged, demoted
    "QUEER": 0.04,  # unchanged, demoted
    "UNDOCUMENTED": 0.10,  # unchanged, demoted
    "INCARCERATED": 0.18,  # unchanged — unreachable from B17001 by principle
    "YOUTH": 0.0,  # structural: lifecycle
    "ADULT": 0.0,  # structural: lifecycle
    "ELDER": 0.02,  # estimated (generational memory)
}

HEAT_DECAY_ALPHA = 0.05  # organizations.py:22-27
COHESION_DECAY_ALPHA = 0.03  # organizations.py:28-33
EDUCATION_PRESSURE_DECAY = 0.1  # consciousness.py:138-143

NAME_TO_NODE: dict[str, int] = {str(n["name"]): i for i, n in enumerate(NODES)}


def census(comms: list[dict[str, float]]) -> None:
    """c00 → c01, in rule order (the reset and the member census)."""

    # ---- c00-census-reset (carrier): the accumulators were seeded above
    # at 0 — this rule's writes are exactly those zeros; the collect pass
    # writes them over any prior tick (world 1 runs one tick, so the reset
    # is the identity here and STILL transcribed, because Task 12's
    # multi-tick worlds need the order visible). ----
    for c in comms:  # ascending HyperedgeId
        c["member-count"] = 0.0
        c["r-raw"] = 0.0
        c["l-raw"] = 0.0
        c["f-raw"] = 0.0
        c["density-sum"] = 0.0

    # ---- c01-member-census (social-class, active only) ----
    # Pre-state law: every `add 1` collects against the c00-reset state;
    # the count lands as the SET of memberships, summed — subject-ascending
    # outer, ascending HyperedgeId inner (the writes commute, being +1s,
    # but the ORDER is stated because D-NF+13 says order is never free).
    census_pending: list[int] = [0] * len(comms)
    for node in NODES:  # ascending declaration order
        if node["type"] != "SOCIAL_CLASS" or node.get("active") != 1:
            continue
        for hid, h in enumerate(HYPEREDGES):  # ascending HyperedgeId
            if node["name"] in h["members"]:
                census_pending[hid] += 1
    for hid, n in enumerate(census_pending):
        comms[hid]["member-count"] += float(n)


def org_weights_and_contributions(
    comms: list[dict[str, float]],
) -> dict[int, dict[str, float]]:
    """c02 → c03r → c03l → c03f → c04, in rule order."""
    # Per-class org accumulators (c02 mints them at 0 each tick).
    class_weights: dict[int, dict[str, float]] = {}

    # ---- c02-org-weight-reset (social-class): mint the four zeros ----
    for nid, node in enumerate(NODES):
        if node["type"] == "SOCIAL_CLASS":
            class_weights[nid] = {
                "org-r-weight": 0.0,
                "org-l-weight": 0.0,
                "org-f-weight": 0.0,
                "org-count": 0.0,
            }

    # ---- c03r / c03l / c03f (organization; the three-rule partition) ----
    # For each tendency rule in order: subjects ascending NodeId, for-each
    # (neighbors self MEMBERSHIP :out SOCIAL_CLASS) — MEMBERSHIP_EDGES is
    # declaration-ordered, and each org's targets are ascending by
    # construction. Each push: weight += cadre × cohesion; count += 1.
    # Rule-id byte order is the execution order (D16), so the tick runs
    # c03f → c03l → c03r — NOT the plan table's reading order. Transcribed
    # in the TRUE order; the result is order-insensitive (disjoint weight
    # fields; the shared org-count is integer-exact additive), which the
    # unchanged output proves.
    for tendency in ("FASCIST", "LIBERAL", "REVOLUTIONARY"):
        key = {
            "REVOLUTIONARY": "org-r-weight",
            "LIBERAL": "org-l-weight",
            "FASCIST": "org-f-weight",
        }[tendency]
        for node in NODES:
            if node["type"] != "ORGANIZATION" or node["tendency"] != tendency:
                continue
            push = float(node["cadre-level"]) * float(node["cohesion"])
            for src, tgt in MEMBERSHIP_EDGES:
                if src != node["name"]:
                    continue
                class_weights[NAME_TO_NODE[tgt]][key] += push
                class_weights[NAME_TO_NODE[tgt]]["org-count"] += 1.0

    # ---- c04-community-contribution-push (social-class, ACTIVE ONLY) ----
    # For each active class (ascending), for each of its hyperedges
    # (ascending): r-raw += org-r-weight / member-count (l, f likewise),
    # and density-sum += org-count / member-count. The active gate is
    # FIDELITY: frozen's community_agents is built from the active-only
    # membership set (community.py:472-474 -> :392-397), so an inactive
    # class's org weights never enter the sum. (In world 1 the gate changes
    # no output: n5's weights are exact zeros either way.)
    for nid, node in enumerate(NODES):
        if node["type"] != "SOCIAL_CLASS" or node.get("active") != 1:
            continue
        w = class_weights[nid]
        for hid, h in enumerate(HYPEREDGES):
            if node["name"] not in h["members"]:
                continue
            divisor = comms[hid]["member-count"]
            comms[hid]["r-raw"] += w["org-r-weight"] / divisor
            comms[hid]["l-raw"] += w["org-l-weight"] / divisor
            comms[hid]["f-raw"] += w["org-f-weight"] / divisor
            comms[hid]["density-sum"] += w["org-count"] / divisor

    return class_weights


def readout(comms: list[dict[str, float]]) -> None:
    """c05 → c06 → c07 → c08, in rule order (c07/c08 DG-2-gated)."""
    # ---- c05-normalize (carrier) — the density-sum > 0 skip gate ----
    # unorganized = max(0, 1 − density-sum) folded into l-raw; total =
    # r+l+f; degenerate (total < 1e-10) → (0, 1, 0) AND NOTHING ELSE (the
    # floor routes through c06, bit-identically — §6.2 I5).
    for _hid, c in enumerate(comms):
        if not c["density-sum"] > 0.0:
            continue  # no-org skip gate: the prior ternary is preserved
        unorganized = max(0.0, 1.0 - c["density-sum"])
        l_raw = c["l-raw"] + unorganized
        total = c["r-raw"] + l_raw + c["f-raw"]
        if total < 1e-10:
            c["revolutionary"], c["liberal"], c["fascist"] = 0.0, 1.0, 0.0
        else:
            c["revolutionary"] = c["r-raw"] / total
            c["liberal"] = l_raw / total
            c["fascist"] = c["f-raw"] / total

    # ---- c06-substrate-floor (carrier) — the pack's ONLY 14-arm dispatch
    # (a dict here: the mirror transcribes SEMANTICS; the .bsl arm chain is
    # the language's only lookup shape, §6.2). The r < floor redistribution
    # with its lf > 1e-10 two-arm split (formulas/consciousness.py:98-107).
    for hid, c in enumerate(comms):
        if not c["density-sum"] > 0.0:
            continue  # the same skip gate — frozen's :452 `if org_landscape`
        floor = FLOOR[str(HYPEREDGES[hid]["kind"])]
        if c["revolutionary"] < floor:
            remaining = 1.0 - floor
            lf = c["liberal"] + c["fascist"]
            if lf > 1e-10:
                c["liberal"] = c["liberal"] * remaining / lf
                c["fascist"] = c["fascist"] * remaining / lf
            else:
                c["liberal"] = remaining
                c["fascist"] = 0.0
            c["revolutionary"] = floor

    # ---- c07-contestation + c08-dominant-tendency (DG-2-GATED — printed
    # here as oracle values; the .bsl rules land only on the Director's
    # ruling). Same skip gate. ----
    for _hid, c in enumerate(comms):
        if not c["density-sum"] > 0.0:
            c["contestation"] = float("nan")  # not recomputed — preserved
            c["dominant"] = float("nan")
            continue
        r, l_val, f = c["revolutionary"], c["liberal"], c["fascist"]
        entropy = 0.0
        for p in (r, l_val, f):
            if p > 1e-10:
                entropy -= p * math.log(p)
        c["contestation"] = entropy / math.log(3)
        # argmax, LIBERAL > REVOLUTIONARY > FASCIST at 1e-6
        # (entities/consciousness.py:167-191, epsilon :189).
        max_val = max(r, l_val, f)
        for tendency, v in (("LIBERAL", l_val), ("REVOLUTIONARY", r), ("FASCIST", f)):
            if abs(v - max_val) < 1e-6:
                c["dominant"] = tendency  # type: ignore[assignment]
                break


def cost_and_decay(
    comms: list[dict[str, float]],
) -> dict[int, float]:
    """c09 → c10 → c11, in rule order."""
    # ---- c09-cost-modifier-reset (social-class, ACTIVE ONLY) ----
    # The inactive n5 is written NOTHING — its key stays ABSENT (§9 item 5).
    cost_modifier: dict[int, float] = {}
    for nid, node in enumerate(NODES):
        if node["type"] == "SOCIAL_CLASS" and node.get("active") == 1:
            cost_modifier[nid] = 1.0

    # ---- c10-cost-modifier-accumulate (active only) ----
    # scale by each membership's reproduction-cost-modifier, ascending
    # HyperedgeId — D-NF+13's float-product-order divergence lives here.
    for nid, node in enumerate(NODES):
        if node["type"] != "SOCIAL_CLASS" or node.get("active") != 1:
            continue
        for hid, h in enumerate(HYPEREDGES):
            if node["name"] in h["members"]:
                cost_modifier[nid] *= comms[hid]["reproduction-cost-modifier"]

    # ---- c11-state-decay (carrier) — max(0, x·(1−α)) per arm; the
    # infrastructure arm is EXCLUDED (§5 — the CORE_ORGANIZER maintenance
    # term waits on #653). ----
    for c in comms:
        c["heat"] = max(0.0, c["heat"] * (1.0 - HEAT_DECAY_ALPHA))
        c["cohesion"] = max(0.0, c["cohesion"] * (1.0 - COHESION_DECAY_ALPHA))
        c["education-pressure"] = max(
            0.0, c["education-pressure"] * (1.0 - EDUCATION_PRESSURE_DECAY)
        )

    return cost_modifier


def run() -> None:
    # Hyperedge scratch state the rules read/write: the seeded own-fields
    # plus the c00-c04 accumulators (minted by c00's reset, not seeded).
    comms: list[dict[str, float]] = []
    for h in HYPEREDGES:
        comms.append(
            {
                "heat": float(h["heat"]),
                "cohesion": float(h["cohesion"]),
                "education-pressure": float(h["education-pressure"]),
                "reproduction-cost-modifier": float(h["reproduction-cost-modifier"]),
                "revolutionary": float(h["revolutionary"]),
                "liberal": float(h["liberal"]),
                "fascist": float(h["fascist"]),
                "member-count": 0.0,
                "r-raw": 0.0,
                "l-raw": 0.0,
                "f-raw": 0.0,
                "density-sum": 0.0,
            }
        )

    census(comms)
    weights = org_weights_and_contributions(comms)
    readout(comms)
    cost_modifier = cost_and_decay(comms)

    # ---- the printout: every oracle value, full round-trip precision ----
    print("community-conformance world 1 — mirror output (the oracle)")
    for hid, h in enumerate(HYPEREDGES):
        c = comms[hid]
        print(f"h{hid} {h['name']} kind={h['kind']}")
        print(f"  member-count = {c['member-count']!r}")
        print(f"  r-raw = {c['r-raw']!r}")
        print(f"  l-raw = {c['l-raw']!r}")
        print(f"  f-raw = {c['f-raw']!r}")
        print(f"  density-sum  = {c['density-sum']!r}")
        print(f"  r = {c['revolutionary']!r}")
        print(f"  l = {c['liberal']!r}")
        print(f"  f = {c['fascist']!r}")
        contestation = c["contestation"]
        if math.isnan(contestation):
            print("  contestation = PRESERVED (no-org skip gate)")
            print("  dominant     = PRESERVED (no-org skip gate)")
        else:
            print(f"  contestation = {contestation!r}   (DG-2-gated)")
            print(f"  dominant     = {c['dominant']}   (DG-2-gated)")
        print(f"  decayed heat               = {c['heat']!r}")
        print(f"  decayed cohesion           = {c['cohesion']!r}")
        print(f"  decayed education-pressure = {c['education-pressure']!r}")
    for nid, node in enumerate(NODES):
        if node["type"] != "SOCIAL_CLASS":
            continue
        w = weights[nid]
        print(
            f"n{nid} {node['name']}: org-r-weight = {w['org-r-weight']!r}, "
            f"org-l-weight = {w['org-l-weight']!r}, org-f-weight = {w['org-f-weight']!r}, "
            f"org-count = {w['org-count']!r}"
        )
        if nid in cost_modifier:
            print(f"n{nid} {node['name']}: community-cost-modifier = {cost_modifier[nid]!r}")
        else:
            print(f"n{nid} {node['name']}: community-cost-modifier = ABSENT (honest null)")


if __name__ == "__main__":
    run()
