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
