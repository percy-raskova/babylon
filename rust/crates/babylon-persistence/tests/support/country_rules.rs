//! The rule sets of the country bench: the price of a short market, and the adjustment rules each
//! set asks for.
use super::country_bench::{BenchError, RuleSet};
use babylon_material_circuit::{AdjustmentRule, GoodId, MarketClearingPolicy, UnitId};
use babylon_persistence::economic_catalog::{EconomicCatalogError, EconomicOpening};
use std::collections::BTreeMap;

/// The seven products in the order a buyer's purse reaches them (price plan Task 8, decision 1).
pub const PAYING_ORDER: [&str; 7] = [
    "food",
    "materials",
    "utility",
    "housing",
    "household_services",
    "business_services",
    "resources",
];

/// The policy of a set, or `None` for the baseline. Labels are `CommodityLabel.key`.
///
/// # Errors
/// `BenchError::Opening` when a product of the paying order has no label in the opening.
pub fn market_policy(
    opening: &EconomicOpening,
    set: RuleSet,
) -> Result<Option<MarketClearingPolicy>, BenchError> {
    if let Some(own) = &opening.market_clearing {
        // The scenario names its own order of paying: the baseline and the market alone keep its
        // policy untouched, the other sets add their rules to it.
        let mut policy = own.clone();
        if !matches!(set, RuleSet::None | RuleSet::Market) {
            policy.plans_from_spare_money = true;
            policy.adjustments = rules_of(set);
        }
        return Ok(Some(policy));
    }
    if matches!(set, RuleSet::None) {
        return Ok(None);
    }
    let labels: BTreeMap<&str, (GoodId, UnitId)> = opening
        .commodity_labels
        .iter()
        .map(|row| (row.key.as_str(), (row.good_id, row.unit_id)))
        .collect();
    let mut paying_order = Vec::with_capacity(PAYING_ORDER.len());
    for key in PAYING_ORDER {
        let found = labels
            .get(key)
            .ok_or(BenchError::Opening(EconomicCatalogError::Opening(
                "a product of the paying order has no commodity label",
            )))?;
        paying_order.push(*found);
    }
    Ok(Some(MarketClearingPolicy {
        paying_order,
        household_wants: Vec::new(),
        plans_from_spare_money: !matches!(set, RuleSet::Market),
        adjustments: rules_of(set),
    }))
}

/// The adjustment rules of a set, in the order of `AdjustmentRule`. The stop rule needs the seekers, so
/// it is in the set that has them.
pub fn rules_of(set: RuleSet) -> Vec<AdjustmentRule> {
    match set {
        RuleSet::None | RuleSet::Market => Vec::new(),
        RuleSet::NoSeekers => vec![
            AdjustmentRule::HiringWithinMeans,
            AdjustmentRule::RestingPrice,
            AdjustmentRule::GoodsStepDown,
        ],
        RuleSet::AllSix | RuleSet::AllSixWithBenefits => vec![
            AdjustmentRule::HiringWithinMeans,
            AdjustmentRule::SeekingInPlace,
            AdjustmentRule::StopWithoutPay,
            AdjustmentRule::RestingPrice,
            AdjustmentRule::OwnerRestart { outlay_periods: 2 },
            AdjustmentRule::GoodsStepDown,
        ],
    }
}
