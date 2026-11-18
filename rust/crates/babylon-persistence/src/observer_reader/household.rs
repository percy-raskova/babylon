//! One household's closed-period population, provisioning and time on the same durable source.
use super::{ObserverEconomyError, ObserverEconomyReader, ObserverMaterialCursor};
use crate::economic_catalog::{
    CatalogAccounting, CommodityLabel, EconomicOpening, EconomicSourceView,
};
use crate::economic_content::EconomicContentAdmission;
use crate::economic_flows::{self, Settlement};
use crate::identity::CampaignId;
use crate::michigan_economy;
use crate::money_journal::MoneyEndpoint;
use crate::national_household_allocation::HouseholdBudgetKey;
use crate::observer_material::{self, ObserverFrameClose};
use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::{
    AccountId, CashTransferPurpose, CircuitAccounting, FinalDemandPrincipalId, GoodId,
    HouseholdLifecycleReceipt, HouseholdStock, HouseholdTimeReceipt, MoneyLocation,
    MoneyTransferPurpose, OutboundOrderId, PublicTransferTreatment, ResidentAges, UnitId,
};
use babylon_tick::material_world::MaterialTickReceipts;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct HouseholdPeriodReport {
    pub version: u8,
    pub campaign: String,
    pub period: u64,
    pub household: String,
    pub residence: EconomicLocation,
    /// Immutable national opening identity, when this campaign captures a household budget.
    pub opening_role: Option<HouseholdOpeningRole>,
    pub foundation_sha256: String,
    pub world_sha256: String,
    pub tick_content_sha256: String,
    pub receipts_sha256: String,
    /// Absent when this principal has no captured age position.
    pub population: Option<HouseholdPopulationReport>,
    pub cash: HouseholdCash,
    pub income_support: Vec<HouseholdIncomeSupport>,
    pub goods: Vec<HouseholdGoodUse>,
    pub services: Vec<HouseholdServiceUse>,
    /// Absent in campaigns without household time accounting.
    pub time: Option<HouseholdHours>,
    pub workforce_attrition: Vec<HouseholdWorkforceRemoval>,
}

