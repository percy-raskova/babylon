//! Source-conserving, Designed opening refinements for real household gifts.
use super::{actors, routes, Builder, NationalOpeningError as Error, Result};
use crate::{
    national_economy::{household_principal, NATIONAL_SCENARIO_ID},
    national_household_allocation::{HouseholdBudgetKey as Key, NationalHouseholdAllocation},
    national_household_time_allocation::NationalHouseholdTimeAllocation,
    national_resident_allocation::{ResidentAttendanceMode, ResidentWorkplaceAllocation},
};
use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::{
    content_digest::sha256_of, currency::Currency, economic_location::EconomicLocation,
    geography::CountyGeoid,
};
use babylon_material_circuit::{
    AccountId, AidMandate, AidTransport, CashAccount, FinalDemandPrincipalId, InstitutionLocation,
    OrganizationAccountId, StaffingMemberBinding, StaffingMemberId,
};

/// All child margins subtract from an exact captured nonowner budget.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AidChildCapture {
    pub principal: FinalDemandPrincipalId,
    pub parent: FinalDemandPrincipalId,
    pub location: EconomicLocation,
    pub budget: Key,
    pub subject: StableElementKey,
    pub class_subject: StableElementKey,
    pub persons: u64,
    pub households: u64,
    pub employed: u64,
    pub reserve: u64,
    pub eligible: u64,
    pub armed: u64,
    pub inactive: u64,
    pub under16: u64,
    pub actor: u64,
    pub contributor: u64,
}
/// Exact immutable metadata; downstream admission must consume every mandate.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct NationalAidCapture {
    pub source_hash: [u8; 32],
    pub children: Vec<AidChildCapture>,
    pub mandates: Vec<AidMandate>,
}
fn location(county: &str) -> Result<EconomicLocation> {
    let county = CountyGeoid::try_from(county).map_err(|_| Error::SourceScope)?;
    EconomicLocation::domestic_county(county).map_err(|_| Error::SourceScope)
}
fn subject(label: &str) -> StableElementKey {
    StableElementKey::Node {
        scenario: NATIONAL_SCENARIO_ID.into(),
        local_name: label.into(),
    }
}
fn principal(label: &str) -> FinalDemandPrincipalId {
    let mut bytes = b"NationalAidHouseholdV1\0".to_vec();
    bytes.extend_from_slice(label.as_bytes());
    FinalDemandPrincipalId::from_bytes(sha256_of(&bytes))
}
fn child(builder: &Builder<'_>, label: &str, county: &str, donor: bool) -> Result<AidChildCapture> {
    let location = location(county)?;
    let budget = if donor {
        Key::EarningNonowner
    } else {
        Key::NoEarnerNonowner
    };
    let policy = &builder.policy.aid;
    let (actor, contributor) = match label {
        "wayne-aid-donor" => (policy.donor_actor, policy.donor_contributor_id),
        "wayne-aid-recipient" => (
            policy.local_recipient_actor,
            policy.local_recipient_contributor_id,
        ),
        "cook-aid-recipient" => (
            policy.remote_recipient_actor,
            policy.remote_recipient_contributor_id,
        ),
        _ => return Err(Error::Identity),
    };
    Ok(AidChildCapture {
        principal: principal(label),
        parent: household_principal(location, budget),
        location,
        budget,
        subject: subject(label),
        class_subject: subject(&format!("{label}-inactive")),
        persons: if donor { 8 } else { 4 },
        households: 4,
        employed: if donor { 4 } else { 0 },
        reserve: 0,
        eligible: if donor { 8 } else { 4 },
        armed: 0,
        inactive: 4,
        under16: 0,
        actor,
        contributor,
    })
}
pub(super) fn prepare(
    builder: &mut Builder<'_>,
    budgets: &NationalHouseholdAllocation,
    time: &NationalHouseholdTimeAllocation,
    allocation: &mut ResidentWorkplaceAllocation,
    source_hash: [u8; 32],
) -> Result<()> {
    if source_hash == [0; 32] {
        return Err(Error::Identity);
    }
    let mut children = vec![
        child(builder, "wayne-aid-donor", "26163", true)?,
        child(builder, "wayne-aid-recipient", "26163", false)?,
        child(builder, "cook-aid-recipient", "17031", false)?,
    ];
    validate_child_margins(builder, budgets, time, &children)?;
    retarget(allocation, &mut children[0], builder.policy)?;
    let payer = AccountId::Organization(OrganizationAccountId::from_bytes(sha256_of(
        b"NationalWayneAidOrganizationV1\0",
    )));
    let food = builder.commodity("food")?;
    let policy = &builder.policy.aid;
    let remote_route = routes::route_id(
        children[0].location,
        children[2].location,
        crate::national_transport::CargoClass::General,
    );
    let mut mandates = Vec::new();
    for recipient in &children[1..] {
        let transport = if recipient.location == children[0].location {
            AidTransport::Local
        } else {
            AidTransport::Routed {
                route_id: remote_route,
                from_node_id: *builder
                    .logistics_nodes
                    .get(&children[0].location)
                    .ok_or(Error::Route)?,
                to_node_id: *builder
                    .logistics_nodes
                    .get(&recipient.location)
                    .ok_or(Error::Route)?,
            }
        };
        let mut bytes = b"NationalAidMandateV1\0".to_vec();
        bytes.extend_from_slice(&source_hash);
        bytes.extend_from_slice(&recipient.principal.as_bytes());
        mandates.push(AidMandate {
            id: sha256_of(&bytes),
            source_hash,
            donor_actor: children[0].actor,
            donor_contributor_id: children[0].contributor,
            recipient_actor: recipient.actor,
            payer,
            donor: children[0].principal,
            recipient: recipient.principal,
            good_id: food.good_id,
            unit_id: food.unit_id,
            labor_unit_id: builder.labor_unit,
            hours_per_unit: policy.fulfillment_hours_per_unit,
            maximum_quantity: policy.maximum_quantity,
            cash_per_unit: Currency::from_micro_units(policy.gift_cash_micros_per_unit),
            transport,
        });
    }
    builder.aid = NationalAidCapture {
        source_hash,
        children,
        mandates,
    };
    Ok(())
}
fn validate_child_margins(
    builder: &mut Builder<'_>,
    budgets: &NationalHouseholdAllocation,
    time: &NationalHouseholdTimeAllocation,
    children: &[AidChildCapture],
) -> Result<()> {
    for row in children {
        let EconomicLocation::County(county) = row.location else {
            return Err(Error::SourceScope);
        };
        let budget = budgets
            .county(county.geoid())
            .map_err(Error::Households)?
            .budgets()
            .iter()
            .find(|b| b.key == row.budget)
            .ok_or(Error::Identity)?;
        let ages = time
            .county(county.geoid())
            .map_err(Error::HouseholdTime)?
            .budgets()
            .iter()
            .find(|b| b.key == row.budget)
            .ok_or(Error::Identity)?;
        // Require a nonempty ordinary remainder; preserve all source categories.
        if budget.persons <= row.persons
            || budget.households <= row.households
            || budget.employed < row.employed
            || budget.reserve < row.reserve
            || ages.eligible_16_plus < row.eligible
            || ages.inactive < row.inactive
            || ages.armed_forces < row.armed
            || ages.under_16 < row.under16
        {
            return Err(Error::SourceScope);
        }
        let remaining_persons = budget.persons - row.persons;
        let remaining_households = budget.households - row.households;
        let remaining_employed = budget.employed - row.employed;
        let remaining_reserve = budget.reserve - row.reserve;
        let remaining_eligible = ages.eligible_16_plus - row.eligible;
        if remaining_households > remaining_persons
            || remaining_employed
                .checked_add(remaining_reserve)
                .ok_or(Error::Arithmetic)?
                > remaining_eligible
            || remaining_eligible > remaining_persons
        {
            return Err(Error::SourceScope);
        }
        builder
            .eligible_overrides
            .insert(row.parent, remaining_eligible);
        builder
            .eligible_overrides
            .insert(row.principal, row.eligible);
    }
    Ok(())
}
fn retarget(
    allocation: &mut ResidentWorkplaceAllocation,
    child: &mut AidChildCapture,
    policy: &crate::national_economy::NationalGamePolicy,
) -> Result<()> {
    // Select one already admitted Employee group, never a workplace Cartesian product.
    let mut candidates: Vec<_> = allocation
        .workplaces
        .iter()
        .enumerate()
        .filter(|(_, workplace)| {
            policy
                .recipes
                .get(&workplace.target.function)
                .and_then(|recipe| policy.commodities.get(&recipe.output))
                .is_some_and(|commodity| {
                    matches!(
                        commodity.kind,
                        babylon_material_circuit::CommodityKind::Storable { .. }
                    )
                })
        })
        .flat_map(|(i, w)| {
            w.members
                .iter()
                .enumerate()
                .filter(|(_, m)| {
                    m.mode == ResidentAttendanceMode::Employee
                        && m.seed.member.household_id() == child.parent
                        && m.seed.employed >= child.employed
                        && m.seed.member.labor_force() > child.employed
                })
                .map(move |(j, _)| (w.target.site_id, i, j))
        })
        .collect();
    candidates.sort_unstable();
    let (_, i, j) = *candidates.first().ok_or(Error::SourceScope)?;
    let workplace = &mut allocation.workplaces[i];
    let member = &mut workplace.members[j];
    let mut moved = member.clone();
    member.seed.employed -= child.employed;
    member.seed.member = StaffingMemberBinding::try_new(
        member.seed.member.member_id(),
        child.parent,
        child.location,
        member
            .seed
            .employed
            .checked_add(member.seed.reserve)
            .ok_or(Error::Arithmetic)?,
    )
    .map_err(|_| {
        Error::Workforce(crate::national_resident_allocation::AllocationError::PopulationControl)
    })?;
    let mut bytes = b"NationalResidentMemberV2\0".to_vec();
    bytes.extend_from_slice(&workplace.target.site_id.as_bytes());
    bytes.extend_from_slice(&child.location.canonical_bytes());
    bytes.push(1);
    bytes.extend_from_slice(&child.principal.as_bytes());
    let id = sha256_of(&bytes);
    moved.seed.member = StaffingMemberBinding::try_new(
        StaffingMemberId::from_bytes(id),
        child.principal,
        child.location,
        child.employed,
    )
    .map_err(|_| {
        Error::Workforce(crate::national_resident_allocation::AllocationError::PopulationControl)
    })?;
    moved.seed.employed = child.employed;
    moved.seed.reserve = 0;
    moved.seed.subject = subject(&format!("member-{}", base32(&id)));
    child.class_subject = moved.seed.subject.clone();
    workplace.members.push(moved);
    workplace
        .members
        .sort_unstable_by_key(|m| m.seed.member.member_id());
    Ok(())
}
fn base32(bytes: &[u8; 32]) -> String {
    const ALPHABET: &[u8; 32] = b"abcdefghijklmnopqrstuvwxyz234567";
    let mut result = String::with_capacity(52);
    let mut bits = 0_u16;
    let mut count = 0;
    for byte in bytes {
        bits = (bits << 8) | u16::from(*byte);
        count += 8;
        while count >= 5 {
            count -= 5;
            result.push(char::from(ALPHABET[usize::from((bits >> count) & 31)]));
        }
    }
    if count > 0 {
        result.push(char::from(
            ALPHABET[usize::from((bits << (5 - count)) & 31)],
        ));
    }
    result
}
pub(super) fn households(
    builder: &mut Builder<'_>,
    location: EconomicLocation,
    budget: Key,
    persons: u64,
    households: u64,
    scale: u16,
) -> Result<()> {
    actors::household(builder, location, budget, persons, households, scale)?;
    let selected: Vec<_> = builder
        .aid
        .children
        .iter()
        .filter(|c| c.location == location && c.budget == budget)
        .cloned()
        .collect();
    for child in selected {
        actors::household_identity(
            builder,
            location,
            budget,
            child.persons,
            child.households,
            scale,
            (child.principal, child.subject.clone()),
        )?;
        let donated = builder
            .opening
            .households
            .last()
            .ok_or(Error::Identity)?
            .clone();
        let parent = builder
            .opening
            .households
            .iter_mut()
            .find(|h| h.principal_id == child.parent)
            .ok_or(Error::Identity)?;
        parent.persons = parent
            .persons
            .checked_sub(child.persons)
            .ok_or(Error::Arithmetic)?;
        parent.households = parent
            .households
            .checked_sub(child.households)
            .ok_or(Error::Arithmetic)?;
        if child.employed > 0 {
            parent.opening_cash = Currency::from_micro_units(
                parent
                    .opening_cash
                    .micro_units()
                    .checked_sub(donated.opening_cash.micro_units())
                    .ok_or(Error::Arithmetic)?,
            );
            for stock in &donated.opening_stock {
                let target = parent
                    .opening_stock
                    .iter_mut()
                    .find(|s| {
                        s.amount.good_id == stock.amount.good_id
                            && s.amount.unit_id == stock.amount.unit_id
                    })
                    .ok_or(Error::Identity)?;
                target.amount.quantity = target
                    .amount
                    .quantity
                    .checked_sub(stock.amount.quantity)
                    .ok_or(Error::Arithmetic)?;
                target.total_cost = Currency::from_micro_units(
                    target
                        .total_cost
                        .micro_units()
                        .checked_sub(stock.total_cost.micro_units())
                        .ok_or(Error::Arithmetic)?,
                );
            }
        } else {
            // Child initially receives zero. Its share remains with the source remainder.
            let recipient = builder
                .opening
                .households
                .iter_mut()
                .find(|h| h.principal_id == child.principal)
                .ok_or(Error::Identity)?;
            recipient.opening_cash = Currency::from_micro_units(0);
            for stock in &mut recipient.opening_stock {
                stock.amount.quantity = 0;
                stock.total_cost = Currency::from_micro_units(0);
            }
        }
    }
    Ok(())
}
pub(super) fn fund(builder: &mut Builder<'_>) -> Result<()> {
    let donor = builder.aid.children.first().ok_or(Error::Identity)?;
    let payer = builder.aid.mandates.first().ok_or(Error::Identity)?.payer;
    let amount = builder.policy.aid.organization_opening_cash_micros;
    let household = builder
        .opening
        .households
        .iter_mut()
        .find(|h| h.principal_id == donor.principal)
        .ok_or(Error::Identity)?;
    let remaining = household
        .opening_cash
        .micro_units()
        .checked_sub(amount)
        .filter(|n| *n >= 0)
        .ok_or(Error::Arithmetic)?;
    household.opening_cash = Currency::from_micro_units(remaining);
    builder.opening.institutional_cash.push(CashAccount {
        id: payer,
        cash: Currency::from_micro_units(amount),
    });
    builder
        .opening
        .institutions
        .locations
        .push(InstitutionLocation {
            account: payer,
            location: donor.location,
        });
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn captured_refinements_conserve_county_margins_and_real_opening_money() {
        let bytes = include_bytes!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../content/scenarios/national/defines.toml"
        ));
        let policy =
            crate::national_economy::NationalGamePolicy::from_captured_bytes(bytes).unwrap();
        let counties = crate::national_counties::national_county_reference().unwrap();
        let cohorts = crate::national_cohorts::national_cohort_reference().unwrap();
        let residents =
            crate::national_resident_workforce::national_resident_workforce_reference().unwrap();
        let households = crate::national_households::national_household_reference().unwrap();
        let budgets = crate::national_household_allocation::allocate_households(
            counties,
            households,
            residents,
            policy.households.private_owner_households_bps,
        )
        .unwrap();
        let time =
            crate::national_household_time_allocation::allocate_household_time(counties, &budgets)
                .unwrap();
        let captured = crate::national_economy::build_national_opening(
            counties,
            cohorts,
            residents,
            households,
            crate::world_reference::world_reference().unwrap(),
            crate::national_transport::national_transport_reference().unwrap(),
            crate::national_economy::NationalOpeningPolicy {
                policy: &policy,
                source_hash: sha256_of(bytes),
            },
        )
        .unwrap();
        assert_eq!(captured.aid.children.len(), 3);
        assert_refined_children(&captured, &policy, &budgets, &time);
        assert_organization_and_route(&captured, &policy);
    }

    fn assert_refined_children(
        captured: &crate::national_economy::NationalOpening,
        policy: &crate::national_economy::NationalGamePolicy,
        budgets: &NationalHouseholdAllocation,
        time: &NationalHouseholdTimeAllocation,
    ) {
        for child in &captured.aid.children {
            let EconomicLocation::County(county) = child.location else {
                panic!("domestic child")
            };
            let source = budgets
                .county(county.geoid())
                .unwrap()
                .budgets()
                .iter()
                .find(|b| b.key == child.budget)
                .unwrap();
            let parent = captured
                .opening
                .households
                .iter()
                .find(|h| h.principal_id == child.parent)
                .unwrap();
            let refined = captured
                .opening
                .households
                .iter()
                .find(|h| h.principal_id == child.principal)
                .unwrap();
            assert_eq!(parent.persons + refined.persons, source.persons);
            assert_eq!(parent.households + refined.households, source.households);
            let grouped: Vec<_> = captured
                .opening
                .staffing
                .iter()
                .flat_map(|p| &p.members)
                .filter(|m| [child.parent, child.principal].contains(&m.member.household_id()))
                .collect();
            assert_eq!(
                grouped.iter().map(|m| m.employed).sum::<u64>(),
                source.employed
            );
            assert_eq!(
                grouped.iter().map(|m| m.reserve).sum::<u64>(),
                source.reserve
            );
            let ages = time
                .county(county.geoid())
                .unwrap()
                .budgets()
                .iter()
                .find(|a| a.key == child.budget)
                .unwrap();
            // The captured whole age partitions are retained, not inferred from jobs.
            assert!(ages.inactive >= child.inactive);
            assert_eq!(
                child.eligible,
                child.employed + child.reserve + child.armed + child.inactive
            );
            assert_eq!(child.persons, child.eligible + child.under16);
            assert_child_endowments(captured, policy, child, refined, &grouped);
        }
    }

    fn assert_child_endowments(
        captured: &crate::national_economy::NationalOpening,
        policy: &crate::national_economy::NationalGamePolicy,
        child: &AidChildCapture,
        refined: &crate::economic_catalog::EconomicHouseholdSeed,
        grouped: &[&crate::economic_catalog::ResidentStaffingMemberSeed],
    ) {
        if child.employed == 0 {
            assert_eq!(refined.opening_cash.micro_units(), 0);
            assert!(refined
                .opening_stock
                .iter()
                .all(|s| s.amount.quantity == 0 && s.total_cost.micro_units() == 0));
            assert!(!captured
                .opening
                .staffing
                .iter()
                .flat_map(|p| &p.members)
                .any(|m| m.member.household_id() == child.principal));
        } else {
            let before = policy
                .household_needs
                .iter()
                .try_fold(0_i128, |total, need| {
                    let n = match need.basis {
                        babylon_material_circuit::HouseholdNeedBasis::Persons => refined.persons,
                        babylon_material_circuit::HouseholdNeedBasis::Households => {
                            refined.households
                        }
                    };
                    let price = policy.commodities[&need.key]
                        .price
                        .as_ref()
                        .unwrap()
                        .opening
                        .micro_units();
                    total.checked_add(
                        i128::from(n * need.units_per_basis)
                            * price
                            * i128::from(policy.working_capital_periods),
                    )
                })
                .unwrap();
            assert_eq!(
                refined.opening_cash.micro_units() + policy.aid.organization_opening_cash_micros,
                before
            );
            assert!(grouped.iter().any(|m| m.subject == child.class_subject
                && m.member.household_id() == child.principal
                && m.employed == 4
                && m.reserve == 0));
        }
    }

    fn assert_organization_and_route(
        captured: &crate::national_economy::NationalOpening,
        policy: &crate::national_economy::NationalGamePolicy,
    ) {
        let payer = captured.aid.mandates[0].payer;
        assert!(matches!(payer, AccountId::Organization(_)));
        assert_eq!(
            captured
                .opening
                .institutional_cash
                .iter()
                .find(|a| a.id == payer)
                .unwrap()
                .cash
                .micro_units(),
            policy.aid.organization_opening_cash_micros
        );
        assert!(captured
            .opening
            .institutions
            .locations
            .iter()
            .any(|l| l.account == payer && l.location == captured.aid.children[0].location));
        let AidTransport::Routed { route_id, .. } = captured.aid.mandates[1].transport else {
            panic!("remote route")
        };
        let stages: Vec<_> = captured
            .opening
            .logistics
            .route_stages
            .iter()
            .filter(|s| s.route_id == route_id)
            .collect();
        assert_eq!(stages.len(), 1);
        assert_eq!(stages[0].travel_periods, 1);
        assert_eq!(stages[0].loss_ppm, 0);
        assert_eq!(
            captured
                .opening
                .logistics
                .memberships
                .iter()
                .filter(|m| m.route_id == route_id)
                .count(),
            5
        );
    }
}
