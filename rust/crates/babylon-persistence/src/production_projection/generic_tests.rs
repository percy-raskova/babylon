//! The public observer consumes the captured common compiler, including controls.
use super::{history::OrderHistory, project_economic_current, ProductionProjectionError};
use crate::{economic_catalog::CapturedEconomicCatalog, michigan_economy::digest_hex};
use babylon_tick::material_world::MaterialWorldRegister;

#[test]
fn actual_captured_control_projects_from_common_opening_and_source_identity() {
    let source = CapturedEconomicCatalog::from_michigan(&crate::test_support::catalog()).unwrap();
    let compiled = source.view().opening.compile().unwrap();
    let register = MaterialWorldRegister::try_new(0, compiled.state).unwrap();
    let history = OrderHistory::from_opening(register.state()).unwrap();
    let view = source.view();
    let snapshot = project_economic_current(view, &register, None, None, &history).unwrap();
    assert_eq!(
        snapshot.content_authority_sha256,
        digest_hex(&view.source_digest)
    );
    assert_eq!(snapshot.sites.len(), view.opening.sites.len());
    assert_eq!(
        snapshot.routes.len(),
        view.opening.logistics.supplier_routes.len()
    );
    assert!(snapshot.routes.iter().any(|r| r.ordered > 0));
    assert!(snapshot.sites.iter().all(|r| !r.roles.is_empty()));
    let mut forged = view.opening.clone();
    forged.sites[0].site_id = babylon_material_circuit::SiteId::from_bytes([237; 32]);
    let mut bad_view = view;
    bad_view.opening = &forged;
    assert!(matches!(
        project_economic_current(bad_view, &register, None, None, &history),
        Err(ProductionProjectionError::Content | ProductionProjectionError::State)
    ));
}

#[test]
fn native_source_view_keeps_foreign_scope_and_suppressed_jobs_without_michigan_labels() {
    use crate::economic_catalog::{EconomicSiteSource, EconomicSourceView};
    let source = CapturedEconomicCatalog::from_michigan(&crate::test_support::catalog()).unwrap();
    let mut opening = source.view().opening.clone();
    for site in &mut opening.sites {
        site.source = EconomicSiteSource::Designed {
            key: "bounded-projection-control".into(),
        };
    }
    let cohorts = crate::national_cohorts::national_cohort_reference().unwrap();
    let observed = cohorts
        .admitted_cohorts()
        .find(|r| r.jobs().missing_members() > 0)
        .unwrap();
    opening.sites[0].source = EconomicSiteSource::Qcew(observed.key());
    opening.sites[0].location =
        babylon_kernel::economic_location::EconomicLocation::domestic_county(observed.key().county)
            .unwrap();
    opening.sites[0].function = observed.key().function.unwrap();
    opening.sites[1].location = "foreign:canada".parse().unwrap();
    let compiled = opening.compile().unwrap();
    let register = MaterialWorldRegister::try_new(0, compiled.state).unwrap();
    let history = OrderHistory::from_opening(register.state()).unwrap();
    let mut view = source.view();
    view.opening = &opening;
    view.sources = EconomicSourceView::National {
        counties: crate::national_counties::national_county_reference().unwrap(),
        cohorts,
        residents: crate::national_resident_workforce::national_resident_workforce_reference()
            .unwrap(),
        world: crate::world_reference::world_reference().unwrap(),
        transport: crate::national_transport::national_transport_reference().unwrap(),
    };
    let snapshot = project_economic_current(view, &register, None, None, &history).unwrap();
    let domestic = snapshot
        .sites
        .iter()
        .find(|r| r.id == digest_hex(&opening.sites[0].site_id.as_bytes()))
        .unwrap();
    assert!(domestic.is_in_county(observed.key().county.as_str()));
    assert_eq!(domestic.observed_employment, None);
    assert!(domestic.industry_code.is_none() && domestic.sector_code.is_none());
    let foreign = snapshot
        .sites
        .iter()
        .find(|r| r.id == digest_hex(&opening.sites[1].site_id.as_bytes()))
        .unwrap();
    assert_eq!(foreign.location, "foreign:canada".parse().unwrap());
    assert!(foreign.county_geoid().is_none() && foreign.industry_code.is_none());
    assert!(snapshot.road_source.is_none() && snapshot.physical_edges.is_empty());
}
