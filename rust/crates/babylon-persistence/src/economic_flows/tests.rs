//! Distinguish reserve custody from actual payer/recipient settlement.
use super::payments;
use super::principals::{Parties, Principals};
use super::EconomicFlowError;
use crate::test_support;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CashAccount, CashTransferPurpose, FinalDemandPrincipalId, GoodId, MonetaryBook,
    MoneyLocation, MoneyPosting, MoneyTransferPurpose, MoneyTransferReceipt, OrderId,
    OutboundOrderId, ServicePerformanceReceipt, ShiftId, SiteId, UnitId, WageAccrualReceipt,
};

fn money(n: i128) -> Currency {
    Currency::from_micro_units(n)
}

fn posting(
    purpose: MoneyTransferPurpose,
    debit: MoneyLocation,
    credit: MoneyLocation,
    n: i128,
) -> MoneyTransferReceipt {
    MoneyTransferReceipt {
        purpose,
        debit: MoneyPosting {
            location: debit,
            delta: money(-n),
        },
        credit: MoneyPosting {
            location: credit,
            delta: money(n),
        },
    }
}

#[test]
fn reserve_legs_preserve_buyer_without_counting_the_sale_twice() {
    let buyer = AccountId::Household(FinalDemandPrincipalId::from_bytes([9; 32]));
    let seller = AccountId::Site(SiteId::from_bytes([9; 32]));
    let original = OrderId::from_bytes([1; 32]);
    for order in [
        OutboundOrderId::Delivery(original),
        OutboundOrderId::LocalFinalDemand(original),
        OutboundOrderId::Service(original),
    ] {
        let mut owners = Principals::default();
        owners.purchases.insert(
            order,
            Parties {
                payer: buyer,
                recipient: seller,
                price: money(5),
            },
        );
        let reserve = MoneyLocation::PurchaseReserve(order);
        let cash = MoneyLocation::Cash;
        assert_eq!(
            payments::parties(
                &posting(
                    MoneyTransferPurpose::PurchaseReservation(order),
                    cash(buyer),
                    reserve,
                    50
                ),
                &owners
            ),
            Ok(None)
        );
        assert_eq!(
            payments::parties(
                &posting(
                    MoneyTransferPurpose::DeliverySettlement(order),
                    reserve,
                    cash(seller),
                    45
                ),
                &owners
            ),
            Ok(Some((buyer, seller)))
        );
        assert_eq!(
            payments::parties(
                &posting(
                    MoneyTransferPurpose::PurchaseRefund(order),
                    reserve,
                    cash(buyer),
                    5
                ),
                &owners
            ),
            Ok(None)
        );
        assert_eq!(
            payments::parties(
                &posting(
                    MoneyTransferPurpose::DeliverySettlement(order),
                    reserve,
                    cash(buyer),
                    45
                ),
                &owners
            ),
            Err(EconomicFlowError::InvalidPosting)
        );
        assert_eq!(
            payments::parties(
                &posting(
                    MoneyTransferPurpose::DeliverySettlement(order),
                    reserve,
                    cash(seller),
                    4
                ),
                &owners
            ),
            Err(EconomicFlowError::InvalidPosting)
        );
    }
}

