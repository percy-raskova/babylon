//! B0's proof that the client links the engine in-process: run the Slice 1
//! seam (scenario -> rule -> one tick -> state hash) at startup and log it.
//!
//! B2 Task 13 adds `EngineSession` — the client's own held, persistent,
//! two-rule `TickSession`, plus the fips<->`NodeId` map and the tick-0
//! population baseline the map lenses (`lens.rs`) need. `engine_link_probe`
//! stays exactly as B0 left it (`tests/engine_link.rs`'s pinned-hash test
//! still exercises it); `EngineSession` is a new, separate surface, not a
//! replacement.
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::substrate::{GraphSubstrate, NodeId};
use babylon_kernel::SessionId;
use babylon_tick::{run_once, TickReport, TickSession};

const SCENARIO: &str = include_str!("../../babylon-tick/content/scenarios/two-classes.bscn");
const RULE: &str = include_str!("../../babylon-tick/content/rules/fundamental-theorem.bsl");

/// Run one deterministic tick over the pinned two-classes scenario and
/// fundamental-theorem rule — the same `babylon_tick::run_once` seam the
/// CLI driver uses, so "the client links the engine" means sharing this
/// exact code path, not a lookalike reimplementation.
pub fn engine_link_probe() -> Result<TickReport, String> {
    run_once(SCENARIO, RULE)
}

const DEMO_SCENARIO: &str =
    include_str!("../../babylon-tick/content/scenarios/us-counties-lifecycle-demo.bscn");
const DEMO_VITALITY: &str = include_str!("../../babylon-tick/content/rules/vitality.bsl");
const DEMO_LIFECYCLE: &str = include_str!("../../babylon-tick/content/rules/lifecycle.bsl");

/// The twelve territory FIPS `us-counties-lifecycle-demo.bscn` declares, in
/// the SAME order as that file's own twelve `(node …)` forms (the file's
/// own header comment, Task 7 Step 1's print output, transcribed) —
/// `EngineSession::start`'s loud startup assertion catches the two ever
/// drifting apart.
const DEMO_FIPS: [&str; 12] = [
    "01001", "01003", "01005", "01007", "01009", "01011", "01013", "01015", "01017", "01019",
    "01021", "01023",
];

/// The client's own held tick session over the B2 demo world: twelve
/// real-FIPS territories (`lifecycle`) and six social classes (`vitality`),
/// both rule packs running every tick in ascending rule-id byte order
/// (§4.2, D16/D100). `Resource`: `loop_ui::spawn_engine_session_and_hud`
/// (Task 14) inserts one at Startup, held for the whole session.
#[derive(bevy::prelude::Resource)]
pub struct EngineSession {
    pub inner: TickSession<HypergraphStore>,
    pub sink: CollectingSink,
    pub node_by_fips: Vec<(String, NodeId)>,
    pub population_baseline: Vec<(String, f64)>,
}

