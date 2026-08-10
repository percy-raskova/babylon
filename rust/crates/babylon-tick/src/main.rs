//! `babylon-tick` — the Phase 2 Slice 1 driver.
//!
//! ```text
//! babylon-tick <scenario.bscn> <rule.bsl>
//! ```
//!
//! Loads a world, loads a rule through every gate, runs one tick, and prints
//! the state hash. Running it twice on the same inputs must print the same
//! hash; that is Constitution III.7 made observable from a shell rather than
//! only from a test.
//!
//! # Where the content lives
//!
//! `content/` **inside this crate**, not at the repo root. §2.2 of the
//! language spec says a content set is "the union of all files under the
//! declared content roots" — *declared*, and plural, so the durable content
//! root is configuration and choosing one is an architecture decision this
//! slice has no standing to make. Until it is declared, this crate's example
//! content is scoped to this crate, where it is unambiguously the driver's
//! demonstration data rather than a claim about where game content belongs.
//!
//! **This is not `babylon-engine`.** The engine — anchor total-order
//! resolution, the system registry, a tick *sequence* — is Phase 3, and
//! naming this binary as though it were would be claiming ground that has
//! not been taken. It drives ONE rule over ONE scenario for ONE tick. When
//! Phase 3 charters the engine, this either becomes its first command or is
//! absorbed and deleted; either way the slice's evidence survives in
//! `babylon-bsl`'s tests, which do not depend on this binary existing.
//!
//! Exit status is 0 on a completed tick and 1 on any failure, with the
//! reason on stderr — a driver that printed a hash for a failed run would be
//! worse than one that printed nothing.

use babylon_bsl::fuel::{CardinalityCeilings, IntrinsicCosts};
use babylon_bsl::intrinsic_host::EmptyIntrinsicHost;
use babylon_bsl::rule_pipeline::{load_rule, LoadContext};
use babylon_bsl::scenario::load_scenario;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_bsl::tick::run_tick;
use babylon_bsl::typecheck::TypeEnv;
use babylon_bsl::BindingVocabulary;
use babylon_graph::memory::MemoryGraph;
use std::collections::{HashMap, HashSet};
use std::process::ExitCode;

fn hex(bytes: &[u8; 32]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    let [_, scenario_path, rule_path] = args.as_slice() else {
        eprintln!("usage: babylon-tick <scenario.bscn> <rule.bsl>");
        return ExitCode::FAILURE;
    };

    match run(scenario_path, rule_path) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("babylon-tick: {message}");
            ExitCode::FAILURE
        }
    }
}

fn run(scenario_path: &str, rule_path: &str) -> Result<(), String> {
    let scenario_src = std::fs::read_to_string(scenario_path)
        .map_err(|e| format!("cannot read scenario {scenario_path}: {e}"))?;
    let rule_src = std::fs::read_to_string(rule_path)
        .map_err(|e| format!("cannot read rule {rule_path}: {e}"))?;

    let mut graph = MemoryGraph::new();
    let scenario = load_scenario(&scenario_src, &mut graph).map_err(|e| e.to_string())?;

    let before = graph
        .state_hash()
        .map_err(|e| format!("pre-tick state: {}", e.message))?;

    // The scenario's `deffield` forms ARE the registries for slice 1. When
    // Phase 2's content registries land they replace this wholesale; until
    // then a field's type and intensivity come from a declaration rather
    // than from a guess about its stored value.
    let types = TypeEnv {
        fields: scenario.fields.clone(),
        exemptions: &[],
    };
    let vocabulary = BindingVocabulary {
        fields: scenario.fields.keys().cloned().collect(),
        consts: HashSet::new(),
        metrics: HashSet::new(),
    };
    // One ceiling per node type the scenario ACTUALLY minted, keyed as the
    // bound checker expects (`NodeType/MEMBER`). Hard-coding a single type
    // would make this driver silently specific to `SOCIAL_CLASS`: any rule
    // querying another type would fail load with `MissingCeiling`, which is
    // a confusing way to say "this driver only ever supported one type".
    //
    // A type the scenario declared zero of still gets no ceiling — and that
    // is correct: a rule querying a population that does not exist should
    // fail loudly at load rather than quietly iterate nothing.
    let ceilings = CardinalityCeilings::new(
        scenario
            .node_types
            .iter()
            .map(|(member, count)| (format!("NodeType/{member}"), *count))
            .collect(),
        HashMap::new(),
    );
    let intrinsics = IntrinsicCosts::default();
    let systems: HashSet<String> = HashSet::from([
        "economics".to_owned(),
        "vitality".to_owned(),
        "consciousness".to_owned(),
    ]);

    let ctx = LoadContext {
        vocabulary: &vocabulary,
        types: &types,
        ceilings: &ceilings,
        intrinsics: &intrinsics,
        systems: &systems,
        // The R9 chapters' vocabulary-dependent gates (D37's field-init
        // owner rule, D43's domain inference, §2.5's foreign-`:field`
        // scoping) need a `ClosedVocabulary`. This harness declares none,
        // so they are skipped here rather than run against a guess — the
        // registry is Phase-2 content work.
        vocabulary_registry: None,
        rule_file: rule_path,
    };
    let loaded = load_rule(&rule_src, &ctx).map_err(|e| format!("rule rejected: {e}"))?;

    let mut sink = CollectingSink::default();
    let outcome = run_tick(
        &loaded,
        &types,
        &EmptyIntrinsicHost,
        &mut graph,
        &mut sink,
        &intrinsics,
    )
    .map_err(|e| format!("tick failed: {e}"))?;

    let after = graph
        .state_hash()
        .map_err(|e| format!("post-tick state: {}", e.message))?;

    println!("scenario  {}", scenario.id);
    let mut populations: Vec<String> = scenario
        .node_types
        .iter()
        .map(|(member, count)| format!("{count} {member}"))
        .collect();
    populations.sort();
    println!(
        "world     {} nodes ({}), {} edges, {} fields declared",
        scenario.node_count,
        populations.join(", "),
        scenario.edge_count,
        scenario.fields.len()
    );
    println!(
        "tick 1    {} of {} {} subjects fired",
        outcome.fired, outcome.considered, outcome.subject_type
    );
    println!("before    {}", hex(&before));
    println!("after     {}", hex(&after));
    if before == after {
        // Not an error — a tick where no guard passed is a real outcome, and
        // saying so beats leaving the reader to compare 64 hex digits.
        println!("note      state unchanged: no subject passed the guard");
    }
    Ok(())
}