#[test]
fn retired_service_and_payroll_resolve_without_an_opening_or_closing_reserve() {
    let household = AccountId::Household(FinalDemandPrincipalId::from_bytes([2; 32]));
    let site = SiteId::from_bytes([3; 32]);
    let employer = AccountId::Site(site);
    let id = OrderId::from_bytes([4; 32]);
    let order = OutboundOrderId::Service(id);
    let shift = ShiftId::from_bytes([4; 32]);
    let mut receipts = test_support::material_receipts(1);
    receipts
        .service_performance
        .push(ServicePerformanceReceipt {
            period: 1,
            order_id: id,
            provider_site_id: site,
            buyer: household,
            good_id: GoodId::from_bytes([1; 32]),
            unit_id: UnitId::from_bytes([1; 32]),
            requested_quantity: 3,
            admitted_quantity: 2,
            performed_quantity: 1,
            used_quantity: 1,
            unused_quantity: 0,
            expired_quantity: 1,
            unit_price: money(7),
        });
    receipts.wage_accruals.push(WageAccrualReceipt {
        shift,
        employer,
        payee: household,
        period: 1,
        obligated_hours: 2,
        amount: money(20),
    });
    let cash = MoneyLocation::Cash;
    let service = posting(
        MoneyTransferPurpose::DeliverySettlement(order),
        MoneyLocation::PurchaseReserve(order),
        cash(employer),
        7,
    );
    let wage = posting(
        MoneyTransferPurpose::WagePayment(shift),
        MoneyLocation::PayrollReserve(shift),
        cash(household),
        20,
    );
    receipts.money_transfers = vec![service.clone(), wage.clone()];
    let book = MonetaryBook::open(
        [household, employer]
            .map(|id| CashAccount {
                id,
                cash: money(100),
            })
            .to_vec(),
    )
    .expect("disjoint funded principals");
    let owners =
        Principals::for_period(&book, &book, &receipts, []).expect("recognized retired principals");
    assert_eq!(
        payments::parties(&service, &owners),
        Ok(Some((household, employer)))
    );
    assert_eq!(
        payments::parties(&wage, &owners),
        Ok(Some((employer, household)))
    );
    let mut missing = receipts.clone();
    missing.wage_accruals.clear();
    let owners = Principals::for_period(&book, &book, &missing, []).expect("no payroll evidence");
    assert_eq!(
        payments::parties(&wage, &owners),
        Err(EconomicFlowError::UnknownShiftPrincipal)
    );
    missing.service_performance.clear();
    let owners = Principals::for_period(&book, &book, &missing, []).expect("no principal evidence");
    assert_eq!(
        payments::parties(&service, &owners),
        Err(EconomicFlowError::UnknownOrderPrincipal)
    );
    let direct = posting(
        MoneyTransferPurpose::Cash(CashTransferPurpose::MutualAid),
        cash(household),
        cash(employer),
        3,
    );
    assert_eq!(
        payments::parties(&direct, &owners),
        Ok(Some((household, employer)))
    );
}

#[test]
fn cancelled_agency_shift_returns_only_its_organizations_reserve() {
    use babylon_material_circuit::{
        AgencyAttendanceInput, AgencyAttendanceOutcome, AgencyObservationFundingReceipt,
        OrganizationAccountId,
    };
    let organization = OrganizationAccountId::from_bytes([1; 32]);
    let household = FinalDemandPrincipalId::from_bytes([2; 32]);
    let shift = babylon_material_circuit::agency_shift_id(1, [3; 32]);
    let mut funding = AgencyObservationFundingReceipt {
        input: AgencyAttendanceInput {
            intent_id: [3; 32],
            shift_id: shift,
            agency: organization,
            principal_id: household,
            residence: "county:26163".parse().expect("Wayne county"),
            labor_unit_id: UnitId::from_bytes([4; 32]),
            due_period: 1,
            hours: 2,
            hourly_rate: money(10),
        },
        outcome: AgencyAttendanceOutcome::InsufficientTime,
        requested: money(20),
        reserved: money(20),
        paid: money(0),
        cancelled: money(20),
        shortfall: money(0),
        attended_hours: 0,
        shortfall_hours: 2,
        attendance: None,
    };
    let organization = AccountId::Organization(organization);
    let household = AccountId::Household(household);
    let cash = MoneyLocation::Cash;
    let reserve = MoneyLocation::PayrollReserve(shift);
    let mut receipts = test_support::material_receipts(1);
    let reservation = posting(
        MoneyTransferPurpose::ShiftReservation(shift),
        cash(organization),
        reserve,
        20,
    );
    let cancellation = posting(
        MoneyTransferPurpose::ShiftCancellation(shift),
        reserve,
        cash(organization),
        20,
    );
    receipts.money_transfers = vec![reservation.clone(), cancellation.clone()];
    let book = MonetaryBook::open(
        [organization, household]
            .map(|id| CashAccount {
                id,
                cash: money(20),
            })
            .to_vec(),
    )
    .expect("two funded cash accounts");
    let owners =
        Principals::for_period(&book, &book, &receipts, [&funding]).expect("agency funding");
    assert_eq!(payments::parties(&reservation, &owners), Ok(None));
    assert_eq!(payments::parties(&cancellation, &owners), Ok(None));
    let wrong = posting(
        MoneyTransferPurpose::ShiftCancellation(shift),
        reserve,
        cash(household),
        20,
    );
    assert_eq!(
        payments::parties(&wrong, &owners),
        Err(EconomicFlowError::InvalidPosting)
    );
    funding.input.due_period = 2;
    let owners = Principals::for_period(&book, &book, &receipts, [&funding])
        .expect("unrelated retained attempt");
    assert_eq!(
        payments::parties(&reservation, &owners),
        Err(EconomicFlowError::UnknownShiftPrincipal)
    );
}

