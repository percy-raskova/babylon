//! Reference scoping (`bsl-language.rst` §2.5): where a `:field` binding of
//! a **foreign** node type may be read, and how many candidate bodies may be
//! in scope when it is.
//!
//! §2.5 has said since this document's first revision that a `:field` qname
//! whose first segment names a node type other than the subject's "is only
//! legal inside a fold body over that type" (`E-TYPE-010`). R9 chapter C1
//! adds the other half (D30): a reference under **two or more** enclosing
//! bodies ranging over that same node type is `E-TYPE-013` — the reference
//! is ambiguous, and the author names an element with `:as` (§2.6) and reads
//! it through `field-of` instead. Single-body code is unaffected.
//!
//! The walk is purely structural and terminates by construction (an `SExpr`
//! is a finite tree — the same argument `canonical_ast` and `bound_checker`
//! rely on).

use crate::bindings::{BindSource, BindingDecl};
use crate::reader::{Atom, SExpr};
use crate::vocabulary::{render_member, ClosedVocabulary, EnumKind};

/// A scoping rejection.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ScopeError {
    /// `E-TYPE-010` — a foreign-node-type `:field` binding referenced
    /// outside every body ranging over that node type.
    ForeignFieldOutsideBody {
        /// The binding name.
        binding: String,
        /// The node-type segment it owns off.
        owner: String,
    },
    /// `E-TYPE-013` — the same reference under two or more enclosing bodies
    /// of that node type: ambiguous, and repaired by naming an element.
    AmbiguousForeignField {
        /// The binding name.
        binding: String,
        /// The node-type segment it owns off.
        owner: String,
        /// How many enclosing bodies range over that type.
        candidates: usize,
    },
}

impl ScopeError {
    /// The spec's error code.
    #[must_use]
    pub fn spec_code(&self) -> &'static str {
        match self {
            Self::ForeignFieldOutsideBody { .. } => "E-TYPE-010",
            Self::AmbiguousForeignField { .. } => "E-TYPE-013",
        }
    }
}

impl std::fmt::Display for ScopeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::ForeignFieldOutsideBody { binding, owner } => write!(
                f,
                "E-TYPE-010: binding {binding} reads a field of the foreign \
                 node type '{owner}' outside every body ranging over it (§2.5)"
            ),
            Self::AmbiguousForeignField {
                binding,
                owner,
                candidates,
            } => write!(
                f,
                "E-TYPE-013: binding {binding} ('{owner}') is referenced under \
                 {candidates} enclosing bodies of that node type — name an \
                 element with :as and read it with field-of (§2.5, D30)"
            ),
        }
    }
}

impl std::error::Error for ScopeError {}

/// The node-type **segment** a query's elements range over, if the query
/// annotates one. Only `nodes` and `neighbors` do: `members-of` yields
/// `NodeRef`s of no annotated type, and the edge/hyperedge queries yield no
/// nodes at all.
#[must_use]
pub fn query_node_type_segment(query_items: &[SExpr]) -> Option<String> {
    let head = match query_items.first() {
        Some(SExpr::Atom(Atom::Symbol(s))) => s.as_str(),
        _ => return None,
    };
    let index = match head {
        "nodes" => 1,
        // §2.6 (C8): the mandatory FOURTH operand is the result NodeType.
        "neighbors" => 4,
        _ => return None,
    };
    match query_items.get(index) {
        Some(SExpr::Atom(Atom::EnumRef { enum_type, member })) if enum_type == "NodeType" => {
            Some(render_member(member))
        }
        _ => None,
    }
}

/// Whether a form is one of §2.6's six query heads.
fn is_query(items: &[SExpr]) -> bool {
    matches!(
        items.first(),
        Some(SExpr::Atom(Atom::Symbol(s)))
            if matches!(
                s.as_str(),
                "nodes" | "edges" | "neighbors" | "hyperedges" | "members-of" | "hyperedges-of"
            )
    )
}

/// The iterating forms whose bodies range over a query's elements (§2.7's
/// `fold`/`select-*`, §2.4's `exists`/`forall`, §2.8's `for-each`). Each
/// takes its `<query>` as its first operand after the head — except `fold`,
/// whose `<fold-op>` comes first.
fn iterating_query_index(head: &str) -> Option<usize> {
    match head {
        "fold" => Some(2),
        "exists" | "forall" | "select-max" | "select-min" | "for-each" => Some(1),
        _ => None,
    }
}

