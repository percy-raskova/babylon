#!/usr/bin/env python3
"""Reference implementation of the RE-POINTED class-surface consciousness law
(issue #588, ADR204 W10, Task 3). NOT the frozen engine's behavior: the frozen
engine accumulates cc/ni and bridges to the ternary at read
(aggregation.py:86-98); the port stores the ternary directly — r += Δr,
l += Δl (APPLIED, not discarded at the frozen call-site ideology.py:394),
f += Δf·(1−suppression) — with closure by a verbatim normalize_to_simplex
transcription (consciousness_routing.py:373-409). This script is the
dual-implementation conformance oracle: it mirrors consciousness.bsl's
nine-rule pack p0..p8 binding-order term-for-term (the BSL side is the
transcription of record — reassociation is a conformance bug) and prints
repr floats for the Rust test to pin exactly. Pure IEEE-754 basic ops; no
libm transcendentals exist anywhere in the re-pointed law (the Curve-5
Gaussian is retired, ADR202 R7).

Controller amendments applied (2026-08-15, binding over the Task-3 brief):
no micros anywhere (the int lane holds verbatim f64 — spike 4's verdict,
scenario header D-record 5); agitation seeds integer 0 (produced
accumulator, R-MEASURED); the wage flow rides the declared class-side
social-class/wages-received field (controller ruling 2 — the WAGES-edge
machinery is dead); nine rule ids p0..p8 per the amendment map; epsilon
rides the expr quotient (/ 1c 10000000000), bit-identical to Python's
1e-10 via one correctly-rounded IEEE-754 division (E-LEX-023 dodged).

Frozen transcription sources (reference-only; transcribed exactly):
  src/babylon/engine/systems/ideology.py:115-442  — the step: input reads
    (:236-317), the agitation call (:372-380), the routing call (:394-400),
    the popular-front throttle (:409), the decay (:413-414).
  src/babylon/formulas/consciousness_routing.py:48-200 —
    compute_agitation_delta; :288-370 — route_agitation_to_ternary;
    :373-409 — normalize_to_simplex; :41 — _EPSILON = 1e-10.
  src/babylon/formulas/contradiction.py:67-100 —
    calculate_wealth_asymmetry_balance, called as (v_produced, w_paid) so
    balance = (w − v)/(v + w): positive = wages dominate = the imperial
    bribe.
"""

# ---- defines environment (transcribed; line cites = src/babylon/data/defines.yaml) ----
ROUTING_SCALE = 0.2  # consciousness.routing_scale, :213
AGITATION_DECAY_RATE = 0.1  # :214
EXPLOITATION_SENSITIVITY = 0.15  # :215
RENT_DECLINE_SENSITIVITY = 0.2  # :216
REPRODUCTION_VISIBILITY_COEFFICIENT = 0.1  # :217 (term is 0.0 verbatim, ideology.py:375)
AGITATION_CONSUMPTION_RATE = 0.6  # :220
CHAUVINIST_PRESSURE_SCALE = 1.0  # :228
REPRESSION_LEVEL_SENSITIVITY = 0.02  # :229
DEFAULT_REPRESSION_FACED = (
    0.5  # survival.default_repression, :167 — DEFAULT_REPRESSION_FACED's alias target
)
ACTIVATION_THRESHOLD = 0.3  # solidarity.activation_threshold, :184
NEGLIGIBLE_TRANSMISSION = 0.01  # solidarity.negligible_transmission, :186
# consciousness/simplex-epsilon has NO defconst row (controller ruling 4):
# the route rule binds it as the expr quotient (/ 1c 10000000000); the
# correctly-rounded quotient of exact operands IS fl(1e-10), so Python's
# 1e-10 literal is bit-identical — verified at load, never assumed.
SIMPLEX_EPSILON = 1.0 / 10000000000.0
DOMINANT_EPSILON = 0.000001  # p8's 0.000001c (consciousness.py:177-192's 1e-6)
WAGE_DETERIORATION_STUB = (
    0.0  # D-row: opposition_states graph attr has no BSL surface (ideology.py:153-157)
)
POPULAR_FRONT_SUPPRESSION_STUB = 0.0  # D-row: electoral register absent (exact under register-absent content, ideology.py:401-409)

