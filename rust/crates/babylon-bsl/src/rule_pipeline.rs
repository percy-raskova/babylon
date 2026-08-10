//! The composed rule-loading pipeline — the single "load a rule" entry
//! point Task 17 requires (no earlier task created it; each earlier task
//! tests its own layer in isolation by design). Composition follows the
//! §4.6 error-class ordering: lexical/syntactic (`E-LEX`/`E-PARSE`) →
//! static/type (`E-TYPE`) → load/link (`E-LOAD`), so the FIRST failure a
//! bad rule reports is the earliest-class one, matching "there is no
//! partial load and no skip-the-bad-rule mode".
//!
//! Stages, in order: read (§1/§2) → rule surface (`:material-basis`
//! `E-PARSE-011`, `:fuel` range `E-PARSE-012`) → binding declarations
//! (`E-PARSE-013/022/030/031`) → fold aggregation typecheck (§3.4,
//! `E-TYPE-041/042/043`) → anchor placement (`E-LOAD-002`) → binding
//! resolution (`E-LOAD-010/011`) → free variables (`E-LOAD-010`) → static
//! fuel bound + member-list ceilings (`E-LOAD-040/042`). The `:default`
//! allowlist lint runs LAST and is carried as findings, not an error —
//! §3.5 item 4 makes it a sign-off gate, not a load rejection.
//!
//! **Fold typecheck adapter (recorded gap):** the §3.4 checker (Task 10)
//! takes the aggregation shape `(op field (:weight wfield)?)`; this
//! pipeline adapts each real `(fold <op> <query> <body> (:weight <w>)?)`
//! whose body (and weight) are FIELD REFERENCES. `count` needs no kind and
//! always passes. A fold whose body is a compound expression needs §3.4's
//! kind PROPAGATION rules, which no Phase-1 task implements — such a fold
//! is rejected LOUDLY as unverifiable rather than passed unchecked (III.11:
//! an unverified pass-through is the silent-degradation shape).

use crate::bindings::{
    check_free_variables, parse_bindings, resolve_bindings, BindingDecl, BindingError,
    BindingVocabulary,
};
use crate::bound_checker::{check_rule, BoundError};
use crate::default_lint::{lint_defaults, DefaultLintFinding};
use crate::domain::{resolve_domain, DomainError, RuleDomain};
use crate::evaluator::{evaluate, EvalEnv, Value};
use crate::fuel::{CardinalityCeilings, IntrinsicCosts};
use crate::grammar::{
    check_enum_ref_kinds, check_field_init_owners, check_graph_flag_placement, GrammarError,
};
use crate::material_basis::{check_rule_surface, SurfaceError};
use crate::mod_anchors::{check_anchor, AnchorDecl, AnchorError};
use crate::reader::{read, Atom, ReadError, SExpr};
use crate::scope::{check_foreign_field_scoping, ScopeError};
use crate::typecheck::{typecheck_aggregation, TypeEnv, TypeError};
use std::collections::{HashMap, HashSet};

/// Everything a rule loads against. Phase 1 takes each registry as an
/// opaque input; their contents are Phase 2/3 content and engine data.
pub struct LoadContext<'a> {
    /// Declared fields / defines keys / registered metrics (§3.5).
    pub vocabulary: &'a BindingVocabulary,
    /// Declared field types and kinds (§3.4).
    pub types: &'a TypeEnv,
    /// Declared cardinality ceilings (§3.7).
    pub ceilings: &'a CardinalityCeilings,
    /// Declared intrinsic costs (§2.7).
    pub intrinsics: &'a IntrinsicCosts,
    /// Registered system names, for the anchor default (§2.3).
    pub systems: &'a HashSet<String>,
    /// The closed graph vocabulary (§3.6). `None` skips the checks that
    /// need it — D74's enum-ref class rule still runs (it is a *kind*
    /// check, independent of membership), but D37's field-init owner rule
    /// cannot resolve an owner without it and is therefore not run.
    pub vocabulary_registry: Option<&'a crate::vocabulary::ClosedVocabulary>,
    /// The rule's source file, for the `:default` allowlist lint.
    pub rule_file: &'a str,
}

