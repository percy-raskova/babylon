//! Checked native instances for captured catalogs. Declarations and instance
//! hydration use the authored loader's existing semantics, one row at a time.

use super::{
    effective_practice_attributes, err, invert_content_ids, invert_hyperedge_content_ids,
    load_edge, load_edge_attr, load_hyperedge, load_hyperedge_attr, load_node,
    map_practice_load_error, require_practice_field_signatures, LoadedScenario, ScenarioError,
};
use crate::reader::{read, Atom, SExpr, ScaledKind, ScaledLit};
use babylon_graph::substrate::{GraphSubstrate, HyperedgeId, NodeId};
use babylon_kernel::currency::Currency;
use babylon_practice_contract::{PracticeTargetDomain, PracticeTopologyLoadCounter};
use std::collections::{BTreeSet, HashMap, HashSet};

// Keep the current authored instance ceiling until the national compiler has
// measured its actual seed. Native capture removes the text/AST duplication;
// it does not silently remove the existing finite admission limits.
const MAX_SEED_ROWS: usize = 65_536;
const MAX_SEED_VALUES: usize = 1_048_576;

/// One exact literal admitted by the same field rules as authored BSCN.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum SeedValue {
    /// An integer exactly representable by the graph's numeric lane.
    Integer(i64),
    /// A canonical decimal in its declared scalar domain.
    Scaled(ScaledLit),
    /// Nonnegative opening money in the separate i128 currency lane.
    Currency(Currency),
    /// A named member of a declared enum.
    Enum { enum_type: String, member: String },
}

impl SeedValue {
    fn atom(&self) -> Atom {
        match self {
            Self::Integer(value) => Atom::Int(*value),
            Self::Scaled(value) => Atom::Scaled(*value),
            Self::Currency(value) => Atom::Currency(*value),
            Self::Enum { enum_type, member } => Atom::EnumRef {
                enum_type: enum_type.clone(),
                member: member.clone(),
            },
        }
    }

    fn validate(&self) -> Result<(), ScenarioError> {
        let valid = match self {
            Self::Integer(value) => value.unsigned_abs() <= 9_007_199_254_740_992,
            Self::Currency(value) => value.micro_units() >= 0,
            Self::Enum { enum_type, member } => {
                validate_atom(&format!("{enum_type}/{member}"), &self.atom())?;
                true
            }
            Self::Scaled(value) => valid_scaled(*value),
        };
        if valid {
            Ok(())
        } else {
            Err(err("native seed literal is outside its canonical domain"))
        }
    }
}

fn valid_scaled(value: ScaledLit) -> bool {
    if value.scale > 9 || value.unscaled < 0 || (value.scale > 0 && value.unscaled % 10 == 0) {
        return false;
    }
    let denominator = 10_i128.pow(u32::from(value.scale));
    match value.kind {
        ScaledKind::Ratio => {
            value.unscaled > 0 && (value.scale < 7 || value.unscaled >= denominator / 2_000_000)
        }
        _ => value.unscaled <= denominator,
    }
}

/// A single declared field and opening value.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SeedAttribute {
    pub field: String,
    pub value: SeedValue,
}

/// An opening node with content-stable local identity.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NodeSeed {
    pub local_name: String,
    pub node_type: String,
    pub attributes: Vec<SeedAttribute>,
}

/// A directed edge identified by type and its ordered endpoints.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EdgeSeed {
    pub edge_type: String,
    pub source: String,
    pub target: String,
    pub strength: SeedValue,
    pub attributes: Vec<SeedAttribute>,
}

/// A native public hyperedge, without pairwise expansion of its membership.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HyperedgeSeed {
    pub local_name: String,
    pub hyperedge_type: String,
    pub members: Vec<String>,
    pub attributes: Vec<SeedAttribute>,
}

/// Immutable checked instance input. Its rows have canonical identity order.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct GraphSeed {
    nodes: Vec<NodeSeed>,
    edges: Vec<EdgeSeed>,
    hyperedges: Vec<HyperedgeSeed>,
}