if SIMPLEX_EPSILON != 1e-10:
    raise ValueError("the (/ 1c 10000000000) quotient must be bit-identical to 1e-10")

# ---- the seed world, verbatim from consciousness-ternary-conformance.bscn ----
# p/i/c seed literals convert as unscaled / 10^scale of exact operands — one
# correctly-rounded IEEE-754 division each — so the plain Python float
# literals below are bit-identical to the store's seeds. ABSENT marks a
# field the scenario never seeds: reads of it are the :optional-:default
# declared literals, and a raw store read would error loud (III.11).
ABSENT = None

Scalar = float | int | str | None
Node = dict[str, Scalar]
World = dict[str, Node]

WORLD: World = {
    "class-exploited": {
        "node_type": "SOCIAL_CLASS",
        "active": 1,
        "population": 1000,
        "wealth": 50.0,
        "wages_paid": 9.0,
        "value_produced": 10.0,
        "r": 0.5,
        "l": 0.4,
        "f": 0.1,
        "agitation": 0.0,
        "wages_received": 9.0,
        "previous_wages": 10.0,
        "previous_wealth": 50.0,
        "repression_faced": ABSENT,
        "solidarity_inbox": ABSENT,
        "wage_balance": ABSENT,
        "dominant": ABSENT,
    },
    "class-bribed": {
        "node_type": "SOCIAL_CLASS",
        "active": 1,
        "population": 800,
        "wealth": 90.0,
        "wages_paid": 12.0,
        "value_produced": 10.0,
        "r": 0.1,
        "l": 0.6,
        "f": 0.3,
        "agitation": 0.0,
        "wages_received": 12.0,
        "previous_wages": 12.0,
        "previous_wealth": 95.0,
        "repression_faced": ABSENT,
        "solidarity_inbox": ABSENT,
        "wage_balance": ABSENT,
        "dominant": ABSENT,
    },
    "class-unpositioned": {
        "node_type": "SOCIAL_CLASS",
        "active": 1,
        "population": 500,
    },
    "class-emergent": {
        "node_type": "SOCIAL_CLASS",
        "active": 1,
        "population": 600,
        "wealth": 30.0,
        "wages_paid": 8.0,
        "value_produced": 10.0,
        "wages_received": 8.0,
        "previous_wages": 9.0,
        "previous_wealth": 30.0,
        "repression_faced": ABSENT,
        "solidarity_inbox": ABSENT,
        "wage_balance": ABSENT,
        "dominant": ABSENT,
        "r": ABSENT,
        "l": ABSENT,
        "f": ABSENT,
        "agitation": ABSENT,
    },
    "employer": {"node_type": "SOCIAL_CLASS", "active": 1, "population": 50},
    "org-solid": {"node_type": "ORGANIZATION", "org_active": 1},
    # Task 2's read-path fixtures: population / active=1 / the ternary /
    # agitation 0 — NO anchors, NO edges.
    "tv-liberal-clear": {
        "node_type": "SOCIAL_CLASS",
        "active": 1,
        "population": 100,
        "r": 0.2,
        "l": 0.5,
        "f": 0.3,
        "agitation": 0.0,
    },
    "tv-revolutionary-clear": {
        "node_type": "SOCIAL_CLASS",
        "active": 1,
        "population": 100,
        "r": 0.6,
        "l": 0.4,
        "f": 0.0,
        "agitation": 0.0,
    },
    "tv-fascist-clear": {
        "node_type": "SOCIAL_CLASS",
        "active": 1,
        "population": 100,
        "r": 0.2,
        "l": 0.3,
        "f": 0.5,
        "agitation": 0.0,
    },
    "tv-tie-lr": {
        "node_type": "SOCIAL_CLASS",
        "active": 1,
        "population": 100,
        "r": 0.5,
        "l": 0.5,
        "f": 0.0,
        "agitation": 0.0,
    },
    "tv-tie-rf": {
        "node_type": "SOCIAL_CLASS",
        "active": 1,
        "population": 100,
        "r": 0.5,
        "l": 0.0,
        "f": 0.5,
        "agitation": 0.0,
    },
    "tv-tie-lf": {
        "node_type": "SOCIAL_CLASS",
        "active": 1,
        "population": 100,
        "r": 0.0,
        "l": 0.5,
        "f": 0.5,
        "agitation": 0.0,
    },
    "tv-strict-gap": {
        "node_type": "SOCIAL_CLASS",
        "active": 1,
        "population": 100,
        "r": 0.333333,
        "l": 0.333333,
        "f": 0.333334,
        "agitation": 0.0,
    },
    "tv-tie-all-true": {
        "node_type": "SOCIAL_CLASS",
        "active": 1,
        "population": 100,
        "r": 0.333333,
        "l": 0.333333,
        "f": 0.333333,
        "agitation": 0.0,
    },
}

