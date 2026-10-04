//! Native instances use the ordinary BSL declaration/type admission path.
use super::{EconomicCatalogError, EconomicOpening};
use crate::national_counties::NationalCountyReference;
use babylon_bsl::scenario_seed::{
    EdgeSeed, GraphSeed, HyperedgeSeed, NodeSeed, SeedAttribute, SeedValue,
};
use babylon_graph::stable_element::StableElementKey;
use std::collections::{BTreeMap, BTreeSet};

type Result<T> = std::result::Result<T, EconomicCatalogError>;
fn attribute(field: &str, value: u64) -> Result<SeedAttribute> {
    Ok(SeedAttribute {
        field: field.to_owned(),
        value: SeedValue::Integer(
            i64::try_from(value).map_err(|_| EconomicCatalogError::Arithmetic)?,
        ),
    })
}
fn local<'a>(scope: &str, key: &'a StableElementKey) -> Result<&'a str> {
    key.canonical_bytes()
        .map_err(|_| EconomicCatalogError::Identity)?;
    match key {
        StableElementKey::Node {
            scenario,
            local_name,
        } if scenario == scope => Ok(local_name),
        _ => Err(EconomicCatalogError::Identity),
    }
}
fn node(
    scope: &str,
    key: &StableElementKey,
    kind: &str,
    attributes: Vec<SeedAttribute>,
) -> Result<NodeSeed> {
    Ok(NodeSeed {
        local_name: local(scope, key)?.to_owned(),
        node_type: kind.to_owned(),
        attributes,
    })
}
pub(super) fn national_seed(
    scope: &str,
    opening: &EconomicOpening,
    counties: &NationalCountyReference,
    aid: &crate::national_economy::NationalAidCapture,
    organizer: Option<&babylon_practice_contract::OrganizerConfig>,
) -> Result<GraphSeed> {
    let mut nodes = Vec::new();
    for county in counties.counties() {
        let geoid = county.geoid();
        nodes.push(NodeSeed {
            local_name: format!("county-{geoid}"),
            node_type: "TERRITORY".to_owned(),
            attributes: vec![attribute(
                "territory/county-fips",
                geoid
                    .as_str()
                    .parse()
                    .map_err(|_| EconomicCatalogError::Identity)?,
            )?],
        });
    }
    let pools: BTreeMap<_, _> = opening.staffing.iter().map(|r| (&r.workplace, r)).collect();
    if pools.len() != opening.staffing.len() {
        return Err(EconomicCatalogError::Opening("duplicate workplace memory"));
    }
    let mut sites = BTreeSet::new();
    for site in &opening.sites {
        if !sites.insert(&site.subject) {
            return Err(EconomicCatalogError::Identity);
        }
        let pool = pools
            .get(&site.subject)
            .ok_or(EconomicCatalogError::Opening("absent workplace memory"))?;
        nodes.push(node(
            scope,
            &site.subject,
            "BUSINESS",
            vec![attribute(
                "business/previous-unretained-labor-hours",
                pool.previous_unretained_hours,
            )?],
        )?);
    }
    if sites != pools.keys().copied().collect() {
        return Err(EconomicCatalogError::Opening("extra workplace memory"));
    }
    for household in &opening.households {
        nodes.push(node(
            scope,
            &household.subject,
            "HOUSEHOLD",
            vec![
                attribute("household/persons", household.persons)?,
                attribute("household/households", household.households)?,
            ],
        )?);
    }
    for pool in &opening.staffing {
        for member in &pool.members {
            nodes.push(node(
                scope,
                &member.subject,
                "SOCIAL_CLASS",
                vec![
                    attribute("social-class/employed-population", member.employed)?,
                    attribute("social-class/reserve-population", member.reserve)?,
                ],
            )?);
        }
    }
    append_aid_classes(scope, opening, aid, &mut nodes)?;
    let mut edges = Vec::new();
    let mut hyperedges = Vec::new();
    if let Some(config) = organizer {
        let organizer = organizer_rows(scope, opening, aid, config)?;
        nodes.extend(organizer.nodes);
        edges = organizer.edges;
        hyperedges = organizer.hyperedges;
    }
    GraphSeed::try_new(nodes, edges, hyperedges).map_err(EconomicCatalogError::from)
}

