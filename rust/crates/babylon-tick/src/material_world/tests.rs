use crate::material_world;
use crate::material_world::monetary_receipt;
use crate::material_world::workforce_receipt;
use crate::material_world::MaterialWorldError;
use crate::material_world::MAX_MATERIAL_TICK_RECEIPT_BYTES;
use crate::material_world::MAX_MATERIAL_WORLD_REGISTER_BYTES;
use crate::material_world::RECEIPT_DOMAIN;
use babylon_material_circuit::CapacityReservations;
use babylon_material_circuit::CapacitySupply;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::GoodId;
use babylon_material_circuit::HouseholdNeedBasis;
use babylon_material_circuit::LaborCompensation;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MaterialCircuitTransition;
use babylon_material_circuit::MemberLaborUseReceipt;
use babylon_material_circuit::SiteId;
use babylon_material_circuit::StaffingMemberId;
use babylon_material_circuit::UnitId;
use material_world::MaterialWorldRegister;

// A merchant's two physical handoffs share the same explicit handling account.
// These bytes exercise the committed receipt boundary independently of its encoder.
fn local_handoff_receipts() -> Vec<u8> {
    let mut bytes = b"babylon.material-tick-receipts.v20\0".to_vec();
    bytes.extend_from_slice(&20_u32.to_be_bytes());
    bytes.extend_from_slice(&1_u64.to_be_bytes());
    for tag in 1..=37_u8 {
        bytes.push(tag);
        bytes.extend_from_slice(&u64::from(matches!(tag, 7 | 8)).to_be_bytes());
        if tag == 7 {
            bytes.extend_from_slice(&[1; 32]); // retailer
            bytes.push(2); // local final demand, not a freight order
            bytes.extend_from_slice(&[2; 32]); // order
            for value in [10_u64, 2, 20, 4] {
                bytes.extend_from_slice(&value.to_be_bytes());
            }
        } else if tag == 8 {
            for key in [2, 1, 3, 4, 5] {
                bytes.extend_from_slice(&[key; 32]);
            }
            bytes.extend_from_slice(&2_u64.to_be_bytes());
        }
    }
    bytes
}

#[test]
fn committed_receipts_admit_explicit_merchant_handling_and_local_fulfillment() {
    use babylon_material_circuit::{OrderId, OutboundOrderId};
    let receipt = material_world::decode_material_receipts(&local_handoff_receipts())
        .expect("the canonical bytes decode into the declared type");
    assert_eq!(receipt.resolve_tick, 1);
    assert_eq!(receipt.dispatches.len(), 0);
    assert_eq!(receipt.arrivals.len(), 0);
    assert_eq!(receipt.handling.len(), 1);
    let work = &receipt.handling[0];
    assert_eq!(
        work.order,
        OutboundOrderId::LocalFinalDemand(OrderId::from_bytes([2; 32]))
    );
    assert_eq!((work.feasible_quantity, work.handled_quantity), (10, 2));
    assert_eq!((work.needed_hours, work.used_hours), (20, 4));
    assert_eq!(receipt.local_fulfillments.len(), 1);
    assert_eq!(receipt.local_fulfillments[0].quantity, 2);
    assert_eq!(receipt.local_fulfillments[0].retailer_site_id, work.site_id);
}

#[test]
fn handling_wire_refuses_unknown_kinds_overdraws_and_false_hours() {
    let canonical = local_handoff_receipts();
    let row = RECEIPT_DOMAIN.len() + 12 + 7 * 9;
    for (offset, replacement) in [
        (row + 32, vec![3]),
        (row + 65 + 8, 11_u64.to_be_bytes().to_vec()),
        (row + 65 + 24, 5_u64.to_be_bytes().to_vec()),
        (row + 65 + 16, 0_u64.to_be_bytes().to_vec()),
    ] {
        let mut changed = canonical.clone();
        changed[offset..offset + replacement.len()].copy_from_slice(&replacement);
        assert_eq!(
            material_world::decode_material_receipts(&changed),
            Err(MaterialWorldError::Wire)
        );
    }
}

