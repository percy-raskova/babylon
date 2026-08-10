//! Static shape checks over the §2 grammar that no other module owns: the
//! **enum-ref operand class rule** (D74) and the **field-init owner rule**
//! (D37). Both are load-time and both are stated once here rather than per
//! form, which is exactly the repair D74 records — "the R9 chapters added
//! four such positions and a per-form restatement left each new one without
//! a rejection".
//!
//! `E-TYPE-011` is a **kind** check and nothing more: whether the named type
//! and member exist at all is `E-LOAD-030`/`E-LOAD-031`
//! ([`crate::vocabulary`]).

use crate::reader::{Atom, SExpr};
use crate::vocabulary::{ClosedVocabulary, EnumKind};

/// A static shape rejection.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GrammarError {
    /// `E-TYPE-011` — an `<enum-ref>` operand naming a member of the wrong
    /// enum kind for its position (D74).
    WrongEnumKind {
        /// The form head whose operand is wrong.
        form: String,
        /// Which operand (1-based, after the head).
        operand: usize,
        /// The kind the position demands.
        expected: EnumKind,
        /// What was written, as `EnumType/MEMBER`.
        found: String,
    },
    /// `E-PARSE-041` — an `add-edge` `<field-init>` naming the implicit
    /// `<edge-type>/strength` field, whose only writer at mint time is the
    /// `:strength` operand (D37).
    StrengthFieldInit {
        /// The offending qname.
        field: String,
    },
    /// `E-PARSE-040` — arithmetic that is not strictly binary; D75 keeps
    /// this as the arithmetic-specific spelling of the arity class.
    ArithmeticArity {
        /// The operator.
        operator: String,
        /// How many operands were written.
        found: usize,
    },
    /// `E-PARSE-042` — a form whose operand count differs from the one its
    /// §2 production fixes (D75). The three-operand `neighbors` of the
    /// pre-C8 grammar is the case this revision creates (D51).
    Arity {
        /// The form head.
        form: String,
        /// How many operands were written (after `:as` is stripped).
        found: usize,
        /// What the production fixes.
        expected: &'static str,
    },
    /// `E-PARSE-015` — a head symbol that is not a member of a closed
    /// terminal set: `<fold-op>`, `<cmp>`, `<update-op>` or `<arith>`
    /// (D75). Two of §6.3's four silent-degradation corrections land here.
    NotInClosedSet {
        /// The offending symbol.
        symbol: String,
        /// Which closed set it was checked against.
        set: &'static str,
    },
    /// `E-PARSE-010` — a string literal in expression position (D75). §1.5
    /// admits strings at `:material-basis` and at conformance-vector
    /// identifiers only; `<expr>` has no string form and `Str` has no
    /// operations, so a string in a payload or a comparison is an atom
    /// rejected by **position**, not by lexis.
    StringInExpressionPosition {
        /// The offending literal.
        literal: String,
    },
    /// `E-PARSE-013` — the `:graph` flag outside a `domain` form (D42).
    /// The keyword set is closed and a misplaced keyword is never ignored.
    GraphFlagOutsideDomain,
    /// `E-TYPE-014` — a `<field-init>` whose owning type is not the element
    /// type the minting verb's `<enum-ref>` names (D37). Static on
    /// `add-node`/`add-edge`/`add-hyperedge`; the same disagreement on the
    /// update verbs surfaces at evaluation as `E-EVAL-033`.
    FieldInitOwnerMismatch {
        /// The offending qname.
        field: String,
        /// The type the verb mints, as `EnumType/MEMBER`.
        verb_type: String,
        /// The type the field owns off, as `EnumType/MEMBER`.
        owner: String,
    },
}

impl GrammarError {
    /// The spec's error code.
    #[must_use]
    pub fn spec_code(&self) -> &'static str {
        match self {
            Self::WrongEnumKind { .. } => "E-TYPE-011",
            Self::ArithmeticArity { .. } => "E-PARSE-040",
            Self::Arity { .. } => "E-PARSE-042",
            Self::NotInClosedSet { .. } => "E-PARSE-015",
            Self::StringInExpressionPosition { .. } => "E-PARSE-010",
            Self::GraphFlagOutsideDomain => "E-PARSE-013",
            Self::StrengthFieldInit { .. } => "E-PARSE-041",
            Self::FieldInitOwnerMismatch { .. } => "E-TYPE-014",
        }
    }
}

