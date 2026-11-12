//! Dated consent-scoped reports from the material close and final household-hour book.
use super::MaterialWorldError;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::{
    AccountId, CircuitAccounting, FinalDemandPrincipalId, MaterialCircuitState,
    MaterialCircuitTransition, MoneyLocation, MoneyTransferPurpose, OutboundOrderId, SiteId,
};
use babylon_practice_contract::{
    OrganizerConfig, OrganizerPartnerFacts, OrganizerReportCommodity, OrganizerReportSharing,
    OrganizerServiceReport,
};
use std::collections::BTreeMap;
use std::result::Result as StdResult;

type Result<T> = StdResult<T, MaterialWorldError>;
type Reports = Vec<(u64, OrganizerPartnerFacts)>;

/// A completed handoff or service performance supplies the expected amount.
/// Actual signed postings independently establish settlement and refund.
struct ReportOrder {
    buyer: AccountId,
    seller: SiteId,
    expected_settled: i128,
    expected_refunded: i128,
    settled: i128,
    refunded: i128,
}

impl ReportOrder {
    fn new(
        buyer: AccountId,
        seller: SiteId,
        price: i128,
        performed: u64,
        expired: u64,
    ) -> Result<Self> {
        Ok(Self {
            buyer,
            seller,
            expected_settled: price
                .checked_mul(i128::from(performed))
                .ok_or(MaterialWorldError::Arithmetic)?,
            expected_refunded: price
                .checked_mul(i128::from(expired))
                .ok_or(MaterialWorldError::Arithmetic)?,
            settled: 0,
            refunded: 0,
        })
    }
}
fn money(
    transition: &MaterialCircuitTransition,
    orders: &mut BTreeMap<OutboundOrderId, ReportOrder>,
) -> Result<()> {
    for receipt in &transition.money_transfers {
        let (id, refund) = match receipt.purpose {
            MoneyTransferPurpose::DeliverySettlement(id) => (id, false),
            MoneyTransferPurpose::PurchaseRefund(id) => (id, true),
            _ => continue,
        };
        let Some(order) = orders.get_mut(&id) else {
            continue;
        };
        let target = if refund {
            order.buyer
        } else {
            AccountId::Site(order.seller)
        };
        let credit = receipt.credit.delta.micro_units();
        if receipt.credit.location != MoneyLocation::Cash(target)
            || receipt.debit.location != MoneyLocation::PurchaseReserve(id)
            || credit < 0
            || credit.checked_neg() != Some(receipt.debit.delta.micro_units())
        {
            return Err(MaterialWorldError::ReportSettlement);
        }
        let value = if refund {
            &mut order.refunded
        } else {
            &mut order.settled
        };
        *value = value
            .checked_add(credit)
            .ok_or(MaterialWorldError::Arithmetic)?;
    }
    if orders
        .values()
        .any(|r| (r.settled, r.refunded) != (r.expected_settled, r.expected_refunded))
    {
        return Err(MaterialWorldError::ReportSettlement);
    }
    Ok(())
}
pub(super) fn closed<'a>(
    scopes: impl IntoIterator<Item = (u64, FinalDemandPrincipalId, &'a OrganizerReportSharing)>,
    opening: &MaterialCircuitState,
    period: u64,
    transition: &MaterialCircuitTransition,
) -> Result<Reports> {
    let mut reports = Vec::new();
    let payments = service_orders(transition, period)?;
    for (actor, principal, sharing) in scopes {
        for commodity in &sharing.food {
            reports.push((
                actor,
                food(opening, transition, period, principal, commodity)?,
            ));
        }
        let services = sharing
            .essential_services
            .iter()
            .map(|c| service(transition, &payments, period, principal, c))
            .collect::<Result<Vec<_>>>()?;
        if !services.is_empty() {
            reports.push((actor, OrganizerPartnerFacts::EssentialServices { services }));
        }
    }
    Ok(reports)
}

