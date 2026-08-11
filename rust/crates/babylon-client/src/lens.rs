//! The three live map lenses (Program 28 B2, Phase C — completes B1's
//! never-built Phase C, generalized to three lenses): `county_tension`
//! (ADR170, Task 8), `county_legitimation` (Task 9), and
//! `county_population_trend` (Task 9b — the one that genuinely moves every
//! tick on this demo content, BLOCKER 2 fix). Each lens computes a raw
//! value only; `map/bands.rs` (Task 10) owns the color mapping.

use babylon_graph::substrate::{GraphSubstrate, NodeId};

/// One lens's live reading: a `(fips, value)` cell per county the lens
/// knows about (`None` = no honest data this tick, never a fabricated
/// zero), plus an optional whole-lens absence reason. Shared shape all
/// three lenses return.
pub struct LensReading {
    pub cells: Vec<(String, Option<f64>)>,
    pub absent_reason: Option<String>,
}

/// The three live `LensReading`s the map can show, refreshed together on
/// every tick advance. `spawn_engine_session_and_hud` (Task 14) is the ONLY
/// inserter, always with a fully-computed literal, in `Startup` — strictly
/// before `recolor_on_lens_changed` (an `Update` system) can ever run, so
/// no earlier reader can observe a missing resource. No `Default` derive on
/// purpose: nothing may construct this half-built.
#[derive(bevy::prelude::Resource)]
pub struct CurrentLensData {
    pub tension: LensReading,
    pub legitimation: LensReading,
    pub population_trend: LensReading,
}

/// Below this, `phi + theta` is the degenerate all-bled-dry limit and `w`
/// collapses to `0.0` — the shared measure kernel's own convention
/// (`babylon.formulas.contradiction.calculate_wealth_asymmetry_gap`,
/// mirrored here for the Rust witness).
const DEGENERATE_EPS: f64 = 1e-9;

/// The two per-territory stamps `v = s / e` recovers from. **No field
/// registry ports these yet** — no shipped rule pack in this repo writes
/// them (confirmed: `vitality`/`lifecycle` touch only their own
/// `social-class/*`/`territory/*` fields, none of these two) — so this
/// lens is UNCONDITIONALLY absent on every scenario this plan ships,
/// exactly as Task 8's own "Related finding" states. Named here, in
/// kebab-case matching every other `territory/*` field in this crate, so
/// the day an economics BSL port lands these two names are the ones it
/// should write.
const TENSION_E_FIELD: &str = "territory/tick-exploitation-rate";
const TENSION_S_FIELD: &str = "territory/tick-total-surplus";

/// The ADR170 `county_extraction` witness, transcribed from
/// `src/babylon/projection/topology/tension.py` unchanged:
/// `phi = v/(v+s)`, `theta = sum(v)/sum(v+s)` (a ratio of sums, never a
/// mean), `w = (phi-theta)/(phi+theta)`, collapsing to `0.0` at
/// `phi+theta <= 1e-9`. A contribution needs BOTH `s > 0` and `e > 0` (the
/// un-hydrated fallback's poisoned zero reads as absence, never as zero
/// tension) — `v = s / e`.
///
/// **Known gap, stated rather than hidden.** This signature takes only
/// `&dyn GraphSubstrate` (matching the plan's own Task 8 interface, unlike
/// `county_legitimation`/`county_population_trend` below, which also take
/// `node_by_fips`) — `GraphSubstrate` has no method recovering a node's
/// FIPS string from its `NodeId` alone (attributes are `f64`-only; §2.9
/// gives no string-valued attribute a home). This function's cell keys are
/// therefore each territory's `NodeId` rendered as a decimal string, NOT a
/// real FIPS code. This is harmless today because the lens is
/// unconditionally absent on this plan's own demo content (no rule pack
/// writes the two fields above) — `map/bands.rs`'s recolor system looks up
/// `atlas.index_of_fips(fips)` per cell and silently skips any key that
/// does not resolve, which every one of these decimal-string keys does. The
/// day a real economics port seeds these fields, whoever wires that content
/// live needs a real fips mapping here too (the same shape
/// `county_legitimation`/`county_population_trend` already carry) —
/// flagged here, not silently worked around.
pub fn county_tension(graph: &dyn GraphSubstrate) -> LensReading {
    let territories = graph.nodes("TERRITORY");

    // (id, v, new_value) for every territory that actually contributes.
    let mut contributions: Vec<(NodeId, f64, f64)> = Vec::new();
    for &id in &territories {
        let e = graph.node_attribute(id, TENSION_E_FIELD).ok();
        let s = graph.node_attribute(id, TENSION_S_FIELD).ok();
        if let (Some(e), Some(s)) = (e, s) {
            if e > 0.0 && s > 0.0 {
                let v = s / e;
                contributions.push((id, v, v + s));
            }
        }
    }

    if contributions.is_empty() {
        return LensReading {
            cells: territories
                .iter()
                .map(|id| (id.0.to_string(), None))
                .collect(),
            absent_reason: Some(
                "no territory carries a positive exploitation-rate/surplus stamp this tick — \
                 no norm exists"
                    .to_owned(),
            ),
        };
    }

    let total_v: f64 = contributions.iter().map(|(_, v, _)| v).sum();
    let total_new_value: f64 = contributions.iter().map(|(_, _, nv)| nv).sum();
    let theta = total_v / total_new_value;

    let phi_by_id: std::collections::HashMap<NodeId, f64> = contributions
        .into_iter()
        .map(|(id, v, nv)| (id, v / nv))
        .collect();

    let cells = territories
        .iter()
        .map(|&id| {
            let key = id.0.to_string();
            match phi_by_id.get(&id) {
                Some(&phi) => {
                    let denom = phi + theta;
                    let w = if denom <= DEGENERATE_EPS {
                        0.0
                    } else {
                        (phi - theta) / denom
                    };
                    (key, Some(w.clamp(-1.0, 1.0)))
                }
                None => (key, None),
            }
        })
        .collect();

    LensReading {
        cells,
        absent_reason: None,
    }
}

