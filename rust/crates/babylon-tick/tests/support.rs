//! Shared helpers for `babylon-tick`'s conformance test suite (theme 6,
//! `docs/superpowers/plans/2026-08-18-bsl-refactor-program.md` §4 Task
//! R2.1).
//!
//! Lives at `tests/support.rs` with the helper bodies in
//! `tests/support/helpers.rs`; sibling test files declare it with
//! `mod support;`. Cargo also discovers `tests/support.rs` as a no-test
//! helper target, so this root carries the helper-target lint allowances.
//!
//! **Genuinely-found shapes only.** `rust/crates/babylon-tick/tests/`
//! comprises 31 files (12,158 lines) sharing a `run_once_into`/
//! `CollectingSink`/`node_attribute` trio 315+ times, but NOT one
//! identical shape — direct reads found three distinct `attribute()`
//! signatures (a `MemoryGraph`-keyed-by-`u64` majority, e.g.
//! `dispossession_conformance.rs:74`; a `HypergraphStore`-keyed-by-`NodeId`
//! variant, e.g. `territory_conformance.rs:169`,
//! `control_ratio_conformance.rs:460`; and a `HypergraphStore`-keyed-by-
//! `u64` variant, `multi_rule_conformance.rs:146`), three distinct `run_*`
//! return shapes (below), and at least one independently-renamed pin-table
//! struct (`ExpectedTerritory` in `multi_rule_conformance.rs:71`, diffed
//! field-for-field against `lifecycle_conformance.rs:110`'s and
//! `lifecycle_crisis_conformance.rs:84`'s own `Expected` and confirmed
//! identical). Every item below generalizes from a genuinely repeated
//! shape, cited at its definition — nothing here forces a merge the source
//! files didn't already share.
//!
//! **Pure addition (R2.1.3).** Landing this module changes NOTHING about
//! the 31 existing files; sweeping them onto it is a named, explicitly
//! deferred follow-up past Checkpoint A — several are under active edit by
//! concurrent port trains this week, and touching them now would maximize
//! rebase conflict for a cosmetic win. `support_smoke_conformance.rs` is
//! this module's own adopter; `metabolism_entropy_high_conformance.rs` is
//! migrated onto it as the proof-of-adoption (mechanical, behavior-
//! identical — same fixture, same assertions, same pass/fail contract).

// This file is both the shared helper module and, because Cargo discovers
// `tests/*.rs`, a standalone helper target with no product API.
#![allow(
    clippy::missing_panics_doc,
    clippy::must_use_candidate,
    reason = "the panic case is documented on the function; the caller consumes the returned value"
)]

#[path = "support/helpers.rs"]
mod helpers;

pub use helpers::{
    assert_deterministic, assert_expected, attribute, run_conformance, run_conformance_with_report,
    run_conformance_with_sink, ExpectedField,
};
