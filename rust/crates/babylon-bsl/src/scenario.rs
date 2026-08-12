//! The world-load path: a scenario file becomes a populated
//! [`GraphSubstrate`] (P27 Phase 2 Slice 1).
//!
//! Before this module the Rust engine had no way to obtain a world at all —
//! every graph in the tree was built by hand in a test. A rule cannot run
//! against a world that does not exist, so this is the first half of the
//! vertical slice; the tick loop is the second.
//!
//! # Why s-expressions and not a new format
//!
//! The reader, its error codes, and its NFC/escape discipline already exist
//! ([`crate::reader`]). A scenario is content, and the project already has a
//! content language — inventing a second one would mean a second lexer, a
//! second error vocabulary, and a second place for encoding bugs to live.
//!
//! ```text
//! (scenario ft/two-classes
//!   (node core NodeType/SOCIAL_CLASS
//!     (social-class/wages 120)
//!     (social-class/value-produced 80))
//!   (node periphery NodeType/SOCIAL_CLASS
//!     (social-class/wages 20)
//!     (social-class/value-produced 90))
//!   (edge EdgeType/SOLIDARITY core periphery 1))
//! ```
//!
//! **Local names are load-time only.** `core` and `periphery` let an edge
//! name its endpoints; they are resolved to [`NodeId`]s during the load and
//! do not survive it. Nothing downstream can address a node by its scenario
//! name, which keeps the substrate's identity model the only one.
//!
//! **Declaration order is the id order.** Nodes are minted top to bottom, so
//! the same file always produces the same [`NodeId`] assignment and hence the
//! same state hash. Reordering two `node` forms is a real change to the
//! scenario, not a cosmetic one — which is honest, since it changes what
//! `NodeId(0)` denotes.
//!
//! # What this deliberately does not do
//!
//! - **No `Currency` attributes.** `GraphSubstrate` attributes are `f64`,
//!   which cannot hold `Currency`'s i128 micro-units; the verb layer already
//!   refuses such a write loudly rather than casting lossily. Typed
//!   attribute storage (Half 2 of the typed-attribute-seeding design,
//!   `reports/typed-attribute-seeding-design-2026-08-11.md`) is DEFERRED TO
//!   ITS FIRST CONSUMER (Director ruling, 2026-08-11 popup) — not to a fixed
//!   phase boundary — and the Fundamental Theorem will want it once it
//!   lands: wages and value produced are properly money. This module states
//!   the gap rather than hiding it.
//! - **`int`- and fractional-typed attributes only (Half 1).** An
//!   `int`-declared field takes an integer literal, exact in `f64` to 2^53.
//!   A `probability`/`intensity`/`coefficient`-declared field takes any
//!   literal that widens to `[0, 1]` — see `attribute_value` (private, this
//!   module) for the conversion contract and its determinism argument.
//! - **No hyperedges yet.** The grammar has room for them; nothing in slice 1
//!   needs one, and an unused form is an untested form.
//! - **No defaults.** A node with no attributes gets no attributes. An
//!   unwritten field errors on read (III.11), and seeding zeros here would
//!   defeat that at the one place it is easiest to defeat.

use crate::evaluator::Value;
use crate::reader::{read_all, Atom, ReadError, SExpr, ScaledKind};
use crate::types::{BslType, EnumRegistry, EnumTypeId, FieldDecl, FieldKind};
use crate::vocabulary::{ClosedVocabulary, EnumKind};
use babylon_graph::substrate::{GraphError, GraphSubstrate, NodeId};
use babylon_kernel::Ratio;
use std::collections::{HashMap, HashSet};

/// Why a scenario would not load.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ScenarioError {
    /// Human-readable detail, naming the offending form.
    pub message: String,
    /// The spec's error code, where §3.9 names one for a hydration
    /// failure. `None` where it does not — no invented codes.
    pub code: Option<&'static str>,
}

impl std::fmt::Display for ScenarioError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self.code {
            Some(code) => write!(f, "{code}: {}", self.message),
            None => write!(f, "{}", self.message),
        }
    }
}

impl std::error::Error for ScenarioError {}

impl From<ReadError> for ScenarioError {
    fn from(err: ReadError) -> Self {
        Self {
            message: format!(
                "scenario read failed at byte {}: {}",
                err.position, err.message
            ),
            code: None,
        }
    }
}

impl From<GraphError> for ScenarioError {
    fn from(err: GraphError) -> Self {
        Self {
            message: format!("substrate refused the scenario: {}", err.message),
            code: None,
        }
    }
}

fn err(message: impl Into<String>) -> ScenarioError {
    ScenarioError {
        message: message.into(),
        code: None,
    }
}

/// A hydration failure the reference gives a code (§3.9).
fn coded_err(code: &'static str, message: impl Into<String>) -> ScenarioError {
    ScenarioError {
        message: message.into(),
        code: Some(code),
    }
}

/// What a loaded scenario declared, beyond the graph itself.
#[derive(Debug, Clone)]
pub struct LoadedScenario {
    /// The scenario's qualified id, for the run record.
    pub id: String,
    /// How many nodes it minted.
    pub node_count: usize,
    /// How many dyadic edges it minted.
    pub edge_count: usize,
    /// How many nodes of each `NodeType` member the scenario minted.
    ///
    /// The load-time bound checker needs a cardinality ceiling per queried
    /// type; taking it from the population the scenario ACTUALLY built means
    /// the static bound is checked against a real number rather than an
    /// invented one.
    pub node_types: HashMap<String, u64>,
    /// How many dyadic edges of each `EdgeType` member the scenario minted.
    ///
    /// The SAME argument as `node_types`, one axis over: `neighbors_ceiling`
    /// (`bound_checker.rs`) bounds a `(neighbors …)` fold against the
    /// **lesser** of the queried edge type's ceiling and the annotated
    /// result `NodeType`'s — so a rule using `neighbors` needs an
    /// `EdgeType/…` entry in `CardinalityCeilings` too, or `check_rule`
    /// raises `MissingCeiling` for the edge axis specifically. Added by the
    /// query-evaluation plan's Task 15 (P27 Phase 2 PR 5) — the FIRST
    /// consumer of `neighbors` through the scenario-driven `run_once_into`
    /// path (every rule pack landed before it read only `:field`s, never a
    /// query), so this gap was latent, not exercised, until now.
    pub edge_types: HashMap<String, u64>,
    /// The fields the scenario DECLARED, keyed by qname.
    ///
    /// This is the `deffield` registry in miniature: a rule's typechecker
    /// and binding vocabulary both need to know a field's type and
    /// intensivity kind, and until Phase 2's content registries exist the
    /// scenario is the only place that knowledge can honestly come from.
    /// Deriving it from usage instead would mean guessing a kind, and
    /// intensivity is exactly what §3.4 refuses to guess.
    pub fields: HashMap<String, FieldDecl>,
    /// The DEFINES ENVIRONMENT a `:const` binding reads (§2.5, §4.2),
    /// keyed by qualified name.
    ///
    /// The same registry-in-miniature argument as `fields`, one level up: a
    /// coefficient's *value* is content, and until Phase 2's registry reads
    /// `GameDefines`/`defines.yaml` there is nowhere else it can honestly
    /// come from. Writing the number into the rule instead would put a
    /// magnitude in the shape's file, which is the one thing the project's
    /// coefficient discipline forbids — so the scenario declares it and
    /// cites the `defines.yaml` line it was taken from.
    pub consts: HashMap<String, Value>,
    /// **§2.13 addendum (D101, Organization spec §1 Q12).** Every
    /// `defenum` type the scenario declared — the registry `enum`-typed
    /// `deffield`s resolve against, and the read path (`tick.rs::
    /// bind_subject`) renders stored ordinals back through. Empty for a
    /// scenario with no `defenum` forms — unlike `fields`/`consts`, there
    /// is no "the scenario is the only registry" claim here: `EnumRegistry`
    /// is §2.13's own new construct, not a stand-in for a Phase-2 content
    /// registry that predates it.
    pub enums: EnumRegistry,
    /// **§2.13 addendum (D101), §3.6.** The closed graph vocabulary this
    /// scenario declared via `defvocabulary`, or `None` for a scenario
    /// declaring none — opt-in per scenario, so every EXISTING content set
    /// (which declares no `defvocabulary` at all) is unaffected (Task 7's
    /// own backward-compatibility proof). Enforcement against this
    /// registry (Task 8 of the Organization foundation plan) is out of
    /// this train's scope; this field only carries what was declared.
    pub vocabulary: Option<ClosedVocabulary>,
}

/// Read `source` and populate `graph` with it.
///
/// # Errors
///
/// [`ScenarioError`] if the source does not read, the top-level form is not a
/// single `scenario`, a node or edge form is malformed, a local name is
/// duplicated or unknown, or the substrate refuses a write.
pub fn load_scenario(
    source: &str,
    graph: &mut dyn GraphSubstrate,
) -> Result<LoadedScenario, ScenarioError> {
    let forms = read_all(source.as_bytes())?;
    let [SExpr::List(items)] = forms.as_slice() else {
        return Err(err(format!(
            "a scenario file holds exactly one (scenario ...) form; found {}",
            forms.len()
        )));
    };

    let (head, id, body) =
        match items.as_slice() {
            [SExpr::Atom(Atom::Symbol(head)), SExpr::Atom(Atom::QName(id)), body @ ..] => {
                (head.as_str(), id.clone(), body)
            }
            _ => return Err(err(
                "expected (scenario <qname> <form>*) — the id must be a qname, e.g. ft/two-classes",
            )),
        };
    if head != "scenario" {
        return Err(err(format!(
            "expected a (scenario ...) form, found ({head} ...)"
        )));
    }

    // Local name -> minted id. Load-time only; it does not outlive this call.
    let mut named: HashMap<String, NodeId> = HashMap::new();
    let mut fields: HashMap<String, FieldDecl> = HashMap::new();
    let mut consts: HashMap<String, Value> = HashMap::new();
    let mut node_types: HashMap<String, u64> = HashMap::new();
    let mut edge_types: HashMap<String, u64> = HashMap::new();
    let mut node_count = 0_usize;
    let mut edge_count = 0_usize;
    // §2.13 (D101): every `defenum` type this scenario declares, top to
    // bottom — a `deffield ... enum <Type>` resolves against this AS IT IS
    // AT THAT POINT, the same "declaration must precede use" discipline
    // `named`/`fields` already enforce for nodes and node-attribute reads.
    let mut enums: EnumRegistry = EnumRegistry::default();
    // §2.13/§3.6: the closed graph vocabulary this scenario declares, per
    // kind — collected across the load and fed to `ClosedVocabulary::new`
    // ONCE at the end, since that constructor runs the whole-vocabulary
    // rendering-disjointness check (`E-LOAD-032`) over every kind at once.
    // `vocabulary_kinds_declared` is the "one form per kind" guard
    // (`E-LOAD-001`) — `ClosedVocabulary::new` itself MERGES same-kind
    // entries via `.extend` rather than rejecting a second one, so that
    // check has to live here, before the merge ever happens.
    let mut vocabulary_members: HashMap<EnumKind, Vec<String>> = HashMap::new();
    let mut vocabulary_kinds_declared: HashSet<EnumKind> = HashSet::new();
    // §3.9 clause 5 (D73): hydration may not seed two dyadic edges sharing
    // one `(source-id, target-id, edge-type)` triple. This set is what
    // makes the triple a KEY rather than a sort field — without it §2.6's
    // edge iteration order is not a total order and §2.10's `edge-between`
    // has no rule for resolving two.
    let mut seeded_edges: HashSet<(String, NodeId, NodeId)> = HashSet::new();

    for form in body {
        let SExpr::List(parts) = form else {
            return Err(err(
                "a scenario body holds only (deffield ...), (node ...) and (edge ...) forms",
            ));
        };
        match parts.first() {
            Some(SExpr::Atom(Atom::Symbol(tag))) if tag == "defenum" => {
                load_defenum(form, &mut enums)?;
            }
            Some(SExpr::Atom(Atom::Symbol(tag))) if tag == "defvocabulary" => {
                load_defvocabulary(
                    form,
                    &mut vocabulary_members,
                    &mut vocabulary_kinds_declared,
                )?;
            }
            Some(SExpr::Atom(Atom::Symbol(tag))) if tag == "deffield" => {
                load_deffield(parts, &mut fields, &enums)?;
            }
            Some(SExpr::Atom(Atom::Symbol(tag))) if tag == "defconst" => {
                load_defconst(parts, &mut consts)?;
            }
            Some(SExpr::Atom(Atom::Symbol(tag))) if tag == "node" => {
                let minted = load_node(parts, graph, &mut named, &fields, &enums)?;
                *node_types.entry(minted).or_insert(0) += 1;
                node_count += 1;
            }
            Some(SExpr::Atom(Atom::Symbol(tag))) if tag == "edge" => {
                let minted = load_edge(parts, graph, &named, &mut seeded_edges)?;
                *edge_types.entry(minted).or_insert(0) += 1;
                edge_count += 1;
            }
            _ => {
                return Err(err(
                    "a scenario body form must begin with `defenum`, `defvocabulary`, \
                     `deffield`, `defconst`, `node` or `edge`",
                ))
            }
        }
    }

    // Opt-in per scenario (Task 7): no `defvocabulary` forms at all yields
    // `None`, which is what keeps every scenario predating this section
    // loading exactly as it did before it.
    let vocabulary = if vocabulary_members.is_empty() {
        None
    } else {
        Some(
            ClosedVocabulary::new(vocabulary_members).map_err(|e| ScenarioError {
                code: Some(e.spec_code()),
                message: e.to_string(),
            })?,
        )
    };

    Ok(LoadedScenario {
        id,
        node_count,
        edge_count,
        node_types,
        edge_types,
        fields,
        consts,
        enums,
        vocabulary,
    })
}

