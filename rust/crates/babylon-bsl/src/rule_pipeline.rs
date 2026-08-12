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
use crate::declarations::DeclError;
use crate::default_lint::{lint_defaults, DefaultLintFinding};
use crate::domain::{resolve_domain, DomainError, RuleDomain};
use crate::evaluator::{evaluate, EvalEnv, Value};
use crate::fuel::{CardinalityCeilings, IntrinsicCosts};
use crate::grammar::{
    check_arities_and_closed_sets, check_enum_ref_kinds, check_field_init_owners,
    check_graph_flag_placement, check_string_positions, GrammarError,
};
use crate::material_basis::{check_rule_surface, SurfaceError};
use crate::mod_anchors::{check_anchor, AnchorDecl, AnchorError};
use crate::reader::{read, read_all, Atom, ReadError, SExpr};
use crate::scope::{
    check_element_names, check_foreign_field_scoping, declared_element_names, ElementNameError,
    ScopeError,
};
use crate::structural_verbs::check_no_deferred_shape_verbs;
use crate::typecheck::{
    check_no_field_of_on_enum_field, check_reference_comparisons, check_selection_scores,
    typecheck_aggregation, TypeEnv, TypeError,
};
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
    /// §2.6's `:as` element naming (R9 chapter C8).
    ElementName(ElementNameError),
    /// §3.7 static bound and member-list ceilings.
    Bound(BoundError),
    /// An `(intrinsic …)` top-form's own declaration errors — `E-LOAD-001`
    /// (duplicate name across the content set), `E-LOAD-020` (signature
    /// disagreeing with the kernel's registration), `E-LOAD-024`
    /// (reserved/prohibited/uncapped name), or uncoded malformed shapes
    /// ([`crate::declarations::parse_intrinsic_decls`]).
    Intrinsic(DeclError),
    /// No numbered code (the no-invented-codes precedent): a content set's
    /// own composition rule — exactly one `(rule …)` top-form — is
    /// [`split_content`]'s discipline, not a §2 grammar production with a
    /// reserved `E-LOAD` number.
    Content(String),
    /// No numbered code, same precedent as [`Self::Content`]: a rule using
    /// one of the six graph-shape verbs Task 12's collect-then-apply
    /// pre-state split does not yet defer (§4.2 chapter C4) — every one of
    /// those verbs IS legal §2.8 content; this is the LOAD-time half of
    /// `check_no_deferred_shape_verbs`'s own composition limit, not a
    /// grammar violation (#519 fix round, fix 4).
    DeferredShapeVerb(String),
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
            Self::ElementName(e) => Some(e.spec_code()),
            Self::Bound(e) => e.spec_code(),
            Self::Intrinsic(e) => e.spec_code(),
            Self::Content(_) | Self::DeferredShapeVerb(_) => None,
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
            Self::ElementName(e) => write!(f, "{e}"),
            Self::Bound(e) => write!(f, "{e}"),
            Self::Intrinsic(e) => write!(f, "{e}"),
            Self::Content(message) | Self::DeferredShapeVerb(message) => write!(f, "{message}"),
        }
    }
}

impl std::error::Error for LoadError {}

/// Load one rule from source through every gate, in §4.6 class order.
///
/// This reads the WHOLE `source` as one `(rule …)` form — it is the
/// single-form entry point every earlier test in this crate was written
/// against, and it stays exactly as it was. A `source` that also carries
/// `(intrinsic …)` top-forms (§2.2) needs [`crate::declarations::
/// parse_intrinsic_decls`]'s composed caller instead (`babylon-tick::
/// run_once_into` splits a combined source via `read_all` before reaching
/// either this function or that one) — see [`load_rule_form`], the half of
/// this function that a multi-form source calls directly, having already
/// isolated the one rule form itself.
///
/// # Errors
///
/// The first-failing stage's [`LoadError`]; a loaded content set has no
/// partially-loaded rules.
pub fn load_rule(source: &str, ctx: &LoadContext<'_>) -> Result<LoadedRule, LoadError> {
    let (rule, _) = read(source).map_err(LoadError::Read)?;
    load_rule_form(rule, ctx)
}

