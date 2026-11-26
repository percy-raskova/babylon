//! Compact shared recipes and household needs; no site gets its own template copy.
use super::{markets, Builder, NationalOpeningError, Result};
use crate::economic_catalog::{
    CommodityAmount, CommodityLabel, EconomicHouseholdSeed, HouseholdNeedCoefficient,
    HouseholdTemplate, HouseholdTemplateId, LaborRequirement, RecipeTemplate, RecipeTemplateId,
};
use crate::national_economy::grain::{FinancialDomainId, ReservePosition};
use crate::national_economy::{GameHandling, GameWant, NationalGamePolicy};
use babylon_kernel::economic_identity::{EconomicFunction, TradeSet};
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::HouseholdNeedBasis;
use babylon_material_circuit::{
    AccountId, CommodityDefinition, CommodityKind, FinalDemandPrincipalId, HouseholdKind,
    HouseholdWant, MarketClearingPolicy, UnitId, WantTier, MAX_HOUSEHOLD_WANTS,
};
use std::collections::BTreeMap;

type Templates = (
    Vec<CommodityDefinition>,
    Vec<CommodityLabel>,
    Vec<RecipeTemplate>,
    Vec<HouseholdTemplate>,
);

/// The recipe id of a trade is its position in the scenario's trade list, plus one.
pub(super) fn recipe_id(trades: TradeSet, function: EconomicFunction) -> Result<RecipeTemplateId> {
    let index = trades
        .functions()
        .iter()
        .position(|f| *f == function)
        .ok_or(NationalOpeningError::Policy)?;
    Ok(RecipeTemplateId(
        u16::try_from(index + 1).map_err(|_| NationalOpeningError::Arithmetic)?,
    ))
}

pub(super) fn compile(policy: &NationalGamePolicy, unit: UnitId) -> Result<Templates> {
    let commodities = policy
        .commodities
        .values()
        .map(|g| CommodityDefinition {
            good_id: g.good_id,
            unit_id: g.unit_id,
            kind: g.kind,
        })
        .collect();
    let labels = policy
        .commodities
        .iter()
        .map(|(key, g)| CommodityLabel {
            good_id: g.good_id,
            unit_id: g.unit_id,
            key: key.clone(),
            label: g.label.clone(),
            unit_label: g.unit_label.clone(),
        })
        .collect();
    let recipes = policy
        .recipes
        .iter()
        .map(|(function, recipe)| {
            Ok(RecipeTemplate {
                id: recipe_id(policy.trades, *function)?,
                output: commodity(policy, &recipe.output, recipe.output_units_per_batch)?,
                inputs: recipe
                    .inputs
                    .iter()
                    .map(|(key, n)| commodity(policy, key, *n))
                    .collect::<Result<Vec<_>>>()?,
                labor: Some(LaborRequirement {
                    unit_id: unit,
                    hours_per_batch: recipe.labor_hours_per_batch,
                }),
            })
        })
        .collect::<Result<Vec<_>>>()?;
    let needs = policy
        .household_needs
        .iter()
        .map(|n| {
            let good = policy
                .commodities
                .get(&n.key)
                .ok_or(NationalOpeningError::Policy)?;
            Ok(HouseholdNeedCoefficient {
                good_id: good.good_id,
                unit_id: good.unit_id,
                basis: n.basis,
                units_per_basis: n.units_per_basis,
            })
        })
        .collect::<Result<Vec<_>>>()?;
    let person_needs = needs
        .iter()
        .filter(|n| n.basis == HouseholdNeedBasis::Persons)
        .cloned()
        .collect();
    Ok((
        commodities,
        labels,
        recipes,
        vec![
            HouseholdTemplate {
                id: HouseholdTemplateId(1),
                needs,
            },
            HouseholdTemplate {
                id: HouseholdTemplateId(2),
                needs: person_needs,
            },
        ],
    ))
}
fn commodity(policy: &NationalGamePolicy, key: &str, quantity: u64) -> Result<CommodityAmount> {
    let good = policy
        .commodities
        .get(key)
        .ok_or(NationalOpeningError::Policy)?;
    if quantity == 0 {
        return Err(NationalOpeningError::Policy);
    }
    Ok(CommodityAmount {
        good_id: good.good_id,
        unit_id: good.unit_id,
        quantity,
    })
}