# (source, target, strength) in declaration order. `solidarity/strength` is
# the edge's implicit field (the <edge-type-lower>/<field> convention).
SOLIDARITY_EDGES = [
    ("org-solid", "class-exploited", 0.4),
    ("class-exploited", "class-emergent", 0.5),
    ("class-bribed", "class-emergent", 0.9),
]


def opt(node: Node, key: str, default: float) -> float:
    """The :optional + :default binding mirror: absent reads observe ONLY the
    declared literal default (the pack's UNPOSITIONED idiom)."""
    value = node.get(key, ABSENT)
    return default if value is ABSENT else value  # type: ignore[return-value]


def ternary_sum(node: Node) -> float:
    """The pack's `(+ r (+ l f))` under the declared 0.0p defaults,
    right-nested exactly as the BSL expr associates."""
    r = opt(node, "r", 0.0)
    lib = opt(node, "l", 0.0)
    f = opt(node, "f", 0.0)
    return r + (lib + f)


def is_class(node: Node) -> bool:
    return node["node_type"] == "SOCIAL_CLASS"


def p0_position(world: World) -> int:
    """p0-position (landed Task 1): the A-001 class-seeding law.
    (when (and (= active 1) (>= wages 0) (>= value 0) (= (+ r (+ l f)) 0)))."""
    fired = 0
    for node in world.values():
        if not is_class(node) or "active" not in node:
            continue  # required bindings: node-type-appropriate fields only
        wages = opt(node, "wages_paid", -1)
        value = opt(node, "value_produced", -1)
        if node["active"] == 1 and wages >= 0 and value >= 0 and ternary_sum(node) == 0:
            node["r"], node["l"], node["f"] = 0.0, 1.0, 0.0  # A-001 rest state
            node["agitation"] = 0
            fired += 1
    return fired


def p1_inbox_reset(world: World) -> int:
    """p1-inbox-reset: the solidarity inbox is per-tick machinery, zeroed
    before this tick's pushes accumulate (D103/D104). Positioned only."""
    fired = 0
    for node in world.values():
        if is_class(node) and ternary_sum(node) > 0:
            node["solidarity_inbox"] = 0
            fired += 1
    return fired


def p2_org_solidarity_push(world: World) -> int:
    """p2-org-solidarity-push: org-sourced strength above the
    negligible-transmission floor (frozen ideology.py:339-356's org arm).
    Push form — each edge pushed exactly once by its unique source (D136)."""
    fired = 0
    for name, node in world.items():
        if node["node_type"] != "ORGANIZATION" or "org_active" not in node:
            continue  # organization/active is a required binding
        if node["org_active"] != 1:
            continue
        fired += 1
        for src, tgt, strength in SOLIDARITY_EDGES:
            if src != name or not is_class(world[tgt]):
                continue
            if strength > NEGLIGIBLE_TRANSMISSION:  # the guard effect form
                world[tgt]["solidarity_inbox"] = opt(world[tgt], "solidarity_inbox", 0) + strength
    return fired


