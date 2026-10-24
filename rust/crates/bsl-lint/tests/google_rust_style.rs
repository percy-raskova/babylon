//! Behavioral contracts for the `google-rust-style` AST sentinel.
//!
//! Each test pins one rule from `docs/agents/rust-style.md` or one documented
//! false-positive guard (local functions, tuple-variant constructors, closures,
//! and module imports used as namespaces).

use bsl_lint::finding::{Finding, Severity};
use bsl_lint::google_rust_style;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

const LEAF: &str = "rust/crates/demo/src/leaf.rs";
const LIB: &str = "rust/crates/demo/src/lib.rs";
const CLIENT: &str = "rust/crates/babylon-client/src/app.rs";
const KERNEL: &str = "rust/crates/babylon-kernel/src/lib.rs";

fn check(path: &str, source: &str) -> Vec<Finding> {
    check_at(Path::new(path), source)
}

fn check_at(path: &Path, source: &str) -> Vec<Finding> {
    google_rust_style::check_rust_source(path, source).expect("fixture source must parse as Rust")
}

fn render(findings: &[Finding]) -> String {
    findings
        .iter()
        .map(ToString::to_string)
        .collect::<Vec<_>>()
        .join("\n")
}

fn assert_flags(path: &str, source: &str, needle: &str) {
    let findings = check(path, source);
    assert!(
        findings
            .iter()
            .all(|finding| finding.check == google_rust_style::CHECK),
        "every finding must carry the check identity:\n{}",
        render(&findings)
    );
    assert!(
        findings
            .iter()
            .all(|finding| finding.severity == Severity::Fail),
        "AST style violations must gate:\n{}",
        render(&findings)
    );
    assert!(
        findings
            .iter()
            .any(|finding| finding.what.contains(needle) || finding.evidence.contains(needle)),
        "expected `{needle}` in the findings:\n{}",
        render(&findings)
    );
}

fn assert_clean(path: &str, source: &str) {
    let findings = check(path, source);
    assert!(
        findings.is_empty(),
        "expected no findings, got:\n{}",
        render(&findings)
    );
}

fn fixture(relative: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/google_rust_style")
        .join(relative)
}

fn bsl_lint() -> Command {
    Command::new(env!("CARGO_BIN_EXE_bsl-lint"))
}

fn run(args: &[&str]) -> Output {
    bsl_lint().args(args).output().expect("bsl-lint must run")
}

#[test]
fn a_path_nested_inside_a_use_brace_group_is_flagged() {
    assert_flags(LEAF, "use crate::{alpha::Alpha, beta};\n", "alpha::Alpha");
    assert_flags(
        LEAF,
        "use crate::alpha::{self, beta::Beta};\n",
        "beta::Beta",
    );
}

#[test]
fn a_flat_use_brace_group_is_clean() {
    assert_clean(
        LEAF,
        "use crate::{alpha, beta};\npub use crate::{Alpha, Beta};\n",
    );
}

#[test]
fn an_unrestricted_glob_import_is_flagged() {
    assert_flags(LEAF, "use crate::alpha::*;\n", "glob");
    assert_flags(LEAF, "pub use crate::alpha::*;\n", "glob");
}

#[test]
fn a_super_glob_inside_a_cfg_test_module_is_allowed() {
    let source = "#[cfg(test)]\nmod tests {\n    use super::*;\n}\n";
    assert_clean(LEAF, source);
}

#[test]
fn a_super_glob_outside_a_cfg_test_module_is_flagged() {
    assert_flags(LEAF, "use super::*;\n", "glob");
    assert_flags(LEAF, "mod inner {\n    use super::*;\n}\n", "glob");
}

#[test]
fn the_bevy_prelude_glob_is_allowed_only_in_the_client_crate() {
    assert_clean(CLIENT, "use bevy::prelude::*;\n");
    assert_flags(KERNEL, "use bevy::prelude::*;\n", "glob");
    assert_flags(CLIENT, "use bevy::app::*;\n", "glob");
}

#[test]
fn a_public_glob_reexport_in_a_non_leaf_module_is_allowed() {
    assert_clean(LIB, "pub use alpha::*;\n");
    assert_flags(LIB, "use alpha::*;\n", "glob");
}

#[test]
fn a_local_enum_glob_inside_a_function_is_allowed() {
    let source = "fn run(direction: Direction) {\n    use Direction::*;\n    let _ = direction;\n    let _ = North;\n}\n";
    assert_clean(LEAF, source);
}

