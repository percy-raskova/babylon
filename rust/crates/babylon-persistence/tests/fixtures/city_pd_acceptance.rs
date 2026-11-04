//! Shared accounting assertions for detached and committed national controls.
use babylon_material_circuit::{
    AccountId, CashTransferPurpose, FinalDemandPrincipalId, MoneyLocation, MoneyTransferPurpose,
    OrganizationAccountId, PublicAccountId, PublicTransferTreatment,
};
use babylon_practice_contract::CityPdConfig;
use babylon_tick::material_world::MaterialTickReceipts;

pub fn assert_receipts(config: &CityPdConfig, receipts: &MaterialTickReceipts, enabled: bool) {
    let agency =
        AccountId::Organization(OrganizationAccountId::from_bytes(config.agency_account_id));
    let public = AccountId::Public(PublicAccountId::from_bytes(config.public_account_id));
    let household = AccountId::Household(FinalDemandPrincipalId::from_bytes(
        config.investigator_household_account_id,
    ));
    let allocations: Vec<_> = receipts
        .public_budgets
        .iter()
        .filter(|r| r.recipient == agency)
        .collect();
    if !enabled {
        assert_eq!(
            allocations,
            [] as [&babylon_material_circuit::PublicBudgetReceipt; 0]
        );
        assert_eq!(
            receipts.agency_paid,
            [] as [babylon_tick::material_world::AgencyPaidReceipt; 0]
        );
        assert!(!receipts.money_transfers.iter().any(|r| {
            r.debit.location == MoneyLocation::Cash(agency)
                || r.credit.location == MoneyLocation::Cash(agency)
        }));
        return;
    }
    let [allocation] = allocations.as_slice() else {
        panic!("one agency allocation")
    };
    assert_eq!(
        allocation.public_account,
        PublicAccountId::from_bytes(config.public_account_id)
    );
    assert_eq!(
        allocation.treatment,
        PublicTransferTreatment::AgencyAppropriation
    );
    assert_eq!(allocation.requested.micro_units(), 24_000_000);
    assert_eq!(allocation.paid.micro_units(), 24_000_000);
    assert_eq!(allocation.unfunded.micro_units(), 0);
    let transfers: Vec<_> = receipts
        .money_transfers
        .iter()
        .filter(|r| {
            r.purpose == MoneyTransferPurpose::Cash(CashTransferPurpose::PublicTransfer)
                && r.debit.location == MoneyLocation::Cash(public)
                && r.credit.location == MoneyLocation::Cash(agency)
        })
        .collect();
    let [transfer] = transfers.as_slice() else {
        panic!("one public to agency transfer")
    };
    assert_eq!(transfer.debit.delta.micro_units(), -24_000_000);
    assert_eq!(transfer.credit.delta.micro_units(), 24_000_000);
    if receipts.resolve_tick == 1 {
        assert_eq!(
            receipts.agency_paid,
            [] as [babylon_tick::material_world::AgencyPaidReceipt; 0]
        );
    } else {
        let [paid] = receipts.agency_paid.as_slice() else {
            panic!("one paid agency shift")
        };
        assert_eq!(
            paid.agency,
            OrganizationAccountId::from_bytes(config.agency_account_id)
        );
        assert_eq!(
            paid.principal_id,
            FinalDemandPrincipalId::from_bytes(config.investigator_household_account_id)
        );
        assert_eq!(paid.hours, 1);
        assert_eq!(paid.wage.micro_units(), 24_000_000);
        for (purpose, debit, credit) in [
            (
                MoneyTransferPurpose::ShiftReservation(paid.shift_id),
                MoneyLocation::Cash(agency),
                MoneyLocation::PayrollReserve(paid.shift_id),
            ),
            (
                MoneyTransferPurpose::WagePayment(paid.shift_id),
                MoneyLocation::PayrollReserve(paid.shift_id),
                MoneyLocation::Cash(household),
            ),
        ] {
            let rows: Vec<_> = receipts
                .money_transfers
                .iter()
                .filter(|r| r.purpose == purpose)
                .collect();
            let [row] = rows.as_slice() else {
                panic!("one transfer for {purpose:?}")
            };
            assert_eq!((row.debit.location, row.credit.location), (debit, credit));
            assert_eq!(row.debit.delta.micro_units(), -24_000_000);
            assert_eq!(row.credit.delta.micro_units(), 24_000_000);
        }
    }
}
