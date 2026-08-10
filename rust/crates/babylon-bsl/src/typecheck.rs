//! The BSL typechecker's first slice: the §3.4 aggregation law
//! (`bsl-language.rst` — "the extensive/intensive lexicon becomes real
//! types"). The load-bearing rule the plan calls out: unweighted
//! aggregation of an intensive-kinded field is a `TypeError` at load, not
//! a runtime surprise — the intensive-aggregation-variance-error class,
//! caught by the compiler.
//!
//! **Deviation from the Phase 1 plan's sketch, recorded:** the sketch
//! rejected every unweighted op except `count` on an intensive field. The
//! normative law is §3.4's five-row PER-OPERATOR table — `min`/`max` are
//! kind-neutral and always legal, and `sum` of an intensive field is
//! `E-TYPE-041` even WITH a weight (summing an intensive quantity is
//! meaningless; no weight rescues it). This module implements the table.
//!
//! Scope (deliberately narrow, per the plan): the fold BODY here is a bare
//! field reference, so its kind is always a declared `FieldKind`.
//! Kind-NEUTRAL bodies (literals, `:const` bindings, arithmetic over them)
//! arrive with the expression typechecker in later tasks, as does
//! `E-TYPE-040` kind mixing.

use crate::exemptions::IntensiveAggregationExemption;
use crate::reader::{Atom, SExpr};
use crate::score_class::{classify, ClassEnv};
use crate::types::{BslType, FieldDecl, FieldKind};
use std::collections::HashMap;

/// The §3.4 aggregation-law error codes, plus the two the R9 chapters add
/// to this module's remit (`E-TYPE-016` on a selection score, `E-TYPE-017`
/// on a reference comparison).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TypeCode {
    /// `E-TYPE-016` — a `select-max`/`select-min` score whose static type
    /// is not a comparable scalar (D46).
    NonComparableScore,
    /// `E-TYPE-017` — a reference compared with an ordering operator, with
    /// a reference of a different kind, or with a non-reference (D67).
    BadReferenceComparison,
    /// `E-TYPE-041` — summing an intensive quantity is meaningless.
    SumOfIntensive,
    /// `E-TYPE-042` — unweighted `mean` of an intensive field.
    UnweightedMeanOfIntensive,
    /// `E-TYPE-043` — a `mean` weight that is not extensive-kinded.
    NonExtensiveWeight,
}

impl TypeCode {
    /// The spec's code string, e.g. `"E-TYPE-042"`.
    #[must_use]
    pub fn spec_code(self) -> &'static str {
        match self {
            Self::NonComparableScore => "E-TYPE-016",
            Self::BadReferenceComparison => "E-TYPE-017",
            Self::SumOfIntensive => "E-TYPE-041",
            Self::UnweightedMeanOfIntensive => "E-TYPE-042",
            Self::NonExtensiveWeight => "E-TYPE-043",
        }
    }
}

/// A typechecking failure: spec-coded where the spec codes it, structural
/// otherwise (`code: None`) — no code is invented.
#[derive(Debug, Clone, PartialEq)]
pub struct TypeError {
    /// The spec code, when §3.4 assigns one.
    pub code: Option<TypeCode>,
    /// Human-readable detail.
    pub message: String,
}

/// The typechecker's environment: declared fields and the exemption ledger.
#[derive(Debug, Clone)]
pub struct TypeEnv {
    /// Declared fields by BSL name (kebab-case symbols or qnames).
    pub fields: HashMap<String, FieldDecl>,
    /// The `EXTENSIVE_INTENSIVE_EXEMPTIONS` ledger in force — an exemption
    /// suppresses `E-TYPE-041/042/043` for its named field only (§3.4).
    pub exemptions: &'static [IntensiveAggregationExemption],
}

