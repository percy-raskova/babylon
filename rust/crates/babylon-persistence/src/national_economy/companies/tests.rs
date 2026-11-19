//! Whole-site occupancy and cohort-source eligibility survive coarse opening grain.
use super::assign::{self, Site};
use super::{CensusDivision, CompanyBand, CompanyCapture, CompanyCaptureError, EmploymentTargets};
use babylon_kernel::economic_identity::EconomicFunction;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::SiteId;
use std::collections::BTreeMap;

fn site(id: u8, employed: u64, division: CensusDivision) -> Site {
    Site {
        id: SiteId::from_bytes([id; 32]),
        function: EconomicFunction::Food,
        county: match division {
            CensusDivision::NewEngland => "09001",
            CensusDivision::MiddleAtlantic => "36001",
            CensusDivision::EastNorthCentral => "26001",
            CensusDivision::WestNorthCentral => "27001",
            CensusDivision::SouthAtlantic => "24001",
            CensusDivision::EastSouthCentral => "01001",
            CensusDivision::WestSouthCentral => "48001",
            CensusDivision::Mountain => "04001",
            CensusDivision::Pacific => "06001",
        }
        .try_into()
        .expect("county"),
        employed,
    }
}

#[test]
fn whole_sites_keep_all_companies_occupied_when_a_large_site_overshoots() {
    let targets = EmploymentTargets::try_new([3500, 3500, 3000]).expect("designed shares");
    let mut sites: Vec<_> = CensusDivision::ALL
        .into_iter()
        .enumerate()
        .map(|(i, d)| site(u8::try_from(i + 1).expect("bounded division"), 1, d))
        .collect();
    sites.extend([
        site(12, 80, CensusDivision::NewEngland),
        site(13, 19, CensusDivision::NewEngland),
    ]);
    let plan = assign::for_function(EconomicFunction::Food, &sites, targets)
        .expect("nine regions and two nationals");
    sites.reverse();
    assert_eq!(
        plan,
        assign::for_function(EconomicFunction::Food, &sites, targets).expect("same sites")
    );
    assert_eq!(plan.members.len(), 11);
    assert_eq!(plan.companies.len(), 11);
    assert!(plan.companies.iter().all(|company| company.employed > 0));
    let cell = plan
        .cells
        .iter()
        .find(|c| c.division == CensusDivision::NewEngland)
        .expect("first division");
    assert_eq!(cell.eligible_employed, 100);
    assert_eq!(cell.assigned_employed.iter().sum::<u64>(), 100);
    assert!(cell.assigned_employed.contains(&80));
    assert!(plan
        .members
        .iter()
        .any(|m| m.site == SiteId::from_bytes([12; 32]) && m.employed == 80));
    let regional = plan
        .companies
        .iter()
        .filter(|company| matches!(company.key.band, CompanyBand::Regional(_)))
        .count();
    assert_eq!(regional, 9);
    sites.retain(|s| s.id != SiteId::from_bytes([13; 32]));
    assert_eq!(
        assign::for_function(EconomicFunction::Food, &sites, targets),
        Err(CompanyCaptureError::TooFewOperatingSites(
            EconomicFunction::Food
        ))
    );
}

#[test]
fn representative_private_ownership_requires_qcew_source_kind() {
    use super::capture;
    use crate::national_economy::grain::{
        CatchmentId, RepresentativeWorkplaceKey, ReservePosition, ResidentWorkplaceSourceKind,
    };
    use crate::national_economy::identity;
    use babylon_kernel::economic_identity::QcewOwnership;
    let county = "26163".try_into().expect("fixed county");
    let location = EconomicLocation::domestic_county(county).expect("domestic");
    let mut key = RepresentativeWorkplaceKey {
        catchment: CatchmentId([7; 32]),
        position: ReservePosition::AtCellReserveRate,
        function: EconomicFunction::HouseholdServices,
        ownership: QcewOwnership::Private,
        source_kind: ResidentWorkplaceSourceKind::HouseholdEnterprise,
    };
    let make = |key| identity::representative_workplace(key, location);
    assert_eq!(capture::eligible_county(&make(key)), Ok(None));
    key.source_kind = ResidentWorkplaceSourceKind::ResidentEmployerFallback;
    assert_eq!(capture::eligible_county(&make(key)), Ok(None));
    key.source_kind = ResidentWorkplaceSourceKind::Qcew;
    assert_eq!(capture::eligible_county(&make(key)), Ok(Some(county)));
    key.ownership = QcewOwnership::LocalGovernment;
    assert_eq!(capture::eligible_county(&make(key)), Ok(None));
}

#[test]
fn one_site_divisions_preserve_achieved_zero_national_shares() {
    let targets = EmploymentTargets::try_new([3500, 3500, 3000]).expect("designed shares");
    let mut sites: Vec<_> = CensusDivision::ALL
        .into_iter()
        .enumerate()
        .map(|(i, d)| site(u8::try_from(i + 1).expect("division"), 1, d))
        .collect();
    sites.extend([
        site(12, 1, CensusDivision::MiddleAtlantic),
        site(13, 1, CensusDivision::Mountain),
    ]);
    let plan =
        assign::for_function(EconomicFunction::Food, &sites, targets).expect("sparse but feasible");
    assert_eq!(plan.companies.len(), 11);
    assert_eq!(plan.cells[0].assigned_employed, [0, 0, 1]);
    assert_eq!(plan.members.len(), 11);
}

fn synthetic_base() -> CompanyCapture {
    let mut rows = Vec::new();
    for (i, division) in CensusDivision::ALL.into_iter().enumerate() {
        for n in 0..40_usize {
            let mut row = site(0, u64::try_from(n + 1).expect("fixture"), division);
            let mut id = [0; 32];
            id[..8].copy_from_slice(&u64::try_from(i * 40 + n).expect("fixture").to_be_bytes());
            row.id = SiteId::from_bytes(id);
            rows.push(row);
        }
    }
    assign::for_function(
        EconomicFunction::Food,
        &rows,
        EmploymentTargets::try_new([3500, 3500, 3000]).expect("source"),
    )
    .expect("eleven occupied source strata")
}

#[test]
fn experimental_controllers_split_only_whole_occupied_sites_within_their_original_stratum() {
    use super::{scale, ExperimentalPopulation};
    let base = synthetic_base();
    let mut reverse = base.clone();
    reverse.members.reverse();
    let experiment = scale::partition(base.clone(), ExperimentalPopulation::ThreeHundred)
        .expect("enough whole sites");
    let reordered =
        scale::partition(reverse, ExperimentalPopulation::ThreeHundred).expect("same inputs");
    assert_eq!(experiment, reordered);
    assert_eq!(experiment.companies.len(), 300);
    assert!(experiment.companies.iter().all(|r| r.employed > 0));
    assert_eq!(experiment.cells, base.cells);
    let membership: BTreeMap<_, _> = base.members.iter().map(|r| (r.site, r)).collect();
    for m in &experiment.members {
        let original = membership[&m.site];
        assert_eq!(
            (m.company.function, m.company.band, m.county, m.employed),
            (
                original.company.function,
                original.company.band,
                original.county,
                original.employed
            )
        );
        assert!(m.company.experiment_partition.is_some());
    }
    assert!(matches!(
        scale::partition(base, ExperimentalPopulation::SixHundred),
        Err(CompanyCaptureError::ControllerCapacity { requested: 600, .. })
    ));
}
