#!/usr/bin/env python3
"""The Community @6.0 port train's frozen-mirror oracle (issue #667, plan
docs/superpowers/plans/2026-08-18-community-port.md §9 — the D146/ADR183
convention).

STANDALONE. No `babylon` import, no pytest, no third-party anything. It
transcribes the RULES' binding order and collect-then-apply semantics
term-for-term over the literal WORLD dicts below — each matching its
`.bscn` node-for-node, hyperedge-for-hyperedge, seed-for-seed — never the
frozen engine's code (the frozen engine is EVIDENCE, captured separately in
reports/community-frozen-corroboration-2026-08-18.md; it prints frozen's
own, sometimes-diverged answer — D-NF+3's summation order, D-NF+5's
500-org cap, and the SnapToGrid 10^-6 Pydantic boundary live there).

Per §9, this header states, for this pack specifically:

1. THE EXACT RULE ORDER (byte order, D16): c00 → c01 → c02 → c03f → c03l
   → c03r → c04 → c05 → c06a → c06b → [c07 → c08, DG-2-gated] → c09 → c10
   → c11. Each rule applies ALL of its writes before the next rule reads
   (§8b's D116 ledger — the cross-rule reads this pack relies on, fatal
   rows included). **THE c06 SPLIT (D204):** the plan's c06 was one rule —
   "the pack's ONLY 14-arm dispatch" driving the redistribution — but the
   pre-state law (item 2) makes a write-then-read WITHIN one rule's body
   impossible: the floor written by an `update-hyperedge` is not visible
   to a later operand's `field-of` in the same collect pass. The dispatch
   therefore lands as `c06a-floor-dispatch` (writes the per-community
   `community/substrate-floor` cache through the pack's only 14-arm chain)
   and `c06b-floor-redistribute` (reads the cache — a same-tick CROSS-RULE
   read, the §8b shape spike (f) proved at Task 7). The MATH is unchanged;
   the rule count moves 14 → 15, recorded in the D-row register.
2. PRE-STATE WITHIN A RULE: a rule's for-each accumulations are COLLECTED
   against the rule-entry state and APPLIED in ascending order only after
   the whole subject population has collected — so c01's `add 1`s against
   one hyperedge never observe each other mid-rule (§4.2 chapter C4).
3. THE EXACT f64 OPERATION ORDER: every accumulator sums
   subject-ascending (NodeId) outer, ascending HyperedgeId inner (D25);
   c10's PRODUCT compounds in ascending HyperedgeId order — D-NF+13's
   multiplication-order divergence lives exactly there.
4. THE FLOOR-DISPATCH ARM each seeded community takes (ADR214 provenance):
   world 1 — h0 NEW_AFRIKAN 0.136, h1 SETTLER 0.0, h2 QUEER 0.04, NONE
   bind (every normalized r clears its floor). World 2 — NEW_AFRIKAN and
   FIRST_NATIONS both bind (their landscapes put normalized r below both
   floors; Ruling 3's 0.155 > 0.136 ordering is EXECUTED, not asserted),
   SETTLER is the 0.0-floor control. World 3 — CHICANO binds through the
   DEGENERATE branch (the zero-cadre org), QUEER exercises the no-org skip
   gate (its prior ternary is preserved byte-exactly).
5. UNWRITTEN FIELDS, PER NODE: an inactive class (world 1's n5) is
   excluded from the census AND from the cost-modifier write (frozen
   community.py:472-474) — the mirror models its
   `community-cost-modifier` as ABSENT (the key does not exist), never
   1.0, so the Rust assertion reads the substrate's honest-null error
   (§1.4, C4). A mirror that defaults an unwritten field is a mirror that
   cannot catch a fabricated write. The same law holds for the no-org
   SKIPPED community (world 3's h1): c05/c06 write it NOTHING, so its
   `substrate-floor` cache is absent too.

c07/c08 are DG-2-GATED (the Director question is unresolved at authoring):
transcribed and printed here because the mirror is the oracle and the
values cost nothing — their .bsl RULES do not land while the gate holds.
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------
# The worlds. Nodes in declaration order (id order); hyperedges in their
# own counter order. Every literal matches its .bscn seed EXACTLY.
# ---------------------------------------------------------------------

WORLD_1: dict[str, object] = {
    "name": "world 1 (community-conformance.bscn)",
    "nodes": [
        {"name": "community-register", "type": "INSTITUTION", "community-carrier": 1},
        {"name": "na-worker", "type": "SOCIAL_CLASS", "active": 1},
        {"name": "na-organizer", "type": "SOCIAL_CLASS", "active": 1},
        {"name": "settler-la", "type": "SOCIAL_CLASS", "active": 1},
        {"name": "unaffiliated", "type": "SOCIAL_CLASS", "active": 1},
        {"name": "inactive-member", "type": "SOCIAL_CLASS", "active": 0},
        {
            "name": "rev-org",
            "type": "ORGANIZATION",
            "cadre-level": 0.5,
            "cohesion": 0.8,
            "tendency": "REVOLUTIONARY",
        },
        {
            "name": "lib-org",
            "type": "ORGANIZATION",
            "cadre-level": 0.25,
            "cohesion": 0.5,
            "tendency": "LIBERAL",
        },
        {
            "name": "fash-org",
            "type": "ORGANIZATION",
            "cadre-level": 0.5,
            "cohesion": 0.25,
            "tendency": "FASCIST",
        },
        {
            "name": "no-member-org",
            "type": "ORGANIZATION",
            "cadre-level": 1.0,
            "cohesion": 1.0,
            "tendency": "REVOLUTIONARY",
        },
    ],
    "edges": [
        ("rev-org", "na-worker"),
        ("rev-org", "na-organizer"),
        ("lib-org", "na-worker"),
        ("lib-org", "settler-la"),
        ("fash-org", "settler-la"),
    ],
    "hyperedges": [
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
    ],
}

# World 2 (community-floor-conformance.bscn, Task 9 Step 6): NEW_AFRIKAN
# and FIRST_NATIONS communities whose org landscapes put normalized r
# BELOW both floors (both bind; the Ruling-3 ordering is observable), plus
# SETTLER as the 0.0-floor control. weak-fash gives h0 a nonzero f so the
# redistribution's PROPORTIONALITY is exercised (not just the l-only arm).
WORLD_2: dict[str, object] = {
    "name": "world 2 (community-floor-conformance.bscn)",
    "nodes": [
        {"name": "floor-register", "type": "INSTITUTION", "community-carrier": 1},
        {"name": "w2-a", "type": "SOCIAL_CLASS", "active": 1},
        {"name": "w2-b", "type": "SOCIAL_CLASS", "active": 1},
        {"name": "w2-s", "type": "SOCIAL_CLASS", "active": 1},
        # w2-c/w2-d: the low-density community's members — h3's density-sum
        # is (1+0)/2 = 0.5, so c05's unorganized = 0.5 folds into l (the
        # `unorganized_fraction_defaults_to_liberal` witness). No floor
        # binds (SETTLER, 0.0), so the pure c05 shape is what shows.
        {"name": "w2-c", "type": "SOCIAL_CLASS", "active": 1},
        {"name": "w2-d", "type": "SOCIAL_CLASS", "active": 1},
        {
            "name": "weak-rev",
            "type": "ORGANIZATION",
            "cadre-level": 0.125,
            "cohesion": 0.25,
            "tendency": "REVOLUTIONARY",
        },
        {
            "name": "strong-lib",
            "type": "ORGANIZATION",
            "cadre-level": 1.0,
            "cohesion": 1.0,
            "tendency": "LIBERAL",
        },
        {
            "name": "weak-fash",
            "type": "ORGANIZATION",
            "cadre-level": 0.25,
            "cohesion": 0.5,
            "tendency": "FASCIST",
        },
    ],
    "edges": [
        ("weak-rev", "w2-a"),
        ("weak-rev", "w2-b"),
        ("strong-lib", "w2-a"),
        ("strong-lib", "w2-b"),
        ("strong-lib", "w2-s"),
        ("weak-fash", "w2-b"),
        ("weak-rev", "w2-d"),
    ],
    "hyperedges": [
        {
            "name": "na-comm",
            "kind": "NEW_AFRIKAN",
            "members": ["w2-a", "w2-b"],
            "heat": 0.5,
            "cohesion": 0.75,
            "education-pressure": 0.25,
            "reproduction-cost-modifier": 0.875,
            "revolutionary": 0.5,
            "liberal": 0.25,
            "fascist": 0.25,
        },
        {
            "name": "fn-comm",
            "kind": "FIRST_NATIONS",
            "members": ["w2-a"],
            "heat": 0.25,
            "cohesion": 0.5,
            "education-pressure": 0.125,
            "reproduction-cost-modifier": 1.25,
            "revolutionary": 0.25,
            "liberal": 0.5,
            "fascist": 0.25,
        },
        {
            "name": "settler-comm",
            "kind": "SETTLER",
            "members": ["w2-s"],
            "heat": 0.75,
            "cohesion": 0.625,
            "education-pressure": 0.5,
            "reproduction-cost-modifier": 1.0,
            "revolutionary": 0.0,
            "liberal": 0.75,
            "fascist": 0.25,
        },
        {
            "name": "low-density-comm",
            "kind": "SETTLER",
            "members": ["w2-c", "w2-d"],
            "heat": 0.5,
            "cohesion": 0.25,
            "education-pressure": 0.375,
            "reproduction-cost-modifier": 1.0,
            "revolutionary": 0.5,
            "liberal": 0.25,
            "fascist": 0.25,
        },
    ],
}

# World 3 (community-degenerate-conformance.bscn, Task 9 Step 6): the
# degenerate case (h0's only org has ZERO cadre — every weight is 0, the
# total collapses, the (0,1,0) branch fires and the floor routes through
# c06, §6.2 I5) AND the no-org skip gate (h1's member has no org edges —
# density-sum stays 0, the prior ternary is preserved byte-exactly).
WORLD_3: dict[str, object] = {
    "name": "world 3 (community-degenerate-conformance.bscn)",
    "nodes": [
        {"name": "degenerate-register", "type": "INSTITUTION", "community-carrier": 1},
        {"name": "d-a", "type": "SOCIAL_CLASS", "active": 1},
        {"name": "d-b", "type": "SOCIAL_CLASS", "active": 1},
        {
            "name": "zero-cadre",
            "type": "ORGANIZATION",
            "cadre-level": 0.0,
            "cohesion": 0.5,
            "tendency": "REVOLUTIONARY",
        },
    ],
    "edges": [
        ("zero-cadre", "d-a"),
    ],
    "hyperedges": [
        {
            "name": "deg-comm",
            "kind": "CHICANO",
            "members": ["d-a"],
            "heat": 0.5,
            "cohesion": 0.75,
            "education-pressure": 0.25,
            "reproduction-cost-modifier": 0.75,
            "revolutionary": 0.25,
            "liberal": 0.5,
            "fascist": 0.25,
        },
        {
            "name": "no-org-comm",
            "kind": "QUEER",
            "members": ["d-b"],
            "heat": 0.25,
            "cohesion": 0.5,
            "education-pressure": 0.125,
            "reproduction-cost-modifier": 1.125,
            "revolutionary": 0.125,
            "liberal": 0.75,
            "fascist": 0.125,
        },
    ],
}

WORLDS: list[dict[str, object]] = [WORLD_1, WORLD_2, WORLD_3]

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


def census(world: dict[str, object], comms: list[dict[str, float]]) -> None:
    """c00 → c01, in rule order (the reset and the member census)."""
    # ---- c00-census-reset (carrier): the accumulators were seeded at 0 —
    # the reset writes those zeros over any prior tick (one tick per world
    # here, so it is the identity and STILL transcribed: Task 12's
    # multi-tick worlds need the order visible). ----
    for c in comms:  # ascending HyperedgeId
        c["member-count"] = 0.0
        c["r-raw"] = 0.0
        c["l-raw"] = 0.0
        c["f-raw"] = 0.0
        c["density-sum"] = 0.0

    # ---- c01-member-census (social-class, active only) ----
    # Pre-state law: every `add 1` collects against the c00-reset state —
    # subject-ascending (NodeId) outer, ascending HyperedgeId inner.
    nodes = world["nodes"]
    hyperedges = world["hyperedges"]
    census_pending: list[int] = [0] * len(comms)
    for node in nodes:  # type: ignore[union-attr]
        if node["type"] != "SOCIAL_CLASS" or node.get("active") != 1:  # type: ignore[union-attr]
            continue
        for hid, h in enumerate(hyperedges):  # type: ignore[union-attr]
            if node["name"] in h["members"]:  # type: ignore[operator]
                census_pending[hid] += 1
    for hid, n in enumerate(census_pending):
        comms[hid]["member-count"] += float(n)


def org_weights_and_contributions(
    world: dict[str, object],
    comms: list[dict[str, float]],
) -> dict[int, dict[str, float]]:
    """c02 → c03f → c03l → c03r → c04, in rule order."""
    nodes = world["nodes"]
    edges = world["edges"]
    hyperedges = world["hyperedges"]
    name_to_node = {str(n["name"]): i for i, n in enumerate(nodes)}  # type: ignore[union-attr]

    # ---- c02-org-weight-reset (social-class): mint the four zeros ----
    class_weights: dict[int, dict[str, float]] = {}
    for nid, node in enumerate(nodes):  # type: ignore[union-attr]
        if node["type"] == "SOCIAL_CLASS":
            class_weights[nid] = {
                "org-r-weight": 0.0,
                "org-l-weight": 0.0,
                "org-f-weight": 0.0,
                "org-count": 0.0,
            }

    # ---- c03f / c03l / c03r (organization; the three-rule partition) ----
    # Rule-id byte order is the execution order (D16): c03f → c03l → c03r.
    # Order-insensitive (disjoint weight fields; the shared org-count is
    # integer-exact additive) — transcribed in the TRUE order anyway.
    for tendency in ("FASCIST", "LIBERAL", "REVOLUTIONARY"):
        key = {
            "REVOLUTIONARY": "org-r-weight",
            "LIBERAL": "org-l-weight",
            "FASCIST": "org-f-weight",
        }[tendency]
        for node in nodes:  # type: ignore[union-attr]
            if node["type"] != "ORGANIZATION" or node["tendency"] != tendency:  # type: ignore[union-attr]
                continue
            push = float(node["cadre-level"]) * float(node["cohesion"])  # type: ignore[arg-type]
            for src, tgt in edges:  # type: ignore[union-attr]
                if src != node["name"]:
                    continue
                class_weights[name_to_node[tgt]][key] += push
                class_weights[name_to_node[tgt]]["org-count"] += 1.0

    # ---- c04-community-contribution-push (social-class, ACTIVE ONLY) ----
    # The active gate is FIDELITY: frozen's community_agents is built from
    # the active-only membership set (community.py:472-474 -> :392-397).
    for nid, node in enumerate(nodes):  # type: ignore[union-attr]
        if node["type"] != "SOCIAL_CLASS" or node.get("active") != 1:  # type: ignore[union-attr]
            continue
        w = class_weights[nid]
        for hid, h in enumerate(hyperedges):  # type: ignore[union-attr]
            if node["name"] not in h["members"]:  # type: ignore[operator]
                continue
            divisor = comms[hid]["member-count"]
            comms[hid]["r-raw"] += w["org-r-weight"] / divisor
            comms[hid]["l-raw"] += w["org-l-weight"] / divisor
            comms[hid]["f-raw"] += w["org-f-weight"] / divisor
            comms[hid]["density-sum"] += w["org-count"] / divisor
    return class_weights


def normalize(comms: list[dict[str, float]]) -> None:
    """c05, alone (the normalization and the degenerate branch)."""

    # ---- c05-normalize (carrier) — the density-sum > 0 skip gate ----
    # unorganized = max(0, 1 − density-sum) folded into l-raw; total =
    # r+l+f (LEFT-associated: (r + (l+u)) + f, frozen's exact chain);
    # degenerate (total < 1e-10) → (0, 1, 0) AND NOTHING ELSE (the floor
    # routes through c06, bit-identically — §6.2 I5). Frozen never stores
    # the unorganized-folded l-raw, so neither does the port — only the
    # normalized ternary is written.
    for c in comms:
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


def floor_and_gated_readout(
    world: dict[str, object],
    comms: list[dict[str, float]],
) -> None:
    """c06a → c06b, then c07/c08 (DG-2-gated), in rule order."""
    hyperedges = world["hyperedges"]
    # ---- c06a-floor-dispatch (carrier) — the pack's ONLY 14-arm chain
    # writes the per-community floor cache. SKIPPED communities are written
    # NOTHING (the cache stays absent — §9 item 5's law one field over).
    # (A dict here: the mirror transcribes SEMANTICS; the .bsl arm chain is
    # the language's only lookup shape, §6.2.)
    for hid, c in enumerate(comms):
        if not c["density-sum"] > 0.0:
            continue
        c["substrate-floor"] = FLOOR[str(hyperedges[hid]["kind"])]  # type: ignore[index]

    # ---- c06b-floor-redistribute (carrier) — reads the cache (the
    # same-tick cross-rule read, §8b). The r < floor redistribution with
    # its lf > 1e-10 two-arm split (formulas/consciousness.py:98-107).
    for c in comms:
        if "substrate-floor" not in c:
            continue  # the skip gate, one hop removed
        floor = c["substrate-floor"]
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
    for c in comms:
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
    world: dict[str, object],
    comms: list[dict[str, float]],
) -> dict[int, float]:
    """c09 → c10 → c11, in rule order."""
    nodes = world["nodes"]
    hyperedges = world["hyperedges"]

    # ---- c09-cost-modifier-reset (social-class, ACTIVE ONLY) ----
    # An inactive class is written NOTHING — its key stays ABSENT (§9
    # item 5).
    cost_modifier: dict[int, float] = {}
    for nid, node in enumerate(nodes):  # type: ignore[union-attr]
        if node["type"] == "SOCIAL_CLASS" and node.get("active") == 1:  # type: ignore[union-attr]
            cost_modifier[nid] = 1.0

    # ---- c10-cost-modifier-accumulate (active only) ----
    # scale by each membership's reproduction-cost-modifier, ascending
    # HyperedgeId — D-NF+13's float-product-order divergence lives here.
    for nid, node in enumerate(nodes):  # type: ignore[union-attr]
        if node["type"] != "SOCIAL_CLASS" or node.get("active") != 1:  # type: ignore[union-attr]
            continue
        for hid, h in enumerate(hyperedges):  # type: ignore[union-attr]
            if node["name"] in h["members"]:  # type: ignore[operator]
                cost_modifier[nid] *= comms[hid]["reproduction-cost-modifier"]

    # ---- c11-state-decay (carrier) — max(0, x·(1−α)) per arm, EVERY
    # community (frozen's decay has no skip gate — community.py:648-675);
    # the infrastructure arm is EXCLUDED (§5 — the CORE_ORGANIZER
    # maintenance term waits on #653). ----
    for c in comms:
        c["heat"] = max(0.0, c["heat"] * (1.0 - HEAT_DECAY_ALPHA))
        c["cohesion"] = max(0.0, c["cohesion"] * (1.0 - COHESION_DECAY_ALPHA))
        c["education-pressure"] = max(
            0.0, c["education-pressure"] * (1.0 - EDUCATION_PRESSURE_DECAY)
        )
    return cost_modifier


def run_world(world: dict[str, object]) -> None:
    """One full tick of the transcribed pack over one world, printed."""
    hyperedges = world["hyperedges"]
    comms: list[dict[str, float]] = []
    for h in hyperedges:  # type: ignore[union-attr]
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

    census(world, comms)
    weights = org_weights_and_contributions(world, comms)
    normalize(comms)
    floor_and_gated_readout(world, comms)
    cost_modifier = cost_and_decay(world, comms)

    # ---- the printout: every oracle value, full round-trip precision ----
    print(f"== {world['name']} ==")
    for hid, h in enumerate(hyperedges):  # type: ignore[union-attr]
        c = comms[hid]
        print(f"h{hid} {h['name']} kind={h['kind']}")
        print(f"  member-count = {c['member-count']!r}")
        print(f"  r-raw = {c['r-raw']!r}")
        print(f"  l-raw = {c['l-raw']!r}")
        print(f"  f-raw = {c['f-raw']!r}")
        print(f"  density-sum  = {c['density-sum']!r}")
        if "substrate-floor" in c:
            print(f"  substrate-floor = {c['substrate-floor']!r}")
        else:
            print("  substrate-floor = ABSENT (no-org skip gate)")
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
    nodes = world["nodes"]
    for nid, node in enumerate(nodes):  # type: ignore[union-attr]
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


def run() -> None:
    """Drive every world, in WORLDS order."""
    print("community-conformance — mirror output (the oracle)")
    for world in WORLDS:
        run_world(world)


if __name__ == "__main__":
    run()