/// Typecheck one aggregation form: `(op field)` or
/// `(mean field :weight weight-field)`, with `op` one of
/// `sum | mean | min | max | count`, applying §3.4's per-operator table.
///
/// # Errors
/// [`TypeError`] with the spec code for a §3.4 violation, or with
/// `code: None` for a malformed form or an unknown field.
pub fn typecheck_aggregation(expr: &SExpr, env: &TypeEnv) -> Result<BslType, TypeError> {
    let (op, field_name, weight_name) = destructure_aggregation(expr)?;
    let field = resolve_field(env, field_name)?;
    let weight = match weight_name {
        Some(name) => Some(resolve_field(env, name)?),
        None => None,
    };
    let exempted = env.exemptions.iter().any(|e| e.field_name == field_name);
    match op {
        "sum" => {
            if field.kind == FieldKind::Intensive && !exempted {
                return Err(TypeError {
                    code: Some(TypeCode::SumOfIntensive),
                    message: format!(
                        "sum of intensive field '{field_name}': summing an intensive \
                         quantity is meaningless — no weight rescues it (§3.4)"
                    ),
                });
            }
            Ok(field.ty.clone())
        }
        "mean" => {
            if field.kind == FieldKind::Intensive && !exempted {
                match weight {
                    None => {
                        return Err(TypeError {
                            code: Some(TypeCode::UnweightedMeanOfIntensive),
                            message: format!(
                                "unweighted mean of intensive field '{field_name}': add an \
                                 explicit extensive :weight term (§3.4)"
                            ),
                        })
                    }
                    Some(w) if w.kind != FieldKind::Extensive => {
                        return Err(TypeError {
                            code: Some(TypeCode::NonExtensiveWeight),
                            message: format!(
                                "the :weight of a mean over intensive field '{field_name}' \
                                 must be extensive-kinded (§3.4)"
                            ),
                        })
                    }
                    Some(_) => {}
                }
            }
            Ok(field.ty.clone())
        }
        // §3.4 row 5: min/max are kind-neutral operations, legal on any kind.
        "min" | "max" => Ok(field.ty.clone()),
        // §3.4 row 6: count is always legal; result Int, extensive.
        "count" => Ok(BslType::Int),
        other => Err(TypeError {
            code: None,
            message: format!("unknown aggregation operator '{other}'"),
        }),
    }
}

/// Destructure `(op field)` / `(op field :weight weight-field)` into its
/// three named parts, rejecting every other shape loudly.
fn destructure_aggregation(expr: &SExpr) -> Result<(&str, &str, Option<&str>), TypeError> {
    let malformed = || TypeError {
        code: None,
        message: "aggregation form must be (op field) or (op field :weight weight-field)".into(),
    };
    let SExpr::List(items) = expr else {
        return Err(malformed());
    };
    let [op_expr, field_expr, rest @ ..] = items.as_slice() else {
        return Err(malformed());
    };
    let SExpr::Atom(Atom::Symbol(op)) = op_expr else {
        return Err(malformed());
    };
    let field_name = field_ref_name(field_expr).ok_or_else(malformed)?;
    let weight_name = match rest {
        [] => None,
        [SExpr::Atom(Atom::Keyword(kw)), weight_expr] if kw == "weight" => {
            Some(field_ref_name(weight_expr).ok_or_else(malformed)?)
        }
        _ => return Err(malformed()),
    };
    Ok((op, field_name, weight_name))
}

/// A field reference is a `symbol` or a `qname` (§1.4's own example:
/// `social-class/wealth`).
fn field_ref_name(expr: &SExpr) -> Option<&str> {
    match expr {
        SExpr::Atom(Atom::Symbol(name) | Atom::QName(name)) => Some(name),
        _ => None,
    }
}

fn resolve_field<'e>(env: &'e TypeEnv, name: &str) -> Result<&'e FieldDecl, TypeError> {
    env.fields.get(name).ok_or_else(|| TypeError {
        code: None,
        message: format!("unknown field: '{name}'"),
    })
}

/// Walk a form tree and apply D46 to every `select-max`/`select-min`
/// score: it must have a **comparable scalar** static type. `Bool`,
/// `Enum<T>`, `Str`, references and sets are `E-TYPE-016`.
///
/// **Kind is unconstrained on the score, deliberately** (D46): §3.4 polices
/// *aggregation*, where an unweighted mean of an intensive quantity is the
/// recorded variance error. Ranking elements by an intensive field
/// aggregates nothing — it orders — so the weighted-mean obligation has
/// nothing to attach to, and this function never consults a kind.
///
/// # Errors
///
/// [`TypeError`] carrying [`TypeCode::NonComparableScore`].
pub fn check_selection_scores(
    expr: &SExpr,
    env: &TypeEnv,
    bindings: &[crate::bindings::BindingDecl],
) -> Result<(), TypeError> {
    let element_names = HashMap::new();
    let class_env = ClassEnv {
        bindings,
        fields: &env.fields,
        element_names: &element_names,
    };
    walk_selections(expr, &class_env)
}