#[test]
fn receipt_version_and_local_delivery_quantity_are_strict() {
    let canonical = local_handoff_receipts();
    let mut previous_version = canonical.clone();
    let version = RECEIPT_DOMAIN.len();
    previous_version[version..version + 4].copy_from_slice(&3_u32.to_be_bytes());
    assert_eq!(
        material_world::decode_material_receipts(&previous_version),
        Err(MaterialWorldError::Wire)
    );
    let mut zero_delivery = canonical;
    // Eight family headers, the preceding handling row, then five identities.
    let quantity = RECEIPT_DOMAIN.len() + 12 + 8 * 9 + 97 + 160;
    zero_delivery[quantity..quantity + 8].copy_from_slice(&0_u64.to_be_bytes());
    assert_eq!(
        material_world::decode_material_receipts(&zero_delivery),
        Err(MaterialWorldError::Wire)
    );
}

#[test]
fn local_transfer_receipts_preserve_both_owners_without_freight() {
    use babylon_material_circuit::SiteId;
    let mut bytes = local_handoff_receipts();
    let tail = bytes.split_off(bytes.len() - (37 - 9) * 9);
    let count = bytes.len() - 8;
    bytes[count..].copy_from_slice(&1_u64.to_be_bytes());
    let row_start = bytes.len();
    for key in [6, 7, 1, 4, 5] {
        bytes.extend_from_slice(&[key; 32]);
    }
    bytes.extend_from_slice(&3_u64.to_be_bytes());
    bytes.extend_from_slice(&tail);
    let receipts = material_world::decode_material_receipts(&bytes)
        .expect("the canonical bytes decode into the declared type");
    assert_eq!(receipts.local_transfers.len(), 1);
    let transfer = &receipts.local_transfers[0];
    assert_eq!(transfer.supplier_site_id, SiteId::from_bytes([7; 32]));
    assert_eq!(transfer.buyer_site_id, SiteId::from_bytes([1; 32]));
    assert_eq!(transfer.quantity, 3);
    assert_eq!(receipts.dispatches.len(), 0);
    assert_eq!(receipts.arrivals.len(), 0);

    let mut self_transfer = bytes.clone();
    self_transfer[row_start + 64..row_start + 96].copy_from_slice(&[7; 32]);
    assert_eq!(
        material_world::decode_material_receipts(&self_transfer),
        Err(MaterialWorldError::Wire)
    );
    let end = bytes.len() - (37 - 9) * 9;
    bytes[end - 8..end].fill(0);
    assert_eq!(
        material_world::decode_material_receipts(&bytes),
        Err(MaterialWorldError::Wire)
    );
}

#[test]
fn monetary_receipt_encoding_preserves_exact_cash_and_execution_order() {
    use babylon_kernel::currency::Currency;
    use babylon_material_circuit::{
        AccountId, CashTransferPurpose, MoneyLocation, MoneyPosting, MoneyTransferPurpose,
        MoneyTransferReceipt, OrganizationAccountId, PublicAccountId,
    };
    let sender = AccountId::Organization(OrganizationAccountId::from_bytes([9; 32]));
    let recipient = AccountId::Public(PublicAccountId::from_bytes([1; 32]));
    let rows: Vec<_> = [i128::MAX, 1, (1_i128 << 100) + 3]
        .map(|amount| MoneyTransferReceipt {
            purpose: MoneyTransferPurpose::Cash(CashTransferPurpose::MutualAid),
            debit: MoneyPosting {
                location: MoneyLocation::Cash(sender),
                delta: Currency::from_micro_units(-amount),
            },
            credit: MoneyPosting {
                location: MoneyLocation::Cash(recipient),
                delta: Currency::from_micro_units(amount),
            },
        })
        .into();
    let mut bytes = RECEIPT_DOMAIN.to_vec();
    bytes.extend_from_slice(&20_u32.to_be_bytes());
    bytes.extend_from_slice(&7_u64.to_be_bytes());
    for tag in 1..=37 {
        bytes.push(tag);
        bytes.extend_from_slice(&if tag == 11 { 3_u64 } else { 0 }.to_be_bytes());
        if tag == 11 {
            for row in &rows {
                monetary_receipt::encode_transfer(row, &mut bytes)
                    .expect("the fixture value encodes to its canonical bytes");
            }
        }
    }
    let decoded = material_world::decode_material_receipts(&bytes)
        .expect("the canonical bytes decode into the declared type");
    assert_eq!(decoded.money_transfers, rows);
    let mut invalid = rows[0].clone();
    invalid.credit.delta = Currency::from_micro_units(1);
    let mut destination = vec![123];
    assert_eq!(
        monetary_receipt::encode_transfer(&invalid, &mut destination),
        Err(MaterialWorldError::Wire)
    );
    assert_eq!(destination, [123]);
}

