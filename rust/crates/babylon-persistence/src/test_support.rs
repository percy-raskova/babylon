//! Explicit shipped-content fixture for native unit tests only.
use crate::michigan_material::MichiganMaterialCatalog;
use babylon_tick::material_world::MaterialTickReceipts;

pub(crate) fn catalog() -> MichiganMaterialCatalog {
    MichiganMaterialCatalog::from_defines_toml(
        &include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../content/scenarios/michigan/defines.toml"
        ))
        .replace(
            "DURATION = { kind = \"continuous\" }",
            "DURATION = { kind = \"finite\", final_period = 16 }",
        ),
    )
    .expect("shipped numeric material fixture")
}

pub(crate) fn material_receipts(period: u64) -> MaterialTickReceipts {
    MaterialTickReceipts {
        agency_paid: vec![],
        household_time: vec![],
        aid: vec![],
        collections: vec![],
        installation: vec![],
        installation_decisions: vec![],
        equipment_wear: vec![],
        investment: vec![],
        staffing_members: vec![],
        member_labor_use: vec![],
        public_budgets: vec![],
        taxes: vec![],
        distributions: vec![],
        company_basis: vec![],
        company_distributions: vec![],
        contributions: vec![],
        service_performance: vec![],
        household_services: vec![],
        service_markets: vec![],
        service_outputs: vec![],
        income: vec![],
        resolve_tick: period,
        household_demand: vec![],
        household_consumption: vec![],
        procurement: vec![],
        production_plans: vec![],
        prices: vec![],
        money_transfers: vec![],
        wage_accruals: vec![],
        labor_use: vec![],
        production: vec![],
        dispatches: vec![],
        losses: vec![],
        arrivals: vec![],
        deliveries: vec![],
        realizations: vec![],
        handling: vec![],
        local_fulfillments: vec![],
        local_transfers: vec![],
        maintenance: None,
    }
}