def p3_class_solidarity_push(world: World) -> int:
    """p3-class-solidarity-push: class-sourced solidarity transmits only past
    the percolation threshold (frozen: source class_consciousness >
    activation_threshold) — re-pointed at the source's revolutionary share
    (post-W1 the same quantity). An UNPOSITIONED source reads r = 0.0p and
    never transmits. The frozen loop's strength <= 0 skip is NOT transcribed
    (inert on declared content — recorded narrowing, D-row)."""
    fired = 0
    for name, node in world.items():
        if not is_class(node):
            continue
        if opt(node, "r", 0.0) > ACTIVATION_THRESHOLD:
            fired += 1
            for src, tgt, strength in SOLIDARITY_EDGES:
                if src != name or not is_class(world[tgt]):
                    continue
                world[tgt]["solidarity_inbox"] = opt(world[tgt], "solidarity_inbox", 0) + strength
    return fired


def p4_wage_balance(node: Node, anchored: bool) -> bool:
    """p4-wage-balance — contradiction.py:67-100 called (v, w) so
    balance = (w − v)/(v + w): positive = the imperial bribe. The frozen
    [-1,1] clamp is inert-by-construction under non-negative anchored
    inputs (|w−v| <= v+w). The frozen 1e-9 zero-guard
    (contradiction.py:98-100: total <= 1e-9 -> 0.0) is NARROWED, not
    inert — the port's guard is `(+ wages value) > 0`, so for
    0 < v+w <= 1e-9 the frozen yields 0.0 where the port yields the
    quotient; content-inert on declared content — recorded narrowing."""
    if not anchored:
        return False
    wages = opt(node, "wages_paid", -1)
    value = opt(node, "value_produced", -1)
    balance = (wages - value) / (value + wages) if wages + value > 0 else 0.0 - 0.0
    node["wage_balance"] = balance
    return True


def p5_agitation(node: Node, anchored: bool, positioned: bool) -> bool:
    """p5-agitation — compute_agitation_delta (consciousness_routing.py:
    48-200) under the frozen call-site's exact argument mapping
    (ideology.py:372-380): exploitation_delta = |wage_change| when wages
    fall; wealth_change passed as imperial_rent_delta; visibility 0.0
    verbatim; the Curve-5 balance component ABSENT (ADR202 R7); repression
    as produced-excess-over-baseline, absent contributing zero (MEDIUM-2).
    Writes the UNDECAYED level; p6 routes on it and writes the decayed
    store."""
    if not (anchored and positioned):
        return False
    wages_in = opt(node, "wages_received", 0)  # controller ruling 2
    prev_wages = opt(node, "previous_wages", 0)
    wealth = opt(node, "wealth", 0)
    prev_wealth = opt(node, "previous_wealth", 0)
    rf = opt(node, "repression_faced", 0.5)
    agitation = opt(node, "agitation", 0)
    wage_change = wages_in - prev_wages
    exploit_delta = (0 - wage_change) if wage_change < 0 else 0
    wealth_change = wealth - prev_wealth
    neg_wealth_change = 0 - wealth_change
    repression_excess = rf - DEFAULT_REPRESSION_FACED
    # The pack's right-nested expr tree E + (R + (V + P)) — mirror exactly
    # (the frozen's Python sum is left-assoc with the balance component
    # absent; identical here, one nonzero term per class, but the BSL
    # association is the transcription of record).
    increment = ((exploit_delta if exploit_delta > 0 else 0) * EXPLOITATION_SENSITIVITY) + (
        ((neg_wealth_change if neg_wealth_change > 0 else 0) * RENT_DECLINE_SENSITIVITY)
        + (
            (0.0 * REPRODUCTION_VISIBILITY_COEFFICIENT)
            + ((repression_excess if repression_excess > 0 else 0) * REPRESSION_LEVEL_SENSITIVITY)
        )
    )
    node["agitation"] = agitation + (increment + WAGE_DETERIORATION_STUB)
    return True


