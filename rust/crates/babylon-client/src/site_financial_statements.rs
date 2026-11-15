//! Headless selected-site statement consumer with exact decimal micro-currency.
use babylon_material_circuit::{
    AccountId, CashTransferPurpose, IncomeReceipt, IncomeStatement, MoneyLocation,
    MoneyTransferPurpose, SiteId,
};
use babylon_persistence::identity::CampaignId;
use babylon_persistence::observer_reader::ObserverEconomyReader;
use babylon_persistence::site_financial_statements::{
    CashFlowCategory, CashFlowStatement, SiteBalanceSheet, SiteFinancialStatements,
};
use serde_json::Value;

pub(crate) fn sites(campaign: CampaignId) -> Result<Value, String> {
    let snapshot = ObserverEconomyReader::from_observer_env()
        .map_err(|e| e.to_string())?
        .snapshot(campaign, 0)
        .map_err(|e| e.to_string())?;
    let production = snapshot
        .production
        .ok_or("Economic site projection unavailable")?;
    Ok(
        serde_json::json!({"record": "economy-sites", "schema_version": 1,
        "campaign_id": campaign.as_uuid().to_string(), "resolve_tick": 0,
        "foundation_digest": snapshot.foundation_digest,
        "sites": production.sites.iter().map(|site| serde_json::json!({"site_id": site.id, "label": crate::production::site_subject(site)})).collect::<Vec<_>>() }),
    )
}

pub(crate) fn read(campaign: CampaignId, site: SiteId, period: u64) -> Result<Value, String> {
    let statements = ObserverEconomyReader::from_observer_env()
        .map_err(|e| e.to_string())?
        .site_financial_statements(campaign, period, site)
        .map_err(|e| e.to_string())?;
    Ok(render(&statements))
}

fn hex(bytes: [u8; 32]) -> String {
    crate::dossier::hex_bytes(bytes)
}
fn account(id: AccountId) -> Value {
    let (kind, bytes) = match id {
        AccountId::Site(id) => ("site", id.as_bytes()),
        AccountId::Household(id) => ("household", id.as_bytes()),
        AccountId::Organization(id) => ("organization", id.as_bytes()),
        AccountId::Public(id) => ("public", id.as_bytes()),
    };
    serde_json::json!({"kind": kind, "id": hex(bytes)})
}

macro_rules! amounts {
    ($row:expr; $($field:ident),+ $(,)?) => { serde_json::json!({ $(stringify!($field): $row.$field.micro_units().to_string()),+ }) };
}

