//! `Host` trait-default contract for the M4 topology/field-state additions
//! (plan Task 30; contracts: `docs/superpowers/specs/
//! 2026-07-27-m4-topology-contracts.md` §1, §2).
//!
//! A host implementing only the ONE required method (`lobby_catalog_json`)
//! must still render honest absence for every optional read — `"null"`,
//! never a fabricated payload (Constitution III.11). This mirrors the M1
//! `hello_frame.rs` convention (`FakeHost` overrides only what a scenario
//! needs, relying on the trait defaults for the rest) applied directly to
//! the two new M4 methods.

use babylon_tui::host::Host;

struct MinimalHost;

impl Host for MinimalHost {
    fn lobby_catalog_json(&self) -> String {
        "[]".to_string()
    }
}

#[test]
fn topology_json_defaults_to_null() {
    let host = MinimalHost;
    assert_eq!(
        host.topology_json(r#"{"kind":"paoh","focus":null}"#),
        "null"
    );
}

#[test]
fn field_state_json_defaults_to_null() {
    let host = MinimalHost;
    assert_eq!(host.field_state_json(), "null");
}

#[test]
fn choropleth_json_defaults_to_null() {
    // M5 contract §1: a host without the maps surface is honest absence.
    let host = MinimalHost;
    assert_eq!(
        host.choropleth_json(r#"{"tier": "county", "lens": "value"}"#),
        "null"
    );
}