/// [`load_rule`]'s body, taking an already-parsed rule form instead of
/// re-reading one from source — the seam a multi-top-form content set
/// (§2.2) needs: its `(intrinsic …)` declarations are split out and parsed
/// BEFORE this runs (their costs feed `ctx.intrinsics`, which the static
/// fuel bound below consumes), leaving exactly the isolated `(rule …)` form
/// for every gate `load_rule` already ran.
///
/// # Errors
///
/// The first-failing stage's [`LoadError`]; a loaded content set has no
/// partially-loaded rules.
pub fn load_rule_form(rule: SExpr, ctx: &LoadContext<'_>) -> Result<LoadedRule, LoadError> {
    check_rule_surface(&rule).map_err(LoadError::Surface)?;
    let bindings = parse_bindings(&rule).map_err(LoadError::Binding)?;
    let binding_names: Vec<String> = bindings.iter().map(|d| d.name.clone()).collect();
    check_element_names(&rule, &binding_names).map_err(LoadError::ElementName)?;
    // §2's static shape rules run with the other E-TYPE-class checks: the
    // enum-ref class rule (D74) needs nothing but the form, and the
    // field-init owner rule (D37) needs the vocabulary.
    check_arities_and_closed_sets(&rule).map_err(LoadError::Grammar)?;
    check_string_positions(&rule).map_err(LoadError::Grammar)?;
    check_enum_ref_kinds(&rule).map_err(LoadError::Grammar)?;
    check_graph_flag_placement(&rule).map_err(LoadError::Grammar)?;
    // #519 fix round, fix 4: a rule using one of the six graph-shape verbs
    // Task 12's collect-then-apply split cannot yet defer must be refused
    // HERE, at load — not left to load clean and abort the first tick
    // whose guard admits a subject (structural_verbs.rs's own doc names
    // the regression this closes).
    check_no_deferred_shape_verbs(&rule).map_err(LoadError::DeferredShapeVerb)?;
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
    check_selection_scores(&rule, ctx.types, &bindings).map_err(LoadError::Type)?;
    check_reference_comparisons(&rule, ctx.types, &bindings).map_err(LoadError::Type)?;
    // §2.13 (D101/D102): field-of is not extended to enum-declared fields —
    // a static, content-only fact, so this is a load-time gate like its
    // two siblings above, not a runtime surprise on the first admitted
    // subject.
    check_no_field_of_on_enum_field(&rule, ctx.types).map_err(LoadError::Type)?;
    let anchor = check_anchor(&rule, ctx.systems).map_err(LoadError::Anchor)?;
    resolve_bindings(&bindings, ctx.vocabulary).map_err(LoadError::Binding)?;
    check_free_variables(&rule, &bindings, &declared_element_names(&rule))
        .map_err(LoadError::Binding)?;
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

/// Split one content source into its `(intrinsic …)` top-forms and its one
/// or more `(rule …)` top-forms, each paired with its own rule id.
///
/// §2.2 is normative that `<top-form> ::= <rule> | <deffield> |
/// <intrinsic-decl> | <manifest>` and that "file boundaries and file names
/// carry no semantics" — an `(intrinsic …)` declaration is ordinary
/// content, not a side channel a caller must route through a separate
/// parameter. This function is what makes that true for the standard
/// rule-loading path: it accepts intrinsic declarations and every rule
/// mixed, in ANY order, within one source string, exactly as `read_all`
/// would hand back any other multi-top-form content set.
///
/// §2.2's grammar (`<top-form>*`, zero-or-more) never limited a content set
/// to exactly one rule — that was this function's OWN cardinality check,
/// with no textual basis in the spec (Program 28 B2, Phase A Task 2). This
/// widening makes the driver honor what the grammar always admitted: one or
/// more `(rule …)` forms, in whatever order the reader encounters them
/// (this function makes no ordering claim — `babylon-tick::prepare_rules`
/// sorts into ascending rule-id byte order per §4.2/D16), duplicate ids
/// across the content set refused as `E-LOAD-001`.
///
/// (`deffield` and `manifest` top-forms are not split out here — nothing
/// in this crate's Slice 1 content path reads them from a rule source yet;
/// adding a case is mechanical when one does.)
///
/// # Errors
///
/// [`LoadError::Read`] for a parse failure; [`LoadError::Content`] (uncoded)
/// when the source contains zero `(rule …)` top-forms, or when two rule
/// forms share the same id (`E-LOAD-001`).
// The return type is a plain, un-nested pair of vecs — flagged only because
// its second element is itself a `Vec` of pairs; a type alias would be one
// more name to chase for a shape this crate already spells out in the doc
// comment above. Same precedent as `structural_verbs.rs`'s test helper.
#[allow(clippy::type_complexity)]
pub fn split_content(source: &str) -> Result<(Vec<SExpr>, Vec<(String, SExpr)>), LoadError> {
    let forms = read_all(source.as_bytes()).map_err(LoadError::Read)?;
    let mut intrinsic_forms = Vec::new();
    let mut rule_forms = Vec::new();
    for form in forms {
        if is_intrinsic_form(&form) {
            intrinsic_forms.push(form);
        } else {
            rule_forms.push(form);
        }
    }
    if rule_forms.is_empty() {
        return Err(LoadError::Content(
            "a content set needs at least one (rule …) top-form, found 0 \
             (§2.2 — intrinsic declarations do not count; deffield/manifest/metric-decl \
             top-forms are not yet split out by this function and would also land here)"
                .to_owned(),
        ));
    }
    // A set, not a `HashMap<String, ()>` — same duplicate-id-refusal shape
    // `declarations::parse_intrinsic_decls` uses for intrinsic names
    // (contains-check before insert, §2.2's duplicate-name discipline), but
    // with no payload to store per id, so nothing here needs a map's value
    // slot at all.
    let mut seen: HashSet<String> = HashSet::with_capacity(rule_forms.len());
    let mut paired = Vec::with_capacity(rule_forms.len());
    for form in rule_forms {
        let id = crate::canonical_ast::rule_id(&form)
            .map_err(|e| LoadError::Content(e.message))?
            .to_owned();
        if seen.contains(&id) {
            return Err(LoadError::Content(format!(
                "E-LOAD-001: duplicate rule id: {id} (§2.2 — rule ids must be \
                 content-set-unique, the same duplicate-name discipline \
                 parse_intrinsic_decls already enforces for intrinsic \
                 declarations)"
            )));
        }
        seen.insert(id.clone());
        paired.push((id, form));
    }
    Ok((intrinsic_forms, paired))
}

/// Whether `expr` is `(intrinsic …)` — the one top-form kind this module's
/// content-loading seam treats specially, since its declarations must be
/// parsed and turned into `IntrinsicCosts` BEFORE the rule form they feed
/// is loaded (`ctx.intrinsics` is an input to [`load_rule_form`]'s static
/// bound check, not an output of it).
fn is_intrinsic_form(expr: &SExpr) -> bool {
    matches!(
        expr,
        SExpr::List(items)
            if matches!(items.first(), Some(SExpr::Atom(Atom::Symbol(h))) if h == "intrinsic")
    )
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
/// [`crate::evaluator::EvalError`] from the operand expression, including `E-EVAL-040` when
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
            // Task 2 (P27 Phase 2 Slice 1) shaped this environment; this
            // resolver still passes `graph: None` unconditionally. That is
            // NOT a permanent fact about `:expr` bindings — §2.7's `<expr>`
            // production includes `<fold>`/`<selection>`/`<accessor>`, so a
            // `:expr` binding's own expression COULD legally contain a
            // query form, which would need the graph exactly as a guard or
            // an effect operand does. P6 (PR #514 fix round): wiring a real
            // graph reference through here is the SAME group 3 / Task 12
            // landing point as tick.rs's guard (`run_tick`'s `env`) — both
            // sites wait on the same collect-then-apply repair before a
            // live `&dyn GraphSubstrate` can be threaded in safely.
            graph: None,
            elements: Vec::new(),
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
        let SExpr::List(inner) = child else { continue };
        match inner.first() {
            Some(SExpr::Atom(Atom::Symbol(h))) if h == "when" || h == "effects" => {
                for body in &inner[1..] {
                    walk_folds(body, types, bindings)?;
                }
            }
            // §2.5 permits a `:expr` to contain a fold of its own, and
            // §3.4's law has no exemption for one. Walking only the rule
            // bodies let `(binding x :expr (fold mean … <intensive>))`
            // escape `E-TYPE-042` entirely while the identical fold written
            // in `<when>` was rejected — the same silent-bypass shape the
            // `:as` blind spot had.
            Some(SExpr::Atom(Atom::Symbol(h))) if h == "bindings" => {
                for row in &inner[1..] {
                    let SExpr::List(cells) = row else { continue };
                    for window in cells.windows(2) {
                        if let [SExpr::Atom(Atom::Keyword(kw)), operand] = window {
                            if kw == "expr" {
                                walk_folds(operand, types, bindings)?;
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

/// The declared field a fold body/weight ultimately names, if it names one.
///
/// Three shapes reduce (§3.4: kind propagates through them unchanged):
/// a bare `<qname>`; a `field-of` accessor, whose kind is the
/// declaration's exactly as a `:field` binding's is; and a binding name,
/// resolved through its source — **including a `:expr` binding**, whose
/// kind comes from its expression (§2.5, C7: "Type and kind come from the
/// expression, computed bottom-up like any other"). The `:expr` case is
/// what makes family 16's kind-propagation row expressible.
///
/// A genuinely compound body (arithmetic, an `if`, a nested fold) does
/// **not** reduce and is `None`, which the caller turns into the loud
/// unverifiable rejection — never a silent pass. `depth` bounds the
/// binding-chain walk so a pathological chain cannot loop; the
/// forward-reference ban (`E-PARSE-032`) already makes the graph a DAG, so
/// the bound is a belt on top of a brace.
fn field_ref_for(expr: &SExpr, bindings: &[BindingDecl], depth: u8) -> Option<SExpr> {
    if depth == 0 {
        return None;
    }
    match expr {
        SExpr::Atom(Atom::QName(_)) => Some(expr.clone()),
        SExpr::Atom(Atom::Symbol(name)) => {
            let decl = bindings.iter().find(|decl| decl.name == *name)?;
            match &decl.source {
                crate::bindings::BindSource::Field(qname) => {
                    Some(SExpr::Atom(Atom::QName(qname.clone())))
                }
                crate::bindings::BindSource::Expr(inner) => {
                    field_ref_for(inner, bindings, depth - 1)
                }
                // Not a field-shaped source — hand the symbol through so
                // the §3.4 checker rejects it loudly as an unknown field
                // rather than silently skipping the law.
                _ => Some(expr.clone()),
            }
        }
        SExpr::List(items) => match items.as_slice() {
            // `(field-of <expr> <qname>)` — §3.4: the accessor carries the
            // declaration's kind, identically to a `:field` binding.
            [SExpr::Atom(Atom::Symbol(head)), _, SExpr::Atom(Atom::QName(qname))]
                if head == "field-of" =>
            {
                Some(SExpr::Atom(Atom::QName(qname.clone())))
            }
            // A NESTED fold: §3.4's table says `sum`/`mean`/`min`/`max`
            // carry the body kind, so the outer fold's body kind is the
            // inner fold's body kind. This is what lets §2.6's own two-hop
            // worked example reach the aggregation law instead of the
            // unverifiable rejection. `count` is deliberately absent: its
            // result is an extensive `Int` that names no declared field, so
            // it stays with the loud Phase-1 rejection rather than getting
            // a synthetic entry in the field registry.
            [SExpr::Atom(Atom::Symbol(head)), SExpr::Atom(Atom::Symbol(op)), rest @ ..]
                if head == "fold" && matches!(op.as_str(), "sum" | "mean" | "min" | "max") =>
            {
                let inner = strip_elem_name(rest);
                inner
                    .get(1)
                    .and_then(|body| field_ref_for(body, bindings, depth - 1))
            }
            _ => None,
        },
        // A literal, an enum-ref or any other atom names no field; the
        // caller turns `None` into the loud unverifiable rejection.
        SExpr::Atom(_) => None,
    }
}

/// The maximum `:expr` binding hops `field_ref_for` will follow.
const MAX_BINDING_CHAIN: u8 = 8;

/// Adapt `(fold <op> <query> <body> (:weight <w>)?)` to the Task 10
/// aggregation shape `(op body (:weight w)?)`. See the module doc for the
/// count special case and the compound-body loud rejection.
fn typecheck_one_fold(
    items: &[SExpr],
    types: &TypeEnv,
    bindings: &[BindingDecl],
) -> Result<(), TypeError> {
    // §2.7's `<fold>` carries an optional `<elem-name>` between the query
    // and the body. Matching only the un-named shapes let a `:as` fold fall
    // to the catch-all and skip §3.4 ENTIRELY — appending a never-referenced
    // `:as` name was a silent bypass of the unweighted-mean-of-an-intensive
    // variance error the law exists to reject. Normalize first.
    let items = strip_elem_name(items);
    let (op, body, weight) = match items.as_slice() {
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
    let body_ref = field_ref_for(body, bindings, MAX_BINDING_CHAIN);
    let weight_ref = match weight {
        None => None,
        Some(w) => match field_ref_for(w, bindings, MAX_BINDING_CHAIN) {
            Some(resolved) => Some(resolved),
            None => {
                return Err(compound_fold_error());
            }
        },
    };
    let Some(body_ref) = body_ref else {
        return Err(compound_fold_error());
    };
    let mut adapted: Vec<SExpr> = vec![op.clone(), body_ref];
    if let Some(w) = weight_ref {
        adapted.push(SExpr::Atom(Atom::Keyword("weight".to_owned())));
        adapted.push(w);
    }
    typecheck_aggregation(&SExpr::List(adapted), types).map(|_| ())
}

/// Drop an optional `:as <symbol>` from a form's operand list (§2.6's
/// `<elem-name>?`). Mirrors `bound_checker::strip_elem_name`; kept separate
/// because that one is fallible on a malformed `:as` and this pass leaves
/// shape errors to the bound checker.
fn strip_elem_name(items: &[SExpr]) -> Vec<SExpr> {
    let mut out = Vec::with_capacity(items.len());
    let mut i = 0;
    while i < items.len() {
        if let SExpr::Atom(Atom::Keyword(kw)) = &items[i] {
            if kw == "as" && matches!(items.get(i + 1), Some(SExpr::Atom(Atom::Symbol(_)))) {
                i += 2;
                continue;
            }
        }
        out.push(items[i].clone());
        i += 1;
    }
    out
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

#[cfg(test)]
mod split_content_tests {
    use super::{split_content, LoadError};

    const RULE: &str = "(rule vitality/probe :material-basis \"x\" :fuel 8 (when #t))";
    const INTRINSIC: &str = "(intrinsic floor :params (real) :returns int :cost 5)";

    /// §2.2: "file boundaries and file names carry no semantics" — an
    /// intrinsic declaration BEFORE the rule form must work exactly like
    /// one after it.
    #[test]
    fn an_intrinsic_declaration_before_the_rule_splits_out() {
        let source = format!("{INTRINSIC}\n{RULE}");
        let (intrinsics, rules) = split_content(&source).unwrap();
        assert_eq!(intrinsics.len(), 1);
        assert_eq!(rules.len(), 1);
        assert!(matches!(rules[0].1, crate::reader::SExpr::List(_)));
    }

    #[test]
    fn an_intrinsic_declaration_after_the_rule_splits_out_the_same_way() {
        let source = format!("{RULE}\n{INTRINSIC}");
        let (intrinsics, rules) = split_content(&source).unwrap();
        assert_eq!(intrinsics.len(), 1);
        assert_eq!(rules.len(), 1);
        assert!(matches!(rules[0].1, crate::reader::SExpr::List(_)));
    }

    #[test]
    fn two_intrinsic_declarations_both_split_out() {
        const SECOND: &str = "(intrinsic exp :params (real) :returns real :cost 40)";
        let source = format!("{INTRINSIC}\n{SECOND}\n{RULE}");
        let (intrinsics, _) = split_content(&source).unwrap();
        assert_eq!(intrinsics.len(), 2);
    }

    #[test]
    fn a_source_with_no_rule_form_is_a_loud_content_error() {
        let err = split_content(INTRINSIC).unwrap_err();
        assert!(matches!(err, LoadError::Content(_)));
        assert!(format!("{err}").contains("found 0"));
    }

    #[test]
    fn a_source_with_two_rule_forms_is_a_loud_content_error() {
        let source = format!("{RULE}\n{RULE}");
        let err = split_content(&source).unwrap_err();
        assert!(matches!(err, LoadError::Content(_)));
    }

    #[test]
    fn a_source_with_no_forms_at_all_is_a_loud_content_error() {
        let err = split_content("").unwrap_err();
        assert!(matches!(err, LoadError::Content(_)));
    }

    #[test]
    fn a_read_failure_propagates_as_load_error_read() {
        let err = split_content("(unterminated").unwrap_err();
        assert!(matches!(err, LoadError::Read(_)));
    }

    #[test]
    fn split_content_admits_two_rules_in_source_order() {
        let source = r#"
(rule a/first :material-basis "x" :fuel 10
  (bindings (binding v :field a/v))
  (effects (update-node self a/v (set v))))
(rule b/second :material-basis "y" :fuel 10
  (bindings (binding v :field b/v))
  (effects (update-node self b/v (set v))))
"#;
        let (_intrinsics, rules) = split_content(source).expect("two distinct rule ids load");
        assert_eq!(rules.len(), 2);
        assert_eq!(rules[0].0, "a/first");
        assert_eq!(rules[1].0, "b/second");
    }

    #[test]
    fn split_content_still_admits_exactly_one_rule() {
        // The pre-Task-2 shape stays legal — this widening is additive, never
        // a floor raise. Every existing single-rule content set in the repo
        // must keep loading unchanged.
        let source = r#"(rule a/only :material-basis "x" :fuel 10
  (bindings (binding v :field a/v))
  (effects (update-node self a/v (set v))))"#;
        let (_intrinsics, rules) = split_content(source).expect("one rule still loads");
        assert_eq!(rules.len(), 1);
    }

    #[test]
    fn split_content_refuses_zero_rules() {
        let err = split_content("").unwrap_err();
        assert!(err.to_string().contains("found 0"));
    }

    #[test]
    fn a_duplicate_rule_id_across_the_content_set_is_e_load_001() {
        let source = r#"
(rule a/dup :material-basis "x" :fuel 10
  (bindings (binding v :field a/v))
  (effects (update-node self a/v (set v))))
(rule a/dup :material-basis "y" :fuel 10
  (bindings (binding v :field a/v2))
  (effects (update-node self a/v2 (set v))))
"#;
        let err = split_content(source).unwrap_err();
        assert!(err.to_string().contains("E-LOAD-001"));
        assert!(err.to_string().contains("a/dup"));
    }
}

#[cfg(test)]
mod deferred_shape_verb_tests {
    // #519 fix round, fix 4: the LOAD-time gate for the six graph-shape
    // verbs Task 12's collect-then-apply split does not defer. Before this
    // gate, a rule using one of them loaded clean and only aborted at
    // RUNTIME, the first tick whose guard admitted a subject.
    use super::{load_rule, LoadContext, LoadError};
    use crate::bindings::BindingVocabulary;
    use crate::fuel::{CardinalityCeilings, IntrinsicCosts};
    use crate::typecheck::TypeEnv;
    use std::collections::{HashMap, HashSet};

    fn load_ctx() -> LoadContext<'static> {
        // Leaked so the borrows in `LoadContext<'static>` are trivially
        // valid for the whole test — this module needs no drop discipline
        // and every other test-fixture pattern in this crate (tick.rs's
        // own `Fixture`) already owns its registries for the test's
        // lifetime; leaking keeps this one function self-contained rather
        // than threading four extra `&'a` parameters through every caller.
        LoadContext {
            vocabulary: Box::leak(Box::new(BindingVocabulary {
                fields: HashSet::new(),
                consts: HashSet::new(),
                metrics: HashSet::new(),
            })),
            types: Box::leak(Box::new(TypeEnv {
                fields: HashMap::new(),
                exemptions: &[],
            })),
            ceilings: Box::leak(Box::new(CardinalityCeilings::new(
                HashMap::new(),
                HashMap::new(),
            ))),
            intrinsics: Box::leak(Box::new(IntrinsicCosts::default())),
            systems: Box::leak(Box::new(HashSet::from(["geography".to_owned()]))),
            vocabulary_registry: None,
            rule_file: "x.bsl",
        }
    }

    #[test]
    fn a_rule_using_remove_node_refuses_at_load_naming_the_verb() {
        let ctx = load_ctx();
        let err = load_rule(
            r#"(rule geography/mint :material-basis "x" :fuel 64
  (bindings)
  (effects (remove-node self)))"#,
            &ctx,
        )
        .unwrap_err();
        assert!(
            matches!(err, LoadError::DeferredShapeVerb(_)),
            "expected LoadError::DeferredShapeVerb, got {err:?}"
        );
        assert!(err.to_string().contains("remove-node"), "{err}");
    }

    #[test]
    fn a_rule_naming_remove_node_only_inside_a_guard_still_refuses_at_load() {
        // The walk must recurse through `guard` nesting, not just the
        // top-level effect-item list.
        let ctx = load_ctx();
        let err = load_rule(
            r#"(rule geography/mint :material-basis "x" :fuel 64
  (bindings)
  (effects (guard #t (remove-node self))))"#,
            &ctx,
        )
        .unwrap_err();
        assert!(matches!(err, LoadError::DeferredShapeVerb(_)), "{err}");
        assert!(err.to_string().contains("remove-node"), "{err}");
    }

    #[test]
    fn a_rule_with_no_deferred_shape_verb_is_unaffected_by_the_gate() {
        // The regression guard: a rule that uses only update-node must not
        // be refused by this gate at all — this bare-bones fixture's empty
        // `TypeEnv`/`vocabulary_registry: None` skip every LATER check that
        // would otherwise reject `geography/heat` as an unknown field, so
        // the rule loads clean end to end. Any failure here would mean the
        // gate over-fired on a verb it must never touch.
        let ctx = load_ctx();
        load_rule(
            r#"(rule geography/mint :material-basis "x" :fuel 64
  (bindings)
  (effects (update-node self geography/heat (set 1))))"#,
            &ctx,
        )
        .expect("update-node must never trip the deferred-shape-verb gate");
    }
}
