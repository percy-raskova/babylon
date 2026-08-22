//! The Community @6.0 port train's conformance suite (issue #667, plan
//! `docs/superpowers/plans/2026-08-18-community-port.md`, Task 7) — world 1
//! (`content/scenarios/community-conformance.bscn`), the frozen mirror
//! (`content/scenarios/community_conformance.py`), THE SPIKE's seven-shape
//! verdicts, and §8c's four permanent anti-pattern guards (landed here,
//! never deleted).
//!
//! # Task 7 deviations from the plan's letter (both recorded, both forced)
//!
//! 1. **Step 1's "expected FAIL (unregistered system)" never red-fired**:
//!    the `community` namespace was registered in `lib.rs`'s systems
//!    `HashSet` at **Task 4** (#681), one task earlier than the plan's
//!    Step 2 — the ceiling supply chain's RED tests needed the two refusal
//!    codes specifically, and an unregistered namespace fails E-LOAD-004
//!    one stage earlier (the registration comment in `lib.rs` says all of
//!    this). So this suite's load-smoke was green from birth; Step 2's
//!    "confirming the entry is genuinely new" discharges by READING that
//!    comment, not by re-adding the entry.
//! 2. **The "empty rule source" deviation, inherited**: `run_once_into`'s
//!    `split_content` refuses a content set with zero `(rule …)` top-forms
//!    outright (`decomposition_conformance.rs`'s Step-1 note and
//!    `production_conformance.rs:75-94` record the same), so the smoke
//!    test drives ONE minimal, never-firing probe rule.
//!
//! # The mirror's verbatim stdout (2026-08-22, python3 3.13)
//!
//! `community_conformance.py` is THE ORACLE (§9: standalone, no `babylon`
//! import, transcribing the planned rules c00→c11 over the literal WORLD).
//! Tasks 8-11 pin bit-exact against these values via the `.to_bits()`
//! idiom — **exact equality, no tolerance**, because every value here is
//! the same IEEE-754 operation chain the rules transcribe (the mirror's
//! header states the operation order per accumulator; shortest-repr
//! decimals round-trip through Rust's correctly-rounded parser to the same
//! binary64):
//!
//! ```text
//! community-conformance world 1 — mirror output (the oracle)
//! h0 new-afrikan kind=NEW_AFRIKAN
//!   member-count = 2.0
//!   r-raw = 0.4
//!   l-raw = 0.0625
//!   f-raw = 0.0
//!   density-sum  = 1.5
//!   r = 0.8648648648648649
//!   l = 0.13513513513513511
//!   f = 0.0
//!   contestation = 0.36048485321765583   (DG-2-gated)
//!   dominant     = REVOLUTIONARY   (DG-2-gated)
//!   decayed heat               = 0.475
//!   decayed cohesion           = 0.7275
//!   decayed education-pressure = 0.225
//! h1 settler kind=SETTLER
//!   member-count = 1.0
//!   r-raw = 0.0
//!   l-raw = 0.125
//!   f-raw = 0.125
//!   density-sum  = 2.0
//!   r = 0.0
//!   l = 0.5
//!   f = 0.5
//!   contestation = 0.6309297535714574   (DG-2-gated)
//!   dominant     = LIBERAL   (DG-2-gated)
//!   decayed heat               = 0.2375
//!   decayed cohesion           = 0.485
//!   decayed education-pressure = 0.1125
//! h2 queer kind=QUEER
//!   member-count = 1.0
//!   r-raw = 0.4
//!   l-raw = 0.125
//!   f-raw = 0.0
//!   density-sum  = 2.0
//!   r = 0.7619047619047619
//!   l = 0.23809523809523808
//!   f = 0.0
//!   contestation = 0.4996069952489026   (DG-2-gated)
//!   dominant     = REVOLUTIONARY   (DG-2-gated)
//!   decayed heat               = 0.7124999999999999
//!   decayed cohesion           = 0.60625
//!   decayed education-pressure = 0.45
//! n1 na-worker: org-r-weight = 0.4, org-l-weight = 0.125, org-f-weight = 0.0, org-count = 2.0
//! n1 na-worker: community-cost-modifier = 1.09375
//! n2 na-organizer: org-r-weight = 0.4, org-l-weight = 0.0, org-f-weight = 0.0, org-count = 1.0
//! n2 na-organizer: community-cost-modifier = 0.875
//! n3 settler-la: org-r-weight = 0.0, org-l-weight = 0.125, org-f-weight = 0.125, org-count = 2.0
//! n3 settler-la: community-cost-modifier = 1.0
//! n4 unaffiliated: org-r-weight = 0.0, org-l-weight = 0.0, org-f-weight = 0.0, org-count = 0.0
//! n4 unaffiliated: community-cost-modifier = 1.0
//! n5 inactive-member: org-r-weight = 0.0, org-l-weight = 0.0, org-f-weight = 0.0, org-count = 0.0
//! n5 inactive-member: community-cost-modifier = ABSENT (honest null)
//! ```text
//! community-conformance world 1 — mirror output (the oracle)
//! h0 new-afrikan kind=NEW_AFRIKAN
//!   member-count = 2.0
//!   density-sum  = 1.5
//!   r = 0.8648648648648649
//!   l = 0.13513513513513511
//!   f = 0.0
//!   contestation = 0.36048485321765583   (DG-2-gated)
//!   dominant     = REVOLUTIONARY   (DG-2-gated)
//!   decayed heat               = 0.475
//!   decayed cohesion           = 0.7275
//!   decayed education-pressure = 0.225
//! h1 settler kind=SETTLER
//!   member-count = 1.0
//!   density-sum  = 2.0
//!   r = 0.0
//!   l = 0.5
//!   f = 0.5
//!   contestation = 0.6309297535714574   (DG-2-gated)
//!   dominant     = LIBERAL   (DG-2-gated)
//!   decayed heat               = 0.2375
//!   decayed cohesion           = 0.485
//!   decayed education-pressure = 0.1125
//! h2 queer kind=QUEER
//!   member-count = 1.0
//!   density-sum  = 2.0
//!   r = 0.7619047619047619
//!   l = 0.23809523809523808
//!   f = 0.0
//!   contestation = 0.4996069952489026   (DG-2-gated)
//!   dominant     = REVOLUTIONARY   (DG-2-gated)
//!   decayed heat               = 0.7124999999999999
//!   decayed cohesion           = 0.60625
//!   decayed education-pressure = 0.45
//! n1 na-worker: community-cost-modifier = 1.09375
//! n2 na-organizer: community-cost-modifier = 0.875
//! n3 settler-la: community-cost-modifier = 1.0
//! n4 unaffiliated: community-cost-modifier = 1.0
//! n5 inactive-member: community-cost-modifier = ABSENT (honest null)
//! ```text
//! community-conformance world 1 — mirror output (the oracle)
//! h0 new-afrikan kind=NEW_AFRIKAN
//!   member-count = 2.0
//!   r-raw = 0.4
//!   l-raw = 0.0625
//!   f-raw = 0.0
//!   density-sum  = 1.5
//!   r = 0.8648648648648649
//!   l = 0.13513513513513511
//!   f = 0.0
//!   contestation = 0.36048485321765583   (DG-2-gated)
//!   dominant     = REVOLUTIONARY   (DG-2-gated)
//!   decayed heat               = 0.475
//!   decayed cohesion           = 0.7275
//!   decayed education-pressure = 0.225
//! h1 settler kind=SETTLER
//!   member-count = 1.0
//!   r-raw = 0.0
//!   l-raw = 0.125
//!   f-raw = 0.125
//!   density-sum  = 2.0
//!   r = 0.0
//!   l = 0.5
//!   f = 0.5
//!   contestation = 0.6309297535714574   (DG-2-gated)
//!   dominant     = LIBERAL   (DG-2-gated)
//!   decayed heat               = 0.2375
//!   decayed cohesion           = 0.485
//!   decayed education-pressure = 0.1125
//! h2 queer kind=QUEER
//!   member-count = 1.0
//!   r-raw = 0.4
//!   l-raw = 0.125
//!   f-raw = 0.0
//!   density-sum  = 2.0
//!   r = 0.7619047619047619
//!   l = 0.23809523809523808
//!   f = 0.0
//!   contestation = 0.4996069952489026   (DG-2-gated)
//!   dominant     = REVOLUTIONARY   (DG-2-gated)
//!   decayed heat               = 0.7124999999999999
//!   decayed cohesion           = 0.60625
//!   decayed education-pressure = 0.45
//! n1 na-worker: org-r-weight = 0.4, org-l-weight = 0.125, org-f-weight = 0.0, org-count = 2.0
//! n1 na-worker: community-cost-modifier = 1.09375
//! n2 na-organizer: org-r-weight = 0.4, org-l-weight = 0.0, org-f-weight = 0.0, org-count = 1.0
//! n2 na-organizer: community-cost-modifier = 0.875
//! n3 settler-la: org-r-weight = 0.0, org-l-weight = 0.125, org-f-weight = 0.125, org-count = 2.0
//! n3 settler-la: community-cost-modifier = 1.0
//! n4 unaffiliated: org-r-weight = 0.0, org-l-weight = 0.0, org-f-weight = 0.0, org-count = 0.0
//! n4 unaffiliated: community-cost-modifier = 1.0
//! n5 inactive-member: org-r-weight = 0.0, org-l-weight = 0.0, org-f-weight = 0.0, org-count = 0.0
//! n5 inactive-member: community-cost-modifier = ABSENT (honest null)
//! ```
//!
//! # THE SPIKE (Task 7 Step 5) — the seven-shape verdicts
//!
//! Each shape below was proven by a THROWAWAY rule against the real
//! `run_once_into` driver and THIS scenario, then deleted (the
//! solidarity-conformance.bscn:9-20 precedent — the scenario header
//! carries the same record). Verdicts:
//!
//! - **(a)** `for-each` over `(hyperedges HyperedgeType/COMMUNITY)` from a
//!   carrier-subject rule — **FIRES** (3 communities × 1 carrier = 3
//!   body-evaluations, verified by a write landing on all three).
//! - **(b)** `(update-hyperedge it community/heat (set …))` inside that
//!   body — **WRITES** (Task 6's own surface; read back bit-exact).
//! - **(c)** `(for-each (hyperedges-of self HyperedgeType/COMMUNITY) …)`
//!   from a SOCIAL_CLASS-subject rule + `(field-of it …)` read inside —
//!   **FIRES and READS** (na-worker sees exactly its two memberships, h0
//!   then h2, and the reads returned the seeded values).
//! - **(d)** repeated `(scale …)` accumulates multiplicatively across a
//!   `for-each` — **PROVEN**: two scales of 0.5c over na-worker's two
//!   memberships landed 1 → 0.25 on the probe field (the operand is
//!   pre-computed per collected write; the COMBINE reads the current value
//!   at APPLY, so the two scales compose as a product — §9 item 2's
//!   pre-state law governs operand evaluation, never the combine).
//! - **(e)** a 14-arm `if`-chain over the enum-field equality (`community/
//!   kind` against each CommunityType member) — **LOADS and EVALUATES**:
//!   each hyperedge's dispatch returned its own floor constant
//!   (0.136/0.0/0.04), the shape §6.2's c06 dispatch needs. The only
//!   landed precedent was 3-arm (`territory.bsl:130-137`); the 14-arm is
//!   now demonstrated, not merely plausible.
//! - **(f)** a same-tick cross-rule read of a hyperedge field written by
//!   an earlier rule — **SEES the new value** (§8b's fatal rows rely on
//!   exactly this; rule-id byte order `community/spike-a` <
//!   `community/spike-b` carried the write → read).
//! - **(g)** the world LOADS with a measured `E-LOAD-040`-bounded
//!   hyperedge-querying rule — Task 4's ceiling supply chain reaches this
//!   scenario: the probe's static bound passed with the census-fed
//!   `HyperedgeType/COMMUNITY` ceiling 3 and max-members 3.
//!
//! No shape refused; §8's rule split stands as planned.
//!
//! # The mirror pin (Task 8+)
//!
//! Tasks 8-11 extend this file with per-rule assertions against the
//! mirror transcript above; Task 7 lands the world, the load-smoke, the
//! ordinal parity, and §8c's four guards only.