/// The products that clear by price, in the policy's order of paying: `None` for a policy with no order
/// (schema 7 and earlier). No wants (stage 5), no plans from spare money and no adjustment rule: the
/// country bench turns rules on itself.
pub(super) fn market_clearing(policy: &NationalGamePolicy) -> Result<Option<MarketClearingPolicy>> {
    let Some(order) = &policy.markets.paying_order else {
        return Ok(None);
    };
    let paying_order = order
        .iter()
        .map(|key| {
            let good = policy
                .commodities
                .get(key)
                .ok_or(NationalOpeningError::Policy)?;
            Ok((good.good_id, good.unit_id))
        })
        .collect::<Result<Vec<_>>>()?;
    Ok(Some(MarketClearingPolicy {
        paying_order,
        household_wants: vec![],
        plans_from_spare_money: false,
        adjustments: vec![],
    }))
}

/// The want's coefficient for an account: a luxury of an account named in the luxury scales is
/// `floor(units_per_basis x bps / 10_000)`, so the engine's `units_per_basis x count` is the scaled
/// want; a comfort is never scaled.
pub(super) fn scaled_units(want: &GameWant, scale_bps: Option<u32>) -> Result<u64> {
    let Some(bps) = scale_bps.filter(|_| want.tier == WantTier::Luxury) else {
        return Ok(want.units_per_basis);
    };
    let scaled = u128::from(want.units_per_basis) * u128::from(bps) / 10_000;
    u64::try_from(scaled).map_err(|_| NationalOpeningError::Arithmetic)
}

/// The wants of every household account of the opening, in canonical order (principal, tier, good,
/// unit). `scales` holds the luxury scale of each account named in the scenario's luxury scales.
/// A want on the households of a collective residence is left out, as a household need is.
pub(super) fn household_wants(
    policy: &NationalGamePolicy,
    households: &[EconomicHouseholdSeed],
    scales: &BTreeMap<FinalDemandPrincipalId, u32>,
) -> Result<Vec<HouseholdWant>> {
    let mut rows = Vec::new();
    for household in households {
        for want in &policy.household_wants {
            if household.kind == HouseholdKind::CollectiveResidence
                && want.basis == HouseholdNeedBasis::Households
            {
                continue;
            }
            let good = policy
                .commodities
                .get(&want.key)
                .ok_or(NationalOpeningError::Policy)?;
            rows.push(HouseholdWant {
                principal_id: household.principal_id,
                tier: want.tier,
                good_id: good.good_id,
                unit_id: good.unit_id,
                basis: want.basis,
                units_per_basis: scaled_units(want, scales.get(&household.principal_id).copied())?,
            });
        }
    }
    if rows.len() > MAX_HOUSEHOLD_WANTS {
        return Err(NationalOpeningError::Bounds);
    }
    rows.sort_unstable_by_key(|w| (w.principal_id, w.tier, w.good_id, w.unit_id));
    Ok(rows)
}

/// The storable goods the shop handles: every storable good a need or a want names, needs first in
/// their order, with its handling.
pub(super) fn shop_goods(policy: &NationalGamePolicy) -> Result<Vec<(String, GameHandling)>> {
    let keys = policy
        .household_needs
        .iter()
        .map(|need| &need.key)
        .chain(policy.household_wants.iter().map(|want| &want.key));
    let mut goods: Vec<(String, GameHandling)> = Vec::new();
    for key in keys {
        let good = policy
            .commodities
            .get(key)
            .ok_or(NationalOpeningError::Policy)?;
        if matches!(good.kind, CommodityKind::Storable { .. }) && !goods.iter().any(|g| &g.0 == key)
        {
            goods.push((key.clone(), markets::handling(policy, key)?));
        }
    }
    Ok(goods)
}