fn member_attendance(member: u8, site: u8) -> babylon_material_circuit::MemberLaborUseReceipt {
    let money = babylon_kernel::currency::Currency::from_micro_units;
    MemberLaborUseReceipt {
        member_id: StaffingMemberId::from_bytes([member; 32]),
        site_id: SiteId::from_bytes([site; 32]),
        unit_id: UnitId::from_bytes([5; 32]),
        payee: FinalDemandPrincipalId::from_bytes([2; 32]),
        compensation: LaborCompensation::Wage(money(3)),
        period: 7,
        available_hours: 6,
        planned_hours: 6,
        unplanned_hours: 0,
        attended_hours: 4,
        unattended_hours: 2,
        production_hours: 1,
        handling_hours: 0,
        maintenance_hours: 0,
        installation_hours: 0,
        idle_hours: 3,
        accrued_wages: money(12),
        production_wages: money(3),
        handling_wages: money(0),
        maintenance_wages: money(0),
        installation_wages: babylon_kernel::currency::Currency::from_micro_units(0),
        idle_wages: money(9),
    }
}

#[test]
fn attendance_receipt_encoding_roundtrips_without_sorting_hashed_shift_ids() {
    use babylon_material_circuit::{
        AccountId, EmploymentTerms, LaborUseReceipt, WageAccrualReceipt,
    };
    let members = [member_attendance(4, 1), member_attendance(1, 2)];
    let wages: Vec<_> = members
        .iter()
        .map(|row| {
            let terms = EmploymentTerms {
                member_id: row.member_id,
                site_id: row.site_id,
                unit_id: row.unit_id,
                payee: row.payee,
                compensation: row.compensation,
            };
            WageAccrualReceipt {
                shift: babylon_material_circuit::member_shift_id(7, &terms),
                employer: AccountId::Site(row.site_id),
                payee: AccountId::Household(row.payee),
                period: 7,
                obligated_hours: 4,
                amount: row.accrued_wages,
            }
        })
        .collect();
    assert!(
        wages[0].shift > wages[1].shift,
        "chronological wages are deliberately not hash ordered"
    );
    let labor: Vec<_> = members
        .iter()
        .map(|row| LaborUseReceipt {
            site_id: row.site_id,
            unit_id: row.unit_id,
            period: 7,
            available_hours: 6,
            planned_hours: 6,
            unplanned_hours: 0,
            funded_hours: 4,
            unfunded_hours: 2,
            non_wage_hours: 0,
            used_hours: 1,
            paid_idle_hours: 3,
            unpaid_idle_hours: 0,
        })
        .collect();
    monetary_receipt::validate_order(&wages, &labor)
        .expect("the authored fixture satisfies the rule");
    let mut bytes = RECEIPT_DOMAIN.to_vec();
    bytes.extend_from_slice(&20_u32.to_be_bytes());
    bytes.extend_from_slice(&7_u64.to_be_bytes());
    for tag in 1..=37 {
        bytes.push(tag);
        bytes.extend_from_slice(
            &if matches!(tag, 12 | 13 | 29) {
                2_u64
            } else {
                0
            }
            .to_be_bytes(),
        );
        if tag == 12 {
            for row in &wages {
                monetary_receipt::encode_accrual(row, 7, &mut bytes)
                    .expect("the fixture value encodes to its canonical bytes");
            }
        } else if tag == 13 {
            for row in &labor {
                monetary_receipt::encode_labor(row, 7, &mut bytes)
                    .expect("the fixture value encodes to its canonical bytes");
            }
        } else if tag == 29 {
            for row in &members {
                workforce_receipt::encode_attendance(row, 7, &mut bytes)
                    .expect("the fixture value encodes to its canonical bytes");
            }
        }
    }
    let decoded = material_world::decode_material_receipts(&bytes)
        .expect("the canonical bytes decode into the declared type");
    assert_eq!(decoded.wage_accruals, wages);
    assert_eq!(decoded.labor_use, labor);
    assert_eq!(decoded.member_labor_use, members);
    let reversed = [labor[1].clone(), labor[0].clone()];
    assert_eq!(
        monetary_receipt::validate_order(&wages, &reversed),
        Err(MaterialWorldError::Wire)
    );
}

