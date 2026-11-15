//! Labor scopes come from the admitted economic opening, including campaigns without cash postings.
use super::labor_facts::LaborFacts;
use crate::economic_content::EconomicContentAdmission;
use crate::michigan_content::MichiganContentPreset;
use crate::michigan_material::MichiganDeliveryPreset;
use crate::recorded_labor::{
    LaborBasis, LaborEdge, LaborId, LaborNode, LaborReceiptFamily, ReceiptRef, RecordedAsset,
    RecordedAssetIdentity, RecordedLaborPeriod,
};
use crate::test_support;

#[test]
fn actual_site_geography_and_unlocated_freight_have_distinct_sql_nodes() {
    let built = MichiganContentPreset::new_campaign(MichiganDeliveryPreset::Standard)
        .create_foundation(&test_support::catalog())
        .expect("captured small campaign");
    let foundation =
        EconomicContentAdmission::from_foundation(built).expect("validated economic opening");
    let first = &foundation.view().opening.sites[0];
    let dest = &foundation.view().opening.sites[1];
    let output = &foundation.material_catalog().process_outputs[0];
    let site = LaborId(first.site_id.as_bytes());
    let good = LaborId(output.good_id.as_bytes());
    let unit = LaborId(output.unit_id.as_bytes());
    // Use the same ID bytes in two namespaces. Only the site has a captured operating location.
    let storage = LaborNode::SiteStock { site, good, unit };
    let transit = LaborNode::Freight { lot: site };
    let report = RecordedLaborPeriod {
        period: 1,
        opening_recorded_micro_hours: 0,
        closing_recorded_micro_hours: 0,
        released_micro_hours: 0,
        direct_micro_hours: 0,
        attendance: vec![],
        household_time: vec![],
        opening_positions: vec![],
        closing_positions: vec![],
        edges: vec![LaborEdge {
            source: storage,
            destination: transit,
            quantity: u64::MAX,
            basis: LaborBasis {
                recorded_micro_hours: u128::MAX,
                unknown_opening: true,
            },
            receipt: ReceiptRef {
                family: LaborReceiptFamily::Dispatches,
                ordinal: 2,
            },
        }],
        assets: vec![RecordedAsset {
            node: transit,
            identity: RecordedAssetIdentity::CommercialFreight {
                source_site: site,
                destination_site: LaborId(dest.site_id.as_bytes()),
                order: LaborId([1; 32]),
                route: LaborId([2; 32]),
                good,
                unit,
            },
        }],
    };
    let mut facts = LaborFacts::from_report(&foundation, &report).expect("normalized scope");
    assert_eq!(facts.nodes.len(), 2);
    let movement = &facts.movements[0];
    let source = &facts.nodes[usize::try_from(movement.source_node).expect("site ordinal")];
    let freight = &facts.nodes[usize::try_from(movement.destination_node).expect("lot ordinal")];
    assert_eq!(source.scope_kind, Some("site_cash"));
    assert_eq!(
        source.location_key.as_deref(),
        Some(first.location.to_string().as_str())
    );
    assert_eq!(
        source.industry_key.as_deref(),
        Some(first.function.source_key())
    );
    assert_eq!(freight.entity_id, source.entity_id);
    assert_eq!(freight.origin_id, Some(site));
    assert!(freight.location_key.is_none() && freight.scope_id.is_none());
    let wire = serde_json::to_value(movement).expect("wire");
    assert_eq!(
        wire["quantity"].as_str(),
        Some(u64::MAX.to_string().as_str())
    );
    assert_eq!(
        wire["recorded_micro_hours"].as_str(),
        Some(u128::MAX.to_string().as_str())
    );
    let digest = facts.fingerprint().expect("source digest");
    facts.movements[0].unknown_opening = false;
    assert_ne!(digest, facts.fingerprint().expect("changed provenance"));
}