use babylon_bsl::scenario::load_scenario;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::substrate::{GraphSubstrate, HyperedgeId, NodeId};
use babylon_tick::run_once_into;

/// The world-1 scenario source, single-homed here — Tasks 8-11's rule
/// packs load against exactly this text.
const SCENARIO: &str = include_str!("../content/scenarios/community-conformance.bscn");

/// The pack source this suite drives — the c00-c04 census/decomposition
/// rules (Task 8); §8c guard 2 reads it, which is what gives the guard
/// teeth (it was vacuous against the Task-7 empty string by design).
const PACK: &str = include_str!("../content/rules/community.bsl");

/// Step 1/7's load-smoke: the world hydrates and ticks clean under one
/// minimal, never-firing probe rule (`active` is 0/1, never 2). The
/// pre/post hashes must be IDENTICAL — a silent probe writes nothing, and
/// the hash brackets the tick, not the hydration.
#[test]
fn scenario_and_empty_pack_load() {
    let probe = r#"
(rule community/load-smoke
  :material-basis "Task 7 Step 1: the load-smoke probe — never fires, proves the world + registration"
  :fuel 64
  (domain NodeType/SOCIAL_CLASS)
  (bindings
    (binding active :field social-class/active))
  (when (= active 2))
  (effects
    (emit EventType/ORGANIZATION_SEEDED (probe 1))))
"#;
    let mut graph = HypergraphStore::new();
    let mut sink = CollectingSink::default();
    let report = run_once_into(SCENARIO, probe, &mut graph, &mut sink)
        .expect("world 1 loads and ticks clean");
    assert_eq!(report.fired, 0, "the probe never fires");
    assert_eq!(
        report.before, report.after,
        "a never-firing probe writes nothing — the hash brackets the tick"
    );
}