/// The `lifecycle` rule pack's own encoded classification (its header
/// comment documents this: 0 = STABLE, 1 = UNSTABLE, 2 = CRISIS).
const LEGITIMATION_CRISIS_FIELD: &str = "territory/legitimation-crisis";

/// `territory/legitimation-crisis`'s three closed values. A straight
/// categorical pass-through — no new cut point, no new math (the standing
/// "no imposed functional forms" ruling).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LegitimationClass {
    Stable,
    Unstable,
    Crisis,
}

/// A plain three-arm match on the encoded float. The encoding is a CLOSED
/// set the rule pack itself defines — anything else is a loud panic, never
/// a silent fallback.
#[must_use]
pub fn classify(raw: f64) -> LegitimationClass {
    if raw == 0.0 {
        LegitimationClass::Stable
    } else if raw == 1.0 {
        LegitimationClass::Unstable
    } else if raw == 2.0 {
        LegitimationClass::Crisis
    } else {
        panic!("territory/legitimation-crisis read an out-of-encoding value: {raw}")
    }
}

/// Reads `territory/legitimation-crisis` for every `(fips, id)` pair in
/// `node_by_fips` and returns `Some(raw_class_as_f64)` per cell — Task 10's
/// `bands.rs` owns the color mapping, matching the Tension lens's own
/// separation of "compute the value" from "pick the color."
///
/// A `node_by_fips` entry naming a `NodeId` this field has never been
/// written on is a WIRING BUG, not an honest absence — unlike Tension's
/// "this county may honestly carry no data," the Phase B demo scenario
/// controls the whole node set and declares this field on every one of its
/// twelve territories. Such an entry panics loudly (III.11) rather than
/// silently reporting `None` — only a FIPS that never appears in
/// `node_by_fips` at all (any of the 3,210 non-demo counties) is the
/// honest "outside the demo, no data this tick" absence, and it never
/// reaches this function in the first place (the caller only ever passes
/// the demo's own `node_by_fips`).
#[must_use]
pub fn county_legitimation(
    graph: &dyn GraphSubstrate,
    node_by_fips: &[(String, NodeId)],
) -> LensReading {
    let cells = node_by_fips
        .iter()
        .map(|(fips, id)| {
            let raw = graph
                .node_attribute(*id, LEGITIMATION_CRISIS_FIELD)
                .unwrap_or_else(|e| {
                    panic!(
                    "demo county {fips} (NodeId {id:?}) has no {LEGITIMATION_CRISIS_FIELD} stamp \
                     — this is a wiring bug (the Phase B scenario declares this field on every \
                     territory), not an honest absence: {e:?}"
                )
                });
            (fips.clone(), Some(raw))
        })
        .collect();

    LensReading {
        cells,
        absent_reason: None,
    }
}

/// The DPD circuit's three genuinely per-tick, per-territory population
/// fields — the ones `lifecycle.bsl`'s Block 1 actually writes, unlike
/// Block 2's const-only legitimation math (Task 9's own finding). Summed,
/// they give a territory's total population.
const POP_D_FIELD: &str = "territory/pop-d";
const POP_P_FIELD: &str = "territory/pop-p";
const POP_D_PRIME_FIELD: &str = "territory/pop-d-prime";