fn balance(row: &SiteBalanceSheet) -> Value {
    amounts!(row; cash, purchase_reserves, payroll_reserves, wage_receivables, inventory,
        freight, equity_investments, equipment, total_assets, wage_payables,
        total_liabilities, opening_capital, contributed_capital, retained_earnings, total_equity)
}
fn income(row: &IncomeReceipt) -> Value {
    let mut value = amounts!(row; opening_capital, opening_retained_earnings,
        opening_contributed_capital, contributions_received, closing_contributed_capital,
        distributions_paid, net_income, closing_retained_earnings);
    value["account"] = account(row.account);
    value["period"] = row.period.into();
    value["statement"] = income_lines(&row.statement);
    value
}
fn income_lines(row: &IncomeStatement) -> Value {
    amounts!(row; sales, wage_income, cost_of_goods_sold, productive_labor_capitalized,
        installation_labor_capitalized, equipment_wear_capitalized, idle_labor_expense,
        handling_expense, maintenance_labor_expense, maintenance_material_expense,
        freight_loss_expense, consumption_expense, final_demand_outlay, unused_service_expense,
        tax_income, tax_expense, public_transfer_income, public_transfer_expense,
        distribution_income, gift_income, gift_expense, agency_observation_labor_expense)
}
fn purpose(value: MoneyTransferPurpose) -> &'static str {
    match value {
        MoneyTransferPurpose::PurchaseReservation(_) => "purchase_reservation",
        MoneyTransferPurpose::DeliverySettlement(_) => "delivery_settlement",
        MoneyTransferPurpose::PurchaseRefund(_) => "purchase_refund",
        MoneyTransferPurpose::ShiftReservation(_) => "shift_reservation",
        MoneyTransferPurpose::WagePayment(_) => "wage_payment",
        MoneyTransferPurpose::ShiftCancellation(_) => "shift_cancellation",
        MoneyTransferPurpose::Cash(value) => match value {
            CashTransferPurpose::Tax => "tax",
            CashTransferPurpose::PublicTransfer => "public_transfer",
            CashTransferPurpose::HouseholdTransfer => "household_transfer",
            CashTransferPurpose::OwnershipDistribution => "ownership_distribution",
            CashTransferPurpose::CapitalContribution => "capital_contribution",
            CashTransferPurpose::TransportService => "transport_service",
            CashTransferPurpose::MutualAid => "mutual_aid",
        },
    }
}
fn cash_flow(row: &CashFlowStatement, site: SiteId) -> Value {
    let mut value = amounts!(row; operating, investing, financing, reserve_reclassification,
        net_change_in_cash, opening_cash, closing_cash, change_in_purchase_reserves, change_in_payroll_reserves);
    value["basis"] = "spendable_cash_excludes_purchase_and_payroll_reserves".into();
    value["reserve_reclassification_basis"] = "cash moved to or from a named purchase/payroll reserve without exact current-period investment evidence; unproved operating/investing use is not inferred".into();
    value["transfers"] = row.transfers.iter().map(|evidence| {
        let transfer = &evidence.transfer;
        let category = match evidence.category {
            CashFlowCategory::Operating => "operating", CashFlowCategory::Investing => "investing",
            CashFlowCategory::Financing => "financing", CashFlowCategory::ReserveReclassification => "reserve_reclassification",
        };
        let delta = if transfer.debit.location == MoneyLocation::Cash(AccountId::Site(site)) { transfer.debit.delta } else { transfer.credit.delta };
        serde_json::json!({"receipt_index": evidence.receipt_index, "purpose": purpose(transfer.purpose), "category": category, "cash_delta": delta.micro_units().to_string()})
    }).collect::<Vec<_>>().into();
    value
}
fn render(row: &SiteFinancialStatements) -> Value {
    serde_json::json!({
        "record": "site-financial-statements", "schema_version": 1,
        "campaign_id": row.campaign_id.as_uuid().to_string(), "site_id": hex(row.site_id.as_bytes()),
        "resolve_tick": row.resolve_tick, "visibility": "full_observer", "evidence_class": "designed",
        "valuation_basis": "governed_historical_carrying_cost", "money_encoding": "decimal_micro_currency_strings",
        "foundation_digest": hex(row.foundation_digest), "nominal_world_hash": row.nominal_world_hash.map(hex),
        "tick_content_hash": row.tick_content_hash.map(hex), "receipt_digest": row.receipt_digest.map(hex),
        "planning_control": {"availability": "not_captured"},
        "ownership_claims": row.books.ownership_claims.iter().map(|claim| serde_json::json!({"beneficiary": account(claim.beneficiary), "shares": claim.shares})).collect::<Vec<_>>(),
        "opening": row.books.opening.as_ref().map(balance), "closing": balance(&row.books.closing),
        "activity": row.books.activity.as_ref().map(|activity| serde_json::json!({
            "income": income(&activity.income), "change_in_equity": activity.change_in_equity.micro_units().to_string(),
            "cash_flow": cash_flow(&activity.cash_flow, row.site_id),
        }))
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_kernel::currency::Currency;

    #[test]
    fn balance_json_preserves_exact_i128_strings_and_explicit_zero() {
        let zero = Currency::from_micro_units(0);
        let maximum = Currency::from_micro_units(i128::MAX);
        let row = SiteBalanceSheet {
            cash: maximum,
            purchase_reserves: zero,
            payroll_reserves: zero,
            wage_receivables: zero,
            inventory: zero,
            freight: zero,
            equity_investments: zero,
            equipment: zero,
            total_assets: maximum,
            wage_payables: zero,
            total_liabilities: zero,
            opening_capital: maximum,
            contributed_capital: zero,
            retained_earnings: zero,
            total_equity: maximum,
        };
        let rendered = balance(&row);
        assert_eq!(rendered["cash"], i128::MAX.to_string());
        assert_eq!(rendered["purchase_reserves"], "0");
        assert_eq!(rendered["total_equity"], rendered["total_assets"]);
        serde_json::to_string(&rendered)
            .expect("exact decimal money JSON serializes at i128 limits");
    }
}