// Exercises the real pre-allocation ceiling, without pretending a byte-capacity
// reservation is a valid giant economic state. No bytes are initialized here.
#[test]
fn register_byte_budget_is_one_gb_and_receipts_keep_their_independent_cap() {
    const ONE_GB: usize = 1_000_000_000;
    let admitted = material_world::bounded_bytes(ONE_GB, MAX_MATERIAL_WORLD_REGISTER_BYTES)
        .expect("the fixture call `bounded_bytes` succeeds for the authored inputs");
    assert_eq!(admitted.len(), 0);
    assert!(admitted.capacity() >= ONE_GB);
    assert_eq!(
        material_world::bounded_bytes(ONE_GB + 1, MAX_MATERIAL_WORLD_REGISTER_BYTES),
        Err(MaterialWorldError::ByteLimit)
    );
    assert_eq!(MAX_MATERIAL_TICK_RECEIPT_BYTES, 925_434_745);
    assert_eq!(
        material_world::bounded_bytes(
            MAX_MATERIAL_TICK_RECEIPT_BYTES + 1,
            MAX_MATERIAL_TICK_RECEIPT_BYTES
        ),
        Err(MaterialWorldError::ByteLimit)
    );
}

#[test]
fn previous_receipt17_handling_semantics_are_not_admitted_as_current() {
    let mut previous = local_handoff_receipts();
    let domain = b"babylon.material-tick-receipts.v17\0";
    previous[..domain.len()].copy_from_slice(domain);
    previous[domain.len()..domain.len() + 4].copy_from_slice(&17_u32.to_be_bytes());
    assert_eq!(
        material_world::decode_material_receipts(&previous),
        Err(MaterialWorldError::Wire)
    );
}

// The admission contract compares the internal candidate path with the external
// wire path on one already-canonical engine state.
fn admission_control() -> (MaterialCatalog, MaterialCircuitState) {
    let catalog = MaterialCatalog::try_new(babylon_material_circuit::MaterialCatalogDefinition {
        capacity_policy: CapacitySupply::FiniteSchedule,
        site_logistics_nodes: vec![],
        process_outputs: vec![],
        input_coefficients: vec![],
        labor_coefficients: vec![],
        commodities: vec![],
        supplier_routes: vec![],
        route_stages: vec![],
        merchants: vec![],
        handling_coefficients: vec![],
        maintenance_binding: None,
        aid_mandates: vec![],
        household_time_policy: vec![],
        service_inputs: vec![],
        household_needs: vec![],
    })
    .expect("the empty control catalog canonicalizes");
    let state = babylon_material_circuit::advance_material_circuit(
        &catalog,
        &MaterialCircuitState {
            period: 1,
            accounting: CircuitAccounting::PhysicalControl,
            service_connections: vec![],
            service_orders: vec![],
            route_stage_capacities: vec![],
            inventory: vec![],
            orders: vec![],
            freight: vec![],
            corridor_capacities: vec![],
            capacities: vec![],
            labor: vec![],
            production_commitments: vec![],
            final_demand_principals: vec![],
            final_demand_orders: vec![],
            maintenance_service: None,
            capacity_reservations: CapacityReservations::default(),
        },
    )
    .expect("the empty control circuit closes one period")
    .state;
    (catalog, state)
}

#[test]
fn validated_candidate_admission_matches_external_decode_identity() {
    let (catalog, state) = admission_control();
    let candidate = MaterialWorldRegister::from_validated_candidate(&catalog, state.clone())
        .expect("the engine's canonical successor admits in one pass");
    assert_eq!(candidate.completed_tick(), 1);
    assert_eq!(candidate.state(), &state);
    assert_eq!(candidate.catalog_digest(), catalog.catalog_digest());
    let external =
        MaterialWorldRegister::decode_external(&catalog, candidate.canonical_bytes().to_vec())
            .expect("the admitted canonical bytes satisfy full wire validation");
    assert_eq!(external.digest(), candidate.digest());
    assert_eq!(external.canonical_bytes(), candidate.canonical_bytes());
    assert_eq!(external.state(), candidate.state());
    assert_eq!(
        material_world::nominal_material_world_hash([7; 32], &external),
        material_world::nominal_material_world_hash([7; 32], &candidate)
    );
}

