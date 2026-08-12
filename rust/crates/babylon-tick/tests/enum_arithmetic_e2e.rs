//! §2.13's "no aggregation kind" law (D101), proven through `run_once` — the
//! SAME entry point production uses (`main.rs`'s CLI driver,
//! `babylon-client`'s engine link) — not just the `babylon-bsl` unit-level
//! `collect_then_apply` harness.
//!
//! **#528 fix round, blocker 2.** Before this fix, `(add OrgKind/BUSINESS)`
//! on an `organization/kind` field seeded `OrgKind/STATE_APPARATUS` silently
//! reduced to `current + operand` — declaration-order ORDINAL arithmetic
//! (`0.0 + 1.0 = 1.0`) that happens to land on a DIFFERENT real member
//! (`BUSINESS`) rather than refusing. `sub`/`scale` are worse: nothing in
//! the store-boundary range check (`store_range_check`, §3.3) bounds an
//! enum field's ordinal, so `(sub OrgKind/BUSINESS)` on `STATE_APPARATUS`
//! (ordinal 0) writes `-1.0` completely unchecked — a stored value with no
//! member at all, caught only later, by a DIFFERENT site, the next time
//! something reads it back (`tick.rs`'s own corrupted-ordinal integrity
//! check). `set` is the only coherent op on an `Enum<T>` field (§2.13: "no
//! aggregation kind ... `Enum<T>` supports no arithmetic"); this file proves
//! `add`/`sub`/`scale` are refused loudly, at the WRITE site, through the
//! full `run_once` seam — not just the `babylon-bsl` unit-level harness the
//! adversarial review found this whole class invisible to.

use babylon_tick::run_once;

const ORG_SCENARIO: &str = r#"
(scenario enum-arithmetic-e2e/one-org
  (defenum OrgKind (STATE_APPARATUS BUSINESS POLITICAL_FACTION CIVIL_SOCIETY))
  (deffield organization/kind enum OrgKind)
  (node acme NodeType/ORGANIZATION (organization/kind OrgKind/STATE_APPARATUS)))
"#;

fn enum_op_rule(op: &str) -> String {
    format!(
        r#"
(rule vitality/enum-arithmetic-e2e-{op}
  :material-basis "prove {op} on an enum field is a loud E-EVAL-042 tick error"
  :fuel 64
  (bindings
    (binding kind :field organization/kind))
  (effects
    (update-node self organization/kind ({op} OrgKind/BUSINESS))))
"#
    )
}

#[test]
fn add_on_a_seeded_enum_field_is_a_loud_e_eval_042_tick_error() {
    let err = run_once(ORG_SCENARIO, &enum_op_rule("add")).unwrap_err();
    assert!(
        err.contains("E-EVAL-042"),
        "add on an enum field must refuse as E-EVAL-042, not silently \
         reinterpret the ordinal as a different member: {err}"
    );
}

#[test]
fn sub_on_a_seeded_enum_field_is_a_loud_e_eval_042_tick_error() {
    // The task's own worst case: STATE_APPARATUS (ordinal 0) minus
    // BUSINESS's ordinal (1) would write -1.0 completely unchecked — no
    // member, and no range check on an enum field catches it at the store
    // boundary (§3.3's unit-interval check does not cover BslType::Enum).
    let err = run_once(ORG_SCENARIO, &enum_op_rule("sub")).unwrap_err();
    assert!(
        err.contains("E-EVAL-042"),
        "sub on an enum field must refuse as E-EVAL-042 BEFORE it corrupts \
         the store into an out-of-range ordinal: {err}"
    );
}

#[test]
fn scale_on_a_seeded_enum_field_is_a_loud_e_eval_042_tick_error() {
    let err = run_once(ORG_SCENARIO, &enum_op_rule("scale")).unwrap_err();
    assert!(err.contains("E-EVAL-042"), "{err}");
}

/// The green path is unaffected: `set` is the coherent op on an enum field
/// and must still clear the full `run_once` seam.
#[test]
fn set_on_a_seeded_enum_field_still_succeeds_through_run_once() {
    const SET_RULE: &str = r#"
(rule vitality/enum-arithmetic-e2e-set
  :material-basis "set remains the coherent op on an enum field"
  :fuel 64
  (bindings
    (binding kind :field organization/kind))
  (effects
    (update-node self organization/kind (set OrgKind/BUSINESS))))
"#;
    let report = run_once(ORG_SCENARIO, SET_RULE)
        .expect("set on an enum field must still succeed through the full seam");
    assert_eq!(report.fired, 1);
}
