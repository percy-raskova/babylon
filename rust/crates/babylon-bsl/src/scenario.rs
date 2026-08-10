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
//!   refuses such a write loudly rather than casting lossily. Values here are
//!   integer literals, exact in `f64` to 2^53. Typed attribute storage is a
//!   declared Phase-2 trait revision (`docs/reference/phase-1-exit-checklist.md`),
//!   and the Fundamental Theorem will want it — wages and value produced are
//!   properly money. Slice 1 states the simplification rather than hiding it.
//! - **No hyperedges yet.** The grammar has room for them; nothing in slice 1
//!   needs one, and an unused form is an untested form.
//! - **No defaults.** A node with no attributes gets no attributes. An
//!   unwritten field errors on read (III.11), and seeding zeros here would
//!   defeat that at the one place it is easiest to defeat.

use crate::evaluator::Value;
use crate::reader::{read_all, Atom, ReadError, SExpr};
use crate::types::{BslType, FieldDecl, FieldKind};
use babylon_graph::substrate::{GraphError, GraphSubstrate, NodeId};
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
    let mut node_count = 0_usize;
    let mut edge_count = 0_usize;
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
            Some(SExpr::Atom(Atom::Symbol(tag))) if tag == "deffield" => {
                load_deffield(parts, &mut fields)?;
            }
            Some(SExpr::Atom(Atom::Symbol(tag))) if tag == "defconst" => {
                load_defconst(parts, &mut consts)?;
            }
            Some(SExpr::Atom(Atom::Symbol(tag))) if tag == "node" => {
                let minted = load_node(parts, graph, &mut named, &fields)?;
                *node_types.entry(minted).or_insert(0) += 1;
                node_count += 1;
            }
            Some(SExpr::Atom(Atom::Symbol(tag))) if tag == "edge" => {
                load_edge(parts, graph, &named, &mut seeded_edges)?;
                edge_count += 1;
            }
            _ => {
                return Err(err(
                    "a scenario body form must begin with `deffield`, `defconst`, \
                     `node` or `edge`",
                ))
            }
        }
    }

    Ok(LoadedScenario {
        id,
        node_count,
        edge_count,
        node_types,
        fields,
        consts,
    })
}

/// `(defconst <qname> <literal>)`
///
/// The defines environment in miniature (§2.5's `:const`, §4.2's
/// "the defines environment (coefficients)"). Slice 1 has no
/// `GameDefines`/`defines.yaml` reader, and §2.5 gives `:const` no other
/// source, so the alternative to declaring the value here is writing it
/// into the rule — putting a magnitude in the file that owns the shape.
///
/// Only the four literal atom classes §2.2 admits at `:default` are legal
/// here, for the same reason: a coefficient is a number, not an expression,
/// and an expression would need an evaluation environment that does not
/// exist at scenario-load time.
fn load_defconst(
    parts: &[SExpr],
    consts: &mut HashMap<String, Value>,
) -> Result<(), ScenarioError> {
    let [_, SExpr::Atom(Atom::QName(qname)), SExpr::Atom(literal)] = parts else {
        return Err(err(
            "expected (defconst <qname> <literal>) — one qualified name, one literal",
        ));
    };
    let value = match literal {
        Atom::Int(value) => Value::Int(*value),
        Atom::Scaled(scaled) => {
            // `unscaled / 10^scale`, the canonical minimal-scale form, and
            // the SAME arithmetic `tick.rs::atom_to_value` performs on a
            // `:default` literal — one conversion, so a coefficient reads
            // identically wherever it enters.
            #[allow(clippy::cast_precision_loss)]
            let numerator = scaled.unscaled as f64;
            Value::Real(numerator / 10_f64.powi(i32::from(scaled.scale)))
        }
        Atom::Bool(value) => Value::Bool(*value),
        Atom::Currency(value) => Value::Currency(*value),
        other => {
            return Err(err(format!(
                "defconst `{qname}`: expected a literal (int, scaled, currency or \
                 boolean), found {other:?}"
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

/// `(deffield <qname> <type-symbol> <kind-symbol>)`
///
/// The `deffield` registry in miniature. A field's TYPE and INTENSIVITY KIND
/// cannot be inferred from a stored value — `120` is an `Int` whether it is a
/// head-count that sums or a rate that does not — and §3.4 exists precisely
/// to stop that being guessed. So the scenario declares them.
fn load_deffield(
    parts: &[SExpr],
    fields: &mut HashMap<String, FieldDecl>,
) -> Result<(), ScenarioError> {
    let [_, SExpr::Atom(Atom::QName(qname)), SExpr::Atom(Atom::Symbol(ty)), SExpr::Atom(Atom::Symbol(kind))] =
        parts
    else {
        return Err(err(
            "expected (deffield <field-qname> <type> <intensive|extensive>)",
        ));
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
                 int / probability / intensity / coefficient / currency"
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
    if fields
        .insert(qname.clone(), FieldDecl { ty, kind })
        .is_some()
    {
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
        graph.update_node(id, field, attribute_value(value, local, field, decl)?)?;
    }
    Ok(member.clone())
}

/// Slice-1 attribute values: integer literals into `int`-declared fields.
///
/// The declaration is checked, not just consulted. A `120` written into a
/// field declared `intensity` would be out of that type's `[0, 1]` domain,
/// and one written into a `currency` field would silently become an f64
/// where i128 micro-units were promised — both are the store lying about
/// what it holds.
fn attribute_value(
    atom: &Atom,
    local: &str,
    field: &str,
    decl: &FieldDecl,
) -> Result<f64, ScenarioError> {
    if !matches!(decl.ty, BslType::Int) {
        return Err(err(format!(
            "node `{local}`: field `{field}` is declared {:?}, and slice 1 stores only \
             `int`-declared fields — the scaled and Currency lanes need typed attribute \
             storage (a declared Phase-2 trait revision), so this refuses rather than \
             widening a value into a type it was not declared as",
            decl.ty
        )));
    }
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
        Atom::Currency(_) => Err(err(format!(
            "node `{local}` field `{field}`: Currency attributes need typed attribute \
             storage (a declared Phase-2 trait revision) — f64 cannot hold i128 \
             micro-units, and slice 1 refuses rather than casting lossily"
        ))),
        other => Err(err(format!(
            "node `{local}` field `{field}`: expected an integer literal, found {other:?}"
        ))),
    }
}

/// `(edge <enum-ref> <local-name> <local-name> <int>)`
fn load_edge(
    parts: &[SExpr],
    graph: &mut dyn GraphSubstrate,
    named: &HashMap<String, NodeId>,
    seeded: &mut HashSet<(String, NodeId, NodeId)>,
) -> Result<(), ScenarioError> {
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
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::load_scenario;
    use babylon_graph::memory::MemoryGraph;
    use babylon_graph::substrate::{Direction, GraphSubstrate, NodeId};

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
    fn an_int_into_a_non_int_declared_field_is_refused() {
        // 120 in a field declared `intensity` is outside that type's [0,1]
        // domain — storing it would make the store lie about what it holds.
        let source = r"
(scenario ft/mistyped
  (deffield social-class/agitation intensity intensive)
  (node core NodeType/SOCIAL_CLASS (social-class/agitation 120)))
";
        let mut graph = MemoryGraph::new();
        let err = load_scenario(source, &mut graph).unwrap_err();
        assert!(err.message.contains("declared"), "{}", err.message);
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
}
