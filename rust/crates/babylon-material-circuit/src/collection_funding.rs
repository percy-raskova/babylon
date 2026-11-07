//! Reconcile a donor's service admissions with actual performance and signed payment legs.
use std::result::Result as StdResult;
type Result<T> = StdResult<T, MaterialCircuitError>;
use crate::{
    AccountId, CircuitAccounting, FinalDemandPrincipalId, GoodId, HouseholdServiceReceipt,
    MaterialCircuitError, MaterialCircuitState, MoneyLocation, MoneyTransferPurpose,
    MoneyTransferReceipt, OrderId, OutboundOrderId, ServicePerformanceReceipt, UnitId,
};
use babylon_kernel::currency::Currency;
use std::collections::BTreeMap;

#[derive(Default)]
pub(crate) struct ServiceAdmissions {
    opening_reserves: BTreeMap<OrderId, Currency>,
    orders: Vec<ServicePerformanceReceipt>,
}

impl ServiceAdmissions {
    pub(crate) fn capture_opening(
        state: &MaterialCircuitState,
        donor: Option<FinalDemandPrincipalId>,
    ) -> Result<Self> {
        let mut sources = Self::default();
        let Some(donor) = donor else {
            return Ok(sources);
        };
        let CircuitAccounting::Monetary(e) = &state.accounting else {
            return Err(MaterialCircuitError::CollectionInvariant);
        };
        for order in state.service_orders.iter().filter(|r| {
            r.performance_period == state.period && r.buyer == AccountId::Household(donor)
        }) {
            let escrow = e.book.purchase(OutboundOrderId::Service(order.order_id))?;
            // The canonical opening already joined buyer, provider, quantity and zero prior closes.
            sources
                .opening_reserves
                .insert(order.order_id, escrow.reserved_amount()?);
        }
        Ok(sources)
    }
    pub(crate) fn capture_requests(
        &mut self,
        rows: &[ServicePerformanceReceipt],
        donor: Option<FinalDemandPrincipalId>,
    ) {
        if let Some(donor) = donor {
            self.orders.extend(
                rows.iter()
                    .filter(|r| r.buyer == AccountId::Household(donor))
                    .cloned(),
            );
        }
    }

    pub(super) fn reconcile(
        &self,
        donor: FinalDemandPrincipalId,
        period: u64,
        performance: &[ServicePerformanceReceipt],
        movements: &[MoneyTransferReceipt],
    ) -> Result<BTreeMap<(GoodId, UnitId), HouseholdServiceFunding>> {
        let buyer = AccountId::Household(donor);
        let mut actual = performance.iter().filter(|r| r.buyer == buyer);
        let mut legs = self
            .orders
            .iter()
            .map(|r| (r.order_id, PaymentLegs::default()))
            .collect::<BTreeMap<_, _>>();
        for movement in movements {
            record_leg(&mut legs, buyer, movement)?;
        }
        let mut funded = BTreeMap::<_, HouseholdServiceFunding>::new();
        for admitted in &self.orders {
            let row = actual
                .next()
                .ok_or(MaterialCircuitError::ServiceInvariant)?;
            verify_admission(admitted, row, period)?;
            let payment = legs
                .remove(&row.order_id)
                .ok_or(MaterialCircuitError::PurchaseInvariant)?;
            let refund =
                payment.reconcile(row, self.opening_reserves.get(&row.order_id).copied())?;
            funded
                .entry((row.good_id, row.unit_id))
                .or_default()
                .add(row, refund)?;
        }
        if actual.next().is_some() {
            return Err(MaterialCircuitError::ServiceInvariant);
        }
        Ok(funded)
    }
}

