//! The annotated member item of a scenario's `(hyperedge ...)` form (Amendment AG clause i, §3.9
//! clause 6; Task 7 of `docs/superpowers/plans/2026-11-21-memberships-that-carry-a-value.md`).
//!
//! ```text
//! <member-item> = <local-name> | (member <NodeType/MEMBER> <local-name> (<qname> <value>)*)
//! ```
//!
//! When the hyperedge's type declares any membership field for a member's node type, every item for
//! such a member is annotated and writes exactly those fields. A bare item or a missing field is
//! `E-LOAD-047`; a field twice is `E-PARSE-041`; a qname of another owner is `E-TYPE-014`; a member
//! not of the annotated type is `E-EVAL-033` (the verb's code, so one fact has one code). Values
//! convert through the loader's one per-type literal law (`attribute_value`).

#![allow(
    clippy::result_large_err,
    reason = "the scenario loader's error carries the full authored refusal context"
)]

use crate::evaluator::EvalCode;
use crate::grammar::GrammarError;
use crate::reader::{Atom, SExpr};
use crate::scenario::{self, ScenarioError};
use crate::types::{EnumRegistry, FieldDecl};
use crate::vocabulary::{ClosedVocabulary, EnumKind};
use babylon_graph::substrate::{GraphSubstrate, HyperedgeId, NodeId};
use std::collections::{BTreeMap, HashMap};

/// One seeded member and the membership values written for it, in the order written.
pub(crate) type SeededMember = (NodeId, Vec<(String, f64)>);

/// What the item parser reads from the loader: the registries, never the substrate's writes.
pub(crate) struct MemberContext<'a> {
    pub(crate) hyperedge: &'a str,
    pub(crate) hyperedge_type: &'a str,
    pub(crate) named: &'a HashMap<String, NodeId>,
    pub(crate) fields: &'a HashMap<String, FieldDecl>,
    pub(crate) membership_fields: &'a BTreeMap<String, String>,
    pub(crate) enums: &'a EnumRegistry,
    pub(crate) vocabulary: Option<&'a ClosedVocabulary>,
}

impl MemberContext<'_> {
    /// The membership qnames this hyperedge type declares for members of `node_type`, ascending.
    fn declared_for(&self, node_type: &str) -> Vec<&str> {
        self.membership_fields
            .iter()
            .filter(|(qname, member)| {
                member.as_str() == node_type
                    && crate::tick::namespace_to_node_type(qname.split('/').next().unwrap_or(qname))
                        == self.hyperedge_type
            })
            .map(|(qname, _)| qname.as_str())
            .collect()
    }

    fn resolve(&self, name: &str) -> Result<NodeId, ScenarioError> {
        let local = self.hyperedge;
        self.named.get(name).copied().ok_or_else(|| {
            scenario::err(format!(
                "hyperedge `{local}` names unknown node `{name}` — a node must be \
                 declared before a hyperedge referring to it, so a scenario reads \
                 top to bottom"
            ))
        })
    }
}

/// Parse and check every item of a `(members ...)` form against the declared membership fields.
pub(crate) fn parse_member_items(
    items: &[SExpr],
    graph: &dyn GraphSubstrate,
    cx: &MemberContext<'_>,
) -> Result<Vec<SeededMember>, ScenarioError> {
    let local = cx.hyperedge;
    let mut seeded = Vec::with_capacity(items.len());
    for item in items {
        match item {
            SExpr::Atom(Atom::Symbol(name)) => {
                let id = cx.resolve(name)?;
                let actual = graph.node_type_of(id)?;
                if !cx.declared_for(actual).is_empty() {
                    return Err(scenario::coded_err(
                        "E-LOAD-047",
                        format!(
                            "hyperedge `{local}`: member `{name}` is a bare item, but \
                             {} declares membership fields for {actual} members — \
                             a membership is written whole at hydration (§3.9 clause 6)",
                            cx.hyperedge_type
                        ),
                    ));
                }
                seeded.push((id, Vec::new()));
            }
            SExpr::List(parts) => seeded.push(parse_annotated(parts, graph, cx)?),
            SExpr::Atom(_) => {
                return Err(scenario::err(format!(
                    "hyperedge `{local}`: a member is a bare local node name or a \
                     (member <NodeType/MEMBER> <local-name> (<qname> <value>)*) item"
                )));
            }
        }
    }
    Ok(seeded)
}