impl std::fmt::Display for GrammarError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::WrongEnumKind {
                form,
                operand,
                expected,
                found,
            } => write!(
                f,
                "E-TYPE-011: ({form} …) operand {operand} takes a {} member, \
                 found {found} (§2.6's class rule, D74)",
                expected.type_name()
            ),
            Self::ArithmeticArity { operator, found } => write!(
                f,
                "E-PARSE-040: ({operator} …) is strictly binary; {found} \
                 operands were written. The reduction order stays explicit in \
                 the source rather than implied by a left-fold convention \
                 (§2.7)"
            ),
            Self::Arity {
                form,
                found,
                expected,
            } => write!(
                f,
                "E-PARSE-042: ({form} …) takes {expected} operands, found \
                 {found} (§2.7, D75)"
            ),
            Self::NotInClosedSet { symbol, set } => write!(
                f,
                "E-PARSE-015: '{symbol}' is not a member of the closed {set} \
                 set — it is never ignored and never reads as false (§6.3)"
            ),
            Self::StringInExpressionPosition { literal } => write!(
                f,
                "E-PARSE-010: the string {literal:?} is in expression position; \
                 §1.5 admits strings at :material-basis and vector ids only, and \
                 Str has no operations (§3.1) — an atom rejected by position"
            ),
            Self::GraphFlagOutsideDomain => write!(
                f,
                "E-PARSE-013: :graph is a flag keyword of the `domain` form and \
                 is illegal elsewhere (§1.6, D42)"
            ),
            Self::StrengthFieldInit { field } => write!(
                f,
                "E-PARSE-041: the :strength operand is {field}'s only writer at \
                 mint time — two writers for one field in one form is an \
                 authoring bug (§2.8)"
            ),
            Self::FieldInitOwnerMismatch {
                field,
                verb_type,
                owner,
            } => write!(
                f,
                "E-TYPE-014: field-init {field} owns off {owner}, but the verb \
                 mints a {verb_type} (§2.8)"
            ),
        }
    }
}

impl std::error::Error for GrammarError {}

/// Every `<enum-ref>` operand position the language has, as
/// `(form head, 1-based operand index, demanded kind)` — D74's list plus
/// §2.8's own per-verb typing, which D74 states as one class.
const ENUM_REF_POSITIONS: [(&str, usize, EnumKind); 16] = [
    ("nodes", 1, EnumKind::NodeType),
    ("edges", 1, EnumKind::EdgeType),
    ("neighbors", 2, EnumKind::EdgeType),
    ("neighbors", 4, EnumKind::NodeType),
    ("hyperedges", 1, EnumKind::HyperedgeType),
    ("members-of", 2, EnumKind::HyperedgeType),
    ("hyperedges-of", 2, EnumKind::HyperedgeType),
    ("the", 1, EnumKind::NodeType),
    ("edge-between", 1, EnumKind::EdgeType),
    ("domain", 1, EnumKind::NodeType),
    ("emit", 1, EnumKind::EventType),
    ("add-node", 1, EnumKind::NodeType),
    ("add-edge", 1, EnumKind::EdgeType),
    ("remove-edge", 1, EnumKind::EdgeType),
    ("add-hyperedge", 1, EnumKind::HyperedgeType),
    ("remove-node", usize::MAX, EnumKind::NodeType), // no enum-ref operand
];

/// The kind demanded at `(head, operand)`, if that position is typed.
fn demanded_kind(head: &str, operand: usize) -> Option<EnumKind> {
    ENUM_REF_POSITIONS
        .iter()
        .find(|(h, i, _)| *h == head && *i == operand)
        .map(|(_, _, kind)| *kind)
}

