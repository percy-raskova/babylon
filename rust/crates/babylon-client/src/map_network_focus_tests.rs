use super::super::tests::fixture;
use super::*;

#[test]
fn county_network_keeps_direct_counterparts_and_local_isolates_but_not_second_hops() {
    let (session, mut frame, anchors) = fixture();
    let snapshot = frame.0.as_mut().unwrap().production.as_mut().unwrap();
    let mut second_hop = snapshot.sites[1].clone();
    second_hop.id = "second-hop".into();
    second_hop.location = "county:26161".parse().unwrap();
    for input in &mut second_hop.processes[0].inputs {
        input.supplier_site_ids = vec!["b".into()];
    }
    let mut isolate = snapshot.sites[0].clone();
    isolate.id = "local-isolate".into();
    snapshot.sites.extend([second_hop, isolate]);
    let result = project_network(
        &frame,
        &session,
        &anchors,
        Some(1),
        NetworkSector::All,
        None,
    );
    assert_eq!(result.total_cohorts, 5);
    assert_eq!(result.total_links, 4);
    assert_eq!(result.links.len(), 2);
    assert_eq!(
        result.nodes.keys().cloned().collect::<BTreeSet<_>>(),
        ["a", "b", "local-isolate"]
            .into_iter()
            .map(|id| NodeKey::Site(id.into()))
            .collect()
    );
    assert!(heading(&result, NetworkSector::All).contains("3 / 5 disclosed cohorts"));
    let other = project_network(
        &frame,
        &session,
        &anchors,
        Some(2),
        NetworkSector::All,
        None,
    );
    assert!(other
        .nodes
        .contains_key(&NodeKey::Site("second-hop".into())));
    assert!(!other
        .nodes
        .contains_key(&NodeKey::Site("local-isolate".into())));
}

#[test]
fn foreign_direct_counterpart_has_an_explicit_peer_and_no_county_geometry() {
    let (session, mut frame, anchors) = fixture();
    let snapshot = frame.0.as_mut().unwrap().production.as_mut().unwrap();
    let mut foreign = snapshot.sites[1].clone();
    foreign.id = "canada".into();
    foreign.name = "Canadian equipment producer".into();
    foreign.location = "foreign:canada".parse().unwrap();
    let mut imports = foreign.processes[0].inputs[0].clone();
    imports.supplier_site_ids = vec![foreign.id.clone()];
    snapshot.sites[0].processes[0].inputs.push(imports);
    snapshot.sites.push(foreign);
    let result = project_network(
        &frame,
        &session,
        &anchors,
        Some(1),
        NetworkSector::All,
        None,
    );
    assert_eq!(result.external.len(), 1);
    assert_eq!(
        result.external[&NodeKey::Site("canada".into())].site_id,
        "canada"
    );
    assert!(result.external[&NodeKey::Site("canada".into())]
        .caption
        .contains("foreign:canada"));
    let caption = &result.external[&NodeKey::Site("canada".into())].caption;
    assert!(caption.contains("Supplies"));
    assert!(caption.contains("Buys from"));
    assert!(caption.contains("steel / kg"));
    assert!(caption.contains("ore / tonne"));
    assert!(!result.nodes.contains_key(&NodeKey::Site("canada".into())));
    assert_eq!(result.links.len(), 5);
    assert_eq!(result.total_links, 5);
    assert_eq!(result.nodes.len(), 2);
    assert!(heading(&result, NetworkSector::All).contains("1 counterparts listed outside this map"));
    assert!(frame
        .0
        .as_ref()
        .unwrap()
        .production
        .as_ref()
        .unwrap()
        .routes
        .is_empty());
}

#[test]
fn household_service_needs_are_visible_without_fabricating_retail_orders() {
    let (session, mut frame, anchors) = fixture();
    let snapshot = frame.0.as_mut().unwrap().production.as_mut().unwrap();
    snapshot.household_service_accounts.push(
        babylon_persistence::ProductionHouseholdServiceAccount {
            kind: babylon_persistence::ProductionHouseholdKind::Ordinary,
            demand_principal_id: "household".into(),
            location: "county:26163".parse().unwrap(),
            good_id: "care".into(),
            unit_id: "service-hour".into(),
            good: "Care".into(),
            unit: "service-hour".into(),
            household_count: 2,
            person_count: 4,
            provider_site_ids: vec!["a".into()],
            required_per_period: 8,
            completed: None,
        },
    );
    let result = project_network(
        &frame,
        &session,
        &anchors,
        Some(1),
        NetworkSector::All,
        None,
    );
    assert!(result
        .nodes
        .contains_key(&NodeKey::EndBuyers("26163".into())));
    assert!(result
        .links
        .iter()
        .any(|link| link.to == NodeKey::EndBuyers("26163".into())
            && matches!(&link.kind, NetworkLinkKind::Commodity {good, ..} if good == "care")));
    assert_eq!(result.total_links, 3);
    assert!(frame
        .0
        .as_ref()
        .unwrap()
        .production
        .as_ref()
        .unwrap()
        .final_demand_accounts
        .is_empty());
}