/// ADR195 ordinal parity: both enum registries in FROZEN DECLARATION
/// ORDER — CommunityType from `models/enums/community.py:38-55`,
/// ConsciousnessTendency from `models/enums/consciousness.py:82-85`. A
/// transposition here silently re-reads every seeded `community/kind`.
#[test]
fn defenum_ordinal_parity_with_the_frozen_order() {
    let mut graph = HypergraphStore::new();
    let loaded = load_scenario(SCENARIO, &mut graph).expect("world 1 loads");
    let community = loaded
        .enums
        .resolve("CommunityType")
        .expect("CommunityType declared");
    let frozen_order = [
        "SETTLER",
        "PATRIARCHAL",
        "NEW_AFRIKAN",
        "FIRST_NATIONS",
        "CHICANO",
        "WOMEN",
        "TRANS",
        "DISABLED",
        "QUEER",
        "UNDOCUMENTED",
        "INCARCERATED",
        "YOUTH",
        "ADULT",
        "ELDER",
    ];
    for (expected, member) in frozen_order.iter().enumerate() {
        assert_eq!(
            loaded.enums.ordinal(community, member),
            Some(expected as u32),
            "CommunityType/{member} must be ordinal {expected} (frozen declaration order)"
        );
    }
    let tendency = loaded
        .enums
        .resolve("ConsciousnessTendency")
        .expect("ConsciousnessTendency declared");
    for (expected, member) in ["LIBERAL", "FASCIST", "REVOLUTIONARY"].iter().enumerate() {
        assert_eq!(
            loaded.enums.ordinal(tendency, member),
            Some(expected as u32),
            "ConsciousnessTendency/{member} must be ordinal {expected} (frozen declaration order)"
        );
    }
    // …and the seeded kinds read back as those ordinals through the
    // substrate: NEW_AFRIKAN=2, SETTLER=0, QUEER=8.
    for (hid, member, ordinal) in [
        (HyperedgeId(0), "NEW_AFRIKAN", 2.0_f64),
        (HyperedgeId(1), "SETTLER", 0.0_f64),
        (HyperedgeId(2), "QUEER", 8.0_f64),
    ] {
        let stored = graph
            .hyperedge_attribute(hid, "community/kind")
            .expect("kind seeded");
        assert_eq!(
            stored.to_bits(),
            (ordinal).to_bits(),
            "h{}'s kind must store {member}'s ordinal",
            hid.0
        );
    }
}

