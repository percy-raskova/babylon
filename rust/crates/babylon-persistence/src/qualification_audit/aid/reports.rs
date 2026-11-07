//! Authenticate disclosed quantities against the dated material source independently of the journal.
use super::{postings, MaterialWorldRegister, Refusal, Result};
use crate::observer_reader::CommittedMaterialReceipts;
use babylon_material_circuit::{
    AccountId, CircuitAccounting, FinalDemandPrincipalId, GoodId, HouseholdDemandReceipt,
    LocalRetailFulfillmentReceipt, MaterialCatalog, MaterialCircuitState, MoneyLocation,
    MoneyTransferPurpose, MoneyTransferReceipt, OrderId, OutboundOrderId, SiteId, UnitId,
};
use babylon_practice_contract::{
    OrganizerAidBinding, OrganizerConfig, OrganizerObservation, OrganizerPartnerFacts,
    OrganizerPeriodJournalEntries, OrganizerReport, OrganizerReportCommodity,
    OrganizerServiceReport,
};
use babylon_tick::material_world::MaterialTickReceipts;
use serde::Serialize;
use std::collections::{BTreeMap, BTreeSet};

/// One independently reconstructed observation within its reader's existing sharing grant.
#[derive(Clone, Debug, Serialize)]
pub struct PartnerReport {
    actor_id: u64,
    subject_id: u64,
    source_actor_id: u64,
    observed_period: u64,
    acquired_period: u64,
    observation_id: [u8; 32],
    receipt_id: Option<[u8; 32]>,
    mandate_id: [u8; 32],
    source_hash: [u8; 32],
    facts: OrganizerPartnerFacts,
}

fn binding(
    config: &OrganizerConfig,
    catalog: &MaterialCatalog,
    row: &OrganizerAidBinding,
) -> Result<FinalDemandPrincipalId> {
    let mandate = super::one(
        catalog
            .aid_mandates
            .iter()
            .filter(|m| m.id == row.mandate_id),
        Refusal::ReportAuthority,
    )?;
    if mandate.source_hash != row.source_hash
        || mandate.recipient_actor != row.partner.actor_id
        || mandate.donor_actor != config.controlled_actor_id
        || mandate.recipient.as_bytes() != row.recipient_principal_id
        || row.report_sharing.food.iter().any(|c| {
            c.good_id != mandate.good_id.as_bytes() || c.unit_id != mandate.unit_id.as_bytes()
        })
        || row
            .report_sharing
            .participation_time
            .iter()
            .any(|u| *u != mandate.labor_unit_id.as_bytes())
    {
        return Err(Refusal::ReportAuthority);
    }
    Ok(mandate.recipient)
}

type Expected<'a> = Vec<(&'a OrganizerAidBinding, OrganizerPartnerFacts)>;

fn compare(
    config: &OrganizerConfig,
    tick: u64,
    actual: &[OrganizerObservation],
    expected: Expected<'_>,
) -> Result<Vec<PartnerReport>> {
    let mut rows = BTreeMap::new();
    for row in actual
        .iter()
        .filter(|o| matches!(o.report, OrganizerReport::Partner { .. }))
    {
        if rows.insert(row.observation_id, row).is_some() {
            return Err(Refusal::ReportGrant);
        }
    }
    let mut result = Vec::new();
    for (binding, facts) in expected {
        let observation = babylon_practice_contract::partner_observation(
            config,
            binding.partner.actor_id,
            tick,
            tick,
            facts.clone(),
        )
        .map_err(|_| Refusal::ReportGrant)?;
        if rows.remove(&observation.observation_id) != Some(&observation) {
            return Err(Refusal::ReportGrant);
        }
        result.push(PartnerReport {
            actor_id: observation.actor_id,
            subject_id: observation.subject_id,
            source_actor_id: observation.source_actor_id,
            observed_period: tick,
            acquired_period: tick,
            observation_id: observation.observation_id,
            receipt_id: observation.receipt_id,
            mandate_id: binding.mandate_id,
            source_hash: binding.source_hash,
            facts,
        });
    }
    if !rows.is_empty() {
        return Err(Refusal::ReportGrant);
    }
    result.sort_by_key(|r| r.observation_id);
    Ok(result)
}