def p6_route(node: Node, positioned: bool) -> bool:
    """p6-route — the ratified bifurcation law (ADR016;
    route_agitation_to_ternary, consciousness_routing.py:345-370) RE-POINTED
    at the stored ternary, closure by a verbatim normalize_to_simplex
    (:373-409). Δl APPLIED (frozen discards at ideology.py:394) — the
    re-point. Decay store follows ideology.py:413-414. The guard is the
    ternary sum-guard ALONE (the BSL `when`): agitation rides an
    `:optional :default 0` binding (pack D-record 1), so a positioned
    class with no agitation field still fires — this mirror must not
    skip it."""
    if not positioned:
        return False
    new_agitation: float = opt(node, "agitation", 0)
    inbox = opt(node, "solidarity_inbox", 0)
    balance = opt(node, "wage_balance", 0)
    r = opt(node, "r", 0.0)
    lib = opt(node, "l", 0.0)
    f = opt(node, "f", 0.0)
    consumed = new_agitation * AGITATION_CONSUMPTION_RATE
    # solidarity_factor = min(1.0, solidarity_pressure) at the frozen
    # call-site (ideology.py:396)
    sol_factor = inbox if inbox < 1 else (1 - 0.0)
    # chauvinist_pressure = max(0.0, balance) * scale (ideology.py:248-251)
    chauvinist = (balance if balance > 0 else 0) * CHAUVINIST_PRESSURE_SCALE
    # effective_solidarity = min(1.0, factor + education_pressure=0.0)
    eff_raw_arg = sol_factor + 0.0
    eff_raw = eff_raw_arg if eff_raw_arg < 1 else (1 - 0.0)
    # then max(0.0, min(1.0, eff - chauvinist))
    eff_arg = eff_raw - chauvinist
    eff_sol = (eff_arg if eff_arg < 1 else (1 - 0.0)) if eff_arg > 0 else (0 - 0.0)
    delta_r = (consumed * eff_sol) * ROUTING_SCALE
    delta_f = ((consumed * (1 - eff_sol)) * ROUTING_SCALE) * (1 - POPULAR_FRONT_SUPPRESSION_STUB)
    delta_l = 0 - (delta_r + delta_f)  # APPLIED — the re-point
    # normalize_to_simplex, verbatim (:373-409), with the pack's
    # right-nested total (+ r1 (+ l1 f1)).
    r1 = (r + delta_r) if (r + delta_r) > 0 else (0 - 0.0)
    l1 = (lib + delta_l) if (lib + delta_l) > 0 else (0 - 0.0)
    f1 = (f + delta_f) if (f + delta_f) > 0 else (0 - 0.0)
    total = r1 + (l1 + f1)
    if total < SIMPLEX_EPSILON:
        r_out, l_out, f_out = 0.0, 1.0, 0.0
    elif total > 1 + SIMPLEX_EPSILON:
        r_out, l_out, f_out = r1 / total, l1 / total, f1 / total
    elif total < 1 - SIMPLEX_EPSILON:
        r_out, l_out, f_out = r1, l1 + (1 - total), f1  # A-001 remainder
    else:
        r_out, l_out, f_out = r1, l1, f1
    node["r"], node["l"], node["f"] = r_out, l_out, f_out
    decayed_arg = new_agitation * (1 - AGITATION_DECAY_RATE)
    node["agitation"] = decayed_arg if decayed_arg > 0 else (0 - 0.0)
    return True


def p7_persist_baselines(node: Node, anchored: bool) -> bool:
    """p7-persist-baselines — the persistent previous-values re-homed to
    node fields (digest gap 4): next tick's deltas read this tick's
    declared flow. Anchored classes only."""
    if not anchored:
        return False
    node["previous_wages"] = opt(node, "wages_received", 0)
    node["previous_wealth"] = opt(node, "wealth", 0)
    return True