/// Walk a form tree and apply D74's class rule to every typed operand
/// position. Untyped positions are left alone: an enum-ref elsewhere is a
/// value (§3.1's `Enum<T>`), not a mis-kinded operand.
///
/// # Errors
///
/// [`GrammarError::WrongEnumKind`] (`E-TYPE-011`).
pub fn check_enum_ref_kinds(expr: &SExpr) -> Result<(), GrammarError> {
    let SExpr::List(items) = expr else {
        return Ok(());
    };
    if let Some(SExpr::Atom(Atom::Symbol(head))) = items.first() {
        for (operand, child) in items.iter().enumerate().skip(1) {
            let SExpr::Atom(Atom::EnumRef { enum_type, member }) = child else {
                continue;
            };
            let Some(expected) = demanded_kind(head, operand) else {
                continue;
            };
            let written = EnumKind::from_type_name(enum_type);
            if written != Some(expected) {
                return Err(GrammarError::WrongEnumKind {
                    form: head.clone(),
                    operand,
                    expected,
                    found: format!("{enum_type}/{member}"),
                });
            }
        }
    }
    for child in items {
        check_enum_ref_kinds(child)?;
    }
    Ok(())
}

/// The three minting verbs whose element type is an operand, so D37's
/// field-init owner check is **static** there (§2.8).
const MINTING_VERBS: [&str; 3] = ["add-node", "add-edge", "add-hyperedge"];

/// Walk a form tree and apply D37 to every `<field-init>` of a minting
/// verb: a qname naming the implicit `<edge-type>/strength` on `add-edge`
/// is `E-PARSE-041`, and one owning off a different type is `E-TYPE-014`.
///
/// # Errors
///
/// [`GrammarError::StrengthFieldInit`] / [`GrammarError::FieldInitOwnerMismatch`].
pub fn check_field_init_owners(
    expr: &SExpr,
    vocabulary: &ClosedVocabulary,
) -> Result<(), GrammarError> {
    let SExpr::List(items) = expr else {
        return Ok(());
    };
    if let Some(SExpr::Atom(Atom::Symbol(head))) = items.first() {
        if MINTING_VERBS.contains(&head.as_str()) {
            check_one_verbs_field_inits(head, items, vocabulary)?;
        }
    }
    for child in items {
        check_field_init_owners(child, vocabulary)?;
    }
    Ok(())
}

fn check_one_verbs_field_inits(
    head: &str,
    items: &[SExpr],
    vocabulary: &ClosedVocabulary,
) -> Result<(), GrammarError> {
    let Some(SExpr::Atom(Atom::EnumRef { enum_type, member })) = items.get(1) else {
        return Ok(()); // a mis-shaped verb is the bound checker's rejection
    };
    let verb_type = format!("{enum_type}/{member}");
    for child in &items[2..] {
        let SExpr::List(pair) = child else { continue };
        let Some(SExpr::Atom(Atom::QName(field))) = pair.first() else {
            continue; // `(members …)` and non-field-init operands
        };
        let segment = field.split('/').next().unwrap_or(field);
        let leaf = field.rsplit('/').next().unwrap_or(field);
        if head == "add-edge" && leaf == "strength" {
            return Err(GrammarError::StrengthFieldInit {
                field: field.clone(),
            });
        }
        let Ok((owner_kind, owner_member)) = vocabulary.owner_of(segment) else {
            continue; // E-LOAD-023 is the declaration reader's rejection
        };
        let owner = format!("{}/{owner_member}", owner_kind.type_name());
        if owner != verb_type {
            return Err(GrammarError::FieldInitOwnerMismatch {
                field: field.clone(),
                verb_type,
                owner,
            });
        }
    }
    Ok(())
}