#[test]
fn external_decode_refuses_a_catalog_that_did_not_admit_the_bytes() {
    let (catalog, state) = admission_control();
    let admitted = MaterialWorldRegister::from_validated_candidate(&catalog, state)
        .expect("the engine's canonical successor admits in one pass");
    let mut foreign = catalog.clone().into_definition();
    foreign
        .household_needs
        .push(babylon_material_circuit::HouseholdNeed {
            principal_id: FinalDemandPrincipalId::from_bytes([9; 32]),
            good_id: GoodId::from_bytes([9; 32]),
            unit_id: UnitId::from_bytes([9; 32]),
            basis: HouseholdNeedBasis::Persons,
            units_per_basis: 1,
        });
    let foreign = MaterialCatalog::try_new(foreign).expect("the foreign catalog canonicalizes");
    assert_eq!(
        MaterialWorldRegister::decode_external(&foreign, admitted.canonical_bytes().to_vec()),
        Err(MaterialWorldError::Circuit(
            babylon_material_circuit::MaterialCircuitError::WireDomain
        ))
    );
}

#[test]
fn a_refused_successor_leaves_the_published_register_unchanged() {
    let (catalog, state) = admission_control();
    let published = MaterialWorldRegister::from_validated_candidate(&catalog, state)
        .expect("the engine's canonical successor admits in one pass");
    let before = published.canonical_bytes().to_vec();
    let digest = published.digest();
    let successor = babylon_material_circuit::advance_material_circuit(&catalog, published.state())
        .expect("the published period closes once")
        .state;
    let advanced = babylon_material_circuit::advance_material_circuit(&catalog, &successor)
        .expect("the successor period closes once");
    assert_eq!(
        published
            .prepare_transition(&catalog, advanced, None, &[])
            .err(),
        Some(MaterialWorldError::PeriodMismatch)
    );
    assert_eq!(published.canonical_bytes(), before.as_slice());
    assert_eq!(published.digest(), digest);
    assert_eq!(published.completed_tick(), 1);
}

#[allow(
    dead_code,
    reason = "the shared paper-control fixture also supports other material tests"
)]
#[path = "../../../babylon-material-circuit/tests/support/organizer_funding_control.rs"]
pub(super) mod agency_control;