// Recipient classes have no fabricated staffing. Existing donor membership is
// checked against the same captured child before reusing its native node.
fn append_aid_classes(
    scope: &str,
    opening: &EconomicOpening,
    aid: &crate::national_economy::NationalAidCapture,
    nodes: &mut Vec<NodeSeed>,
) -> Result<()> {
    let staffing_keys: BTreeSet<_> = opening
        .staffing
        .iter()
        .flat_map(|pool| &pool.members)
        .map(|member| &member.subject)
        .collect();
    for child in &aid.children {
        if staffing_keys.contains(&child.class_subject) {
            let member = opening
                .staffing
                .iter()
                .flat_map(|pool| &pool.members)
                .find(|member| member.subject == child.class_subject)
                .ok_or(EconomicCatalogError::Identity)?;
            if child.employed == 0
                || member.member.household_id() != child.principal
                || member.employed != child.employed
                || member.reserve != child.reserve
            {
                return Err(EconomicCatalogError::Identity);
            }
            continue;
        }
        if child.employed != 0 || child.reserve != 0 {
            return Err(EconomicCatalogError::Identity);
        }
        nodes.push(node(
            scope,
            &child.class_subject,
            "SOCIAL_CLASS",
            vec![
                attribute("social-class/employed-population", 0)?,
                attribute("social-class/reserve-population", 0)?,
            ],
        )?);
    }
    Ok(())
}