/// The closed terminal sets §2 fixes, and the arities its productions do.
/// `min`/`max` are operand counts **after** an optional `:as <symbol>` is
/// stripped; `usize::MAX` means "no upper bound" (a variadic body).
const ARITIES: [(&str, usize, usize, &str); 20] = [
    ("nodes", 1, 2, "1 (or 2 with a predicate)"),
    ("edges", 1, 2, "1 (or 2 with a predicate)"),
    ("hyperedges", 1, 2, "1 (or 2 with a predicate)"),
    // D51: the mandatory fourth operand — element expr, EdgeType,
    // direction, result NodeType.
    ("neighbors", 4, 4, "exactly 4"),
    ("members-of", 2, 2, "exactly 2"),
    ("hyperedges-of", 2, 2, "exactly 2"),
    ("the", 1, 1, "exactly 1"),
    ("field-of", 2, 2, "exactly 2"),
    ("edge-between", 3, 3, "exactly 3"),
    ("metric-of", 2, 2, "exactly 2"),
    ("domain", 1, 1, "exactly 1"),
    ("if", 3, 3, "exactly 3"),
    ("not", 1, 1, "exactly 1"),
    ("forall", 2, 2, "exactly 2"),
    ("exists", 1, 2, "1 (or 2 with a body)"),
    ("select-max", 2, 2, "exactly 2"),
    ("select-min", 2, 2, "exactly 2"),
    ("update-node", 3, 3, "exactly 3"),
    ("update-edge", 3, 3, "exactly 3"),
    ("update-hyperedge", 3, 3, "exactly 3"),
];

/// The closed five-member `<fold-op>` set (§2.7).
const FOLD_OPS: [&str; 5] = ["sum", "mean", "min", "max", "count"];
/// The closed four-member `<update-op>` set (§2.8).
const UPDATE_OPS: [&str; 4] = ["add", "sub", "set", "scale"];
/// The closed four-member `<arith>` set and six-member `<cmp>` set (§2.4,
/// §2.7) — one lexical class, so one list.
const OPERATORS: [&str; 10] = ["<", "<=", ">", ">=", "=", "!=", "+", "-", "*", "/"];
/// The four `<arith>` members, which are strictly binary.
const ARITH: [&str; 4] = ["+", "-", "*", "/"];

/// Operand count with an optional `:as <symbol>` removed.
fn operand_count(items: &[SExpr]) -> usize {
    let mut count = 0;
    let mut i = 1;
    while i < items.len() {
        if let SExpr::Atom(Atom::Keyword(kw)) = &items[i] {
            if kw == "as" {
                i += 2;
                continue;
            }
        }
        count += 1;
        i += 1;
    }
    count
}

/// D75: apply every fixed arity and every closed terminal set, at load.
///
/// `fold` is checked separately from `ARITIES` because its own operand
/// count depends on whether a `:weight` is present, and because its
/// `<fold-op>` is the closed set this same pass checks.
///
/// # Errors
///
/// [`GrammarError::Arity`] (`E-PARSE-042`),
/// [`GrammarError::ArithmeticArity`] (`E-PARSE-040`),
/// [`GrammarError::NotInClosedSet`] (`E-PARSE-015`).
pub fn check_arities_and_closed_sets(expr: &SExpr) -> Result<(), GrammarError> {
    let SExpr::List(items) = expr else {
        return Ok(());
    };
    match items.first() {
        Some(SExpr::Atom(Atom::Operator(op))) => {
            if ARITH.contains(&op.as_str()) && items.len() != 3 {
                return Err(GrammarError::ArithmeticArity {
                    operator: op.clone(),
                    found: items.len() - 1,
                });
            }
            if !ARITH.contains(&op.as_str()) && OPERATORS.contains(&op.as_str()) && items.len() != 3
            {
                return Err(GrammarError::Arity {
                    form: op.clone(),
                    found: items.len() - 1,
                    expected: "exactly 2",
                });
            }
        }
        Some(SExpr::Atom(Atom::Symbol(head))) => {
            check_head_arity(head, items)?;
        }
        _ => {}
    }
    for child in items {
        check_arities_and_closed_sets(child)?;
    }
    Ok(())
}

