//! Native instances use the ordinary BSL declaration/type admission path.
use super::{EconomicCatalogError, EconomicOpening};
use crate::national_counties::NationalCountyReference;
use babylon_bsl::scenario_seed::{GraphSeed, NodeSeed, SeedAttribute, SeedValue};
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
    GraphSeed::try_new(nodes, vec![], vec![]).map_err(EconomicCatalogError::from)
}