#[test]
fn actual_paid_agency_attendance_roundtrips_through_the_canonical_tick() {
    use babylon_material_circuit::AccountId;
    use babylon_material_circuit::AgencyAttendanceInput;
    use babylon_material_circuit::AgencyAttendanceOutcome;

    let (catalog, opening) = agency_control::opening_with_agency(500_000);
    let AccountId::Organization(agency) = agency_control::organization() else {
        unreachable!("the fixture agency is an organization")
    };
    let principal_id = agency_control::recipient();
    let residence = opening
        .final_demand_principals
        .iter()
        .find(|row| row.id == principal_id)
        .expect("the fixture contains the household")
        .location;
    let intent_id = [71; 32];
    let input = AgencyAttendanceInput {
        intent_id,
        shift_id: babylon_material_circuit::agency_shift_id(opening.period, intent_id),
        agency,
        principal_id,
        residence,
        labor_unit_id: agency_control::unit(90),
        due_period: opening.period,
        hours: 1,
        hourly_rate: agency_control::money(100_000),
    };
    let completed = babylon_material_circuit::close_material_period_with_support(
        &catalog,
        &opening,
        &[],
        &[],
        &[input],
    )
    .expect("the funded agency close starts")
    .finish_with_workforce(
        &catalog,
        agency_control::labor(2),
        agency_control::members(2),
    )
    .expect("the funded agency close finishes");
    assert_eq!(
        completed.agency_attendance[0].outcome,
        AgencyAttendanceOutcome::Paid
    );
    let bytes = material_world::encode_material_receipts(&catalog, 1, &completed)
        .expect("actual paid attendance must encode as canonical evidence");
    let decoded = material_world::decode_material_receipts(&bytes)
        .expect("actual paid attendance must decode from canonical evidence");
    assert_eq!(decoded.wage_accruals, completed.wage_accruals);
    assert_eq!(decoded.household_time, completed.household_time);
    assert_eq!(decoded.money_transfers, completed.money_transfers);
    assert_eq!(decoded.agency_paid.len(), 1);
    assert_eq!(decoded.agency_paid[0].wage, agency_control::money(100_000));
    let row = bytes.len() - 192;
    for offset in [0, 32, 64, 96, 128, 160, 168, 176] {
        let mut changed = bytes.clone();
        changed[row + offset + if offset >= 160 { 7 } else { 0 }] ^= 1;
        assert!(
            material_world::decode_material_receipts(&changed).is_err(),
            "tampered paid field {offset}"
        );
    }
    let mut missing = bytes.clone();
    missing.truncate(row);
    missing[row - 8..row].copy_from_slice(&0_u64.to_be_bytes());
    assert!(material_world::decode_material_receipts(&missing).is_err());
    let mut duplicate = bytes.clone();
    duplicate[row - 8..row].copy_from_slice(&2_u64.to_be_bytes());
    duplicate.extend_from_slice(&bytes[row..]);
    assert!(material_world::decode_material_receipts(&duplicate).is_err());
    let mut forged = completed.clone();
    forged.agency_attendance[0].input.agency =
        babylon_material_circuit::OrganizationAccountId::from_bytes([99; 32]);
    assert!(material_world::encode_material_receipts(&catalog, 1, &forged).is_err());
    let mut duplicated = completed.clone();
    duplicated
        .agency_attendance
        .push(duplicated.agency_attendance[0].clone());
    assert!(material_world::encode_material_receipts(&catalog, 1, &duplicated).is_err());
}

#[test]
fn unfunded_and_cancelled_agency_inputs_do_not_forge_paid_evidence() {
    use babylon_material_circuit::AccountId;
    use babylon_material_circuit::AgencyAttendanceInput;
    use babylon_material_circuit::AgencyAttendanceOutcome;
    for funded in [false, true] {
        let (catalog, opening) =
            agency_control::opening_with_agency(if funded { 500_000 } else { 0 });
        let mut definition = catalog.into_definition();
        if funded {
            let policy = definition
                .household_time_policy
                .iter_mut()
                .find(|p| p.principal_id == agency_control::recipient())
                .expect("recipient policy");
            policy.hours_per_eligible_person = 1;
        }
        let catalog = MaterialCatalog::try_new(definition).expect("catalog is valid");
        let AccountId::Organization(agency) = agency_control::organization() else {
            unreachable!()
        };
        let principal_id = agency_control::recipient();
        let residence = opening
            .final_demand_principals
            .iter()
            .find(|p| p.id == principal_id)
            .expect("recipient exists")
            .location;
        let intent_id = [75; 32];
        let input = AgencyAttendanceInput {
            intent_id,
            shift_id: babylon_material_circuit::agency_shift_id(1, intent_id),
            agency,
            principal_id,
            residence,
            labor_unit_id: agency_control::unit(90),
            due_period: 1,
            hours: 1,
            hourly_rate: agency_control::money(100_000),
        };
        let result = babylon_material_circuit::close_material_period_with_support(
            &catalog,
            &opening,
            &[],
            &[],
            &[input],
        )
        .expect("close begins")
        .finish_with_workforce(
            &catalog,
            agency_control::labor(2),
            agency_control::members(2),
        )
        .expect("close finishes");
        assert_eq!(
            result.agency_attendance[0].outcome,
            if funded {
                AgencyAttendanceOutcome::InsufficientTime
            } else {
                AgencyAttendanceOutcome::NoFunds
            }
        );
        let canonical = material_world::encode_material_receipts(&catalog, 1, &result)
            .expect("nonpaid close encodes");
        assert_eq!(
            material_world::decode_material_receipts(&canonical)
                .expect("nonpaid close decodes")
                .agency_paid
                .len(),
            0
        );
        material_world::validate_committed_nonpaid(&result.agency_attendance[0], &canonical)
            .expect("the original nonpaid result joins its committed material receipts");
        let mut forged = result.agency_attendance[0].clone();
        forged.input.shift_id = babylon_material_circuit::agency_shift_id(1, [76; 32]);
        assert!(material_world::validate_committed_nonpaid(&forged, &canonical).is_err());
    }
}

