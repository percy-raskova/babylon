//! Modding ordering anchors (`bsl-language.rst` §2.3): a rule declares
//! `(anchor :after <system>)` / `(anchor :before <system>)`, or omits the
//! anchor and belongs to the system named by its rule id's first segment —
//! a rule can never land "nowhere", and a raw position float is not
//! expressible (§2.2 `:after`/`:before`).
//!
//! Scope (Phase 1 Task 16, per the plan): this module validates the
//! DECLARATION — shape, and the E-LOAD-002 no-system case. Resolving
//! anchors into a total order belongs to `babylon-engine`'s anchor-based
//! registry (Phase 3), and the Material Base interleave check
//! (`E-LOAD-003`) belongs there with it, because the partition boundaries
//! are engine registry data this crate does not hold — deferred with a
//! name, not silently.

use crate::reader::{Atom, SExpr};
use std::collections::HashSet;

/// Which side of the named system the rule lands on.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AnchorPosition {
    /// `:before <system>`.
    Before,
    /// `:after <system>`.
    After,
}

/// A validated anchor declaration.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AnchorDecl {
    /// Before or after.
    pub position: AnchorPosition,
    /// The registered system the anchor names.
    pub system: String,
}

/// An anchor rejection.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AnchorError {
    /// `E-LOAD-002` — a rule with no `<anchor>` whose first id segment
    /// names no registered system: mods cannot land a rule "nowhere".
    NoSystemForRule {
        /// The rule id whose first segment resolved nothing.
        rule_id: String,
    },
    /// `E-PARSE-013` — an anchor keyword outside `:after`/`:before`.
    UnknownKeyword {
        /// The offending keyword (without colon).
        keyword: String,
    },
    /// A shape off the §2.3 `<anchor>` production.
    Malformed {
        /// What was expected, and what was found.
        message: String,
    },
}

impl AnchorError {
    /// The spec's error code, where the reference names one.
    #[must_use]
    pub fn spec_code(&self) -> Option<&'static str> {
        match self {
            Self::NoSystemForRule { .. } => Some("E-LOAD-002"),
            Self::UnknownKeyword { .. } => Some("E-PARSE-013"),
            Self::Malformed { .. } => None,
        }
    }
}

impl std::fmt::Display for AnchorError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NoSystemForRule { rule_id } => write!(
                f,
                "E-LOAD-002: rule {rule_id} carries no anchor and its first \
                 id segment names no registered system — a rule cannot land \
                 nowhere (§2.3)"
            ),
            Self::UnknownKeyword { keyword } => write!(
                f,
                "E-PARSE-013: anchor keyword :{keyword} — the set is \
                 :after | :before (§2.3)"
            ),
            Self::Malformed { message } => write!(f, "malformed anchor: {message}"),
        }
    }
}

impl std::error::Error for AnchorError {}

fn malformed(message: impl Into<String>) -> AnchorError {
    AnchorError::Malformed {
        message: message.into(),
    }
}