/// Count the enclosing bodies of node type `owner` at every reference to
/// `binding`, and apply §2.5's two rules.
fn walk(
    expr: &SExpr,
    binding: &str,
    owner: &str,
    depth: usize,
    result: &mut Result<(), ScopeError>,
) {
    if result.is_err() {
        return;
    }
    match expr {
        SExpr::Atom(Atom::Symbol(name)) if name == binding => {
            if depth == 0 {
                *result = Err(ScopeError::ForeignFieldOutsideBody {
                    binding: binding.to_owned(),
                    owner: owner.to_owned(),
                });
            } else if depth > 1 {
                *result = Err(ScopeError::AmbiguousForeignField {
                    binding: binding.to_owned(),
                    owner: owner.to_owned(),
                    candidates: depth,
                });
            }
        }
        SExpr::Atom(_) => {}
        SExpr::List(items) => {
            let head = match items.first() {
                Some(SExpr::Atom(Atom::Symbol(s))) => Some(s.as_str()),
                _ => None,
            };
            // A query form's own element predicate is a body over that
            // query's elements, exactly as a fold body is.
            if is_query(items) {
                let inner_depth = depth + usize::from(matches_owner(items, owner));
                for child in &items[1..] {
                    walk(child, binding, owner, inner_depth, result);
                }
                return;
            }
            if let Some(query_index) = head.and_then(iterating_query_index) {
                let ranges_over = match items.get(query_index) {
                    Some(SExpr::List(q)) if is_query(q) => matches_owner(q, owner),
                    _ => false,
                };
                let inner_depth = depth + usize::from(ranges_over);
                for (i, child) in items.iter().enumerate().skip(1) {
                    // The query operand itself is evaluated in the OUTER
                    // scope; only the body sees the new element.
                    let child_depth = if i == query_index { depth } else { inner_depth };
                    walk(child, binding, owner, child_depth, result);
                }
                return;
            }
            for child in &items[1..] {
                walk(child, binding, owner, depth, result);
            }
        }
    }
}

/// The `:expr` operands of one `(binding …)` row — the only expressions a
/// binding declaration contains (§2.5, R9 chapter C7).
fn expr_operands(row: &SExpr) -> Vec<&SExpr> {
    let SExpr::List(items) = row else {
        return Vec::new();
    };
    let mut out = Vec::new();
    for window in items.windows(2) {
        if let [SExpr::Atom(Atom::Keyword(kw)), operand] = window {
            if kw == "expr" {
                out.push(operand);
            }
        }
    }
    out
}

fn matches_owner(query_items: &[SExpr], owner: &str) -> bool {
    query_node_type_segment(query_items).is_some_and(|segment| segment == owner)
}