// ---- §8c's four permanent anti-pattern guards (landed Task 7, NEVER
// deleted — the INV-010 estate's Rust half) ----

/// §8c row 1: communities appear ONLY as hyperedges — no node whose type
/// name contains `COMMUNITY` may exist in the census.
#[test]
fn no_community_typed_node_exists() {
    let mut graph = HypergraphStore::new();
    let loaded = load_scenario(SCENARIO, &mut graph).expect("world 1 loads");
    for (member, count) in &loaded.node_types {
        assert!(
            !member.contains("COMMUNITY"),
            "node type {member} (×{count}) — communities are hyperedges, never nodes (§8c row 1)"
        );
    }
}

/// §8c row 2: no `(binding … :field community/…)` in the pack source —
/// a `:field` binding is node-scoped and stays node-scoped (D29; the
/// mechanism is `tick.rs::subject_type_of`'s owner-kind filter, D202, whose
/// error this guard never wants to see fire on real content). Reads the
/// pack string THIS suite drives — vacuous at Task 7 (PACK is empty),
/// toothed from Task 8 on.
#[test]
fn no_field_binding_uses_the_community_namespace() {
    let mut rest = PACK;
    while let Some(idx) = rest.find("(binding") {
        rest = &rest[idx..];
        let end = rest.find(')').expect("a binding form closes");
        let form = &rest[..=end];
        assert!(
            !(form.contains(":field") && form.contains("community/")),
            "a :field binding owns off the community namespace: {form} — \
             a hyperedge's field reads through field-of / writes through \
             update-hyperedge, never a binding (D29, D202)"
        );
        rest = &rest[1..];
    }
}

