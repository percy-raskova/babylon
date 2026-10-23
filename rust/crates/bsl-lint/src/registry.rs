//! The single check registry.
//!
//! `in_default_all` keeps a check runnable by name without joining the `all`
//! set. `google-rust-style` stays out of `all` until Tasks 5-10 finish the
//! workspace refactors; Task 11 flips the flag.

use crate::finding::Finding;
use crate::google_rust_style;
use crate::repo::Repo;
use crate::{citation_drift, namespace_unique, rust_contract_authority, sfs_non_authorability};

/// One registered check: its stable CLI name, its runner, and whether `all`
/// includes it today.
pub struct Check {
    pub name: &'static str,
    pub run: CheckFn,
    pub in_default_all: bool,
}

/// A check runner over the discovered repository and the optional path scope.
pub type CheckFn = fn(&Repo, &[String]) -> Result<Vec<Finding>, String>;

/// Every runnable check, in stable CLI order.
pub const CHECKS: &[Check] = &[
    Check {
        name: citation_drift::CHECK,
        run: citation_drift::run,
        in_default_all: true,
    },
    Check {
        name: google_rust_style::CHECK,
        run: google_rust_style::run,
        in_default_all: false,
    },
    Check {
        name: namespace_unique::CHECK,
        run: namespace_unique::run,
        in_default_all: true,
    },
    Check {
        name: rust_contract_authority::CHECK,
        run: rust_contract_authority::run,
        in_default_all: true,
    },
    Check {
        name: sfs_non_authorability::CHECK,
        run: sfs_non_authorability::run,
        in_default_all: true,
    },
];