/// Examine only the opening material register and its captured disclosure agreement.
/// # Errors
/// Refuses an ineligible topic, ambiguous source, or contradictory opening assessment.
pub fn opening_reports(
    catalog: &MaterialCatalog,
    register: &MaterialWorldRegister,
) -> Result<Vec<PartnerReport>> {
    if register.catalog_digest() != catalog.catalog_digest() {
        return Err(Refusal::Identity);
    }
    let config = register.organizer_config().ok_or(Refusal::Capture)?;
    if register.completed_tick() != 0 {
        return Err(Refusal::Period);
    }
    opening_from(config, catalog, register.state())
}

fn opening_from(
    config: &OrganizerConfig,
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
) -> Result<Vec<PartnerReport>> {
    let mut expected = Vec::new();
    for b in &config.aid_bindings {
        for commodity in &b.report_sharing.food {
            let principal = binding(config, catalog, b)?;
            let CircuitAccounting::Monetary(economy) = &state.accounting else {
                return Err(Refusal::ReportOpening);
            };
            let recurring = economy.recurring.as_ref().ok_or(Refusal::ReportOpening)?;
            let household = super::one(
                recurring
                    .households
                    .iter()
                    .filter(|r| r.principal_id == principal),
                Refusal::ReportOpening,
            )?;
            let need = super::one(
                catalog.household_needs.iter().filter(|r| {
                    r.principal_id == principal
                        && r.good_id.as_bytes() == commodity.good_id
                        && r.unit_id.as_bytes() == commodity.unit_id
                }),
                Refusal::ReportOpening,
            )?;
            let mut stock = recurring.household_stocks.iter().filter(|r| {
                r.principal_id == principal
                    && r.good_id == need.good_id
                    && r.unit_id == need.unit_id
            });
            let opening_stock = stock.next().map_or(0, |r| r.quantity);
            if stock.next().is_some() {
                return Err(Refusal::ReportOpening);
            }
            expected.push((
                b,
                OrganizerPartnerFacts::OpeningAssessment {
                    commodity: commodity.clone(),
                    required: need
                        .required_quantity(household)
                        .map_err(|_| Refusal::ReportOpening)?,
                    opening_stock,
                },
            ));
        }
    }
    compare(config, 0, &config.initial_observations, expected)
}

#[derive(Clone, Default)]
pub(super) struct RetailOpening {
    // Only the original captured identity and fixed price for a granted food order.
    prices: BTreeMap<OrderId, RetailTerms>,
}

#[derive(Clone)]
struct RetailTerms {
    buyer: FinalDemandPrincipalId,
    good: GoodId,
    unit: UnitId,
    seller: SiteId,
    price: i128,
}

impl RetailOpening {
    pub(super) fn capture(register: &MaterialWorldRegister) -> Result<Self> {
        let config = register.organizer_config().ok_or(Refusal::Capture)?;
        let mut prices = BTreeMap::new();
        let CircuitAccounting::Monetary(economy) = &register.state().accounting else {
            return Err(Refusal::Capture);
        };
        for order in &register.state().final_demand_orders {
            if order.ordered == order.fulfilled
                || !config.aid_bindings.iter().any(|b| {
                    b.recipient_principal_id == order.demand_principal_id.as_bytes()
                        && b.report_sharing.food.iter().any(|c| {
                            c.good_id == order.good_id.as_bytes()
                                && c.unit_id == order.unit_id.as_bytes()
                        })
                })
            {
                continue;
            }
            let escrow = economy
                .book
                .purchase(OutboundOrderId::LocalFinalDemand(order.order_id))
                .map_err(|_| Refusal::ReportRetail)?;
            if escrow.buyer != AccountId::Household(order.demand_principal_id)
                || escrow.seller != AccountId::Site(order.retailer_site_id)
                || prices
                    .insert(
                        order.order_id,
                        RetailTerms {
                            buyer: order.demand_principal_id,
                            good: order.good_id,
                            unit: order.unit_id,
                            seller: order.retailer_site_id,
                            price: escrow.unit_price.micro_units(),
                        },
                    )
                    .is_some()
            {
                return Err(Refusal::ReportRetail);
            }
        }
        Ok(Self { prices })
    }
}