/// `(defconst <qname> <literal>)`, or `(defconst <qname> <ratio-literal>
/// [:floor <ratio-literal>] [:cap <ratio-literal>])` (§3.2 addendum,
/// Director ruling 2026-08-11, #492/ADR194 — the declared-domain scale
/// operation).
///
/// The defines environment in miniature (§2.5's `:const`, §4.2's
/// "the defines environment (coefficients)"). Slice 1 has no
/// `GameDefines`/`defines.yaml` reader, and §2.5 gives `:const` no other
/// source, so the alternative to declaring the value here is writing it
/// into the rule — putting a magnitude in the file that owns the shape.
///
/// Of the five literal atom classes §2.2 admits at `:default` plus §1.5's
/// addendum, four are legal here — `Int`, `Scaled` (`p`/`i`/`c`/`r`), and
/// `Bool` (defines carry toggles as well as magnitudes); `Currency` is
/// refused exactly as `:default` refuses it (no i128 storage in slice 1).
/// The literal-only rule holds for the same reason `:default`'s does: a
/// define is a value, not an expression, and an expression would need an
/// evaluation environment that does not exist at scenario-load time.
///
/// **`:floor`/`:cap` (#492/ADR194).** `defconst`/`node`/`edge`/`scenario`
/// are the `.bscn`-dialect construct `bsl-language.rst` §7 records as OUT
/// of the consolidated grammar's scope (D93: "no section specifies it") —
/// so both keywords are Rust-implementation machinery, not an RST
/// production, and do NOT go through the closed §1.6 keyword vocabulary or
/// its `E-PARSE-013` enforcement ([`parse_bound_keywords`] is that
/// enforcement, same as this function's own hand-rolled positional match is
/// for `defconst`'s base shape). Both are legal ONLY on a `Ratio`
/// (`r`-suffixed) literal: `Ratio`'s own domain is already `(0, ∞)` (§1.5
/// addendum), and each keyword narrows ONE end of it —
/// `:cap` to `(0, cap]` (INCLUSIVE, matching a `<=`-bounded consumer like
/// `pareto_alpha`'s `(0, 10]`), `:floor` to `(floor, ∞)` (EXCLUSIVE,
/// matching Ratio's own open-at-zero law AND a `>`-bounded consumer like
/// `entropy_factor`'s `(1.0, 3.0]`), together `(floor, cap]`. Stated at
/// declaration, loud and visible in the source text, and each bound checked
/// twice: HERE at load (`E-LOAD-052`, the literal must not itself violate
/// the domain it declares) and again at every `Currency × Ratio` evaluation
/// (`E-EVAL-041`, `evaluator::currency_mul_ratio`) — defense in depth, per
/// III.11. An UNDECLARED (bare) `Ratio` defconst is exactly as legal as
/// before this addendum; the `[0,1]` cap on `p`/`i`/`c` defconsts is
/// completely untouched — this is a new, disjoint literal kind, not a
/// widening of the existing three.
fn load_defconst(
    parts: &[SExpr],
    consts: &mut HashMap<String, Value>,
) -> Result<(), ScenarioError> {
    let [_, SExpr::Atom(Atom::QName(qname)), SExpr::Atom(literal), rest @ ..] = parts else {
        return Err(err(
            "expected (defconst <qname> <literal>) — one qualified name, one literal",
        ));
    };
    let (floor_literal, cap_literal) = parse_bound_keywords(qname, rest)?;
    let value = match literal {
        Atom::Int(value) => {
            reject_stray_bounds(qname, floor_literal, cap_literal, "an Int")?;
            Value::Int(*value)
        }
        Atom::Scaled(scaled) if scaled.kind == ScaledKind::Ratio => {
            load_ratio_defconst(qname, scaled, floor_literal, cap_literal)?
        }
        Atom::Scaled(scaled) => {
            reject_stray_bounds(qname, floor_literal, cap_literal, "a p/i/c literal")?;
            // `unscaled / 10^scale`, the canonical minimal-scale form, and
            // the SAME arithmetic `tick.rs::atom_to_value` performs on a
            // `:default` literal — so a scaled coefficient reads identically
            // whichever door it enters by.
            #[allow(clippy::cast_precision_loss)]
            let numerator = scaled.unscaled as f64;
            Value::Real(numerator / 10_f64.powi(i32::from(scaled.scale)))
        }
        Atom::Bool(value) => {
            reject_stray_bounds(qname, floor_literal, cap_literal, "a Bool")?;
            Value::Bool(*value)
        }
        // Refused, not carried. `tick.rs::atom_to_value` refuses a Currency
        // `:default` and `attribute_value` above refuses a Currency
        // attribute, both because slice 1 has no typed storage for i128
        // micro-units. Accepting one HERE would make the same literal legal
        // through one door and rejected through the others — the entry point
        // deciding the type system, which is the drift the sibling refusals
        // exist to prevent. Currency coefficients arrive with typed
        // attribute storage once it lands — DEFERRED TO ITS FIRST CONSUMER
        // (Director ruling, 2026-08-11 popup), not to a fixed phase
        // boundary — not before.
        Atom::Currency(_) => {
            return Err(err(format!(
                "defconst `{qname}`: a Currency coefficient needs typed \
                 attribute storage — the Director ruled (2026-08-11) that \
                 this lands with Currency's first real consumer — the \
                 `:default` and node-attribute paths refuse one for the same \
                 reason, and admitting it here alone would make the literal's \
                 legality depend on which form it was written in"
            )))
        }
        other => {
            return Err(err(format!(
                "defconst `{qname}`: expected an int, scaled or boolean \
                 literal, found {other:?}"
            )))
        }
    };
    if consts.insert(qname.clone(), value).is_some() {
        return Err(err(format!(
            "duplicate defconst `{qname}` — a coefficient has one value, and \
             silently rebinding it would make the rule reading it depend on \
             declaration order"
        )));
    }
    Ok(())
}

/// Scan the trailing `[:floor <literal>] [:cap <literal>]` keyword-operand
/// pairs after a `defconst`'s required `<qname> <literal>` (in either
/// order, either or both present) — the same hand-rolled enforcement
/// [`load_defconst`]'s doc describes: `.bscn` machinery, not the closed
/// §1.6 vocabulary.
///
/// # Errors
/// A structural (uncoded) [`ScenarioError`] on an unrecognized keyword, a
/// duplicated one, a keyword with no operand, or a non-keyword atom in this
/// position — never a silent drop of the extra tokens.
fn parse_bound_keywords<'a>(
    qname: &str,
    rest: &'a [SExpr],
) -> Result<(Option<&'a Atom>, Option<&'a Atom>), ScenarioError> {
    let mut floor_literal = None;
    let mut cap_literal = None;
    let mut i = 0;
    while i < rest.len() {
        let SExpr::Atom(Atom::Keyword(kw)) = &rest[i] else {
            return Err(err(format!(
                "defconst `{qname}`: expected :floor or :cap here, found {:?}",
                rest[i]
            )));
        };
        let Some(SExpr::Atom(operand)) = rest.get(i + 1) else {
            return Err(err(format!(
                "defconst `{qname}`: :{kw} takes an operand but ends the form"
            )));
        };
        let slot = match kw.as_str() {
            "floor" => &mut floor_literal,
            "cap" => &mut cap_literal,
            other => {
                return Err(err(format!(
                    "defconst `{qname}`: unrecognized keyword :{other} — only \
                     :floor and :cap are legal here (§3.2 addendum, #492/ADR194)"
                )))
            }
        };
        if slot.replace(operand).is_some() {
            return Err(err(format!(
                "defconst `{qname}`: :{kw} given twice — a bound has one \
                 value, and silently rebinding it would make the check \
                 depend on declaration order"
            )));
        }
        i += 2;
    }
    Ok((floor_literal, cap_literal))
}

/// `:floor`/`:cap` are legal only on a `Ratio` literal (see
/// [`load_defconst`]'s doc); this names the refusal by the OTHER literal
/// kind found instead, rather than routing through the generic "expected an
/// int, scaled or boolean literal" arm, which would misdiagnose a
/// well-formed-but-misplaced bound as a malformed literal.
fn reject_stray_bounds(
    qname: &str,
    floor_literal: Option<&Atom>,
    cap_literal: Option<&Atom>,
    found: &str,
) -> Result<(), ScenarioError> {
    if floor_literal.is_some() || cap_literal.is_some() {
        return Err(err(format!(
            "defconst `{qname}`: :floor/:cap are legal only on a Ratio \
             (r-suffixed) literal (§3.2 addendum, #492/ADR194), found {found}"
        )));
    }
    Ok(())
}

