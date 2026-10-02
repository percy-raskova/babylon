//! One aggregate staffing decision, conserved across resident members.
use babylon_material_circuit::*;

fn member(key: u8, employed: u64, reserve: u64) -> StaffingMemberState {
    StaffingMemberState::try_new(
        StaffingMemberBinding::try_new(
            StaffingMemberId::from_bytes([key; 32]),
            FinalDemandPrincipalId::from_bytes([key; 32]),
            "county:26163".parse().unwrap(),
            employed + reserve,
        )
        .unwrap(),
        employed,
        reserve,
    )
    .unwrap()
}

fn decision(employed: u64, reserve: u64, requested_hours: u64) -> StaffingReceipt {
    let binding = StaffingPoolBinding::try_new(
        StaffingPoolId::from_bytes([1; 32]),
        SiteId::from_bytes([2; 32]),
        UnitId::from_bytes([3; 32]),
        employed + reserve,
        StaffingPolicy::one_period(4).unwrap(),
        vec![StaffingWorkSource::Production(ProcessId::from_bytes(
            [4; 32],
        ))],
    )
    .unwrap();
    let request = StaffingWorkRequest::new(
        1,
        binding.pool_id(),
        binding.work_sources()[0],
        binding.site_id(),
        binding.unit_id(),
        requested_hours,
    );
    let state = StaffingState::try_new(
        1,
        vec![StaffingPoolState::try_new(binding, employed, reserve, 0).unwrap()],
    )
    .unwrap();
    advance_staffing(&state, &[request]).unwrap().receipts()[0].clone()
}

#[test]
fn resident_hires_and_separations_share_the_existing_pool_decision_exactly() {
    let members = vec![member(1, 1, 1), member(2, 2, 2)];
    let hired = distribute_staffing_members(&decision(3, 3, 20), &members).unwrap();
    assert_eq!(hired.iter().map(|r| r.hires).collect::<Vec<_>>(), [1, 1]);
    assert_eq!(hired.iter().map(|r| r.closing_employed).sum::<u64>(), 5);
    assert_eq!(hired.iter().map(|r| r.next_opening_hours).sum::<u64>(), 20);
    let released = distribute_staffing_members(&decision(3, 3, 4), &members).unwrap();
    assert_eq!(
        released.iter().map(|r| r.separations).collect::<Vec<_>>(),
        [1, 1]
    );
    for receipt in hired.iter().chain(&released) {
        assert_eq!(
            receipt.closing_employed + receipt.closing_reserve,
            receipt.member.labor_force()
        );
        receipt.validate().unwrap();
    }
}

#[test]
fn tied_member_transfers_are_identity_ordered_not_input_ordered() {
    let mut members = vec![member(1, 0, 1), member(2, 0, 1), member(3, 0, 1)];
    let first = distribute_staffing_members(&decision(0, 3, 4), &members).unwrap();
    members.reverse();
    let reversed = distribute_staffing_members(&decision(0, 3, 4), &members).unwrap();
    assert_eq!(first, reversed);
    assert_eq!(first.iter().map(|r| r.hires).collect::<Vec<_>>(), [1, 0, 0]);
}

#[test]
fn inconsistent_duplicate_and_overflowing_member_claims_are_refused() {
    let receipt = decision(3, 3, 20);
    assert!(distribute_staffing_members(&receipt, &[member(1, 1, 1)]).is_err());
    assert!(distribute_staffing_members(&receipt, &[member(1, 1, 1), member(1, 2, 2)]).is_err());
    let binding = StaffingMemberBinding::try_new(
        StaffingMemberId::from_bytes([1; 32]),
        FinalDemandPrincipalId::from_bytes([2; 32]),
        "county:26163".parse().unwrap(),
        u64::MAX,
    )
    .unwrap();
    assert!(StaffingMemberState::try_new(binding, u64::MAX, 1).is_err());
}

#[test]
fn an_explicit_zero_force_workplace_stays_empty_even_when_work_is_requested() {
    let row = decision(0, 0, 20);
    assert_eq!(row.target_employed(), 0);
    assert!(distribute_staffing_members(&row, &[]).unwrap().is_empty());
    assert!(distribute_staffing_members(&decision(1, 0, 4), &[]).is_err());
}