fn parse_annotated(
    parts: &[SExpr],
    graph: &dyn GraphSubstrate,
    cx: &MemberContext<'_>,
) -> Result<SeededMember, ScenarioError> {
    let local = cx.hyperedge;
    let [SExpr::Atom(Atom::Symbol(head)), SExpr::Atom(Atom::EnumRef { enum_type, member }), SExpr::Atom(Atom::Symbol(name)), pairs @ ..] =
        parts
    else {
        return Err(scenario::err(format!(
            "hyperedge `{local}`: expected a member item (member <NodeType/MEMBER> \
             <local-name> (<qname> <value>)*)"
        )));
    };
    if head != "member" {
        return Err(scenario::err(format!(
            "hyperedge `{local}`: expected a member item (member ...), found ({head} ...)"
        )));
    }
    let form = format!("hyperedge `{local}` member `{name}`");
    scenario::demand_enum_kind(enum_type, member, EnumKind::NodeType, cx.enums)
        .map_err(|e| scenario::vocab_err(&form, &e))?;
    if let Some(vocabulary) = cx.vocabulary {
        vocabulary
            .check_enum_ref(enum_type, member)
            .map_err(|e| scenario::vocab_err(&form, &e))?;
    }
    let id = cx.resolve(name)?;
    let actual = graph.node_type_of(id)?;
    if actual != member {
        return Err(scenario::coded_err(
            EvalCode::AccessorTypeOrValueMismatch.spec_code(),
            format!("{form}: annotated {member}, but the node is a {actual}"),
        ));
    }
    let declared = cx.declared_for(member);
    let mut values: Vec<(String, f64)> = Vec::with_capacity(pairs.len());
    for pair in pairs {
        let (qname, value) = read_pair(pair, &form)?;
        let Some(decl) = cx.fields.get(qname) else {
            return Err(scenario::err(format!(
                "{form}: field `{qname}` was never declared — add a \
                 (deffield {qname} <type> <kind> :member NodeType/{member}) form ABOVE the \
                 hyperedge forms that use it"
            )));
        };
        if !declared.contains(&qname.as_str()) {
            let error = GrammarError::FieldInitOwnerMismatch {
                field: qname.clone(),
                verb_type: format!("{}/{member}", cx.hyperedge_type),
                owner: qname.split('/').next().unwrap_or(qname).to_owned(),
            };
            return Err(scenario::coded_err(
                error.spec_code(),
                format!(
                    "{form}: field `{qname}` is not a membership field of {} for {member} \
                     members",
                    cx.hyperedge_type
                ),
            ));
        }
        if values.iter().any(|(seen, _)| seen == qname) {
            let error = GrammarError::MemberFieldTwice {
                field: qname.clone(),
            };
            return Err(scenario::coded_err(error.spec_code(), error.to_string()));
        }
        let converted = scenario::attribute_value(value, &form, qname, decl, cx.enums)?;
        values.push((qname.clone(), converted));
    }
    if let Some(missing) = declared
        .iter()
        .find(|qname| !values.iter().any(|(seen, _)| seen == **qname))
    {
        return Err(scenario::coded_err(
            "E-LOAD-047",
            format!(
                "{form}: membership field `{missing}` is declared for {member} members \
                 but not written — a membership is written whole at hydration (§3.9 clause 6)"
            ),
        ));
    }
    Ok((id, values))
}

fn read_pair<'a>(pair: &'a SExpr, form: &str) -> Result<(&'a String, &'a Atom), ScenarioError> {
    if let SExpr::List(parts) = pair {
        if let [SExpr::Atom(Atom::QName(qname)), SExpr::Atom(value)] = parts.as_slice() {
            return Ok((qname, value));
        }
    }
    Err(scenario::err(format!(
        "{form}: expected (<qname> <value>), found {pair:?}"
    )))
}

/// One `update_membership_attribute` per seeded value, after the hyperedge is minted.
pub(crate) fn write_member_values(
    graph: &mut dyn GraphSubstrate,
    id: HyperedgeId,
    seeded: &[SeededMember],
) -> Result<(), ScenarioError> {
    for (member, values) in seeded {
        for (qname, value) in values {
            graph.update_membership_attribute(id, *member, qname, *value)?;
        }
    }
    Ok(())
}