/// The `Ratio`-literal half of [`load_defconst`]: builds
/// `Value::Ratio { value, floor, cap }`, checking the declared bounds at
/// load (`E-LOAD-052`) — the bounds against EACH OTHER first (when both are
/// present), then the value against each declared bound.
///
/// **Order matters, and is checked by
/// `a_floor_not_strictly_below_its_cap_is_e_load_052`.** `(floor, cap]` is
/// only a non-empty domain when `floor < cap`; when it is NOT, `floor >=
/// cap` implies `value > floor` and `value <= cap` can never BOTH hold (if
/// they could, `floor < value <= cap` would prove `floor < cap`, the
/// contrapositive of what triggered this branch) — so checking the value
/// against either bound FIRST would always fire on ONE of them, misreporting
/// a self-inconsistent DECLARATION as a bad VALUE. Checking the bounds
/// against each other first names the actual defect.
fn load_ratio_defconst(
    qname: &str,
    scaled: &crate::reader::ScaledLit,
    floor_literal: Option<&Atom>,
    cap_literal: Option<&Atom>,
) -> Result<Value, ScenarioError> {
    let value = ratio_from_scaled(qname, scaled)?;
    let floor = parse_ratio_bound(qname, "floor", floor_literal)?;
    let cap = parse_ratio_bound(qname, "cap", cap_literal)?;
    if let (Some(floor), Some(cap)) = (floor, cap) {
        if floor.get() >= cap.get() {
            return Err(coded_err(
                "E-LOAD-052",
                format!(
                    "defconst `{qname}`: declared :floor {} is not strictly \
                     below its own :cap {} — (floor, cap] is empty unless \
                     floor < cap (§3.2 addendum, #492/ADR194)",
                    floor.get(),
                    cap.get()
                ),
            ));
        }
    }
    if let Some(floor) = floor {
        // EXCLUSIVE: value must be STRICTLY greater than its declared floor
        // (matches Ratio's own open-at-zero law and entropy_factor's own
        // `> 1.0`). `floor > 0` needs no separate check here: `floor` is
        // itself a `Ratio`, whose constructor already refused a
        // non-positive value (and the reader's `E-LEX-027` refused it
        // earlier still) — re-checking it would be provably redundant, the
        // same class of already-guaranteed check D-4 of
        // `content/rules/lifecycle.bsl` records rather than re-asserting.
        if value.get() <= floor.get() {
            return Err(coded_err(
                "E-LOAD-052",
                format!(
                    "defconst `{qname}`: declared value {} does not exceed its \
                     own :floor {} — a defconst's :floor states the const's OWN \
                     domain floor EXCLUSIVE, so the literal must be strictly \
                     greater than it (§3.2 addendum, #492/ADR194)",
                    value.get(),
                    floor.get()
                ),
            ));
        }
    }
    if let Some(cap) = cap {
        if value.get() > cap.get() {
            return Err(coded_err(
                "E-LOAD-052",
                format!(
                    "defconst `{qname}`: declared value {} exceeds its own \
                     :cap {} — a defconst's :cap states the const's OWN \
                     domain ceiling INCLUSIVE, so the literal must satisfy it \
                     (§3.2 addendum, #492/ADR194)",
                    value.get(),
                    cap.get()
                ),
            ));
        }
    }
    Ok(Value::Ratio { value, floor, cap })
}

/// One `:floor`/`:cap` operand, as a [`Ratio`] — `None` when the keyword was
/// absent, else the parsed bound or a structural refusal if its literal is
/// not itself a `Ratio`.
fn parse_ratio_bound(
    qname: &str,
    keyword: &str,
    literal: Option<&Atom>,
) -> Result<Option<Ratio>, ScenarioError> {
    match literal {
        None => Ok(None),
        Some(Atom::Scaled(scaled)) if scaled.kind == ScaledKind::Ratio => {
            ratio_from_scaled(qname, scaled).map(Some)
        }
        Some(other) => Err(err(format!(
            "defconst `{qname}`: :{keyword}'s operand must be a Ratio \
             (r-suffixed) literal, found {other:?}"
        ))),
    }
}

/// Convert a canonicalized `r`-literal to a kernel [`Ratio`]. Should never
/// fail — the reader's `E-LEX-027` already refused a non-positive value at
/// lex time — but a defensive, named error (rather than an `expect`) keeps
/// a reader/kernel sort disagreement a loud `ScenarioError`, not a panic.
fn ratio_from_scaled(
    qname: &str,
    scaled: &crate::reader::ScaledLit,
) -> Result<Ratio, ScenarioError> {
    #[allow(clippy::cast_precision_loss)]
    let raw = scaled.unscaled as f64 / 10_f64.powi(i32::from(scaled.scale));
    Ratio::new(raw).map_err(|e| {
        err(format!(
            "defconst `{qname}`: r literal {raw} failed Ratio construction \
             ({e:?}) — the reader's E-LEX-027 should have refused this at lex \
             time; reaching here is a reader/kernel sort disagreement, not a \
             content error"
        ))
    })
}

/// `(defenum <EnumTypeName> (<member>+))` — §2.13, D101. Delegates to
/// `declarations::parse_defenum`, the SAME parser `.bsl` rule content uses
/// (D93's own dialect split is about `defconst`/`node`/`edge`/`scenario`,
/// which the RST grammar disclaims; `defenum` is an RST `<top-form>`, so
/// there is exactly one grammar for it and no reason for a second reader).
///
/// # Errors
///
/// A [`ScenarioError`] wrapping the underlying [`crate::declarations::DeclError`]
/// — `E-LOAD-001` for a duplicate type/member, uncoded for an empty member
/// list or a malformed shape.
fn load_defenum(form: &SExpr, enums: &mut EnumRegistry) -> Result<(), ScenarioError> {
    crate::declarations::parse_defenum(form, enums)
        .map(|_| ())
        .map_err(|e| ScenarioError {
            code: e.spec_code(),
            message: e.to_string(),
        })
}

/// `(defvocabulary <EnumKind> (<member>+))` — §2.13, D101; §3.6's own
/// closed graph vocabulary, populated **explicitly**, never inferred from
/// what a scenario happens to seed. `<EnumKind>` is syntactically an
/// `<enum-type>` (a bare, slash-free `Atom::EnumTypeName` — see that
/// variant's doc for why the reader lexes it that way) but SEMANTICALLY
/// restricted to `NodeType` / `EdgeType` / `HyperedgeType` / `EventType` —
/// an unknown name is `E-LOAD-030`, the same code §3.6 already uses for an
/// unregistered `<enum-ref>` type name (this is a load-time check, not a
/// lexical one, exactly as `enum-type`'s own `defenum` doc reasons for its
/// sibling). Members are written as full `<EnumKind>/<MEMBER>` enum-refs
/// repeating the declaring kind — the SAME convention `load_defenum` uses,
/// for the SAME reason (no bare-member atom class exists; see that
/// function's doc).
///
/// Only inserts into `collected`/`declared` — `ClosedVocabulary::new` (the
/// caller, once at end-of-load) runs the whole-vocabulary
/// rendering-disjointness check over every kind together.
///
/// # Errors
///
/// `E-LOAD-030` for an unregistered `<enum-kind>`; `E-LOAD-001` for a
/// second `defvocabulary` naming a kind already declared; an uncoded
/// [`ScenarioError`] off the grammar, including a member whose kind prefix
/// does not match the kind being declared.
fn load_defvocabulary(
    form: &SExpr,
    collected: &mut HashMap<EnumKind, Vec<String>>,
    declared: &mut HashSet<EnumKind>,
) -> Result<(), ScenarioError> {
    let SExpr::List(items) = form else {
        return Err(err("a defvocabulary must be a form"));
    };
    let [SExpr::Atom(Atom::Symbol(head)), SExpr::Atom(Atom::EnumTypeName(kind_name)), SExpr::List(member_items)] =
        items.as_slice()
    else {
        return Err(err("expected (defvocabulary <EnumKind> (<member>+))"));
    };
    if head != "defvocabulary" {
        return Err(err(format!("expected (defvocabulary …), found ({head} …)")));
    }
    let Some(kind) = EnumKind::from_type_name(kind_name) else {
        return Err(coded_err(
            "E-LOAD-030",
            format!(
                "defvocabulary: `{kind_name}` is not one of NodeType / \
                 EdgeType / HyperedgeType / EventType (§3.6)"
            ),
        ));
    };
    if !declared.insert(kind) {
        return Err(coded_err(
            "E-LOAD-001",
            format!(
                "duplicate defvocabulary for {kind_name} — a kind's \
                 vocabulary is declared once (§2.13)"
            ),
        ));
    }
    let mut members = Vec::with_capacity(member_items.len());
    for item in member_items {
        let SExpr::Atom(Atom::EnumRef { enum_type, member }) = item else {
            return Err(err(format!(
                "defvocabulary {kind_name}: member {item:?} must be written \
                 {kind_name}/<MEMBER>, repeating the declaring kind (§2.13)"
            )));
        };
        if enum_type != kind_name {
            return Err(err(format!(
                "defvocabulary {kind_name}: member {enum_type}/{member} \
                 names a different kind than the one being declared \
                 ({kind_name})"
            )));
        }
        members.push(member.clone());
    }
    collected.entry(kind).or_default().extend(members);
    Ok(())
}

/// `(deffield <qname> <type-symbol> <kind-symbol>)`, or — since §2.13
/// (D101, Organization spec §1 Q12) — `(deffield <qname> enum
/// <EnumTypeName>)`: the 4th slot holds the enum type name instead of a
/// kind symbol, because an enum-typed field carries no aggregation kind
/// at all (there is no `intensive`/`extensive` reading of a member
/// identity) — this dialect has no separate `:enum-type` keyword the way
/// the `.bsl` `deffield` production does; the type-symbol slot itself
/// being `enum` is what selects the 4th slot's alternate meaning.
///
/// The `deffield` registry in miniature. A field's TYPE and INTENSIVITY KIND
/// cannot be inferred from a stored value — `120` is an `Int` whether it is a
/// head-count that sums or a rate that does not — and §3.4 exists precisely
/// to stop that being guessed. So the scenario declares them.
fn load_deffield(
    parts: &[SExpr],
    fields: &mut HashMap<String, FieldDecl>,
    enums: &EnumRegistry,
) -> Result<(), ScenarioError> {
    let [_, SExpr::Atom(Atom::QName(qname)), SExpr::Atom(Atom::Symbol(ty)), fourth] = parts else {
        return Err(err(
            "expected (deffield <field-qname> <type> <intensive|extensive>) or \
             (deffield <field-qname> enum <EnumTypeName>)",
        ));
    };
    let decl = if ty == "enum" {
        let SExpr::Atom(Atom::EnumTypeName(type_name)) = fourth else {
            return Err(err(format!(
                "deffield `{qname}`: an enum-typed field's 4th slot is the \
                 declared enum type name — (deffield {qname} enum \
                 <EnumTypeName>), found {fourth:?}"
            )));
        };
        let Some(id) = enums.resolve(type_name) else {
            return Err(coded_err(
                "E-LOAD-054",
                format!(
                    "deffield `{qname}`: enum type `{type_name}` was never \
                     declared — add a (defenum {type_name} (…)) form ABOVE \
                     this deffield"
                ),
            ));
        };
        FieldDecl {
            ty: BslType::Enum(id),
            kind: FieldKind::NotApplicable,
        }
    } else {
        let SExpr::Atom(Atom::Symbol(kind)) = fourth else {
            return Err(err(format!(
                "deffield `{qname}`: expected an intensive|extensive kind \
                 symbol, found {fourth:?}"
            )));
        };
        let ty = match ty.as_str() {
            "int" => BslType::Int,
            "probability" => BslType::Probability,
            "intensity" => BslType::Intensity,
            "coefficient" => BslType::Coefficient,
            "currency" => BslType::Currency,
            other => {
                return Err(err(format!(
                    "deffield `{qname}`: unknown type `{other}` — one of \
                     int / probability / intensity / coefficient / currency / enum"
                )))
            }
        };
        let kind = match kind.as_str() {
            "intensive" => FieldKind::Intensive,
            "extensive" => FieldKind::Extensive,
            other => {
                return Err(err(format!(
                    "deffield `{qname}`: unknown kind `{other}` — intensive or extensive. \
                     An intensive field averaged without an extensive weight is the \
                     variance error §3.4 exists to catch, so this is not optional"
                )))
            }
        };
        FieldDecl { ty, kind }
    };
    if fields.insert(qname.clone(), decl).is_some() {
        return Err(err(format!(
            "duplicate deffield `{qname}` — a field has one declared type and kind"
        )));
    }
    Ok(())
}