fn round2_agency_transition(
    funded: bool,
    short_time: bool,
) -> (MaterialCatalog, MaterialCircuitTransition) {
    use babylon_material_circuit::AccountId;
    use babylon_material_circuit::AgencyAttendanceInput;
    let (catalog, opening) = agency_control::opening_with_agency(if funded { 500_000 } else { 0 });
    let mut definition = catalog.into_definition();
    if short_time {
        definition
            .household_time_policy
            .iter_mut()
            .find(|row| row.principal_id == agency_control::recipient())
            .expect("recipient policy")
            .hours_per_eligible_person = 1;
    }
    let catalog = MaterialCatalog::try_new(definition).expect("catalog valid");
    let AccountId::Organization(agency) = agency_control::organization() else {
        unreachable!()
    };
    let principal_id = agency_control::recipient();
    let residence = opening
        .final_demand_principals
        .iter()
        .find(|row| row.id == principal_id)
        .expect("recipient exists")
        .location;
    let intent_id = [71; 32];
    let input = AgencyAttendanceInput {
        intent_id,
        shift_id: babylon_material_circuit::agency_shift_id(1, intent_id),
        agency,
        principal_id,
        residence,
        labor_unit_id: agency_control::unit(90),
        due_period: 1,
        hours: 1,
        hourly_rate: agency_control::money(100_000),
    };
    let result = babylon_material_circuit::close_material_period_with_support(
        &catalog,
        &opening,
        &[],
        &[],
        &[input],
    )
    .expect("close begins")
    .finish_with_workforce(
        &catalog,
        agency_control::labor(2),
        agency_control::members(2),
    )
    .expect("close finishes");
    (catalog, result)
}

fn round2_family(bytes: &[u8], target: usize) -> (usize, usize, usize) {
    let mut cursor = RECEIPT_DOMAIN.len() + 12;
    for (index, width) in material_world::RECEIPT_ROW_BYTES.iter().enumerate() {
        assert_eq!(usize::from(bytes[cursor]), index + 1);
        let count = u64::from_be_bytes(
            bytes[cursor + 1..cursor + 9]
                .try_into()
                .expect("family count"),
        );
        cursor += 9;
        if index + 1 == target {
            return (cursor, usize::try_from(count).expect("count fits"), *width);
        }
        cursor += usize::try_from(count).expect("count fits") * width;
    }
    unreachable!("expected receipt family")
}

#[test]
fn round2_paid_priority_refuses_coherent_protected_and_unpaid_shortfalls() {
    use babylon_material_circuit::CircuitAccounting;
    use babylon_material_circuit::HouseholdTimeAccounting;
    let (catalog, result) = round2_agency_transition(true, false);
    let canonical =
        material_world::encode_material_receipts(&catalog, 1, &result).expect("paid close encodes");
    let (start, count, width) = round2_family(&canonical, 34);
    let row = (0..count)
        .map(|i| start + i * width)
        .find(|&i| canonical[i..i + 32] == agency_control::recipient().as_bytes())
        .expect("paid household time row");
    for unpaid in [false, true] {
        let mut changed = canonical.clone();
        let attended = u64::from_be_bytes(
            changed[row + 80..row + 88]
                .try_into()
                .expect("attended hours"),
        );
        for (offset, value) in [
            (72, attended),
            (88, 0),
            (96, u64::from(!unpaid)),
            (104, u64::from(unpaid)),
            (112, 0),
            (120, u64::from(unpaid)),
            (128, 0),
        ] {
            changed[row + offset..row + offset + 8].copy_from_slice(&value.to_be_bytes());
        }
        assert!(
            material_world::decode_material_receipts(&changed).is_err(),
            "priority shortfall must refuse"
        );
        let mut forged = result.clone();
        let item = forged
            .household_time
            .iter_mut()
            .find(|r| r.principal_id == agency_control::recipient())
            .expect("household row");
        item.endowment_hours = item.attended_hours;
        item.protected_hours = 0;
        item.protected_unresolved_hours = u64::from(!unpaid);
        item.unpaid_requested_hours = u64::from(unpaid);
        item.unpaid_allocated_hours = 0;
        item.unpaid_unresolved_hours = u64::from(unpaid);
        item.contribution_available_hours = 0;
        item.validate()
            .expect("the forged time partition is individually coherent");
        let CircuitAccounting::Monetary(economy) = &mut forged.state.accounting else {
            unreachable!()
        };
        let HouseholdTimeAccounting::Modeled(book) = &mut economy.household_time else {
            unreachable!()
        };
        *book
            .receipts
            .iter_mut()
            .find(|r| r.principal_id == item.principal_id)
            .expect("state time row") = item.clone();
        assert!(
            material_world::encode_material_receipts(&catalog, 1, &forged).is_err(),
            "priority shortfall must refuse on encode"
        );
    }
}

