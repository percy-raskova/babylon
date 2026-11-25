//! Compact shared recipes and household needs; no site gets its own template copy.
use super::{NationalOpeningError, Result, FUNCTIONS};
use crate::economic_catalog::{
    CommodityAmount, CommodityLabel, HouseholdNeedCoefficient, HouseholdTemplate,
    HouseholdTemplateId, LaborRequirement, RecipeTemplate, RecipeTemplateId,
};
use crate::national_economy::NationalGamePolicy;
use babylon_kernel::economic_identity::EconomicFunction;
use babylon_material_circuit::HouseholdNeedBasis;
use babylon_material_circuit::{CommodityDefinition, MarketClearingPolicy, UnitId};

type Templates = (
    Vec<CommodityDefinition>,
    Vec<CommodityLabel>,
    Vec<RecipeTemplate>,
    Vec<HouseholdTemplate>,
);

pub(super) fn recipe_id(function: EconomicFunction) -> Result<RecipeTemplateId> {
    let index = FUNCTIONS
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
                id: recipe_id(*function)?,
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

#[cfg(test)]
mod tests {
    use super::*;

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
}
