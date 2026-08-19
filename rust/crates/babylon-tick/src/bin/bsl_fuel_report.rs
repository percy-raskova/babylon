//! `bsl-fuel-report` — Task W3 (BSL Hygiene Knock-out train): the fuel-bound
//! report mode. Prints, for every rule in every landed content set,
//! `rule-id declared=<n> computed=<m> headroom=<n-m>` — the same numbers
//! `bound_checker::check_rule` already computes on a successful load
//! (`bound_checker.rs:757-769`, `LoadedRule::{declared_fuel, static_bound}`),
//! surfaced without the "red-run ritual" (temporarily lowering a rule's
//! `:fuel` until `E-LOAD-040` fires, just to read its error message's
//! `computed_bound`/`declared_budget` fields).
//!
//! This is a REPORT, not a gate: it runs no tick, calls no second
//! reader/parser (`babylon_tick::fuel_bound_report` is a thin wrapper over
//! `prepare_rules`, the identical seam `run_once` uses), and changes no
//! load behavior. Exit is non-zero ONLY when a rule's declared budget is
//! under its computed bound — a condition `E-LOAD-040` already refuses at
//! load, so in practice this branch is unreachable for any content set
//! that made it into a printed row at all (a `check_rule` failure there
//! surfaces as this binary's `Err` branch instead, before any row for that
//! content set exists) — see [`babylon_tick::any_over_budget`]'s own doc
//! for the same documented redundancy on the library side.
//!
//! **Content-set enumeration.** No `content-sets.toml` exists on this
//! branch (it lands with the #652 train — the controller addenda for this
//! task names it explicitly) — this binary hardcodes the same 13-pack,
//! one-scenario-per-pack SOLO pairing every dedicated
//! `tests/*_conformance.rs` file (and `tick_goldens.rs`) already
//! establishes as each pack's own canonical load, matching
//! `w2-preaudit-table.md` §1's identical "13 packs, solo everywhere except
//! two co-loads" finding for the same-tick-ordering checker. The two
//! committed co-loads (`vitality+lifecycle`, `decomposition+control-ratio`)
//! are deliberately NOT also included here: each pack's rule ids are
//! already covered by its own solo row above, and a co-load would only
//! ever repeat the same rule ids (fuel bounds are a per-rule static
//! property of the AST plus the ceilings in scope, not of "which other
//! pack shares this tick") — a second row per rule-id would break the
//! "one row per rule" reading the format line implies without adding new
//! information.

use babylon_tick::{any_over_budget, fuel_bound_report};
use std::process::ExitCode;

/// (pack name, scenario source, optional declaration prelude, rule source)
/// — the SAME scenario each pack's own dedicated conformance test loads it
/// against (see this file's module doc for the citations backing each
/// pairing).
const CONTENT_SETS: &[(&str, &str, Option<&str>, &str)] = &[
    (
        "fundamental-theorem",
        include_str!("../../content/scenarios/two-classes.bscn"),
        None,
        include_str!("../../content/rules/fundamental-theorem.bsl"),
    ),
    (
        "vitality",
        include_str!("../../content/scenarios/vitality-conformance.bscn"),
        None,
        include_str!("../../content/rules/vitality.bsl"),
    ),
    (
        "lifecycle",
        include_str!("../../content/scenarios/lifecycle-conformance.bscn"),
        None,
        include_str!("../../content/rules/lifecycle.bsl"),
    ),
    (
        "organization",
        include_str!("../../content/scenarios/organization-foundation.bscn"),
        None,
        include_str!("../../content/rules/organization.bsl"),
    ),
    (
        "territory",
        include_str!("../../content/scenarios/territory-conformance.bscn"),
        None,
        include_str!("../../content/rules/territory.bsl"),
    ),
    (
        "production",
        include_str!("../../content/scenarios/production-conformance.bscn"),
        None,
        include_str!("../../content/rules/production.bsl"),
    ),
    (
        "worldview",
        include_str!("../../content/scenarios/worldview-foundation.bscn"),
        None,
        include_str!("../../content/rules/worldview.bsl"),
    ),
    (
        "consciousness",
        include_str!("../../content/scenarios/consciousness-ternary-conformance.bscn"),
        Some(include_str!("../../content/declarations/worldview.bscn")),
        include_str!("../../content/rules/consciousness.bsl"),
    ),
    (
        "solidarity",
        include_str!("../../content/scenarios/solidarity-conformance.bscn"),
        None,
        include_str!("../../content/rules/solidarity.bsl"),
    ),
    (
        "decomposition",
        include_str!("../../content/scenarios/decomposition-conformance.bscn"),
        None,
        include_str!("../../content/rules/decomposition.bsl"),
    ),
    (
        "control-ratio",
        include_str!("../../content/scenarios/control-ratio-conformance.bscn"),
        None,
        include_str!("../../content/rules/control-ratio.bsl"),
    ),
    (
        "dispossession",
        include_str!("../../content/scenarios/dispossession-conformance.bscn"),
        None,
        include_str!("../../content/rules/dispossession.bsl"),
    ),
    (
        "metabolism",
        include_str!("../../content/scenarios/metabolism-conformance.bscn"),
        None,
        include_str!("../../content/rules/metabolism.bsl"),
    ),
];

fn main() -> ExitCode {
    let mut rows = Vec::new();
    for (pack, scenario, prelude, rule) in CONTENT_SETS {
        match fuel_bound_report(scenario, *prelude, rule) {
            Ok(pack_rows) => rows.extend(pack_rows),
            Err(e) => {
                eprintln!("bsl-fuel-report: {pack}: {e}");
                return ExitCode::from(2);
            }
        }
    }
    // Global sort, byte order — each pack's own rows already arrive sorted
    // (`prepare_rules`, §4.2/D16), but sorting the WHOLE report again makes
    // its determinism independent of `CONTENT_SETS`' own declared order,
    // which (like any content ordering, §2.2) carries no semantics.
    rows.sort_by(|a, b| a.rule_id.as_bytes().cmp(b.rule_id.as_bytes()));

    for row in &rows {
        println!("{row}");
    }

    if any_over_budget(&rows) {
        ExitCode::from(1)
    } else {
        ExitCode::SUCCESS
    }
}