/// A rule that survived every load-time gate.
#[derive(Debug, Clone)]
pub struct LoadedRule {
    /// The parsed rule form.
    pub rule: SExpr,
    /// Its declared bindings.
    pub bindings: Vec<BindingDecl>,
    /// Its anchor declaration, or `None` for the anchor default.
    pub anchor: Option<AnchorDecl>,
    /// What the rule fires over and how many times (§2.3, R9 chapter C4).
    /// `None` when no vocabulary was supplied, since the inference resolves
    /// a field qname's owning node type through the registry.
    pub domain: Option<RuleDomain>,
    /// The §3.7 static bound `check_rule` computed and accepted — the
    /// load-time PROOF that the rule fits its budget.
    pub static_bound: u64,
    /// The rule's declared `:fuel` (§2.2) — the budget it RUNS under.
    ///
    /// Distinct from `static_bound` on purpose. Metering on the computed
    /// bound would couple runtime to whatever the checker currently returns
    /// and would silently under-fund a rule whose author allotted more.
    pub declared_fuel: u64,
    /// `:default` declarations with no allowlist row — sign-off findings,
    /// never a rejection (§3.5 item 4).
    pub default_findings: Vec<DefaultLintFinding>,
}

/// A load-time rejection, tagged by the stage that raised it.
#[derive(Debug, Clone, PartialEq)]
pub enum LoadError {
    /// §1/§2 — the reader.
    Read(ReadError),
    /// §2.2 mandatory keywords.
    Surface(SurfaceError),
    /// §2.5/§3.5 binding declarations and resolution.
    Binding(BindingError),
    /// §3.4 aggregation law.
    Type(TypeError),
    /// §2's static shape rules — D74's enum-ref operand class rule and
    /// D37's field-init owner rule.
    Grammar(GrammarError),
    /// §2.3 anchors.
    Anchor(AnchorError),
    /// §2.3's rule domain (R9 chapter C4).
    Domain(DomainError),
    /// §2.5's foreign-`:field` reference scoping (R9 chapter C1).
    Scope(ScopeError),
    /// §3.7 static bound and member-list ceilings.
    Bound(BoundError),
}

impl LoadError {
    /// The spec's error code, where the failing stage names one.
    #[must_use]
    pub fn spec_code(&self) -> Option<&'static str> {
        match self {
            Self::Read(e) => match &e.kind {
                crate::reader::ReadErrorKind::Lex(code) => Some(code.spec_code()),
                _ => None,
            },
            Self::Surface(e) => e.spec_code(),
            Self::Binding(e) => e.spec_code(),
            Self::Type(e) => e.code.map(crate::typecheck::TypeCode::spec_code),
            Self::Grammar(e) => Some(e.spec_code()),
            Self::Anchor(e) => e.spec_code(),
            Self::Domain(e) => e.spec_code(),
            Self::Scope(e) => Some(e.spec_code()),
            Self::Bound(e) => e.spec_code(),
        }
    }
}

impl std::fmt::Display for LoadError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Read(e) => write!(f, "read: {}", e.message),
            Self::Surface(e) => write!(f, "{e}"),
            Self::Binding(e) => write!(f, "{e}"),
            Self::Type(e) => write!(f, "{}", e.message),
            Self::Grammar(e) => write!(f, "{e}"),
            Self::Anchor(e) => write!(f, "{e}"),
            Self::Domain(e) => write!(f, "{e}"),
            Self::Scope(e) => write!(f, "{e}"),
            Self::Bound(e) => write!(f, "{e}"),
        }
    }
}

impl std::error::Error for LoadError {}