fn food(
    opening: &MaterialCircuitState,
    transition: &MaterialCircuitTransition,
    period: u64,
    principal: FinalDemandPrincipalId,
    commodity: &OrganizerReportCommodity,
) -> Result<OrganizerPartnerFacts> {
    let row = transition
        .household_consumption
        .iter()
        .find(|r| {
            r.period == period
                && r.principal_id == principal
                && r.good_id.as_bytes() == commodity.good_id
                && r.unit_id.as_bytes() == commodity.unit_id
        })
        .ok_or(MaterialWorldError::ReportRetailHandoff)?;
    let buyer = AccountId::Household(principal);
    let mut orders = BTreeMap::new();
    let mut handoffs = BTreeMap::new();
    for handoff in transition.local_fulfillments.iter().filter(|r| {
        r.demand_principal_id == principal && r.good_id == row.good_id && r.unit_id == row.unit_id
    }) {
        if handoff.quantity == 0 || handoffs.insert(handoff.order_id, handoff).is_some() {
            return Err(MaterialWorldError::ReportRetailHandoff);
        }
    }
    for r in transition.household_demand.iter().filter(|r| {
        r.period == period
            && r.principal_id == principal
            && r.good_id == row.good_id
            && r.unit_id == row.unit_id
    }) {
        let handoff = handoffs.get(&r.order_id);
        if r.fulfilled_quantity != handoff.map_or(0, |h| h.quantity)
            || handoff.is_some_and(|h| h.retailer_site_id != r.retailer_site_id)
        {
            return Err(MaterialWorldError::ReportRetailHandoff);
        }
        if orders
            .insert(
                OutboundOrderId::LocalFinalDemand(r.order_id),
                ReportOrder::new(
                    buyer,
                    r.retailer_site_id,
                    r.unit_price.micro_units(),
                    r.fulfilled_quantity,
                    r.expired_quantity,
                )?,
            )
            .is_some()
        {
            return Err(MaterialWorldError::ReportRetailHandoff);
        }
    }
    let mut purchased = 0_u64;
    for handoff in handoffs.values() {
        let id = OutboundOrderId::LocalFinalDemand(handoff.order_id);
        purchased = purchased
            .checked_add(handoff.quantity)
            .ok_or(MaterialWorldError::Arithmetic)?;
        if let std::collections::btree_map::Entry::Vacant(slot) = orders.entry(id) {
            let CircuitAccounting::Monetary(economy) = &opening.accounting else {
                return Err(MaterialWorldError::ReportRetailHandoff);
            };
            let escrow = economy
                .book
                .purchase(id)
                .map_err(|_| MaterialWorldError::ReportRetailHandoff)?;
            if escrow.buyer != buyer || escrow.seller != AccountId::Site(handoff.retailer_site_id) {
                return Err(MaterialWorldError::ReportRetailHandoff);
            }
            slot.insert(ReportOrder::new(
                buyer,
                handoff.retailer_site_id,
                escrow.unit_price.micro_units(),
                handoff.quantity,
                0,
            )?);
        }
    }
    money(transition, &mut orders)?;
    let settled_micros = orders
        .values()
        .try_fold(0i128, |v, r| v.checked_add(r.settled))
        .ok_or(MaterialWorldError::Arithmetic)?;
    Ok(OrganizerPartnerFacts::FoodProvision {
        commodity: commodity.clone(),
        required: row.required_quantity,
        consumed: row.consumed_quantity,
        unmet: row.unmet_quantity,
        closing: row.closing_quantity,
        purchased,
        settled_micros,
    })
}
fn service_orders(
    transition: &MaterialCircuitTransition,
    period: u64,
) -> Result<BTreeMap<OutboundOrderId, ReportOrder>> {
    let mut orders = BTreeMap::new();
    for r in &transition.service_performance {
        if r.period != period
            || orders
                .insert(
                    OutboundOrderId::Service(r.order_id),
                    ReportOrder::new(
                        r.buyer,
                        r.provider_site_id,
                        r.unit_price.micro_units(),
                        r.performed_quantity,
                        r.expired_quantity,
                    )?,
                )
                .is_some()
        {
            return Err(MaterialWorldError::ReportServicePerformance);
        }
    }
    for posting in &transition.money_transfers {
        if let MoneyTransferPurpose::DeliverySettlement(id @ OutboundOrderId::Service(_))
        | MoneyTransferPurpose::PurchaseRefund(id @ OutboundOrderId::Service(_)) =
            posting.purpose
        {
            if !orders.contains_key(&id) {
                return Err(MaterialWorldError::ReportServicePerformance);
            }
        }
    }
    money(transition, &mut orders)?;
    Ok(orders)
}