fn record_leg<'a>(
    legs: &mut BTreeMap<OrderId, PaymentLegs<'a>>,
    buyer: AccountId,
    movement: &'a MoneyTransferReceipt,
) -> Result<()> {
    match movement.purpose {
        MoneyTransferPurpose::PurchaseReservation(OutboundOrderId::Service(id)) => {
            if let Some(p) = legs.get_mut(&id) {
                unique(&mut p.reservation, movement)?;
            } else if movement.debit.location == MoneyLocation::Cash(buyer) {
                return Err(MaterialCircuitError::PurchaseInvariant);
            }
        }
        MoneyTransferPurpose::DeliverySettlement(OutboundOrderId::Service(id)) => {
            if let Some(p) = legs.get_mut(&id) {
                unique(&mut p.settlement, movement)?;
            }
        }
        MoneyTransferPurpose::PurchaseRefund(OutboundOrderId::Service(id)) => {
            if let Some(p) = legs.get_mut(&id) {
                unique(&mut p.refund, movement)?;
            } else if movement.credit.location == MoneyLocation::Cash(buyer) {
                return Err(MaterialCircuitError::PurchaseInvariant);
            }
        }
        _ => {}
    }
    Ok(())
}

fn verify_admission(
    source: &ServicePerformanceReceipt,
    row: &ServicePerformanceReceipt,
    period: u64,
) -> Result<()> {
    row.validate()?;
    if row.period != period
        || row.period != source.period
        || row.order_id != source.order_id
        || row.provider_site_id != source.provider_site_id
        || row.buyer != source.buyer
        || row.good_id != source.good_id
        || row.unit_id != source.unit_id
        || row.requested_quantity != source.requested_quantity
        || row.admitted_quantity != source.admitted_quantity
        || row.unit_price != source.unit_price
    {
        return Err(MaterialCircuitError::ServiceInvariant);
    }
    Ok(())
}

#[derive(Default)]
struct PaymentLegs<'a> {
    reservation: Option<&'a MoneyTransferReceipt>,
    settlement: Option<&'a MoneyTransferReceipt>,
    refund: Option<&'a MoneyTransferReceipt>,
}

fn unique<'a>(
    slot: &mut Option<&'a MoneyTransferReceipt>,
    movement: &'a MoneyTransferReceipt,
) -> Result<()> {
    if slot.replace(movement).is_some() {
        return Err(MaterialCircuitError::PurchaseInvariant);
    }
    Ok(())
}

fn posting(
    leg: Option<&MoneyTransferReceipt>,
    debit: MoneyLocation,
    credit: MoneyLocation,
    expected: i128,
) -> Result<i128> {
    match leg {
        None if expected == 0 => Ok(0),
        Some(row)
            if expected > 0
                && row.debit.location == debit
                && row.credit.location == credit
                && row.debit.delta.micro_units() == -expected
                && row.credit.delta.micro_units() == expected =>
        {
            Ok(row.credit.delta.micro_units())
        }
        _ => Err(MaterialCircuitError::PurchaseInvariant),
    }
}

impl PaymentLegs<'_> {
    fn reconcile(
        &self,
        row: &ServicePerformanceReceipt,
        opening: Option<Currency>,
    ) -> Result<i128> {
        let amount = |q: u64| {
            row.unit_price
                .micro_units()
                .checked_mul(i128::from(q))
                .ok_or(MaterialCircuitError::Arithmetic)
        };
        let reserve = MoneyLocation::PurchaseReserve(OutboundOrderId::Service(row.order_id));
        let buyer = MoneyLocation::Cash(row.buyer);
        let admitted = amount(row.admitted_quantity)?;
        if let Some(carried) = opening {
            if carried.micro_units() != admitted || self.reservation.is_some() {
                return Err(MaterialCircuitError::PurchaseInvariant);
            }
        } else {
            posting(self.reservation, buyer, reserve, admitted)?;
        }
        let settled = posting(
            self.settlement,
            reserve,
            MoneyLocation::Cash(AccountId::Site(row.provider_site_id)),
            amount(row.performed_quantity)?,
        )?;
        let refunded = posting(self.refund, reserve, buyer, amount(row.expired_quantity)?)?;
        if settled.checked_add(refunded) != Some(admitted) {
            return Err(MaterialCircuitError::PurchaseInvariant);
        }
        Ok(refunded)
    }
}

#[derive(Default)]
pub(super) struct HouseholdServiceFunding {
    admitted: u64,
    partially_funded: bool,
    used: u64,
    performed: u64,
    refunded: i128,
}