/// Load one rule from source through every gate, in §4.6 class order.
///
/// # Errors
///
/// The first-failing stage's [`LoadError`]; a loaded content set has no
/// partially-loaded rules.
pub fn load_rule(source: &str, ctx: &LoadContext<'_>) -> Result<LoadedRule, LoadError> {
    let (rule, _) = read(source).map_err(LoadError::Read)?;
    check_rule_surface(&rule).map_err(LoadError::Surface)?;
    let bindings = parse_bindings(&rule).map_err(LoadError::Binding)?;
    // §2's static shape rules run with the other E-TYPE-class checks: the
    // enum-ref class rule (D74) needs nothing but the form, and the
    // field-init owner rule (D37) needs the vocabulary.
    check_enum_ref_kinds(&rule).map_err(LoadError::Grammar)?;
    check_graph_flag_placement(&rule).map_err(LoadError::Grammar)?;
    let mut domain = None;
    if let Some(vocabulary) = ctx.vocabulary_registry {
        check_field_init_owners(&rule, vocabulary).map_err(LoadError::Grammar)?;
        // The domain resolves BEFORE the scoping check, which needs the
        // subject node type to know which `:field` bindings are foreign.
        let resolved = resolve_domain(&rule, &bindings, vocabulary).map_err(LoadError::Domain)?;
        let subject = match &resolved {
            RuleDomain::Node(segment) => Some(segment.clone()),
            RuleDomain::Graph => None,
        };
        check_foreign_field_scoping(&rule, &bindings, subject.as_deref(), vocabulary)
            .map_err(LoadError::Scope)?;
        domain = Some(resolved);
    }
    typecheck_rule_folds(&rule, ctx.types, &bindings).map_err(LoadError::Type)?;
    let anchor = check_anchor(&rule, ctx.systems).map_err(LoadError::Anchor)?;
    resolve_bindings(&bindings, ctx.vocabulary).map_err(LoadError::Binding)?;
    check_free_variables(&rule, &bindings).map_err(LoadError::Binding)?;
    let static_bound = check_rule(&rule, ctx.ceilings, ctx.intrinsics).map_err(LoadError::Bound)?;
    let default_findings = lint_defaults(ctx.rule_file, &bindings);
    let SExpr::List(rule_items) = &rule else {
        unreachable!("check_rule_surface accepted a non-list rule form")
    };
    let declared_fuel =
        crate::bound_checker::declared_fuel(rule_items).map_err(LoadError::Bound)?;
    Ok(LoadedRule {
        rule,
        bindings,
        anchor,
        domain,
        static_bound,
        declared_fuel,
        default_findings,
    })
}

/// §3.5's evaluation-side half: build the evaluator environment from the
/// declared bindings and the values the world supplied. A required binding
/// with no supplied value is loud (`E-LOAD-010`-shaped — the loader should
/// have proven it present); an `:optional` binding takes its declared
/// default. No rule ever observes absence.
///
/// # Errors
///
/// [`BindingError::Unresolved`] for a missing required value.
pub fn bind_environment<S: std::hash::BuildHasher>(
    decls: &[BindingDecl],
    supplied: &HashMap<String, Value, S>,
) -> Result<HashMap<String, Value>, BindingError> {
    let mut env = HashMap::with_capacity(decls.len());
    for decl in decls {
        if let Some(value) = supplied.get(&decl.name) {
            env.insert(decl.name.clone(), value.clone());
            continue;
        }
        match &decl.default {
            Some(literal) => {
                env.insert(decl.name.clone(), literal_value(literal));
            }
            None => {
                return Err(BindingError::Unresolved {
                    name: decl.name.clone(),
                    what: "binding value (required, not supplied)",
                })
            }
        }
    }
    Ok(env)
}

/// §4.5's `:expr` accounting (D50), executed: a computed binding charges
/// its expression **once**, when the binding resolves, and each later
/// reference charges a variable-reference 1 like any other binding. That
/// asymmetry is the whole of the fuel win C7 buys, and it is why the same
/// algebra written twice inline costs strictly more than the same algebra
/// named once.
///
/// `:expr` bindings resolve in **declaration order** against the bindings
/// already resolved (§4.2), which is exactly the order `parse_bindings`
/// preserved and `E-PARSE-032` made acyclic.
///
/// # Errors
///
/// [`EvalError`] from the operand expression, including `E-EVAL-040` when
/// the shared meter runs out.
pub fn resolve_expr_bindings<S: std::hash::BuildHasher + Clone>(
    decls: &[BindingDecl],
    env: &mut HashMap<String, Value, S>,
    intrinsic_costs: &IntrinsicCosts,
    host: &dyn crate::intrinsic_host::IntrinsicHost,
    fuel: &mut u64,
) -> Result<(), crate::evaluator::EvalError> {
    for decl in decls {
        let crate::bindings::BindSource::Expr(expr) = &decl.source else {
            continue;
        };
        let scope = EvalEnv {
            bindings: env.iter().map(|(k, v)| (k.clone(), v.clone())).collect(),
            intrinsic_costs,
        };
        let value = evaluate(expr, &scope, host, fuel)?;
        env.insert(decl.name.clone(), value);
    }
    Ok(())
}

/// A `:default` literal's runtime value (§2.2: only literals).
fn literal_value(atom: &Atom) -> Value {
    match atom {
        Atom::Int(n) => Value::Int(*n),
        Atom::Currency(c) => Value::Currency(*c),
        Atom::Scaled(s) => {
            // Unit-interval literal, unscaled < 10⁹ — exact in f64.
            #[allow(clippy::cast_precision_loss)]
            let value = s.unscaled as f64 / 10f64.powi(i32::from(s.scale));
            Value::Real(value)
        }
        Atom::Bool(b) => Value::Bool(*b),
        // parse_bindings admits only the four literal atom classes above.
        other => unreachable!("non-literal :default survived parse_bindings: {other:?}"),
    }
}

