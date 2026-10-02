use super::*;
use babylon_material_circuit::{
    member_shift_id, AccountId, EmploymentTerms, LaborUseReceipt, WageAccrualReceipt,
};
fn staffing() -> StaffingMemberReceipt {
    StaffingMemberReceipt {
        period: 1,
        pool_id: StaffingPoolId::from_bytes([1; 32]),
        site_id: SiteId::from_bytes([2; 32]),
        unit_id: UnitId::from_bytes([3; 32]),
        member: StaffingMemberBinding::try_new(
            StaffingMemberId::from_bytes([4; 32]),
            FinalDemandPrincipalId::from_bytes([5; 32]),
            "county:26163".parse().unwrap(),
            2,
        )
        .unwrap(),
        hours_per_person: 4,
        opening_employed: 1,
        opening_reserve: 1,
        hires: 1,
        separations: 0,
        closing_employed: 2,
        closing_reserve: 0,
        next_opening_hours: 8,
    }
}
fn attendance() -> MemberLaborUseReceipt {
    let row = staffing();
    let money = Currency::from_micro_units;
    MemberLaborUseReceipt {
        member_id: row.member.member_id(),
        site_id: row.site_id,
        unit_id: row.unit_id,
        payee: row.member.household_id(),
        compensation: LaborCompensation::Wage(money(3)),
        period: 1,
        available_hours: 4,
        planned_hours: 4,
        unplanned_hours: 0,
        attended_hours: 3,
        unattended_hours: 1,
        production_hours: 1,
        handling_hours: 1,
        maintenance_hours: 0,
        idle_hours: 1,
        accrued_wages: money(9),
        production_wages: money(3),
        handling_wages: money(3),
        maintenance_wages: money(0),
        idle_wages: money(3),
    }
}
#[test]
fn member_wire_roundtrips_and_refuses_false_population_or_wage_partitions() {
    let staff = staffing();
    let work = attendance();
    let mut bytes = vec![];
    encode_staffing(&staff, 1, &mut bytes).unwrap();
    assert_eq!(bytes.len(), STAFFING_BYTES);
    assert_eq!(
        decode_staffing(
            &mut ReceiptCursor {
                bytes: &bytes,
                position: 0
            },
            1
        )
        .unwrap(),
        staff
    );
    bytes.clear();
    encode_attendance(&work, 1, &mut bytes).unwrap();
    assert_eq!(bytes.len(), ATTENDANCE_BYTES);
    assert_eq!(
        decode_attendance(
            &mut ReceiptCursor {
                bytes: &bytes,
                position: 0
            },
            1
        )
        .unwrap(),
        work
    );
    let mut corrupt = bytes.clone();
    corrupt[128] = 2; // owner cannot retain an employee rate
    assert!(decode_attendance(
        &mut ReceiptCursor {
            bytes: &corrupt,
            position: 0
        },
        1
    )
    .is_err());
    let mut false_work = work;
    false_work.idle_wages = Currency::from_micro_units(-1);
    let mut unchanged = vec![7];
    assert!(encode_attendance(&false_work, 1, &mut unchanged).is_err());
    assert_eq!(unchanged, [7]);
    let mut false_staff = staff;
    false_staff.closing_reserve = 1;
    assert!(encode_staffing(&false_staff, 1, &mut unchanged).is_err());
    assert_eq!(unchanged, [7]);
}
#[test]
fn member_receipts_authenticate_payee_and_earned_wages_against_the_aggregate() {
    let staff = staffing();
    let work = attendance();
    let aggregate = LaborUseReceipt {
        site_id: work.site_id,
        unit_id: work.unit_id,
        period: 1,
        available_hours: 4,
        planned_hours: 4,
        unplanned_hours: 0,
        funded_hours: 3,
        unfunded_hours: 1,
        non_wage_hours: 0,
        used_hours: 2,
        paid_idle_hours: 1,
        unpaid_idle_hours: 0,
    };
    let terms = EmploymentTerms {
        member_id: work.member_id,
        site_id: work.site_id,
        unit_id: work.unit_id,
        payee: work.payee,
        compensation: work.compensation,
    };
    let wage = WageAccrualReceipt {
        shift: member_shift_id(1, &terms),
        employer: AccountId::Site(work.site_id),
        payee: AccountId::Household(work.payee),
        period: 1,
        obligated_hours: 3,
        amount: Currency::from_micro_units(9),
    };
    let validate = |staff: &[StaffingMemberReceipt],
                    members: &[MemberLaborUseReceipt],
                    wages: &[WageAccrualReceipt]| {
        validate_join(staff, members, std::slice::from_ref(&aggregate), wages)
    };
    validate(
        std::slice::from_ref(&staff),
        std::slice::from_ref(&work),
        std::slice::from_ref(&wage),
    )
    .unwrap();
    assert!(validate(
        std::slice::from_ref(&staff),
        std::slice::from_ref(&work),
        &[]
    )
    .is_err());
    let mut changed = work.clone();
    changed.payee = FinalDemandPrincipalId::from_bytes([8; 32]);
    assert!(validate(
        std::slice::from_ref(&staff),
        &[changed],
        std::slice::from_ref(&wage)
    )
    .is_err());
    let mut false_wage = wage;
    false_wage.amount = Currency::from_micro_units(10);
    assert!(validate(&[staff], &[work], &[false_wage]).is_err());
}