fn check_head_arity(head: &str, items: &[SExpr]) -> Result<(), GrammarError> {
    let count = operand_count(items);
    if let Some((_, min, max, expected)) = ARITIES.iter().find(|(h, _, _, _)| *h == head) {
        if count < *min || count > *max {
            return Err(GrammarError::Arity {
                form: head.to_owned(),
                found: count,
                expected,
            });
        }
    }
    if head == "fold" {
        // (fold <fold-op> <query> <elem-name>? <expr> (:weight <expr>)?)
        // — 3 operands, or 5 with the weight keyword and its expression.
        if count != 3 && count != 5 {
            return Err(GrammarError::Arity {
                form: head.to_owned(),
                found: count,
                expected: "3 (or 5 with :weight)",
            });
        }
        if let Some(SExpr::Atom(Atom::Symbol(op))) = items.get(1) {
            if !FOLD_OPS.contains(&op.as_str()) {
                return Err(GrammarError::NotInClosedSet {
                    symbol: op.clone(),
                    set: "<fold-op>",
                });
            }
        }
    }
    // An `<update-op>` sits in the third operand of the three update verbs;
    // a fifth head there — the `(unset …)` the frozen estate reaches for —
    // is E-PARSE-015 (§2.8: the set is closed).
    if matches!(head, "update-node" | "update-edge" | "update-hyperedge") {
        if let Some(SExpr::List(op_items)) = items.get(3) {
            if let Some(SExpr::Atom(Atom::Symbol(op))) = op_items.first() {
                if !UPDATE_OPS.contains(&op.as_str()) {
                    return Err(GrammarError::NotInClosedSet {
                        symbol: op.clone(),
                        set: "<update-op>",
                    });
                }
            }
        }
    }
    Ok(())
}

/// D75 / §3.8 item 4: a string literal anywhere in a rule's `<when>` or
/// `<effects>` is `E-PARSE-010`. Transcribed systems carrying `predicate`
/// or `description` strings convert them to enum-refs or drop them — the
/// rule id already identifies the rule, and an event whose payload restates
/// its own provenance in prose is carrying a log line, not state.
///
/// The walk covers the `<when>` and `<effects>` bodies **and every `:expr`
/// binding operand** (§2.5) — a `:expr` is an expression position like any
/// other, and the crate's sibling passes (`scope::check_foreign_field_scoping`,
/// `domain::reference_sites`) already treat it as one. It starts *below*
/// the rule's own options, so `:material-basis`'s string — a rule-level
/// option, not an expression — is never reached.
///
/// # Errors
///
/// [`GrammarError::StringInExpressionPosition`].
pub fn check_string_positions(rule: &SExpr) -> Result<(), GrammarError> {
    let SExpr::List(items) = rule else {
        return Ok(());
    };
    for child in items {
        let SExpr::List(inner) = child else { continue };
        match inner.first() {
            Some(SExpr::Atom(Atom::Symbol(h))) if h == "when" || h == "effects" => {
                for body in &inner[1..] {
                    walk_for_strings(body)?;
                }
            }
            Some(SExpr::Atom(Atom::Symbol(h))) if h == "bindings" => {
                for row in &inner[1..] {
                    let SExpr::List(cells) = row else { continue };
                    for window in cells.windows(2) {
                        if let [SExpr::Atom(Atom::Keyword(kw)), operand] = window {
                            if kw == "expr" {
                                walk_for_strings(operand)?;
                            }
                        }
                    }
                }
            }
            _ => {}
        }
    }
    Ok(())
}

fn walk_for_strings(expr: &SExpr) -> Result<(), GrammarError> {
    match expr {
        SExpr::Atom(Atom::Str(s)) => {
            Err(GrammarError::StringInExpressionPosition { literal: s.clone() })
        }
        SExpr::Atom(_) => Ok(()),
        SExpr::List(items) => {
            for child in items {
                walk_for_strings(child)?;
            }
            Ok(())
        }
    }
}

