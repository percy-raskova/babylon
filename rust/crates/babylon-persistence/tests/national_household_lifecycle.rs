//! Source admission and two actual four-week national campaign closes at the normal seed.
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_kernel::geography::CountyGeoid;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_material_circuit::HouseholdTimeAccounting;
use babylon_persistence::economic_catalog::{
    self, CapturedEconomicCatalog, EconomicCatalogError, SourceArtifactKind,
};
use babylon_persistence::identity::CampaignId;
use babylon_persistence::national_economy;
use babylon_persistence::national_household_allocation::HouseholdBudgetKey;
use babylon_tick::material_world;
use babylon_tick::replay_session::ReplayCommitDisposition;
use std::collections::BTreeMap;
use uuid::Uuid;

#[test]
fn provisional_policy_without_initial_age_distribution_is_refused() {
    let current = include_str!("../../../../content/scenarios/national/defines.toml");
    let field = "initial_age_distribution = \"uniform_remaining_birthdays\"";
    assert!(current.contains(field));
    assert!(national_economy::NationalGamePolicy::parse(current).is_ok());
    assert!(national_economy::NationalGamePolicy::parse(&current.replace(field, "")).is_err());
}

#[test]
fn new_national_campaign_requires_its_age_source() {
    let mut input = economic_catalog::national_catalog_input();
    input
        .sources
        .retain(|s| s.kind() != SourceArtifactKind::NationalAges);
    assert!(matches!(
        CapturedEconomicCatalog::capture(input, None),
        Err(EconomicCatalogError::Source(
            SourceArtifactKind::NationalAges
        ))
    ));
}

fn check_opening(capture: &CapturedEconomicCatalog) {
    let households = &capture.opening().households;
    let HouseholdTimeAccounting::Modeled(time) = &capture.opening().policies.household_time else {
        panic!("modeled national household time")
    };
    let positions = &time
        .lifecycle
        .as_ref()
        .expect("dated opening ages")
        .positions;
    assert_eq!(positions.len(), households.len());
    let mut domestic = [0_u64; 4];
    let eligible: BTreeMap<_, _> = capture
        .opening()
        .policies
        .household_time_policy
        .iter()
        .map(|p| (p.principal_id, p.eligible_persons))
        .collect();
    let mut external = 0;
    for household in households {
        let position = positions
            .binary_search_by_key(&household.principal_id, |p| p.principal_id)
            .expect("every principal");
        let ages = positions[position].ages;
        assert_eq!(ages.persons().expect("resident count"), household.persons);
        assert_eq!(
            ages.eligible().expect("eligible residents"),
            eligible[&household.principal_id]
        );
        match household.location {
            EconomicLocation::County(_) => {
                for (sum, n) in domestic.iter_mut().zip([
                    ages.under_16,
                    ages.age_16_17,
                    ages.age_18_64,
                    ages.age_65_plus,
                ]) {
                    *sum += n;
                }
            }
            EconomicLocation::Foreign(_) | EconomicLocation::Dependency(_) => {
                external += 1;
            }
        }
    }
    assert_eq!(domestic, [64_740_863, 8_776_971, 203_771_037, 57_633_628]);
    assert!(external > 0);
}

#[test]
fn dated_national_world_wayne_residents_change_the_next_food_requirement() {
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x2616_3024));
    let capture = CapturedEconomicCatalog::capture_national_campaign(
        economic_catalog::national_catalog_input(),
        campaign,
    )
    .expect("playable national world, organizer and City PD");
    assert_eq!(capture.compiler_version(), "national-world-v10");
    check_opening(&capture);
    let wayne =
        EconomicLocation::domestic_county(CountyGeoid::try_from("26163").expect("Wayne County"))
            .expect("domestic county");
    let principal =
        national_economy::household_principal(wayne, HouseholdBudgetKey::EarningNonowner);
    let food = capture
        .opening()
        .commodity_labels
        .iter()
        .find(|c| c.key == "food")
        .expect("food")
        .good_id;
    let mut live = capture
        .create_foundation(
            ReplaySessionId::try_from("national-world").expect("stable campaign"),
            ReplaySeed::new(319),
        )
        .expect("foundation")
        .into_session()
        .expect("material session");
    let mut previous = None;
    for period in 1..=2 {
        let actions = babylon_practice_contract::organizer_action_batch(
            live.material()
                .organizer_config()
                .expect("admitted organizer config"),
            live.material()
                .organizer_state()
                .expect("current organizer state"),
            None,
            live.graph_session().session_identity().clone(),
        )
        .expect("ordinary no-command organizer action batch");
        assert_eq!(actions.resolve_tick(), period);
        let candidate = live
            .prepare_advance(&actions)
            .expect("ordinary national close");
        let receipts =
            material_world::decode_material_receipts(candidate.material().receipt_bytes())
                .expect("canonical material receipts");
        let flow = receipts
            .household_lifecycle
            .iter()
            .find(|r| r.principal_id == principal)
            .expect("Wayne earning nonowner population");
        let demand = receipts
            .household_demand
            .iter()
            .find(|r| r.principal_id == principal && r.good_id == food)
            .expect("Wayne food order");
        let consumption = receipts
            .household_consumption
            .iter()
            .find(|r| r.principal_id == principal && r.good_id == food)
            .expect("Wayne food consumption");
        assert_eq!(
            demand.required_quantity,
            flow.opening.persons().expect("opening residents")
        );
        assert_eq!(consumption.required_quantity, demand.required_quantity);
        assert_eq!(
            consumption.consumed_quantity + consumption.unmet_quantity,
            consumption.required_quantity
        );
        assert!(
            demand.fulfilled_quantity <= demand.admitted_quantity
                && demand.admitted_quantity <= demand.requested_quantity
        );
        if let Some(closing) = previous {
            assert_eq!(flow.opening, closing);
        }
        assert_ne!(flow.opening.persons(), flow.closing.persons());
        assert!(flow.births > 0 && flow.deaths.persons().expect("actual deaths") > 0);
        eprintln!("Wayne County earning nonowner P{period} lifecycle={flow:?} food={demand:?} consumption={consumption:?}");
        previous = Some(flow.closing);
        live.commit_prepared_and_publish(&mut CollectingSink::default(), candidate, |_, _| {
            Ok::<_, &str>(ReplayCommitDisposition::Committed)
        })
        .expect("publish actual close");
    }
}