#[test]
fn representative_payee_uses_its_live_hub_and_keeps_the_catchment_separate() {
    use super::accounts;
    use crate::economic_catalog::{self, CapturedEconomicCatalog, EconomicSourceView};
    use babylon_kernel::economic_location::EconomicLocation;
    use std::collections::BTreeMap;

    let catalog =
        CapturedEconomicCatalog::capture(economic_catalog::national_catalog_input(), None)
            .expect("pinned national source capture");
    let view = catalog.view();
    let EconomicSourceView::National { counties, .. } = view.sources else {
        panic!("national sources")
    };
    let witness = catalog
        .national_generation()
        .expect("captured grain membership");
    let sites: BTreeMap<_, _> = view.opening.sites.iter().map(|s| (s.site_id, s)).collect();
    let (site, hub) = witness
        .source_incidence
        .iter()
        .find_map(|row| {
            let site = sites.get(&row.destination_site)?;
            let EconomicLocation::County(hub) = site.location else {
                return None;
            };
            (hub.geoid() != row.source_county).then_some((site, hub))
        })
        .expect("representative site includes a source county outside its operating hub");
    let foreign = view
        .opening
        .sites
        .iter()
        .find(|s| matches!(s.location, EconomicLocation::Foreign(_)))
        .expect("foreign site");
    let book = MonetaryBook::open(
        [site.site_id, foreign.site_id]
            .map(|s| CashAccount {
                id: AccountId::Site(s),
                cash: money(0),
            })
            .to_vec(),
    )
    .expect("two captured sites");
    let rows = accounts::project(&catalog, &book, None).expect("authenticated geography");
    let domestic = rows
        .iter()
        .find(|row| row.account == AccountId::Site(site.site_id).into())
        .expect("domestic site");
    assert_eq!(
        domestic.location.as_deref(),
        Some(site.location.to_string().as_str())
    );
    assert_eq!(
        domestic.industry.as_deref(),
        Some(site.function.source_key())
    );
    assert!(domestic
        .catchment
        .as_deref()
        .is_some_and(|value| value.starts_with("catchment:")));
    let expected = counties
        .county(hub.geoid())
        .expect("operating county")
        .internal_point();
    let point = domestic
        .county_internal_point
        .as_ref()
        .expect("TIGER internal point");
    assert_eq!(point.latitude, expected.latitude());
    assert_eq!(point.longitude, expected.longitude());
    let exterior = rows
        .iter()
        .find(|row| row.account == AccountId::Site(foreign.site_id).into())
        .expect("foreign account");
    assert_eq!(
        exterior.location.as_deref(),
        Some(foreign.location.to_string().as_str())
    );
    assert_eq!(exterior.county_internal_point, None);
    assert_eq!(exterior.catchment, None);
}