impl GraphSeed {
    /// Check identities, duplicates, endpoints, finite bounds and literal domains.
    /// Declaration/type admission happens in [`load_scenario_with_seed`].
    ///
    /// # Errors
    /// Refuses ambiguous authority, malformed literals or names, and excess rows.
    pub fn try_new(
        mut nodes: Vec<NodeSeed>,
        mut edges: Vec<EdgeSeed>,
        mut hyperedges: Vec<HyperedgeSeed>,
    ) -> Result<Self, ScenarioError> {
        if nodes.len() > MAX_SEED_ROWS
            || edges.len() > MAX_SEED_ROWS
            || hyperedges.len() > MAX_SEED_ROWS
        {
            return Err(err(
                "native seed exceeds the current 65,536-row instance bound",
            ));
        }
        let mut names = BTreeSet::new();
        let mut values = 0_usize;
        for node in &mut nodes {
            validate_local(&node.local_name)?;
            validate_type("NodeType", &node.node_type)?;
            if !names.insert(node.local_name.clone()) {
                return Err(err("duplicate native node identity"));
            }
            validate_attributes(&mut node.attributes, &mut values)?;
        }
        let mut keys = BTreeSet::new();
        for edge in &mut edges {
            validate_type("EdgeType", &edge.edge_type)?;
            if !names.contains(&edge.source) || !names.contains(&edge.target) {
                return Err(err("native edge names an absent node"));
            }
            if !keys.insert((
                edge.edge_type.clone(),
                edge.source.clone(),
                edge.target.clone(),
            )) {
                return Err(err("duplicate native edge identity"));
            }
            edge.strength.validate()?;
            validate_attributes(&mut edge.attributes, &mut values)?;
        }
        validate_hyperedges(&mut hyperedges, &names, &mut values)?;
        nodes.sort_by(|a, b| a.local_name.cmp(&b.local_name));
        edges.sort_by(|a, b| {
            (&a.edge_type, &a.source, &a.target).cmp(&(&b.edge_type, &b.source, &b.target))
        });
        hyperedges.sort_by(|a, b| a.local_name.cmp(&b.local_name));
        Ok(Self {
            nodes,
            edges,
            hyperedges,
        })
    }

    #[must_use]
    pub fn nodes(&self) -> &[NodeSeed] {
        &self.nodes
    }
    #[must_use]
    pub fn edges(&self) -> &[EdgeSeed] {
        &self.edges
    }
    #[must_use]
    pub fn hyperedges(&self) -> &[HyperedgeSeed] {
        &self.hyperedges
    }
}

fn validate_hyperedges(
    rows: &mut [HyperedgeSeed],
    nodes: &BTreeSet<String>,
    values: &mut usize,
) -> Result<(), ScenarioError> {
    let mut names = BTreeSet::new();
    for row in rows {
        validate_local(&row.local_name)?;
        validate_type("HyperedgeType", &row.hyperedge_type)?;
        if !names.insert(row.local_name.clone()) {
            return Err(err("duplicate native hyperedge identity"));
        }
        if row.members.is_empty() {
            return Err(err("native hyperedge requires members"));
        }
        row.members.sort();
        if row.members.windows(2).any(|pair| pair[0] == pair[1])
            || row.members.iter().any(|name| !nodes.contains(name))
        {
            return Err(err("native hyperedge has duplicate or absent members"));
        }
        add_values(values, row.members.len())?;
        validate_attributes(&mut row.attributes, values)?;
    }
    Ok(())
}

fn validate_attributes(
    rows: &mut [SeedAttribute],
    values: &mut usize,
) -> Result<(), ScenarioError> {
    add_values(values, rows.len())?;
    rows.sort_by(|a, b| a.field.cmp(&b.field));
    if rows.windows(2).any(|pair| pair[0].field == pair[1].field) {
        return Err(err("duplicate native field authority"));
    }
    for row in rows {
        validate_atom(&row.field, &Atom::QName(row.field.clone()))?;
        row.value.validate()?;
    }
    Ok(())
}

fn add_values(count: &mut usize, additional: usize) -> Result<(), ScenarioError> {
    *count = count
        .checked_add(additional)
        .filter(|n| *n <= MAX_SEED_VALUES)
        .ok_or_else(|| err("native seed exceeds the value/membership bound"))?;
    Ok(())
}

fn validate_local(value: &str) -> Result<(), ScenarioError> {
    validate_atom(value, &Atom::Symbol(value.to_owned()))
}

fn validate_type(kind: &str, member: &str) -> Result<(), ScenarioError> {
    validate_atom(
        &format!("{kind}/{member}"),
        &Atom::EnumRef {
            enum_type: kind.to_owned(),
            member: member.to_owned(),
        },
    )
}