#[test]
fn round2_paid_reservation_must_precede_payment_on_encode_and_decode() {
    use babylon_material_circuit::MoneyTransferPurpose;
    let (catalog, result) = round2_agency_transition(true, false);
    let shift = result.agency_attendance[0].input.shift_id;
    let reservation = result
        .money_transfers
        .iter()
        .position(|t| t.purpose == MoneyTransferPurpose::ShiftReservation(shift))
        .expect("reservation");
    let payment = result
        .money_transfers
        .iter()
        .position(|t| t.purpose == MoneyTransferPurpose::WagePayment(shift))
        .expect("payment");
    assert!(reservation < payment);
    let canonical =
        material_world::encode_material_receipts(&catalog, 1, &result).expect("paid close encodes");
    let (start, _, width) = round2_family(&canonical, 11);
    let mut changed = canonical.clone();
    let first = canonical[start + reservation * width..start + (reservation + 1) * width].to_vec();
    let second = canonical[start + payment * width..start + (payment + 1) * width].to_vec();
    changed[start + reservation * width..start + (reservation + 1) * width]
        .copy_from_slice(&second);
    changed[start + payment * width..start + (payment + 1) * width].copy_from_slice(&first);
    assert!(
        material_world::decode_material_receipts(&changed).is_err(),
        "payment before reserve must refuse"
    );
    let mut forged = result;
    forged.money_transfers.swap(reservation, payment);
    assert!(
        material_world::encode_material_receipts(&catalog, 1, &forged).is_err(),
        "payment before reserve must refuse on encode"
    );
}

#[test]
fn round2_cancelled_reservation_must_precede_cancellation() {
    use babylon_material_circuit::MoneyTransferPurpose;
    let (catalog, mut result) = round2_agency_transition(true, true);
    let shift = result.agency_attendance[0].input.shift_id;
    let reservation = result
        .money_transfers
        .iter()
        .position(|t| t.purpose == MoneyTransferPurpose::ShiftReservation(shift))
        .expect("reservation");
    let cancellation = result
        .money_transfers
        .iter()
        .position(|t| t.purpose == MoneyTransferPurpose::ShiftCancellation(shift))
        .expect("cancellation");
    assert!(reservation < cancellation);
    let canonical = material_world::encode_material_receipts(&catalog, 1, &result)
        .expect("cancelled close encodes");
    let (start, _, width) = round2_family(&canonical, 11);
    let mut changed = canonical.clone();
    let first = canonical[start + reservation * width..start + (reservation + 1) * width].to_vec();
    let second =
        canonical[start + cancellation * width..start + (cancellation + 1) * width].to_vec();
    changed[start + reservation * width..start + (reservation + 1) * width]
        .copy_from_slice(&second);
    changed[start + cancellation * width..start + (cancellation + 1) * width]
        .copy_from_slice(&first);
    assert!(
        material_world::decode_material_receipts(&changed).is_err(),
        "cancellation before reserve must refuse on decode"
    );
    result.money_transfers.swap(reservation, cancellation);
    assert!(
        material_world::encode_material_receipts(&catalog, 1, &result).is_err(),
        "cancellation before reserve must refuse"
    );
}