/// `(node <local-name> <enum-ref> (<qname> <int>)*)`
fn load_node(
    parts: &[SExpr],
    graph: &mut dyn GraphSubstrate,
    named: &mut HashMap<String, NodeId>,
    declared: &HashMap<String, FieldDecl>,
    enums: &EnumRegistry,
) -> Result<String, ScenarioError> {
    let [_, SExpr::Atom(Atom::Symbol(local)), SExpr::Atom(Atom::EnumRef { member, .. }), attrs @ ..] =
        parts
    else {
        return Err(err(
            "expected (node <local-name> <NodeType/MEMBER> (<field-qname> <int>)*)",
        ));
    };
    if named.contains_key(local) {
        return Err(err(format!(
            "duplicate scenario name `{local}` — a local name denotes exactly one node, \
             and silently rebinding it would make later edges ambiguous"
        )));
    }

    // The node type string is the enum MEMBER verbatim, matching what
    // `(add-node NodeType/SOCIAL_CLASS ...)` stamps in the verb layer. Any
    // other convention here would produce nodes production queries cannot see.
    let id = graph.add_node(member)?;
    named.insert(local.clone(), id);

    for attr in attrs {
        let SExpr::List(pair) = attr else {
            return Err(err(format!(
                "node `{local}`: an attribute is a (<field-qname> <int>) form"
            )));
        };
        let [SExpr::Atom(Atom::QName(field)), SExpr::Atom(value)] = pair.as_slice() else {
            return Err(err(format!(
                "node `{local}`: an attribute is a (<field-qname> <int>) form"
            )));
        };
        // The registry contract, ENFORCED rather than merely documented: an
        // undeclared qname is a typo, and accepting it would silently mint a
        // field no typechecker knows about — the rule that meant to read it
        // would then fail far from the mistake. Declaration must precede
        // use, so a scenario reads top to bottom exactly as its edges do.
        let Some(decl) = declared.get(field) else {
            return Err(err(format!(
                "node `{local}`: field `{field}` was never declared — add a \
                 (deffield {field} <type> <intensive|extensive>) form ABOVE this node"
            )));
        };
        graph.update_node(
            id,
            field,
            attribute_value(value, local, field, decl, enums)?,
        )?;
    }
    Ok(member.clone())
}

/// Attribute values: `int` literals into `int`-declared fields (unchanged
/// since slice 1), and — Half 1 of the typed-attribute-seeding design
/// (`reports/typed-attribute-seeding-design-2026-08-11.md`) — a fractional
/// literal into a `probability`/`intensity`/`coefficient`-declared field.
///
/// The declaration is checked, not just consulted. A `120` written into a
/// field declared `intensity` is out of that type's `[0, 1]` domain, and one
/// written into a `currency` field would silently become an f64 where i128
/// micro-units were promised — both are the store lying about what it holds.
///
/// **Half 1 needs no new typed storage.** `GraphSubstrate` attributes are
/// already `f64` in and out (`rust/crates/babylon-graph/src/substrate.rs`);
/// nothing about the trait restricts values to integers, and
/// `CanonicalState`'s section `0x02`
/// (`rust/crates/babylon-graph/src/state_hash.rs`) is a bare `f64`
/// regardless of which `BslType` declared the field — a `0.358` seeded into a
/// `coefficient`-declared field and one seeded into an (illegally)
/// `int`-declared field hash byte-identically. The restriction lived
/// entirely in this function; widening it changes zero bytes for any
/// existing scenario, since every one seeds only `int` fields today.
fn attribute_value(
    atom: &Atom,
    local: &str,
    field: &str,
    decl: &FieldDecl,
    enums: &EnumRegistry,
) -> Result<f64, ScenarioError> {
    match &decl.ty {
        BslType::Int => attribute_value_int(atom, local, field),
        BslType::Probability | BslType::Intensity | BslType::Coefficient => {
            attribute_value_unit_interval(atom, local, field, &decl.ty)
        }
        BslType::Currency => Err(err(currency_refusal_message(local, field))),
        BslType::Enum(ty) => attribute_value_enum(atom, local, field, *ty, enums),
        // Defense in depth, not a reachable content error: `load_deffield`
        // is the SOLE populator of the `declared` map `attribute_value` is
        // called against, and its own match on the type symbol admits only
        // int/probability/intensity/coefficient/currency/enum (anything else
        // is refused AT DECLARATION, before a `node` form naming the field
        // can even be read). Reaching here is a wiring bug in the deffield
        // parser, not a content error — kept anyway because `BslType` is
        // not a closed match the compiler can prove exhaustive against this
        // function's actual call graph, and a silent `unreachable!()` would
        // panic rather than name the field that triggered it.
        other => Err(err(format!(
            "node `{local}`: field `{field}` is declared {other:?}, and the scenario \
             loader stores only `int`, `probability`, `intensity`, `coefficient` or \
             `enum`-declared node attributes (currency is refused separately, deferred \
             to typed storage's first consumer) — {other:?} has no representation as a \
             GraphSubstrate f64 attribute at all"
        ))),
    }
}

/// `enum`-declared fields (§2.13, D101 — the Q12 enum row's own lane in the
/// Half-1 typed-attribute-seeding design). Accepts **only** a matching
/// `<enum-ref>` atom, resolves its member through `enums`, and stores
/// `ordinal as f64` — the SAME binary64 attribute lane every other declared
/// type here already uses (zero bytes of any existing golden move: no
/// existing scenario declares an enum field). The ordinal is never a
/// surface value: a bare number, an `<enum-ref>` of a different declared
/// type, or any other atom is `E-LOAD-056`; an `<enum-ref>` of the RIGHT
/// type naming a member that type does not declare is `E-LOAD-055` — there
/// is no "seed it as a number and let the engine resolve the member" path
/// and no default member (§3.6's own "a name outside the registry is a
/// load error, never a fallback" law, restated here for the content-declared
/// registry).
fn attribute_value_enum(
    atom: &Atom,
    local: &str,
    field: &str,
    ty: EnumTypeId,
    enums: &EnumRegistry,
) -> Result<f64, ScenarioError> {
    let Atom::EnumRef { enum_type, member } = atom else {
        return Err(coded_err(
            "E-LOAD-056",
            format!(
                "node `{local}` field `{field}`: an enum-typed field is seeded \
                 ONLY as <EnumType>/<MEMBER> — the ordinal is never a surface \
                 value; found {atom:?}"
            ),
        ));
    };
    let declared_type = enums.name(ty);
    if enum_type != declared_type {
        return Err(coded_err(
            "E-LOAD-056",
            format!(
                "node `{local}` field `{field}`: declared enum type is \
                 {declared_type}, found {enum_type}/{member} — an <enum-ref> \
                 of a different declared type is exactly as illegal as a bare \
                 number here"
            ),
        ));
    }
    let Some(ordinal) = enums.ordinal(ty, member) else {
        return Err(coded_err(
            "E-LOAD-055",
            format!(
                "node `{local}` field `{field}`: {declared_type} has no \
                 member {member} — never a default"
            ),
        ));
    };
    Ok(f64::from(ordinal))
}

/// `int`-declared fields — unchanged behavior, Half 1 does not touch this arm.
fn attribute_value_int(atom: &Atom, local: &str, field: &str) -> Result<f64, ScenarioError> {
    match atom {
        Atom::Int(value) => {
            // Exact in f64 to 2^53; past that the stored value would differ
            // from the declared one, which is a lie the state hash would
            // faithfully record.
            if value.unsigned_abs() > (1_u64 << 53) {
                return Err(err(format!(
                    "node `{local}` field `{field}`: {value} exceeds f64's exact integer range"
                )));
            }
            #[allow(clippy::cast_precision_loss)]
            Ok(*value as f64)
        }
        Atom::Currency(_) => Err(err(currency_refusal_message(local, field))),
        other => Err(err(format!(
            "node `{local}` field `{field}`: expected an integer literal, found {other:?}"
        ))),
    }
}