#[test]
fn a_module_glob_inside_a_function_is_flagged() {
    assert_flags(LEAF, "fn run() {\n    use crate::alpha::*;\n}\n", "glob");
}

#[test]
fn a_mod_rs_path_is_flagged() {
    assert_flags("rust/crates/demo/src/alpha/mod.rs", "", "mod.rs");
}

#[test]
fn function_and_type_definitions_in_lib_are_flagged() {
    let source = "pub fn build() {}\npub struct Widget;\npub enum Mode {\n    On,\n    Off,\n}\npub trait Render {}\npub const LIMIT: usize = 1;\npub type Alias = u8;\n";
    let findings = check(LIB, source);
    assert_eq!(
        findings.len(),
        4,
        "exactly the fn, struct, enum, and trait must be flagged:\n{}",
        render(&findings)
    );
    for name in ["build", "Widget", "Mode", "Render"] {
        assert!(
            findings
                .iter()
                .any(|finding| finding.evidence.contains(name)),
            "expected `{name}` in the non-leaf findings:\n{}",
            render(&findings)
        );
    }
}

#[test]
fn a_file_beside_its_own_module_directory_is_non_leaf() {
    let widget = fixture("layout/widget.rs");
    let findings = check_at(&widget, "pub fn build() {}\n");
    assert_eq!(
        findings.len(),
        1,
        "a file with a companion directory must not define items:\n{}",
        render(&findings)
    );
}

#[test]
fn a_leaf_file_may_define_items() {
    assert_clean("rust/crates/demo/src/widget.rs", "pub fn build() {}\n");
}

#[test]
fn inline_module_contents_in_lib_are_not_top_level_definitions() {
    assert_clean(LIB, "mod inner {\n    pub fn build() {}\n}\n");
}

#[test]
fn the_process_entry_point_is_not_a_non_leaf_api_definition() {
    assert_clean(LIB, "fn main() {}\n");
    assert_flags(LIB, "fn main() {}\nfn helper() {}\n", "helper");
}

#[test]
fn a_direct_lowercase_free_function_import_is_flagged() {
    let source = "use crate::alpha::beta::my_fn;\n\npub fn run() {\n    my_fn();\n}\n";
    assert_flags(LEAF, source, "my_fn");
}

#[test]
fn a_module_import_used_as_a_namespace_is_clean() {
    let source = "use std::sync::mpsc;\n\npub fn run() {\n    let (_sender, _receiver) = mpsc::channel::<u8>();\n}\n";
    assert_clean(LEAF, source);
}

#[test]
fn a_module_import_whose_name_is_a_local_function_is_clean() {
    let source = "use babylon_bsl::scenario;\n\nfn scenario(body: &str) -> String {\n    body.to_owned()\n}\n\npub fn run() {\n    let _ = scenario(\"x\");\n    let _ = scenario::load();\n}\n";
    assert_clean(LEAF, source);
}

#[test]
fn local_function_and_closure_calls_are_not_free_function_imports() {
    let source = "pub fn run() {\n    let helper = |value: u8| value + 1;\n    let _ = helper(1);\n    local(2);\n}\n\nfn local(value: u8) -> u8 {\n    value\n}\n";
    assert_clean(LEAF, source);
}

#[test]
fn an_inline_module_qualified_type_in_an_expression_is_flagged() {
    let source = "// STYLE-EXCEPTION(EXC-04): test fixture keeps the Arc discount local.\npub fn wrap() -> std::sync::Arc<u8> {\n    std::sync::Arc::new(0)\n}\n";
    assert_flags(LEAF, source, "std::sync::Arc");
}

#[test]
fn an_inline_module_qualified_type_in_a_signature_is_flagged() {
    assert_flags(
        LEAF,
        "pub fn render(value: crate::alpha::Widget) {}\n",
        "crate::alpha::Widget",
    );
}

#[test]
fn qualified_types_with_two_owners_are_disambiguating() {
    assert_clean(
        LEAF,
        "pub fn render(left: crate::alpha::Widget, right: crate::beta::Widget) {}\n",
    );
}

#[test]
fn single_segment_type_constructors_and_local_calls_are_clean() {
    let source = "pub fn build(value: Option<u8>) -> Result<u8, ()> {\n    let _first = Some(value);\n    let _second = Ok(1_u8);\n    let _third = Err(());\n    let _fourth = MyEnum::Variant(1_u8);\n    value.ok_or(())\n}\n";
    assert_clean(LEAF, source);
}

