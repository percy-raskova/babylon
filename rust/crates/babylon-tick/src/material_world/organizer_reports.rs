//! Dated consent-scoped reports from the material close and final household-hour book.
use super::MaterialWorldError;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::{
    AccountId, FinalDemandPrincipalId, MaterialCircuitState, MaterialCircuitTransition,
    MoneyLocation, MoneyTransferPurpose, OutboundOrderId, SiteId,
};
use babylon_practice_contract::{
    OrganizerConfig, OrganizerPartnerFacts, OrganizerReportCommodity, OrganizerServiceReport,
};
use std::collections::BTreeMap;
use std::result::Result as StdResult;

type Result<T> = StdResult<T, MaterialWorldError>;
type Reports = Vec<(u64, OrganizerPartnerFacts)>;

/// Only permitted partner orders enter this join. Funds come from actual matching
/// signed postings; the quoted price independently validates an observed posting.
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
            return Err(MaterialWorldError::Wire);
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
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}
pub(super) fn closed(
    config: &OrganizerConfig,
    period: u64,
    transition: &MaterialCircuitTransition,
) -> Result<Reports> {
    let mut reports = Vec::new();
    for binding in &config.aid_bindings {
        let principal = FinalDemandPrincipalId::from_bytes(binding.recipient_principal_id);
        let actor = binding.partner.actor_id;
        for commodity in &binding.report_sharing.food {
            let row = transition
                .household_consumption
                .iter()
                .find(|r| {
                    r.period == period
                        && r.principal_id == principal
                        && r.good_id.as_bytes() == commodity.good_id
                        && r.unit_id.as_bytes() == commodity.unit_id
                })
                .ok_or(MaterialWorldError::Wire)?;
            let buyer = AccountId::Household(principal);
            let mut orders = BTreeMap::new();
            let mut purchased = 0u64;
            for r in transition.household_demand.iter().filter(|r| {
                r.period == period
                    && r.principal_id == principal
                    && r.good_id == row.good_id
                    && r.unit_id == row.unit_id
            }) {
                purchased = purchased
                    .checked_add(r.fulfilled_quantity)
                    .ok_or(MaterialWorldError::Arithmetic)?;
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
                    return Err(MaterialWorldError::Wire);
                }
            }
            money(transition, &mut orders)?;
            let settled_micros = orders
                .values()
                .try_fold(0i128, |v, r| v.checked_add(r.settled))
                .ok_or(MaterialWorldError::Arithmetic)?;
            reports.push((
                actor,
                OrganizerPartnerFacts::FoodProvision {
                    commodity: commodity.clone(),
                    required: row.required_quantity,
                    consumed: row.consumed_quantity,
                    unmet: row.unmet_quantity,
                    closing: row.closing_quantity,
                    purchased,
                    settled_micros,
                },
            ));
        }
        let services = binding
            .report_sharing
            .essential_services
            .iter()
            .map(|c| service(transition, period, principal, c))
            .collect::<Result<Vec<_>>>()?;
        if !services.is_empty() {
            reports.push((actor, OrganizerPartnerFacts::EssentialServices { services }));
        }
    }
    Ok(reports)
}

fn service(
    transition: &MaterialCircuitTransition,
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
        .ok_or(MaterialWorldError::Wire)?;
    let buyer = AccountId::Household(principal);
    let mut orders = BTreeMap::new();
    let mut performed = 0u64;
    let mut expired = 0u64;
    for r in transition.service_performance.iter().filter(|r| {
        r.period == period
            && r.buyer == buyer
            && r.good_id == row.good_id
            && r.unit_id == row.unit_id
    }) {
        if orders
            .insert(
                OutboundOrderId::Service(r.order_id),
                ReportOrder::new(
                    buyer,
                    r.provider_site_id,
                    r.unit_price.micro_units(),
                    r.performed_quantity,
                    r.expired_quantity,
                )?,
            )
            .is_some()
        {
            return Err(MaterialWorldError::Wire);
        }
        performed = performed
            .checked_add(r.performed_quantity)
            .ok_or(MaterialWorldError::Arithmetic)?;
        expired = expired
            .checked_add(r.expired_quantity)
            .ok_or(MaterialWorldError::Arithmetic)?;
    }
    if performed != row.performed_quantity {
        return Err(MaterialWorldError::Wire);
    }
    money(transition, &mut orders)?;
    let settled_micros = orders
        .values()
        .try_fold(0i128, |v, r| v.checked_add(r.settled))
        .ok_or(MaterialWorldError::Arithmetic)?;
    let refunded_micros = orders
        .values()
        .try_fold(0i128, |v, r| v.checked_add(r.refunded))
        .ok_or(MaterialWorldError::Arithmetic)?;
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
                .ok_or(MaterialWorldError::Wire)?;
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
            .ok_or(MaterialWorldError::Wire)?;
        for commodity in scope.food.iter().chain(&scope.essential_services) {
            let good = GoodId::from_bytes(commodity.good_id);
            let unit = UnitId::from_bytes(commodity.unit_id);
            catalog
                .household_needs
                .binary_search_by_key(&(mandate.recipient, good, unit), |n| {
                    (n.principal_id, n.good_id, n.unit_id)
                })
                .map_err(|_| MaterialWorldError::Wire)?;
            let kind = catalog
                .commodities
                .iter()
                .find(|c| c.good_id == good && c.unit_id == unit)
                .ok_or(MaterialWorldError::Wire)?
                .kind;
            let valid = if scope.food.contains(commodity) {
                good == mandate.good_id
                    && unit == mandate.unit_id
                    && matches!(kind, CommodityKind::Storable { .. })
            } else {
                matches!(kind, CommodityKind::PeriodService { .. })
            };
            if !valid {
                return Err(MaterialWorldError::Wire);
            }
        }
        if scope.participation_time.iter().any(|id| {
            *id != mandate.labor_unit_id.as_bytes()
                || !catalog.household_time_policy.iter().any(|p| {
                    p.principal_id == mandate.recipient && p.labor_unit_id.as_bytes() == *id
                })
        }) {
            return Err(MaterialWorldError::Wire);
        }
    }
    Ok(())
}