fn validate_atom(source: &str, expected: &Atom) -> Result<(), ScenarioError> {
    if source.len() > 128 {
        return Err(err("native seed name exceeds its byte bound"));
    }
    let (actual, consumed) = read(source)?;
    if consumed == source.len() && actual == SExpr::Atom(expected.clone()) {
        Ok(())
    } else {
        Err(err("native seed name is not one canonical atom"))
    }
}

fn symbol(name: &str) -> SExpr {
    SExpr::Atom(Atom::Symbol(name.to_owned()))
}
fn enum_ref(kind: &str, member: &str) -> SExpr {
    SExpr::Atom(Atom::EnumRef {
        enum_type: kind.to_owned(),
        member: member.to_owned(),
    })
}
fn attribute(row: &SeedAttribute) -> SExpr {
    SExpr::List(vec![
        SExpr::Atom(Atom::QName(row.field.clone())),
        SExpr::Atom(row.value.atom()),
    ])
}
fn node_form(row: &NodeSeed) -> Vec<SExpr> {
    let mut form = vec![
        symbol("node"),
        symbol(&row.local_name),
        enum_ref("NodeType", &row.node_type),
    ];
    form.extend(row.attributes.iter().map(attribute));
    form
}

/// Load declaration-only BSCN and hydrate checked captured instances through
/// the same field/type/graph operations as authored scenario instances.
///
/// # Errors
/// Refuses authored instances in native mode, missing closed vocabulary,
/// undeclared fields/types, practice topology violations or substrate failures.
pub fn load_scenario_with_seed(
    declarations: &str,
    prelude: Option<&str>,
    seed: &GraphSeed,
    graph: &mut dyn GraphSubstrate,
) -> Result<LoadedScenario, ScenarioError> {
    check_declaration_only(declarations)?;
    let mut loaded = match prelude {
        Some(prelude) => super::load_scenario_with_prelude(prelude, declarations, graph)?,
        None => super::load_scenario(declarations, graph)?,
    };
    if loaded.vocabulary.is_none() {
        return Err(err("native seed requires a declared closed vocabulary"));
    }
    check_practice(seed, &loaded)?;
    let mut hydration = Hydration::default();
    hydration.nodes(seed, &mut loaded, graph)?;
    hydration.edges(seed, &mut loaded, graph)?;
    hydration.hyperedges(seed, &mut loaded, graph)?;
    loaded.node_content_ids = invert_content_ids(&hydration.nodes);
    loaded.hyperedge_content_ids = invert_hyperedge_content_ids(&hydration.hyperedges);
    Ok(loaded)
}

fn check_declaration_only(source: &str) -> Result<(), ScenarioError> {
    let forms = super::bounded_scenario_read(source)?;
    let [SExpr::List(parts)] = forms.as_slice() else {
        return Err(err("native declarations require one scenario"));
    };
    for form in parts.iter().skip(2) {
        let SExpr::List(parts) = form else {
            return Err(err("native declarations require declaration forms"));
        };
        if !matches!(parts.first(), Some(SExpr::Atom(Atom::Symbol(tag)))
            if matches!(tag.as_str(), "defenum" | "defvocabulary" | "deffield" | "defconst"))
        {
            return Err(err("native graph source cannot contain authored instances"));
        }
    }
    Ok(())
}

fn check_practice(seed: &GraphSeed, loaded: &LoadedScenario) -> Result<(), ScenarioError> {
    if !loaded.fields.contains_key("organization/action-budget") {
        return Ok(());
    }
    require_practice_field_signatures(&loaded.fields)?;
    let mut counter = PracticeTopologyLoadCounter::new();
    let mut names = HashMap::new();
    for (index, node) in seed.nodes.iter().enumerate() {
        let ordinal = u64::try_from(index).map_err(|_| err("native node ordinal overflow"))?;
        names.insert(node.local_name.as_str(), (ordinal, node.node_type.as_str()));
        if node.node_type == "ORGANIZATION" {
            let attrs: Vec<_> = node.attributes.iter().map(attribute).collect();
            let (active, budget) = effective_practice_attributes(&attrs);
            counter
                .observe_organization(ordinal, active, budget)
                .map_err(map_practice_load_error)?;
        }
    }
    for edge in &seed.edges {
        let (from, from_kind) = names[edge.source.as_str()];
        let (to, to_kind) = names[edge.target.as_str()];
        if edge.edge_type == "SOLIDARITY"
            && from_kind == "ORGANIZATION"
            && to_kind == "SOCIAL_CLASS"
        {
            counter
                .observe_solidarity_edge(from, PracticeTargetDomain::SocialClass, to)
                .map_err(map_practice_load_error)?;
        }
    }
    counter.finish().map_err(map_practice_load_error)
}