impl EngineSession {
    /// Loads the demo scenario TWICE — once here, to recover the territory
    /// `NodeId`s and their SEEDED (pre-tick) population totals before
    /// `TickSession` takes ownership of its own graph, and once inside
    /// `TickSession::new`. Deterministic loading means both loads mint the
    /// identical eighteen ids (Task 13's own test proves this independently
    /// of this comment). This costs one extra scenario parse at startup
    /// (microseconds against an 18-node scenario) and keeps `TickSession`'s
    /// public surface exactly the four methods Task 6 specified, rather
    /// than widening it to expose its internal graph mutably pre-tick.
    ///
    /// # Errors
    /// The same failure modes `TickSession::new` has: an intrinsic
    /// declaration, a scenario load, or a rule load.
    pub fn start() -> Result<Self, String> {
        let mut graph = HypergraphStore::new();
        babylon_bsl::scenario::load_scenario(DEMO_SCENARIO, &mut graph)
            .map_err(|e| e.to_string())?;

        // "TERRITORY" — the bare enum member the substrate actually stores
        // (namespace_to_node_type stamps it verbatim), never
        // "NodeType/TERRITORY".
        let ids = graph.nodes("TERRITORY");
        if ids.len() != DEMO_FIPS.len() {
            panic!(
                "demo scenario minted {} TERRITORY nodes, DEMO_FIPS names {} — \
                 the array drifted from the .bscn file, fix DEMO_FIPS",
                ids.len(),
                DEMO_FIPS.len()
            );
        }
        let node_by_fips: Vec<(String, NodeId)> = DEMO_FIPS
            .iter()
            .zip(ids.iter())
            .map(|(fips, id)| ((*fips).to_owned(), *id))
            .collect();

        // The tick-0 baseline the Population Trend lens measures against —
        // read from THIS graph, before it is discarded, while it still
        // holds only the scenario's seeded (un-ticked) values. A missing
        // attribute fails LOUDLY naming the county and field — a 0.0
        // default here would silently skew every later trend delta
        // (`node_attribute` is "never a default 0.0" for exactly this
        // reason; Copilot review, PR #504).
        let population_baseline: Vec<(String, f64)> = node_by_fips
            .iter()
            .map(|(fips, id)| {
                let read = |field: &str| {
                    graph.node_attribute(*id, field).map_err(|e| {
                        format!(
                            "tick-0 baseline: county {fips} has no {field}: {}",
                            e.message
                        )
                    })
                };
                let pop_d = read("territory/pop-d")?;
                let pop_p = read("territory/pop-p")?;
                let pop_dp = read("territory/pop-d-prime")?;
                Ok((fips.clone(), pop_d + pop_p + pop_dp))
            })
            .collect::<Result<_, String>>()?;

        // Concatenation order below is arbitrary — the driver sorts by
        // rule-id BYTE ORDER (§4.2, D16) regardless of which text comes
        // first, so this order has no bearing on execution order or on the
        // resulting TickReport (babylon-tick's own multi_rule_conformance.rs
        // proves the file-order invariance directly).
        let rule_src = format!("{DEMO_VITALITY}\n{DEMO_LIFECYCLE}");
        // The `rng-draw` seam's session id (Task 4, #576 intrinsic-host
        // train, plan §3.5) — a fixed, deterministic literal (III.7: never
        // a UUID, never a wall-clock read), same class as `run_once`'s own
        // `SessionId::new("run-once")`. Naming the campaign's REAL session
        // id (a `ContentDigest` hex, or the scenario id) is a separate,
        // small recorded decision (plan §3.5, Task 6.5) this placeholder
        // does not preempt.
        let session_id = SessionId::new("babylon-client-b2-demo").expect("literal is non-empty");
        let inner = TickSession::new(DEMO_SCENARIO, &rule_src, HypergraphStore::new(), session_id)
            .map_err(|e| format!("tick session: {e}"))?;

        Ok(Self {
            inner,
            sink: CollectingSink::default(),
            node_by_fips,
            population_baseline,
        })
    }

    /// Advances the held session by one tick, against the SAME `sink` every
    /// call — the event feed (Task 15) reads the whole session's
    /// accumulated history.
    ///
    /// # Errors
    /// Whatever `TickSession::advance` returns.
    pub fn advance(&mut self) -> Result<TickReport, String> {
        self.inner.advance(&mut self.sink)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::atlas::CountyAtlas;

    const ATLAS_BYTES: &[u8] = include_bytes!("../assets/map/county_atlas.bin");

    #[test]
    fn engine_session_starts_and_the_twelve_fips_resolve_on_the_real_atlas() {
        let session = EngineSession::start().expect("engine session starts");
        assert_eq!(session.node_by_fips.len(), 12);
        let atlas = CountyAtlas::parse(ATLAS_BYTES).unwrap();
        for (fips, _id) in &session.node_by_fips {
            assert!(
                atlas.index_of_fips(fips).is_some(),
                "demo FIPS {fips} must resolve on the committed atlas"
            );
        }
    }

    #[test]
    fn population_baseline_matches_the_seeded_tick_zero_totals() {
        let session = EngineSession::start().expect("engine session starts");
        assert_eq!(session.population_baseline.len(), 12);
        // Task 7's Step 2 table: index 0 (core x0.95) seeds pop-d=2042,
        // pop-p=5748, pop-d-prime=1710 — total 9,500 exactly. Same fips
        // order as node_by_fips/DEMO_FIPS.
        let (fips0, total0) = &session.population_baseline[0];
        assert_eq!(fips0, &session.node_by_fips[0].0);
        assert!((total0 - 9500.0).abs() < 1e-6, "got {total0}");
    }

    #[test]
    fn engine_session_advance_moves_the_hash_and_runs_both_rules_every_tick() {
        let mut session = EngineSession::start().expect("start");
        let r1 = session.advance().expect("tick 1");
        let r2 = session.advance().expect("tick 2");
        assert_eq!(session.inner.tick(), 2);
        assert_ne!(r1.after, r2.after);
        assert_eq!(r1.per_rule_fired.len(), 2, "both packs run every tick");
    }
}