/// Walk the rule's `<when>` and `<effects>` for `(fold …)` forms and run
/// each through the §3.4 aggregation law via the adapter described in the
/// module doc. A fold body written as a BINDING name resolves through the
/// binding's `:field` source for kind purposes — the binding carries its
/// declared kind (§3.4: "a `:field` binding carries its declared kind").
fn typecheck_rule_folds(
    rule: &SExpr,
    types: &TypeEnv,
    bindings: &[BindingDecl],
) -> Result<(), TypeError> {
    let SExpr::List(items) = rule else {
        return Ok(()); // shape errors are earlier stages' business
    };
    for child in items {
        if let SExpr::List(inner) = child {
            if matches!(inner.first(), Some(SExpr::Atom(Atom::Symbol(h))) if h == "when" || h == "effects")
            {
                for body in &inner[1..] {
                    walk_folds(body, types, bindings)?;
                }
            }
        }
    }
    Ok(())
}

fn walk_folds(expr: &SExpr, types: &TypeEnv, bindings: &[BindingDecl]) -> Result<(), TypeError> {
    let SExpr::List(items) = expr else {
        return Ok(());
    };
    if matches!(items.first(), Some(SExpr::Atom(Atom::Symbol(h))) if h == "fold") {
        typecheck_one_fold(items, types, bindings)?;
    }
    for item in items {
        walk_folds(item, types, bindings)?;
    }
    Ok(())
}

/// A fold-body field reference, resolved through the binding table when it
/// is a binding name rather than a bare qname.
fn field_ref_for(expr: &SExpr, bindings: &[BindingDecl]) -> Option<SExpr> {
    match expr {
        SExpr::Atom(Atom::QName(_)) => Some(expr.clone()),
        SExpr::Atom(Atom::Symbol(name)) => {
            let source_qname = bindings.iter().find_map(|decl| {
                if decl.name == *name {
                    if let crate::bindings::BindSource::Field(qname) = &decl.source {
                        return Some(qname.clone());
                    }
                }
                None
            });
            match source_qname {
                Some(qname) => Some(SExpr::Atom(Atom::QName(qname))),
                // Not a field binding — hand the symbol through so the §3.4
                // checker rejects it loudly as an unknown field.
                None => Some(expr.clone()),
            }
        }
        _ => None,
    }
}

/// Adapt `(fold <op> <query> <body> (:weight <w>)?)` to the Task 10
/// aggregation shape `(op body (:weight w)?)`. See the module doc for the
/// count special case and the compound-body loud rejection.
fn typecheck_one_fold(
    items: &[SExpr],
    types: &TypeEnv,
    bindings: &[BindingDecl],
) -> Result<(), TypeError> {
    let (op, body, weight) = match items {
        [_, op, _query, body] => (op, body, None),
        [_, op, _query, body, SExpr::Atom(Atom::Keyword(kw)), w] if kw == "weight" => {
            (op, body, Some(w))
        }
        _ => return Ok(()), // shape errors are the bound checker's business
    };
    let is_count = matches!(op, SExpr::Atom(Atom::Symbol(name)) if name == "count");
    if is_count {
        return Ok(()); // §3.4 row 6: count is always legal, no kind involved
    }
    let body_ref = field_ref_for(body, bindings);
    let weight_ref = match weight {
        None => None,
        Some(w) => match field_ref_for(w, bindings) {
            Some(resolved) => Some(resolved),
            None => {
                return Err(compound_fold_error());
            }
        },
    };
    let Some(body_ref) = body_ref else {
        return Err(compound_fold_error());
    };
    let mut adapted: Vec<SExpr> = vec![(*op).clone(), body_ref];
    if let Some(w) = weight_ref {
        adapted.push(SExpr::Atom(Atom::Keyword("weight".to_owned())));
        adapted.push(w);
    }
    typecheck_aggregation(&SExpr::List(adapted), types).map(|_| ())
}

fn compound_fold_error() -> TypeError {
    TypeError {
        code: None,
        message: "fold body/weight kind-propagation over compound \
                  expressions is not implemented in Phase 1 — rejected \
                  loudly rather than passed unchecked (III.11); use a \
                  field reference, or wait for the Phase-2 checker"
            .to_owned(),
    }
}