/// §8c row 3 (VIII.9 verbatim): a seeded community records ONE hyperedge
/// with N members, never C(n,2) dyadic edges — the world's total edge
/// census is exactly the five org→class MEMBERSHIP edges, and h0 (three
/// members) minted no dyadic clique.
#[test]
fn membership_crosses_whole() {
    let mut graph = HypergraphStore::new();
    let loaded = load_scenario(SCENARIO, &mut graph).expect("world 1 loads");
    assert_eq!(loaded.edge_count, 5, "the five MEMBERSHIP edges, no more");
    assert_eq!(
        loaded.edge_types.get("MEMBERSHIP"),
        Some(&5),
        "every edge is an org→class MEMBERSHIP edge"
    );
    assert_eq!(
        loaded.hyperedge_types.get("COMMUNITY"),
        Some(&3),
        "three communities, as hyperedges"
    );
    // h0's three members are ONE hyperedge — if a clique expansion existed,
    // three more dyadic edges would have appeared above.
    let members = graph
        .hyperedges_of(NodeId(1), "COMMUNITY")
        .expect("na-worker exists");
    assert_eq!(
        members.len(),
        2,
        "na-worker crosses two communities whole (h0, h2)"
    );
}

/// §8c row 4 (§3.7a / C3): every world this pack loads into contains
/// EXACTLY ONE NodeType/INSTITUTION node — never two (each carrier-subject
/// rule would fire twice, double-applying every hyperedge write) and never
/// zero (six rules would iterate an empty population — silent inertness
/// dressed as a passing test).
#[test]
fn exactly_one_institution_carrier() {
    let mut graph = HypergraphStore::new();
    let loaded = load_scenario(SCENARIO, &mut graph).expect("world 1 loads");
    assert_eq!(
        loaded.node_types.get("INSTITUTION"),
        Some(&1),
        "exactly one INSTITUTION carrier — tick.rs's subject derivation \
         iterates EVERY node of the type (D202's filter note), so zero is \
         silent inertness and two is double-applied hyperedge writes"
    );
    // …and it is the anchor: `institution/community-carrier` reads 1.
    let carrier = graph.nodes("INSTITUTION");
    assert_eq!(carrier.len(), 1);
    let anchor = graph
        .node_attribute(carrier[0], "institution/community-carrier")
        .expect("the carrier carries the anchor field");
    assert_eq!(anchor.to_bits(), (1.0_f64).to_bits());
}

// ---- Task 8: c00-c04 — the census and the org-weight decomposition ----
// Every assertion is bit-exact against the mirror (`.to_bits()`, the
// doc-comment transcript above) — no tolerance, per §9.

/// Run the pack over world 1, returning the post-tick graph.
fn tick_world_1() -> HypergraphStore {
    let mut graph = HypergraphStore::new();
    let mut sink = CollectingSink::default();
    let report = run_once_into(SCENARIO, PACK, &mut graph, &mut sink)
        .expect("world 1 + the c00-c04 pack ticks clean");
    assert_eq!(
        report.fired, 18,
        "c00:1 (carrier) + c01:4 (active classes) + c02:5 (all classes) + \
         c03f:1 (fash-org) + c03l:1 (lib-org) + c03r:2 (rev-org AND n9 — \
         n9 is REVOLUTIONARY too; it FIRES with an empty for-each, frozen's \
         :421 skip) + c04:4 (active classes)"
    );
    graph
}

fn he(graph: &HypergraphStore, hid: u64, field: &str) -> f64 {
    graph
        .hyperedge_attribute(HyperedgeId(hid), field)
        .unwrap_or_else(|e| panic!("h{hid} {field}: {}", e.message))
}