impl HouseholdServiceFunding {
    fn add(&mut self, row: &ServicePerformanceReceipt, refund: i128) -> Result<()> {
        self.partially_funded |= row.admitted_quantity < row.requested_quantity;
        self.admitted = self
            .admitted
            .checked_add(row.admitted_quantity)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        self.used = self
            .used
            .checked_add(row.used_quantity)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        self.performed = self
            .performed
            .checked_add(row.performed_quantity)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        self.refunded = self
            .refunded
            .checked_add(refund)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        Ok(())
    }

    /// An unfunded unmet need refuses the gift. Otherwise return the actual protected refund.
    pub(super) fn protected_refund(&self, need: &HouseholdServiceReceipt) -> Result<Option<i128>> {
        need.validate()?;
        if self.performed != need.performed_quantity || self.used != need.satisfied_quantity {
            return Err(MaterialCircuitError::ServiceInvariant);
        }
        Ok(if need.unmet_quantity == 0 {
            Some(0)
        } else if self.partially_funded || self.admitted < need.required_quantity {
            None
        } else {
            Some(self.refunded)
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{CashAccount, MonetaryBook, PurchaseEscrow, SiteId};
    #[test]
    fn missing_or_contradictory_service_legs_never_release_refunded_cash() {
        let principal = FinalDemandPrincipalId::from_bytes([3; 32]);
        let buyer = AccountId::Household(principal);
        let site = SiteId::from_bytes([9; 32]);
        let seller = AccountId::Site(site);
        let id = OrderId::from_bytes([7; 32]);
        let order = OutboundOrderId::Service(id);
        let price = Currency::from_micro_units(5);
        let mut book = MonetaryBook::open(vec![
            CashAccount {
                id: buyer,
                cash: Currency::from_micro_units(20),
            },
            CashAccount {
                id: seller,
                cash: Currency::from_micro_units(0),
            },
        ])
        .expect("real buyer and seller accounts");
        let mut performance = ServicePerformanceReceipt {
            period: 1,
            order_id: id,
            provider_site_id: site,
            buyer,
            good_id: GoodId::from_bytes([5; 32]),
            unit_id: UnitId::from_bytes([6; 32]),
            requested_quantity: 4,
            admitted_quantity: 4,
            performed_quantity: 0,
            used_quantity: 0,
            unused_quantity: 0,
            expired_quantity: 0,
            unit_price: price,
        };
        let mut sources = ServiceAdmissions::default();
        sources.capture_requests(std::slice::from_ref(&performance), Some(principal));
        performance.performed_quantity = 1;
        performance.used_quantity = 1;
        performance.expired_quantity = 3;
        let movements = vec![
            book.reserve_purchase(
                PurchaseEscrow::new(order, buyer, seller, 4, price).expect("four units"),
            )
            .expect("buyer funds full order"),
            book.settle_purchase(order, 1)
                .expect("one unit performed")
                .transfer,
            book.refund_purchase(order, 3)
                .expect("three units refunded")
                .transfer,
        ];
        let valid = std::slice::from_ref(&performance);
        let good = sources
            .reconcile(principal, 1, valid, &movements)
            .expect("verified funding");
        assert_eq!(
            good[&(performance.good_id, performance.unit_id)].refunded,
            15
        );
        for i in 0..3 {
            let mut missing = movements.clone();
            missing.remove(i);
            assert!(matches!(
                sources.reconcile(principal, 1, valid, &missing),
                Err(MaterialCircuitError::PurchaseInvariant)
            ));
            let mut duplicate = movements.clone();
            duplicate.push(movements[i].clone());
            assert!(matches!(
                sources.reconcile(principal, 1, valid, &duplicate),
                Err(MaterialCircuitError::PurchaseInvariant)
            ));
        }
        let mut wrong = movements.clone();
        wrong[2].credit.location = MoneyLocation::Cash(seller);
        assert!(matches!(
            sources.reconcile(principal, 1, valid, &wrong),
            Err(MaterialCircuitError::PurchaseInvariant)
        ));
        wrong[2] = movements[2].clone();
        wrong[2].debit.delta = Currency::from_micro_units(-10);
        assert!(matches!(
            sources.reconcile(principal, 1, valid, &wrong),
            Err(MaterialCircuitError::PurchaseInvariant)
        ));
        assert!(matches!(
            sources.reconcile(principal, 1, &[], &movements),
            Err(MaterialCircuitError::ServiceInvariant)
        ));
    }
}