/// `probability`/`intensity`/`coefficient`-declared fields (Half 1).
///
/// Mirrors `structural_verbs.rs::store_range_check`'s runtime predicate
/// VERBATIM, one call frame earlier — not a new invented rule, the same
/// `[0,1]` rule the runtime write boundary already lives by:
/// `matches!(decl.ty, Probability | Intensity | Coefficient)` then
/// `(0.0..=1.0).contains(&value)`. That runtime check is itself kind-blind
/// among the three unit-interval types — `Value::Real` carries no `p`/`i`/`c`
/// tag once evaluated, so a rule computing a value for a `coefficient` field
/// is checked by the exact same predicate as one for a `probability` field —
/// so this load-time mirror is equally kind-blind: an `Int` literal or any
/// `p`/`i`/`c`-suffixed literal is accepted for ANY of the three declared
/// types, provided its magnitude is in range. `Ratio` (`r`-suffixed) is
/// EXCLUDED even though its value may numerically fall in `[0,1]` for a
/// given literal — `Ratio` is a genuinely distinct runtime `Value` variant
/// with its own `(0, ∞)` domain and its own restricted operator
/// (`Currency × Ratio` only, §3.2 addendum); a field read can never legally
/// produce one (`bind_subject` wraps every `:field` read `Value::Real`,
/// never `Value::Ratio`), so admitting one here would store a value under a
/// type the read path cannot represent.
///
/// # The conversion contract, and why it is NOT `babylon_kernel::grid::quantize`
///
/// A scaled (`p`/`i`/`c`) literal converts as `unscaled / 10^scale` — one
/// IEEE-754 division of two exactly-representable operands (`unscaled` as an
/// integer, `10^scale` exact in `f64` for `scale <= 9`, the literal's own
/// bound) — the SAME arithmetic `tick.rs::atom_to_value` and
/// `scenario.rs::load_defconst` already perform for a `:default`/`:const`
/// literal of the same value. This is deliberate, not an oversight: `grid.rs`'s
/// `(value * 1e6 + 0.5).floor() / 1e6` half-up quantization is a
/// `babylon_kernel` **scalar newtype** invariant
/// (`Probability::new`/`Intensity::new`/`Coefficient::new` call it on
/// construction) that nothing in `babylon-bsl` reaches today — the
/// evaluator's binary64 lane is raw `f64` (`Value::Real`) end to end, and a
/// value entering storage via `(update-node self field (+ x y))` during a
/// tick is not grid-quantized either. Snapping only the seed path to the
/// grid would create exactly the asymmetry it would be trying to prevent: a
/// rule-computed write and a scenario-seeded value of the identical field
/// would then follow two different rounding rules for the same declared
/// type. A single correctly-rounded IEEE-754 division is a "basic IEEE-754
/// op" — it reproduces bit-identically across conforming implementations,
/// the same guarantee class CLAUDE.md's Tests-as-Behavioral-Contracts
/// principle 4 names as safe ("basic IEEE-754 ops reproduce across
/// languages") — so no new rule is minted; the existing rule is extended
/// verbatim to the node-attribute seed path.
fn attribute_value_unit_interval(
    atom: &Atom,
    local: &str,
    field: &str,
    ty: &BslType,
) -> Result<f64, ScenarioError> {
    let value = match atom {
        Atom::Int(value) => {
            // Bare Int literals carry NO domain check at lex time
            // (`E-LEX-024` bounds only `p`/`i`/`c`-suffixed literals) — the
            // `[0,1]` check below is this arm's ONLY domain enforcement, and
            // it is load-bearing: an out-of-range bare Int (e.g. `6`) must
            // still be refused here.
            #[allow(clippy::cast_precision_loss)]
            let widened = *value as f64;
            widened
        }
        Atom::Scaled(scaled) if scaled.kind == ScaledKind::Ratio => {
            #[allow(clippy::cast_precision_loss)]
            let numerator = scaled.unscaled as f64;
            let value = numerator / 10_f64.powi(i32::from(scaled.scale));
            return Err(err(format!(
                "node `{local}` field `{field}`: {value}r is a Ratio (r-suffixed) literal, \
                 not a legal {ty:?} attribute value — Ratio is its own runtime type with \
                 domain (0, ∞), and a :field read can never legally produce one"
            )));
        }
        Atom::Scaled(scaled) => {
            // See this function's doc comment for the conversion contract
            // and why it is not `grid::quantize`.
            #[allow(clippy::cast_precision_loss)]
            let numerator = scaled.unscaled as f64;
            numerator / 10_f64.powi(i32::from(scaled.scale))
        }
        Atom::Currency(_) => return Err(err(currency_refusal_message(local, field))),
        other => {
            return Err(err(format!(
                "node `{local}` field `{field}`: expected an int or scaled (p/i/c) \
                 literal, found {other:?}"
            )))
        }
    };
    if !(0.0..=1.0).contains(&value) {
        return Err(err(format!(
            "node `{local}` field `{field}`: storing {value} leaves its declared \
             {ty:?} [0,1] domain — a loud failure, never a clamp (mirrors \
             structural_verbs.rs::store_range_check's runtime rule, checked one \
             call frame earlier)"
        )));
    }
    Ok(value)
}

/// Currency's refusal, worded identically at every site it fires — the
/// Half-2 typed-storage gap this train (Half 1) explicitly does not close.
///
/// Wording note (typed-attribute-seeding train, 2026-08-11): earlier
/// revisions of this message cited "a declared Phase-2 trait revision"
/// pending on the Phase-1 exit checklist's own DEFERRED row. The Director's
/// 2026-08-11 popup ruling supersedes that framing: Half 2 (Currency i128
/// typed storage) is DEFERRED TO ITS FIRST CONSUMER — whichever port first
/// needs a real Currency field — not to a fixed phase boundary, so the
/// message cites the ruling directly rather than a phase number.
fn currency_refusal_message(local: &str, field: &str) -> String {
    format!(
        "node `{local}` field `{field}`: Currency attributes need typed attribute \
         storage — the Director ruled (2026-08-11) that this lands with Currency's \
         first real consumer, not this train — f64 cannot hold i128 micro-units, and \
         this refuses rather than casting lossily"
    )
}

/// `(edge <enum-ref> <local-name> <local-name> <int>)` — returns the minted
/// `EdgeType` member (verbatim, matching `load_node`'s own return
/// convention) so the caller can build the `edge_types` census.
fn load_edge(
    parts: &[SExpr],
    graph: &mut dyn GraphSubstrate,
    named: &HashMap<String, NodeId>,
    seeded: &mut HashSet<(String, NodeId, NodeId)>,
) -> Result<String, ScenarioError> {
    let [_, SExpr::Atom(Atom::EnumRef { member, .. }), SExpr::Atom(Atom::Symbol(from)), SExpr::Atom(Atom::Symbol(to)), SExpr::Atom(strength)] =
        parts
    else {
        return Err(err(
            "expected (edge <EdgeType/MEMBER> <from-name> <to-name> <int>)",
        ));
    };
    let resolve = |name: &String| -> Result<NodeId, ScenarioError> {
        named.get(name).copied().ok_or_else(|| {
            err(format!(
                "edge names unknown node `{name}` — a node must be declared before an \
                 edge referring to it, so a scenario reads top to bottom"
            ))
        })
    };
    // An edge strength is not a node field, so no deffield governs it; the
    // int-literal restriction is stated directly here.
    let strength = match strength {
        Atom::Int(value) => {
            #[allow(clippy::cast_precision_loss)]
            let widened = *value as f64;
            widened
        }
        other => {
            return Err(err(format!(
                "edge {member}: expected an integer strength literal, found {other:?}"
            )))
        }
    };
    let (from_id, to_id) = (resolve(from)?, resolve(to)?);
    // §3.9 clause 5 / D73 — reported as E-LOAD-044 HERE rather than left to
    // the substrate's generic refusal, because the two failures are
    // different facts: `E-EVAL-031` is a verb adding an edge that already
    // exists, and `E-LOAD-044` is a scenario seeding one key twice.
    if !seeded.insert((member.clone(), from_id, to_id)) {
        return Err(coded_err(
            "E-LOAD-044",
            format!(
                "hydration seeds two {member} edges between one ordered pair \
                 ({from} → {to}); the (source, target, type) triple is a KEY, \
                 which is what makes §2.6's edge order total and \
                 `edge-between` well defined"
            ),
        ));
    }
    graph.add_edge(member, from_id, to_id, strength)?;
    Ok(member.clone())
}

#[cfg(test)]
mod tests {
    use super::{load_scenario, BslType, EnumKind, EnumRegistry, FieldDecl, FieldKind};
    use crate::bindings::BindingVocabulary;
    use crate::fuel::{CardinalityCeilings, IntrinsicCosts};
    use crate::intrinsic_host::EmptyIntrinsicHost;
    use crate::rule_pipeline::{load_rule, LoadContext};
    use crate::structural_verbs::CollectingSink;
    use crate::tick::{run_tick, DefinesEnv};
    use crate::typecheck::TypeEnv;
    use babylon_graph::memory::MemoryGraph;
    use babylon_graph::state_hash::{CanonicalState, StateEncoder};
    use babylon_graph::substrate::{Direction, GraphSubstrate, NodeId};
    use std::collections::{HashMap, HashSet};

    const TWO_CLASSES: &str = r"
(scenario ft/two-classes
  (deffield social-class/wages int extensive)
  (deffield social-class/value-produced int extensive)
  (node core NodeType/SOCIAL_CLASS
    (social-class/wages 120)
    (social-class/value-produced 80))
  (node periphery NodeType/SOCIAL_CLASS
    (social-class/wages 20)
    (social-class/value-produced 90))
  (edge EdgeType/SOLIDARITY core periphery 1))
";

    #[test]
    fn a_scenario_becomes_a_populated_graph() {
        let mut graph = MemoryGraph::new();
        let loaded = load_scenario(TWO_CLASSES, &mut graph).unwrap();
        assert_eq!(loaded.id, "ft/two-classes");
        assert_eq!(loaded.node_count, 2);
        assert_eq!(loaded.edge_count, 1);

        let classes = graph.nodes("SOCIAL_CLASS");
        assert_eq!(classes.len(), 2, "both classes exist and are queryable");
        assert!(
            (graph
                .node_attribute(classes[0], "social-class/wages")
                .unwrap()
                - 120.0)
                .abs()
                < 1e-12
        );
        assert_eq!(
            graph
                .neighbors(classes[0], "SOLIDARITY", Direction::Out)
                .unwrap(),
            vec![classes[1]],
            "the edge resolved both endpoints by local name"
        );
    }

    #[test]
    fn the_same_file_always_produces_the_same_state() {
        // Declaration order fixes id assignment, so a scenario is replayable.
        let mut first = MemoryGraph::new();
        let mut second = MemoryGraph::new();
        load_scenario(TWO_CLASSES, &mut first).unwrap();
        load_scenario(TWO_CLASSES, &mut second).unwrap();
        assert_eq!(first.state_hash().unwrap(), second.state_hash().unwrap());
    }

    #[test]
    fn an_unwritten_field_still_errors_after_a_load() {
        // The loader seeds no defaults, so III.11's honest null survives it.
        let mut graph = MemoryGraph::new();
        load_scenario(TWO_CLASSES, &mut graph).unwrap();
        let err = graph
            .node_attribute(NodeId(0), "social-class/agitation")
            .unwrap_err();
        assert!(err.message.contains("never a default"), "{}", err.message);
    }

    #[test]
    fn a_duplicate_local_name_is_loud() {
        let source = r"
(scenario ft/dup
  (node core NodeType/SOCIAL_CLASS)
  (node core NodeType/SOCIAL_CLASS))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert!(
            err.message.contains("duplicate scenario name"),
            "{}",
            err.message
        );
    }

    #[test]
    fn an_edge_to_an_undeclared_name_is_loud() {
        let source = r"
(scenario ft/dangling
  (node core NodeType/SOCIAL_CLASS)
  (edge EdgeType/SOLIDARITY core ghost 1))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert!(
            err.message.contains("unknown node `ghost`"),
            "{}",
            err.message
        );
    }

    #[test]
    fn a_currency_attribute_is_refused_not_cast() {
        // The known Phase-2 gap, stated at the boundary instead of silently
        // truncating i128 micro-units into an f64.
        let source = r"
(scenario ft/money
  (deffield social-class/wages currency extensive)
  (node core NodeType/SOCIAL_CLASS (social-class/wages 120$)))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert!(
            err.message.contains("typed attribute storage"),
            "{}",
            err.message
        );
    }

    #[test]
    fn an_undeclared_field_is_a_typo_not_a_new_field() {
        // The registry contract enforced. Accepting an undeclared qname
        // would mint a field no typechecker knows about, and the rule that
        // meant to read it would fail far from the mistake.
        let source = r"
(scenario ft/typo
  (deffield social-class/wages int extensive)
  (node core NodeType/SOCIAL_CLASS (social-class/wagez 120)))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert!(err.message.contains("never declared"), "{}", err.message);
    }