/// Check every foreign-node-type `:field` binding of a rule against §2.5's
/// two rules, given the rule's subject node-type **segment** (`None` for a
/// `(domain :graph)` rule, where every `:field` binding is foreign).
///
/// # Errors
///
/// [`ScopeError::ForeignFieldOutsideBody`] (`E-TYPE-010`) or
/// [`ScopeError::AmbiguousForeignField`] (`E-TYPE-013`).
pub fn check_foreign_field_scoping(
    rule: &SExpr,
    decls: &[BindingDecl],
    subject_segment: Option<&str>,
    vocabulary: &ClosedVocabulary,
) -> Result<(), ScopeError> {
    let SExpr::List(items) = rule else {
        return Ok(());
    };
    for decl in decls {
        let BindSource::Field(qname) = &decl.source else {
            continue;
        };
        let segment = qname.split('/').next().unwrap_or(qname);
        // Only NODE-type fields are read by a `:field` binding at all (D29);
        // an edge/hyperedge owner is the grammar checker's rejection, not
        // this pass's.
        match vocabulary.owner_of(segment) {
            Ok((EnumKind::NodeType, _)) => {}
            _ => continue,
        }
        if subject_segment == Some(segment) {
            continue; // the subject's own field: always in scope
        }
        let mut result = Ok(());
        for child in items {
            let SExpr::List(inner) = child else { continue };
            match inner.first() {
                Some(SExpr::Atom(Atom::Symbol(h))) if h == "when" || h == "effects" => {
                    for body in &inner[1..] {
                        walk(body, &decl.name, segment, 0, &mut result);
                    }
                }
                // A `(bindings …)` form's rows carry their own NAMES in
                // value-shaped positions, so the whole form must not be
                // walked: only a `:expr` operand (§2.5, C7) is a reference
                // site, and a `:expr` is evaluated at rule scope (depth 0).
                Some(SExpr::Atom(Atom::Symbol(h))) if h == "bindings" => {
                    for row in &inner[1..] {
                        for expr in expr_operands(row) {
                            walk(expr, &decl.name, segment, 0, &mut result);
                        }
                    }
                }
                _ => {}
            }
        }
        result?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::check_foreign_field_scoping;
    use crate::bindings::parse_bindings;
    use crate::reader::read;
    use crate::vocabulary::{ClosedVocabulary, EnumKind};

    fn vocabulary() -> ClosedVocabulary {
        ClosedVocabulary::new([
            (
                EnumKind::NodeType,
                vec![
                    "SOCIAL_CLASS".to_owned(),
                    "ORGANIZATION".to_owned(),
                    "TERRITORY".to_owned(),
                ],
            ),
            (EnumKind::EdgeType, vec!["SOLIDARITY".to_owned()]),
        ])
        .unwrap()
    }

    fn check(source: &str, subject: Option<&str>) -> Result<(), super::ScopeError> {
        let (rule, _) = read(source).expect("test source must parse");
        let decls = parse_bindings(&rule).expect("bindings must parse");
        check_foreign_field_scoping(&rule, &decls, subject, &vocabulary())
    }

    const PREAMBLE: &str = ":material-basis \"the wage relation\" :fuel 4096";

    #[test]
    fn the_subjects_own_field_is_always_in_scope() {
        let source = format!(
            "(rule demo/own {PREAMBLE} \
             (bindings (binding wealth :field social-class/wealth)) \
             (when (< wealth 5)) \
             (effects (update-node self social-class/agitation (add 0.05i))))"
        );
        assert_eq!(check(&source, Some("social-class")), Ok(()));
    }

    #[test]
    fn a_foreign_field_outside_every_body_is_e_type_010() {
        let source = format!(
            "(rule demo/foreign {PREAMBLE} \
             (bindings (binding claim :field organization/claim-strength)) \
             (when (< claim 5)) \
             (effects (update-node self social-class/agitation (add 0.05i))))"
        );
        let err = check(&source, Some("social-class")).unwrap_err();
        assert_eq!(err.spec_code(), "E-TYPE-010");
    }

    #[test]
    fn a_foreign_field_inside_one_body_over_that_type_is_legal() {
        let source = format!(
            "(rule demo/one-body {PREAMBLE} \
             (bindings (binding claim :field organization/claim-strength)) \
             (when (< (fold sum (nodes NodeType/ORGANIZATION) claim) 5)) \
             (effects (update-node self social-class/agitation (add 0.05i))))"
        );
        assert_eq!(check(&source, Some("social-class")), Ok(()));
    }

    #[test]
    fn two_enclosing_bodies_of_that_type_is_e_type_013() {
        let source = format!(
            "(rule demo/ambiguous {PREAMBLE} \
             (bindings (binding claim :field organization/claim-strength)) \
             (when (< (fold sum (nodes NodeType/ORGANIZATION) \
                        (fold max (nodes NodeType/ORGANIZATION) claim)) 5)) \
             (effects (update-node self social-class/agitation (add 0.05i))))"
        );
        let err = check(&source, Some("social-class")).unwrap_err();
        assert_eq!(err.spec_code(), "E-TYPE-013");
    }

    #[test]
    fn a_body_over_a_different_node_type_does_not_license_the_read() {
        let source = format!(
            "(rule demo/wrong-body {PREAMBLE} \
             (bindings (binding claim :field organization/claim-strength)) \
             (when (< (fold sum (nodes NodeType/TERRITORY) claim) 5)) \
             (effects (update-node self social-class/agitation (add 0.05i))))"
        );
        assert_eq!(
            check(&source, Some("social-class"))
                .unwrap_err()
                .spec_code(),
            "E-TYPE-010"
        );
    }

    #[test]
    fn nesting_a_different_type_inside_does_not_double_count() {
        let source = format!(
            "(rule demo/nested-mixed {PREAMBLE} \
             (bindings (binding claim :field organization/claim-strength)) \
             (when (< (fold sum (nodes NodeType/ORGANIZATION) \
                        (fold max (nodes NodeType/TERRITORY) claim)) 5)) \
             (effects (update-node self social-class/agitation (add 0.05i))))"
        );
        assert_eq!(check(&source, Some("social-class")), Ok(()));
    }

    #[test]
    fn the_query_operand_is_evaluated_in_the_outer_scope() {
        // A reference in the query's own operand position sits OUTSIDE the
        // body it introduces — reading it there is still E-TYPE-010.
        let source = format!(
            "(rule demo/operand {PREAMBLE} \
             (bindings (binding claim :field organization/claim-strength)) \
             (when (< (fold sum (hyperedges-of claim HyperedgeType/CELL) it) 5)) \
             (effects (update-node self social-class/agitation (add 0.05i))))"
        );
        assert_eq!(
            check(&source, Some("social-class"))
                .unwrap_err()
                .spec_code(),
            "E-TYPE-010"
        );
    }
}