#[test]
fn rustfmt_skip_without_a_marker_is_flagged() {
    assert_flags(
        LEAF,
        "#[rustfmt::skip]\nconst TABLE: [u8; 2] = [0, 1];\n",
        "EXC-05",
    );
}

#[test]
fn rustfmt_skip_with_an_exc_05_marker_is_allowed() {
    let source = "// STYLE-EXCEPTION(EXC-05): manual byte-table alignment\n#[rustfmt::skip]\nconst TABLE: [u8; 2] = [0, 1];\n";
    assert_clean(LEAF, source);
}

#[test]
fn an_arc_without_a_marker_is_flagged() {
    assert_flags(
        LEAF,
        "pub struct Holder {\n    value: Arc<u8>,\n}\n",
        "EXC-04",
    );
}

#[test]
fn an_arc_with_an_exc_04_marker_is_allowed() {
    let source = "pub struct Holder {\n    // STYLE-EXCEPTION(EXC-04): shared immutable snapshot.\n    value: Arc<u8>,\n}\n";
    assert_clean(LEAF, source);
}

#[test]
fn an_rc_is_flagged_even_with_a_marker() {
    let source = "// STYLE-EXCEPTION(EXC-04): not a permitted site.\npub struct Holder {\n    value: Rc<u8>,\n}\n";
    assert_flags(LEAF, source, "Rc");
}

#[test]
fn an_arc_vec_without_a_marker_is_flagged() {
    assert_flags(
        LEAF,
        "pub struct Holder {\n    value: Arc<Vec<u8>>,\n}\n",
        "Arc<Vec",
    );
}

#[test]
fn an_arc_vec_with_a_registered_marker_is_allowed() {
    let source = "pub struct Holder {\n    // STYLE-EXCEPTION(EXC-04): adopts the caller's allocation.\n    value: Arc<Vec<u8>>,\n}\n";
    assert_clean(LEAF, source);
}

#[test]
fn catch_unwind_without_a_marker_is_flagged() {
    assert_flags(
        LEAF,
        "pub fn guard() {\n    let _ = std::panic::catch_unwind(|| 1_u8);\n}\n",
        "catch_unwind",
    );
}

#[test]
fn catch_unwind_with_an_exception_marker_is_allowed() {
    let source = "pub fn guard() {\n    // STYLE-EXCEPTION(EXC-01): the runtime boundary owns this unwind.\n    let _ = std::panic::catch_unwind(|| 1_u8);\n}\n";
    assert_clean(LEAF, source);
}

#[test]
fn an_uppercase_hex_literal_is_flagged() {
    assert_flags(LEAF, "pub const MASK: u32 = 0xAB;\n", "0xAB");
}

#[test]
fn a_lowercase_hex_literal_is_clean() {
    assert_clean(LEAF, "pub const MASK: u32 = 0xab;\n");
}

#[test]
fn a_clean_leaf_module_passes() {
    let source = "use std::collections::BTreeMap;\nuse std::sync::mpsc;\n\npub fn run(values: BTreeMap<u8, u8>) -> usize {\n    let (_sender, _receiver) = mpsc::channel::<u8>();\n    helper(values)\n}\n\nfn helper(values: BTreeMap<u8, u8>) -> usize {\n    values.len()\n}\n";
    assert_clean(LEAF, source);
}

#[test]
fn malformed_source_is_an_explicit_error() {
    let error = google_rust_style::check_rust_source(Path::new(LEAF), "pub fn broken(")
        .expect_err("malformed source must be refused");
    assert!(error.contains("parse"), "{error}");
}

#[test]
fn the_check_is_registered_and_listed() {
    let output = run(&["--list"]);
    assert!(output.status.success(), "bsl-lint --list must succeed");
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(
        stdout.lines().any(|line| line == google_rust_style::CHECK),
        "registry must list {}:\n{stdout}",
        google_rust_style::CHECK
    );
}

#[test]
fn the_check_runs_by_name_over_a_directory() {
    let layout = fixture("layout");
    let layout = layout.to_str().expect("fixture path must be UTF-8");
    let output = run(&[google_rust_style::CHECK, layout]);
    assert_eq!(
        output.status.code(),
        Some(1),
        "the fixture directory must gate:\nstdout:\n{}\nstderr:\n{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("widget.rs"), "{stdout}");
    assert!(stdout.contains("non-leaf"), "{stdout}");
}