    #[test]
    fn a_bare_int_above_1_into_a_unit_interval_field_is_refused() {
        // 120 in a field declared `intensity` is outside that type's [0,1]
        // domain — storing it would make the store lie about what it holds.
        //
        // Renamed from `an_int_into_a_non_int_declared_field_is_refused`
        // (F3, typed-attribute-seeding fix round): before Half 1, EVERY
        // non-int-declared field refused EVERY value outright, so that name
        // described the whole refusal. Half 1 legalized the field's type; a
        // bare Int is now syntactically admissible for `intensity`
        // (`attribute_value_unit_interval`'s bare-Int arm — no lex-time
        // domain check on an unsuffixed literal) and refused ONLY because
        // 120 leaves [0,1] — the name now says what's actually tested. The
        // assertion (`"declared"`) is unmodified from before Half 1 and
        // continues to pass unchanged: existing behavior at this exact
        // boundary held, part of the additivity proof.
        let source = r"
(scenario ft/mistyped
  (deffield social-class/agitation intensity intensive)
  (node core NodeType/SOCIAL_CLASS (social-class/agitation 120)))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert!(err.message.contains("declared"), "{}", err.message);
    }

    // ---- Half 1 (typed-attribute seeding, P27 Phase 2) ----
    // `reports/typed-attribute-seeding-design-2026-08-11.md` §A/§E.

    #[test]
    fn a_scaled_literal_seeds_correctly_into_each_unit_interval_type() {
        // Exact-bit pins, NOT a tolerance. A `< 1e-12` comparison here would
        // hide exactly the transcription error it would appear to absorb —
        // the repo's own rule (`vitality_conformance.rs`). The conversion
        // CONTRACT `attribute_value_unit_interval`'s doc comment documents is
        // bit-for-bit IEEE-754, not approximately-equal.
        //
        // Expected bits computed INDEPENDENTLY of this crate — Python's
        // `struct.pack('>d', v)`, a different language's own correctly-
        // rounded decimal-to-binary conversion — not by re-running this
        // crate's own division and calling the result the oracle.
        //
        // `0.7c` and `0.123456789c` are DISCRIMINATING: `numerator *
        // 10_f64.powi(-scale)` (a real, non-equivalent reciprocal-multiply
        // substitution for the `/` this function actually uses) diverges
        // from `numerator / 10_f64.powi(scale)` at exactly these values
        // (`0.7c` seeds as `0x3fe6666666666667` under the mutation, against
        // `0x3fe6666666666666` here) while AGREEING at 0.75/0.5/0.358 — a
        // test using only the latter three is blind to that whole mutation
        // class, which is exactly what the F1 fix round found.
        for (ty, literal, expected_bits) in [
            ("probability", "0.75p", 0x3fe8_0000_0000_0000_u64),
            ("intensity", "0.5i", 0x3fe0_0000_0000_0000_u64),
            ("coefficient", "0.358c", 0x3fd6_e978_d4fd_f3b6_u64),
            ("coefficient", "0.7c", 0x3fe6_6666_6666_6666_u64),
            ("coefficient", "0.123456789c", 0x3fbf_9add_3739_635f_u64),
        ] {
            let source = format!(
                "(scenario ft/unit-interval\n  \
                 (deffield social-class/x {ty} intensive)\n  \
                 (node core NodeType/SOCIAL_CLASS (social-class/x {literal})))"
            );
            let mut graph = MemoryGraph::new();
            load_scenario(&source, &mut graph).unwrap();
            let value = graph.node_attribute(NodeId(0), "social-class/x").unwrap();
            assert_eq!(
                value.to_bits(),
                expected_bits,
                "{ty} {literal}: got 0x{:016x}, want 0x{expected_bits:016x}",
                value.to_bits()
            );
        }
    }

    #[test]
    fn a_seeded_literal_bit_matches_the_same_literal_written_by_a_rule() {
        // F1 (typed-attribute-seeding fix round): the conversion contract
        // pinned as the RELATION between the two paths, which is what
        // `attribute_value_unit_interval`'s doc comment actually promises —
        // not two independently-eyeballed numbers that happen to agree.
        // Seeds a field via the scenario loader (`attribute_value`) with a
        // literal, and separately has a rule write the IDENTICAL literal
        // text to a parallel field via `(update-node self … (set …))` —
        // the runtime path (`tick.rs::atom_to_value` /
        // `structural_verbs.rs::numeric_write_value`) — then compares
        // `to_bits()` off the live graph. Mutation-caught: the same
        // reciprocal-multiply substitution the previous test's doc comment
        // describes leaves this test's OTHER two literals agreeing but
        // diverges `0.7c` between the two paths.
        for literal in ["0.7c", "0.5c", "0.123456789c"] {
            let source = format!(
                "(scenario ft/bit-equality\n  \
                 (deffield social-class/seeded coefficient extensive)\n  \
                 (deffield social-class/written coefficient extensive)\n  \
                 (node core NodeType/SOCIAL_CLASS (social-class/seeded {literal})))"
            );
            let mut graph = MemoryGraph::new();
            load_scenario(&source, &mut graph).unwrap();

            let types = TypeEnv {
                fields: HashMap::from([
                    (
                        "social-class/seeded".to_owned(),
                        FieldDecl {
                            ty: BslType::Coefficient,
                            kind: FieldKind::Extensive,
                        },
                    ),
                    (
                        "social-class/written".to_owned(),
                        FieldDecl {
                            ty: BslType::Coefficient,
                            kind: FieldKind::Extensive,
                        },
                    ),
                ]),
                exemptions: &[],
            };
            let vocabulary = BindingVocabulary {
                fields: types.fields.keys().cloned().collect(),
                consts: HashSet::new(),
                metrics: HashSet::new(),
            };
            let ceilings = CardinalityCeilings::new(
                HashMap::from([("NodeType/SOCIAL_CLASS".to_owned(), 100)]),
                HashMap::new(),
            );
            let intrinsics = IntrinsicCosts::default();
            let systems = HashSet::from(["ft".to_owned()]);
            let ctx = LoadContext {
                vocabulary: &vocabulary,
                types: &types,
                ceilings: &ceilings,
                intrinsics: &intrinsics,
                systems: &systems,
                vocabulary_registry: None,
                rule_file: "ft/bit-equality.bsl",
            };
            let rule = format!(
                "(rule ft/mirror\n  \
                 :material-basis \"pins the seed path and the runtime write path to the \
                 SAME conversion, as one relation rather than two independently-eyeballed \
                 numbers\"\n  \
                 :fuel 64\n  \
                 (bindings (binding seeded :field social-class/seeded))\n  \
                 (when (>= seeded 0.0c))\n  \
                 (effects (update-node self social-class/written (set {literal}))))"
            );
            let loaded =
                load_rule(&rule, &ctx).unwrap_or_else(|e| panic!("{literal}: rule must load: {e}"));
            let mut sink = CollectingSink::default();
            let enums = EnumRegistry::default();
            run_tick(
                &loaded,
                &types,
                &enums,
                &EmptyIntrinsicHost,
                &mut graph,
                &mut sink,
                &intrinsics,
                &DefinesEnv::new(),
                1,
            )
            .unwrap_or_else(|e| panic!("{literal}: tick must run: {e}"));

            let seeded = graph
                .node_attribute(NodeId(0), "social-class/seeded")
                .unwrap();
            let written = graph
                .node_attribute(NodeId(0), "social-class/written")
                .unwrap();
            assert_eq!(
                seeded.to_bits(),
                written.to_bits(),
                "{literal}: seed path 0x{:016x} != runtime path 0x{:016x}",
                seeded.to_bits(),
                written.to_bits()
            );
        }
    }

    #[test]
    fn unit_interval_literal_acceptance_is_kind_blind_among_p_i_c() {
        // `store_range_check`'s own runtime predicate does not distinguish
        // Probability/Intensity/Coefficient from one another — `Value::Real`
        // carries no p/i/c tag once a literal is evaluated. This load-time
        // mirror does not either: a `p`-suffixed literal is legal for a
        // `coefficient`-declared field.
        let source = r"
(scenario ft/kind-blind
  (deffield social-class/agitation coefficient intensive)
  (node core NodeType/SOCIAL_CLASS (social-class/agitation 0.5p)))
";
        let mut graph = MemoryGraph::new();
        load_scenario(source, &mut graph).unwrap();
        let value = graph
            .node_attribute(NodeId(0), "social-class/agitation")
            .unwrap();
        assert!((value - 0.5).abs() < 1e-12);
    }

    #[test]
    fn a_bare_int_within_0_1_seeds_a_unit_interval_field() {
        // Bare Int literals carry no lex-time domain check, so an IN-range
        // one (unlike `a_bare_int_above_1_into_a_unit_interval_field_is_refused`'s
        // 120) must be accepted, exactly as `store_range_check` would accept
        // a rule-computed `Value::Int` widened to the same f64 at runtime.
        let source = r"
(scenario ft/bare-int-in-range
  (deffield social-class/agitation intensity intensive)
  (node core NodeType/SOCIAL_CLASS (social-class/agitation 1)))
";
        let mut graph = MemoryGraph::new();
        load_scenario(source, &mut graph).unwrap();
        let value = graph
            .node_attribute(NodeId(0), "social-class/agitation")
            .unwrap();
        assert!((value - 1.0).abs() < 1e-12);
    }

    #[test]
    fn a_negative_bare_int_into_a_unit_interval_field_is_refused() {
        // The mirrored predicate's message, pinned precisely: mentions the
        // [0,1] domain and states the never-a-clamp discipline, matching
        // `store_range_check`'s own wording family (`E-EVAL-020`).
        let source = r"
(scenario ft/negative-bare-int
  (deffield social-class/agitation probability intensive)
  (node core NodeType/SOCIAL_CLASS (social-class/agitation -3)))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert!(err.message.contains("[0,1]"), "{}", err.message);
        assert!(err.message.contains("never a clamp"), "{}", err.message);
    }

    #[test]
    fn a_ratio_literal_is_refused_for_a_unit_interval_field_even_in_range() {
        // 0.5r numerically falls in [0,1], but Ratio is a distinct runtime
        // `Value` variant with its own (0, ∞) domain, and a `:field` read
        // can never legally produce one (`bind_subject` wraps every field
        // read `Value::Real`) — a kind refusal, not a range violation.
        let source = r"
(scenario ft/ratio-into-coefficient
  (deffield social-class/agitation coefficient intensive)
  (node core NodeType/SOCIAL_CLASS (social-class/agitation 0.5r)))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert!(err.message.contains("Ratio"), "{}", err.message);
    }

    #[test]
    fn an_int_exceeding_f64_exact_range_is_refused() {
        // The 2^53 guard, unchanged by Half 1 — still lives in
        // `attribute_value_int`, still fires for an `int`-declared field.
        let source = format!(
            "(scenario ft/too-big\n  (deffield social-class/population int extensive)\n  \
             (node core NodeType/SOCIAL_CLASS (social-class/population {})))",
            (1_i64 << 53) + 1
        );
        let mut graph = MemoryGraph::new();
        let err = load_scenario(&source, &mut graph).unwrap_err();
        assert!(
            err.message.contains("exceeds f64's exact integer range"),
            "{}",
            err.message
        );
    }

    #[test]
    fn an_int_at_exactly_2_pow_53_still_loads() {
        // The boundary is inclusive — exact in f64 up to and including 2^53.
        let source = format!(
            "(scenario ft/at-boundary\n  (deffield social-class/population int extensive)\n  \
             (node core NodeType/SOCIAL_CLASS (social-class/population {})))",
            1_i64 << 53
        );
        let mut graph = MemoryGraph::new();
        load_scenario(&source, &mut graph).unwrap();
    }

