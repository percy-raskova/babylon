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
use crate::score_class::{classify, selection_result_class, ClassEnv, ScoreClass};
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
    // CT4P A3 (issue #525): `op` converts to the closed `FoldOp` sum type
    // ONCE, here, and every arm below matches it EXHAUSTIVELY — no wildcard.
    // The message text on the unrecognized-operator path is preserved
    // byte-for-byte; only the dispatch mechanism changed.
    let Some(fold_op) = crate::grammar::FoldOp::parse(op) else {
        return Err(TypeError {
            code: None,
            message: format!("unknown aggregation operator '{op}'"),
        });
    };
    match fold_op {
        crate::grammar::FoldOp::Sum => {
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
        crate::grammar::FoldOp::Mean => {
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
        crate::grammar::FoldOp::Min | crate::grammar::FoldOp::Max => Ok(field.ty.clone()),
        // §3.4 row 6: count is always legal; result Int, extensive.
        crate::grammar::FoldOp::Count => Ok(BslType::Int),
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
    walk_typed(expr, env, bindings, &HashMap::new(), Check::Selections)
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
    walk_typed(expr, env, bindings, &HashMap::new(), Check::References)
}

/// **§2.13's `field-of` deferral (D101/D102, Organization spec §1 Q12).**
/// An `:enum-type`-declared field is read through a `:field` binding
/// exactly as any other node field is (§2.5); this is NOT extended to
/// §2.10's `field-of` accessor. A `field-of` naming an enum-declared field
/// refuses, loudly, citing D102 — deferred, not forbidden: an
/// enum-declared EDGE or HYPEREDGE field (this document does not rule one
/// out) would need `field-of` access precisely because it has no single
/// owning body to bind a `:field` against, and building that accessor is
/// left to whichever revision first has one.
///
/// This is a LOAD-time check (unlike Task 5's runtime write re-check):
/// whether a `qname` is enum-declared is a static, content-only fact, so
/// catching this before any tick executes matches §3's own law ("every
/// check in this chapter runs at content load") rather than deferring an
/// always-wrong construct to a runtime surprise on the first admitted
/// subject.
///
/// # Errors
///
/// A structural [`TypeError`] (`code: None` — D102 mints no error code;
/// this is a deferred gap, not a new failure class with its own number).
pub fn check_no_field_of_on_enum_field(expr: &SExpr, env: &TypeEnv) -> Result<(), TypeError> {
    if let SExpr::List(items) = expr {
        if let [SExpr::Atom(Atom::Symbol(head)), _referent, SExpr::Atom(Atom::QName(qname))] =
            items.as_slice()
        {
            if head == "field-of" {
                if let Some(decl) = env.fields.get(qname) {
                    if matches!(decl.ty, BslType::Enum(_)) {
                        return Err(TypeError {
                            code: None,
                            message: format!(
                                "field-of {qname}: an :enum-type-declared field is read \
                                 via a :field binding only (§2.5) — field-of is not \
                                 extended to enum-declared fields (§2.13, D102). The gap \
                                 is deferred, not forbidden: an enum-declared edge or \
                                 hyperedge field would need field-of for exactly the \
                                 reason §2.10 exists, and building that path is left to \
                                 whichever revision first has one"
                            ),
                        });
                    }
                }
            }
        }
        for child in items {
            check_no_field_of_on_enum_field(child, env)?;
        }
    }
    Ok(())
}

/// **§2.13's no-arithmetic law (D101), the static half (D118, #528 fix
/// round Item C).** `Enum<T>` supports no arithmetic (§2.13, §3.1) — an
/// `add`/`sub`/`scale` `update-op` targeting an `:enum-type`-declared
/// field is a coherence violation the field's declared type and the
/// op's own symbol already decide, in full, from content alone. Before
/// this function the only guards were THREE eval-time ones
/// (`structural_verbs.rs::refuse_arithmetic_on_enum_field`, `c268b83b`),
/// so a rule shaped exactly like this check's own red-test content
/// loaded clean and died mid-tick on the first admitted subject — the
/// same "always-wrong construct deferred to a runtime surprise" shape
/// [`check_no_field_of_on_enum_field`]'s own doc names for its sibling
/// gap, and the same static-decidability argument as `rule_pipeline.rs`
/// D102 wiring: §3's own law is "every check in this chapter runs at
/// content load, before any tick executes."
///
/// The three eval-time guards STAY, unchanged, as defense in depth
/// (the same two-site discipline `refuse_arithmetic_on_enum_field`'s own
/// doc already names for its three call sites) — this function only
/// moves the FIRST catch earlier, from the first admitted subject to
/// load.
///
/// # Errors
///
/// A structural [`TypeError`] (`code: None` — same precedent
/// [`check_no_field_of_on_enum_field`] already sets: E-EVAL-042 already
/// covers this refusal at evaluation, D118, so this is a
/// static-decidability repair, not a new failure class).
pub fn check_no_arithmetic_on_enum_field(expr: &SExpr, env: &TypeEnv) -> Result<(), TypeError> {
    if let SExpr::List(items) = expr {
        if let [SExpr::Atom(Atom::Symbol(head)), _node, SExpr::Atom(Atom::QName(qname)), SExpr::List(op_items)] =
            items.as_slice()
        {
            if head == "update-node" {
                if let [SExpr::Atom(Atom::Symbol(op)), _operand] = op_items.as_slice() {
                    if matches!(op.as_str(), "add" | "sub" | "scale") {
                        if let Some(decl) = env.fields.get(qname) {
                            if matches!(decl.ty, BslType::Enum(_)) {
                                return Err(TypeError {
                                    code: None,
                                    message: format!(
                                        "update-node {qname}: ({op} …) is not a coherent \
                                         operation on an enum-typed field — Enum<T> \
                                         supports no arithmetic (§2.13, D118); only `set` \
                                         may write it. Statically decidable from the \
                                         field's declared type and this op's own symbol \
                                         — refused here, at load, rather than left to die \
                                         mid-tick on the first admitted subject (§3's own \
                                         law: every check in this chapter runs at content \
                                         load)"
                                    ),
                                });
                            }
                        }
                    }
                }
            }
        }
        for child in items {
            check_no_arithmetic_on_enum_field(child, env)?;
        }
    }
    Ok(())
}

/// Which §2 rule the shared walker is applying. Both need the same thing —
/// the classes of the element names in scope at each node — and computing
/// that twice in two walkers is how the empty-map defect survived.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Check {
    Selections,
    References,
}

const ORDERING_OPERATORS: [&str; 4] = ["<", "<=", ">", ">="];

/// The element names an iterating or query form puts in scope for the
/// children *inside* it, and the class each denotes.
///
/// `it` always denotes the **innermost** enclosing element (D53), so an
/// inner form's insertion overwrites an outer one's. A `:as` name persists
/// through nested bodies (D54), which falls out of carrying the map down.
fn element_bindings_of(items: &[SExpr]) -> HashMap<String, ScoreClass> {
    let mut out = HashMap::new();
    let head = match items.first() {
        Some(SExpr::Atom(Atom::Symbol(s))) => s.as_str(),
        _ => return out,
    };
    // A query form's own predicate ranges over that query's elements; an
    // iterating form's body ranges over its `<query>` operand's.
    let element_class = if crate::scope::is_query(items) {
        selection_result_class(&SExpr::List(items.to_vec()))
    } else {
        match crate::scope::iterating_query_index(head).and_then(|i| items.get(i)) {
            Some(query) => selection_result_class(query),
            None => return out,
        }
    };
    out.insert("it".to_owned(), element_class);
    if let Some(name) = elem_name(items) {
        out.insert(name.to_owned(), element_class);
    }
    out
}

/// The `:as <symbol>` name a form declares, if any.
fn elem_name(items: &[SExpr]) -> Option<&str> {
    let mut i = 1;
    while i + 1 < items.len() {
        if let SExpr::Atom(Atom::Keyword(kw)) = &items[i] {
            if kw == "as" {
                if let SExpr::Atom(Atom::Symbol(name)) = &items[i + 1] {
                    return Some(name);
                }
            }
        }
        i += 1;
    }
    None
}

/// Whether child `index` sits inside the element scope `items` introduces.
///
/// Delegates to [`crate::scope::child_is_inside`] — the crate's single
/// source of truth for "a query's element predicate is a body, its element
/// operand is not". This module used to hardcode its own copy of the rule,
/// which is three implementations of one clause and exactly the shape that
/// lets a future query head diverge silently in one of them.
fn child_is_inside(items: &[SExpr], index: usize) -> bool {
    crate::scope::child_is_inside(items, index)
}

fn walk_typed(
    expr: &SExpr,
    env: &TypeEnv,
    bindings: &[crate::bindings::BindingDecl],
    element_names: &HashMap<String, ScoreClass>,
    check: Check,
) -> Result<(), TypeError> {
    let SExpr::List(items) = expr else {
        return Ok(());
    };
    let class_env = ClassEnv {
        bindings,
        fields: &env.fields,
        element_names,
    };
    match check {
        Check::Selections => check_one_selection(items, &class_env)?,
        Check::References => check_one_comparison(items, &class_env)?,
    }
    let introduced = element_bindings_of(items);
    for (index, child) in items.iter().enumerate() {
        if index > 0 && child_is_inside(items, index) && !introduced.is_empty() {
            let mut inner = element_names.clone();
            inner.extend(introduced.clone());
            walk_typed(child, env, bindings, &inner, check)?;
        } else {
            walk_typed(child, env, bindings, element_names, check)?;
        }
    }
    Ok(())
}

fn check_one_selection(items: &[SExpr], env: &ClassEnv<'_>) -> Result<(), TypeError> {
    let Some(SExpr::Atom(Atom::Symbol(head))) = items.first() else {
        return Ok(());
    };
    if head != "select-max" && head != "select-min" {
        return Ok(());
    }
    // The score is the last operand, after the query and an optional
    // `:as <symbol>`. It is evaluated INSIDE the selection's element scope,
    // so it classifies against the element bindings this form introduces.
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
    let mut inner = env.element_names.clone();
    inner.extend(element_bindings_of(items));
    let scoped = ClassEnv {
        bindings: env.bindings,
        fields: env.fields,
        element_names: &inner,
    };
    let class = classify(score, &scoped);
    if class.is_comparable_scalar() {
        return Ok(());
    }
    Err(TypeError {
        code: Some(TypeCode::NonComparableScore),
        message: format!(
            "E-TYPE-016: a {head} score must be a comparable scalar (Int, \
             Currency, Probability, Intensity, Coefficient or Real); this one \
             classifies as {class:?} (§2.7)"
        ),
    })
}

fn check_one_comparison(items: &[SExpr], env: &ClassEnv<'_>) -> Result<(), TypeError> {
    let [SExpr::Atom(Atom::Operator(op)), lhs, rhs] = items else {
        return Ok(());
    };
    let (left, right) = (classify(lhs, env), classify(rhs, env));
    if !(left.is_reference() || right.is_reference()) {
        return Ok(());
    }
    let legal = matches!(op.as_str(), "=" | "!=")
        && left.is_reference()
        && right.is_reference()
        && left == right;
    if legal {
        return Ok(());
    }
    let why = if ORDERING_OPERATORS.contains(&op.as_str()) {
        "there is no ordering on references (§2.4)"
    } else if !left.is_reference() || !right.is_reference() {
        "a reference compares only against a reference (§2.4)"
    } else {
        "a reference compares only against one of the SAME kind (§2.4)"
    };
    Err(TypeError {
        code: Some(TypeCode::BadReferenceComparison),
        message: format!("E-TYPE-017: ({op} {left:?} {right:?}) — {why}"),
    })
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

    /// CT4P A3 (issue #525): the `FoldOp` × `FieldKind` legality table,
    /// walked EXHAUSTIVELY — 5 fold-ops × the two kind-bearing `FieldKind`
    /// variants the §3.4 law actually discriminates on (`Intensive`,
    /// `Extensive`; `wealth-share`/`wealth` from `env()`, the SAME pair the
    /// individual tests above already use). `FieldKind`'s third variant,
    /// `NotApplicable` (an enum-typed field, §2.13/D101), is deliberately
    /// OUT OF SCOPE here: `typecheck_aggregation` never special-cases it —
    /// every op reaches `Ok` for a `NotApplicable`-kinded field today, a
    /// fact about the current code this table does not assert one way or
    /// the other. This is exactly the 10-row table A3's dossier item names;
    /// each row states its OWN accept/refuse verdict — nothing here infers
    /// one row from another, and a sixth `FoldOp` variant is a compile
    /// error at the `match fold_op` in `typecheck_aggregation` until this
    /// table (and that match) are updated to decide it.
    #[test]
    fn fold_op_x_field_kind_legality_table_is_exhaustive() {
        use crate::grammar::FoldOp;
        let table: [(FoldOp, &str, bool); 10] = [
            (FoldOp::Sum, "wealth-share", false), // E-TYPE-041
            (FoldOp::Sum, "wealth", true),
            (FoldOp::Mean, "wealth-share", false), // E-TYPE-042 (unweighted)
            (FoldOp::Mean, "wealth", true),
            (FoldOp::Min, "wealth-share", true), // kind-neutral
            (FoldOp::Min, "wealth", true),
            (FoldOp::Max, "wealth-share", true), // kind-neutral
            (FoldOp::Max, "wealth", true),
            (FoldOp::Count, "wealth-share", true), // always legal
            (FoldOp::Count, "wealth", true),
        ];
        for (op, field, expect_legal) in table {
            let source = format!("({} {field})", op.as_str());
            let result = check(&source, &env());
            assert_eq!(
                result.is_ok(),
                expect_legal,
                "{op:?} over {field} (unweighted): expected legal={expect_legal}, got {result:?}"
            );
        }
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

    // ---- §2.13's field-of deferral (D101/D102, Organization spec §1 Q12) ----

    fn org_env() -> TypeEnv {
        let mut registry = crate::types::EnumRegistry::default();
        let ty = registry
            .declare(
                "OrgKind",
                &["STATE_APPARATUS".to_owned(), "BUSINESS".to_owned()],
            )
            .unwrap();
        TypeEnv {
            fields: HashMap::from([
                (
                    "organization/kind".to_owned(),
                    FieldDecl {
                        ty: BslType::Enum(ty),
                        kind: FieldKind::NotApplicable,
                    },
                ),
                (
                    "organization/budget".to_owned(),
                    FieldDecl {
                        ty: BslType::Currency,
                        kind: FieldKind::Extensive,
                    },
                ),
            ]),
            exemptions: &[],
        }
    }

    #[test]
    fn field_of_over_an_enum_declared_field_refuses_citing_d102() {
        let (expr, _) = read("(field-of self organization/kind)").expect("must parse");
        let err = super::check_no_field_of_on_enum_field(&expr, &org_env()).unwrap_err();
        assert_eq!(err.code, None, "D102 mints no error code");
        assert!(err.message.contains("D102"), "{}", err.message);
        assert!(err.message.contains("organization/kind"), "{}", err.message);
    }

    #[test]
    fn field_of_over_a_non_enum_field_is_untouched() {
        let (expr, _) = read("(field-of self organization/budget)").expect("must parse");
        assert!(super::check_no_field_of_on_enum_field(&expr, &org_env()).is_ok());
    }

    #[test]
    fn field_of_over_an_enum_field_nested_inside_another_form_still_refuses() {
        // The walk must recurse into (and/if/fold/…) bodies, not just the
        // top-level form.
        let (expr, _) = read("(and #t (= (field-of self organization/kind) OrgKind/BUSINESS))")
            .expect("must parse");
        assert!(super::check_no_field_of_on_enum_field(&expr, &org_env()).is_err());
    }

    // ---- §2.13's no-arithmetic law, the static half (D118, #528 fix
    // round Item C) ----

    #[test]
    fn add_on_an_enum_declared_field_refuses_citing_d118() {
        let (expr, _) = read("(update-node self organization/kind (add 1))").expect("must parse");
        let err = super::check_no_arithmetic_on_enum_field(&expr, &org_env()).unwrap_err();
        assert_eq!(
            err.code, None,
            "D118 mints no error code — E-EVAL-042 already covers it"
        );
        assert!(err.message.contains("D118"), "{}", err.message);
        assert!(err.message.contains("organization/kind"), "{}", err.message);
    }

    #[test]
    fn sub_and_scale_on_an_enum_declared_field_both_refuse() {
        for op in ["sub", "scale"] {
            let source = format!("(update-node self organization/kind ({op} 1))");
            let (expr, _) = read(&source).expect("must parse");
            assert!(
                super::check_no_arithmetic_on_enum_field(&expr, &org_env()).is_err(),
                "{op} must refuse"
            );
        }
    }

    #[test]
    fn set_on_an_enum_declared_field_is_untouched() {
        // `set` is the ONE coherent op on an enum field (§2.13) — the
        // guard must never widen to refuse it.
        let (expr, _) = read("(update-node self organization/kind (set OrgKind/BUSINESS))")
            .expect("must parse");
        assert!(super::check_no_arithmetic_on_enum_field(&expr, &org_env()).is_ok());
    }

    #[test]
    fn add_on_a_non_enum_field_is_untouched() {
        let (expr, _) =
            read("(update-node self organization/budget (add 5$))").expect("must parse");
        assert!(super::check_no_arithmetic_on_enum_field(&expr, &org_env()).is_ok());
    }

    #[test]
    fn add_on_an_enum_field_nested_inside_a_guard_still_refuses() {
        // The walk must recurse into (guard/for-each/…) effect bodies, not
        // just the top-level effect item.
        let (expr, _) =
            read("(guard #t (update-node self organization/kind (add 1)))").expect("must parse");
        assert!(super::check_no_arithmetic_on_enum_field(&expr, &org_env()).is_err());
    }
}