fn node(graph: &HypergraphStore, nid: u64, field: &str) -> f64 {
    graph
        .node_attribute(NodeId(nid), field)
        .unwrap_or_else(|e| panic!("n{nid} {field}: {}", e.message))
}

/// Task 8 Step 1: the census counts ACTIVE members only — n5's membership
/// in h0 is real but inactive (frozen community.py:472-474).
#[test]
fn census_counts_only_active_members() {
    let graph = tick_world_1();
    assert_eq!(
        he(&graph, 0, "community/member-count").to_bits(),
        (2.0_f64).to_bits(),
        "h0: n1+n2, n5 excluded"
    );
    assert_eq!(
        he(&graph, 1, "community/member-count").to_bits(),
        (1.0_f64).to_bits(),
        "h1: n3"
    );
    assert_eq!(
        he(&graph, 2, "community/member-count").to_bits(),
        (1.0_f64).to_bits(),
        "h2: n1"
    );
}

/// Task 8 Step 1: n9 (`no-member-org`) has zero MEMBERSHIP edges, so its
/// cadre x cohesion = 1.0 x 1.0 push lands NOWHERE (frozen's :421 skip).
/// The strongest pin: the r-weight total across every class is exactly
/// rev-org's two pushes — 0.8, not 1.8.
#[test]
fn orgs_with_no_members_contribute_nothing() {
    let graph = tick_world_1();
    let r_total: f64 = (1..=5u64) // the five social classes (n0 is the carrier)
        .map(|nid| node(&graph, nid, "social-class/org-r-weight"))
        .sum();
    assert_eq!(
        r_total.to_bits(),
        (0.8_f64).to_bits(),
        "n9's 1.0 push never landed"
    );
    let count_total: f64 = (1..=5u64)
        .map(|nid| node(&graph, nid, "social-class/org-count"))
        .sum();
    assert_eq!(
        count_total.to_bits(),
        (5.0_f64).to_bits(),
        "exactly the five real MEMBERSHIP edges"
    );
}

/// Task 8 Step 1: the pushed weight is cadre x cohesion — n1's l-weight is
/// lib-org's 0.25 x 0.5 = 0.125, never the 0.75 the `+` mutation yields.
#[test]
fn org_weight_is_cadre_times_cohesion() {
    let graph = tick_world_1();
    assert_eq!(
        node(&graph, 1, "social-class/org-l-weight").to_bits(),
        (0.125_f64).to_bits()
    );
    assert_eq!(
        node(&graph, 1, "social-class/org-r-weight").to_bits(),
        (0.4_f64).to_bits(),
        "0.5 x 0.8"
    );
    assert_eq!(
        node(&graph, 3, "social-class/org-f-weight").to_bits(),
        (0.125_f64).to_bits(),
        "0.5 x 0.25"
    );
}

/// Task 8 Step 1: c04's divisor is the SAME-TICK census count (§8b row 1),
/// not a literal and not a stale tick — h0's r-raw is (0.4 + 0.4)/2 = 0.4;
/// h2's is 0.4/1 = 0.4.
#[test]
fn contribution_divides_by_the_census_count() {
    let graph = tick_world_1();
    assert_eq!(
        he(&graph, 0, "community/r-raw").to_bits(),
        (0.4_f64).to_bits()
    );
    assert_eq!(
        he(&graph, 0, "community/l-raw").to_bits(),
        (0.0625_f64).to_bits(),
        "0.125/2, n1 only"
    );
    assert_eq!(
        he(&graph, 2, "community/r-raw").to_bits(),
        (0.4_f64).to_bits(),
        "0.4/1"
    );
    assert_eq!(
        he(&graph, 1, "community/f-raw").to_bits(),
        (0.125_f64).to_bits(),
        "0.125/1"
    );
}

/// Task 8 Step 1: density-sum counts org MEMBERSHIPS (org-count per
/// class), not orgs — h0 reads (2 + 1)/2 = 1.5, not 2/2 = 1.0.
#[test]
fn density_sum_counts_org_memberships_not_orgs() {
    let graph = tick_world_1();
    assert_eq!(
        he(&graph, 0, "community/density-sum").to_bits(),
        (1.5_f64).to_bits()
    );
    assert_eq!(
        he(&graph, 1, "community/density-sum").to_bits(),
        (2.0_f64).to_bits()
    );
    assert_eq!(
        he(&graph, 2, "community/density-sum").to_bits(),
        (2.0_f64).to_bits(),
        "n1's 2 orgs over 1 member"
    );
}
