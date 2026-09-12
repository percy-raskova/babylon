//! Companion worlds must retain the canonical declarations of fractional fields.
//!
//! Numeric output checks alone do not catch this drift: the current graph store
//! accepts fractional writes into an `int` field, although the scenario loader
//! refuses fractional seeds for that declaration. Load the real worlds through
//! the same loader their rule consumers use and compare both type and kind.

use std::path::Path;

use babylon_bsl::scenario::{load_scenario, LoadedScenario};
use babylon_bsl::types::BslType;
use babylon_graph::memory::MemoryGraph;

struct FieldFamily {
    canonical: &'static str,
    fields: &'static [&'static str],
    companions: &'static [&'static str],
}

const FAMILIES: &[FieldFamily] = &[
    FieldFamily {
        canonical: "metabolism-conformance.bscn",
        fields: &["territory/biocapacity", "territory/max-biocapacity"],
        companions: &[
            "metabolism-ceiling-conformance.bscn",
            "metabolism-ceiling-suppression-conformance.bscn",
            "metabolism-entropy-high-conformance.bscn",
            "metabolism-entropy-low-conformance.bscn",
            "metabolism-extreme-damage-conformance.bscn",
            "metabolism-ratcheted-ceiling-conformance.bscn",
            "metabolism-rounding-divergence-conformance.bscn",
        ],
    },
    FieldFamily {
        canonical: "dispossession-conformance.bscn",
        fields: &["territory/wealth", "territory/dispossession-intensity"],
        companions: &[
            "dispossession-ceiling-matrix-conformance.bscn",
            "dispossession-negative-input-conformance.bscn",
            "dispossession-negative-weight-conformance.bscn",
            "dispossession-saturation-conformance.bscn",
            "dispossession-single-rate-conformance.bscn",
            "dispossession-zero-rate-conformance.bscn",
        ],
    },
    FieldFamily {
        canonical: "lifecycle-conformance.bscn",
        fields: &[
            "territory/pop-d",
            "territory/pop-p",
            "territory/pop-d-prime",
            "territory/wealth-d-prime",
            "territory/dependency-ratio",
            "territory/legitimation-index",
            "territory/transmitted-ideology",
        ],
        companions: &[
            "lifecycle-crisis-conformance.bscn",
            "vitality-lifecycle-combined-conformance.bscn",
            "us-counties-lifecycle-demo.bscn",
        ],
    },
    FieldFamily {
        canonical: "vitality-conformance.bscn",
        fields: &["social-class/wealth"],
        companions: &[
            "vitality-lifecycle-combined-conformance.bscn",
            "us-counties-lifecycle-demo.bscn",
        ],
    },
];

fn load_world(filename: &str) -> LoadedScenario {
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../babylon-tick/content/scenarios")
        .join(filename);
    let source = std::fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("reading {}: {error}", path.display()));
    load_scenario(&source, &mut MemoryGraph::new())
        .unwrap_or_else(|error| panic!("loading {}: {error}", path.display()))
}

#[test]
fn fractional_fields_agree_with_their_canonical_scenarios() {
    let mut mismatches = Vec::new();
    for family in FAMILIES {
        let canonical = load_world(family.canonical);
        for field in family.fields {
            let expected = canonical.fields.get(*field).unwrap_or_else(|| {
                panic!("{} is missing canonical field {field}", family.canonical)
            });
            assert_eq!(
                expected.ty,
                BslType::Real,
                "{} {field} must admit fractional values",
                family.canonical
            );
        }
        for filename in family.companions {
            let companion = load_world(filename);
            for field in family.fields {
                let expected = &canonical.fields[*field];
                match companion.fields.get(*field) {
                    Some(actual) if actual.ty == expected.ty && actual.kind == expected.kind => {}
                    actual => mismatches.push(format!(
                        "{filename} {field}: {actual:?}; expected {expected:?} from {}",
                        family.canonical
                    )),
                }
            }
        }
    }
    assert!(
        mismatches.is_empty(),
        "fractional field declarations drifted:\n{}",
        mismatches.join("\n")
    );
}