    #[test]
    fn the_currency_refusal_cites_the_directors_defer_to_first_consumer_ruling() {
        // Wording update (typed-attribute-seeding train, 2026-08-11): the
        // refusal used to cite "a declared Phase-2 trait revision"; the
        // Director's popup ruling supersedes that framing.
        let source = r"
(scenario ft/money-ruling
  (deffield social-class/wages currency extensive)
  (node core NodeType/SOCIAL_CLASS (social-class/wages 120$)))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert!(
            err.message.contains("typed attribute storage"),
            "{}",
            err.message
        );
        assert!(
            err.message.contains("first real consumer"),
            "{}",
            err.message
        );
        assert!(err.message.contains("2026-08-11"), "{}", err.message);
    }

    #[test]
    fn a_currency_literal_into_an_int_declared_field_is_refused() {
        // The OTHER Currency-refusal site: the field is legally declared
        // `int`, but the literal itself is `$`-suffixed.
        let source = r"
(scenario ft/currency-into-int
  (deffield social-class/wages int extensive)
  (node core NodeType/SOCIAL_CLASS (social-class/wages 120$)))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert!(
            err.message.contains("typed attribute storage"),
            "{}",
            err.message
        );
    }

    #[test]
    fn a_currency_literal_into_a_unit_interval_field_is_refused() {
        let source = r"
(scenario ft/currency-into-coefficient
  (deffield social-class/agitation coefficient intensive)
  (node core NodeType/SOCIAL_CLASS (social-class/agitation 120$)))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert!(
            err.message.contains("typed attribute storage"),
            "{}",
            err.message
        );
    }

    #[test]
    fn a_coefficient_attribute_hashes_identically_to_the_same_f64_as_an_int() {
        // The "provably additive" claim, made concrete at the byte level:
        // seeding a `coefficient`-declared field with `0.358c` must produce
        // the EXACT same section-0x02 row shape `StateEncoder` would produce
        // for an `int`-declared field holding the same f64 — proving
        // `attribute_value`'s widening introduced no format branch keyed on
        // `BslType`. `CanonicalState`'s section 0x02 is a bare
        // `u64 id ‖ str name ‖ u64 value-bits` regardless of which BSL type
        // declared the field (`rust/crates/babylon-graph/src/state_hash.rs`
        // module docs).
        let source = r"
(scenario ft/mixed-types
  (deffield social-class/population int extensive)
  (deffield social-class/agitation coefficient intensive)
  (node core NodeType/SOCIAL_CLASS
    (social-class/population 120)
    (social-class/agitation 0.358c)))
";
        let mut graph = MemoryGraph::new();
        load_scenario(source, &mut graph).unwrap();
        let hash = graph.state_hash().unwrap();

        // Hand-built via StateEncoder directly, bypassing attribute_value
        // (and the whole scenario loader) entirely — a second, independent
        // encoding of the identical facts, attributes sorted by name
        // ascending ("social-class/agitation" < "social-class/population").
        let mut enc = StateEncoder::new();
        enc.write_nodes(&[(NodeId(0), "SOCIAL_CLASS".to_owned())])
            .unwrap();
        enc.write_attributes(&[
            (
                NodeId(0),
                "social-class/agitation".to_owned(),
                358.0 / 1000.0,
            ),
            (NodeId(0), "social-class/population".to_owned(), 120.0),
        ])
        .unwrap();
        enc.write_edges(&[]).unwrap();
        enc.write_hyperedges(&[]).unwrap();
        assert_eq!(hash, enc.finish());
    }

    #[test]
    fn a_defconst_becomes_the_defines_environment() {
        // §2.5's `:const` reads the defines environment, and slice 1 has no
        // GameDefines reader — so the scenario declares it, exactly as it
        // declares fields.
        let source = r"
(scenario ft/coefficients
  (defconst economy/base-subsistence 0.0005c)
  (defconst economy/tick-budget 12))
";
        let mut graph = MemoryGraph::new();
        let loaded = load_scenario(source, &mut graph).unwrap();
        assert_eq!(loaded.consts.len(), 2);
        // 5 / 10^4, the canonical minimal-scale form — the same conversion
        // the tick applies to a `:default` literal.
        assert_eq!(
            loaded.consts["economy/base-subsistence"],
            crate::evaluator::Value::Real(5.0 / 10_f64.powi(4))
        );
        assert_eq!(
            loaded.consts["economy/tick-budget"],
            crate::evaluator::Value::Int(12)
        );
    }

    // ---- §3.2 addendum, #492/ADR194: Ratio defconsts + :cap ----

    #[test]
    fn a_bare_ratio_defconst_carries_no_cap() {
        // No :cap — the domain is Ratio's own (0, ∞), unbounded above.
        // Matches rent_spike_multiplier's declared domain exactly (Territory
        // eviction pipeline; "moddable to 2.0" is well inside it).
        let source = r"
(scenario ft/uncapped-ratio
  (defconst territory/rent-spike-multiplier 2.0r))
";
        let mut graph = MemoryGraph::new();
        let loaded = load_scenario(source, &mut graph).unwrap();
        match &loaded.consts["territory/rent-spike-multiplier"] {
            crate::evaluator::Value::Ratio { value, floor, cap } => {
                assert!((value.get() - 2.0).abs() < 1e-12);
                assert_eq!(*floor, None);
                assert_eq!(*cap, None);
            }
            other => panic!("expected Value::Ratio, got {other:?}"),
        }
    }

    #[test]
    fn a_capped_ratio_defconst_within_bounds_loads() {
        // pareto_alpha's shape: declared domain (0, 10], value 1.5.
        let source = r"
(scenario ft/capped-ratio
  (defconst lifecycle/pareto-alpha 1.5r :cap 10r))
";
        let mut graph = MemoryGraph::new();
        let loaded = load_scenario(source, &mut graph).unwrap();
        match &loaded.consts["lifecycle/pareto-alpha"] {
            crate::evaluator::Value::Ratio { value, floor, cap } => {
                assert!((value.get() - 1.5).abs() < 1e-12);
                assert_eq!(*floor, None);
                assert!((cap.expect("cap declared").get() - 10.0).abs() < 1e-12);
            }
            other => panic!("expected Value::Ratio, got {other:?}"),
        }
    }

    #[test]
    fn a_ratio_defconst_exceeding_its_own_declared_cap_is_e_load_052() {
        let source = r"
(scenario ft/over-cap
  (defconst lifecycle/pareto-alpha 12r :cap 10r))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert_eq!(err.code, Some("E-LOAD-052"));
        assert!(
            err.message.contains("exceeds its own :cap"),
            "{}",
            err.message
        );
    }

    #[test]
    fn a_ratio_defconst_exactly_at_its_cap_loads() {
        // Closed at the top, like every other closed-interval-at-the-top
        // domain this spec uses (p/i/c's [0,1] accepts the endpoint).
        let source = r"
(scenario ft/at-cap
  (defconst lifecycle/pareto-alpha 10r :cap 10r))
";
        let mut graph = MemoryGraph::new();
        let loaded = load_scenario(source, &mut graph).unwrap();
        match &loaded.consts["lifecycle/pareto-alpha"] {
            crate::evaluator::Value::Ratio { value, floor, cap } => {
                assert!((value.get() - 10.0).abs() < 1e-12);
                assert_eq!(*floor, None);
                assert!((cap.unwrap().get() - 10.0).abs() < 1e-12);
            }
            other => panic!("expected Value::Ratio, got {other:?}"),
        }
    }

    #[test]
    fn cap_on_a_non_ratio_literal_is_refused() {
        // :cap narrows Ratio's own (0, ∞) domain specifically — it has no
        // meaning on a p/i/c literal (already capped [0,1] at lex time) or
        // an Int, and silently ignoring it would hide an authoring mistake.
        for (label, src) in [
            ("c", "(defconst economy/rate 0.5c :cap 10r)"),
            ("int", "(defconst economy/count 5 :cap 10r)"),
        ] {
            let source = format!("(scenario ft/stray-cap {src})");
            let mut graph = MemoryGraph::new();
            let err = load_scenario(&source, &mut graph).unwrap_err();
            assert!(
                err.message
                    .contains(":floor/:cap are legal only on a Ratio"),
                "{label}: {}",
                err.message
            );
        }
    }

    #[test]
    fn caps_own_operand_must_itself_be_a_ratio_literal() {
        let source = r"
(scenario ft/bad-cap-operand
  (defconst lifecycle/pareto-alpha 1.5r :cap 0.5c))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert!(
            err.message.contains(":cap's operand must be a Ratio"),
            "{}",
            err.message
        );
    }

    // ---- :floor (DEFECT 1 fix round, adversarial verification of #500) ----

    #[test]
    fn a_floored_ratio_defconst_within_bounds_loads() {
        // entropy_factor's exact shape: declared domain (1.0, 3.0], value
        // 1.5. `content/rules/metabolism.bsl`'s eventual port will read
        // this exact const once that train lands.
        let source = r"
(scenario ft/floored-ratio
  (defconst metabolism/entropy-factor 1.5r :floor 1r :cap 3r))
";
        let mut graph = MemoryGraph::new();
        let loaded = load_scenario(source, &mut graph).unwrap();
        match &loaded.consts["metabolism/entropy-factor"] {
            crate::evaluator::Value::Ratio { value, floor, cap } => {
                assert!((value.get() - 1.5).abs() < 1e-12);
                assert!((floor.expect("floor declared").get() - 1.0).abs() < 1e-12);
                assert!((cap.expect("cap declared").get() - 3.0).abs() < 1e-12);
            }
            other => panic!("expected Value::Ratio, got {other:?}"),
        }
    }

    #[test]
    fn floor_alone_with_no_cap_loads() {
        let source = r"
(scenario ft/floor-only
  (defconst metabolism/entropy-factor 1.5r :floor 1r))
";
        let mut graph = MemoryGraph::new();
        let loaded = load_scenario(source, &mut graph).unwrap();
        match &loaded.consts["metabolism/entropy-factor"] {
            crate::evaluator::Value::Ratio { value, floor, cap } => {
                assert!((value.get() - 1.5).abs() < 1e-12);
                assert!((floor.expect("floor declared").get() - 1.0).abs() < 1e-12);
                assert_eq!(*cap, None);
            }
            other => panic!("expected Value::Ratio, got {other:?}"),
        }
    }

    #[test]
    fn cap_before_floor_in_source_order_still_parses() {
        // parse_bound_keywords accepts either order.
        let source = r"
(scenario ft/cap-then-floor
  (defconst metabolism/entropy-factor 1.5r :cap 3r :floor 1r))
";
        let mut graph = MemoryGraph::new();
        let loaded = load_scenario(source, &mut graph).unwrap();
        match &loaded.consts["metabolism/entropy-factor"] {
            crate::evaluator::Value::Ratio { value, floor, cap } => {
                assert!((value.get() - 1.5).abs() < 1e-12);
                assert!((floor.unwrap().get() - 1.0).abs() < 1e-12);
                assert!((cap.unwrap().get() - 3.0).abs() < 1e-12);
            }
            other => panic!("expected Value::Ratio, got {other:?}"),
        }
    }