fn walk_selections(expr: &SExpr, env: &ClassEnv<'_>) -> Result<(), TypeError> {
    let SExpr::List(items) = expr else {
        return Ok(());
    };
    if let Some(SExpr::Atom(Atom::Symbol(head))) = items.first() {
        if head == "select-max" || head == "select-min" {
            // The score is the last operand, after the query and an
            // optional `:as <symbol>`.
            let score = match items.get(2) {
                Some(SExpr::Atom(Atom::Keyword(kw))) if kw == "as" => items.get(4),
                other => other,
            };
            let Some(score) = score else {
                return Err(TypeError {
                    code: None,
                    message: format!("({head} <query> <elem-name>? <expr>) — missing score"),
                });
            };
            let class = classify(score, env);
            if !class.is_comparable_scalar() {
                return Err(TypeError {
                    code: Some(TypeCode::NonComparableScore),
                    message: format!(
                        "E-TYPE-016: a {head} score must be a comparable scalar \
                         (Int, Currency, Probability, Intensity, Coefficient or \
                         Real); this one classifies as {class:?} (§2.7)"
                    ),
                });
            }
        }
    }
    for child in items {
        walk_selections(child, env)?;
    }
    Ok(())
}

/// D67: **references compare by identity, with `=` and `!=` only.**
/// Comparing a reference with an ordering operator, with a reference of a
/// different kind, or with any non-reference is `E-TYPE-017`.
///
/// There is no ordering on references *in the language*: §2.6's iteration
/// order is the executor's, and exposing it as a comparison would invite
/// content to depend on id assignment.
///
/// # Errors
///
/// [`TypeError`] carrying [`TypeCode::BadReferenceComparison`].
pub fn check_reference_comparisons(
    expr: &SExpr,
    env: &TypeEnv,
    bindings: &[crate::bindings::BindingDecl],
) -> Result<(), TypeError> {
    let element_names = HashMap::new();
    let class_env = ClassEnv {
        bindings,
        fields: &env.fields,
        element_names: &element_names,
    };
    walk_comparisons(expr, &class_env)
}

const ORDERING_OPERATORS: [&str; 4] = ["<", "<=", ">", ">="];