def p8_dominant(world: World) -> int:
    """p8-dominant-worldview (landed Task 2): argmax, then the ruled tie
    order LIBERAL > REVOLUTIONARY > FASCIST within a STRICT 1e-6 of the max
    (consciousness.py:177-192, verbatim)."""
    fired = 0
    for node in world.values():
        if not is_class(node) or "active" not in node:
            continue
        r = opt(node, "r", 0.0)
        lib = opt(node, "l", 0.0)
        f = opt(node, "f", 0.0)
        if node["active"] == 1 and r + (lib + f) > 0:
            fired += 1
            mx = (r if r >= f else f) if r >= lib else (lib if lib >= f else f)
            dr = (r - mx) if r > mx else (mx - r)
            dl = (lib - mx) if lib > mx else (mx - lib)
            node["dominant"] = (
                "LIBERAL"
                if dl < DOMINANT_EPSILON
                else ("REVOLUTIONARY" if dr < DOMINANT_EPSILON else "FASCIST")
            )
    return fired


def run_pack(world: World) -> dict[str, int]:
    """One tick of the nine-rule pack, in D116 byte order (p0..p8), against
    the same mutable world — rules run to completion in ascending rule-id
    order and later rules see earlier rules' writes this same tick."""
    fired = {
        "p0": p0_position(world),
        "p1": p1_inbox_reset(world),
        "p2": p2_org_solidarity_push(world),
        "p3": p3_class_solidarity_push(world),
        "p4": 0,
        "p5": 0,
        "p6": 0,
        "p7": 0,
    }
    # p4 / p5 / p6 / p7 — the per-class chain (anchored and positioned gates
    # computed from the same pre-chain node state per rule's own guard).
    for node in world.values():
        if not is_class(node):
            continue
        anchored = opt(node, "wages_paid", -1) >= 0 and opt(node, "value_produced", -1) >= 0
        positioned = ternary_sum(node) > 0
        fired["p4"] += p4_wage_balance(node, anchored)
        fired["p5"] += p5_agitation(node, anchored, positioned)
        fired["p6"] += p6_route(node, positioned)
        fired["p7"] += p7_persist_baselines(node, anchored)
    fired["p8"] = p8_dominant(world)
    return fired


def fmt(value: Scalar) -> str:
    return "ABSENT" if value is ABSENT else repr(value)


def print_tick(world: World, fired: dict[str, int], tick: int) -> None:
    print(f"--- tick {tick} ---")
    print("predicted fired counts (guard-passed subjects per rule):")
    for rule_id in sorted(fired):
        print(f"  consciousness/{rule_id}: {fired[rule_id]}")
    print(f"  total: {sum(fired.values())}")
    print()
    if tick == 1:
        print("p0 seed result for class-emergent's tick-1 start: (0.0, 1.0, 0.0)")
        print()
    header = (
        f"{'node':<24} {'r':<22} {'l':<22} {'f':<22} {'agitation_out':<22} "
        f"{'inbox':<8} {'balance':<22} {'prev_w':<8} {'prev_wealth':<8} dominant"
    )
    print(header)
    for name, node in world.items():
        if not is_class(node):
            continue
        print(
            f"{name:<24} {fmt(node.get('r', ABSENT)):<22} "
            f"{fmt(node.get('l', ABSENT)):<22} {fmt(node.get('f', ABSENT)):<22} "
            f"{fmt(node.get('agitation', ABSENT)):<22} "
            f"{fmt(node.get('solidarity_inbox', ABSENT)):<8} "
            f"{fmt(node.get('wage_balance', ABSENT)):<22} "
            f"{fmt(node.get('previous_wages', ABSENT)):<8} "
            f"{fmt(node.get('previous_wealth', ABSENT)):<8} "
            f"{fmt(node.get('dominant', ABSENT))}"
        )
    print()


def main() -> None:
    world: World = {name: dict(fields) for name, fields in WORLD.items()}
    # Tick 1: the update-law vectors. Tick 2: the ACCUMULATION witness
    # (Controller ruling 2026-08-15, Ruling A extended) — p7 persisted
    # baselines at tick 1, so tick-2 wage/wealth increments are ZERO (that
    # zero is itself the persist machinery's differential witness) and the
    # stored decayed agitation routes again: class-bribed's dominant flips
    # LIBERAL -> FASCIST at tick 2 (hegemony erodes, it doesn't snap).
    fired1 = run_pack(world)
    print_tick(world, fired1, 1)
    fired2 = run_pack(world)
    print_tick(world, fired2, 2)


if __name__ == "__main__":
    main()