// Signed postings are borrowed by typed order identity for this single admitted envelope.
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
enum Leg {
    Settlement,
    Refund,
}

struct Payments<'a> {
    rows: BTreeMap<(OutboundOrderId, Leg), &'a MoneyTransferReceipt>,
}

impl<'a> Payments<'a> {
    fn new(receipts: &'a MaterialTickReceipts) -> Result<Self> {
        let mut service_ids = BTreeSet::new();
        for r in &receipts.service_performance {
            if r.period != receipts.resolve_tick || !service_ids.insert(r.order_id) {
                return Err(Refusal::ReportSettlement);
            }
        }
        let mut rows = BTreeMap::new();
        for row in &receipts.money_transfers {
            let (id, leg) = match row.purpose {
                MoneyTransferPurpose::DeliverySettlement(id) => (id, Leg::Settlement),
                MoneyTransferPurpose::PurchaseRefund(id) => (id, Leg::Refund),
                _ => continue,
            };
            if let OutboundOrderId::Service(order) = id {
                if !service_ids.contains(&order) {
                    return Err(Refusal::ReportSettlement);
                }
            }
            if matches!(
                id,
                OutboundOrderId::LocalFinalDemand(_) | OutboundOrderId::Service(_)
            ) && rows.insert((id, leg), row).is_some()
            {
                return Err(Refusal::ReportSettlement);
            }
        }
        Ok(Self { rows })
    }

    fn amount(
        &self,
        id: OutboundOrderId,
        leg: Leg,
        account: AccountId,
        price: i128,
        quantity: u64,
    ) -> Result<i128> {
        let expected = price
            .checked_mul(i128::from(quantity))
            .ok_or(Refusal::Overflow)?;
        let total = if let Some(row) = self.rows.get(&(id, leg)) {
            let amount = row.credit.delta.micro_units();
            if row.debit.location != MoneyLocation::PurchaseReserve(id)
                || row.credit.location != MoneyLocation::Cash(account)
                || amount <= 0
                || amount.checked_neg() != Some(row.debit.delta.micro_units())
            {
                return Err(Refusal::ReportSettlement);
            }
            amount
        } else {
            0
        };
        if total != expected {
            return Err(Refusal::ReportSettlement);
        }
        Ok(total)
    }
}

fn handoff_price(
    h: &LocalRetailFulfillmentReceipt,
    demand: Option<&HouseholdDemandReceipt>,
    opening: &RetailOpening,
    payments: &Payments<'_>,
) -> Result<i128> {
    if let Some(d) = demand {
        if d.retailer_site_id != h.retailer_site_id || d.fulfilled_quantity != h.quantity {
            return Err(Refusal::ReportRetail);
        }
        Ok(d.unit_price.micro_units())
    } else {
        let terms = opening
            .prices
            .get(&h.order_id)
            .ok_or(Refusal::ReportRetail)?;
        if (terms.buyer, terms.good, terms.unit, terms.seller)
            != (
                h.demand_principal_id,
                h.good_id,
                h.unit_id,
                h.retailer_site_id,
            )
        {
            return Err(Refusal::ReportRetail);
        }
        payments.amount(
            OutboundOrderId::LocalFinalDemand(h.order_id),
            Leg::Refund,
            AccountId::Household(h.demand_principal_id),
            terms.price,
            0,
        )?;
        Ok(terms.price)
    }
}