#[derive(Default)]
struct Hydration {
    nodes: HashMap<String, NodeId>,
    edges: HashSet<(String, NodeId, NodeId)>,
    hyperedges: HashMap<String, HyperedgeId>,
}

impl Hydration {
    fn nodes(
        &mut self,
        seed: &GraphSeed,
        loaded: &mut LoadedScenario,
        graph: &mut dyn GraphSubstrate,
    ) -> Result<(), ScenarioError> {
        for row in &seed.nodes {
            let kind = load_node(
                &node_form(row),
                graph,
                &mut self.nodes,
                &loaded.fields,
                &loaded.enums,
                loaded.vocabulary.as_ref(),
            )?;
            *loaded.node_types.entry(kind).or_insert(0) += 1;
            loaded.node_count += 1;
        }
        Ok(())
    }

    fn edges(
        &mut self,
        seed: &GraphSeed,
        loaded: &mut LoadedScenario,
        graph: &mut dyn GraphSubstrate,
    ) -> Result<(), ScenarioError> {
        let mut attrs = HashSet::new();
        for row in &seed.edges {
            let form = vec![
                symbol("edge"),
                enum_ref("EdgeType", &row.edge_type),
                symbol(&row.source),
                symbol(&row.target),
                SExpr::Atom(row.strength.atom()),
            ];
            let kind = load_edge(
                &form,
                graph,
                &self.nodes,
                &mut self.edges,
                &loaded.enums,
                loaded.vocabulary.as_ref(),
            )?;
            *loaded.edge_types.entry(kind).or_insert(0) += 1;
            loaded.edge_count += 1;
            for attr in &row.attributes {
                let form = vec![
                    symbol("edge-attr"),
                    enum_ref("EdgeType", &row.edge_type),
                    symbol(&row.source),
                    symbol(&row.target),
                    SExpr::Atom(Atom::QName(attr.field.clone())),
                    SExpr::Atom(attr.value.atom()),
                ];
                load_edge_attr(
                    &form,
                    graph,
                    &self.nodes,
                    &self.edges,
                    &mut attrs,
                    &loaded.fields,
                    &loaded.enums,
                    loaded.vocabulary.as_ref(),
                )?;
            }
        }
        Ok(())
    }

    fn hyperedges(
        &mut self,
        seed: &GraphSeed,
        loaded: &mut LoadedScenario,
        graph: &mut dyn GraphSubstrate,
    ) -> Result<(), ScenarioError> {
        let mut attrs = HashSet::new();
        for row in &seed.hyperedges {
            let mut members = vec![symbol("members")];
            members.extend(row.members.iter().map(|name| symbol(name)));
            let form = vec![
                symbol("hyperedge"),
                symbol(&row.local_name),
                enum_ref("HyperedgeType", &row.hyperedge_type),
                SExpr::List(members),
            ];
            let (kind, count) = load_hyperedge(
                &form,
                graph,
                &self.nodes,
                &mut self.hyperedges,
                &loaded.enums,
                loaded.vocabulary.as_ref(),
            )?;
            *loaded.hyperedge_types.entry(kind.clone()).or_insert(0) += 1;
            loaded
                .max_members_seen
                .entry(kind)
                .and_modify(|n| *n = (*n).max(count))
                .or_insert(count);
            for attr in &row.attributes {
                let form = vec![
                    symbol("hyperedge-attr"),
                    symbol(&row.local_name),
                    SExpr::Atom(Atom::QName(attr.field.clone())),
                    SExpr::Atom(attr.value.atom()),
                ];
                load_hyperedge_attr(
                    &form,
                    graph,
                    &self.hyperedges,
                    &mut attrs,
                    &loaded.fields,
                    &loaded.enums,
                )?;
            }
        }
        Ok(())
    }
}
