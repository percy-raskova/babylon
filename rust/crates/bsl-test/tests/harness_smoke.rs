//! Smoke contracts for the `bsl-test` fixture and lint harnesses.

use babylon_bsl::reader::Atom;
use babylon_bsl::reader::SExpr;
use bsl_test::fixture_harness;
use bsl_test::lint_harness;
use std::path::Path;

const CLEAN_RULE: &str = r#"(rule geography/mint
  :role mechanic :evidence derived
  :material-basis "Inline smoke fixture: an ordinary update-node effect."
  :fuel 64
  (bindings)
  (effects (update-node self geography/heat (set 1))))"#;

const ILL_TYPED_RULE: &str = r#"(rule geography/mint
  :role mechanic :evidence derived
  :material-basis "Inline smoke fixture: a fold over an undeclared field."
  :fuel 64
  (bindings
    (binding average :expr (fold mean (nodes NodeType/SOCIAL_CLASS) bsl-test/undeclared)))
  (effects (update-node self geography/heat (set 1))))"#;

#[test]
fn parse_and_typecheck_bsl_accepts_a_well_formed_rule() {
    let parsed = fixture_harness::parse_and_typecheck_bsl(CLEAN_RULE)
        .expect("the smoke rule must parse and typecheck");
    assert!(
        matches!(&parsed, SExpr::List(_)),
        "a parsed rule must stay a list form: {parsed:?}"
    );
}

#[test]
fn parse_and_typecheck_bsl_reports_a_type_failure() {
    let error = fixture_harness::parse_and_typecheck_bsl(ILL_TYPED_RULE)
        .expect_err("an undeclared fold body must fail the typechecker");
    assert!(
        error.contains("unknown field"),
        "the typecheck failure must name the field: {error}"
    );
}

#[test]
fn load_bscn_fixture_returns_the_scenario_form() {
    let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/smoke.bscn");
    let scenario = fixture_harness::load_bscn_fixture(&path).expect("the smoke scenario must load");
    let SExpr::List(items) = scenario else {
        panic!("a .bscn fixture must load as a list form");
    };
    assert!(
        matches!(
            items.first(),
            Some(SExpr::Atom(Atom::Symbol(head))) if head == "scenario"
        ),
        "the fixture must keep its scenario head: {items:?}"
    );
}

#[test]
fn lint_harness_accepts_clean_rust_and_flags_a_style_violation() {
    lint_harness::assert_bsl_lint_clean("pub fn identity(value: u8) -> u8 { value }");
    let findings = lint_harness::run_bsl_check_on_str("pub const MASK: u64 = 0xFF;")
        .expect("the style-violation fixture must be valid Rust");
    assert!(
        findings
            .iter()
            .any(|finding| finding.what.contains("uppercase")),
        "the sentinel must flag uppercase hex digits: {findings:?}"
    );
}

#[test]
fn scenario_fixture_rejects_missing_or_non_qname_identity() {
    for (name, source) in [("missing", "(scenario)"), ("number", "(scenario 123)")] {
        let path =
            std::env::temp_dir().join(format!("bsl-fixture-{}-{name}.bscn", std::process::id()));
        std::fs::write(&path, source).expect("write fixture");
        let result = fixture_harness::load_bscn_fixture(&path);
        std::fs::remove_file(&path).expect("remove fixture");
        assert!(result.is_err(), "{source} must be rejected");
    }
}