struct OrganizerSeedRows {
    nodes: Vec<NodeSeed>,
    edges: Vec<EdgeSeed>,
    hyperedges: Vec<HyperedgeSeed>,
}
type OrganizerActors = [(u64, &'static str, u64); 5];
fn organizer_rows(
    scope: &str,
    opening: &EconomicOpening,
    aid: &crate::national_economy::NationalAidCapture,
    config: &babylon_practice_contract::OrganizerConfig,
) -> Result<OrganizerSeedRows> {
    validate_organizer_seed(scope, opening, aid, config)?;
    let actors = organizer_actors(config);
    let mut nodes = organization_nodes(&actors)?;
    let names = participant_nodes(aid, config, &mut nodes)?;
    let hyperedges = participant_bodies(&actors, config, &names)?;
    Ok(OrganizerSeedRows {
        nodes,
        edges: ordinary_contacts(),
        hyperedges,
    })
}
fn validate_organizer_seed(
    scope: &str,
    opening: &EconomicOpening,
    aid: &crate::national_economy::NationalAidCapture,
    config: &babylon_practice_contract::OrganizerConfig,
) -> Result<()> {
    babylon_practice_contract::validate_organizer_config(config)
        .map_err(|_| EconomicCatalogError::Identity)?;
    if scope != crate::national_economy::NATIONAL_SCENARIO_ID
        || aid.children.len() != 3
        || config.controlled_actor_id != aid.children[0].actor
        || config.aid_bindings.len() != 2
    {
        return Err(EconomicCatalogError::Identity);
    }
    let workplace = opening
        .sites
        .iter()
        .find(|s| {
            s.processes
                .iter()
                .any(|p| p.process_id.as_bytes() == config.workplace_process_id)
        })
        .ok_or(EconomicCatalogError::Identity)?;
    if !opening
        .employment
        .iter()
        .any(|e| e.site_id == workplace.site_id && e.payee == aid.children[0].principal)
    {
        return Err(EconomicCatalogError::Identity);
    }
    for (binding, child) in config.aid_bindings.iter().zip(&aid.children[1..]) {
        if binding.partner.actor_id != child.actor
            || binding.recipient_principal_id != child.principal.as_bytes()
            || binding.social_class_target
                != babylon_kernel::content_digest::sha256_of(
                    &child
                        .class_subject
                        .canonical_bytes()
                        .map_err(|_| EconomicCatalogError::Identity)?,
                )
        {
            return Err(EconomicCatalogError::Identity);
        }
    }
    Ok(())
}
fn organizer_actors(config: &babylon_practice_contract::OrganizerConfig) -> OrganizerActors {
    [
        (
            config.controlled_actor_id,
            "wayne-organizing-collective",
            26163,
        ),
        (
            config.workplace_partner.actor_id,
            "wayne-workplace-committee",
            26163,
        ),
        (
            config.neighborhood_partner.actor_id,
            "wayne-neighborhood-contact-group",
            26163,
        ),
        (
            config.aid_bindings[0].partner.actor_id,
            "wayne-local-aid-partners",
            26163,
        ),
        (
            config.aid_bindings[1].partner.actor_id,
            "cook-independent-solidarity-partners",
            17031,
        ),
    ]
}
fn organization_nodes(actors: &OrganizerActors) -> Result<Vec<NodeSeed>> {
    let mut nodes = Vec::new();
    for (_, name, county) in actors {
        nodes.push(NodeSeed {
            local_name: (*name).into(),
            node_type: "ORGANIZATION".into(),
            attributes: vec![
                SeedAttribute {
                    field: "organization/kind".into(),
                    value: SeedValue::Enum {
                        enum_type: "OrgKind".into(),
                        member: "CIVIL_SOCIETY".into(),
                    },
                },
                attribute("organization/county-fips", *county)?,
            ],
        });
    }
    Ok(nodes)
}
fn participant_nodes(
    aid: &crate::national_economy::NationalAidCapture,
    config: &babylon_practice_contract::OrganizerConfig,
    nodes: &mut Vec<NodeSeed>,
) -> Result<BTreeMap<u64, String>> {
    let mut participant_names = BTreeMap::new();
    for participant in &config.participants {
        let child = aid
            .children
            .iter()
            .find(|c| c.contributor == participant.contributor_id)
            .ok_or(EconomicCatalogError::Identity)?;
        let babylon_practice_contract::OrganizerTimeBindingMode::Household { bindings } =
            &config.time_binding
        else {
            return Err(EconomicCatalogError::Identity);
        };
        if !bindings.iter().any(|b| {
            b.contributor_id == child.contributor && b.principal_id == child.principal.as_bytes()
        }) {
            return Err(EconomicCatalogError::Identity);
        }
        let name = format!("organizer-contributor-{}", participant.contributor_id);
        participant_names.insert(participant.contributor_id, name.clone());
        nodes.push(NodeSeed {
            local_name: name,
            node_type: "PARTICIPANT_BODY".into(),
            attributes: vec![],
        });
    }
    Ok(participant_names)
}
fn participant_bodies(
    actors: &OrganizerActors,
    config: &babylon_practice_contract::OrganizerConfig,
    participant_names: &BTreeMap<u64, String>,
) -> Result<Vec<HyperedgeSeed>> {
    let mut hyperedges = Vec::new();
    for (actor, name, _) in actors {
        let mut members = vec![(*name).to_owned()];
        for participant in &config.participants {
            if participant.commitments.iter().any(|c| c.actor_id == *actor) {
                members.push(
                    participant_names
                        .get(&participant.contributor_id)
                        .ok_or(EconomicCatalogError::Identity)?
                        .clone(),
                );
            }
        }
        if members.len() < 2 {
            return Err(EconomicCatalogError::Identity);
        }
        hyperedges.push(HyperedgeSeed {
            local_name: format!("organizer-participant-body-{actor}"),
            hyperedge_type: "ORGANIZATION_BODY".into(),
            members,
            attributes: vec![],
        });
    }
    Ok(hyperedges)
}
fn ordinary_contacts() -> Vec<EdgeSeed> {
    // Initial ordinary contacts are captured routine relations. Gift consent
    // creates no contact/agreement with an independent aid partner.
    [
        "wayne-workplace-committee",
        "wayne-neighborhood-contact-group",
    ]
    .into_iter()
    .map(|target| EdgeSeed {
        edge_type: "CONTACT".into(),
        source: "wayne-organizing-collective".into(),
        target: target.into(),
        strength: SeedValue::Integer(1),
        attributes: vec![],
    })
    .collect()
}

#[cfg(test)]
mod organizer_seed_tests {
    use super::*;
    #[test]
    fn shared_contributor_bodies_load_as_native_public_incidence_without_extra_people() {
        let defines = crate::michigan_defines::MichiganDefines::parse(include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../content/scenarios/michigan/defines.toml"
        )))
        .unwrap();
        let mut config = crate::organizer_content::config(
            crate::identity::CampaignId::from_uuid(uuid::Uuid::from_u128(26163)),
            &defines.organizer,
            [7; 32],
        )
        .unwrap();
        let actors: OrganizerActors = [
            (1, "wayne-organizing-collective", 26163),
            (2, "wayne-workplace-committee", 26163),
            (3, "wayne-neighborhood-contact-group", 26163),
            (4, "wayne-local-aid-partners", 26163),
            (5, "cook-independent-solidarity-partners", 17031),
        ];
        let promises = [vec![1, 2], vec![3, 4], vec![5]];
        let mut names = BTreeMap::new();
        let mut nodes = organization_nodes(&actors).unwrap();
        for (participant, actors) in config.participants.iter_mut().zip(promises) {
            participant.commitments = actors
                .into_iter()
                .map(
                    |actor_id| babylon_practice_contract::OrganizerContribution {
                        actor_id,
                        hours: 2,
                    },
                )
                .collect();
            let name = format!("organizer-contributor-{}", participant.contributor_id);
            names.insert(participant.contributor_id, name.clone());
            nodes.push(NodeSeed {
                local_name: name,
                node_type: "PARTICIPANT_BODY".into(),
                attributes: vec![],
            });
        }
        let bodies = participant_bodies(&actors, &config, &names).unwrap();
        assert_eq!(bodies.len(), 5);
        assert!(bodies.iter().all(|body| body.members.len() == 2));
        let occurrences = names
            .values()
            .map(|name| {
                bodies
                    .iter()
                    .filter(|body| body.members.contains(name))
                    .count()
            })
            .collect::<Vec<_>>();
        assert_eq!(occurrences, vec![2, 2, 1]);
        assert_eq!(
            nodes
                .iter()
                .filter(|node| node.node_type == "PARTICIPANT_BODY")
                .count(),
            3
        );
        assert!(nodes.iter().all(|node| !node
            .attributes
            .iter()
            .any(|a| a.field.starts_with("social-class/"))));
        let contacts = ordinary_contacts();
        assert_eq!(contacts.len(), 2);
        assert!(contacts
            .iter()
            .all(|edge| edge.target != "wayne-local-aid-partners"
                && edge.target != "cook-independent-solidarity-partners"));
        let seed = GraphSeed::try_new(nodes, contacts, bodies).unwrap();
        let mut store = babylon_graph::hypergraph_store::HypergraphStore::new();
        let loaded = babylon_bsl::scenario_seed::load_scenario_with_seed(
            include_str!(concat!(
                env!("CARGO_MANIFEST_DIR"),
                "/../../../content/scenarios/national/structure.bscn"
            )),
            None,
            &seed,
            &mut store,
        )
        .unwrap();
        assert_eq!(loaded.id, crate::national_economy::NATIONAL_SCENARIO_ID);
        let missing = BTreeMap::new();
        assert!(matches!(
            participant_bodies(&actors, &config, &missing),
            Err(EconomicCatalogError::Identity)
        ));
    }
}