fn service(
    transition: &MaterialCircuitTransition,
    payments: &BTreeMap<OutboundOrderId, ReportOrder>,
    period: u64,
    principal: FinalDemandPrincipalId,
    commodity: &OrganizerReportCommodity,
) -> Result<OrganizerServiceReport> {
    let row = transition
        .household_services
        .iter()
        .find(|r| {
            r.period == period
                && r.principal_id == principal
                && r.good_id.as_bytes() == commodity.good_id
                && r.unit_id.as_bytes() == commodity.unit_id
        })
        .ok_or(MaterialWorldError::ReportServicePerformance)?;
    let buyer = AccountId::Household(principal);
    let mut settled_micros = 0_i128;
    let mut refunded_micros = 0_i128;
    let mut performed = 0u64;
    let mut expired = 0u64;
    for r in transition.service_performance.iter().filter(|r| {
        r.period == period
            && r.buyer == buyer
            && r.good_id == row.good_id
            && r.unit_id == row.unit_id
    }) {
        let payment = payments
            .get(&OutboundOrderId::Service(r.order_id))
            .ok_or(MaterialWorldError::ReportServicePerformance)?;
        settled_micros = settled_micros
            .checked_add(payment.settled)
            .ok_or(MaterialWorldError::Arithmetic)?;
        refunded_micros = refunded_micros
            .checked_add(payment.refunded)
            .ok_or(MaterialWorldError::Arithmetic)?;
        performed = performed
            .checked_add(r.performed_quantity)
            .ok_or(MaterialWorldError::Arithmetic)?;
        expired = expired
            .checked_add(r.expired_quantity)
            .ok_or(MaterialWorldError::Arithmetic)?;
    }
    if performed != row.performed_quantity {
        return Err(MaterialWorldError::ReportServicePerformance);
    }
    Ok(OrganizerServiceReport {
        commodity: commodity.clone(),
        required: row.required_quantity,
        performed,
        satisfied: row.satisfied_quantity,
        unmet: row.unmet_quantity,
        unused: row.unused_quantity,
        expired,
        settled_micros,
        refunded_micros,
    })
}

pub(super) fn completed_time(
    config: &OrganizerConfig,
    period: u64,
    state: &MaterialCircuitState,
) -> Result<Reports> {
    let book = super::organizer_time::book(state)?;
    let mut reports = Vec::new();
    for binding in &config.aid_bindings {
        for labor_unit in &binding.report_sharing.participation_time {
            let principal = FinalDemandPrincipalId::from_bytes(binding.recipient_principal_id);
            let row = book
                .receipts
                .iter()
                .find(|r| {
                    r.period == period
                        && r.principal_id == principal
                        && r.labor_unit_id.as_bytes() == *labor_unit
                })
                .ok_or(MaterialWorldError::ReportHouseholdTime)?;
            let contributed = book
                .contributions
                .iter()
                .filter(|r| r.period == period && r.contribution.principal_id == principal)
                .try_fold(0u64, |v, r| v.checked_add(r.contribution.hours))
                .ok_or(MaterialWorldError::Arithmetic)?;
            let remaining = row
                .contribution_available_hours
                .checked_sub(contributed)
                .ok_or(MaterialWorldError::Arithmetic)?;
            reports.push((
                binding.partner.actor_id,
                OrganizerPartnerFacts::ParticipationTime {
                    labor_unit: *labor_unit,
                    attended: row.attended_hours,
                    protected: row.protected_hours,
                    unpaid: row.unpaid_allocated_hours,
                    contributed,
                    remaining,
                },
            ));
        }
    }
    Ok(reports)
}

