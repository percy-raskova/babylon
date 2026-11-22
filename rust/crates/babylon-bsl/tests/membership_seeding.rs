//! A scenario seeds a membership's values at hydration (Amendment AG clause i, §3.9 clause 6): the
//! annotated `(member <NodeType/X> <name> (<qname> <value>)*)` item, its refusals and their codes.

use babylon_bsl::scenario::{self, ScenarioError};
use babylon_graph::memory::MemoryGraph;
use babylon_graph::substrate::GraphSubstrate;

const PRELUDE: &str = "(defvocabulary NodeType (SOCIAL_CLASS PERIPHERY))
  (defvocabulary HyperedgeType (NATION))
  (deffield nation/households int extensive :member NodeType/SOCIAL_CLASS)
  (deffield nation/share probability intensive :member NodeType/SOCIAL_CLASS)
  (deffield nation/label int extensive)
  (node g1 NodeType/SOCIAL_CLASS)
  (node g2 NodeType/SOCIAL_CLASS)
  (node p1 NodeType/PERIPHERY)";

fn load(body: &str) -> Result<MemoryGraph, Box<ScenarioError>> {
    let mut graph = MemoryGraph::new();
    let source = format!("(scenario ft/seed {PRELUDE} {body})");
    scenario::load_scenario(&source, &mut graph).map_err(Box::new)?;
    Ok(graph)
}

fn refusal(body: &str) -> ScenarioError {
    *load(body).expect_err("the hydration is refused")
}

#[test]
fn annotated_members_seed_their_values() {
    let graph = load(
        "(hyperedge n1 HyperedgeType/NATION (members
           (member NodeType/SOCIAL_CLASS g1 (nation/households 120) (nation/share 0.5p))
           (member NodeType/SOCIAL_CLASS g2 (nation/share 0.25p) (nation/households 7))))
         (hyperedge n2 HyperedgeType/NATION (members
           (member NodeType/SOCIAL_CLASS g1 (nation/households 30) (nation/share 1))))",
    )
    .expect("an annotated hydration loads");
    let nations = graph.hyperedges("NATION");
    assert_eq!(nations.len(), 2);
    let classes = graph.nodes("SOCIAL_CLASS");
    let (g1, g2) = (classes[0], classes[1]);
    let read = |n: usize, m, q: &str| {
        graph
            .membership_attribute(nations[n], m, q)
            .expect("a seeded value")
    };
    assert!((read(0, g1, "nation/households") - 120.0).abs() < 1e-12);
    assert!((read(0, g1, "nation/share") - 0.5).abs() < 1e-12);
    assert!((read(0, g2, "nation/households") - 7.0).abs() < 1e-12);
    assert!((read(0, g2, "nation/share") - 0.25).abs() < 1e-12);
    // The same group in the other nation keeps its own value.
    assert!((read(1, g1, "nation/households") - 30.0).abs() < 1e-12);
    assert!(graph.is_member(nations[1], g1).expect("known pair"));
    assert!(!graph.is_member(nations[1], g2).expect("known pair"));
}

#[test]
fn a_hydration_omitting_a_payload_field_is_e_load_047() {
    let e = refusal(
        "(hyperedge n1 HyperedgeType/NATION (members
           (member NodeType/SOCIAL_CLASS g1 (nation/households 120))))",
    );
    assert_eq!(e.code, Some("E-LOAD-047"), "{}", e.message);
}

#[test]
fn a_bare_item_under_a_payload_type_is_e_load_047() {
    let e = refusal("(hyperedge n1 HyperedgeType/NATION (members g1))");
    assert_eq!(e.code, Some("E-LOAD-047"), "{}", e.message);
}

#[test]
fn a_bare_item_of_an_unannotated_member_type_keeps_its_meaning() {
    let graph = load(
        "(hyperedge n1 HyperedgeType/NATION (members p1
           (member NodeType/SOCIAL_CLASS g1 (nation/households 1) (nation/share 1))))",
    )
    .expect("a member type with no declared fields stays bare");
    assert_eq!(graph.hyperedges("NATION").len(), 1);
}

#[test]
fn a_payload_field_twice_is_e_parse_041() {
    let e = refusal(
        "(hyperedge n1 HyperedgeType/NATION (members
           (member NodeType/SOCIAL_CLASS g1
             (nation/households 1) (nation/households 2) (nation/share 1))))",
    );
    assert_eq!(e.code, Some("E-PARSE-041"), "{}", e.message);
}

#[test]
fn a_foreign_qname_is_e_type_014() {
    // A plain hyperedge field, and a field owned by another type, are not this membership's.
    for qname in ["nation/label", "social-class/wages"] {
        let e = refusal(&format!(
            "(deffield social-class/wages int extensive)
             (hyperedge n1 HyperedgeType/NATION (members
               (member NodeType/SOCIAL_CLASS g1
                 (nation/households 1) (nation/share 1) ({qname} 5))))"
        ));
        assert_eq!(e.code, Some("E-TYPE-014"), "{qname}: {}", e.message);
    }
}

#[test]
fn a_member_not_of_the_annotated_type_is_e_eval_033() {
    let e = refusal(
        "(hyperedge n1 HyperedgeType/NATION (members
           (member NodeType/SOCIAL_CLASS p1 (nation/households 1) (nation/share 1))))",
    );
    assert_eq!(e.code, Some("E-EVAL-033"), "{}", e.message);
}

#[test]
fn an_int_payload_past_2_pow_53_is_refused() {
    let e = refusal(
        "(hyperedge n1 HyperedgeType/NATION (members
           (member NodeType/SOCIAL_CLASS g1
             (nation/households 9007199254740993) (nation/share 1))))",
    );
    assert!(e.message.contains("exact integer range"), "{}", e.message);
    let e = refusal(
        "(hyperedge n1 HyperedgeType/NATION (members
           (member NodeType/SOCIAL_CLASS g1 (nation/households 1) (nation/share 6))))",
    );
    assert!(e.message.contains("nation/share"), "{}", e.message);
}