/// D42: `:graph` is legal only inside a `domain` form; anywhere else it is
/// an unrecognized keyword in that position and `E-PARSE-013` — never
/// ignored, because the keyword set is closed (§1.6).
///
/// # Errors
///
/// [`GrammarError::GraphFlagOutsideDomain`].
pub fn check_graph_flag_placement(expr: &SExpr) -> Result<(), GrammarError> {
    let SExpr::List(items) = expr else {
        return Ok(());
    };
    let in_domain_form =
        matches!(items.first(), Some(SExpr::Atom(Atom::Symbol(h))) if h == "domain");
    for child in items {
        if !in_domain_form {
            if let SExpr::Atom(Atom::Keyword(kw)) = child {
                if kw == "graph" {
                    return Err(GrammarError::GraphFlagOutsideDomain);
                }
            }
        }
        check_graph_flag_placement(child)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{check_enum_ref_kinds, check_field_init_owners};
    use crate::reader::read;
    use crate::vocabulary::{ClosedVocabulary, EnumKind};

    fn vocabulary() -> ClosedVocabulary {
        ClosedVocabulary::new([
            (
                EnumKind::NodeType,
                vec!["SOCIAL_CLASS".to_owned(), "POLITY".to_owned()],
            ),
            (EnumKind::EdgeType, vec!["SOLIDARITY".to_owned()]),
            (EnumKind::HyperedgeType, vec!["COMMUNITY".to_owned()]),
            (EnumKind::EventType, vec!["RUPTURE".to_owned()]),
        ])
        .unwrap()
    }

    fn e(source: &str) -> crate::reader::SExpr {
        read(source).expect("test source must parse").0
    }

    #[test]
    fn every_typed_operand_position_rejects_the_wrong_enum_kind() {
        for source in [
            "(nodes EdgeType/SOLIDARITY)",
            "(edges NodeType/SOCIAL_CLASS)",
            "(hyperedges NodeType/SOCIAL_CLASS)",
            "(members-of h NodeType/SOCIAL_CLASS)",
            "(hyperedges-of n EdgeType/SOLIDARITY)",
            "(the EdgeType/SOLIDARITY)",
            "(edge-between NodeType/SOCIAL_CLASS a b)",
            "(domain EdgeType/SOLIDARITY)",
            "(emit NodeType/SOCIAL_CLASS)",
            "(add-node EdgeType/SOLIDARITY n1)",
            "(add-hyperedge EdgeType/SOLIDARITY h1 (members a b))",
        ] {
            let err = check_enum_ref_kinds(&e(source)).expect_err(source);
            assert_eq!(err.spec_code(), "E-TYPE-011", "{source}");
        }
    }

    #[test]
    fn neighbors_rejects_the_two_operands_swapped_at_both_positions() {
        // §2.6 (C8): operand 2 is the EdgeType traversed, operand 4 the
        // result NodeType. Swapping them is E-TYPE-011 at both.
        let err = check_enum_ref_kinds(&e(
            "(neighbors self NodeType/SOCIAL_CLASS :out EdgeType/SOLIDARITY)",
        ))
        .unwrap_err();
        assert_eq!(err.spec_code(), "E-TYPE-011");
        assert!(check_enum_ref_kinds(&e(
            "(neighbors self EdgeType/SOLIDARITY :out NodeType/SOCIAL_CLASS)"
        ))
        .is_ok());
    }

    #[test]
    fn an_enum_ref_in_an_untyped_position_is_a_value_not_a_mis_kinded_operand() {
        // §3.1's `Enum<T>` compares with =/!=; that position types nothing.
        assert!(check_enum_ref_kinds(&e("(= NodeType/POLITY NodeType/POLITY)")).is_ok());
    }

    #[test]
    fn an_add_edge_field_init_naming_strength_is_e_parse_041() {
        let err = check_field_init_owners(
            &e("(add-edge EdgeType/SOLIDARITY a b :strength 0.5c (solidarity/strength 0.9c))"),
            &vocabulary(),
        )
        .unwrap_err();
        assert_eq!(err.spec_code(), "E-PARSE-041");
    }

    #[test]
    fn a_field_init_owning_off_the_wrong_type_is_e_type_014() {
        let err = check_field_init_owners(
            &e("(add-node NodeType/SOCIAL_CLASS n1 (polity/imperial-rent-pool 5$))"),
            &vocabulary(),
        )
        .unwrap_err();
        assert_eq!(err.spec_code(), "E-TYPE-014");
    }

    #[test]
    fn a_field_init_owning_off_the_verbs_own_type_accepts() {
        assert!(check_field_init_owners(
            &e("(add-node NodeType/SOCIAL_CLASS n1 (social-class/wealth 5$))"),
            &vocabulary(),
        )
        .is_ok());
        assert!(check_field_init_owners(
            &e("(add-edge EdgeType/SOLIDARITY a b :strength 0.5c (solidarity/tension 0.1i))"),
            &vocabulary(),
        )
        .is_ok());
    }
}