/// Validate authored scope against the actual mandate and material catalog.
pub(super) fn validate_scopes(catalog: &MaterialCatalog, config: &OrganizerConfig) -> Result<()> {
    use babylon_material_circuit::{CommodityKind, GoodId, UnitId};
    for binding in &config.aid_bindings {
        let scope = &binding.report_sharing;
        if scope.food.is_empty()
            && scope.essential_services.is_empty()
            && scope.participation_time.is_empty()
        {
            continue;
        }
        let mandate = catalog
            .aid_mandates
            .iter()
            .find(|m| {
                m.id == binding.mandate_id
                    && m.source_hash == binding.source_hash
                    && m.recipient_actor == binding.partner.actor_id
                    && m.recipient.as_bytes() == binding.recipient_principal_id
            })
            .ok_or(MaterialWorldError::ReportSharingScope)?;
        for commodity in scope.food.iter().chain(&scope.essential_services) {
            let good = GoodId::from_bytes(commodity.good_id);
            let unit = UnitId::from_bytes(commodity.unit_id);
            catalog
                .household_needs
                .binary_search_by_key(&(mandate.recipient, good, unit), |n| {
                    (n.principal_id, n.good_id, n.unit_id)
                })
                .map_err(|_| MaterialWorldError::ReportSharingScope)?;
            let kind = catalog
                .commodities
                .iter()
                .find(|c| c.good_id == good && c.unit_id == unit)
                .ok_or(MaterialWorldError::ReportSharingScope)?
                .kind;
            let valid = if scope.food.contains(commodity) {
                good == mandate.good_id
                    && unit == mandate.unit_id
                    && matches!(kind, CommodityKind::Storable { .. })
            } else {
                matches!(kind, CommodityKind::PeriodService { .. })
            };
            if !valid {
                return Err(MaterialWorldError::ReportSharingScope);
            }
        }
        if scope.participation_time.iter().any(|id| {
            *id != mandate.labor_unit_id.as_bytes()
                || !catalog.household_time_policy.iter().any(|p| {
                    p.principal_id == mandate.recipient && p.labor_unit_id.as_bytes() == *id
                })
        }) {
            return Err(MaterialWorldError::ReportSharingScope);
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::super::tests::agency_control as material;
    use super::*;
    use babylon_material_circuit::{FinalDemandOrder, MaterialPurchase, OrderId};

    fn commodity(id: u8) -> OrganizerReportCommodity {
        OrganizerReportCommodity {
            good_id: material::good(id).as_bytes(),
            unit_id: material::unit(id).as_bytes(),
            label: format!("Commodity {id}"),
            unit_label: "unit".into(),
        }
    }

    #[test]
    fn scoped_receipts_include_old_and_new_food_handoffs_with_both_signed_payments() {
        let (catalog, opening) = material::opening();
        let old = OrderId::from_bytes([1; 32]);
        let food_good = 2;
        let seller = material::site(2);
        let principal = material::donor();
        let (opening, _) = babylon_material_circuit::admit_material_purchase(
            &catalog,
            &opening,
            MaterialPurchase::LocalFinalDemand(FinalDemandOrder {
                order_id: old,
                retailer_site_id: seller,
                demand_principal_id: principal,
                good_id: material::good(food_good),
                unit_id: material::unit(food_good),
                ordered: 1,
                fulfilled: 0,
            }),
            material::money(7),
        )
        .expect("old finite order at its own fixed price");
        let mut close =
            material::close(&catalog, &opening, &[], &[]).expect("ordinary household close");
        let handoffs: Vec<_> = close
            .local_fulfillments
            .iter()
            .filter(|r| {
                r.demand_principal_id == principal && r.good_id == material::good(food_good)
            })
            .collect();
        assert_eq!(
            handoffs.len(),
            2,
            "expected both the finite and generated handoff"
        );
        let quantity = handoffs.iter().map(|r| r.quantity).sum();
        let paid = close
            .money_transfers
            .iter()
            .filter(|t| {
                handoffs.iter().any(|r| {
                    t.purpose
                        == MoneyTransferPurpose::DeliverySettlement(
                            OutboundOrderId::LocalFinalDemand(r.order_id),
                        )
                })
            })
            .map(|t| t.credit.delta.micro_units())
            .sum();
        let sharing = OrganizerReportSharing {
            food: vec![commodity(food_good)],
            ..OrganizerReportSharing::withheld()
        };
        let publish = |candidate: &_| closed([(30, principal, &sharing)], &opening, 1, candidate);
        let reports = publish(&close).expect("opted-in food report");
        let [(
            30,
            OrganizerPartnerFacts::FoodProvision {
                purchased,
                settled_micros,
                ..
            },
        )] = reports.as_slice()
        else {
            panic!("food report")
        };
        assert_eq!((*purchased, *settled_micros), (quantity, paid));
        close.money_transfers.retain(|row| {
            row.purpose
                != MoneyTransferPurpose::DeliverySettlement(OutboundOrderId::LocalFinalDemand(old))
        });
        assert!(matches!(
            publish(&close),
            Err(MaterialWorldError::ReportSettlement)
        ));
    }

    #[test]
    fn scoped_receipts_reject_missing_fully_expired_performance_and_its_unmatched_refund() {
        let (catalog, mut opening) = material::opening();
        opening
            .production_commitments
            .retain(|p| p.site_id != material::site(3));
        let mut close = material::close(&catalog, &opening, &[], &[])
            .expect("real service payments and refunds");
        let principal = material::donor();
        let sharing = OrganizerReportSharing {
            essential_services: vec![commodity(3), commodity(4)],
            ..OrganizerReportSharing::withheld()
        };
        let publish = |candidate: &_| closed([(30, principal, &sharing)], &opening, 1, candidate);
        let reports = publish(&close).expect("opted-in service report");
        let [(30, OrganizerPartnerFacts::EssentialServices { services })] = reports.as_slice()
        else {
            panic!("only granted service topic")
        };
        let [expired, paid] = services.as_slice() else {
            panic!("two granted services")
        };
        assert!(paid.settled_micros > 0);
        assert_eq!(expired.performed, 0);
        assert!(expired.expired > 0 && expired.refunded_micros > 0);
        close
            .service_performance
            .retain(|r| r.good_id != material::good(3));
        assert!(
            matches!(
                publish(&close),
                Err(MaterialWorldError::ReportServicePerformance)
            ),
            "a real refund lost its private order"
        );
    }
}