/// For each `(fips, id)` in `node_by_fips`, sums `pop-d + pop-p +
/// pop-d-prime` off the LIVE graph and reports its signed delta against
/// `baseline`'s own entry for that fips — `baseline` is each demo
/// territory's tick-0 total population, captured once by
/// `EngineSession::start` before any `advance()` runs (Task 13). No sign
/// normalization, no size threshold, no clamping — the raw signed delta
/// travels to `map/bands.rs` (Task 10), which does the classification.
///
/// A `fips` present in `node_by_fips` but ABSENT from `baseline` is a
/// wiring bug (both come from the same `EngineSession::start` call) and
/// panics loudly, never resolving to a silent `None` — the same
/// strictness `county_legitimation` applies to its own `node_by_fips`
/// mismatch case. A FIPS outside BOTH slices (any of the 3,210 non-demo
/// counties) never reaches this function at all — the caller only ever
/// passes the demo's own `node_by_fips`/`baseline` pair, so that absence
/// is realized by the recolor system simply never touching that county's
/// mesh vertices, not by a cell this function emits.
#[must_use]
pub fn county_population_trend(
    graph: &dyn GraphSubstrate,
    node_by_fips: &[(String, NodeId)],
    baseline: &[(String, f64)],
) -> LensReading {
    let cells = node_by_fips
        .iter()
        .map(|(fips, id)| {
            let pop_d = graph.node_attribute(*id, POP_D_FIELD).unwrap_or(0.0);
            let pop_p = graph.node_attribute(*id, POP_P_FIELD).unwrap_or(0.0);
            let pop_d_prime = graph.node_attribute(*id, POP_D_PRIME_FIELD).unwrap_or(0.0);
            let now = pop_d + pop_p + pop_d_prime;

            let baseline_total = baseline
                .iter()
                .find(|(baseline_fips, _)| baseline_fips == fips)
                .unwrap_or_else(|| {
                    panic!(
                        "demo county {fips} is in node_by_fips but missing from baseline — \
                         this is a wiring bug (both come from the same EngineSession::start \
                         call), not an honest absence"
                    )
                })
                .1;

            (fips.clone(), Some(now - baseline_total))
        })
        .collect();

    LensReading {
        cells,
        absent_reason: None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_graph::hypergraph_store::HypergraphStore;

    fn territory_with(graph: &mut HypergraphStore, e: f64, s: f64) -> NodeId {
        let id = graph.add_node("TERRITORY").expect("add territory");
        graph.update_node(id, TENSION_E_FIELD, e).expect("stamp e");
        graph.update_node(id, TENSION_S_FIELD, s).expect("stamp s");
        id
    }

    /// (a) Two clean-stamped territories: `theta` (the ratio of sums) must
    /// differ from the mean of the two `phi`s — the single most likely
    /// transcription slip (using a mean instead of a ratio-of-sums).
    #[test]
    fn theta_is_the_ratio_of_sums_not_the_mean_of_phis() {
        let mut graph = HypergraphStore::new();
        // territory 1: e=2, s=10 -> v=5, new_value=15, phi1=1/3
        let id1 = territory_with(&mut graph, 2.0, 10.0);
        // territory 2: e=10, s=100 -> v=10, new_value=110, phi2=10/110
        let id2 = territory_with(&mut graph, 10.0, 100.0);

        let reading = county_tension(&graph);
        assert!(reading.absent_reason.is_none());

        let phi1: f64 = 5.0 / 15.0;
        let phi2: f64 = 10.0 / 110.0;
        let mean_of_phis: f64 = (phi1 + phi2) / 2.0;
        let theta_ratio_of_sums: f64 = (5.0 + 10.0) / (15.0 + 110.0);
        assert!(
            (mean_of_phis - theta_ratio_of_sums).abs() > 1e-6,
            "fixture must make the two candidate thetas differ, or this test cannot \
             distinguish them"
        );

        let w1 = cell_value(&reading, id1);
        let w2 = cell_value(&reading, id2);
        let expected_w1 = {
            let denom = phi1 + theta_ratio_of_sums;
            ((phi1 - theta_ratio_of_sums) / denom).clamp(-1.0, 1.0)
        };
        let expected_w2 = {
            let denom = phi2 + theta_ratio_of_sums;
            ((phi2 - theta_ratio_of_sums) / denom).clamp(-1.0, 1.0)
        };
        assert!(
            (w1 - expected_w1).abs() < 1e-9,
            "got {w1}, want {expected_w1}"
        );
        assert!(
            (w2 - expected_w2).abs() < 1e-9,
            "got {w2}, want {expected_w2}"
        );

        // The mean-of-phis alternative would have produced a DIFFERENT w1 —
        // proving the implementation used the ratio of sums, not the mean.
        let wrong_w1 = {
            let denom = phi1 + mean_of_phis;
            ((phi1 - mean_of_phis) / denom).clamp(-1.0, 1.0)
        };
        assert!((w1 - wrong_w1).abs() > 1e-6);
    }

    /// (b) A net Phi-source (bled) territory scores `w < 0`; a net
    /// Phi-recipient (bribed) territory scores `w > 0`.
    #[test]
    fn bled_scores_negative_and_bribed_scores_positive() {
        let mut graph = HypergraphStore::new();
        // Low phi (wage share far below the norm) -> bled, w < 0.
        let bled = territory_with(&mut graph, 100.0, 1.0); // v=0.01, phi≈0.0099
                                                           // High phi (wage share far above the norm) -> bribed, w > 0.
        let bribed = territory_with(&mut graph, 1.0, 100.0); // v=100, phi≈0.99

        let reading = county_tension(&graph);
        assert!(cell_value(&reading, bled) < 0.0);
        assert!(cell_value(&reading, bribed) > 0.0);
    }

    /// (c) A territory with `s > 0, e == 0` contributes nothing to `theta`
    /// and reports `None` for its own cell, while a genuinely-stamped
    /// sibling still resolves.
    #[test]
    fn a_zero_exploitation_rate_with_positive_surplus_contributes_nothing() {
        let mut graph = HypergraphStore::new();
        let good = territory_with(&mut graph, 2.0, 10.0);
        let broken = territory_with(&mut graph, 0.0, 5.0);

        let reading = county_tension(&graph);
        assert!(
            reading.absent_reason.is_none(),
            "the good territory still carries data"
        );
        assert!(cell_value_opt(&reading, good).is_some());
        assert!(cell_value_opt(&reading, broken).is_none());
    }

    /// (d) A graph where every territory fails the `s>0 && e>0` gate (the
    /// un-hydrated-fallback shape) yields whole-lens absence and every
    /// cell `None`.
    #[test]
    fn no_data_bearing_territory_yields_whole_lens_absence() {
        let mut graph = HypergraphStore::new();
        territory_with(&mut graph, 0.0, 0.0);
        territory_with(&mut graph, 0.0, 0.0);

        let reading = county_tension(&graph);
        assert!(reading.absent_reason.is_some());
        assert_eq!(reading.cells.len(), 2);
        assert!(reading.cells.iter().all(|(_, v)| v.is_none()));
    }

    /// (e) Every returned `w` lands inside `[-1, 1]`, even under an extreme
    /// stamp that would overflow the raw formula without the clamp.
    #[test]
    fn every_w_lands_in_unit_interval() {
        let mut graph = HypergraphStore::new();
        territory_with(&mut graph, 0.0001, 1_000_000.0); // huge v
        territory_with(&mut graph, 1_000_000.0, 0.0001); // tiny v

        let reading = county_tension(&graph);
        for (_, w) in &reading.cells {
            if let Some(w) = w {
                assert!((-1.0..=1.0).contains(w), "w {w} out of [-1, 1]");
            }
        }
    }

    fn cell_value_opt(reading: &LensReading, id: NodeId) -> Option<f64> {
        reading
            .cells
            .iter()
            .find(|(k, _)| k == &id.0.to_string())
            .and_then(|(_, v)| *v)
    }

    fn cell_value(reading: &LensReading, id: NodeId) -> f64 {
        cell_value_opt(reading, id).expect("cell must carry a value")
    }

    fn territory_with_crisis_class(graph: &mut HypergraphStore, class: f64) -> NodeId {
        let id = graph.add_node("TERRITORY").expect("add territory");
        graph
            .update_node(id, LEGITIMATION_CRISIS_FIELD, class)
            .expect("stamp legitimation-crisis");
        id
    }

    #[test]
    fn classify_maps_the_three_encoded_values() {
        assert_eq!(classify(0.0), LegitimationClass::Stable);
        assert_eq!(classify(1.0), LegitimationClass::Unstable);
        assert_eq!(classify(2.0), LegitimationClass::Crisis);
    }

    #[test]
    #[should_panic(expected = "out-of-encoding value")]
    fn classify_panics_loudly_on_an_out_of_encoding_value() {
        let _ = classify(3.0);
    }

    #[test]
    fn county_legitimation_reads_back_the_raw_encoded_class_per_fips() {
        let mut graph = HypergraphStore::new();
        let stable = territory_with_crisis_class(&mut graph, 0.0);
        let unstable = territory_with_crisis_class(&mut graph, 1.0);
        let crisis = territory_with_crisis_class(&mut graph, 2.0);
        let node_by_fips = vec![
            ("00001".to_owned(), stable),
            ("00002".to_owned(), unstable),
            ("00003".to_owned(), crisis),
        ];

        let reading = county_legitimation(&graph, &node_by_fips);
        assert!(reading.absent_reason.is_none());
        assert_eq!(reading.cells.len(), 3);
        assert_eq!(reading.cells[0], ("00001".to_owned(), Some(0.0)));
        assert_eq!(reading.cells[1], ("00002".to_owned(), Some(1.0)));
        assert_eq!(reading.cells[2], ("00003".to_owned(), Some(2.0)));
        assert_eq!(
            classify(reading.cells[0].1.unwrap()),
            LegitimationClass::Stable
        );
        assert_eq!(
            classify(reading.cells[1].1.unwrap()),
            LegitimationClass::Unstable
        );
        assert_eq!(
            classify(reading.cells[2].1.unwrap()),
            LegitimationClass::Crisis
        );
    }

    /// A `node_by_fips` entry naming a `NodeId` the graph never minted (or
    /// never stamped this field on) is a wiring bug — it must panic loudly,
    /// never resolve to a silent `None`.
    #[test]
    #[should_panic(expected = "wiring bug")]
    fn a_node_by_fips_entry_with_no_matching_stamp_panics_loudly() {
        let graph = HypergraphStore::new();
        let node_by_fips = vec![("99999".to_owned(), NodeId(0))];
        let _ = county_legitimation(&graph, &node_by_fips);
    }

    fn territory_with_population(
        graph: &mut HypergraphStore,
        pop_d: f64,
        pop_p: f64,
        pop_d_prime: f64,
    ) -> NodeId {
        let id = graph.add_node("TERRITORY").expect("add territory");
        graph
            .update_node(id, POP_D_FIELD, pop_d)
            .expect("stamp pop-d");
        graph
            .update_node(id, POP_P_FIELD, pop_p)
            .expect("stamp pop-p");
        graph
            .update_node(id, POP_D_PRIME_FIELD, pop_d_prime)
            .expect("stamp pop-d-prime");
        id
    }

    #[test]
    fn a_territory_above_its_baseline_reports_a_positive_delta() {
        let mut graph = HypergraphStore::new();
        let id = territory_with_population(&mut graph, 100.0, 200.0, 50.0); // now = 350
        let node_by_fips = vec![("00001".to_owned(), id)];
        let baseline = vec![("00001".to_owned(), 300.0)];

        let reading = county_population_trend(&graph, &node_by_fips, &baseline);
        assert_eq!(reading.cells, vec![("00001".to_owned(), Some(50.0))]);
    }

    #[test]
    fn a_territory_below_its_baseline_reports_a_negative_delta() {
        let mut graph = HypergraphStore::new();
        let id = territory_with_population(&mut graph, 100.0, 100.0, 50.0); // now = 250
        let node_by_fips = vec![("00001".to_owned(), id)];
        let baseline = vec![("00001".to_owned(), 300.0)];

        let reading = county_population_trend(&graph, &node_by_fips, &baseline);
        assert_eq!(reading.cells, vec![("00001".to_owned(), Some(-50.0))]);
    }

    #[test]
    fn a_territory_exactly_at_its_baseline_reports_exactly_zero() {
        let mut graph = HypergraphStore::new();
        let id = territory_with_population(&mut graph, 100.0, 100.0, 100.0); // now = 300
        let node_by_fips = vec![("00001".to_owned(), id)];
        let baseline = vec![("00001".to_owned(), 300.0)];

        let reading = county_population_trend(&graph, &node_by_fips, &baseline);
        assert_eq!(reading.cells, vec![("00001".to_owned(), Some(0.0))]);
    }

    /// A fips in `node_by_fips` but missing from `baseline` is a wiring bug
    /// (both come from the same `EngineSession::start` call) — panic
    /// loudly, never a silent `None`.
    #[test]
    #[should_panic(expected = "wiring bug")]
    fn a_fips_missing_from_baseline_panics_loudly() {
        let mut graph = HypergraphStore::new();
        let id = territory_with_population(&mut graph, 100.0, 100.0, 100.0);
        let node_by_fips = vec![("00001".to_owned(), id)];
        let baseline: Vec<(String, f64)> = vec![]; // no matching entry
        let _ = county_population_trend(&graph, &node_by_fips, &baseline);
    }
}