fn walk_comparisons(expr: &SExpr, env: &ClassEnv<'_>) -> Result<(), TypeError> {
    let SExpr::List(items) = expr else {
        return Ok(());
    };
    if let [SExpr::Atom(Atom::Operator(op)), lhs, rhs] = items.as_slice() {
        let (left, right) = (classify(lhs, env), classify(rhs, env));
        if left.is_reference() || right.is_reference() {
            let legal = matches!(op.as_str(), "=" | "!=")
                && left.is_reference()
                && right.is_reference()
                && left == right;
            if !legal {
                let why = if ORDERING_OPERATORS.contains(&op.as_str()) {
                    "there is no ordering on references (§2.4)"
                } else if !left.is_reference() || !right.is_reference() {
                    "a reference compares only against a reference (§2.4)"
                } else {
                    "a reference compares only against one of the SAME kind (§2.4)"
                };
                return Err(TypeError {
                    code: Some(TypeCode::BadReferenceComparison),
                    message: format!("E-TYPE-017: ({op} {left:?} {right:?}) — {why}"),
                });
            }
        }
    }
    for child in items {
        walk_comparisons(child, env)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{typecheck_aggregation, TypeCode, TypeEnv};
    use crate::exemptions::IntensiveAggregationExemption;
    use crate::reader::read;
    use crate::types::{BslType, FieldDecl, FieldKind};
    use std::collections::HashMap;

    fn env() -> TypeEnv {
        let mut fields = HashMap::new();
        fields.insert(
            "wealth-share".to_string(),
            FieldDecl {
                ty: BslType::Coefficient,
                kind: FieldKind::Intensive,
            },
        );
        fields.insert(
            "consciousness".to_string(),
            FieldDecl {
                ty: BslType::Intensity,
                kind: FieldKind::Intensive,
            },
        );
        fields.insert(
            "population".to_string(),
            FieldDecl {
                ty: BslType::Int,
                kind: FieldKind::Extensive,
            },
        );
        fields.insert(
            "wealth".to_string(),
            FieldDecl {
                ty: BslType::Currency,
                kind: FieldKind::Extensive,
            },
        );
        TypeEnv {
            fields,
            exemptions: &[],
        }
    }

    fn check(source: &str, env: &TypeEnv) -> Result<BslType, super::TypeError> {
        let (expr, _) = read(source).expect("test source should parse");
        typecheck_aggregation(&expr, env)
    }

    fn code_of(source: &str, env: &TypeEnv) -> Option<TypeCode> {
        check(source, env).expect_err("should be a type error").code
    }

    // ---- the five-row table (§3.4) ----

    #[test]
    fn unweighted_mean_of_an_intensive_field_is_e_type_042() {
        // The recorded variance error, caught at load.
        assert_eq!(
            code_of("(mean wealth-share)", &env()),
            Some(TypeCode::UnweightedMeanOfIntensive)
        );
    }

    #[test]
    fn mean_of_an_intensive_field_with_an_extensive_weight_is_legal() {
        assert_eq!(
            check("(mean wealth-share :weight population)", &env()),
            Ok(BslType::Coefficient)
        );
    }

    #[test]
    fn a_weight_that_is_not_extensive_is_e_type_043() {
        // consciousness is intensive — weighting by it is the same error
        // one level up.
        assert_eq!(
            code_of("(mean wealth-share :weight consciousness)", &env()),
            Some(TypeCode::NonExtensiveWeight)
        );
    }

    #[test]
    fn sum_of_an_intensive_field_is_e_type_041_even_with_a_weight() {
        // §3.4: summing an intensive quantity is meaningless — no weight
        // rescues it (deviation from the plan sketch, recorded above).
        assert_eq!(
            code_of("(sum wealth-share)", &env()),
            Some(TypeCode::SumOfIntensive)
        );
        assert_eq!(
            code_of("(sum wealth-share :weight population)", &env()),
            Some(TypeCode::SumOfIntensive)
        );
    }

    #[test]
    fn sum_of_an_extensive_field_is_legal() {
        assert_eq!(check("(sum wealth)", &env()), Ok(BslType::Currency));
    }

    #[test]
    fn unweighted_mean_of_an_extensive_field_is_legal() {
        assert_eq!(check("(mean wealth)", &env()), Ok(BslType::Currency));
    }

    #[test]
    fn min_and_max_are_kind_neutral_and_always_legal() {
        // The plan's sketch would have wrongly rejected these (§3.4 row 5).
        assert_eq!(
            check("(min wealth-share)", &env()),
            Ok(BslType::Coefficient)
        );
        assert_eq!(check("(max consciousness)", &env()), Ok(BslType::Intensity));
    }

    #[test]
    fn count_is_always_legal_and_returns_int() {
        assert_eq!(check("(count wealth-share)", &env()), Ok(BslType::Int));
    }

    // ---- exemptions (§3.4: named-field suppression) ----

    const TEST_EXEMPTION: &[IntensiveAggregationExemption] = &[IntensiveAggregationExemption {
        field_name: "wealth-share",
        reason: "test-only: verifies the suppression path",
        owner: "test-suite",
        date: "2026-07-30",
    }];

    #[test]
    fn an_exemption_suppresses_the_law_for_its_named_field_only() {
        let mut exempted = env();
        exempted.exemptions = TEST_EXEMPTION;
        assert!(check("(mean wealth-share)", &exempted).is_ok());
        assert!(check("(sum wealth-share)", &exempted).is_ok());
        // A different intensive field still rejects.
        assert_eq!(
            code_of("(mean consciousness)", &exempted),
            Some(TypeCode::UnweightedMeanOfIntensive)
        );
    }

    // ---- structural errors (no spec code) ----

    #[test]
    fn an_unknown_field_is_a_loud_uncoded_error() {
        let err = check("(sum imperial-rent)", &env()).unwrap_err();
        assert_eq!(err.code, None);
        assert!(err.message.contains("imperial-rent"));
    }

    #[test]
    fn an_unknown_operator_is_a_loud_uncoded_error() {
        let err = check("(median wealth)", &env()).unwrap_err();
        assert_eq!(err.code, None);
    }

    #[test]
    fn a_malformed_form_is_a_loud_uncoded_error() {
        assert!(check("wealth", &env()).is_err());
        assert!(check("(mean)", &env()).is_err());
        assert!(check("(mean wealth-share :weight)", &env()).is_err());
    }
}
