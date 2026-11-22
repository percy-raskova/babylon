//! Explicit shipped-content fixture for native unit tests only.
use crate::michigan_material::MichiganMaterialCatalog;
use babylon_tick::material_world::MaterialTickReceipts;

pub(crate) fn catalog() -> MichiganMaterialCatalog {
    MichiganMaterialCatalog::from_defines_toml(
        &include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../content/scenarios/michigan/defines.toml"
        ))
        .replace(
            "DURATION = { kind = \"continuous\" }",
            "DURATION = { kind = \"finite\", final_period = 16 }",
        ),
    )
    .expect("shipped numeric material fixture")
}

/// Local names of the two counties the membership fixture's hyperedge joins.
pub(crate) const MEMBERSHIP_COUNTIES: [&str; 2] = ["county-26163", "county-26125"];
/// Qualified name of the membership field the fixture declares.
pub(crate) const MEMBERSHIP_QNAME: &str = "economic-sector/weight";

/// The shipped catalog with one membership field and one hyperedge whose two
/// members carry values (7 and -3), authored as a replacement graph
/// declarations artifact: the way content reaches a campaign, nothing else.
pub(crate) fn catalog_with_membership_values() -> MichiganMaterialCatalog {
    use crate::economic_catalog::{SourceArtifact, SourceArtifactKind};
    let mut catalog = catalog();
    let shipped = catalog
        .captured_sources()
        .iter()
        .find(|source| source.kind() == SourceArtifactKind::GraphDeclarations)
        .map(|source| String::from_utf8(source.bytes().to_vec()))
        .expect("the shipped catalog captures its graph declarations")
        .expect("the shipped declarations are text");
    let authored = format!(
        "{shipped}\n  (deffield {MEMBERSHIP_QNAME} int extensive :member NodeType/TERRITORY)\n  \
         (hyperedge membership-proof HyperedgeType/ECONOMIC_SECTOR (members\n    \
         (member NodeType/TERRITORY {a} ({MEMBERSHIP_QNAME} 7))\n    \
         (member NodeType/TERRITORY {b} ({MEMBERSHIP_QNAME} -3))))\n",
        a = MEMBERSHIP_COUNTIES[0],
        b = MEMBERSHIP_COUNTIES[1],
    );
    catalog
        .source_inputs
        .retain(|source| source.kind() != SourceArtifactKind::GraphDeclarations);
    catalog.source_inputs.push(SourceArtifact::capture(
        SourceArtifactKind::GraphDeclarations,
        authored.into_bytes(),
    ));
    catalog.source_inputs.sort_by_key(SourceArtifact::kind);
    catalog
}

pub(crate) fn material_receipts(period: u64) -> MaterialTickReceipts {
    MaterialTickReceipts {
        agency_paid: vec![],
        household_time: vec![],
        household_lifecycle: vec![],
        resident_workforce_attrition: vec![],
        aid: vec![],
        collections: vec![],
        installation: vec![],
        installation_decisions: vec![],
        equipment_wear: vec![],
        investment: vec![],
        staffing_members: vec![],
        member_labor_use: vec![],
        public_budgets: vec![],
        taxes: vec![],
        distributions: vec![],
        company_basis: vec![],
        company_distributions: vec![],
        contributions: vec![],
        service_performance: vec![],
        household_services: vec![],
        service_markets: vec![],
        service_outputs: vec![],
        income: vec![],
        resolve_tick: period,
        household_demand: vec![],
        household_consumption: vec![],
        procurement: vec![],
        production_plans: vec![],
        prices: vec![],
        money_transfers: vec![],
        wage_accruals: vec![],
        labor_use: vec![],
        production: vec![],
        dispatches: vec![],
        losses: vec![],
        arrivals: vec![],
        deliveries: vec![],
        realizations: vec![],
        handling: vec![],
        local_fulfillments: vec![],
        local_transfers: vec![],
        maintenance: None,
    }
}
