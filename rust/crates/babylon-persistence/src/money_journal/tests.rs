//! Transfer classification retains exact postings without inventing reserve counterparties.
use super::{model, JournalError, MoneyLocationKind, MoneyPurpose};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CashTransferPurpose, FinalDemandPrincipalId, MoneyLocation, MoneyPosting,
    MoneyTransferPurpose, MoneyTransferReceipt, OrderId, OrganizationAccountId, OutboundOrderId,
    PublicAccountId, ShiftId, SiteId,
};

fn transfer(
    purpose: MoneyTransferPurpose,
    debit: MoneyLocation,
    credit: MoneyLocation,
    amount: i128,
) -> MoneyTransferReceipt {
    MoneyTransferReceipt {
        purpose,
        debit: MoneyPosting {
            location: debit,
            delta: Currency::from_micro_units(-amount),
        },
        credit: MoneyPosting {
            location: credit,
            delta: Currency::from_micro_units(amount),
        },
    }
}
fn purpose_and_namespace_transfers() -> Vec<MoneyTransferReceipt> {
    let site = MoneyLocation::Cash(AccountId::Site(SiteId::from_bytes([1; 32])));
    let household = MoneyLocation::Cash(AccountId::Household(FinalDemandPrincipalId::from_bytes(
        [1; 32],
    )));
    let organization = MoneyLocation::Cash(AccountId::Organization(
        OrganizationAccountId::from_bytes([1; 32]),
    ));
    let public = MoneyLocation::Cash(AccountId::Public(PublicAccountId::from_bytes([1; 32])));
    let shift = ShiftId::from_bytes([2; 32]);
    let mut source = Vec::new();
    for order in [
        OutboundOrderId::Delivery(OrderId::from_bytes([3; 32])),
        OutboundOrderId::LocalFinalDemand(OrderId::from_bytes([3; 32])),
        OutboundOrderId::Service(OrderId::from_bytes([3; 32])),
    ] {
        let reserve = MoneyLocation::PurchaseReserve(order);
        source.push(transfer(
            MoneyTransferPurpose::PurchaseReservation(order),
            household,
            reserve,
            i128::MAX,
        ));
        source.push(transfer(
            MoneyTransferPurpose::DeliverySettlement(order),
            reserve,
            site,
            i128::MAX,
        ));
        source.push(transfer(
            MoneyTransferPurpose::PurchaseRefund(order),
            reserve,
            household,
            i128::MAX,
        ));
    }
    source.push(transfer(
        MoneyTransferPurpose::ShiftReservation(shift),
        site,
        MoneyLocation::PayrollReserve(shift),
        7,
    ));
    source.push(transfer(
        MoneyTransferPurpose::WagePayment(shift),
        MoneyLocation::PayrollReserve(shift),
        household,
        7,
    ));
    source.push(transfer(
        MoneyTransferPurpose::ShiftCancellation(shift),
        MoneyLocation::PayrollReserve(shift),
        site,
        7,
    ));
    for purpose in [
        CashTransferPurpose::Tax,
        CashTransferPurpose::PublicTransfer,
        CashTransferPurpose::HouseholdTransfer,
        CashTransferPurpose::OwnershipDistribution,
        CashTransferPurpose::CapitalContribution,
        CashTransferPurpose::TransportService,
        CashTransferPurpose::MutualAid,
    ] {
        source.push(transfer(
            MoneyTransferPurpose::Cash(purpose),
            organization,
            public,
            9,
        ));
    }
    source
}

#[test]
fn every_purpose_and_location_namespace_preserves_source_identity_and_amount() {
    let source = purpose_and_namespace_transfers();
    let rows = model::movements(&source).expect("balanced exact transfers derive facts");
    assert_eq!(rows.len(), 19, "every source movement has one journal row");
    assert_eq!(
        rows[0].purpose,
        MoneyPurpose::PurchaseReservation,
        "reservation remains distinct from settlement"
    );
    assert_eq!(
        rows[1].purpose,
        MoneyPurpose::DeliverySettlement,
        "only settlement is a sale payment"
    );
    assert_eq!(
        rows[2].purpose,
        MoneyPurpose::PurchaseRefund,
        "refund remains distinct from settlement"
    );
    assert_eq!(
        rows[0].amount_micros,
        i128::MAX.to_string(),
        "maximum positive i128 stays exact"
    );
    assert_eq!(
        rows[0].credit.kind,
        MoneyLocationKind::DeliveryReserve,
        "reserve namespace survives"
    );
    assert_eq!(
        rows[3].credit.kind,
        MoneyLocationKind::LocalFinalDemandReserve,
        "equal bytes in a different order namespace remain different"
    );
    assert_eq!(
        rows[6].credit.kind,
        MoneyLocationKind::ServiceReserve,
        "service reserve remains distinct"
    );
    assert_eq!(
        rows[9].credit.kind,
        MoneyLocationKind::PayrollReserve,
        "payroll reserve is never inferred as an employer"
    );
    for (ordinal, row) in rows.iter().enumerate() {
        assert_eq!(
            row.ordinal,
            u64::try_from(ordinal).expect("small fixture"),
            "source ordinal remains stable"
        );
        assert_eq!(
            MoneyPurpose::parse(row.purpose.as_str()),
            Ok(row.purpose),
            "closed purpose round trip"
        );
        assert_eq!(
            MoneyLocationKind::parse(row.debit.kind.as_str()),
            Ok(row.debit.kind),
            "closed debit namespace round trip"
        );
        assert_eq!(
            MoneyLocationKind::parse(row.credit.kind.as_str()),
            Ok(row.credit.kind),
            "closed credit namespace round trip"
        );
    }
}
#[test]
fn nonpositive_or_unbalanced_postings_refuse_projection() {
    let from = MoneyLocation::Cash(AccountId::Site(SiteId::from_bytes([1; 32])));
    let to = MoneyLocation::Cash(AccountId::Public(PublicAccountId::from_bytes([2; 32])));
    let purpose = MoneyTransferPurpose::Cash(CashTransferPurpose::Tax);
    for amount in [0, -1] {
        assert_eq!(
            model::movements(&[transfer(purpose, from, to, amount)]),
            Err(JournalError::Projection),
            "nonpositive transfer is refused"
        );
    }
    let mut broken = transfer(purpose, from, to, 2);
    broken.debit.delta = Currency::from_micro_units(-1);
    assert_eq!(
        model::movements(&[broken]),
        Err(JournalError::Projection),
        "a mismatched debit cannot produce a fact"
    );
}