fn food(
    receipts: &MaterialTickReceipts,
    opening: &RetailOpening,
    payments: &Payments<'_>,
    principal: FinalDemandPrincipalId,
    commodity: &OrganizerReportCommodity,
) -> Result<OrganizerPartnerFacts> {
    let row = super::one(
        receipts.household_consumption.iter().filter(|r| {
            r.principal_id == principal
                && r.good_id.as_bytes() == commodity.good_id
                && r.unit_id.as_bytes() == commodity.unit_id
        }),
        Refusal::ReportRetail,
    )?;
    if row.period != receipts.resolve_tick {
        return Err(Refusal::Period);
    }
    let mut orders = BTreeMap::new();
    for d in receipts.household_demand.iter().filter(|r| {
        r.principal_id == principal && r.good_id == row.good_id && r.unit_id == row.unit_id
    }) {
        if d.period != row.period || orders.insert(d.order_id, d).is_some() {
            return Err(Refusal::ReportRetail);
        }
    }
    let mut purchased = 0;
    let mut settled_micros = 0;
    let mut seen = BTreeSet::new();
    for h in receipts.local_fulfillments.iter().filter(|h| {
        h.demand_principal_id == principal && h.good_id == row.good_id && h.unit_id == row.unit_id
    }) {
        if h.quantity == 0 || !seen.insert(h.order_id) {
            return Err(Refusal::ReportRetail);
        }
        let price = handoff_price(h, orders.get(&h.order_id).copied(), opening, payments)?;
        super::add(&mut purchased, h.quantity)?;
        super::cash(
            &mut settled_micros,
            payments.amount(
                OutboundOrderId::LocalFinalDemand(h.order_id),
                Leg::Settlement,
                AccountId::Site(h.retailer_site_id),
                price,
                h.quantity,
            )?,
        )?;
    }
    let identity = (principal, row.good_id, row.unit_id);
    // An outstanding funded order can lack a recurring demand row. Any
    // settlement against its escrow still requires a matching handoff.
    if opening.prices.iter().any(|(order, terms)| {
        (terms.buyer, terms.good, terms.unit) == identity
            && !seen.contains(order)
            && payments
                .rows
                .contains_key(&(OutboundOrderId::LocalFinalDemand(*order), Leg::Settlement))
    }) {
        return Err(Refusal::ReportSettlement);
    }
    let selected = |id: &OrderId| seen.contains(id) || orders.contains_key(id);
    if receipts
        .local_fulfillments
        .iter()
        .any(|h| selected(&h.order_id) && (h.demand_principal_id, h.good_id, h.unit_id) != identity)
        || receipts
            .household_demand
            .iter()
            .any(|d| selected(&d.order_id) && (d.principal_id, d.good_id, d.unit_id) != identity)
    {
        return Err(Refusal::ReportRetail);
    }
    for d in orders.values() {
        if d.fulfilled_quantity > 0 && !seen.contains(&d.order_id) {
            return Err(Refusal::ReportRetail);
        }
        let id = OutboundOrderId::LocalFinalDemand(d.order_id);
        if d.fulfilled_quantity == 0 {
            payments.amount(
                id,
                Leg::Settlement,
                AccountId::Site(d.retailer_site_id),
                d.unit_price.micro_units(),
                0,
            )?;
        }
        payments.amount(
            id,
            Leg::Refund,
            AccountId::Household(principal),
            d.unit_price.micro_units(),
            d.expired_quantity,
        )?;
    }
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

fn service(
    receipts: &MaterialTickReceipts,
    payments: &Payments<'_>,
    principal: FinalDemandPrincipalId,
    commodity: &OrganizerReportCommodity,
) -> Result<OrganizerServiceReport> {
    let row = super::one(
        receipts.household_services.iter().filter(|r| {
            r.principal_id == principal
                && r.good_id.as_bytes() == commodity.good_id
                && r.unit_id.as_bytes() == commodity.unit_id
        }),
        Refusal::ReportService,
    )?;
    if row.period != receipts.resolve_tick {
        return Err(Refusal::Period);
    }
    let buyer = AccountId::Household(principal);
    let mut performed = 0;
    let mut expired = 0;
    let mut satisfied = 0;
    let mut unused = 0;
    let mut settled_micros = 0;
    let mut refunded_micros = 0;
    for p in receipts
        .service_performance
        .iter()
        .filter(|r| r.buyer == buyer && r.good_id == row.good_id && r.unit_id == row.unit_id)
    {
        let order = OutboundOrderId::Service(p.order_id);
        super::add(&mut performed, p.performed_quantity)?;
        super::add(&mut expired, p.expired_quantity)?;
        super::add(&mut satisfied, p.used_quantity)?;
        super::add(&mut unused, p.unused_quantity)?;
        super::cash(
            &mut settled_micros,
            payments.amount(
                order,
                Leg::Settlement,
                AccountId::Site(p.provider_site_id),
                p.unit_price.micro_units(),
                p.performed_quantity,
            )?,
        )?;
        super::cash(
            &mut refunded_micros,
            payments.amount(
                order,
                Leg::Refund,
                buyer,
                p.unit_price.micro_units(),
                p.expired_quantity,
            )?,
        )?;
    }
    if (performed, satisfied, unused)
        != (
            row.performed_quantity,
            row.satisfied_quantity,
            row.unused_quantity,
        )
    {
        return Err(Refusal::ReportService);
    }
    Ok(OrganizerServiceReport {
        commodity: commodity.clone(),
        required: row.required_quantity,
        performed,
        satisfied,
        unmet: row.unmet_quantity,
        unused,
        expired,
        settled_micros,
        refunded_micros,
    })
}

fn check_observation_receipts(journal: &OrganizerPeriodJournalEntries) -> Result<()> {
    for obs in &journal.observations {
        if matches!(
            obs.report,
            OrganizerReport::Work { .. } | OrganizerReport::Maintenance { .. }
        ) && obs.receipt_id.is_none()
        {
            return Err(Refusal::ReportGrant);
        }
        if let Some(id) = obs.receipt_id {
            let receipt = super::one(
                journal.receipts().filter(|r| r.receipt_id == id),
                Refusal::ReportGrant,
            )?;
            if receipt.actor_id != obs.actor_id
                || receipt.period != obs.acquired_period
                || !receipt.observation_ids.contains(&obs.observation_id)
            {
                return Err(Refusal::ReportGrant);
            }
        }
    }
    for receipt in journal.receipts() {
        let mut seen = BTreeSet::new();
        for id in &receipt.observation_ids {
            let observation = super::one(
                journal
                    .observations
                    .iter()
                    .filter(|r| r.observation_id == *id),
                Refusal::ReportGrant,
            )?;
            if !seen.insert(id) || observation.receipt_id != Some(receipt.receipt_id) {
                return Err(Refusal::ReportGrant);
            }
        }
    }
    Ok(())
}

pub(super) fn closed(
    catalog: &MaterialCatalog,
    register: &MaterialWorldRegister,
    admitted: &CommittedMaterialReceipts,
    opening: &RetailOpening,
) -> Result<Vec<PartnerReport>> {
    let config = register.organizer_config().ok_or(Refusal::Capture)?;
    let journal = register
        .organizer_journal()
        .and_then(|j| j.latest())
        .ok_or(Refusal::ReportGrant)?;
    let receipts = &admitted.receipts;
    let tick = receipts.resolve_tick;
    if journal.period != tick {
        return Err(Refusal::ReportGrant);
    }
    check_observation_receipts(journal)?;
    if config.aid_bindings.iter().all(|binding| {
        let scope = &binding.report_sharing;
        scope.food.is_empty()
            && scope.essential_services.is_empty()
            && scope.participation_time.is_empty()
    }) {
        return compare(config, tick, &journal.observations, Vec::new());
    }
    let payments = Payments::new(receipts)?;
    let mut expected = Vec::new();
    for b in &config.aid_bindings {
        let scope = &b.report_sharing;
        let principal = binding(config, catalog, b)?;
        for commodity in &scope.food {
            expected.push((b, food(receipts, opening, &payments, principal, commodity)?));
        }
        if !scope.essential_services.is_empty() {
            let services = scope
                .essential_services
                .iter()
                .map(|c| service(receipts, &payments, principal, c))
                .collect::<Result<_>>()?;
            expected.push((b, OrganizerPartnerFacts::EssentialServices { services }));
        }
        for &unit in &scope.participation_time {
            let remaining = postings::remaining(
                &receipts.household_time,
                &admitted.household_contributions,
                principal,
                tick,
                unit,
            )?;
            let r = super::one(
                receipts
                    .household_time
                    .iter()
                    .filter(|r| r.principal_id == principal && r.labor_unit_id.as_bytes() == unit),
                Refusal::ReportGrant,
            )?;
            let contributed = r
                .contribution_available_hours
                .checked_sub(remaining)
                .ok_or(Refusal::Overflow)?;
            expected.push((
                b,
                OrganizerPartnerFacts::ParticipationTime {
                    labor_unit: unit,
                    attended: r.attended_hours,
                    protected: r.protected_hours,
                    unpaid: r.unpaid_allocated_hours,
                    contributed,
                    remaining,
                },
            ));
        }
    }
    compare(config, tick, &journal.observations, expected)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::organizer_aid_fixture as fixture;
    use crate::receipt_storage::agency_paid_tests::control;
    use babylon_material_circuit::HouseholdStock;

    fn commodity(id: u8) -> OrganizerReportCommodity {
        OrganizerReportCommodity {
            good_id: control::good(id).as_bytes(),
            unit_id: control::unit(id).as_bytes(),
            label: format!("Commodity {id}"),
            unit_label: "unit".into(),
        }
    }

    #[test]
    fn admitted_retail_and_service_refuse_missing_paid_or_refunded_transfers() {
        use babylon_tick::material_world;

        let (catalog, mut state) = control::opening();
        state
            .production_commitments
            .retain(|p| p.site_id != control::site(3));
        let close = control::close(&catalog, &state, &[], &[]).expect("actual material close");
        let bytes =
            material_world::encode_material_receipts(&catalog, 1, &close).expect("canonical close");
        let receipts = material_world::decode_material_receipts(&bytes).expect("admitted receipts");
        let principal = control::donor();
        let opening = RetailOpening::default();
        let payments = Payments::new(&receipts).expect("dated transfers");
        let OrganizerPartnerFacts::FoodProvision {
            purchased,
            settled_micros,
            ..
        } = food(&receipts, &opening, &payments, principal, &commodity(2)).expect("funded food")
        else {
            panic!("food provision")
        };
        assert!(purchased > 0 && settled_micros > 0);
        let paid = service(&receipts, &payments, principal, &commodity(4)).expect("paid service");
        let expired =
            service(&receipts, &payments, principal, &commodity(3)).expect("expired service");
        assert!(paid.performed > 0 && paid.settled_micros > 0);
        assert!(expired.performed == 0 && expired.expired > 0 && expired.refunded_micros > 0);
        let retail = receipts
            .local_fulfillments
            .iter()
            .find(|r| r.demand_principal_id == principal && r.good_id == control::good(2))
            .expect("actual food handoff");
        let mut damaged = receipts.clone();
        damaged.money_transfers.retain(|r| {
            r.purpose
                != MoneyTransferPurpose::DeliverySettlement(OutboundOrderId::LocalFinalDemand(
                    retail.order_id,
                ))
        });
        let missing = Payments::new(&damaged).expect("remaining indexed transfers");
        assert!(matches!(
            food(&damaged, &opening, &missing, principal, &commodity(2)),
            Err(Refusal::ReportSettlement)
        ));
        for (id, leg) in [(3, Leg::Refund), (4, Leg::Settlement)] {
            let mut damaged = receipts.clone();
            let order = receipts
                .service_performance
                .iter()
                .find(|r| {
                    r.buyer == AccountId::Household(principal) && r.good_id == control::good(id)
                })
                .expect("actual scoped service order")
                .order_id;
            let purpose = match leg {
                Leg::Refund => {
                    MoneyTransferPurpose::PurchaseRefund(OutboundOrderId::Service(order))
                }
                Leg::Settlement => {
                    MoneyTransferPurpose::DeliverySettlement(OutboundOrderId::Service(order))
                }
            };
            damaged.money_transfers.retain(|r| r.purpose != purpose);
            let missing = Payments::new(&damaged).expect("remaining indexed transfers");
            assert!(matches!(
                service(&damaged, &missing, principal, &commodity(id)),
                Err(Refusal::ReportSettlement)
            ));
        }
        let mut damaged = receipts;
        damaged
            .service_performance
            .retain(|r| r.good_id != control::good(3));
        assert!(matches!(
            Payments::new(&damaged),
            Err(Refusal::ReportSettlement)
        ));
    }

    #[test]
    fn separate_opening_sharing_and_actual_stock_control_each_canonical_grant() {
        let mut config = fixture::config();
        let session = fixture::authored_session(
            crate::michigan_dynamic_hex_foundation().expect("Michigan opening"),
            config.clone(),
            false,
            false,
        );
        let state = session.material().state();
        let catalog = session.catalog();
        let withheld =
            opening_from(&config, catalog, state).expect("withheld sharing needs no grant");
        assert!(withheld.is_empty());
        let b = &config.aid_bindings[0];
        let m = &catalog.aid_mandates[0];
        let commodity = OrganizerReportCommodity {
            good_id: m.good_id.as_bytes(),
            unit_id: m.unit_id.as_bytes(),
            label: "Food".into(),
            unit_label: "unit".into(),
        };
        let actor = b.partner.actor_id;
        let principal = m.recipient;
        let CircuitAccounting::Monetary(economy) = &state.accounting else {
            panic!("monetary opening")
        };
        let recurring = economy.recurring.as_ref().expect("households");
        let need = catalog
            .household_needs
            .iter()
            .find(|n| {
                n.principal_id == principal && n.good_id == m.good_id && n.unit_id == m.unit_id
            })
            .expect("captured need");
        let household = recurring
            .households
            .iter()
            .find(|h| h.principal_id == principal)
            .expect("captured household");
        let quantity = recurring
            .household_stocks
            .iter()
            .filter(|r| {
                r.principal_id == principal && r.good_id == m.good_id && r.unit_id == m.unit_id
            })
            .map(|r| r.quantity)
            .sum();
        let facts = OrganizerPartnerFacts::OpeningAssessment {
            commodity: commodity.clone(),
            required: need
                .required_quantity(household)
                .expect("actual requirement"),
            opening_stock: quantity,
        };
        config.aid_bindings[0].report_sharing.food.push(commodity);
        assert!(
            opening_from(&config, catalog, state).is_err(),
            "required zero-stock observation is absent"
        );
        let actual = babylon_practice_contract::partner_observation(&config, actor, 0, 0, facts)
            .expect("actual canonical partner observation");
        config.initial_observations.push(actual);
        let valid = opening_from(&config, catalog, state).expect("whole admitted grant");
        assert_eq!(valid.len(), 1);
        assert_eq!(valid[0].receipt_id, None);
        let mut changed = state.clone();
        let CircuitAccounting::Monetary(economy) = &mut changed.accounting else {
            panic!("monetary opening")
        };
        let stocks = &mut economy
            .recurring
            .as_mut()
            .expect("households")
            .household_stocks;
        if let Some(s) = stocks.iter_mut().find(|r| {
            r.principal_id == principal && r.good_id == m.good_id && r.unit_id == m.unit_id
        }) {
            s.quantity += 1;
        } else {
            stocks.push(HouseholdStock {
                principal_id: principal,
                good_id: m.good_id,
                unit_id: m.unit_id,
                quantity: 1,
            });
        }
        assert!(
            opening_from(&config, catalog, &changed).is_err(),
            "changing stock behind the same report"
        );
        check_crossed_opening(&config, catalog, state);
    }

    fn check_crossed_opening(
        config: &OrganizerConfig,
        catalog: &MaterialCatalog,
        state: &MaterialCircuitState,
    ) {
        for change in 0..4 {
            let mut other = config.clone();
            let observation = other
                .initial_observations
                .last_mut()
                .expect("opening grant");
            match change {
                0 => observation.receipt_id = Some([9; 32]),
                1 => observation.source_actor_id += 1,
                2 => other.aid_bindings[0].report_sharing.food.clear(),
                _ => other.aid_bindings[0].source_hash = [10; 32],
            }
            assert!(
                opening_from(&other, catalog, state).is_err(),
                "crossed opening permission or source {change}"
            );
        }
    }
}