/// Validate a rule's anchor situation against the registered system set:
/// returns the declared anchor if present and well-shaped, or `None` for
/// the anchor-default case (first id segment names a registered system).
///
/// # Errors
///
/// [`AnchorError::NoSystemForRule`] (`E-LOAD-002`) when neither an anchor
/// nor a system-named id segment places the rule;
/// [`AnchorError::UnknownKeyword`] / [`AnchorError::Malformed`] for shapes
/// off the §2.3 production.
pub fn check_anchor<S: std::hash::BuildHasher>(
    rule: &SExpr,
    registered_systems: &HashSet<String, S>,
) -> Result<Option<AnchorDecl>, AnchorError> {
    let SExpr::List(items) = rule else {
        return Err(malformed(format!(
            "expected a (rule …) form, found {rule:?}"
        )));
    };
    let mut anchor_forms = items.iter().filter_map(|child| match child {
        SExpr::List(inner)
            if matches!(inner.first(), Some(SExpr::Atom(Atom::Symbol(h))) if h == "anchor") =>
        {
            Some(inner.as_slice())
        }
        _ => None,
    });
    let anchor_form = anchor_forms.next();
    // III.11: a second anchor form is a LOUD error — first-one-wins would
    // let a contradictory declaration vanish silently at load.
    if anchor_form.is_some() && anchor_forms.next().is_some() {
        return Err(malformed(
            "a rule declares at most one (anchor …) form — a second would \
             silently lose to the first",
        ));
    }
    if let Some(anchor_items) = anchor_form {
        let [_, SExpr::Atom(Atom::Keyword(kw)), SExpr::Atom(Atom::Symbol(system))] = anchor_items
        else {
            return Err(malformed(format!(
                "(anchor (:after | :before) <symbol>) — unrecognized shape {anchor_items:?}"
            )));
        };
        let position = match kw.as_str() {
            "after" => AnchorPosition::After,
            "before" => AnchorPosition::Before,
            other => {
                return Err(AnchorError::UnknownKeyword {
                    keyword: other.to_owned(),
                })
            }
        };
        return Ok(Some(AnchorDecl {
            position,
            system: system.clone(),
        }));
    }
    // Anchor default (§2.3 draft ruling): the rule belongs to the system
    // named by its id's first segment.
    let rule_id = match items.get(1) {
        Some(SExpr::Atom(Atom::QName(q))) => q.clone(),
        other => {
            return Err(malformed(format!(
                "rule id must be a qname, found {other:?}"
            )))
        }
    };
    let first_segment = rule_id.split('/').next().unwrap_or_default();
    if registered_systems.contains(first_segment) {
        Ok(None)
    } else {
        Err(AnchorError::NoSystemForRule { rule_id })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::reader::read;

    fn systems() -> HashSet<String> {
        HashSet::from(["survival".to_owned(), "consciousness".to_owned()])
    }

    fn rule(source: &str) -> SExpr {
        read(source).expect("test rule must parse").0
    }

    #[test]
    fn a_declared_anchor_parses_both_positions() {
        for (kw, position) in [
            ("after", AnchorPosition::After),
            ("before", AnchorPosition::Before),
        ] {
            let r = rule(&format!(
                "(rule mods/extra :material-basis \"wage relation\" :fuel 8 \
                 (anchor :{kw} survival) (bindings) \
                 (effects (update-node self social-class/agitation (add 0.05i))))"
            ));
            assert_eq!(
                check_anchor(&r, &systems()),
                Ok(Some(AnchorDecl {
                    position,
                    system: "survival".to_owned(),
                }))
            );
        }
    }

    /// Two `(anchor …)` forms in one rule are a LOUD error (III.11) —
    /// never a silent first-one-wins, which would let a contradictory
    /// second anchor vanish at load.
    #[test]
    fn a_second_anchor_form_is_a_loud_error_never_first_wins() {
        let r = rule(
            "(rule mods/extra :material-basis \"wage relation\" :fuel 8 \
             (anchor :after survival) (anchor :before consciousness) (bindings) \
             (effects (update-node self social-class/agitation (add 0.05i))))",
        );
        let err = check_anchor(&r, &systems()).unwrap_err();
        assert!(
            matches!(&err, AnchorError::Malformed { message } if message.contains("one (anchor")),
            "expected the single-anchor rejection, got: {err:?}"
        );
    }

    #[test]
    fn the_anchor_default_places_a_system_named_rule() {
        let r = rule(
            "(rule survival/hunger :material-basis \"wage relation\" :fuel 8 \
             (bindings) \
             (effects (update-node self social-class/agitation (add 0.05i))))",
        );
        assert_eq!(check_anchor(&r, &systems()), Ok(None));
    }

    #[test]
    fn a_rule_landing_nowhere_is_e_load_002() {
        let r = rule(
            "(rule nowhere/hunger :material-basis \"wage relation\" :fuel 8 \
             (bindings) \
             (effects (update-node self social-class/agitation (add 0.05i))))",
        );
        let err = check_anchor(&r, &systems()).unwrap_err();
        assert_eq!(
            err,
            AnchorError::NoSystemForRule {
                rule_id: "nowhere/hunger".to_owned()
            }
        );
        assert_eq!(err.spec_code(), Some("E-LOAD-002"));
    }

    #[test]
    fn an_off_set_anchor_keyword_is_e_parse_013() {
        let r = rule(
            "(rule mods/extra :material-basis \"wage relation\" :fuel 8 \
             (anchor :during survival) (bindings) \
             (effects (update-node self social-class/agitation (add 0.05i))))",
        );
        let err = check_anchor(&r, &systems()).unwrap_err();
        assert_eq!(err.spec_code(), Some("E-PARSE-013"));
    }
}