/// A part's label in the scenario: its hub's geoid, then `/<position>` for a part with a position;
/// a counterpart's key; a dependency's code.
fn part_label(domain: FinancialDomainId) -> String {
    match domain.location {
        EconomicLocation::County(county) => {
            let hub = county.geoid().as_str().to_owned();
            match domain.representative {
                None => hub,
                Some((_, position)) => format!(
                    "{hub}/{}",
                    match position {
                        ReservePosition::NoLaborForce => "none",
                        ReservePosition::BelowCellReserveRate => "below",
                        ReservePosition::AtCellReserveRate => "at",
                        ReservePosition::AboveCellReserveRate => "above",
                    }
                ),
            }
        }
        EconomicLocation::Foreign(counterpart) => counterpart.as_str().to_owned(),
        EconomicLocation::Dependency(dependency) => dependency.m49().to_owned(),
    }
}

/// The luxury scale of every account the scenario names: every account of a part and budget key,
/// an account carved from another (an aid child, the claimant) in its own domain, which is its
/// parent's. A scale that names no account is a `Policy` refusal.
pub(super) fn luxury_scales(
    builder: &Builder<'_>,
) -> Result<BTreeMap<FinalDemandPrincipalId, u32>> {
    let mut scales = BTreeMap::new();
    let mut used = vec![false; builder.policy.luxury_scales.len()];
    if builder.policy.luxury_scales.is_empty() {
        return Ok(scales);
    }
    for household in &builder.opening.households {
        let domain = builder.domain(
            AccountId::Household(household.principal_id),
            household.location,
        )?;
        let key = *builder
            .household_keys
            .get(&household.principal_id)
            .ok_or(NationalOpeningError::Identity)?;
        let label = part_label(domain);
        for (index, scale) in builder.policy.luxury_scales.iter().enumerate() {
            if scale.place == label && scale.key == key {
                used[index] = true;
                scales.insert(household.principal_id, scale.bps);
            }
        }
    }
    if used.contains(&false) {
        return Err(NationalOpeningError::Policy);
    }
    Ok(scales)
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_kernel::economic_identity::TradeSet;

    const FIXTURE: &str =
        include_str!("../../../tests/fixtures/national_twelve_trades.defines.toml");
    const SHIPPED: &str = include_str!("../../../../../../content/scenarios/national/defines.toml");

    #[test]
    fn the_catalog_clears_by_price_under_schema_8() {
        let policy = NationalGamePolicy::parse(FIXTURE).expect("the fixture admits");
        let clearing = market_clearing(&policy)
            .expect("the order resolves")
            .expect("schema 8 clears by price");
        let keys = policy
            .markets
            .paying_order
            .as_ref()
            .expect("schema 8 has an order");
        assert_eq!(clearing.paying_order.len(), 9);
        for (key, (good, unit)) in keys.iter().zip(&clearing.paying_order) {
            let commodity = &policy.commodities[key];
            assert_eq!((commodity.good_id, commodity.unit_id), (*good, *unit));
        }
        assert_eq!(clearing.household_wants.len(), 0);
        assert!(!clearing.plans_from_spare_money);
        assert_eq!(clearing.adjustments.len(), 0);
        let shipped = NationalGamePolicy::parse(SHIPPED).expect("the shipped policy admits");
        assert_eq!(market_clearing(&shipped), Ok(None));
    }

    #[test]
    fn recipe_ids_follow_the_set() {
        use EconomicFunction::*;
        let id = |set, function| recipe_id(set, function).map(|id| id.0);
        assert_eq!(id(TradeSet::Ten, DistributionTransport), Ok(4));
        assert_eq!(id(TradeSet::Ten, PublicProvisioning), Ok(10));
        assert_eq!(id(TradeSet::Twelve, ConsumerGoods), Ok(4));
        assert_eq!(id(TradeSet::Twelve, DistributionTransport), Ok(5));
        assert_eq!(id(TradeSet::Twelve, PublicProvisioning), Ok(12));
        assert_eq!(
            id(TradeSet::Ten, ConsumerGoods),
            Err(NationalOpeningError::Policy)
        );
    }
}
