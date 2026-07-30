//! `ContentDigest` (spec §7): the canonical `{defines_hash, rules_hash}`
//! pair. This module owns `defines_hash`; `rules_hash` is wired once
//! `babylon-bsl`'s canonical AST serializer exists (Task 12 of the Phase-1
//! plan).
use sha2::{Digest, Sha256};

/// The canonical content fingerprint pair (spec §7).
///
/// `rules_hash` is `None` until Task 12 lands the canonical BSL AST
/// serializer — an explicit, documented interim state, not a silent
/// default; Task 12 makes it mandatory.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContentDigest {
    /// SHA-256 of the canonical `GameDefines` JSON (the Phase-0 Task-1
    /// layout: sorted keys, `(",", ":")` separators, `ensure_ascii`).
    pub defines_hash: [u8; 32],
    /// SHA-256 of the canonical BSL AST serialization — `None` until the
    /// serializer exists.
    pub rules_hash: Option<[u8; 32]>,
}

/// SHA-256 over the caller-supplied canonical JSON string.
///
/// The canonical form itself (sorted keys, `(",", ":")` separators,
/// `ensure_ascii`) is the Python side's job
/// (`babylon.config.defines.canonical_defines_hash`, Phase 0 Task 1) —
/// this function trusts its input is already canonical and only does the
/// hashing, so the same canonicalization bug class Phase 0 fixed cannot
/// reappear split across two languages.
#[must_use]
pub fn defines_hash_of(canonical_json: &str) -> [u8; 32] {
    Sha256::digest(canonical_json.as_bytes()).into()
}

#[cfg(test)]
mod tests {
    use super::{defines_hash_of, ContentDigest};

    fn hex(bytes: [u8; 32]) -> String {
        use std::fmt::Write;
        bytes.iter().fold(String::new(), |mut out, b| {
            let _ = write!(out, "{b:02x}");
            out
        })
    }

    /// Cross-language conformance vector — the REAL canonical JSON of a
    /// default `GameDefines()` (generated 2026-07-30 by
    /// `canonical_defines_hash`, committed as a fixture) and its Python
    /// hash. The fixture pins `hash(string)`, not `hash(current defines)`,
    /// so it stays valid as defines evolve — it proves the byte contract,
    /// not the current coefficient values. Independent cross-check: this
    /// hash is the exact `defines_hash` stamped in the 2026-07-30
    /// regression baselines.
    #[test]
    fn matches_the_python_canonical_defines_hash() {
        // The repo's end-of-file-fixer hook appends one trailing newline to
        // every committed text file; the canonical string itself has none
        // (json.dumps emits no trailing newline), so it is stripped —
        // explicitly, once — before the byte pin.
        let canonical_json = include_str!("../tests/fixtures/canonical_defines.json")
            .strip_suffix('\n')
            .expect("fixture is committed with exactly one hook-appended trailing newline");
        assert_eq!(canonical_json.len(), 25_184, "fixture length pin");
        assert_eq!(
            hex(defines_hash_of(canonical_json)),
            "4af1178032a2b420376e35c7a98ac2b151ea8fb9ee68636d1560528d5fd927d4"
        );
    }

    /// A small hand-checkable vector (`sha256(b'{"a":1}')`), so a fixture
    /// problem and a hashing problem are distinguishable at a glance.
    #[test]
    fn hashes_a_minimal_canonical_string() {
        assert_eq!(
            hex(defines_hash_of(r#"{"a":1}"#)),
            "015abd7f5cc57a2dd94b7590f04ad8084273905ee33ec5cebeae62276a97f862"
        );
    }

    #[test]
    fn the_interim_rules_hash_is_an_explicit_none() {
        let digest = ContentDigest {
            defines_hash: defines_hash_of("{}"),
            rules_hash: None,
        };
        assert!(digest.rules_hash.is_none());
    }
}