impl HouseholdPeriodReport {
    /// Version 3 adds the opening role and settled ownership payments and cash support.
    pub const VERSION: u8 = 3;
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct HouseholdOpeningRole {
    pub budget: HouseholdBudgetKey,
    /// Stable authored node name for a separately modeled aid household.
    pub authored_subject: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct AgeCounts {
    pub under_16: u64,
    pub age_16_17: u64,
    pub age_18_64: u64,
    pub age_65_plus: u64,
}
impl From<&ResidentAges> for AgeCounts {
    fn from(ages: &ResidentAges) -> Self {
        Self {
            under_16: ages.under_16,
            age_16_17: ages.age_16_17,
            age_18_64: ages.age_18_64,
            age_65_plus: ages.age_65_plus,
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct HouseholdPopulationReport {
    pub opening: AgeCounts,
    pub closing: AgeCounts,
    pub opening_households: u64,
    pub closing_households: u64,
    pub births: u64,
    pub deaths: AgeCounts,
    pub reached_16: u64,
    pub reached_18: u64,
    pub reached_65: u64,
}

/// Accrued claims and settled payments in nominal currency micros.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct HouseholdCash {
    #[serde(rename = "wages_accrued_micros")]
    pub wages_accrued: String,
    #[serde(rename = "wages_paid_micros")]
    pub wages_paid: String,
    #[serde(rename = "goods_purchases_settled_micros")]
    pub goods_purchases_settled: String,
    #[serde(rename = "service_purchases_settled_micros")]
    pub service_purchases_settled: String,
    /// Absent when the period has no monetary accounting.
    pub other_income_received: Option<HouseholdOtherIncomeReceived>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct HouseholdOtherIncomeReceived {
    #[serde(rename = "site_ownership_micros")]
    pub site_ownership: String,
    #[serde(rename = "company_ownership_micros")]
    pub company_ownership: String,
    #[serde(rename = "public_support_micros")]
    pub public_support: String,
    #[serde(rename = "mutual_aid_micros")]
    pub mutual_aid: String,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct HouseholdIncomeSupport {
    pub public_payer: String,
    pub requested_micros: String,
    pub paid_micros: String,
    pub unfunded_micros: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct HouseholdHours {
    pub available_at_open: u64,
    pub attended: u64,
    pub protected: u64,
    pub protected_unresolved: u64,
    pub unpaid_requested: u64,
    pub unpaid_allocated: u64,
    pub unpaid_unresolved: u64,
    pub available_for_contribution: u64,
    pub contribution_used: u64,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct HouseholdGoodUse {
    pub retailer_site_id: String,
    pub retailer_name: String,
    pub opening_stock: u64,
    pub requested: u64,
    pub admitted: u64,
    pub expired: u64,
    pub closing_stock: u64,
    pub good: String,
    pub unit: String,
    pub required: u64,
    pub purchased: u64,
    pub consumed: u64,
    pub unmet: u64,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct HouseholdServiceUse {
    pub good: String,
    pub unit: String,
    pub required: u64,
    pub delivered: u64,
    pub satisfied: u64,
    pub unmet: u64,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct HouseholdWorkforceRemoval {
    pub pool: String,
    pub member: String,
    pub opening_employed: u64,
    pub opening_reserve: u64,
    pub employed_removed: u64,
    pub reserve_removed: u64,
}

impl ObserverEconomyReader {
    /// Read demographic flows and actual household support, goods, services and time from the same committed close.
    /// # Errors
    /// Refuses restricted credentials, absent households or periods, and missing or inconsistent source receipts.
    pub fn household_period(
        &self,
        campaign: CampaignId,
        period: u64,
        principal: FinalDemandPrincipalId,
    ) -> Result<HouseholdPeriodReport, ObserverEconomyError> {
        self.with_committed_receipts(campaign, period, &mut None, |cursor, _, source| {
            cursor.household_period_for_frame(
                campaign,
                period,
                principal,
                source.identity.foundation_digest(),
                *source.identity.tick_content_hash().as_bytes(),
            )
        })
    }
}

impl ObserverMaterialCursor {
    /// Read one household's closed-period receipt from the full-observer frame already on screen.
    /// # Errors
    /// Refuses changed frames, absent households and inconsistent posting or provisioning evidence.
    pub fn household_period_for_frame(
        &self,
        campaign: CampaignId,
        tick: u64,
        principal: FinalDemandPrincipalId,
        foundation: [u8; 32],
        tick_hash: [u8; 32],
    ) -> Result<HouseholdPeriodReport, ObserverEconomyError> {
        let (admission, close) = self.displayed_frame(campaign, tick, foundation, tick_hash)?;
        read_household(campaign, &admission, close, principal)
    }
}

fn household_stocks(accounting: &CircuitAccounting) -> &[HouseholdStock] {
    match accounting {
        CircuitAccounting::Monetary(book) => book
            .recurring
            .as_ref()
            .map_or(&[], |economy| economy.household_stocks.as_slice()),
        CircuitAccounting::PhysicalControl => &[],
    }
}

fn read_household(
    campaign: CampaignId,
    admission: &EconomicContentAdmission,
    close: &ObserverFrameClose,
    id: FinalDemandPrincipalId,
) -> Result<HouseholdPeriodReport, ObserverEconomyError> {
    let opening = admission.view().opening;
    let before = close.opening(admission);
    let rows = &close.receipts;
    let settlements = economic_flows::account_settlements(
        rows,
        admission,
        before,
        &close.register,
        AccountId::Household(id),
    )
    .map_err(ObserverEconomyError::EconomicFlow)?;
    let contributions =
        observer_material::household_contributions(&close.register, close.identity.resolve_tick())?;
    let household = opening
        .households
        .iter()
        .find(|h| h.principal_id == id)
        .ok_or(ObserverEconomyError::HouseholdAbsent)?;
    let population = rows
        .household_lifecycle
        .iter()
        .find(|r| r.principal_id == id)
        .map(HouseholdPopulationReport::from);
    let hours = rows.household_time.iter().find(|r| r.principal_id == id);
    let contribution_used = contributions
        .iter()
        .filter(|r| r.contribution.principal_id == id)
        .try_fold(0_u64, |sum, r| sum.checked_add(r.contribution.hours))
        .ok_or(ObserverEconomyError::InvalidProjection)?;
    let time = hours.map(|row| HouseholdHours::from_close(row, contribution_used));
    let (goods, services) = provisions(
        opening,
        household_stocks(&before.state().accounting),
        rows,
        id,
    )?;
    let income_support = rows
        .public_budgets
        .iter()
        .filter(|r| {
            r.recipient == AccountId::Household(id)
                && r.treatment == PublicTransferTreatment::HouseholdIncomeSupport
        })
        .map(|r| HouseholdIncomeSupport {
            public_payer: michigan_economy::digest_hex(&r.public_account.as_bytes()),
            requested_micros: r.requested.micro_units().to_string(),
            paid_micros: r.paid.micro_units().to_string(),
            unfunded_micros: r.unfunded.micro_units().to_string(),
        })
        .collect();
    let workforce_attrition = rows
        .resident_workforce_attrition
        .iter()
        .filter(|r| r.principal_id == id)
        .map(|r| HouseholdWorkforceRemoval {
            pool: michigan_economy::digest_hex(&r.pool_id.as_bytes()),
            member: michigan_economy::digest_hex(&r.member_id.as_bytes()),
            opening_employed: r.opening_employed,
            opening_reserve: r.opening_reserve,
            employed_removed: r.employed_removed,
            reserve_removed: r.reserve_removed,
        })
        .collect();
    Ok(HouseholdPeriodReport {
        version: HouseholdPeriodReport::VERSION,
        campaign: campaign.as_uuid().to_string(),
        period: close.identity.resolve_tick(),
        household: michigan_economy::digest_hex(&id.as_bytes()),
        residence: household.location,
        opening_role: opening_role(admission, id, &household.subject)?,
        foundation_sha256: michigan_economy::digest_hex(&close.identity.foundation_digest()),
        world_sha256: michigan_economy::digest_hex(&close.identity.result_world_hash()),
        tick_content_sha256: michigan_economy::digest_hex(
            close.identity.tick_content_hash().as_bytes(),
        ),
        receipts_sha256: michigan_economy::digest_hex(&close.identity.receipt_digest()),
        population,
        time,
        goods,
        services,
        cash: cash(rows, &settlements, id, opening.accounting)?,
        income_support,
        workforce_attrition,
    })
}

fn opening_role(
    admission: &EconomicContentAdmission,
    id: FinalDemandPrincipalId,
    subject: &StableElementKey,
) -> Result<Option<HouseholdOpeningRole>, ObserverEconomyError> {
    if !matches!(
        admission.view().sources,
        EconomicSourceView::National { .. }
    ) {
        return Ok(None);
    }
    let catalog = admission
        .foundation()
        .graph_foundation()
        .content_bundle()
        .economic_catalog()
        .ok_or(ObserverEconomyError::InvalidProjection)?;
    let budget = catalog
        .national_household_budget(id)
        .ok_or(ObserverEconomyError::InvalidProjection)?;
    let authored_subject = catalog
        .national_aid_capture()
        .and_then(|capture| capture.children.iter().find(|child| child.principal == id))
        .map(|child| match &child.subject {
            StableElementKey::Node { local_name, .. } if &child.subject == subject => {
                Ok(local_name.clone())
            }
            _ => Err(ObserverEconomyError::InvalidProjection),
        })
        .transpose()?;
    Ok(Some(HouseholdOpeningRole {
        budget,
        authored_subject,
    }))
}

fn cash(
    receipts: &MaterialTickReceipts,
    settlements: &[Settlement],
    id: FinalDemandPrincipalId,
    accounting: CatalogAccounting,
) -> Result<HouseholdCash, ObserverEconomyError> {
    let account = AccountId::Household(id);
    let endpoint = MoneyEndpoint::from(account);
    let earned = receipts
        .wage_accruals
        .iter()
        .filter(|r| r.payee == account)
        .try_fold(0_i128, |total, r| total.checked_add(r.amount.micro_units()))
        .ok_or(ObserverEconomyError::InvalidProjection)?;
    let mut paid = 0_i128;
    let mut goods = 0_i128;
    let mut services = 0_i128;
    let mut site_ownership = 0_i128;
    let mut company_ownership = 0_i128;
    let mut public_support = 0_i128;
    let mut mutual_aid = 0_i128;
    for settlement in settlements {
        if settlement.recipient != endpoint && settlement.payer != endpoint {
            continue;
        }
        let n = usize::try_from(settlement.ordinal)
            .map_err(|_| ObserverEconomyError::InvalidProjection)?;
        let payment = receipts
            .money_transfers
            .get(n)
            .ok_or(ObserverEconomyError::InvalidProjection)?;
        let total = match (payment.purpose, settlement.recipient == endpoint) {
            (MoneyTransferPurpose::WagePayment(_), true) => &mut paid,
            (MoneyTransferPurpose::DeliverySettlement(order), false) => match order {
                OutboundOrderId::Service(_) => &mut services,
                OutboundOrderId::LocalFinalDemand(_) | OutboundOrderId::Delivery(_) => &mut goods,
            },
            (MoneyTransferPurpose::Cash(CashTransferPurpose::OwnershipDistribution), true) => {
                match payment.debit.location {
                    MoneyLocation::Cash(AccountId::Site(_)) => &mut site_ownership,
                    MoneyLocation::Cash(AccountId::Company(_)) => &mut company_ownership,
                    _ => return Err(ObserverEconomyError::InvalidProjection),
                }
            }
            (MoneyTransferPurpose::Cash(CashTransferPurpose::PublicTransfer), true) => {
                &mut public_support
            }
            (MoneyTransferPurpose::Cash(CashTransferPurpose::MutualAid), true) => &mut mutual_aid,
            _ => continue,
        };
        *total = total
            .checked_add(payment.credit.delta.micro_units())
            .ok_or(ObserverEconomyError::InvalidProjection)?;
    }
    Ok(HouseholdCash {
        wages_accrued: earned.to_string(),
        wages_paid: paid.to_string(),
        goods_purchases_settled: goods.to_string(),
        service_purchases_settled: services.to_string(),
        other_income_received: match accounting {
            CatalogAccounting::Monetary => Some(HouseholdOtherIncomeReceived {
                site_ownership: site_ownership.to_string(),
                company_ownership: company_ownership.to_string(),
                public_support: public_support.to_string(),
                mutual_aid: mutual_aid.to_string(),
            }),
            CatalogAccounting::PhysicalControl => None,
        },
    })
}

impl From<&HouseholdLifecycleReceipt> for HouseholdPopulationReport {
    fn from(flow: &HouseholdLifecycleReceipt) -> Self {
        Self {
            opening: (&flow.opening).into(),
            closing: (&flow.closing).into(),
            opening_households: flow.opening_households,
            closing_households: flow.closing_households,
            births: flow.births,
            deaths: (&flow.deaths).into(),
            reached_16: flow.reached_16,
            reached_18: flow.reached_18,
            reached_65: flow.reached_65,
        }
    }
}

impl HouseholdHours {
    fn from_close(time: &HouseholdTimeReceipt, contribution_used: u64) -> Self {
        Self {
            available_at_open: time.endowment_hours,
            attended: time.attended_hours,
            protected: time.protected_hours,
            protected_unresolved: time.protected_unresolved_hours,
            unpaid_requested: time.unpaid_requested_hours,
            unpaid_allocated: time.unpaid_allocated_hours,
            unpaid_unresolved: time.unpaid_unresolved_hours,
            available_for_contribution: time.contribution_available_hours,
            contribution_used,
        }
    }
}

fn provisions(
    opening: &EconomicOpening,
    stocks: &[HouseholdStock],
    rows: &MaterialTickReceipts,
    id: FinalDemandPrincipalId,
) -> Result<(Vec<HouseholdGoodUse>, Vec<HouseholdServiceUse>), ObserverEconomyError> {
    let labels: BTreeMap<_, _> = opening
        .commodity_labels
        .iter()
        .map(|g| ((g.good_id, g.unit_id), g))
        .collect();
    let label = |g: GoodId, u: UnitId| -> Result<&CommodityLabel, ObserverEconomyError> {
        labels
            .get(&(g, u))
            .copied()
            .ok_or(ObserverEconomyError::InvalidProjection)
    };
    let goods = rows
        .household_consumption
        .iter()
        .filter(|r| r.principal_id == id)
        .map(|r| {
            let name = label(r.good_id, r.unit_id)?;
            let key = (id, r.good_id, r.unit_id);
            let k = rows
                .household_demand
                .binary_search_by_key(&key, |d| (d.principal_id, d.good_id, d.unit_id))
                .map_err(|_| ObserverEconomyError::InvalidProjection)?;
            let demand = &rows.household_demand[k];
            if demand.required_quantity != r.required_quantity {
                return Err(ObserverEconomyError::InvalidProjection);
            }
            let retailer = opening
                .sites
                .iter()
                .find(|s| s.site_id == demand.retailer_site_id)
                .ok_or(ObserverEconomyError::InvalidProjection)?;
            // Inbound aid can reach the pantry between period open and order admission.
            let stock = stocks
                .binary_search_by_key(&key, |s| (s.principal_id, s.good_id, s.unit_id))
                .map_err(|_| ObserverEconomyError::InvalidProjection)?;
            Ok(HouseholdGoodUse {
                retailer_site_id: michigan_economy::digest_hex(&retailer.site_id.as_bytes()),
                retailer_name: retailer.label.clone(),
                opening_stock: stocks[stock].quantity,
                requested: demand.requested_quantity,
                admitted: demand.admitted_quantity,
                expired: demand.expired_quantity,
                closing_stock: r.closing_quantity,
                good: name.key.clone(),
                unit: name.unit_label.clone(),
                required: r.required_quantity,
                purchased: demand.fulfilled_quantity,
                consumed: r.consumed_quantity,
                unmet: r.unmet_quantity,
            })
        })
        .collect::<Result<_, ObserverEconomyError>>()?;
    let services = rows
        .household_services
        .iter()
        .filter(|r| r.principal_id == id)
        .map(|r| {
            let name = label(r.good_id, r.unit_id)?;
            Ok(HouseholdServiceUse {
                good: name.key.clone(),
                unit: name.unit_label.clone(),
                required: r.required_quantity,
                delivered: r.performed_quantity,
                satisfied: r.satisfied_quantity,
                unmet: r.unmet_quantity,
            })
        })
        .collect::<Result<_, ObserverEconomyError>>()?;
    Ok((goods, services))
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_kernel::currency::Currency;
    use babylon_material_circuit::CashTransferPurpose::{
        CapitalContribution, MutualAid, OwnershipDistribution, PublicTransfer,
    };
    use babylon_material_circuit::{
        CompanyId, MoneyPosting, MoneyTransferReceipt, PublicAccountId, SiteId,
    };

    #[test]
    fn household_cash_counts_only_settled_income_received_by_the_household() {
        let id = FinalDemandPrincipalId::from_bytes([1; 32]);
        let household = AccountId::Household(id);
        let site = AccountId::Site(SiteId::from_bytes([2; 32]));
        let company = AccountId::Company(CompanyId::from_bytes([3; 32]));
        let parent_company = AccountId::Company(CompanyId::from_bytes([6; 32]));
        let another = AccountId::Household(FinalDemandPrincipalId::from_bytes([4; 32]));
        let public = AccountId::Public(PublicAccountId::from_bytes([5; 32]));
        let mut receipts = crate::test_support::material_receipts(1);
        let mut settlements = Vec::new();
        for (payer, recipient, purpose, amount) in [
            (site, household, OwnershipDistribution, 17),
            (company, household, OwnershipDistribution, 31),
            (site, company, OwnershipDistribution, 47),
            (company, parent_company, OwnershipDistribution, 53),
            (company, another, OwnershipDistribution, 63),
            (household, site, CapitalContribution, 71),
            (public, household, PublicTransfer, 89),
            (another, household, MutualAid, 5),
            (household, another, MutualAid, 7),
        ] {
            let ordinal =
                u64::try_from(receipts.money_transfers.len()).expect("fixture has nine transfers");
            receipts.money_transfers.push(MoneyTransferReceipt {
                purpose: MoneyTransferPurpose::Cash(purpose),
                debit: MoneyPosting {
                    location: MoneyLocation::Cash(payer),
                    delta: Currency::from_micro_units(-amount),
                },
                credit: MoneyPosting {
                    location: MoneyLocation::Cash(recipient),
                    delta: Currency::from_micro_units(amount),
                },
            });
            settlements.push(Settlement {
                ordinal,
                payer: payer.into(),
                recipient: recipient.into(),
            });
        }
        // Use the same serialized output as the observer command.
        let report = cash(&receipts, &settlements, id, CatalogAccounting::Monetary)
            .expect("balanced fixture payments");
        let result = serde_json::to_value(report).expect("serializable report");
        let income = &result["other_income_received"];
        assert_eq!(income["site_ownership_micros"], "17");
        assert_eq!(income["company_ownership_micros"], "31");
        assert_eq!(income["public_support_micros"], "89");
        assert_eq!(income["mutual_aid_micros"], "5");
        assert!(cash(&receipts, &[], id, CatalogAccounting::PhysicalControl)
            .expect("physical control has no monetary settlements")
            .other_income_received
            .is_none());
    }
}