    #[test]
    fn a_value_at_exactly_its_declared_floor_is_e_load_052() {
        // EXCLUSIVE: the declared value must be STRICTLY greater than its
        // own floor — matching entropy_factor's `> 1.0`, not `>= 1.0`.
        let source = r"
(scenario ft/at-floor
  (defconst metabolism/entropy-factor 1r :floor 1r :cap 3r))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert_eq!(err.code, Some("E-LOAD-052"));
        assert!(
            err.message.contains("does not exceed its own :floor"),
            "{}",
            err.message
        );
    }

    #[test]
    fn a_value_below_its_declared_floor_is_e_load_052() {
        let source = r"
(scenario ft/below-floor
  (defconst metabolism/entropy-factor 0.5r :floor 1r :cap 3r))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert_eq!(err.code, Some("E-LOAD-052"));
        assert!(
            err.message.contains("does not exceed its own :floor"),
            "{}",
            err.message
        );
    }

    #[test]
    fn a_floor_not_strictly_below_its_cap_is_e_load_052() {
        // (floor, cap] is empty unless floor < cap — floor == cap and
        // floor > cap are both refused.
        for (label, src) in [
            (
                "equal",
                "(defconst metabolism/entropy-factor 2r :floor 2r :cap 2r)",
            ),
            (
                "inverted",
                "(defconst metabolism/entropy-factor 2r :floor 3r :cap 2r)",
            ),
        ] {
            let source = format!("(scenario ft/bad-floor-cap {src})");
            let mut graph = MemoryGraph::new();
            let err = load_scenario(&source, &mut graph).unwrap_err();
            assert_eq!(err.code, Some("E-LOAD-052"), "{label}: {}", err.message);
            assert!(
                err.message.contains("is not strictly below its own :cap"),
                "{label}: {}",
                err.message
            );
        }
    }

    #[test]
    fn floors_own_operand_must_itself_be_a_ratio_literal() {
        let source = r"
(scenario ft/bad-floor-operand
  (defconst metabolism/entropy-factor 1.5r :floor 0.5c))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert!(
            err.message.contains(":floor's operand must be a Ratio"),
            "{}",
            err.message
        );
    }

    #[test]
    fn a_repeated_bound_keyword_is_loud_never_last_one_wins() {
        let source = r"
(scenario ft/dup-floor
  (defconst metabolism/entropy-factor 1.5r :floor 1r :floor 0.5r))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert!(err.message.contains("given twice"), "{}", err.message);
    }

    #[test]
    fn an_unrecognized_bound_keyword_is_refused() {
        let source = r"
(scenario ft/bad-keyword
  (defconst metabolism/entropy-factor 1.5r :ceiling 3r))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert!(
            err.message.contains("unrecognized keyword"),
            "{}",
            err.message
        );
    }

    #[test]
    fn a_currency_defconst_is_refused_exactly_as_a_currency_default_is() {
        // One literal, one legality. `tick.rs::atom_to_value` refuses a
        // Currency `:default` and `attribute_value` refuses a Currency
        // attribute; a defconst that accepted one would make the form the
        // literal was written in decide whether it typechecks.
        let source = r"
(scenario ft/money-coefficient
  (defconst economy/floor-wage 15$))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert!(
            err.message.contains("typed attribute storage"),
            "{}",
            err.message
        );
    }

    #[test]
    fn a_duplicate_defconst_is_loud_never_last_one_wins() {
        // A coefficient has one value. Silently rebinding it would make the
        // rule reading it depend on declaration order.
        let source = r"
(scenario ft/twice
  (defconst economy/base-subsistence 0.0005c)
  (defconst economy/base-subsistence 0.5c))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert!(
            err.message.contains("duplicate defconst"),
            "{}",
            err.message
        );
    }

    #[test]
    fn a_defconst_taking_an_expression_is_refused() {
        // A coefficient is a number. An expression would need an evaluation
        // environment that does not exist at scenario-load time, and
        // accepting the form while ignoring the operand is the silent-drop
        // shape.
        let source = r"
(scenario ft/computed
  (defconst economy/base-subsistence (* 2 3)))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert!(err.message.contains("<literal>"), "{}", err.message);
    }

    #[test]
    fn a_file_holding_two_scenarios_is_refused() {
        let source = "(scenario a/one) (scenario a/two)";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert!(err.message.contains("exactly one"), "{}", err.message);
    }

    // ---- §2.13 `.bscn` dialect: defenum, enum deffield, EnumRef-only
    // seeding (Organization spec §1 Q12, D101) ----

    const ORG_KIND_SOURCE: &str = r"
(scenario org/t
  (defenum OrgKind (OrgKind/STATE_APPARATUS OrgKind/BUSINESS
                     OrgKind/POLITICAL_FACTION OrgKind/CIVIL_SOCIETY))
  (deffield organization/kind enum OrgKind)
  (node acme NodeType/ORGANIZATION (organization/kind OrgKind/BUSINESS)))
";

    #[test]
    fn an_enum_field_seeds_by_member_ref_and_stores_the_declared_ordinal() {
        let mut graph = MemoryGraph::new();
        let loaded = load_scenario(ORG_KIND_SOURCE, &mut graph).expect("loads");
        assert_eq!(loaded.node_count, 1);
        let id = graph.nodes("ORGANIZATION")[0];
        let stored = graph.node_attribute(id, "organization/kind").unwrap();
        assert!(
            (stored - 1.0).abs() < 1e-12,
            "BUSINESS is declaration-order index 1, stored: {stored}"
        );
        assert!(loaded.enums.resolve("OrgKind").is_some());
    }

    #[test]
    fn a_bare_number_into_an_enum_field_refuses_naming_the_law() {
        let source = r"
(scenario org/t
  (defenum OrgKind (OrgKind/STATE_APPARATUS OrgKind/BUSINESS))
  (deffield organization/kind enum OrgKind)
  (node acme NodeType/ORGANIZATION (organization/kind 1)))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert_eq!(err.code, Some("E-LOAD-056"));
        assert!(
            err.message.contains("<EnumType>/<MEMBER>") && err.message.contains("never"),
            "{}",
            err.message
        );
    }

    #[test]
    fn a_wrong_enum_type_member_refuses() {
        let source = r"
(scenario org/t
  (defenum OrgKind (OrgKind/STATE_APPARATUS OrgKind/BUSINESS))
  (deffield organization/kind enum OrgKind)
  (node acme NodeType/ORGANIZATION (organization/kind NodeType/SOCIAL_CLASS)))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert_eq!(err.code, Some("E-LOAD-056"));
        assert!(err.message.contains("OrgKind"), "{}", err.message);
    }

    #[test]
    fn an_undeclared_member_refuses() {
        let source = r"
(scenario org/t
  (defenum OrgKind (OrgKind/STATE_APPARATUS OrgKind/BUSINESS))
  (deffield organization/kind enum OrgKind)
  (node acme NodeType/ORGANIZATION (organization/kind OrgKind/NOWHERE)))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert_eq!(err.code, Some("E-LOAD-055"));
        assert!(err.message.contains("NOWHERE"), "{}", err.message);
    }

    #[test]
    fn an_enum_deffield_naming_an_undeclared_type_is_e_load_054() {
        let source = r"
(scenario org/t
  (deffield organization/kind enum Nowhere)
  (node acme NodeType/ORGANIZATION))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert_eq!(err.code, Some("E-LOAD-054"));
    }

    #[test]
    fn enum_seeding_moves_no_existing_golden_bytes() {
        // A scenario with NO defenum/enum-deffield forms loads exactly as
        // it did before this train — an untouched, empty `EnumRegistry`.
        // `tick_goldens.rs` re-proves this at the byte level for
        // vitality-conformance.bscn on every run; this is the same claim
        // at the unit level, for the fixture this test module already uses.
        let mut first = MemoryGraph::new();
        let mut second = MemoryGraph::new();
        let a = load_scenario(TWO_CLASSES, &mut first).unwrap();
        let b = load_scenario(TWO_CLASSES, &mut second).unwrap();
        assert_eq!(first.state_hash().unwrap(), second.state_hash().unwrap());
        assert_eq!(a.node_count, 2);
        assert_eq!(b.node_count, 2);
    }

    // ---- §2.13/§3.6 `defvocabulary`: the closed graph vocabulary is
    // declared, never inferred (Task 7) ----

    #[test]
    fn a_scenario_declaring_the_vocabulary_loads_and_is_some() {
        let source = r"
(scenario org/vocab
  (defvocabulary NodeType (NodeType/SOCIAL_CLASS NodeType/TERRITORY NodeType/ORGANIZATION))
  (defvocabulary EdgeType
    (EdgeType/MEMBERSHIP EdgeType/PRESENCE EdgeType/COMMAND
     EdgeType/TRANSACTIONAL EdgeType/SOLIDARISTIC EdgeType/SOLIDARITY))
  (node acme NodeType/ORGANIZATION))
";
        let mut graph = MemoryGraph::new();
        let loaded = load_scenario(source, &mut graph).expect("loads");
        let vocabulary = loaded.vocabulary.expect("a declared vocabulary is Some");
        assert_eq!(
            vocabulary
                .check_enum_ref("NodeType", "ORGANIZATION")
                .unwrap(),
            EnumKind::NodeType
        );
        assert_eq!(
            vocabulary.check_enum_ref("EdgeType", "SOLIDARITY").unwrap(),
            EnumKind::EdgeType
        );
    }

    #[test]
    fn a_scenario_with_no_defvocabulary_forms_yields_none() {
        // Backward compatibility: existing content (this test module's own
        // TWO_CLASSES fixture, and every scenario predating §2.13) declares
        // no `defvocabulary` at all — enforcement stays exactly as inert
        // as it is today.
        let mut graph = MemoryGraph::new();
        let loaded = load_scenario(TWO_CLASSES, &mut graph).expect("loads");
        assert!(loaded.vocabulary.is_none());
    }

    #[test]
    fn closed_vocabularys_own_rendering_collision_propagates_as_e_load_032() {
        // TENANCY under two structural kinds — §2.9's disjointness
        // obligation, `ClosedVocabulary::new`'s own check, reached through
        // `load_defvocabulary`'s collected map rather than reinvented here.
        let source = r"
(scenario org/collision
  (defvocabulary NodeType (NodeType/TENANCY))
  (defvocabulary EdgeType (EdgeType/TENANCY))
  (node acme NodeType/TENANCY))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert_eq!(err.code, Some("E-LOAD-032"));
    }

    #[test]
    fn an_unknown_enum_kind_symbol_refuses() {
        let source = r"
(scenario org/badkind
  (defvocabulary SovereignType (SovereignType/USA)))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert_eq!(err.code, Some("E-LOAD-030"));
    }

    #[test]
    fn two_defvocabulary_forms_for_one_kind_is_e_load_001() {
        let source = r"
(scenario org/twice
  (defvocabulary NodeType (NodeType/SOCIAL_CLASS))
  (defvocabulary NodeType (NodeType/TERRITORY)))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert_eq!(err.code, Some("E-LOAD-001"));
    }

    #[test]
    fn a_defvocabulary_member_naming_a_different_kind_refuses() {
        let source = r"
(scenario org/mismatched
  (defvocabulary NodeType (EdgeType/SOLIDARITY)))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert!(err.message.contains("different kind"), "{}", err.message);
    }
}
